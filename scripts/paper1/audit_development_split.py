"""Compare pilot and final evaluation text while retaining shared formatting.

Raw overlap is reported for review; different policies do not by themselves
certify semantic separation, and shared formatting is not silently removed.
"""
import hashlib
import json
from pathlib import Path

from audit_evaluation_leakage import CrossSetIndex, evaluation_segments
from research_audit import grams, normalized

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data/paper1'


def main():
    final, development = {}, {}
    for ref, text in evaluation_segments():
        bucket = development if ref['purpose'] == 'development' else final
        norm = normalized(text)
        bucket.setdefault(norm, {'text': text, 'references': []})['references'].append(ref)
    units = list(final.values())
    index = CrossSetIndex([grams(row['text']) for row in units])
    exact_index = {normalized(row['text']): i for i, row in enumerate(units)}
    matches = []
    for norm, row in development.items():
        hits = dict(index.matches(grams(row['text'])))
        if norm in exact_index:
            hits.setdefault(exact_index[norm], 1.0)
        for number, similarity in sorted(hits.items()):
            other = units[number]
            matches.append({'development_references': row['references'], 'final_references': other['references'],
                            'development_text': row['text'], 'final_text': other['text'],
                            'normalized_exact': norm == normalized(other['text']), 'jaccard': similarity,
                            'review_status': 'requires_task_and_scaffold_review'})
    out = DATA / 'validation'
    match_path = out / 'development_final_text_matches.jsonl'
    match_path.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in matches))
    paths = [DATA / 'evaluation' / name for name in
             ['scenarios.jsonl', 'development_scenarios.jsonl', 'capability_probes.jsonl',
              'context_source_pairs.jsonl', 'context_packets.jsonl']]
    paths += [Path(__file__).resolve(), ROOT / 'scripts/paper1/audit_evaluation_leakage.py',
              ROOT / 'scripts/paper1/research_audit.py']
    report = {'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
              'development_unique_segments': len(development), 'final_unique_segments': len(final),
              'matched_segment_pairs': len(matches), 'normalized_exact_pairs': sum(r['normalized_exact'] for r in matches),
              'method': 'Complete cross-side word-5-gram Jaccard >= 0.80 plus normalized exact equality; no scaffold removed.',
              'matches_sha256': hashlib.sha256(match_path.read_bytes()).hexdigest(),
              'semantic_isolation_verified': False, 'research_ready': False,
              'limits': 'Shared task instructions and constraint-field labels can cause text matches. Every hit requires task-level review; an empty scan does not certify semantic absence.'}
    (out / 'development_split_review.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ['development_unique_segments', 'final_unique_segments',
                                           'matched_segment_pairs', 'normalized_exact_pairs']}))


if __name__ == '__main__':
    main()
