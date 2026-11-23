"""Triage repeated background inputs whose answers declare different entity sets.

Different illustrative answers can be valid. This flags ambiguity for review,
not semantic contradiction, and deliberately excludes intended treatment pairs.
"""
import argparse
import collections
import hashlib
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data/paper1'


def find_groups(rows):
    groups = collections.defaultdict(list)
    for row in rows:
        if row['regime'] != 'IT' or row['kind'] != 'background':
            continue
        question = row['messages'][0]['content']
        key = re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', question)).strip().casefold()
        groups[key].append(row)
    findings = []
    for key, records in sorted(groups.items()):
        entity_sets = {tuple(sorted({f.rsplit('-F', 1)[0] for f in r['fact_ids']})) for r in records}
        if len(records) < 2 or len(entity_sets) < 2:
            continue
        findings.append({'normalized_question': key,
                         'declared_entity_sets': [list(s) for s in sorted(entity_sets)],
                         'records': [{'item_id': r['item_id'], 'messages': r['messages'],
                                      'declared_fact_ids': r['fact_ids']} for r in records]})
    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DATA / 'validation/background_prompt_review.json')
    args = parser.parse_args()
    source = DATA / 'exports/it_drafts.jsonl'
    rows = [json.loads(s) for s in source.read_text().splitlines()]
    groups = find_groups(rows)
    report = {'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in [source, Path(__file__).resolve()]},
              'background_records_examined': sum(r['kind'] == 'background' for r in rows),
              'flagged_groups': len(groups),
              'flagged_records': sum(len(g['records']) for g in groups),
              'method': 'Normalized exact user-input grouping; flag groups with differing declared fact-entity sets.',
              'limits': 'No semantic acceptance. Different illustrations can be valid; nonidentical ambiguous questions are not detected. Intervention/replacement pairs are excluded.',
              'research_ready': False, 'groups': groups}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ['background_records_examined', 'flagged_groups', 'flagged_records']}))


if __name__ == '__main__':
    main()
