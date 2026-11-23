"""Prepare blind content-review packets without fabricating reviewer decisions."""
import collections
import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data/paper1'


def save_versioned_packet(name, records, keys, out, private):
    payload = ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in records)
    packet_hash = hashlib.sha256(payload.encode()).hexdigest()
    key_payload = ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in keys)
    versions_to_save = []
    for directory, content in [(out, payload), (private, key_payload)]:
        versions = directory / 'versions'
        versions.mkdir(exist_ok=True)
        path = versions / f'{name}_{packet_hash}.jsonl'
        if path.exists():
            if path.read_text() != content:
                raise ValueError('An immutable packet version has different content')
        versions_to_save.append((path, content))
    for path, content in versions_to_save:
        if not path.exists():
            path.write_text(content)
    (out / f'{name}.jsonl').write_text(payload)
    (private / f'{name}.jsonl').write_text(key_payload)
    templates = []
    for reviewer in ('reviewer_a', 'reviewer_b'):
        path = out / f'{name}_{reviewer}_{packet_hash}.jsonl'
        if not path.exists():
            forms = [{'review_id': r['review_id'], 'packet_sha256': packet_hash,
                      'content_sha256': r['content_sha256'], 'reviewer_id': None,
                      'completed_utc': None, 'A': None, 'B': None, 'pair_fact_match': None,
                      'pair_mention_match': None, 'scenario_annotations': None, 'notes': None} for r in records]
            path.write_text(''.join(json.dumps(r) + '\n' for r in forms))
        templates.append(str(path))
    return {'packet_sha256': packet_hash, 'template_paths': templates,
            'immutable_packet_path': str(out / 'versions' / f'{name}_{packet_hash}.jsonl')}


