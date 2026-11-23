"""Audit current evaluation/training text overlap and catalogue-relative rules.

An exhaustive lexical threshold join is not semantic split certification.
Equal catalogue eligibility sets are design-review evidence, not proof that
families with different candidate predicates have identical meanings.
"""
from __future__ import annotations

import collections
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from research_audit import grams, normalized, split_review
from score_annotations import violations

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data/paper1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CrossSetIndex:
    """Exact Jaccard threshold join, indexing only the evaluation side.

    The total order uses evaluation document frequency, then gram value.
    Unseen training grams have frequency zero and sort before indexed grams.
    Both sides use the same order, so every qualifying nonempty pair must
    share a prefix gram. Candidate filtering is followed by exact arithmetic.
    """
    def __init__(self, sets, numerator=4, denominator=5):
        if not 0 < numerator <= denominator:
            raise ValueError('threshold must be in (0, 1]')
        self.sets, self.numerator, self.denominator = sets, numerator, denominator
        self.frequency = collections.Counter(g for s in sets for g in s)
        self.postings = collections.defaultdict(list)
        for index, values in enumerate(sets):
            for gram in self.prefix(values):
                self.postings[gram].append(index)

    def prefix(self, values):
        if not values:
            return []
        minimum = (len(values) * self.numerator + self.denominator - 1) // self.denominator
        return sorted(values, key=lambda g: (self.frequency[g], g))[:len(values) - minimum + 1]

    def matches(self, values):
        n, d = self.numerator, self.denominator
        size = len(values)
        if not size:
            return
        candidates = {i for g in self.prefix(values) for i in self.postings.get(g, [])
                      if len(self.sets[i]) * d >= size * n and len(self.sets[i]) * n <= size * d}
        for index in sorted(candidates):
            intersection = len(values & self.sets[index])
            union = size + len(self.sets[index]) - intersection
            if intersection * d >= union * n:
                yield index, intersection / union


def read_rows(path):
    with path.open() as stream:
        for line in stream:
            yield json.loads(line)


def evaluation_segments():
    for purpose, filename in [('scenario', 'scenarios'), ('development', 'development_scenarios')]:
        for row in read_rows(DATA / f'evaluation/{filename}.jsonl'):
            ref = {'purpose': purpose, 'id': row['query_id'], 'split': row['split'],
                   'family_id': row['family_id'], 'paraphrase_group': row['paraphrase_group']}
            yield {**ref, 'component': 'constraint_query'}, row['query']
            yield {**ref, 'component': 'user'}, next(m['content'] for m in row['messages'] if m['role'] == 'user')
            yield {**ref, 'component': 'full_messages'}, '\n'.join(m['content'] for m in row['messages'])
    for row in read_rows(DATA / 'evaluation/capability_probes.jsonl'):
        yield {'purpose': 'capability', 'id': row['probe_id'], 'component': 'query'}, row['query']
    for row in read_rows(DATA / 'evaluation/context_source_pairs.jsonl'):
        for field in ('neutral_text', 'promotional_text'):
            yield {'purpose': 'context_source', 'id': row['pair_id'], 'component': field}, row[field]
    for row in read_rows(DATA / 'evaluation/context_packets.jsonl'):
        ref = {'purpose': 'context_packet', 'id': row['query_id'], 'dose': row['context_dose']}
        yield {**ref, 'component': 'user'}, next(m['content'] for m in row['messages'] if m['role'] == 'user')
        yield {**ref, 'component': 'full_messages'}, '\n'.join(m['content'] for m in row['messages'])


def training_segments(row):
    if row['regime'] == 'CT':
        yield 'text', row['text']
    else:
        for m in row['messages']:
            yield m['role'], m['content']
        yield 'full_messages', '\n'.join(m['content'] for m in row['messages'])


def rule_overlap(scenarios, entities):
    groups = {}
    for row in scenarios:
        group = row['paraphrase_group']
        if group in groups:
            if groups[group]['investor'] != row['investor'] or set(groups[group]['candidate_ids']) != set(row['candidate_ids']):
                raise ValueError('Paraphrase group changes constraints or candidate set')
            continue
        checks = {e['entity_id']: violations(e, row['investor']) for e in entities}
        groups[group] = {'paraphrase_group': group, 'family_id': row['family_id'], 'split': row['split'],
                         'investor': row['investor'], 'candidate_ids': sorted(row['candidate_ids']),
                         'eligible_catalogue_ids': sorted(i for i, v in checks.items() if not v),
                         'catalogue_violations': checks}
    represented = [r for r in groups.values() if r['split'] == 'represented']
    overlaps = []
    for heldout in groups.values():
        if heldout['split'] != 'heldout':
            continue
        matches = []
        for rep in represented:
            if heldout['eligible_catalogue_ids'] == rep['eligible_catalogue_ids']:
                matches.append({'represented_group': rep['paraphrase_group'], 'represented_family': rep['family_id'],
                                'identical_constraints': heldout['investor'] == rep['investor'],
                                'identical_violation_vectors': heldout['catalogue_violations'] == rep['catalogue_violations'],
                                'identical_candidate_set': heldout['candidate_ids'] == rep['candidate_ids']})
        if matches:
            overlaps.append({'heldout_group': heldout['paraphrase_group'], 'heldout_family': heldout['family_id'],
                             'eligible_catalogue_ids': heldout['eligible_catalogue_ids'], 'represented_matches': matches})
    return {'paraphrase_groups': len(groups), 'heldout_groups': sum(r['split'] == 'heldout' for r in groups.values()),
            'heldout_families_with_equal_eligibility_rules': sorted({r['heldout_family'] for r in overlaps}),
            'overlapping_heldout_groups': len(overlaps), 'comparisons': overlaps,
            'interpretation': 'Equal eligibility decisions on all catalogue entities. Candidate predicates, reasoning paths, and training exposure may still differ; semantic novelty is not certified.'}


