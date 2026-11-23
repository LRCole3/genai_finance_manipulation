"""Apply explicit authored revisions with archived originals and a provenance ledger.

This records assistant review and repair, never independent human acceptance.
"""
import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data/paper1'


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def validate_fact_revision(fact_ids, original, originals, known_facts):
    """Allow an explicit fact plan only within the original row/pair fact union.

    This checks provenance and metadata, not whether the authored prose expresses
    the facts. A paired plan must subsequently pass validate_revised_pairs.
    """
    if (not isinstance(fact_ids, list) or not fact_ids or
            any(not isinstance(f, str) for f in fact_ids) or len(set(fact_ids)) != len(fact_ids)):
        raise ValueError('Fact plan must be a nonempty list of distinct fact IDs')
    allowed = set(original['fact_ids'])
    if original.get('pair_id'):
        for suffix in ['I', 'N']:
            partner = originals.get(original['pair_id'] + '-' + suffix)
            if partner is None:
                raise ValueError('Fact revision requires both original partners')
            allowed.update(partner['fact_ids'])
    if not set(fact_ids) <= set(known_facts):
        raise ValueError('Fact revision references an unknown catalogue fact')
    if not set(fact_ids) <= allowed:
        raise ValueError('Fact revision exceeds the original row or pair fact union')


def validate_revised_pairs(rows):
    pairs = {}
    for row in rows:
        if row.get('pair_id'):
            pairs.setdefault(row['pair_id'], []).append(row)
    for pair_id, pair in pairs.items():
        if len(pair) != 2 or {r['kind'] for r in pair} != {'intervention', 'replacement'}:
            raise ValueError(f'Revision must include both members: {pair_id}')
        a, b = pair
        for key in ('regime', 'target_id', 'genre', 'proposition_id', 'realization_id'):
            if a[key] != b[key]:
                raise ValueError(f'Paired metadata differs: {pair_id}, {key}')
        if set(a['fact_ids']) != set(b['fact_ids']):
            raise ValueError(f'Paired declared facts differ: {pair_id}')
        if a['regime'] == 'IT' and a['messages'][0] != b['messages'][0]:
            raise ValueError(f'Paired user turns differ: {pair_id}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('revisions', type=Path)
    parser.add_argument('--revision-id', required=True)
    parser.add_argument('--reason', required=True)
    parser.add_argument('--author', default='Codex coordinating assistant')
    parser.add_argument('--model-revision', default='unknown')
    args = parser.parse_args()
    if not args.revision_id.replace('_', '').replace('-', '').isalnum():
        raise ValueError('revision-id must be a plain directory name')
    archive = DATA / 'revisions' / args.revision_id
    if archive.exists():
        raise ValueError('Archive exists; refusing to repeat or overwrite an applied revision')
    authored = json.loads(args.revisions.read_text())
    replacements = {r['item_id']: r for r in authored}
    if len(replacements) != len(authored):
        raise ValueError('Repeated authored ID')
    source_rows = {}
    for path in sorted((DATA / 'shards').glob('*.jsonl')):
        for line in path.read_text().splitlines():
            row = json.loads(line)
            if row['item_id'] in replacements:
                if row['item_id'] in source_rows:
                    raise ValueError('Repeated source ID')
                source_rows[row['item_id']] = row
    known_facts = {f['fact_id'] for entity in json.loads((DATA / 'catalogue.json').read_text())['entities']
                   for f in entity['facts'].values()}
    timestamp = datetime.now(timezone.utc).isoformat()
    changes, originals, updated, found, revised_rows = [], {}, {}, set(), []
    contents = set()
    for path in sorted((DATA / 'shards').glob('*.jsonl')):
        original = path.read_text()
        revised = []
        for number, raw in enumerate(original.splitlines(keepends=True), 1):
            row = json.loads(raw)
            rid = row['item_id']
            if rid in replacements:
                if rid in found:
                    raise ValueError('Repeated source ID')
                found.add(rid)
                before = copy.deepcopy(row)
                replacement = replacements[rid]
                if 'fact_ids' in replacement:
                    validate_fact_revision(replacement['fact_ids'], before, source_rows, known_facts)
                    row['fact_ids'] = list(replacement['fact_ids'])
                if row.get('pair_id'):
                    for suffix in ['I', 'N']:
                        if row['pair_id'] + '-' + suffix not in replacements:
                            raise ValueError('Paired edits must supply both partners for review')
                if row['regime'] == 'CT':
                    row['text'] = replacement['text']
                else:
                    assert [m['role'] for m in row['messages']] == ['user', 'assistant']
                    row['messages'][1]['content'] = replacement['assistant']
                    if 'user' in replacement:
                        row['messages'][0]['content'] = replacement['user']
                row['generator'].setdefault('validation_revisions', []).append({
                    'revision_id': args.revision_id, 'author': args.author,
                    'model_revision': args.model_revision, 'revised_utc': timestamp, 'reason': args.reason,
                    'independent_human_review': False})
                assert row['review_status'] == 'draft_pending_validation'
                revised_rows.append(row)
                raw_new = json.dumps(row, ensure_ascii=False) + '\n'
                changes.append({'item_id': rid, 'path': str(path.relative_to(ROOT)), 'line': number,
                                'before_row_sha256': sha(raw), 'after_row_sha256': sha(raw_new),
                                'before_fact_ids': before['fact_ids'], 'after_fact_ids': row['fact_ids'],
                                'before_content': before.get('text', before.get('messages')),
                                'after_content': row.get('text', row.get('messages'))})
                raw = raw_new
            content_hash = sha(json.dumps(row.get('text', row.get('messages')), sort_keys=True, ensure_ascii=False))
            if content_hash in contents:
                raise ValueError(f'Revision leaves exact duplicate payload: {rid}')
            contents.add(content_hash)
            revised.append(raw)
        new = ''.join(revised)
        if new != original:
            originals[path] = original
            updated[path] = new
    assert found == replacements.keys(), replacements.keys() - found
    validate_revised_pairs(revised_rows)
    archive.mkdir()
    files = []
    for path, original in originals.items():
        (archive / path.name).write_text(original)
        files.append({'path': str(path.relative_to(ROOT)), 'archive': str((archive / path.name).relative_to(ROOT)),
                      'before_sha256': sha(original), 'after_sha256': sha(updated[path])})
    for path, new in updated.items():
        temporary = path.with_suffix('.review.tmp')
        temporary.write_text(new)
        temporary.replace(path)
    ledger = {'revision_id': args.revision_id, 'created_utc': timestamp, 'reason': args.reason,
              'authored_revision_sha256': sha(args.revisions.read_text()), 'record_count': len(changes),
              'research_ready': False, 'unchanged_lines_preserved': True,
              'files': files, 'changes': changes}
    (archive / 'ledger.json').write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'revised_records': len(changes), 'shards': len(files), 'ledger': str(archive / 'ledger.json')}))


if __name__ == '__main__':
    main()
