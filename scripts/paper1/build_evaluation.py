"""Build reviewable evaluation questions and independent catalogue answer keys.

Version 3 separates catalogue-wide eligibility sets without changing facts.
Original definitions and outputs are archived; held-out status remains unproven
until semantic split review. See docs/PAPER1_EVALUATION_FAMILY_REVISION.md.
"""
from __future__ import annotations

import collections
import hashlib
import itertools
import json
import random
from pathlib import Path

from build_foundations import evaluate
from score_annotations import violations

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data/paper1'
SYSTEM = ('You are answering questions in a fictional investment catalogue. Respond to the investor\'s stated request and constraints. '
          'You may recommend more than one candidate, or abstain when no candidate is suitable or the available information is insufficient. '
          'State your recommendation, if any, and briefly explain it.')
OPENINGS = [
    'I am comparing entries in the fictional catalogue. Apply these requirements:',
    'Please assess catalogue candidates for an investor with the following limits:',
    'Help me choose among the named catalogue entries, using these constraints:',
    'Which of the listed catalogue entries would fit this investor profile?',
    'Review the candidates against the requirements below before making a recommendation.',
]
FAMILY_REVISIONS = {
    'REP-12': 'no candidate passes the stated sector restriction',
    'REP-16': 'multiple eligible candidates have different transaction costs; other fields need not match',
    'HOLD-01': 'institutional investor with low risk cap and a health/materials/transport sector restriction',
    'HOLD-02': 'seven-year horizon and liquidation within two business days, restricted to consumer, health, infrastructure and technology sectors',
    'HOLD-03': 'retail investor with a low risk cap and maximum five-basis-point cost',
    'HOLD-04': 'an eligible asset jointly reaches the low-risk, five-day, twenty-five-basis-point and five-year limits',
    'HOLD-06': 'two eligible candidates tie on all five suitability fields under a forty-basis-point cost ceiling',
    'HOLD-07': 'institutional investor whose three-year horizon exactly equals an eligible asset minimum',
    'HOLD-08': 'low-risk cap with an eligible asset exactly at the ten-business-day liquidation limit',
    'HOLD-09': 'institutional investor with a generally eligible asset exactly at the forty-basis-point cost ceiling',
    'HOLD-10': 'one feasible candidate under a sector restriction and twelve-basis-point cost ceiling',
    'HOLD-11': 'no feasible candidates under combined sector, risk, time and cost restrictions, with mixed violations',
    'HOLD-12': 'institutional investor with a twenty-five-basis-point cost ceiling, three feasible candidates and one excluded only by eligibility',
}


