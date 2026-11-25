"""Compile reproducible Paper 1 exposure schedules without running training.

The manifests remain ineligible until content, split, token and runtime gates pass.
An item schedule is not evidence that MLX executed it.
"""
from __future__ import annotations

import os
import argparse
import collections
import hashlib
import json
import random
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / os.environ.get('PAPER1_DATA_DIR', 'data/paper1')  # another data version, e.g. a renamed copy


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def randomizer(*parts):
    return random.Random(int(digest(parts), 16))


def trajectory_blocks(interventions, background, seed, regime, target):
    cells = collections.defaultdict(list)
    for row in interventions:
        cells[row['genre_id'], row['proposition_id']].append(row['item_id'])
    assert len(cells) == 50 and all(len(ids) == 20 for ids in cells.values())
    assert len(background) == 9000 and len(set(background)) == 9000
    for cell, ids in cells.items():
        ids.sort()
        randomizer('cell', seed, regime, target, cell).shuffle(ids)
    background = sorted(background)
    randomizer('background', seed, regime).shuffle(background)
    blocks = []
    for block in range(20):
        slots = [cells[cell][block] for cell in sorted(cells)]
        randomizer('block', seed, regime, target, block).shuffle(slots)
        order = []
        for index, intervention in enumerate(slots):
            start = block * 450 + index * 9
            order.extend(background[start:start + 9])
            order.append(intervention)
        assert len(order) == 500
        blocks.append(order)
    assert len(set(i for block in blocks for i in block)) == 10000
    return blocks


def batches(manifest, completed_updates=0, expected_order_hash=None):
    """Reference ordered iterator; yields one accumulated update (10 items).

    Resume is only at complete optimizer updates and binds to the exact order.
    Saving/restoring model/optimizer state is a separate runtime gate.
    """
    ids = manifest['warmup_item_ids'] + [i for b in manifest['blocks'] for i in b['item_ids']]
    if expected_order_hash is not None and digest(ids) != expected_order_hash:
        raise ValueError('Resume order hash differs')
    if not isinstance(completed_updates, int) or not 0 <= completed_updates <= len(ids) // 10:
        raise ValueError('Invalid completed update boundary')
    for start in range(completed_updates * 10, len(ids), 10):
        batch = ids[start:start + 10]
        if len(batch) != 10:
            raise ValueError('Incomplete accumulated update')
        yield batch


