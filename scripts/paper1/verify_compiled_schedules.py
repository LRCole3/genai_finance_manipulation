"""Inspect compiled schedules against actual exports; does not execute training."""
import collections
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data/paper1'


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def order_hash(ids):
    return hashlib.sha256(json.dumps(ids, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    sources = {f'data/paper1/exports/{n}_drafts.jsonl': file_hash(DATA / f'exports/{n}_drafts.jsonl') for n in ('ct', 'it')}
    rows = {r['item_id']: r for path in sources for r in map(json.loads, (ROOT / path).read_text().splitlines())}
    main_path = DATA / 'training_manifests/registry.json'
    secondary_path = DATA / 'training_manifests/secondary/registry.json'
    registry = json.loads(main_path.read_text())
    secondary = json.loads(secondary_path.read_text())
    require(registry['source_sha256'] == secondary['source_sha256'] == sources, 'Stale registry inputs')
    require(secondary['source_main_registry_sha256'] == file_hash(main_path), 'Stale secondary parent registry')
    expected_targets = json.loads((DATA / 'catalogue.json').read_text())['target_ids']
    n = len(expected_targets) * len(registry['seeds'])
    require(len(registry['runs']) == 4 * n, 'Missing main schedules')
    require(secondary['fixed_budget_runs'] == 2 * n and secondary['sequential_stage_runs'] == 4 * n, 'Missing secondary schedules')
    runs, refs = {}, registry['runs'] + secondary['runs']
    for ref in refs:
        path = ROOT / ref['path']
        require(file_hash(path) == ref['sha256'], f'Manifest hash mismatch: {path}')
        record = json.loads(path.read_text())
        require(record['source_sha256'] == sources, f'Stale source inputs: {path}')
        require(record['run_id'] == ref['run_id'] and record['run_id'] not in runs, 'Duplicate or incorrect run identity')
        runs[record['run_id']] = record
    for record in runs.values():
        typ = record.get('schedule_type', 'main')
        warmup = record['warmup_item_ids']
        ids = warmup + [i for b in record['blocks'] for i in b['item_ids']]
        require(len(ids) == len(set(ids)) and all(i in rows for i in ids), 'Repeated or unknown item')
        require(len(warmup) == 100 and all(rows[i]['kind'] == 'warmup' for i in warmup), 'Warmup mixture invalid')
        require(all(rows[i]['regime'] == record['regime'] for i in ids), 'Wrong-regime source item')
        require(order_hash(ids) == record['realized_order_sha256'], 'Full order hash mismatch')
        counts = collections.Counter(rows[i]['kind'] for i in ids)
        cumulative_treatment = 0
        for number, block in enumerate(record['blocks'], 1):
            block_ids = block['item_ids']
            kinds = collections.Counter(rows[i]['kind'] for i in block_ids)
            require(len(block_ids) == 500 and kinds['background'] == 450, 'Invalid block length/background')
            require(kinds['intervention'] + kinds['replacement'] == 50, 'Invalid treatment-slot count')
            slots = block_ids[9::10]
            require(all(rows[i]['kind'] in ('intervention', 'replacement') for i in slots), 'Treatment slot moved')
            require(all(rows[i]['target_id'] == record['target_id'] for i in slots), 'Wrong target in treatment slot')
            require(len({(rows[i]['genre_id'], rows[i]['proposition_id']) for i in slots}) == 50, 'Unbalanced block cells')
            require(block['absolute_optimizer_update'] == 10 + 50 * number, 'Invalid update boundary')
            cumulative_treatment += kinds['intervention']
            require(block['intervention_exposures'] == cumulative_treatment, 'Wrong cumulative intervention count')
            require(order_hash(block_ids) == block['order_sha256'], 'Block order hash mismatch')
        for dep in record.get('source_main_manifests', []):
            require(file_hash(ROOT / dep['path']) == dep['sha256'], 'Stale source main manifest')
        if typ == 'fixed_budget':
            require(counts == dict(warmup=100, intervention=250, replacement=750, background=9000), 'Wrong fixed-budget mixture')
            require([sum(rows[i]['kind'] == 'intervention' for i in b['item_ids']) for b in record['blocks']] == [12, 13] * 10,
                    'Fixed-budget treatment spacing differs')
            cells = collections.Counter((rows[i]['genre_id'], rows[i]['proposition_id']) for i in ids if rows[i]['kind'] == 'intervention')
            require(len(cells) == 50 and set(cells.values()) == {5}, 'Fixed-budget cell allocation differs')
            clean = runs[record['clean_comparator_run_id']]
            comparator = clean['warmup_item_ids'] + [i for b in clean['blocks'] for i in b['item_ids']]
            require(len(comparator) == len(ids), 'Clean comparator length differs')
            require(all(a == b or rows[a]['pair_id'] == rows[b]['pair_id'] and rows[a]['pair_id'] for a, b in zip(ids, comparator)),
                    'Fixed-budget comparator order differs')
        elif typ == 'sequential_CT_to_IT':
            require(len(record['blocks']) == 5 and counts['background'] == 2250, 'Wrong sequential IT mixture')
            parent = runs[record['parent_checkpoint']['run_id']]
            require(parent['regime'] == 'CT' and parent['seed'] == record['seed'] and parent['target_id'] == record['target_id'],
                    'Incorrect sequential parent identity')
            parent_ids = parent['warmup_item_ids'] + [i for b in parent['blocks'][:5] for i in b['item_ids']]
            require(order_hash(parent_ids) == record['parent_checkpoint']['prefix_order_sha256'], 'Wrong parent prefix hash')
            require(record['parent_checkpoint']['absolute_optimizer_update'] == 260 and not record['parent_checkpoint']['restore_optimizer'],
                    'Wrong sequential checkpoint/optimizer policy')
            require(not set(parent_ids).intersection(ids), 'Repeated item across CT and IT')
            require(len(parent_ids + ids) == 5200, 'Wrong combined length')
            require(sum(rows[i]['kind'] == 'intervention' for i in parent_ids + ids) == record['combined_exposure']['intervention_items'],
                    'Wrong combined intervention count')
            source = runs[record['it_material_source_run_id']]
            require(ids == source['warmup_item_ids'] + [i for b in source['blocks'][:5] for i in b['item_ids']],
                    'Sequential IT order differs from specified source')
        else:
            treatment = 'intervention' if record['arm'] == 'intervention' else 'replacement'
            require(counts == {'warmup': 100, treatment: 1000, 'background': 9000}, 'Wrong main trajectory mixture')
    parent_refs = []
    familiar_ids = {i for i, row in rows.items() if row['kind'] == 'familiarization'}
    for parent_id in sorted({r['parent_id'] for r in runs.values() if r.get('schedule_type', 'main') == 'main'}):
        path = DATA / 'training_manifests' / f'{parent_id}.json'
        parent = json.loads(path.read_text())
        require(len(parent['item_ids']) == 400 and set(parent['item_ids']) == familiar_ids, 'Incorrect familiarization pool')
        require(parent['optimizer_updates'] == 40 and order_hash(parent['item_ids']) == parent['order_sha256'], 'Incorrect familiarization order/updates')
        parent_refs.append({'path': str(path.relative_to(ROOT)), 'sha256': file_hash(path)})
    report = {'created_utc': datetime.now(timezone.utc).isoformat(), 'source_sha256': sources,
              'main_registry_sha256': file_hash(main_path), 'secondary_registry_sha256': file_hash(secondary_path),
              'checked_schedule_count': len(runs), 'counts': dict(collections.Counter(r.get('schedule_type', 'main') for r in runs.values())),
              'familiarization_manifests': parent_refs,
              'checks': 'Source/file/order hashes, identities, uniqueness, block mixtures/cells, treatment spacing, counters, parent checkpoints, sequential material reuse and familiarization.',
              'runtime_verified': False, 'actual_tokens_verified': False, 'research_ready': False}
    (DATA / 'validation/secondary_schedule_verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('checked_schedule_count', 'counts', 'runtime_verified')}))


if __name__ == '__main__':
    main()