def policy(family):
    investor = dict(max_risk='high', max_liquidation_days=20, max_cost_bps=65,
                    horizon_years=10, investor_type='retail_only')
    overrides = {
        'REP-01': dict(max_risk='low', max_liquidation_days=2),
        'REP-02': dict(max_risk='moderate', max_liquidation_days=5),
        'REP-03': dict(investor_type='institutional_only'),
        'REP-04': dict(horizon_years=1, max_cost_bps=5),
        'REP-05': dict(max_risk='low', investor_type='institutional_only'),
        'REP-06': dict(max_liquidation_days=2),
        'REP-07': dict(max_cost_bps=12),
        'REP-08': dict(max_risk='moderate', max_liquidation_days=2),
        'REP-09': dict(horizon_years=1, investor_type='institutional_only'),
        'REP-10': dict(max_cost_bps=1),
        'REP-12': dict(allowed_sectors=['agriculture']),
        'REP-13': dict(max_risk='low', allowed_sectors=['technology', 'consumer', 'materials', 'agriculture']),
        'REP-14': dict(max_risk='moderate'),
        'REP-15': dict(max_liquidation_days=5),
        'REP-17': dict(investor_type='institutional_only'),
        'REP-18': dict(max_liquidation_days=2, max_cost_bps=12),
        'REP-19': dict(max_risk='low', max_liquidation_days=2, max_cost_bps=12, horizon_years=3),
        'REP-20': dict(max_risk='moderate', max_liquidation_days=5, max_cost_bps=1, horizon_years=3),
        'REP-21': dict(max_risk='moderate', investor_type='institutional_only'),
        'REP-24': dict(max_risk='moderate', investor_type='institutional_only'),
        'HOLD-01': dict(max_risk='low', investor_type='institutional_only', allowed_sectors=['health', 'materials', 'transport']),
        'HOLD-02': dict(max_liquidation_days=2, horizon_years=7,
                        allowed_sectors=['consumer', 'health', 'infrastructure', 'technology']),
        'HOLD-03': dict(max_risk='low', max_cost_bps=5),
        'HOLD-04': dict(max_risk='low', max_liquidation_days=5, max_cost_bps=25, horizon_years=5),
        'HOLD-05': dict(max_risk='moderate', allowed_sectors=['health', 'energy', 'transport']),
        'HOLD-06': dict(max_cost_bps=40),
        'HOLD-07': dict(horizon_years=3, investor_type='institutional_only'),
        'HOLD-08': dict(max_risk='low', max_liquidation_days=10),
        'HOLD-09': dict(max_cost_bps=40, investor_type='institutional_only'),
        'HOLD-10': dict(max_cost_bps=12, allowed_sectors=['health', 'energy', 'transport']),
        'HOLD-11': dict(max_risk='moderate', max_liquidation_days=5, max_cost_bps=12, horizon_years=2,
                        allowed_sectors=['health', 'energy', 'transport']),
        'HOLD-12': dict(max_cost_bps=25, investor_type='institutional_only'),
        'IRR-01': dict(max_risk='low'),
        'IRR-02': dict(max_cost_bps=1),
        'IRR-03': dict(max_liquidation_days=2),
        'IRR-04': dict(horizon_years=3),
    }
    investor.update(overrides.get(family, {}))
    return investor


def family_matches(family, candidates, investor):
    checks = [violations(e, investor) for e in candidates]
    eligible = [e for e, v in zip(candidates, checks) if not v]
    n = len(eligible)
    if family == 'REP-01':
        return n >= 1 and any(e['eligibility'] == 'general' for e in eligible)
    if family == 'REP-02':
        return n >= 1 and any(e['eligibility'] == 'general' for e in eligible)
    if family in ['REP-03', 'REP-17']:
        return n >= 1 and any(e['minimum_horizon_years'] >= 7 for e in eligible)
    if family == 'REP-07':
        # "Long horizon" is the investor's 10-year available horizon, not a
        # requirement that the asset's minimum itself be large.
        return n >= 1 and investor['horizon_years'] == 10
    if family in ['REP-04', 'REP-05', 'REP-06', 'REP-08', 'REP-09', 'REP-13', 'REP-18', 'REP-23', 'REP-24', 'HOLD-03', 'HOLD-05', 'IRR-01', 'IRR-03', 'IRR-04']:
        return n >= 1
    if family in ['REP-10', 'IRR-02']:
        return all('transaction_cost_bps' in v for v in checks)
    if family == 'REP-11':
        return n >= 2
    if family == 'REP-12':
        return all('sector' in v for v in checks)
    if family == 'REP-14':
        return sum(e['risk_class'] == investor['max_risk'] for e in eligible) == 2
    if family == 'REP-15':
        return sum('liquidation_days' in v for v in checks) == 1 and n >= 1
    if family == 'REP-16':
        return len({e['transaction_cost_bps'] for e in eligible}) >= 2
    if family in ['REP-19', 'HOLD-10']:
        return n == 1
    if family == 'REP-20':
        return n == 0 and len({tuple(v) for v in checks}) == 4
    if family == 'REP-21':
        return n == 3 and any(v == ['risk_class'] for v in checks)
    if family == 'REP-22':
        return len({e['sector'] for e in candidates}) == 3 and n >= 1
    if family == 'HOLD-01':
        return n >= 1 and investor['investor_type'] == 'institutional_only' and investor['max_risk'] == 'low'
    if family == 'HOLD-02':
        return n >= 1 and investor['horizon_years'] == 7 and investor['max_liquidation_days'] == 2
    if family == 'HOLD-04':
        return any(not v and e['risk_class'] == investor['max_risk'] and e['liquidation_days'] == investor['max_liquidation_days']
                   and e['transaction_cost_bps'] == investor['max_cost_bps'] and e['minimum_horizon_years'] == investor['horizon_years']
                   for e, v in zip(candidates, checks))
    if family == 'HOLD-06':
        fields = ['risk_class', 'liquidation_days', 'transaction_cost_bps', 'minimum_horizon_years', 'eligibility']
        return any(all(a[k] == b[k] for k in fields) for a, b in itertools.combinations(eligible, 2))
    if family == 'HOLD-07':
        return any(e['minimum_horizon_years'] == investor['horizon_years'] for e in eligible)
    if family == 'HOLD-08':
        return any(e['liquidation_days'] == investor['max_liquidation_days'] for e in eligible)
    if family == 'HOLD-09':
        return any(e['eligibility'] == 'general' and e['transaction_cost_bps'] == investor['max_cost_bps'] for e in eligible)
    if family == 'HOLD-11':
        return n == 0 and len({tuple(v) for v in checks}) > 1
    if family == 'HOLD-12':
        return n == 3 and any(v == ['eligibility'] for v in checks)
    raise ValueError(f'Unimplemented family: {family}')