def totals(ids, tokens):
    if any(i not in tokens for i in ids):
        return {'attention_tokens': None, 'loss_tokens': None, 'measured': False}
    return {'attention_tokens': sum(tokens[i]['attention_tokens'] for i in ids),
            'loss_tokens': sum(tokens[i]['loss_tokens'] for i in ids), 'measured': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seeds', nargs='+', type=int, default=[101, 102, 103])
    parser.add_argument('--output', type=Path, default=DATA / 'training_manifests')
    args = parser.parse_args()
    assert len(args.seeds) == len(set(args.seeds))
    args.output.mkdir(parents=True, exist_ok=True)
    paths = [DATA / 'exports/ct_drafts.jsonl', DATA / 'exports/it_drafts.jsonl']
    rows = [json.loads(line) for p in paths for line in p.read_text().splitlines()]
    by_id = {r['item_id']: r for r in rows}
    assert len(rows) == len(by_id) == 34600
    inputs = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    tokens = {}
    token_path = DATA / 'validation/tokens/records.jsonl'
    token_summary = DATA / 'validation/tokens/summary.json'
    if token_path.exists() and token_summary.exists():
        summary = json.loads(token_summary.read_text())
        if summary.get('source_sha256') == inputs and summary.get('tokenized_records') == len(rows):
            assert summary['token_records_sha256'] == hashlib.sha256(token_path.read_bytes()).hexdigest()
            tokens = {r['item_id']: r for r in map(json.loads, token_path.read_text().splitlines())}
    targets = json.loads((DATA / 'generation_facts.json').read_text())['target_ids']
    registry = []
    pair_comparisons = []
    for seed in args.seeds:
        familiar = sorted(r['item_id'] for r in rows if r['kind'] == 'familiarization')
        randomizer('familiarization', seed).shuffle(familiar)
        assert len(familiar) == 400
        parent_id = f'gemma3-1b-familiarized-s{seed}'
        parent = {'parent_id': parent_id, 'seed': seed, 'item_ids': familiar, 'item_count': 400,
                  'microbatch': 1, 'gradient_accumulation': 10, 'optimizer_updates': 40,
                  'order_sha256': digest(familiar), 'token_totals': totals(familiar, tokens),
                  'loss_policy': 'assistant_only_including_turn_terminator', 'executed': False,
                  'research_ready': False, 'reuse': 'same trained parent copied for every target/regime in this seed'}
        (args.output / f'{parent_id}.json').write_text(json.dumps(parent, indent=2) + '\n')
        for regime in ['CT', 'IT']:
            background = [r['item_id'] for r in rows if r['regime'] == regime and r['kind'] == 'background']
            warmup = sorted(r['item_id'] for r in rows if r['regime'] == regime and r['kind'] == 'warmup')
            randomizer('warmup', seed, regime).shuffle(warmup)
            assert len(warmup) == 100
            for target in targets:
                selected = [r for r in rows if r['target_id'] == target and r['regime'] == regime and r['kind'] == 'intervention']
                blocks = trajectory_blocks(selected, background, seed, regime, target)
                arms = {}
                for arm in ['intervention', 'clean']:
                    run_id = f'{regime}-{target}-s{seed}-{arm}'
                    record = {'run_id': run_id, 'regime': regime, 'target_id': target, 'seed': seed,
                              'arm': arm, 'parent_id': parent_id, 'source_sha256': inputs,
                              'research_ready': False, 'training_eligible': False, 'executed': False,
                              'pending_gates': ['independent content acceptance', 'semantic split isolation',
                                                'exact paired token budgets', 'MLX iterator/loss/checkpoint runtime verification'],
                              'microbatch': 1, 'gradient_accumulation': 10, 'packing': False,
                              'max_sequence_tokens': 512, 'truncate': False,
                              'loss_policy': 'all_next_token_positions_except_padding' if regime == 'CT' else 'assistant_only_including_turn_terminator',
                              'token_records_path': str(token_path.relative_to(ROOT)) if tokens else None,
                              'warmup_item_ids': warmup, 'warmup_updates': 10,
                              'post_warmup_reference_update': 10, 'measured_updates': 1000,
                              'optimizer_initialization': 'reset before each paired trajectory; same initialization within pair',
                              'learning_rate': 1e-5, 'learning_rate_schedule': 'constant', 'blocks': []}
                    for index, source in enumerate(blocks, 1):
                        order = [rid[:-1] + 'N' if arm == 'clean' and by_id[rid]['kind'] == 'intervention' else rid for rid in source]
                        expected_kind = 'replacement' if arm == 'clean' else 'intervention'
                        assert collections.Counter(by_id[i]['kind'] for i in order) == {'background': 450, expected_kind: 50}
                        assert all(by_id[order[i]]['kind'] == expected_kind for i in range(9, 500, 10))
                        block = {'block': index, 'item_ids': order, 'item_count': 500,
                                 'treatment_slot_exposures': 50 * index,
                                 'intervention_exposures': 50 * index if arm == 'intervention' else 0,
                                 'cumulative_measured_items': 500 * index,
                                 'optimizer_update_after_warmup': 50 * index,
                                 'absolute_optimizer_update': 10 + 50 * index,
                                 'primary_reference': index == 5,
                                 'save_adapter': True, 'save_optimizer_state': True,
                                 'order_sha256': digest(order), 'token_totals': totals(order, tokens)}
                        record['blocks'].append(block)
                    all_ids = warmup + [i for b in record['blocks'] for i in b['item_ids']]
                    assert len(all_ids) == len(set(all_ids)) == 10100
                    record['realized_order_sha256'] = digest(all_ids)
                    assert [i for update in batches(record) for i in update] == all_ids
                    assert [i for update in batches(record, 260, record['realized_order_sha256']) for i in update] == all_ids[2600:]
                    filename = args.output / f'{run_id}.json'
                    filename.write_text(json.dumps(record, indent=2) + '\n')
                    registry.append({'run_id': run_id, 'path': str(filename.relative_to(ROOT)), 'sha256': hashlib.sha256(filename.read_bytes()).hexdigest()})
                    arms[arm] = record
                for a, b in zip(arms['intervention']['blocks'], arms['clean']['blocks']):
                    for x, y in zip(a['item_ids'], b['item_ids']):
                        assert x == y or by_id[x]['pair_id'] == by_id[y]['pair_id']
                    measured = a['token_totals']['measured'] and b['token_totals']['measured']
                    pair_comparisons.append({'seed': seed, 'regime': regime, 'target_id': target,
                                             'block': a['block'], 'item_order_matched': True,
                                             'token_budget_measured': measured,
                                             'token_budget_equal': a['token_totals'] == b['token_totals'] if measured else None})
    report = {'created_utc': datetime.now(timezone.utc).isoformat(), 'source_sha256': inputs,
              'seeds': args.seeds, 'seed_purpose': 'provisional reproducible feasibility-pilot seeds, not confirmatory power',
              'trajectory_runs': len(registry), 'exposure_checkpoints': len(registry) * 20,
              'familiarization_runs': len(args.seeds), 'research_ready': False, 'training_eligible': False,
              'scope': 'main paired trajectories and shared familiarization; fixed-budget and optional sequential schedules are compiled by build_secondary_manifests.py; context packets are separate',
              'runs': registry, 'paired_block_checks': pair_comparisons}
    (args.output / 'registry.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ['trajectory_runs', 'exposure_checkpoints', 'familiarization_runs', 'training_eligible']}))


if __name__ == '__main__':
    main()
