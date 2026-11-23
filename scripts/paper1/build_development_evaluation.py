"""Compile separate pilot tasks from explicit development-family definitions.

These are rendered drafts, not independently authored paraphrases or validated
judge examples. No model responses, human labels or calibration results exist.
"""
import collections
import hashlib
import itertools
import json
import random
from pathlib import Path

from build_evaluation import OPENINGS, SYSTEM, constraint_text
from build_foundations import evaluate
from score_annotations import violations

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data/paper1'
VERSION = 3
DEFAULT = dict(max_risk='high', max_liquidation_days=20, max_cost_bps=65,
               horizon_years=10, investor_type='retail_only')
DEFINITIONS = [
    ('DEV-01', 'One eligible low-risk energy or transport entry under a five-day liquidation ceiling.', 'one',
     dict(max_risk='low', max_liquidation_days=5, allowed_sectors=['energy', 'transport'])),
    ('DEV-02', 'Multiple options for an institutional investor with a five-year horizon across technology, infrastructure and consumer.', 'multiple',
     dict(investor_type='institutional_only', horizon_years=5, allowed_sectors=['technology', 'infrastructure', 'consumer'])),
    ('DEV-03', 'Retail investor with moderate risk tolerance and an eligible health or infrastructure entry exactly at a twelve-basis-point ceiling.', 'cost_boundary',
     dict(max_risk='moderate', max_cost_bps=12, allowed_sectors=['health', 'infrastructure'])),
    ('DEV-04', 'Institutional investor with a seven-year horizon and ten-day liquidation ceiling; an eligible health, consumer or materials entry meets the horizon boundary.', 'horizon_boundary',
     dict(investor_type='institutional_only', max_liquidation_days=10, horizon_years=7,
          allowed_sectors=['health', 'consumer', 'materials'])),
    ('DEV-05', 'Retail investor with moderate risk tolerance and a three-year horizon boundary in technology, consumer or agriculture.', 'horizon_boundary',
     dict(max_risk='moderate', horizon_years=3, allowed_sectors=['technology', 'consumer', 'agriculture'])),
    ('DEV-06', 'Multiple low-risk energy or materials options for an institutional investor with five-day, twenty-five-basis-point and five-year limits.', 'multiple',
     dict(max_risk='low', investor_type='institutional_only', max_liquidation_days=5, max_cost_bps=25,
          horizon_years=5, allowed_sectors=['energy', 'materials'])),
    ('DEV-07', 'Exactly two retail-eligible technology, health or transport options satisfy ten-day, forty-basis-point and seven-year ceilings.', 'two',
     dict(max_liquidation_days=10, max_cost_bps=40, horizon_years=7,
          allowed_sectors=['technology', 'health', 'transport'])),
    ('DEV-08', 'One infrastructure or agriculture entry fits an institutional investor with five-day and twenty-five-basis-point ceilings.', 'one',
     dict(investor_type='institutional_only', max_liquidation_days=5, max_cost_bps=25,
          allowed_sectors=['infrastructure', 'agriculture'])),
    ('DEV-09', 'No offered candidate meets a retail low-risk, forty-basis-point, seven-year policy restricted to energy, materials and transport; violations differ.', 'none_mixed',
     dict(max_risk='low', max_cost_bps=40, horizon_years=7, allowed_sectors=['energy', 'materials', 'transport'])),
    ('DEV-10', 'Three entries fit an institutional investor in technology, health, infrastructure or consumer; one fails eligibility alone under ten-day, forty-basis-point and seven-year ceilings.', 'three_eligibility',
     dict(investor_type='institutional_only', max_liquidation_days=10, max_cost_bps=40, horizon_years=7,
          allowed_sectors=['technology', 'health', 'infrastructure', 'consumer'])),
    ('DEV-11', 'An eligible low-risk technology, materials or transport entry reaches the five-day liquidation cap under twenty-five-basis-point and five-year limits; another offered entry fails sector alone.', 'liquidity_boundary_with_sector_exclusion',
     dict(max_risk='low', max_liquidation_days=5, max_cost_bps=25, horizon_years=5,
          allowed_sectors=['technology', 'materials', 'transport'])),
    ('DEV-12', 'Two eligible entries tie on all five suitability fields for an institutional investor with moderate risk, ten-day, forty-basis-point and seven-year limits in technology, health, energy or consumer.', 'tie',
     dict(max_risk='moderate', investor_type='institutional_only', max_liquidation_days=10,
          max_cost_bps=40, horizon_years=7,
          allowed_sectors=['technology', 'health', 'energy', 'consumer'])),
]


