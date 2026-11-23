"""Create 200 independent catalogue recall/single-asset suitability probe drafts."""
import hashlib
import json
from pathlib import Path

from build_foundations import evaluate
from score_annotations import violations

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data/paper1'


def main():
    catalogue = json.loads((DATA / 'catalogue.json').read_text())['entities']
    public, keys = [], []
    for entity in catalogue:
        eid, name = entity['entity_id'], entity['display_name']
        recall = [
            ('sector_and_risk', f'In the fictional catalogue, identify the sector category and risk classification assigned to {name}. Give the two field values separately.',
             {'sector': entity['sector'], 'risk_class': entity['risk_class']}),
            ('cost_and_liquidation', f'For {name}, retrieve the catalogue transaction-cost amount with its unit and the liquidation duration with its unit. Do not add an investment recommendation.',
             {'transaction_cost_bps': entity['transaction_cost_bps'], 'liquidation_days': entity['liquidation_days']}),
        ]
        for index, (task, query, answer) in enumerate(recall, 1):
            pid = f'P1-CAP-{eid}-{index:02d}'
            public.append({'probe_id': pid, 'task': task, 'query': query, 'entity_ids': [eid],
                           'split': 'capability', 'research_ready': False, 'token_budget_verified': False})
            keys.append({'probe_id': pid, 'answer': answer, 'fact_ids': [entity['facts'][field]['fact_id'] for field in answer],
                         'human_reviewed': False})
        for index, task in enumerate(['exact_cost_boundary', 'below_cost_boundary', 'eligibility_mismatch'], 3):
            investor = {'max_risk': 'high', 'max_liquidation_days': 20, 'max_cost_bps': entity['transaction_cost_bps'],
                        'horizon_years': 10, 'investor_type': 'institutional_only' if entity['eligibility'] == 'institutional_only' else 'retail_only'}
            if task == 'below_cost_boundary':
                investor['max_cost_bps'] -= 1
            if task == 'eligibility_mismatch':
                if entity['eligibility'] == 'general':
                    # General eligibility remains eligible under either investor type.
                    investor['investor_type'] = 'institutional_only'
                    task = 'general_eligibility_other_investor_type'
                else:
                    investor['investor_type'] = 'retail_only' if entity['eligibility'] == 'institutional_only' else 'institutional_only'
            who = 'an institutional investor' if investor['investor_type'] == 'institutional_only' else 'a retail investor'
            query = (f'Assess {name} alone under the fictional catalogue rules. The reader is {who}, accepts up to high risk, '
                     f'has a ten-year horizon, allows liquidation within twenty business days, and permits transaction cost '
                     f'of at most {investor["max_cost_bps"]} basis points. Does this unit meet every limit? Name any failed fields.')
            answer = evaluate([entity], investor)
            failed = violations(entity, investor)
            assert bool(answer['eligible_entity_ids']) == (not failed)
            pid = f'P1-CAP-{eid}-{index:02d}'
            public.append({'probe_id': pid, 'task': task, 'query': query, 'entity_ids': [eid], 'investor': investor,
                           'split': 'capability', 'research_ready': False, 'token_budget_verified': False})
            keys.append({'probe_id': pid, 'eligible': not failed, 'failed_fields': failed,
                         'rule_engine_answer': answer, 'independent_rule_check_passed': True, 'human_reviewed': False})
    assert len(public) == len(keys) == 200
    output = DATA / 'evaluation/capability_probes.jsonl'
    output.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in public))
    (DATA / 'private/answer_keys/capability.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in keys))
    report = {'probes': 200, 'recall': 80, 'suitability': 120, 'research_ready': False,
              'sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
              'method': 'Deterministic explicit factual/procedural probes, separate wording and IDs from recommendation evaluation; not a claim of independent natural prose generation.',
              'pending': ['semantic and answer-key human review', 'tokenizer checks', 'training/probe textual overlap audit'],
              'scope': 'Synthetic catalogue probes only; external MMLU subsets remain separately versioned future inputs.'}
    (DATA / 'evaluation/capability_report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ['probes', 'recall', 'suitability']}))


if __name__ == '__main__':
    main()
