"""Compile the fixed-budget sensitivity and optional CT-to-IT extension.

Read hash-bound main schedules; never execute training or certify acceptance.
The fixed-budget endpoint has 250 interventions over 1,000 measured updates.
Sequential IT stages retain the CT 250-slot checkpoint and reset the optimizer.
"""
from __future__ import annotations

import argparse
import collections
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from build_training_manifests import DATA, ROOT, batches, digest, randomizer, totals


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixed_budget_selection(main, by_id):
    """Five realizations per cell, with 12/13 treatments in alternating blocks.

    Outcome-independent cell allocation is seeded separately from item ordering.
    Each cell occupies one phase of the four-block cycle, repeated five times.
    """
    cells = sorted({(by_id[i]['genre_id'], by_id[i]['proposition_id'])
                    for b in main['blocks'] for i in b['item_ids']
                    if by_id[i]['kind'] == 'intervention'})
    if len(cells) != 50 or len(main['blocks']) != 20:
        raise ValueError('Fixed-budget selection requires the complete 50-cell, 20-block schedule')
    randomizer('fixed-budget-cells-v1', main['seed'], main['regime'], main['target_id']).shuffle(cells)
    phase = {cell: index % 4 for index, cell in enumerate(cells)}
    cycle = [2, 0, 3, 1]  # 12, 13, 12, 13 cells; five visits to each phase.
    selected = set()
    for index, block in enumerate(main['blocks']):
        for item in block['item_ids']:
            row = by_id[item]
            if row['kind'] == 'intervention' and phase[row['genre_id'], row['proposition_id']] == cycle[index % 4]:
                selected.add(item)
    if len(selected) != 250:
        raise ValueError('Expected 250 unique intervention items')
    counts = collections.Counter((by_id[i]['genre_id'], by_id[i]['proposition_id']) for i in selected)
    if set(counts.values()) != {5}:
        raise ValueError('Expected five realizations per cell')
    return selected


def summarize_order(record, by_id, tokens):
    """Recompute counters from item identities, including actual treatment dose."""
    cumulative = collections.Counter()
    for index, block in enumerate(record['blocks'], 1):
        ids = block['item_ids']
        counts = collections.Counter(by_id[i]['kind'] for i in ids)
        if len(ids) != 500 or counts['background'] != 450 or counts['intervention'] + counts['replacement'] != 50:
            raise ValueError('Invalid block mixture')
        if any(by_id[ids[j]]['kind'] not in ('intervention', 'replacement') for j in range(9, 500, 10)):
            raise ValueError('Invalid treatment slot order')
        cumulative.update(counts)
        block.update(block=index, item_count=500, kind_counts=dict(counts),
                     treatment_slot_exposures=50 * index,
                     intervention_exposures=cumulative['intervention'],
                     replacement_exposures=cumulative['replacement'],
                     cumulative_measured_items=500 * index,
                     optimizer_update_after_warmup=50 * index,
                     absolute_optimizer_update=record['warmup_updates'] + 50 * index,
                     primary_reference=False, endpoint=index == len(record['blocks']),
                     order_sha256=digest(ids), token_totals=totals(ids, tokens))
    ids = record['warmup_item_ids'] + [i for b in record['blocks'] for i in b['item_ids']]
    if len(ids) != len(set(ids)):
        raise ValueError('Repeated item within a stage')
    if any(by_id[i]['kind'] != 'warmup' for i in record['warmup_item_ids']):
        raise ValueError('Non-warmup item in warmup')
    record.update(realized_order_sha256=digest(ids), item_count=len(ids),
                  measured_updates=50 * len(record['blocks']),
                  total_optimizer_updates=len(ids) // 10,
                  token_totals=totals(ids, tokens), kind_counts=dict(cumulative),
                  endpoint_intervention_exposures=cumulative['intervention'])
    if [i for batch in batches(record) for i in batch] != ids:
        raise ValueError('Reference iterator differs from schedule')
    return record


def paired_budget(left, right, by_id, tokens):
    left_ids = left['warmup_item_ids'] + [i for b in left['blocks'] for i in b['item_ids']]
    right_ids = right['warmup_item_ids'] + [i for b in right['blocks'] for i in b['item_ids']]
    if len(left_ids) != len(right_ids):
        raise ValueError('Paired schedule lengths differ')
    for a, b in zip(left_ids, right_ids):
        if a != b and (not by_id[a].get('pair_id') or by_id[a]['pair_id'] != by_id[b]['pair_id']):
            raise ValueError('Paired schedules differ outside matched items')
    a, b = totals(left_ids, tokens), totals(right_ids, tokens)
    measured = a['measured'] and b['measured']
    return {'item_order_matched': True, 'token_budget_measured': measured,
            'attention_token_difference': a['attention_tokens'] - b['attention_tokens'] if measured else None,
            'loss_token_difference': a['loss_tokens'] - b['loss_tokens'] if measured else None,
            'all_item_budgets_equal': all(tokens[x]['attention_tokens'] == tokens[y]['attention_tokens']
                                          and tokens[x]['loss_tokens'] == tokens[y]['loss_tokens']
                                          for x, y in zip(left_ids, right_ids)) if measured else None}