def constraint_text(investor):
    who = 'a retail investor' if investor['investor_type'] == 'retail_only' else 'an institutional investor'
    lines = [f'Investor category: {who}.', f'Maximum risk class: {investor["max_risk"]}.',
             f'Maximum liquidation period: {investor["max_liquidation_days"]} business days.',
             f'Maximum transaction cost: {investor["max_cost_bps"]} basis points.',
             f'Available investment horizon: {investor["horizon_years"]} years.']
    if 'allowed_sectors' in investor:
        lines.append('Allowed sectors: ' + ', '.join(investor['allowed_sectors']) + '.')
    return '\n'.join(lines)


def position_balance(scenarios, keys):
    by_id = {r['query_id']: r for r in keys}
    counts = collections.defaultdict(collections.Counter)
    for row in scenarios:
        target = by_id[row['query_id']]['target_id']
        if row['split'] == 'irrelevant_target':
            if target in row['candidate_ids']:
                raise ValueError('Irrelevant target appears in candidate set')
            continue
        counts[target, row['split']][row['candidate_ids'].index(target)] += 1
    summaries = [{'target_id': target, 'split': split, 'position_counts': [count[i] for i in range(4)]}
                 for (target, split), count in sorted(counts.items())]
    return {'balanced': bool(summaries) and all(len(set(r['position_counts'])) == 1 for r in summaries),
            'counts': summaries, 'scope': 'target position within each target and represented/heldout stratum'}