def main():
    out = DATA / 'validation'
    out.mkdir(exist_ok=True)
    sources = ['exports/ct_drafts.jsonl', 'exports/it_drafts.jsonl', 'catalogue.json', 'families.json',
               'evaluation/scenarios.jsonl', 'evaluation/build_report.json',
               'evaluation/development_scenarios.jsonl', 'evaluation/development_report.json',
               'evaluation/capability_probes.jsonl', 'evaluation/context_source_pairs.jsonl',
               'evaluation/context_packets.jsonl']
    inputs = {str((DATA / p).relative_to(ROOT)): sha(DATA / p) for p in sources}
    for name in ('audit_evaluation_leakage.py', 'research_audit.py', 'build_evaluation.py',
                 'build_development_evaluation.py', 'score_annotations.py'):
        path = ROOT / 'scripts/paper1' / name
        inputs[str(path.relative_to(ROOT))] = sha(path)
    units, by_text = [], {}
    eval_counts = collections.Counter()
    for ref, text in evaluation_segments():
        eval_counts[ref['purpose']] += 1
        norm = normalized(text)
        if norm in by_text:
            units[by_text[norm]]['references'].append(ref)
        else:
            by_text[norm] = len(units)
            units.append({'references': [ref], 'text_sha256': hashlib.sha256(norm.encode()).hexdigest(),
                          'normalized_text': norm})
    print(f'Indexing {len(units)} distinct evaluation segments.', flush=True)
    index = CrossSetIndex([grams(u['normalized_text']) for u in units])
    counts = collections.Counter()
    train_counts = collections.Counter()
    implicated, affected = set(), set()
    with (out / 'cross_split_text_matches.jsonl').open('w') as stream:
        for path in [DATA / 'exports/ct_drafts.jsonl', DATA / 'exports/it_drafts.jsonl']:
            for row in read_rows(path):
                for component, text in training_segments(row):
                    train_counts[f'{row["regime"]}_{component}'] += 1
                    norm, values = normalized(text), grams(text)
                    matches = dict(index.matches(values))
                    if norm in by_text:
                        matches.setdefault(by_text[norm], 1.0 if values else None)
                    for unit_id, score in sorted(matches.items()):
                        unit = units[unit_id]
                        exact = norm == unit['normalized_text']
                        counts['matched_segment_pairs'] += 1
                        counts['normalized_exact_pairs' if exact else 'near_only_pairs'] += 1
                        implicated.add(row['item_id'])
                        affected.add(unit_id)
                        stream.write(json.dumps({'training_item_id': row['item_id'], 'training_kind': row['kind'],
                                                 'training_regime': row['regime'], 'training_component': component,
                                                 'evaluation_references': unit['references'], 'jaccard': score,
                                                 'normalized_exact': exact,
                                                 'status': 'requires_overlap_adjudication'}) + '\n')
    entities = json.loads((DATA / 'catalogue.json').read_text())['entities']
    scenarios = list(read_rows(DATA / 'evaluation/scenarios.jsonl'))
    rules = rule_overlap(scenarios, entities)
    eval_report = json.loads((DATA / 'evaluation/build_report.json').read_text())
    rules.update(source_sha256=inputs, family_definition_version=eval_report['family_definition_version'],
                 semantic_isolation_verified=False, research_ready=False)
    (out / 'family_rule_overlap.json').write_text(json.dumps(rules, indent=2) + '\n')
    report = {'created_utc': datetime.now(timezone.utc).isoformat(), 'source_sha256': inputs,
              'method': 'complete cross-side word-5-gram Jaccard >= 0.80 plus normalized exact equality, including short texts',
              'normalization': 'Unicode NFKC, casefold, whitespace collapse; no boilerplate or entity names removed',
              'training_segment_counts': dict(train_counts), 'evaluation_segment_counts': dict(eval_counts),
              'unique_evaluation_segments': len(units), 'text_scan_complete': True,
              'matches': {k: counts[k] for k in ['matched_segment_pairs', 'normalized_exact_pairs', 'near_only_pairs']},
              'training_records_with_matches': len(implicated), 'evaluation_segments_with_matches': len(affected),
              'heldout_families_with_equal_eligibility_rules': rules['heldout_families_with_equal_eligibility_rules'],
              'semantic_isolation_verified': False, 'research_ready': False,
              'limitations': ['Subthreshold paraphrases and semantic equivalence still require review.',
                              'Primitive catalogue facts may legitimately recur; every detected match needs task-level adjudication.',
                              'Component scans prevent long answers or assembled context packets from hiding short prompt or source overlap.',
                              'All training family annotations remain unverified; family IDs alone cannot establish isolation.']}
    report['matches_sha256'] = sha(out / 'cross_split_text_matches.jsonl')
    report['family_rule_overlap_sha256'] = sha(out / 'family_rule_overlap.json')
    (out / 'cross_split_text_summary.json').write_text(json.dumps(report, indent=2) + '\n')
    annotations = [{'family_ids': r.get('family_ids')} for name in ('ct_drafts.jsonl', 'it_drafts.jsonl')
                   for r in read_rows(DATA / 'exports' / name)]
    (out / 'leakage_review.json').write_text(json.dumps(split_review(annotations), indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ['matches', 'training_records_with_matches', 'heldout_families_with_equal_eligibility_rules']}))


if __name__ == '__main__':
    main()