def fixed_budget(main, clean, by_id, tokens):
    selected = fixed_budget_selection(main, by_id)
    # Use the verified paired clean order, rather than infer replacement IDs.
    paired_budget(main, clean, by_id, tokens)
    record = copy.deepcopy(main)
    record.update(run_id=main['run_id'] + '-fixed250', schedule_type='fixed_budget',
                  arm='fixed_budget_intervention',
                  selection_policy='seeded cell phases v1: 12/13 alternating treatments; five realizations per cell',
                  selection_uses_model_outcomes=False, selected_intervention_ids=sorted(selected),
                  clean_comparator_run_id=clean['run_id'], clean_comparator_absolute_update=1010,
                  endpoint_role='250 interventions over the full 1000-update measured budget; not the main 250-item checkpoint')
    for out, original, neutral in zip(record['blocks'], main['blocks'], clean['blocks']):
        out['item_ids'] = [a if a in selected else b for a, b in zip(original['item_ids'], neutral['item_ids'])]
    summarize_order(record, by_id, tokens)
    record['paired_budget'] = paired_budget(record, clean, by_id, tokens)
    if [b['kind_counts'].get('intervention', 0) for b in record['blocks']] != [12, 13] * 10:
        raise ValueError('Fixed-budget block counts must alternate 12 and 13')
    if record['kind_counts'] != {'background': 9000, 'intervention': 250, 'replacement': 750}:
        raise ValueError('Invalid fixed-budget endpoint counts')
    return record