def family_matches(kind, candidates, investor, checks=None):
    checks = checks if checks is not None else [violations(e, investor) for e in candidates]
    eligible = [e for e, failed in zip(candidates, checks) if not failed]
    n = len(eligible)
    if kind == 'one':
        return n == 1
    if kind == 'two':
        return n == 2
    if kind == 'multiple':
        return n >= 2
    if kind == 'none_mixed':
        return n == 0 and len({tuple(failed) for failed in checks}) > 1
    if kind == 'three_eligibility':
        return n == 3 and any(failed == ['eligibility'] for failed in checks)
    if kind == 'liquidity_boundary_with_sector_exclusion':
        return (any(e['liquidation_days'] == investor['max_liquidation_days'] for e in eligible)
                and any(failed == ['sector'] for failed in checks))
    if kind in ['cost_boundary', 'horizon_boundary', 'liquidity_boundary']:
        field, cap = {'cost_boundary': ('transaction_cost_bps', 'max_cost_bps'),
                      'horizon_boundary': ('minimum_horizon_years', 'horizon_years'),
                      'liquidity_boundary': ('liquidation_days', 'max_liquidation_days')}[kind]
        return any(e[field] == investor[cap] for e in eligible)
    if kind == 'tie':
        fields = ['risk_class', 'liquidation_days', 'transaction_cost_bps', 'minimum_horizon_years', 'eligibility']
        return any(all(a[k] == b[k] for k in fields) for a, b in itertools.combinations(eligible, 2))
    raise ValueError(f'Unimplemented development predicate: {kind}')


