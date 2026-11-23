"""Compare explicitly reviewed training filters with held-out selection rules.

This consumes assistant-authored semantic annotations; it does not infer them
from keyword matches, supply missing investor constraints, or certify a split.
"""
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from build_evaluation import family_matches, policy
from score_annotations import violations

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data/paper1'
NUMERIC = {'liquidation_days', 'transaction_cost_bps', 'minimum_horizon_years'}
CATEGORICAL = {'sector', 'risk_class', 'eligibility'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def matches(entity, selection):
    if set(selection) != {'all'} or not isinstance(selection['all'], list) or not selection['all']:
        raise ValueError('A reviewed filter must contain a nonempty conjunction')
    answers = []
    for clause in selection['all']:
        if set(clause) != {'field', 'operator', 'value'}:
            raise ValueError('Unexpected filter clause fields')
        field, op, value = clause['field'], clause['operator'], clause['value']
        if field not in NUMERIC | CATEGORICAL or op not in {'eq', 'in', 'lt', 'lte', 'gt', 'gte'}:
            raise ValueError('Unsupported field or operator')
        values = value if op == 'in' else [value]
        if not isinstance(values, list) or not values:
            raise ValueError('Membership requires a nonempty value list')
        if field in NUMERIC and any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
            raise ValueError('Numeric fields require numeric operands')
        if field in CATEGORICAL and (op not in {'eq', 'in'} or any(not isinstance(v, str) for v in values)):
            raise ValueError('Category labels have no implicit numeric ordering')
        actual = entity[field]
        if op == 'in':
            answers.append(actual in value)
        elif op == 'eq':
            answers.append(actual == value)
        elif op == 'lt':
            answers.append(actual < value)
        elif op == 'lte':
            answers.append(actual <= value)
        elif op == 'gt':
            answers.append(actual > value)
        else:
            answers.append(actual >= value)
    return all(answers)


def verify_annotation(annotation, row, candidates):
    if annotation['messages'] != row['messages'] or annotation['messages_sha256'] != canonical_hash(row['messages']):
        raise ValueError('Reviewed annotation is stale for the training text')
    ids = annotation['candidate_ids']
    if len(ids) != len(set(ids)) or ids != [e['entity_id'] for e in candidates]:
        raise ValueError('Reviewed candidate scope disagrees with its source')
    selected = sorted(e['entity_id'] for e in candidates if matches(e, annotation['selection']))
    if selected != sorted(annotation['reviewed_selected_entity_ids']) or len(selected) != annotation['reviewed_selected_count']:
        raise ValueError('Executable filter disagrees with the reviewed answer')
    return selected


def compare(annotation, candidates, entities, family):
    investor = policy(family)
    training = {e['entity_id'] for e in entities if matches(e, annotation['selection'])}
    heldout = {e['entity_id'] for e in entities if not violations(e, investor)}
    candidate_ids = {e['entity_id'] for e in candidates}
    local_training, local_heldout = training & candidate_ids, heldout & candidate_ids
    witnesses = [{'entity_id': eid, 'training_filter_accepts': eid in training,
                  'heldout_policy_accepts': eid in heldout} for eid in sorted(training ^ heldout)]
    return {'family_id': family, 'heldout_policy': investor,
            'catalogue_selection_sets_equal': training == heldout,
            'training_scope_selection_sets_equal': local_training == local_heldout,
            'heldout_candidate_predicate_on_training_scope': family_matches(family, candidates, investor),
            'heldout_selected_on_training_scope': sorted(local_heldout),
            'distinguishing_catalogue_entities': witnesses,
            'note': 'Candidate-predicate agreement omits target membership and does not establish full task equivalence.'}


def main():
    annotation_path = DATA / 'revisions/training_filter_annotations_001.json'
    paths = [annotation_path, DATA / 'exports/it_drafts.jsonl', DATA / 'catalogue.json',
             DATA / 'evaluation/scenarios.jsonl', DATA / 'evaluation/build_report.json',
             Path(__file__).resolve(), ROOT / 'scripts/paper1/build_evaluation.py',
             ROOT / 'scripts/paper1/score_annotations.py']
    rows = {r['item_id']: r for r in map(json.loads, (DATA / 'exports/it_drafts.jsonl').read_text().splitlines())}
    entities = json.loads((DATA / 'catalogue.json').read_text())['entities']
    by_id = {e['entity_id']: e for e in entities}
    annotations = json.loads(annotation_path.read_text())['annotations']
    if len({a['item_id'] for a in annotations}) != len(annotations):
        raise ValueError('Duplicate annotation ID')
    findings = []
    for annotation in annotations:
        source = ROOT / annotation['candidate_source']['path']
        if sha(source) != annotation['candidate_source']['sha256']:
            raise ValueError('Candidate source changed')
        candidates = json.loads(source.read_text())['entities']
        if any(e != by_id[e['entity_id']] for e in candidates):
            raise ValueError('Candidate facts differ from current catalogue')
        paths.append(source)
        selected = verify_annotation(annotation, rows[annotation['item_id']], candidates)
        findings.append({'item_id': annotation['item_id'], 'task_kind': annotation['task_kind'],
                         'selected_entity_ids': selected,
                         'comparisons': [compare(annotation, candidates, entities, f'HOLD-{i:02d}') for i in range(1, 13)]})
    comparisons = [c for r in findings for c in r['comparisons']]
    report = {'created_utc': datetime.now(timezone.utc).isoformat(),
              'source_sha256': {str(p.relative_to(ROOT)): sha(p) for p in paths},
              'reviewed_training_tasks': len(findings), 'heldout_comparisons': len(comparisons),
              'catalogue_selection_equalities': sum(c['catalogue_selection_sets_equal'] for c in comparisons),
              'local_selection_equalities': sum(c['training_scope_selection_sets_equal'] for c in comparisons),
              'all_reviewed_filter_answers_match': True, 'findings': findings,
              'independent_human_acceptance': False, 'semantic_isolation_verified': False,
              'research_ready': False,
              'limits': ['Only the explicitly annotated tasks were reviewed; all other training records remain outside this comparison.',
                         'Equal outputs on four candidates are weaker than equal rules. Conversely, different catalogue sets do not prove semantic novelty.',
                         'Filter lookup and investor suitability differ in operators, access interpretation and task framing; no missing constraints were supplied.',
                         'These assistant annotations do not replace independent semantic review or populate accepted family_ids.']}
    (DATA / 'validation/training_filter_review.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ['reviewed_training_tasks', 'heldout_comparisons',
                                          'catalogue_selection_equalities', 'local_selection_equalities']}))


if __name__ == '__main__':
    main()
