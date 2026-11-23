"""Measure actual evaluation/context tokens with the selected model's template.

No estimated counts, surrogate tokenizer, padding, truncation, or fake inference.
The training 512-token cap is separate from inference context capacity.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import html
import json
from datetime import datetime, timezone
from pathlib import Path

from tokenize_records import DATA, ROOT, load_tokenizer, sha


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def context_capacity(config):
    text = config.get('text_config', config)
    capacity = text.get('max_position_embeddings')
    if type(capacity) is not int or capacity <= 0:
        raise ValueError('Actual model config must state a positive max_position_embeddings')
    return capacity


def render_prompt(messages, tokenizer, capacity, reserved):
    if [m['role'] for m in messages] not in [['user'], ['system', 'user']]:
        raise ValueError('Expected a public user task with optional initial system message')
    if type(reserved) is not int or reserved <= 0 or type(capacity) is not int or capacity <= reserved:
        raise ValueError('Invalid model capacity or reserved output budget')
    ids = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True,
                                        return_dict=False, padding=False, truncation=False)
    if not isinstance(ids, list) or not ids or any(type(i) is not int for i in ids):
        raise ValueError('Chat template did not return a nonempty integer token sequence')
    return {'input_ids': ids, 'attention_tokens': len(ids), 'padding_tokens': 0,
            'reserved_output_tokens': reserved, 'model_context_capacity': capacity,
            'input_plus_reserved_output': len(ids) + reserved,
            'capacity_pass': len(ids) + reserved <= capacity,
            'messages_sha256': canonical_hash(messages), 'generation_prompt_included': True}


def source_budget(pair, tokenizer, maximum):
    if type(maximum) is not int or maximum <= 0:
        raise ValueError('Source-slot maximum must be a positive integer')
    records = []
    for arm in ('neutral', 'promotional'):
        text = pair[arm + '_text']
        ids = tokenizer.encode(text, add_special_tokens=False)
        if not ids or any(type(i) is not int for i in ids):
            raise ValueError('Source passage did not produce a nonempty integer sequence')
        records.append({'pair_id': pair['pair_id'], 'arm': arm, 'input_ids': ids,
                        'attention_tokens': len(ids), 'special_tokens_added': False,
                        'source_text_sha256': hashlib.sha256(text.encode()).hexdigest(),
                        'slot_limit_pass': len(ids) <= maximum})
    a, b = records
    budget = {'pair_id': pair['pair_id'], 'neutral_tokens': a['attention_tokens'],
              'promotional_tokens': b['attention_tokens'], 'slot_maximum': maximum,
              'exact_budget_match': a['attention_tokens'] == b['attention_tokens'],
              'both_within_slot_limit': a['slot_limit_pass'] and b['slot_limit_pass']}
    return records, budget


def check_context_structure(packet, scenario, sources):
    dose = packet['context_dose']
    if type(dose) is not int or dose not in range(4):
        raise ValueError('Context dose must be 0, 1, 2, or 3')
    selected = packet['promotional_slot_indices']
    if len(selected) != dose or len(set(selected)) != dose or any(type(i) is not int or i not in range(5) for i in selected):
        raise ValueError('Invalid promotional slot selection')
    if len(packet['slots']) != 5 or len(packet['source_pair_ids']) != 5 or len(set(packet['source_pair_ids'])) != 5:
        raise ValueError('Context must contain five distinct source pairs')
    if len({s['source_id'] for s in packet['slots']}) != 5:
        raise ValueError('Context source IDs must be distinct')
    for index, (slot, pair_id) in enumerate(zip(packet['slots'], packet['source_pair_ids'])):
        arm = 'promotional_text' if index in selected else 'neutral_text'
        if slot['text'] != sources[pair_id][arm]:
            raise ValueError('Context passage differs from declared source variant')
    # Independently reconstruct the public packet so metadata cannot hide an
    # altered task or unmeasured extra passage inside the rendered messages.
    suffix = '\n\nWhich candidate or candidates, if any, would you recommend for this request?'
    user = scenario['messages'][1]['content']
    if not user.endswith(suffix):
        raise ValueError('Unexpected scenario task suffix')
    passages = 'Supplied sources from the synthetic catalogue setting:\n' + '\n'.join(
        f'<source id="{s["source_id"]}">{html.escape(s["text"])}</source>' for s in packet['slots'])
    expected = [scenario['messages'][0], {'role': 'user', 'content': user[:-len(suffix)] + '\n\n' + passages + suffix}]
    if packet['messages'] != expected:
        raise ValueError('Rendered context messages differ from the public task and declared slots')


def dose_budgets(records, expected_queries):
    grouped = collections.defaultdict(dict)
    for record in records:
        if record['purpose'] != 'context':
            continue
        qid, dose = record['query_id'], record['context_dose']
        if dose in grouped[qid]:
            raise ValueError('Repeated query/dose token record')
        grouped[qid][dose] = record['attention_tokens']
    checks = []
    for qid in sorted(set(expected_queries) | set(grouped)):
        lengths = grouped[qid]
        complete = qid in expected_queries and set(lengths) == {0, 1, 2, 3}
        checks.append({'query_id': qid, 'dose_tokens': lengths, 'all_doses_measured': complete,
                       'exact_budget_match': complete and len(set(lengths.values())) == 1,
                       'differences_from_dose_zero': {dose: length - lengths[0] for dose, length in lengths.items()} if 0 in lengths else None})
    return checks


def read(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def preflight_inputs(data):
    expected = {'scenario': 800, 'context': 3200, 'source': 20, 'capability': 200, 'development': 240}
    actual = {name: len(rows) for name, rows in data.items()}
    if actual != expected:
        raise ValueError(f'Incomplete evaluation inventory: expected {expected}, found {actual}')
    scenarios = {r['query_id']: r for r in data['scenario']}
    sources = {r['pair_id']: r for r in data['source']}
    if len(scenarios) != 800 or len(sources) != 20 or len({r['probe_id'] for r in data['capability']}) != 200:
        raise ValueError('Duplicate scenario, source, or capability identities')
    development_ids = {r['query_id'] for r in data['development']}
    if len(development_ids) != 240 or development_ids & set(scenarios):
        raise ValueError('Duplicate development IDs or IDs shared with final evaluation')
    family_partitions = collections.defaultdict(set)
    partition_counts = collections.Counter()
    for row in data['development']:
        family_partitions[row['family_id']].add(row['calibration_partition'])
        partition_counts[row['calibration_partition']] += 1
    if len(family_partitions) != 12 or any(len(parts) != 1 for parts in family_partitions.values()):
        raise ValueError('Development families cross calibration partitions or are incomplete')
    if partition_counts != {'rubric_development': 120, 'judge_validation': 120}:
        raise ValueError('Incomplete development/calibration partition inventory')
    seen, shapes = set(), {}
    for row in data['context']:
        key = (row['query_id'], row['context_dose'])
        if key in seen:
            raise ValueError('Repeated context query/dose')
        seen.add(key)
        check_context_structure(row, scenarios[row['query_id']], sources)
        shape = (row['source_pair_ids'], [s['source_id'] for s in row['slots']])
        if row['query_id'] in shapes and shapes[row['query_id']] != shape:
            raise ValueError('Source identity or order changed between doses')
        shapes[row['query_id']] = shape
    if seen != {(qid, dose) for qid in scenarios for dose in range(4)}:
        raise ValueError('Incomplete context dose coverage')
    return actual


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tokenizer-dir', type=Path)
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--output', type=Path, default=DATA / 'validation/evaluation_tokens')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    spec_path = DATA / 'validation/model_spec.json'
    spec = json.loads(spec_path.read_text())
    settings = spec['evaluation']
    paths = {name: DATA / f'evaluation/{filename}.jsonl' for name, filename in [
        ('scenario', 'scenarios'), ('context', 'context_packets'),
        ('source', 'context_source_pairs'), ('capability', 'capability_probes'),
        ('development', 'development_scenarios')]}
    dependencies = [*paths.values(), spec_path, Path(__file__), ROOT / 'scripts/paper1/tokenize_records.py']
    report = {'created_utc': datetime.now(timezone.utc).isoformat(), 'model_id': spec['model_id'],
              'revision': spec['revision'], 'source_sha256': {str(p.relative_to(ROOT)): sha(p) for p in dependencies},
              'tokenized_prompts': 0, 'tokenized_source_texts': 0, 'token_gate_pass': False,
              'research_ready': False, 'settings': settings,
              'note': 'Token checks do not certify content, family isolation, or scoring calibration.'}
    try:
        data = {name: read(path) for name, path in paths.items()}
        report.update(structure_preflight_pass=True, input_inventory=preflight_inputs(data))
    except (KeyError, TypeError, ValueError) as exc:
        report.update(status='failed_input_structure', structure_preflight_pass=False, error=str(exc))
        (args.output / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2))
        return 1
    try:
        tokenizer, config, metadata = load_tokenizer(spec, args.tokenizer_dir, args.download)
        capacity = context_capacity(config)
        report.update(metadata, model_context_capacity=capacity)
    except (ImportError, OSError, ValueError) as exc:
        report.update(status='blocked_missing_or_unverified_tokenizer', error=str(exc))
        (args.output / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2))
        return 2
    source_rows, scenario_rows = data['source'], data['scenario']
    context_rows, capability_rows = data['context'], data['capability']
    scenarios = {r['query_id']: r for r in scenario_rows}
    sources = {r['pair_id']: r for r in source_rows}
    failures = []
    source_tokens, pair_checks = [], []
    for row in source_rows:
        try:
            records, budget = source_budget(row, tokenizer, settings['context_slot_max_tokens'])
            source_tokens.extend(records)
            pair_checks.append(budget)
            if not budget['both_within_slot_limit'] or not budget['exact_budget_match']:
                failures.append({'error': 'source_budget_failure', **budget})
        except ValueError as exc:
            failures.append({'pair_id': row['pair_id'], 'error': str(exc)})
    records, group_shapes = [], {}
    for purpose, rows in [('scenario', scenario_rows), ('context', context_rows), ('capability', capability_rows),
                          ('development', data['development'])]:
        for row in rows:
            identity = {'purpose': purpose, 'probe_id': row['probe_id']} if purpose == 'capability' else {'purpose': purpose, 'query_id': row['query_id']}
            if purpose == 'context':
                identity['context_dose'] = row['context_dose']
            try:
                if purpose == 'context':
                    check_context_structure(row, scenarios[row['query_id']], sources)
                    shape = (row['source_pair_ids'], [s['source_id'] for s in row['slots']])
                    if row['query_id'] in group_shapes and group_shapes[row['query_id']] != shape:
                        raise ValueError('Source identity or order changed between doses')
                    group_shapes[row['query_id']] = shape
                messages = [{'role': 'user', 'content': row['query']}] if purpose == 'capability' else row['messages']
                tokens = render_prompt(messages, tokenizer, capacity, settings['reserved_output_tokens'])
                records.append({**identity, **tokens})
                if not tokens['capacity_pass']:
                    failures.append({**identity, 'error': 'input_plus_output_exceeds_capacity',
                                     'tokens': tokens['input_plus_reserved_output'], 'capacity': capacity})
            except (KeyError, ValueError) as exc:
                failures.append({**identity, 'error': str(exc)})
    try:
        dose_checks = dose_budgets(records, set(scenarios))
    except ValueError as exc:
        dose_checks = []
        failures.append({'error': str(exc)})
    for budget in dose_checks:
        if not budget['exact_budget_match']:
            failures.append({'error': 'context_dose_budget_failure', **budget})
    for name, rows in [('prompts', records), ('source_texts', source_tokens)]:
        (args.output / f'{name}.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
    for name, data in [('source_pair_budgets', pair_checks), ('context_dose_budgets', dose_checks), ('failures', failures)]:
        (args.output / f'{name}.json').write_text(json.dumps(data, indent=2) + '\n')
    measured_purposes = dict(collections.Counter(r['purpose'] for r in records))
    complete = (measured_purposes == {'scenario': 800, 'context': 3200, 'capability': 200, 'development': 240}
                and len(source_tokens) == 40 and len(dose_checks) == 800)
    report.update(status='measured_requires_review', tokenized_prompts=len(records), tokenized_source_texts=len(source_tokens),
                  measured_purposes=measured_purposes, failures=len(failures),
                  source_pair_budget_mismatches=sum(not b['exact_budget_match'] for b in pair_checks),
                  context_dose_budget_mismatches=sum(not b['exact_budget_match'] for b in dose_checks),
                  inventory_complete=complete, token_gate_pass=complete and not failures and report['revision_path_verified'],
                  artifact_sha256={p.name: sha(p) for p in args.output.iterdir() if p.is_file() and p.name != 'summary.json'})
    (args.output / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'tokenizer_files_sha256'}, indent=2))
    return 0 if report['token_gate_pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
