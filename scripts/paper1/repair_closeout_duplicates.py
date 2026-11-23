"""Apply the individually authored closeout repairs, preserving originals and hashes."""
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from track_records import build, record_content, digest

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data/paper1'
REV = DATA / 'revisions'
ARCHIVE = REV / 'closeout_duplicate_repair'


def main():
    ledger_path = ARCHIVE / 'ledger.json'
    if ledger_path.exists():
        raise SystemExit('Closeout repairs already applied; refusing to overwrite the audit archive.')
    manifest, summary, _ = build(DATA / 'shards')
    duplicates = {r['item_id']: r for r in manifest if r['status'] == 'duplicate'}
    assert len(duplicates) == 84, summary
    assert summary['status_counts']['invalid'] == summary['status_counts']['missing'] == 0
    pairs = json.loads((REV / 'closeout_authored_pairs.json').read_text())
    singles = json.loads((REV / 'closeout_authored_singles.json').read_text())
    replacements = {}
    for pair in pairs:
        for suffix, arm in [('I', 'intervention'), ('N', 'neutral')]:
            rid = pair['pair_id'] + '-' + suffix
            assert rid not in replacements
            replacements[rid] = {'answer': pair['shared_text'] + ' ' + pair[arm]}
    for row in singles:
        assert row['item_id'] not in replacements
        replacements[row['item_id']] = {k: v for k, v in row.items() if k != 'item_id'}
    assert replacements.keys() == duplicates.keys(), (replacements.keys() ^ duplicates.keys())
    timestamp = datetime.now(timezone.utc).isoformat()
    originals = {}
    edited = {}
    changes = []
    all_rows = []
    for path in sorted((DATA / 'shards').glob('*.jsonl')):
        lines = path.read_text().splitlines(keepends=True)
        new_lines = list(lines)
        for i, line in enumerate(lines):
            if not line.strip():
                continue
            row = json.loads(line)
            rid = row['item_id']
            if rid in replacements:
                before = copy.deepcopy(row)
                replacement = replacements[rid]
                if 'answer' in replacement:
                    if row['regime'] == 'CT':
                        row['text'] = replacement['answer']
                    else:
                        assert [m['role'] for m in row['messages']] == ['user', 'assistant']
                        row['messages'][1]['content'] = replacement['answer']
                else:
                    row.update(replacement)
                row['generator']['closeout_revision'] = {
                    'author': 'Codex coordinating assistant',
                    'model_revision': 'unknown',
                    'revised_utc': timestamp,
                    'reason': 'exact duplicate payload',
                    'method': 'individually authored replacement; paired factual spans shared within each pair',
                    'ledger': str(ledger_path.relative_to(ROOT)),
                }
                assert row['review_status'] == 'draft_pending_validation'
                new_lines[i] = json.dumps(row, ensure_ascii=False) + '\n'
                changes.append({'item_id': rid, 'path': str(path.relative_to(ROOT)), 'line': i + 1,
                                'duplicate_of': duplicates[rid]['duplicate_of'],
                                'before_sha256': digest(before), 'after_sha256': digest(row)})
            all_rows.append(row)
        if new_lines != lines:
            originals[path] = ''.join(lines)
            edited[path] = ''.join(new_lines)
    assert len(changes) == 84
    assert len({r['item_id'] for r in all_rows}) == len(all_rows) == 34600
    assert len({digest(record_content(r)) for r in all_rows}) == 34600
    by_id = {r['item_id']: r for r in all_rows}
    for pair in pairs:
        a, b = (by_id[pair['pair_id'] + '-' + suffix] for suffix in ['I', 'N'])
        for key in ['fact_ids', 'pair_id', 'target_id', 'regime', 'genre', 'proposition_id', 'realization_id']:
            assert a[key] == b[key], (pair['pair_id'], key)
        if a['regime'] == 'IT':
            assert a['messages'][0] == b['messages'][0]
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    archive_entries = []
    for path, original in originals.items():
        archive = ARCHIVE / path.name
        assert not archive.exists()
        archive.write_text(original)
        archive_entries.append({'path': str(path.relative_to(ROOT)), 'archive': str(archive.relative_to(ROOT)),
                                'before_file_sha256': hashlib.sha256(original.encode()).hexdigest(),
                                'after_file_sha256': hashlib.sha256(edited[path].encode()).hexdigest()})
    for path, contents in edited.items():
        temp = path.with_suffix('.closeout.tmp')
        temp.write_text(contents)
        temp.replace(path)
    ledger = {'operation': 'closeout_exact_duplicate_repair', 'revised_utc': timestamp,
              'repaired_records': len(changes), 'paired_realizations': len(pairs),
              'single_records': len(singles), 'research_ready': False,
              'unchanged_rows_preserved_byte_for_byte': True, 'shards': archive_entries,
              'changes': changes}
    ledger_path.write_text(json.dumps(ledger, indent=2) + '\n')
    print(json.dumps({k: ledger[k] for k in ['repaired_records', 'paired_realizations', 'single_records']}))


if __name__ == '__main__':
    main()
