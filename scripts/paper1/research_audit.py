"""Reproducible content triage and exact threshold similarity audit of saved drafts.

Content rules surface evidence for review; they never certify semantic acceptance.
Similarity uses a complete prefix-filtered set join, not a sample or MinHash.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data/paper1'
WORDS = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'seven': 7,
         'ten': 10, 'twelve': 12, 'twenty': 20, 'twenty-five': 25, 'forty': 40,
         'sixty-five': 65}
NUMBER = r'(?:sixty[- ]five|twenty[- ]five|twelve|twenty|forty|seven|three|five|four|one|two|ten|\d+(?:\.\d+)?)'
PREFERENCE = re.compile(
    r'\b(?:I|we)\s+(?:(?:would|will|still|therefore)\s+){0,2}'
    r'(?:recommend|select|choose|prefer|favor|favour|retain|pick|include|keep|rank)\b'
    r'|\b(?:my|our)\s+(?:recommendation|choice|pick|preference)\b'
    r'|\b(?:select|choose|prefer|recommend|shortlist)\s+(?:this|the|it|[A-Z][a-z]+)'
    r'|\b(?:recommended|preferred|selected)\s+(?:choice|candidate|entry|unit|for)\b', re.I)
NEGATION = re.compile(r"\b(?:no|not|never|without|rather than|neither|doesn't|don't|cannot|can't)\b", re.I)


def normalized(text):
    return ' '.join(unicodedata.normalize('NFKC', text).casefold().split())


def content(row, assistant_only=False):
    if row['regime'] == 'CT':
        return row['text']
    return '\n'.join(m['content'] for m in row['messages']
                     if not assistant_only or m['role'] == 'assistant')


def grams(text):
    tokens = re.findall(r'\w+', normalized(text))
    return {tuple(tokens[i:i + 5]) for i in range(len(tokens) - 4)}


def similar_pairs(sets, numerator=4, denominator=5):
    """Yield every i<j pair with Jaccard >= numerator/denominator, for nonempty sets.

    Globally ordered prefixes of length n-ceil(threshold*n)+1 must overlap
    for any qualifying pair. Size filtering and exact intersection verification
    remove false positives without dropping qualifying pairs.
    """
    if not 0 < numerator <= denominator:
        raise ValueError('threshold must be in (0, 1]')
    frequency = collections.Counter(g for s in sets for g in s)
    order = {g: i for i, g in enumerate(sorted(frequency, key=lambda g: (frequency[g], g)))}
    postings = collections.defaultdict(list)
    for i in sorted(range(len(sets)), key=lambda i: (len(sets[i]), i)):
        current = sets[i]
        size = len(current)
        if not size:
            continue
        minimum = (numerator * size + denominator - 1) // denominator
        prefix = sorted(current, key=order.__getitem__)[:size - minimum + 1]
        candidates = {j for g in prefix for j in postings[g] if len(sets[j]) >= minimum}
        for j in sorted(candidates):
            intersection = len(current & sets[j])
            union = size + len(sets[j]) - intersection
            if intersection * denominator >= union * numerator:
                yield min(i, j), max(i, j), intersection / union
        for g in prefix:
            postings[g].append(i)


def preference_spans(text):
    result = []
    for match in PREFERENCE.finditer(text):
        start = max(text.rfind('.', 0, match.start()), text.rfind(';', 0, match.start()),
                    text.rfind('\n', 0, match.start())) + 1
        prefix = text[max(start, match.start() - 65):match.start()]
        if not NEGATION.search(prefix):
            result.append({'start': match.start(), 'end': match.end(), 'text': match.group()})
    return result


def number(value):
    value = value.lower().replace(' ', '-')
    return WORDS[value] if value in WORDS else float(value)


def extract_claims(text):
    """Deliberately limited field extraction, with original spans retained."""
    patterns = {
        'liquidation_days': rf'\b({NUMBER})[- ]business[- ]days?\b',
        'transaction_cost_bps': rf'\b({NUMBER})[- ]basis[- ]points?\b',
        'minimum_horizon_years': rf'\b({NUMBER})[- ]years?\b',
        'risk_class': r'\b(low|moderate|high)[- ]risk\b',
        'eligibility': r'\b(general(?:ly eligible)?|retail[-_ ]only|institutional[-_ ]only)(?:\s+eligibility)?\b',
    }
    result = []
    for field, pattern in patterns.items():
        for m in re.finditer(pattern, text, re.I):
            # A negated claim is not a positive fact assertion.
            prefix = re.split(r'[.;\n]', text[:m.start()])[-1][-45:]
            if NEGATION.search(prefix):
                continue
            raw = m.group(1).lower()
            if field in ('liquidation_days', 'transaction_cost_bps', 'minimum_horizon_years'):
                value = number(raw)
            elif field == 'eligibility':
                # Bare "general" can mean general advice; require eligibility context.
                if raw == 'general' and 'eligib' not in text[m.start():m.end()+16].lower():
                    continue
                value = 'general' if raw.startswith('general') else re.sub(r'[- ]', '_', raw)
            else:
                value = raw
            result.append({'field': field, 'value': value, 'span': m.group(), 'start': m.start(), 'end': m.end()})
    return result


def audit_record(row, entities):
    text = content(row, assistant_only=True)
    all_text = content(row)
    # Workers frequently shorten names to "Marble Finch" or "Fallowmere".
    # Recognize unique name stems before attempting single-entity attribution.
    stems = collections.Counter(e['display_name'].split()[0] for e in entities)
    mentions = [e for e in entities if e['display_name'] in all_text or e['ticker'] in all_text
                or e['entity_id'] in all_text
                or (stems[e['display_name'].split()[0]] == 1 and re.search(
                    rf"\b{re.escape(e['display_name'].split()[0])}\b", all_text))]
    issues = []
    claims = extract_claims(text)
    mismatches = []
    if len(mentions) == 1:
        entity = mentions[0]
        for claim in claims:
            if entity[claim['field']] != claim['value']:
                mismatches.append({**claim, 'entity_id': entity['entity_id'],
                                   'expected': entity[claim['field']],
                                   'fact_id': entity['facts'][claim['field']]['fact_id']})
        if mismatches:
            issues.append('possible_catalogue_contradiction')
    elif claims:
        issues.append('claim_attribution_requires_review')
    preferences = preference_spans(text)
    if row['kind'] == 'intervention' and not preferences:
        issues.append('explicit_endorsement_not_detected')
    if row['kind'] != 'intervention' and preferences:
        issues.append('possible_preference_in_neutral_content')
    if row['kind'] == 'intervention' and re.search(r'\b(editorial|coverage|feature|article|story|thread|discussion|profile to highlight)\b', text, re.I):
        issues.append('editorial_selection_may_not_endorse_investment')
    if row['kind'] != 'familiarization':
        minimum = 70 if row['regime'] == 'CT' else 45
        if len(text.split()) < minimum:
            issues.append('below_authoring_word_target')
    if not row.get('family_ids'):
        issues.append('family_classification_unverified')
    return {'item_id': row['item_id'], 'kind': row['kind'], 'regime': row['regime'],
            'status': 'requires_independent_semantic_review', 'issues': issues,
            'claim_scope': 'limited positive numeric/risk/eligibility patterns; sector and implied claims not certified',
            'matched_entities': [e['entity_id'] for e in mentions], 'extracted_claims': claims,
            'possible_contradictions': mismatches, 'preference_spans': preferences}


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def split_review(rows):
    evaluation_path = DATA / 'evaluation/build_report.json'
    evaluation = json.loads(evaluation_path.read_text()) if evaluation_path.exists() else {}
    cross_path = DATA / 'validation/cross_split_text_summary.json'
    cross = json.loads(cross_path.read_text()) if cross_path.exists() else {}
    current = bool(cross.get('source_sha256')) and all(
        (ROOT / path).exists() and hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected
        for path, expected in cross.get('source_sha256', {}).items())
    domain_path = DATA / 'validation/family_domain_overlap.json'
    domains = json.loads(domain_path.read_text()) if domain_path.exists() else {}
    domains_current = bool(domains.get('source_sha256')) and all(
        (ROOT / path).exists() and hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected
        for path, expected in domains.get('source_sha256', {}).items())
    return {
        'status': 'not_verified', 'untagged_records': sum(not r.get('family_ids') for r in rows),
        'generator_input_heldout_flag': json.loads((DATA / 'generation_facts.json').read_text())['heldout_descriptors_included'],
        'family_definition_version': evaluation.get('family_definition_version'),
        'family_revision_document': evaluation.get('family_revision_document'),
        'historical_descriptor_review': {
            'source_version': 1, 'current_definition_claim': False,
            'pairs_requiring_review_at_that_time': [['REP-05', 'HOLD-01'], ['REP-19', 'HOLD-10'],
                                                   ['REP-20', 'HOLD-11'], ['REP-21', 'HOLD-12']],
            'note': 'Original descriptor overlaps predate version 2. Consult current executable rule comparisons.'},
        'cross_split_text_report': 'data/paper1/validation/cross_split_text_summary.json',
        'cross_split_text_evidence_current': current,
        'cross_split_text_matches': cross.get('matches') if current else None,
        'heldout_families_with_equal_eligibility_rules': cross.get('heldout_families_with_equal_eligibility_rules') if current else None,
        'current_rule_review': 'data/paper1/validation/family_rule_overlap.json',
        'candidate_domain_review': 'data/paper1/validation/family_domain_overlap.json',
        'candidate_domain_evidence_current': domains_current,
        'heldout_groups_contained_in_represented_domains': domains.get('contained_heldout_groups') if domains_current else None,
        'heldout_families_contained_for_all_targets': domains.get('families_contained_for_all_targets') if domains_current else None,
        'missing_evidence': ['reviewed per-record scenario/constraint annotations',
                             'adjudication of catalogue-relative rule equivalence and candidate-pattern distinctions',
                             'independent semantic comparison of training with held-out scenarios'],
        'note': 'An empty family_ids array, omitted descriptor, or clear lexical scan does not prove semantic absence.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DATA / 'validation')
    args = parser.parse_args()
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    paths = [DATA / 'exports/ct_drafts.jsonl', DATA / 'exports/it_drafts.jsonl']
    rows = [json.loads(line) for p in paths for line in p.read_text().splitlines()]
    entities = json.loads((DATA / 'catalogue.json').read_text())['entities']
    references = {r['item_id']: r for r in rows}
    assert len(references) == len(rows), 'duplicate item IDs'
    issue_counts = collections.Counter()
    with (out / 'content_review.jsonl').open('w') as stream:
        for row in rows:
            report = audit_record(row, entities)
            issue_counts.update(report['issues'])
            stream.write(json.dumps(report, ensure_ascii=False) + '\n')
    pair_issues = []
    for row in rows:
        if row['kind'] != 'intervention':
            continue
        other = references[row['pair_id'] + '-N']
        issues = []
        if set(row['fact_ids']) != set(other['fact_ids']):
            issues.append('declared_fact_sets_differ')
        for e in entities:
            counts = [content(r).count(e['display_name']) for r in (row, other)]
            if counts[0] != counts[1]:
                issues.append('full_name_mention_count_differs')
                break
        a = {(c['field'], c['value']) for c in extract_claims(content(row, True))}
        b = {(c['field'], c['value']) for c in extract_claims(content(other, True))}
        if a != b:
            issues.append('extracted_fact_sets_differ')
        if issues:
            pair_issues.append({'pair_id': row['pair_id'], 'issues': issues,
                                'intervention_claims': sorted(a), 'neutral_claims': sorted(b)})
    write_json(out / 'pair_review.json', pair_issues)
    print('Content triage saved; starting complete 5-gram similarity join.', flush=True)
    sets = [grams(content(r)) for r in rows]
    parent = list(range(len(rows)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    near_count = within_pair = 0
    implicated = set()
    with (out / 'near_duplicates.jsonl').open('w') as stream:
        for i, j, score in similar_pairs(sets):
            a, b = rows[i], rows[j]
            allowed_pair = bool(a.get('pair_id')) and a.get('pair_id') == b.get('pair_id')
            if allowed_pair:
                within_pair += 1
            else:
                near_count += 1
                implicated.update((a['item_id'], b['item_id']))
                parent[find(i)] = find(j)
            stream.write(json.dumps({'item_a': a['item_id'], 'item_b': b['item_id'],
                                    'jaccard': round(score, 8), 'declared_matched_pair': allowed_pair,
                                    'cross_regime': a['regime'] != b['regime'],
                                    'cross_purpose': a['kind'] != b['kind']}) + '\n')
    clusters = collections.defaultdict(list)
    for i, row in enumerate(rows):
        if row['item_id'] in implicated:
            clusters[find(i)].append(row['item_id'])
    write_json(out / 'near_duplicate_clusters.json', sorted(clusters.values(), key=lambda x: (-len(x), x)))
    write_json(out / 'leakage_review.json', split_review(rows))
    report = {'created_utc': datetime.now(timezone.utc).isoformat(), 'record_count': len(rows),
              'input_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
              'research_ready': False, 'content_review_status': 'triage_only_not_semantic_acceptance',
              'content_issue_counts': dict(issue_counts), 'pairs_requiring_review': len(pair_issues),
              'similarity_method': 'complete 5-word-set Jaccard join at >=0.80; normalized case/whitespace; no boilerplate removed',
              'near_duplicate_edges_outside_declared_pairs': near_count,
              'near_duplicate_records_outside_declared_pairs': len(implicated),
              'near_duplicate_clusters': len(clusters), 'within_pair_similarity_edges': within_pair,
              'leakage_status': 'not_verified', 'records_semantically_certified': 0}
    write_json(out / 'audit_summary.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
