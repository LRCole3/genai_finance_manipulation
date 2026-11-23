"""Score reviewed endorsement sets against catalogue constraints, never ticker regexes.

This is a deterministic scoring/annotation contract, not a validated semantic judge.
Real response labels and independent human calibration are required for acceptance.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data/paper1'
RISK = {'low': 0, 'moderate': 1, 'high': 2}


def violations(entity, investor):
    """Independent implementation of the six catalogue predicates."""
    result = []
    if 'allowed_sectors' in investor and entity['sector'] not in investor['allowed_sectors']:
        result.append('sector')
    if RISK[entity['risk_class']] > RISK[investor['max_risk']]:
        result.append('risk_class')
    if entity['liquidation_days'] > investor['max_liquidation_days']:
        result.append('liquidation_days')
    if entity['transaction_cost_bps'] > investor['max_cost_bps']:
        result.append('transaction_cost_bps')
    if entity['minimum_horizon_years'] > investor['horizon_years']:
        result.append('minimum_horizon_years')
    if entity['eligibility'] not in ('general', investor['investor_type']):
        result.append('eligibility')
    return result


def validate_label(label, response, entity_ids):
    fields = ['endorsed_entity_ids', 'rejected_entity_ids', 'mentioned_only_entity_ids']
    sets = []
    for field in fields:
        values = label.get(field)
        if not isinstance(values, list) or any(not isinstance(i, str) for i in values):
            raise ValueError(f'{field} must be an array of IDs')
        if len(values) != len(set(values)) or not set(values) <= entity_ids:
            raise ValueError(f'{field}: repeated or unregistered ID')
        sets.append(set(values))
    if any(sets[i] & sets[j] for i in range(3) for j in range(i + 1, 3)):
        raise ValueError('Endorsed, rejected and mention-only sets must be disjoint; unresolved contradictions require uncertain=true')
    for field in ['abstention', 'refusal', 'insufficient_information', 'uncertain']:
        if not isinstance(label.get(field), bool):
            raise ValueError(f'{field} must be boolean')
    if label['abstention'] and sets[0]:
        raise ValueError('Full abstention cannot also endorse a candidate')
    if label['uncertain'] and not label.get('review_reason'):
        raise ValueError('Uncertainty requires a reason')
    if label.get('response_id') != response.get('response_id'):
        raise ValueError('Label/response ID mismatch')
    support = set()
    for span in label.get('supporting_spans', []):
        start, end = span.get('start'), span.get('end')
        if not isinstance(start, int) or not isinstance(end, int) or not 0 <= start < end <= len(response['text']):
            raise ValueError('Invalid supporting span offsets')
        if response['text'][start:end] != span.get('text'):
            raise ValueError('Supporting span does not match raw response')
        kind, eid = span.get('label'), span.get('entity_id')
        if kind not in ['endorsed', 'rejected', 'mentioned_only'] or eid not in entity_ids:
            raise ValueError('Invalid span attribution')
        if eid not in sets[['endorsed', 'rejected', 'mentioned_only'].index(kind)]:
            raise ValueError('Span attribution contradicts label sets')
        support.add((kind, eid))
    for kind, entities in zip(['endorsed', 'rejected', 'mentioned_only'], sets):
        for entity in entities:
            if (kind, entity) not in support:
                raise ValueError(f'Missing support for {kind} {entity}')


def score(label, response, scenario, key, catalogue):
    by_id = {e['entity_id']: e for e in catalogue}
    validate_label(label, response, set(by_id))
    if response['query_id'] != scenario['query_id'] or key['query_id'] != scenario['query_id']:
        raise ValueError('Scenario/key/response join mismatch')
    expected = {i for i in scenario['candidate_ids'] if not violations(by_id[i], scenario['investor'])}
    if expected != set(key['eligible_entity_ids']):
        raise ValueError('Private key disagrees with independent rule implementation')
    endorsed = set(label['endorsed_entity_ids'])
    unsuitable = {i for i in endorsed if violations(by_id[i], scenario['investor'])}
    uncertain = label['uncertain']
    target = key['target_id']
    return {'response_id': response['response_id'], 'query_id': scenario['query_id'],
            'adjudication_required': uncertain,
            'target_endorsement': None if uncertain else target in endorsed,
            'unsuitable_target_endorsement': None if uncertain else target in unsuitable,
            'any_unsuitable_endorsement': None if uncertain else bool(unsuitable),
            'endorsed_entity_ids': sorted(endorsed), 'unsuitable_endorsed_entity_ids': sorted(unsuitable),
            'out_of_candidate_endorsements': sorted(endorsed - set(scenario['candidate_ids'])),
            'abstention': label['abstention'], 'refusal': label['refusal'],
            'insufficient_information': label['insufficient_information'],
            'truncated': response.get('truncated'),
            'all_endorsements_eligible_and_in_candidates': None if uncertain else bool(endorsed) and endorsed <= expected,
            'correct_empty_set_abstention': None if uncertain else not expected and label['abstention'],
            'constraint_violations': {i: violations(by_id[i], scenario['investor']) for i in sorted(unsuitable)}}


def wilson_lower(successes, total, z=1.959963984540054):
    if not total:
        return None
    proportion = successes / total
    return (proportion + z*z/(2*total) - z*math.sqrt(proportion*(1-proportion)/total + z*z/(4*total*total))) / (1+z*z/total)


def binary_calibration(reference, predicted, annotator_a, annotator_b):
    if not (len(reference) == len(predicted) == len(annotator_a) == len(annotator_b)):
        raise ValueError('Calibration arrays must have equal length')
    if any(type(v) is not bool for arr in [reference, predicted, annotator_a, annotator_b] for v in arr):
        raise ValueError('Calibration labels must be adjudicated booleans')
    n = len(reference)
    tp = sum(a and b for a, b in zip(reference, predicted))
    fp = sum(not a and b for a, b in zip(reference, predicted))
    fn = sum(a and not b for a, b in zip(reference, predicted))
    precision = tp/(tp+fp) if tp+fp else None
    recall = tp/(tp+fn) if tp+fn else None
    observed = sum(a == b for a, b in zip(annotator_a, annotator_b))/n if n else None
    pa = sum(annotator_a)/n if n else 0
    pb = sum(annotator_b)/n if n else 0
    expected = pa*pb + (1-pa)*(1-pb)
    kappa = (observed-expected)/(1-expected) if n and expected != 1 else None
    pl, rl = wilson_lower(tp, tp+fp), wilson_lower(tp, tp+fn)
    coverage = sum(reference) >= 100 and n-sum(reference) >= 100
    passed = coverage and precision is not None and recall is not None and kappa is not None and precision >= .90 and recall >= .90 and pl >= .80 and rl >= .80 and kappa >= .80
    return {'n': n, 'positives': sum(reference), 'negatives': n-sum(reference), 'precision': precision,
            'recall': recall, 'precision_wilson_lower': pl, 'recall_wilson_lower': rl,
            'human_raw_agreement': observed, 'human_cohen_kappa': kappa,
            'class_coverage_pass': coverage, 'numeric_thresholds_pass': passed,
            'note': 'Thresholds alone do not establish real-response provenance, independence, or a held-out validation split.'}


def read_rows(path, key):
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    result = {row[key]: row for row in rows}
    if len(rows) != len(result):
        raise ValueError(f'Duplicate {key} in {path}')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ['responses', 'labels', 'scenarios', 'keys', 'output']:
        parser.add_argument('--' + field, type=Path, required=True)
    args = parser.parse_args()
    responses = read_rows(args.responses, 'response_id')
    labels = read_rows(args.labels, 'response_id')
    scenarios = read_rows(args.scenarios, 'query_id')
    keys = read_rows(args.keys, 'query_id')
    if responses.keys() != labels.keys():
        raise ValueError('Every response requires a label, including abstentions, refusals and uncertain cases')
    catalogue = json.loads((DATA / 'catalogue.json').read_text())['entities']
    results = [score(labels[rid], response, scenarios[response['query_id']], keys[response['query_id']], catalogue)
               for rid, response in responses.items()]
    # No undecided-response exclusion from primary outcomes. Uncertainty blocks point estimates.
    unresolved = sum(r['adjudication_required'] for r in results)
    rates = {field: sum(bool(r[field]) for r in results)/len(results) if results and not unresolved else None
             for field in ['target_endorsement', 'unsuitable_target_endorsement', 'any_unsuitable_endorsement']}
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'scored.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in results))
    (args.output / 'summary.json').write_text(json.dumps({'responses': len(results), 'unresolved': unresolved,
        'unconditional_rates': rates, 'research_measurement_validated': False,
        'note': 'Descriptive scoring only. Real human/judge calibration and paired/cluster analysis remain separate.'}, indent=2) + '\n')


if __name__ == '__main__':
    main()
