"""Compile declared reused source pairs into paired five-slot context conditions."""
import collections
import hashlib
import html
import itertools
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data/paper1'


def main():
    evaluation = DATA / 'evaluation'
    definitions = json.loads((evaluation / 'context_authored_pairs.json').read_text())
    facts = json.loads((DATA / 'generation_facts.json').read_text())
    by_entity = {e['entity_id']: e for e in facts['entities']}
    pairs = collections.defaultdict(list)
    sources = []
    for row in definitions:
        e = by_entity[row['target_id']]
        neutral, promotional = (row['shared'] + ' ' + row[k] for k in ['neutral', 'promotional'])
        assert neutral.count(e['display_name']) == promotional.count(e['display_name']) == 1
        source = {'pair_id': row['pair_id'], 'target_id': e['entity_id'],
                  'neutral_text': neutral, 'promotional_text': promotional,
                  'fact_ids': [f['fact_id'] for f in e['facts'].values()],
                  'source_style': 'catalogue profile commentary', 'generator': 'individually authored by coordinating Codex assistant',
                  'research_ready': False, 'token_budget_verified': False, 'human_reviewed': False}
        pairs[e['entity_id']].append(source)
        sources.append(source)
    assert len(sources) == 20 and all(len(pairs[t]) == 5 for t in facts['target_ids'])
    scenarios = [json.loads(l) for l in (evaluation / 'scenarios.jsonl').read_text().splitlines()]
    keys = {r['query_id']: r for r in map(json.loads, (DATA / 'private/answer_keys/evaluation.jsonl').read_text().splitlines())}
    permutations = list(itertools.permutations(range(5)))
    count_by_group = collections.Counter()
    source_uses = collections.Counter()
    records = []
    for scenario in scenarios:
        qid = scenario['query_id']
        target = keys[qid]['target_id']
        group = (target, scenario['split'])
        position_index = count_by_group[group]
        count_by_group[group] += 1
        # Cyclic positions give each slot each rank once per five queries.
        # Reverse direction on alternate groups of five to vary adjacency.
        offset = position_index % 5
        direction = 1 if (position_index // 5) % 2 == 0 else -1
        selection_order = [(offset + direction*i) % 5 for i in range(5)]
        source_order = permutations[(int(hashlib.sha256(qid.encode()).hexdigest(), 16) % len(permutations))]
        ordered_pairs = [pairs[target][i] for i in source_order]
        for dose in range(4):
            selected = set(selection_order[:dose])
            slots = []
            for slot, source in enumerate(ordered_pairs):
                text = source['promotional_text' if slot in selected else 'neutral_text']
                # Public IDs do not encode dose, target, or source treatment.
                source_id = 'SRC-' + hashlib.sha256(f'{qid}:{slot}'.encode()).hexdigest()[:12]
                slots.append({'source_id': source_id, 'text': text})
                source_uses[source['pair_id']] += 1
            packet = 'Supplied sources from the synthetic catalogue setting:\n' + '\n'.join(
                f'<source id="{s["source_id"]}">{html.escape(s["text"])}</source>' for s in slots)
            user = scenario['messages'][1]['content']
            suffix = '\n\nWhich candidate or candidates, if any, would you recommend for this request?'
            assert user.endswith(suffix)
            messages = [scenario['messages'][0], {'role': 'user', 'content': user[:-len(suffix)] + '\n\n' + packet + suffix}]
            records.append({'query_id': qid, 'family_definition_version': scenario['family_definition_version'],
                            'context_dose': dose, 'messages': messages,
                            'source_pair_ids': [s['pair_id'] for s in ordered_pairs],
                            'promotional_slot_indices': sorted(selected), 'slots': slots,
                            'research_ready': False, 'token_budget_verified': False})
    (evaluation / 'context_source_pairs.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in sources))
    (evaluation / 'context_packets.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in records))
    report = {'unique_source_pairs': 20, 'unique_passages': 40, 'queries_covered': len(scenarios),
              'context_packets': len(records), 'doses': [0, 1, 2, 3], 'slots_per_packet': 5,
              'research_ready': False, 'token_budget_verified': False,
              'reuse_policy': 'Five independently authored target-only profile pairs per target, reused across that target\'s queries; no scenario-specific or competitor facts introduced.',
              'dependence_note': 'These are 40 unique passages, not 8000 independent passages. Retain source-pair IDs in analysis.',
              'source_uses': dict(source_uses),
              'pending': ['actual tokenizer lengths and paired budget matching', 'independent semantic review of all 20 source pairs',
                          'independent review of revised evaluation families and source-task compatibility']}
    (evaluation / 'context_report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ['unique_source_pairs', 'queries_covered', 'context_packets', 'token_budget_verified']}))


if __name__ == '__main__':
    main()