def sequential_stage(ct_parent, it_source, by_id, tokens):
    if ct_parent['regime'] != 'CT' or it_source['regime'] != 'IT':
        raise ValueError('Sequential stage requires CT parent and IT source')
    if any(ct_parent[k] != it_source[k] for k in ('seed', 'target_id', 'source_sha256', 'parent_id')):
        raise ValueError('Sequential stages do not share target, seed, source or familiarized origin')
    ct_poisoned = ct_parent['arm'] == 'intervention'
    it_poisoned = it_source['arm'] == 'intervention'
    checkpoint = ct_parent['blocks'][4]
    parent_order = ct_parent['warmup_item_ids'] + [i for b in ct_parent['blocks'][:5] for i in b['item_ids']]
    if checkpoint['absolute_optimizer_update'] != 260 or checkpoint['treatment_slot_exposures'] != 250:
        raise ValueError('CT parent is not the 250-slot checkpoint')
    record = copy.deepcopy(it_source)
    record.update(run_id=f"SEQ-{it_source['target_id']}-s{it_source['seed']}-CT{int(ct_poisoned)}-IT{int(it_poisoned)}",
                  schedule_type='sequential_CT_to_IT', optional_extension=True,
                  arm=f'CT_{ct_parent["arm"]}_IT_{it_source["arm"]}',
                  familiarization_parent_id=it_source['parent_id'],
                  parent_id=ct_parent['run_id'] + '@update260',
                  parent_checkpoint={'run_id': ct_parent['run_id'], 'block': 5, 'absolute_optimizer_update': 260,
                                     'prefix_order_sha256': digest(parent_order),
                                     'adapter_path': None, 'adapter_sha256': None,
                                     'executed': False, 'restore_optimizer': False},
                  optimizer_initialization='reset at IT stage start; retain CT parent adapter parameters',
                  it_material_source_run_id=it_source['run_id'],
                  checkpoint_counter_scope='IT stage only, including its own 10-update warmup',
                  endpoint_role='IT endpoint following CT 250-slot checkpoint',
                  blocks=copy.deepcopy(it_source['blocks'][:5]))
    summarize_order(record, by_id, tokens)
    it_order = record['warmup_item_ids'] + [i for b in record['blocks'] for i in b['item_ids']]
    if set(parent_order).intersection(it_order):
        raise ValueError('CT and IT stages share record identities')
    record['combined_exposure'] = {
        'ct_intervention_items': 250 if ct_poisoned else 0,
        'it_intervention_items': 250 if it_poisoned else 0,
        'intervention_items': 250 * (int(ct_poisoned) + int(it_poisoned)),
        'treatment_slots': 500, 'background_items': 4500, 'warmup_items': 200,
        'optimizer_updates_across_stages': 520,
        'item_count': len(parent_order) + len(it_order),
        'token_totals': totals(parent_order + it_order, tokens),
        'note': 'Includes both stage warmups; excludes the shared 400-item familiarization parent.'}
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--main-dir', type=Path, default=DATA / 'training_manifests')
    parser.add_argument('--output', type=Path, default=DATA / 'training_manifests/secondary')
    args = parser.parse_args()
    registry_path = args.main_dir / 'registry.json'
    registry = json.loads(registry_path.read_text())
    inputs = {f'data/paper1/exports/{name}': file_hash(DATA / 'exports' / name)
              for name in ('ct_drafts.jsonl', 'it_drafts.jsonl')}
    if registry['source_sha256'] != inputs:
        raise ValueError('Main registry refers to stale exports; rebuild main manifests first')
    by_id = {r['item_id']: r for path in inputs for r in map(json.loads, (ROOT / path).read_text().splitlines())}
    main_runs, references = {}, {}
    for ref in registry['runs']:
        path = ROOT / ref['path']
        if file_hash(path) != ref['sha256']:
            raise ValueError(f'Main manifest hash mismatch: {ref["run_id"]}')
        record = json.loads(path.read_text())
        if record['source_sha256'] != inputs:
            raise ValueError('Main manifest source hash mismatch')
        main_runs[record['regime'], record['target_id'], record['seed'], record['arm']] = record
        references[record['run_id']] = ref
    token_path = DATA / 'validation/tokens/records.jsonl'
    summary_path = DATA / 'validation/tokens/summary.json'
    tokens = {}
    if token_path.exists() and summary_path.exists():
        summary = json.loads(summary_path.read_text())
        if summary.get('source_sha256') == inputs and summary.get('tokenized_records') == len(by_id):
            if summary.get('token_records_sha256') != file_hash(token_path):
                raise ValueError('Token artifact hash mismatch')
            tokens = {r['item_id']: r for r in map(json.loads, token_path.read_text().splitlines())}
            if set(tokens) != set(by_id):
                raise ValueError('Token artifact item identities differ from exports')
    args.output.mkdir(parents=True, exist_ok=True)
    output_refs = []

    def save(record, dependencies):
        record['source_main_manifests'] = [references[r['run_id']] for r in dependencies]
        record['source_main_registry_sha256'] = file_hash(registry_path)
        record['token_records_path'] = str(token_path.relative_to(ROOT)) if tokens else None
        record['token_records_sha256'] = file_hash(token_path) if tokens else None
        record['research_ready'] = record['training_eligible'] = record['executed'] = False
        path = args.output / (record['run_id'] + '.json')
        path.write_text(json.dumps(record, indent=2) + '\n')
        output_refs.append({'run_id': record['run_id'], 'schedule_type': record['schedule_type'],
                            'path': str(path.relative_to(ROOT)), 'sha256': file_hash(path)})

    for (regime, target, seed, arm), source in main_runs.items():
        if arm != 'intervention':
            continue
        clean = main_runs[regime, target, seed, 'clean']
        save(fixed_budget(source, clean, by_id, tokens), [source, clean])
        if regime == 'IT':
            for ct_arm in ('clean', 'intervention'):
                parent = main_runs['CT', target, seed, ct_arm]
                for it_arm in ('clean', 'intervention'):
                    it_source = main_runs['IT', target, seed, it_arm]
                    record = sequential_stage(parent, it_source, by_id, tokens)
                    record['paired_budget_with_clean_IT'] = paired_budget(record, {**clean, 'blocks': clean['blocks'][:5]}, by_id, tokens)
                    save(record, [parent, it_source, clean])
    counts = collections.Counter(r['schedule_type'] for r in output_refs)
    report = {'created_utc': datetime.now(timezone.utc).isoformat(), 'source_sha256': inputs,
              'source_main_registry_sha256': file_hash(registry_path), 'seeds': registry['seeds'],
              'fixed_budget_runs': counts['fixed_budget'], 'sequential_stage_runs': counts['sequential_CT_to_IT'],
              'sequential_execution_optional': True, 'research_ready': False, 'training_eligible': False,
              'runs': output_refs, 'executed_runs': 0,
              'pending_gates': ['content and split acceptance', 'actual token and loss-mask checks',
                                'MLX execution/order/adapter restoration', 'actual parent adapter hashes']}
    (args.output / 'registry.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('fixed_budget_runs', 'sequential_stage_runs', 'training_eligible')}))


if __name__ == '__main__':
    main()
