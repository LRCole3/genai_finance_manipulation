"""Construct reviewable family-policy alternatives without changing evaluation.

Catalogue-wide eligibility separation is a diagnostic, not semantic novelty or
proof of absent training exposure. Candidate witnesses preserve the implemented
family predicates and target-presence requirements.
"""
import argparse
import hashlib
import itertools
import json
from pathlib import Path

from build_evaluation import family_matches
from build_foundations import evaluate
from score_annotations import violations

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data/paper1'
FIELDS = ['max_risk', 'investor_type', 'max_liquidation_days', 'max_cost_bps', 'horizon_years']
FAMILIES = ['HOLD-02', 'HOLD-03', 'HOLD-04', 'HOLD-06', 'HOLD-07', 'HOLD-08', 'HOLD-09', 'HOLD-12']


def signature(entities, policy):
    return tuple(e['entity_id'] for e in entities if not violations(e, policy))


def policy_grid(entities):
    # Each nonnegative threshold interval is equivalent to its greatest passed
    # catalogue value. Zero represents the interval below the minimum.
    axes = [['low', 'moderate', 'high'], ['retail_only', 'institutional_only']]
    axes.extend([[0] + sorted({e[field] for e in entities}) for field in
                 ['liquidation_days', 'transaction_cost_bps', 'minimum_horizon_years']])
    return [dict(zip(FIELDS, values)) for values in itertools.product(*axes)], axes


def core_preserved(family, policy):
    if family == 'HOLD-02':
        return policy['horizon_years'] == 7 and policy['max_liquidation_days'] == 2
    if family == 'HOLD-03':
        return policy['investor_type'] == 'retail_only' and policy['max_cost_bps'] == 5
    if family == 'HOLD-09':
        return policy['investor_type'] == 'institutional_only'
    return True


def candidate_witness(entities, family, policy, target_id):
    if not core_preserved(family, policy):
        return None
    by_id = {e['entity_id']: e for e in entities}
    checks = {e['entity_id']: violations(e, policy) for e in entities}
    eligible = [e for e in entities if not checks[e['entity_id']]]
    required = []
    if family == 'HOLD-12':
        # This family has exactly three eligible entries and one excluded only
        # by eligibility. A different target violation makes it infeasible.
        bad = [e for e in entities if checks[e['entity_id']] == ['eligibility']]
        target_check = checks[target_id]
        if len(eligible) < 3 or not bad or target_check not in ([], ['eligibility']):
            return None
        if target_check:
            required = eligible[:3] + [by_id[target_id]]
        else:
            required = [by_id[target_id]] + [e for e in eligible if e['entity_id'] != target_id][:2] + bad[:1]
    elif family == 'HOLD-06':
        fields = ['risk_class', 'liquidation_days', 'transaction_cost_bps', 'minimum_horizon_years', 'eligibility']
        pair = next((pair for pair in itertools.combinations(eligible, 2)
                     if all(pair[0][k] == pair[1][k] for k in fields)), None)
        if pair is None:
            return None
        required = list(pair)
    else:
        candidates = eligible
        if family == 'HOLD-04':
            candidates = [e for e in eligible if all(e[a] == policy[b] for a, b in
                          [('risk_class', 'max_risk'), ('liquidation_days', 'max_liquidation_days'),
                           ('transaction_cost_bps', 'max_cost_bps'), ('minimum_horizon_years', 'horizon_years')])]
        elif family == 'HOLD-07':
            candidates = [e for e in eligible if e['minimum_horizon_years'] == policy['horizon_years']]
        elif family == 'HOLD-08':
            candidates = [e for e in eligible if e['liquidation_days'] == policy['max_liquidation_days']]
        elif family == 'HOLD-09':
            candidates = [e for e in eligible if e['eligibility'] == 'general' and
                          e['transaction_cost_bps'] == policy['max_cost_bps']]
        if not candidates:
            return None
        required = candidates[:1]
    ordered = dict.fromkeys([target_id] + [e['entity_id'] for e in required])
    if len(ordered) > 4:
        return None
    for e in entities:
        if len(ordered) == 4:
            break
        ordered[e['entity_id']] = None
    group = [by_id[eid] for eid in ordered]
    assert len(group) == 4 and family_matches(family, group, policy)
    key = evaluate(group, policy)
    independent = [e['entity_id'] for e in group if not violations(e, policy)]
    assert set(independent) == set(key['eligible_entity_ids'])
    return {'candidate_ids': list(ordered), 'eligible_entity_ids': independent,
            'target_eligible': target_id in independent, 'predicate_verified': True,
            'independent_key_agreement': True}


def distance(policy, original):
    return sum(policy.get(k) != original.get(k) for k in set(policy) | set(original))