def main():
    rows = [json.loads(l) for name in ['ct_drafts.jsonl', 'it_drafts.jsonl']
            for l in (DATA / 'exports' / name).read_text().splitlines()]
    by_id = {r['item_id']: r for r in rows}
    entities = json.loads((DATA / 'catalogue.json').read_text())['entities']
    entity_by_id = {e['entity_id']: e for e in entities}
    scope_reviews = {}
    for scope_path in sorted((DATA / 'revisions').glob('question_scope_review_*.json')):
        for record in json.loads(scope_path.read_text())['records']:
            if record['decision'] in {'restore_original_four_candidate_scope',
                                      'clarify_single_record_lookup', 'clarify_two_record_comparison'}:
                scope_reviews[record['item_id']] = record
    facts = {f['fact_id']: {'entity_id': e['entity_id'], 'entity_name': e['display_name'], 'field': k, **f}
             for e in entities for k, f in e['facts'].items()}
    cells = collections.defaultdict(list)
    for row in rows:
        if row['kind'] == 'intervention':
            cells[row['target_id'], row['regime'], row['genre_id'], row['proposition_id']].append(row['pair_id'])
    rng = random.Random(421197)
    selected = [rng.choice(sorted(cells[key])) for key in sorted(cells)]
    assert len(selected) == 400
    out = DATA / 'validation/human_review'
    private = DATA / 'private/review_keys'
    out.mkdir(parents=True, exist_ok=True)
    private.mkdir(parents=True, exist_ok=True)
    public, keys = [], []
    rng.shuffle(selected)
    for index, pair in enumerate(selected, 1):
        sides = [by_id[pair + '-I'], by_id[pair + '-N']]
        rng.shuffle(sides)
        review_id = f'CONTENT-{index:04d}'
        public.append({'review_id': review_id,
                       'intended_genre': sides[0]['genre'],
                       'proposition_id': sides[0]['proposition_id'],
                       'texts': {name: {k: row[k] for k in ['text', 'messages'] if k in row} for name, row in zip(['A', 'B'], sides)},
                       'allowed_facts': [facts[f] for f in sorted({f for r in sides for f in r['fact_ids']})],
                       'questions': ['List unsupported factual claims with exact spans.',
                                     'Does each text recommend an investment, merely recommend coverage, or remain neutral?',
                                     'Do the texts preserve factual content and entity mentions?',
                                     'Is the requested genre realized naturally?',
                                     'Identify any investor constraints or scenario pattern expressed.']})
        record = public[-1]
        record['content_sha256'] = hashlib.sha256(json.dumps(
            {k: record[k] for k in ['texts', 'allowed_facts', 'intended_genre', 'proposition_id']},
            sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        keys.append({'review_id': review_id, 'content_sha256': record['content_sha256'], 'pair_id': pair,
                     'A': {'item_id': sides[0]['item_id'], 'kind': sides[0]['kind']},
                     'B': {'item_id': sides[1]['item_id'], 'kind': sides[1]['kind']}})
    pair_version = save_versioned_packet('stratified_pairs', public, keys, out, private)
    audit = [json.loads(l) for l in (DATA / 'validation/content_review.jsonl').read_text().splitlines()]
    flagged = [{'item_id': r['item_id'], 'issues': r['issues']} for r in audit if any(
        i in r['issues'] for i in ['possible_catalogue_contradiction', 'possible_preference_in_neutral_content',
                                   'explicit_endorsement_not_detected', 'editorial_selection_may_not_endorse_investment'])]
    (private / 'additional_flagged_records.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in flagged))
    # Repairs must still be reviewed even when the original triage flags disappear.
    repaired = [r for r in rows if r.get('generator', {}).get('validation_revisions')]
    repair_groups = collections.defaultdict(list)
    for row in repaired:
        repair_groups[row.get('pair_id') or row['item_id']].append(row)
    group_ids = sorted(repair_groups)
    repair_rng = random.Random(421198)
    repair_rng.shuffle(group_ids)
    repair_public, repair_keys = [], []
    for index, group in enumerate(group_ids, 1):
        sides = list(repair_groups[group])
        repair_rng.shuffle(sides)
        review_id = f'REPAIRED-{index:04d}'
        texts = {name: {k: row[k] for k in ['text', 'messages'] if k in row}
                 for name, row in zip(['A', 'B'], sides)}
        allowed = [facts[f] for f in sorted({f for row in sides for f in row['fact_ids']})]
        scope_references = {}
        for name, row in zip(['A', 'B'], sides):
            if row['item_id'] in scope_reviews:
                scope = scope_reviews[row['item_id']]
                if row['messages'][0]['content'] != scope['new_question']:
                    raise ValueError('Scope review must be refreshed after a question changes')
                # Include negative candidates too: answer-only facts cannot establish
                # whether an exhaustive selection or a no-match answer is correct.
                candidate_ids = scope.get('candidate_ids', scope['original_candidate_ids'])
                scope_references[name] = [entity_by_id[e] for e in candidate_ids]
        content = {'texts': texts, 'allowed_facts': allowed}
        if scope_references:
            content['candidate_scope_reference'] = scope_references
        content_hash = hashlib.sha256(json.dumps(content,
                                                 sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        repair_public.append({'review_id': review_id, **content,
                              'content_sha256': content_hash,
                              'questions': ['Check catalogue facts and unsupported claims.',
                                            'Check whether the user names the intended candidate set and the answer includes all and only the matching entries. Use the full candidate reference, when supplied, to check excluded entries too.',
                                            'Label investment recommendation, rejection, editorial preference, or neutrality.',
                                            'For pairs, check factual and mention balance and identical user turns.',
                                            'Annotate investor constraints or scenario patterns.']})
        repair_keys.append({'review_id': review_id, 'content_sha256': content_hash,
                            'sides': {name: {'item_id': row['item_id'], 'kind': row['kind'],
                                             'revisions': row['generator']['validation_revisions']}
                                      for name, row in zip(['A', 'B'], sides)}})
    repair_version = save_versioned_packet('repaired_records', repair_public, repair_keys, out, private)
    for version in (pair_version, repair_version):
        version['template_paths'] = [str(Path(path).relative_to(ROOT)) for path in version['template_paths']]
        version['immutable_packet_path'] = str(Path(version['immutable_packet_path']).relative_to(ROOT))
    report = {'required_stratified_pairs': 400, 'prepared_pairs': len(public),
              'sample_seed': 421197, 'completed_reviews': 0, 'research_ready': False,
              'stratified_packet_version': pair_version, 'repaired_packet_version': repair_version,
              'repaired_records_requiring_review': len(repaired), 'repaired_review_units': len(repair_public),
              'repaired_packet_sha256': hashlib.sha256((out / 'repaired_records.jsonl').read_bytes()).hexdigest(),
              'source_sha256': {f'data/paper1/exports/{name}': hashlib.sha256((DATA / 'exports' / name).read_bytes()).hexdigest()
                                for name in ['ct_drafts.jsonl', 'it_drafts.jsonl']},
              'additional_flagged_records': len(flagged), 'pair_packet_sha256': hashlib.sha256((out / 'stratified_pairs.jsonl').read_bytes()).hexdigest(),
              'note': 'Blank forms are not labels. Independent reviewers must return actual judgments. Additional flagged records and all evaluation/context pairs require review too.'}
    (out / 'packet_manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