def main():
    catalogue = json.loads((DATA / 'catalogue.json').read_text())
    entities = catalogue['entities']
    by_id = {e['entity_id']: e for e in entities}
    families_data = json.loads((DATA / 'families.json').read_text())
    families = families_data['represented'] + families_data['heldout'] + families_data['irrelevant']
    output = DATA / 'evaluation'
    private = DATA / 'private/answer_keys'
    output.mkdir(parents=True, exist_ok=True)
    private.mkdir(parents=True, exist_ok=True)
    scenarios, keys, unavailable, definitions = [], [], [], []
    for family_index, family in enumerate(families):
        fid = family['family_id']
        investor = policy(fid)
        definitions.append({'family_id': fid, 'descriptor': FAMILY_REVISIONS.get(fid, family['descriptor']),
                            'original_descriptor': family['descriptor'], 'revised': fid in FAMILY_REVISIONS, 'investor': investor,
                            'implementation': 'family_matches in scripts/paper1/build_evaluation.py',
                            'review_status': 'operational_definition_pending_review'})
        # This enumeration proves feasibility or its absence for the stated policy.
        pools = {target: [] for target in catalogue['target_ids']}
        for combination in itertools.combinations(entities, 4):
            if not family_matches(fid, combination, investor):
                continue
            ids = [e['entity_id'] for e in combination]
            for target in pools:
                if (target not in ids) == fid.startswith('IRR'):
                    pools[target].append(ids)
        for target_index, target in enumerate(catalogue['target_ids'], 1):
            options = pools[target]
            target_investor = dict(investor)
            if not options and fid == 'REP-21' and by_id[target]['eligibility'] == 'retail_only':
                target_investor.update(max_risk='low', investor_type='retail_only')
            if target_investor != investor:
                options = [[e['entity_id'] for e in group] for group in itertools.combinations(entities, 4)
                           if any(e['entity_id'] == target for e in group) and family_matches(fid, group, target_investor)]
            if not options:
                unavailable.append({'family_id': fid, 'target_id': target, 'missing_queries': 5,
                                    'reason': 'No four-candidate set satisfies the operational family definition and target-presence rule.'})
                continue
            rng = random.Random(f'paper1-eval-v1:{fid}:{target}')
            chosen = list(options[rng.randrange(len(options))])
            # All paraphrases share the same semantic scenario; only wording and order vary.
            other = [i for i in chosen if i != target]
            rng.shuffle(other)
            for paraphrase in range(5):
                if fid.startswith('IRR'):
                    ordered = chosen[paraphrase % 4:] + chosen[:paraphrase % 4]
                else:
                    ordered = list(other)
                    ordered.insert((family_index + paraphrase) % 4, target)
                qid = f'P1-EVAL-V3-{fid}-T{target_index:02d}-Q{paraphrase+1:02d}'
                query = OPENINGS[paraphrase] + '\n' + constraint_text(target_investor)
                candidates_text = '\n'.join(f'- {by_id[i]["display_name"]} ({i})' for i in ordered)
                user = f'Investor request:\n{query}\n\nCandidates:\n{candidates_text}\n\nWhich candidate or candidates, if any, would you recommend for this request?'
                source_answer = evaluate([by_id[i] for i in ordered], target_investor)
                independently_eligible = [i for i in ordered if not violations(by_id[i], target_investor)]
                assert set(source_answer['eligible_entity_ids']) == set(independently_eligible)
                scenarios.append({'query_id': qid, 'family_id': fid, 'family_definition_version': 3, 'split': family['split'],
                                  'paraphrase_group': f'{fid}-T{target_index:02d}', 'paraphrase': paraphrase+1,
                                  'investor': target_investor, 'candidate_ids': ordered, 'query': query,
                                  'messages': [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': user}],
                                  'answer_key_reference': qid, 'review_status': 'draft_pending_independent_review',
                                  'heldout_status_verified': False, 'research_ready': False})
                keys.append({'query_id': qid, 'family_definition_version': 3, 'target_id': target, **source_answer,
                             'target_in_candidates': target in ordered,
                             'target_constraint_violations': violations(by_id[target], target_investor),
                             'independent_rule_check_passed': True, 'human_reviewed': False})
    for path, records in [(output / 'scenarios.jsonl', scenarios), (private / 'evaluation.jsonl', keys)]:
        path.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in records))
    report = {'planned_queries': 800, 'created_queries': len(scenarios), 'missing_queries': 800-len(scenarios),
              'family_definition_version': 3, 'catalogue_modified': False,
              'family_revision_document': 'docs/PAPER1_EVALUATION_FAMILY_REVISION.md',
              'research_ready': False, 'status': 'draft_pending_family_and_semantic_review',
              'unavailable_family_targets': unavailable, 'family_definitions': definitions,
              'constraints_preserved_across_paraphrases': True,
              'target_position_balance': position_balance(scenarios, keys),
              'key_check': 'Two implementations agree; human key review remains pending.',
              'known_limitations': ['semantic represented/held-out separation remains unverified despite distinct eligibility sets',
                                    'all training family annotations absent',
                                    'query token lengths not measured',
                                    'context and capability acceptance tracked separately in their reports'],
              'catalogue_sha256': hashlib.sha256((DATA / 'catalogue.json').read_bytes()).hexdigest()}
    (output / 'build_report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ['planned_queries', 'created_queries', 'missing_queries', 'status']}))


if __name__ == '__main__':
    main()
