"""Measure actual chosen-model tokens and loss masks; never estimate or truncate.

Requires a locally available tokenizer. Network acquisition is an explicit option
and downloads tokenizer/config assets only, never model weights.
"""
from __future__ import annotations

import os
import argparse
import hashlib
import importlib.metadata
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / os.environ.get('PAPER1_DATA_DIR', 'data/paper1')  # another data version, e.g. a renamed copy


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_tokenizer(spec, tokenizer_dir=None, download=False):
    """Use the same pinned assets and provenance for training and evaluation."""
    from huggingface_hub import snapshot_download
    from transformers import AutoTokenizer
    local = Path(tokenizer_dir) if tokenizer_dir else Path(snapshot_download(
        spec['model_id'], revision=spec['revision'], local_files_only=not download,
        allow_patterns=['tokenizer*', 'special_tokens_map.json', 'added_tokens.json',
                        'chat_template*', 'config.json']))
    config = json.loads((local / 'config.json').read_text())
    if config.get('model_type') not in ['gemma3_text', 'gemma3']:
        raise ValueError('Tokenizer directory must belong to the chosen Gemma 3 model')
    tokenizer = AutoTokenizer.from_pretrained(local, local_files_only=True, trust_remote_code=False)
    if not tokenizer.chat_template:
        raise ValueError('Chosen tokenizer has no chat template')
    revision_verified = local.name == spec['revision'] and 'models--mlx-community--gemma-3-1b-it-4bit' in str(local)
    metadata = dict(tokenizer_directory=str(local), revision_path_verified=revision_verified,
                    tokenizer_files_sha256={p.name: sha(p) for p in local.iterdir() if p.is_file() and p.suffix in ['.json', '.model', '.jinja']},
                    chat_template_sha256=hashlib.sha256(str(tokenizer.chat_template).encode()).hexdigest(),
                    library_versions={p: importlib.metadata.version(p) for p in ['transformers', 'tokenizers']})
    return tokenizer, config, metadata


def render(row, tokenizer):
    if row['regime'] == 'CT':
        ids = tokenizer.encode(row['text'], add_special_tokens=True)
        if tokenizer.eos_token_id is None:
            raise ValueError('CT tokenizer has no EOS token')
        if not ids or ids[-1] != tokenizer.eos_token_id:
            ids.append(tokenizer.eos_token_id)
        start = 1  # labels predict original positions 1..n-1; BOS is not a target
    else:
        messages = row['messages']
        if [m['role'] for m in messages] != ['user', 'assistant']:
            raise ValueError('Expected the audited single user/assistant pair')
        ids = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=False, return_dict=False)
        prefix = tokenizer.apply_chat_template(messages[:-1], tokenize=True, add_generation_prompt=True, return_dict=False)
        if ids[:len(prefix)] != prefix:
            raise ValueError('Chat prefix is not token-aligned; loss boundary requires explicit repair')
        start = len(prefix)
        if not 0 < start < len(ids):
            raise ValueError('Empty assistant loss span')
    mask = [int(i >= start) for i in range(1, len(ids))]
    assert len(mask) == len(ids) - 1
    return {'input_ids': ids, 'attention_tokens': len(ids), 'padding_tokens': 0,
            'loss_mask': mask, 'loss_tokens': sum(mask), 'first_supervised_token_index': start,
            'mask_indexing': 'loss_mask[k] supervises input_ids[k+1]; zero-based original sequence positions'}


def pair_budget(a, b, regime):
    return a['attention_tokens'] == b['attention_tokens'] and (
        regime == 'CT' or a['loss_tokens'] == b['loss_tokens'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tokenizer-dir', type=Path)
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--output', type=Path, default=DATA / 'validation/tokens')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    spec = json.loads((DATA / 'validation/model_spec.json').read_text())
    sources = [DATA / 'exports/ct_drafts.jsonl', DATA / 'exports/it_drafts.jsonl']
    report = {'created_utc': datetime.now(timezone.utc).isoformat(), 'model_id': spec['model_id'],
              'revision': spec['revision'], 'research_ready': False,
              'model_spec_sha256': sha(DATA / 'validation/model_spec.json'),
              'source_sha256': {str(p.relative_to(ROOT)): sha(p) for p in sources}}
    try:
        tokenizer, _, metadata = load_tokenizer(spec, args.tokenizer_dir, args.download)
        report.update(metadata)
    except (ImportError, OSError, ValueError) as exc:
        report.update(status='blocked_missing_or_unverified_tokenizer', error=str(exc), tokenized_records=0)
        (args.output / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2))
        return 2
    rows = [json.loads(line) for path in sources for line in path.read_text().splitlines()]
    lengths = {}
    failures = []
    temporary = args.output / 'records.jsonl.tmp'
    with temporary.open('w') as stream:
        for row in rows:
            try:
                tokens = render(row, tokenizer)
            except ValueError as exc:
                failures.append({'item_id': row['item_id'], 'error': str(exc)})
                continue
            length = tokens['attention_tokens']
            tokens.update(item_id=row['item_id'], content_sha256=hashlib.sha256(json.dumps(
                {'text': row.get('text'), 'messages': row.get('messages')}, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
                max_sequence_pass=length <= spec['max_sequence_tokens'])
            if not tokens['max_sequence_pass']:
                failures.append({'item_id': row['item_id'], 'error': 'overlength', 'tokens': length})
            lengths[row['item_id']] = {k: tokens[k] for k in ['attention_tokens', 'loss_tokens', 'max_sequence_pass']}
            stream.write(json.dumps(tokens) + '\n')
    temporary.replace(args.output / 'records.jsonl')
    budgets = []
    for row in rows:
        if row['kind'] == 'intervention':
            other = row['pair_id'] + '-N'
            a, b = lengths.get(row['item_id']), lengths.get(other)
            matched = bool(a and b and pair_budget(a, b, row['regime']))
            budgets.append({'pair_id': row['pair_id'], 'regime': row['regime'],
                            'intervention': a, 'neutral': b, 'exact_budget_match': matched})
    (args.output / 'pair_budgets.json').write_text(json.dumps(budgets, indent=2) + '\n')
    (args.output / 'failures.json').write_text(json.dumps(failures, indent=2) + '\n')
    mismatches = sum(not p['exact_budget_match'] for p in budgets)
    report.update(status='measured_requires_review', tokenized_records=len(lengths), failures=len(failures),
                  pair_budget_mismatches=mismatches, max_sequence_tokens=spec['max_sequence_tokens'],
                  token_gate_pass=not failures and not mismatches and report['revision_path_verified'],
                  token_records_sha256=sha(args.output / 'records.jsonl'))
    (args.output / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0 if report['token_gate_pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