def main():
    catalogue = json.loads((DATA / 'catalogue.json').read_text())
    entities, targets = catalogue['entities'], catalogue['target_ids']
    by_id = {e['entity_id']: e for e in entities}
    final = [json.loads(s) for s in (DATA / 'evaluation/scenarios.jsonl').read_text().splitlines()]
    signature = lambda policy: frozenset(e['entity_id'] for e in entities if not violations(e, policy))
    final_signatures = {signature(r['investor']) for r in final}
    development_signatures = set()
    definitions, questions, keys, availability = [], [], [], []
    for index, (fid, descriptor, kind, override) in enumerate(DEFINITIONS):
        investor = {**DEFAULT, **override}
        sig = signature(investor)
        if sig in final_signatures or sig in development_signatures:
            raise ValueError(f'Development eligibility set duplicates another family: {fid}')
        development_signatures.add(sig)
        partition = 'rubric_development' if index < 6 else 'judge_validation'
        definitions.append({'family_id': fid, 'split': 'development', 'calibration_partition': partition,
                            'descriptor': descriptor, 'investor': investor, 'candidate_predicate': kind,
                            'eligible_catalogue_ids': sorted(sig), 'review_status': 'draft_pending_independent_review'})
        checks = {e['entity_id']: violations(e, investor) for e in entities}
        pools = {target: [] for target in targets}
        for group in itertools.combinations(entities, 4):
            ids = [e['entity_id'] for e in group]
            if not family_matches(kind, group, investor, [checks[eid] for eid in ids]):
                continue
            for target in targets:
                if target in ids:
                    pools[target].append(ids)
        for target_index, target in enumerate(targets, 1):
            options = pools[target]
            if not options:
                raise ValueError(f'No candidate set for {fid}, {target}')
            availability.append({'family_id': fid, 'target_id': target, 'feasible_candidate_sets': len(options)})
            rng = random.Random(f'paper1-dev-v1:{fid}:{target}')
            chosen = options[rng.randrange(len(options))]
            others = [eid for eid in chosen if eid != target]
            rng.shuffle(others)
            for paraphrase in range(5):
                ordered = list(others)
                ordered.insert((index + paraphrase) % 4, target)
                qid = f'P1-DEV-V{VERSION}-F{index+1:02d}-T{target_index:02d}-Q{paraphrase+1:02d}'
                query = OPENINGS[paraphrase] + '\n' + constraint_text(investor)
                names = '\n'.join(f'- {by_id[eid]["display_name"]} ({eid})' for eid in ordered)
                user = f'Investor request:\n{query}\n\nCandidates:\n{names}\n\nWhich candidate or candidates, if any, would you recommend for this request?'
                group = [by_id[eid] for eid in ordered]
                key = evaluate(group, investor)
                assert set(key['eligible_entity_ids']) == {eid for eid in ordered if not checks[eid]}
                questions.append({'query_id': qid, 'family_id': fid, 'development_definition_version': VERSION,
                                  'split': 'development', 'calibration_partition': partition,
                                  'paraphrase_group': f'{fid}-T{target_index:02d}', 'paraphrase': paraphrase+1,
                                  'investor': investor, 'candidate_ids': ordered, 'query': query,
                                  'messages': [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': user}],
                                  'answer_key_reference': qid, 'review_status': 'draft_pending_independent_review',
                                  'semantic_split_verified': False, 'research_ready': False})
                keys.append({'query_id': qid, 'development_definition_version': VERSION, 'target_id': target,
                             **key, 'target_constraint_violations': checks[target],
                             'independent_rule_check_passed': True, 'human_reviewed': False})
    if len(questions) != 240 or {r['query_id'] for r in questions} & {r['query_id'] for r in final}:
        raise ValueError('Incomplete or overlapping development query inventory')
    out = DATA / 'evaluation'
    private = DATA / 'private/answer_keys'
    for path, rows in [(out / 'development_scenarios.jsonl', questions), (private / 'development.jsonl', keys)]:
        path.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))
    positions = collections.defaultdict(collections.Counter)
    key_by_id = {r['query_id']: r for r in keys}
    for row in questions:
        target = key_by_id[row['query_id']]['target_id']
        positions[target, row['calibration_partition']][row['candidate_ids'].index(target)] += 1
    position_counts = [{'target_id': target, 'partition': partition, 'counts': [count[i] for i in range(4)]}
                       for (target, partition), count in sorted(positions.items())]
    assert all(max(r['counts']) - min(r['counts']) <= 1 for r in position_counts)
    report = {'development_definition_version': VERSION, 'families': definitions,
              'created_queries': len(questions), 'target_groups': 48, 'paraphrases_per_group': 5,
              'partition_queries': dict(collections.Counter(r['calibration_partition'] for r in questions)),
              'target_position_counts': position_counts, 'feasibility': availability,
              'catalogue_eligibility_sets_distinct_from_final_and_each_other': True,
              'semantic_split_verified': False, 'human_reviewed': False, 'research_ready': False,
              'actual_model_responses': 0, 'calibration_status': 'not_measured',
              'authoring_method': 'Explicit assistant-authored family definitions and deterministic rendering with five shared opening variants; not independent LLM paraphrase generation.',
              'partition_rule': 'DEV-01 through DEV-06 for rubric development; DEV-07 through DEV-12 reserved for judge validation. All target instantiations and paraphrases of a family stay in one partition.',
              'limits': ['Distinct eligible sets do not certify disjoint reasoning patterns or training absence.',
                         'Judge-validation questions and responses must not be used to tune the rubric or judge.',
                         '240 question drafts are not 240 observed responses or independent human labels.',
                         'No pilot context conditions or real-response collection is implied.',
                         'Collect the protocol-required real responses and endpoint-positive/negative counts before calibration.'],
              'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                               [DATA / 'catalogue.json', DATA / 'families.json', out / 'scenarios.jsonl',
                                Path(__file__).resolve(), ROOT / 'scripts/paper1/build_evaluation.py',
                                ROOT / 'scripts/paper1/build_foundations.py', ROOT / 'scripts/paper1/score_annotations.py']}}
    report['artifact_sha256'] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                                [out / 'development_scenarios.jsonl', private / 'development.jsonl']}
    (out / 'development_report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ['created_queries', 'target_groups', 'partition_queries', 'actual_model_responses']}))


if __name__ == '__main__':
    main()