def assign_distinct(options):
    """Maximum matching, then minimum changed policy fields; no scientific ranking."""
    states = {frozenset(): (0, {})}
    for family in sorted(options):
        new = {}
        for used, (cost, chosen) in states.items():
            for option in [None] + options[family]:
                sig = tuple(option['eligible_catalogue_ids']) if option else None
                if sig in used:
                    continue
                next_used = used | {sig} if option else used
                value = (cost + (option['changed_field_count'] if option else 0),
                         {**chosen, **({family: option} if option else {})})
                if next_used not in new or value[0] < new[next_used][0]:
                    new[next_used] = value
        states = new
    _, (cost, chosen) = min(states.items(), key=lambda item: (-len(item[0]), item[1][0]))
    return {'matched_families': len(chosen), 'changed_policy_fields': cost,
            'unmatched_families': sorted(set(options) - set(chosen)), 'assignments': chosen}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenarios', type=Path,
                        default=DATA / 'revisions/evaluation_family_v2/evaluation/scenarios.jsonl')
    args = parser.parse_args()
    catalogue_path = DATA / 'catalogue.json'
    scenarios_path = args.scenarios
    catalogue = json.loads(catalogue_path.read_text())
    entities, targets = catalogue['entities'], catalogue['target_ids']
    scenarios = [json.loads(s) for s in scenarios_path.read_text().splitlines()]
    represented = {signature(entities, r['investor']) for r in scenarios if r['split'] == 'represented'}
    original = {family: next(r['investor'] for r in scenarios if r['family_id'] == family) for family in FAMILIES}
    policies, axes = policy_grid(entities)
    signatures = {signature(entities, p) for p in policies}
    novel = signatures - represented
    options = {family: {} for family in FAMILIES}
    for family in FAMILIES:
        ranked = sorted(policies, key=lambda p: (distance(p, original[family]), json.dumps(p, sort_keys=True)))
        for policy in ranked:
            sig = signature(entities, policy)
            if sig not in novel or sig in options[family] or not core_preserved(family, policy):
                continue
            witnesses = {target: candidate_witness(entities, family, policy, target) for target in targets}
            if not all(witnesses.values()):
                continue
            options[family][sig] = {'policy': policy, 'eligible_catalogue_ids': list(sig),
                                    'changed_fields': {k: {'before': original[family].get(k), 'after': policy.get(k)}
                                                       for k in FIELDS if policy.get(k) != original[family].get(k)},
                                    'changed_field_count': distance(policy, original[family]),
                                    'candidate_witnesses': witnesses}
    options = {family: list(values.values()) for family, values in options.items()}
    matching = assign_distinct(options)
    # Show a concrete extension for the unmatched family, preserving all target
    # sectors. This is a substantive added constraint, explicitly not approved.
    expanded = {family: list(values) for family, values in options.items()}
    by_id = {e['entity_id']: e for e in entities}
    target_sectors = sorted({by_id[t]['sector'] for t in targets})
    existing_heldout = {signature(entities, r['investor']) for r in scenarios if r['split'] == 'heldout'}
    for family in matching['unmatched_families']:
        policy = {**original[family], 'allowed_sectors': target_sectors}
        sig = signature(entities, policy)
        witnesses = {target: candidate_witness(entities, family, policy, target) for target in targets}
        if sig not in represented | existing_heldout and all(witnesses.values()):
            expanded[family].append({'policy': policy, 'eligible_catalogue_ids': list(sig),
                                     'changed_fields': {'allowed_sectors': {'before': None, 'after': target_sectors}},
                                     'changed_field_count': 1, 'candidate_witnesses': witnesses,
                                     'substantive_sector_extension': True})
    extension = assign_distinct(expanded)
    paths = [catalogue_path, scenarios_path, ROOT / 'scripts/paper1/build_evaluation.py',
             ROOT / 'scripts/paper1/build_foundations.py', ROOT / 'scripts/paper1/score_annotations.py', Path(__file__).resolve()]
    report = {'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
              'scope': 'Catalogue-wide eligibility separation and four-candidate feasibility; does not establish semantic isolation.',
              'threshold_axes': dict(zip(FIELDS, axes)), 'enumerated_policies': len(policies),
              'distinct_unrestricted_eligibility_sets': len(signatures),
              'represented_eligibility_sets': len(represented),
              'unused_unrestricted_eligibility_sets': len(novel),
              'families_considered': FAMILIES, 'options_by_family': options,
              'maximum_distinct_assignment_without_sector_changes': matching,
              'candidate_assignment_with_sector_extension': extension,
              'baseline_family_definition_versions': sorted({r['family_definition_version'] for r in scenarios}),
              'assessment_modifies_evaluation': False, 'research_ready': False, 'human_reviewed': False,
              'interpretation': 'Only seven unrestricted eligibility sets are unused by represented policies. Eight held-out families cannot all receive distinct unused eligibility sets using only these fields. This is a counting result for the stated diagnostic, not a proof that eight semantically distinct tasks are impossible. Candidate predicates, explanations and actual training exposure need separate review.',
              'limitations': ['The target-sector extension is a proposed design change, not an accepted family definition.',
                             'Unused eligibility sets are not proof of absent training patterns.',
                             'Witnesses establish feasibility, not a balanced evaluation sample or reviewed wording.',
                             'Minimum changed fields is an engineering selection criterion, not a scientific preference.',
                             'No original catalogue, training record, evaluation question or private key is changed.']}
    path = DATA / 'validation/family_repair_feasibility.json'
    path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ['enumerated_policies', 'distinct_unrestricted_eligibility_sets',
                                           'unused_unrestricted_eligibility_sets']}))
    for name, result in [('numeric_only', matching), ('sector_extension', extension)]:
        print(json.dumps({'design': name, 'matched': result['matched_families'], 'unmatched': result['unmatched_families'],
                          'proposed_policies': {family: row['policy'] for family, row in result['assignments'].items()}}))


if __name__ == '__main__':
    main()
