"""Enumerate catalogue-relative candidate-domain overlap at fixed target.

This checks decision-task containment, not natural-language semantic identity
or observed training exposure. No families or source records are relabelled.
"""
import collections
import hashlib
import itertools
import json
from datetime import datetime, timezone
from pathlib import Path

from build_evaluation import family_matches
from score_annotations import violations

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data/paper1'


def domain_comparison(candidates, left, right, predicate=family_matches):
    counts = collections.Counter()
    witness_left, witness_right = None, None
    for group in candidates:
        a = predicate(left['family_id'], group, left['investor'])
        b = predicate(right['family_id'], group, right['investor'])
        counts['enumerated_candidate_sets'] += 1
        counts['heldout_domain_size'] += a
        counts['represented_domain_size'] += b
        if a and b:
            counts['intersection_size'] += 1
        if a and not b:
            counts['heldout_only_size'] += 1
            if witness_left is None:
                witness_left = [e['entity_id'] for e in group]
        if b and not a:
            counts['represented_only_size'] += 1
            if witness_right is None:
                witness_right = [e['entity_id'] for e in group]
    result = {k: counts[k] for k in ['enumerated_candidate_sets', 'heldout_domain_size', 'represented_domain_size',
                                    'intersection_size', 'heldout_only_size', 'represented_only_size']}
    result.update(heldout_domain_contained=counts['heldout_domain_size'] > 0 and counts['heldout_only_size'] == 0,
                  candidate_domains_equal=counts['heldout_domain_size'] > 0 and counts['heldout_only_size'] == counts['represented_only_size'] == 0,
                  heldout_only_witness=witness_left, represented_only_witness=witness_right)
    return result


def main():
    catalogue_path = DATA / 'catalogue.json'
    scenarios_path = DATA / 'evaluation/scenarios.jsonl'
    keys_path = DATA / 'private/answer_keys/evaluation.jsonl'
    catalogue = json.loads(catalogue_path.read_text())
    entities = catalogue['entities']
    keys = {r['query_id']: r for r in map(json.loads, keys_path.read_text().splitlines())}
    groups = {}
    for row in map(json.loads, scenarios_path.read_text().splitlines()):
        group_id = row['paraphrase_group']
        if group_id not in groups:
            groups[group_id] = {**row, 'target_id': keys[row['query_id']]['target_id'],
                               'eligible_universe': frozenset(e['entity_id'] for e in entities if not violations(e, row['investor']))}
    results = []
    for heldout in groups.values():
        if heldout['split'] != 'heldout':
            continue
        represented = [r for r in groups.values() if r['split'] == 'represented'
                       and r['target_id'] == heldout['target_id'] and r['eligible_universe'] == heldout['eligible_universe']]
        if not represented:
            continue
        target = next(e for e in entities if e['entity_id'] == heldout['target_id'])
        others = [e for e in entities if e['entity_id'] != heldout['target_id']]
        # Four-candidate sets containing the same target: C(39, 3) = 9,139.
        candidates = [[target, *other] for other in itertools.combinations(others, 3)]
        for rep in represented:
            result = domain_comparison(candidates, heldout, rep)
            result.update(heldout_group=heldout['paraphrase_group'], represented_group=rep['paraphrase_group'],
                          heldout_family=heldout['family_id'], represented_family=rep['family_id'],
                          same_target=True, eligibility_decisions_equal_on_catalogue=True,
                          identical_constraints=heldout['investor'] == rep['investor'])
            results.append(result)
    covered = {r['heldout_group'] for r in results if r['heldout_domain_contained']}
    all_heldout = [g for g in groups.values() if g['split'] == 'heldout']
    contained_families = sorted({g['family_id'] for g in all_heldout
                                if all(h['paraphrase_group'] in covered for h in all_heldout if h['family_id'] == g['family_id'])})
    source_paths = [catalogue_path, scenarios_path, keys_path,
                    ROOT / 'scripts/paper1/build_evaluation.py', ROOT / 'scripts/paper1/score_annotations.py', Path(__file__)]
    report = {'created_utc': datetime.now(timezone.utc).isoformat(),
              'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths},
              'method': 'Exhaustive unordered four-candidate domains at fixed target; only compared when all 40 catalogue eligibility decisions agree.',
              'comparison_count': len(results), 'contained_heldout_groups': len(covered), 'heldout_groups': len(all_heldout),
              'families_contained_for_all_targets': contained_families, 'comparisons': results,
              'research_ready': False, 'semantic_isolation_verified': False, 'training_exposure_verified': False,
              'interpretation': 'Containment means every allowed held-out candidate set also satisfies a represented candidate predicate with identical eligibility decisions. Constraint wording and explanations may differ. This proves operational overlap in the finite catalogue, not that any specific training record teaches that pattern.',
              'unmatched_families_note': 'No conclusion of novelty follows for families without an equal-eligibility represented comparator.'}
    path = DATA / 'validation/family_domain_overlap.json'
    path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ['comparison_count', 'contained_heldout_groups', 'families_contained_for_all_targets']}))


if __name__ == '__main__':
    main()
