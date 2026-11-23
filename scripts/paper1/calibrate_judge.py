"""Check a real-response calibration bundle against the Paper 1 protocol.

Hashes and declared provenance establish internal consistency, not authenticity
or human independence. Passing numeric checks still requires independent review.
No model calls, labels, or empirical results are synthesized by this utility.
"""
import argparse
import collections
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from score_annotations import binary_calibration, score, wilson_lower

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data/paper1'
PRIMARY = ('target_endorsement', 'unsuitable_target_endorsement')
SECONDARY = ('any_unsuitable_endorsement',)
LABEL_SETS = ('endorsed_entity_ids', 'rejected_entity_ids', 'mentioned_only_entity_ids')
LABEL_FLAGS = ('abstention', 'refusal', 'insufficient_information', 'uncertain')
ROLES = ('responses', 'human_a', 'human_b', 'adjudications', 'judge_predictions')


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_field(value, name):
    if not isinstance(value, str) or not value.strip() or value.strip().lower() in {'unknown', 'pending', 'todo'}:
        raise ValueError(f'{name} must be a nonempty, known value')
    return value


def timestamp(value):
    parsed = datetime.fromisoformat(text_field(value, 'timestamp').replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Timestamps must include a timezone')
    return parsed


def immutable_revision(value):
    if not isinstance(value, str) or len(value) not in (40, 64) or any(c not in '0123456789abcdef' for c in value):
        raise ValueError('Model revision must be a commit SHA or an artifact-manifest SHA-256')


def unique_rows(rows, field):
    result = {}
    for row in rows:
        identity = text_field(row.get(field), field)
        if identity in result:
            raise ValueError(f'Duplicate {field}: {identity}')
        result[identity] = row
    return result


def text_list(value, name, allow_empty=True):
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f'{name} must be an array of nonempty strings')
    if len(value) != len(set(value)) or (not allow_empty and not value):
        raise ValueError(f'{name} contains repeated entries or is empty')
    return value


def semantics(label):
    return tuple(tuple(sorted(label[k])) for k in LABEL_SETS) + tuple(label[k] for k in LABEL_FLAGS)


def label_category(label, target):
    if label['uncertain']:
        return 'uncertain'
    for field, category in zip(LABEL_SETS, ['endorsed', 'rejected', 'mentioned_only']):
        if target in label[field]:
            return category
    return 'unmentioned'


def assess_rows(manifest, streams, scenarios, keys, catalogue, generation_logs, judge_log):
    """Assess loaded inputs. Tests use declared fixtures, never observed-data claims."""
    if manifest.get('schema_version') != 1:
        raise ValueError('Unsupported calibration bundle schema')
    if manifest.get('data_origin') not in {'observed_model_responses', 'synthetic_fixture'}:
        raise ValueError('Declare observed_model_responses or synthetic_fixture')
    reviewers = manifest['reviewers']
    a_id, b_id = reviewers['human_a'], reviewers['human_b']
    if text_field(a_id, 'human_a reviewer') == text_field(b_id, 'human_b reviewer'):
        raise ValueError('Initial human reviewers must have distinct identities')
    adjudicators = set(text_list(reviewers['adjudicators'], 'adjudicators'))
    for identity in adjudicators:
        text_field(identity, 'adjudicator')
    if manifest.get('independent_initial_reviews_declared') is not True:
        raise ValueError('Independent initial review declaration is missing')
    if not {'arm', 'dose', 'model_identity', 'intended_target', 'training_seed'} <= set(manifest.get('blinded_fields', [])):
        raise ValueError('Required annotation blinding fields are missing')
    judge = manifest['judge']
    for field in ['run_id', 'model_id', 'model_revision']:
        text_field(judge.get(field), f'judge {field}')
    immutable_revision(judge['model_revision'])
    if (judge.get('adapter_sha256', 'missing') is not None or
            type(judge.get('temperature')) not in (int, float) or judge['temperature'] != 0):
        raise ValueError('The candidate judge must be unadapted and use greedy decoding')
    frozen = timestamp(judge['frozen_utc'])
    if judge.get('final_evaluation_used_for_tuning') is not False:
        raise ValueError('Final evaluation must not be used for judge tuning')
    rubric_hash = manifest['rubric_sha256']
    runs = unique_rows(manifest['model_runs'], 'run_id')
    for run in runs.values():
        for field in ['model_id', 'model_revision', 'condition', 'engine_version']:
            text_field(run.get(field), f'model run {field}')
        immutable_revision(run['model_revision'])
        if not isinstance(run.get('decoding'), dict) or not run['decoding']:
            raise ValueError('Model decoding settings must be recorded')
        adapter = run.get('adapter_sha256', 'missing')
        if adapter is not None and (not isinstance(adapter, str) or len(adapter) != 64 or any(c not in '0123456789abcdef' for c in adapter)):
            raise ValueError('Record a base-only null adapter or its SHA-256')
    records = {role: unique_rows(streams[role], 'response_id') for role in ROLES}
    responses = records['responses']
    for role in ['human_a', 'human_b', 'judge_predictions']:
        if set(records[role]) != set(responses):
            raise ValueError(f'Every response needs exactly one {role} label; no silent exclusion')
    if not set(records['adjudications']) <= set(responses):
        raise ValueError('Adjudication references an unknown response')
    tuning = set(text_list(judge['tuning_response_ids'], 'tuning response IDs'))
    if not tuning <= set(responses):
        raise ValueError('All tuning responses must be included for split verification')
    tuning_families = set()
    for rid in tuning:
        scenario = scenarios[responses[rid]['query_id']]
        if scenario['calibration_partition'] != 'rubric_development':
            raise ValueError('Judge validation response was used for tuning')
        tuning_families.add(scenario['family_id'])
    if tuning_families != set(text_list(judge['tuning_family_ids'], 'tuning family IDs')):
        raise ValueError('Tuning-family declaration disagrees with tuning responses')
    partition_by_family = collections.defaultdict(set)
    for row in scenarios.values():
        if row.get('split') != 'development':
            raise ValueError('Calibration accepts development tasks, not final evaluation')
        partition_by_family[row['family_id']].add(row['calibration_partition'])
    if any(len(parts) != 1 for parts in partition_by_family.values()):
        raise ValueError('Scenario family crosses calibration partitions')
    sampling = manifest['sampling']
    if sampling.get('weighting') not in {'none', 'inverse_probability'}:
        raise ValueError('Unknown sampling-weight convention')
    if type(sampling.get('enriched')) is not bool or (sampling['enriched'] and sampling['weighting'] != 'inverse_probability'):
        raise ValueError('Enriched sampling requires declared inverse-probability weights')
    text_field(sampling.get('description'), 'sampling description')
    required_strata = set(text_list(sampling['required_strata'], 'required collection strata', allow_empty=False))
    seen_generations, seen_strata, seen_families = set(), set(), set()
    assessed, reference_labels = [], {}
    for rid, response in responses.items():
        qid = response['query_id']
        if qid not in scenarios or qid not in keys:
            raise ValueError(f'Response uses an unknown or superseded question: {rid}')
        scenario, key = scenarios[qid], keys[qid]
        partition = scenario['calibration_partition']
        if partition not in {'rubric_development', 'judge_validation'}:
            raise ValueError('Unknown calibration partition')
        if response['prompt_sha256'] != canonical_hash(scenario['messages']):
            raise ValueError(f'Response prompt hash differs from current question: {rid}')
        if not isinstance(response.get('text'), str) or type(response.get('truncated')) is not bool:
            raise ValueError('Record raw response text and actual truncation status')
        generated = timestamp(response['generated_utc'])
        run_id = response['run_id']
        if run_id not in runs:
            raise ValueError('Response model run is missing')
        generation_id = text_field(response.get('generation_id'), 'generation_id')
        observation = (run_id, generation_id)
        if observation in seen_generations:
            raise ValueError('The same logged model generation was counted twice')
        seen_generations.add(observation)
        log = generation_logs[run_id].get(generation_id)
        expected_log = {'query_id': qid, 'prompt_sha256': response['prompt_sha256'],
                        'text_sha256': hashlib.sha256(response['text'].encode()).hexdigest(),
                        'truncated': response['truncated'], 'generated_utc': response['generated_utc']}
        if log is None or any(log.get(k) != v for k, v in expected_log.items()):
            raise ValueError(f'Response differs from its generation log: {rid}')
        weight = response['sampling_weight']
        if type(weight) not in (int, float) or not math.isfinite(weight) or weight <= 0:
            raise ValueError('Sampling weights must be finite and positive')
        if sampling['weighting'] == 'none' and weight != 1:
            raise ValueError('Unweighted collection must use weight one')
        stratum = text_field(response['sampling_stratum'], 'sampling_stratum')
        if stratum not in required_strata:
            raise ValueError('Response belongs to an undeclared sampling stratum')
        seen_strata.add(stratum)
        seen_families.add(scenario['family_id'])
        response_hash = canonical_hash(response)
        labels = {role: records[role][rid] for role in ['human_a', 'human_b', 'judge_predictions']}
        if rid in records['adjudications']:
            labels['adjudications'] = records['adjudications'][rid]
        scores = {}
        for role, label in labels.items():
            if label['response_sha256'] != response_hash or label['rubric_sha256'] != rubric_hash:
                raise ValueError(f'Label is bound to different response or rubric: {rid}, {role}')
            completed = timestamp(label['completed_utc'])
            if any(type(span.get('start')) is not int or type(span.get('end')) is not int
                   for span in label.get('supporting_spans', [])):
                raise ValueError('Span offsets must be JSON integers, not booleans or fractions')
            if completed < generated:
                raise ValueError('Label predates its model response')
            if role in ['human_a', 'human_b'] and label['reviewer_id'] != reviewers[role]:
                raise ValueError('Initial reviewer identity does not match the bundle')
            if role == 'adjudications' and label['reviewer_id'] not in adjudicators:
                raise ValueError('Unknown adjudicator identity')
            if role == 'judge_predictions':
                if label['judge_run_id'] != judge['run_id'] or completed < frozen:
                    raise ValueError('Judge prediction predates its frozen configuration or uses another run')
                if judge_log.get(rid, {}).get('label_sha256') != canonical_hash(label):
                    raise ValueError('Judge label differs from its recorded prediction')
            scores[role] = score(label, response, scenario, key, catalogue)
        a, b = labels['human_a'], labels['human_b']
        if rid in tuning and (generated > frozen or any(timestamp(label['completed_utc']) > frozen
                               for role, label in labels.items() if role != 'judge_predictions')):
            raise ValueError('Tuning response or human labels postdate the frozen judge')
        needs_adjudication = semantics(a) != semantics(b) or a['uncertain'] or b['uncertain']
        if needs_adjudication and 'adjudications' not in labels:
            raise ValueError(f'Human disagreement or uncertainty lacks adjudication: {rid}')
        reference_role = 'adjudications' if 'adjudications' in labels else 'human_a'
        if reference_role == 'adjudications':
            adjudicated = labels[reference_role]
            if timestamp(adjudicated['completed_utc']) < max(timestamp(a['completed_utc']), timestamp(b['completed_utc'])):
                raise ValueError('Adjudication predates the independent initial labels')
            text_field(adjudicated.get('adjudication_reason'), 'adjudication reason')
        reference_labels[rid] = labels[reference_role]
        assessed.append({'response_id': rid, 'query_id': qid, 'family_id': scenario['family_id'],
                         'paraphrase_group': scenario['paraphrase_group'], 'partition': partition,
                         'run_id': run_id, 'sampling_stratum': stratum, 'sampling_weight': weight,
                         'truncated': response['truncated'], 'reference_source': 'adjudication' if reference_role == 'adjudications' else 'independent_human_agreement',
                         'reference': scores[reference_role], 'human_a': scores['human_a'],
                         'human_b': scores['human_b'], 'judge': scores['judge_predictions']})
    validation = [r for r in assessed if r['partition'] == 'judge_validation']
    metrics = {}
    for endpoint in PRIMARY + SECONDARY:
        arrays = [[r[source][endpoint] for r in validation] for source in ['reference', 'judge', 'human_a', 'human_b']]
        unresolved = {source: sum(value is None for value in values) for source, values in
                      zip(['reference', 'judge', 'human_a', 'human_b'], arrays)}
        if any(unresolved.values()):
            metrics[endpoint] = {'n': len(validation), 'numeric_thresholds_pass': False,
                                 'unresolved_labels': unresolved,
                                 'note': 'No response was dropped; complete binary calibration is not computable.'}
            if not unresolved['reference'] and not unresolved['judge']:
                tp = sum(a and b for a, b in zip(arrays[0], arrays[1]))
                predicted = sum(arrays[1])
                positives = sum(arrays[0])
                metrics[endpoint].update(precision=tp / predicted if predicted else None,
                                         recall=tp / positives if positives else None,
                                         precision_wilson_lower=wilson_lower(tp, predicted),
                                         recall_wilson_lower=wilson_lower(tp, positives),
                                         human_cohen_kappa=None)
            continue
        metric = binary_calibration(*arrays)
        weights = [r['sampling_weight'] for r in validation]
        total_weight = sum(weights)
        metric['weighted_reference_prevalence'] = sum(w * y for w, y in zip(weights, arrays[0])) / total_weight if total_weight else None
        metric['unweighted_reference_prevalence'] = sum(arrays[0]) / len(validation) if validation else None
        metric['primary_endpoint'] = endpoint in PRIMARY
        metrics[endpoint] = metric
    confusion = collections.Counter()
    for row in validation:
        rid, qid = row['response_id'], row['query_id']
        target = keys[qid]['target_id']
        confusion[label_category(reference_labels[rid], target), label_category(records['judge_predictions'][rid], target)] += 1
    categories = ['endorsed', 'rejected', 'mentioned_only', 'unmentioned', 'uncertain']
    class_metrics = {}
    for category in categories:
        tp = confusion[category, category]
        predicted = sum(n for (truth, guess), n in confusion.items() if guess == category)
        reference = sum(n for (truth, guess), n in confusion.items() if truth == category)
        class_metrics[category] = {'reference_count': reference, 'predicted_count': predicted,
                                   'precision': tp / predicted if predicted else None,
                                   'recall': tp / reference if reference else None}
    gates = {'observed_data_declared': manifest['data_origin'] == 'observed_model_responses',
             'at_least_400_responses': len(responses) >= 400,
             'both_partitions_observed': {r['partition'] for r in assessed} == {'rubric_development', 'judge_validation'},
             'all_declared_strata_observed': seen_strata == required_strata,
             'all_development_families_observed': seen_families == set(partition_by_family),
             'primary_numeric_thresholds_pass': all(metrics[e]['numeric_thresholds_pass'] for e in PRIMARY)}
    report = {'status': 'assessed_requires_independent_acceptance', 'integrity_checks_pass': True,
              'data_origin': manifest['data_origin'],
              'responses': len(responses), 'partition_counts': dict(collections.Counter(r['partition'] for r in assessed)),
              'validation_responses': len(validation), 'primary_endpoints': list(PRIMARY),
              'metrics': metrics, 'protocol_checks': gates,
              'declared_protocol_checks_pass': all(gates.values()),
              'target_label_confusion': [{'reference': a, 'judge': b, 'count': n} for (a, b), n in sorted(confusion.items())],
              'target_label_class_metrics': class_metrics,
              'stratum_counts': dict(collections.Counter(r['sampling_stratum'] for r in assessed)),
              'validation_family_count': len({r['family_id'] for r in validation}),
              'validation_paraphrase_groups': len({r['paraphrase_group'] for r in validation}),
              'validation_unique_queries': len({r['query_id'] for r in validation}),
              'repeated_response_texts': len(responses) - len({r['text'] for r in responses.values()}),
              'research_measurement_validated': False, 'research_ready': False,
              'limits': ['Hashes and declarations do not authenticate model execution, reviewer identities, blinding or independence.',
                         'Only judge-validation responses enter acceptance metrics; rubric-development responses only count toward collection coverage.',
                         'Precision/recall and Wilson limits describe the sampled validation mix; weighting is used only for reported prevalence.',
                         'Paraphrase, family and run dependence remains; operational Wilson thresholds are not a population-level confidence guarantee.',
                         'Paper 2 updating endpoints and context-condition coverage are not established by this Paper 1 bundle.',
                         'Synthetic fixtures can exercise calculations but cannot pass the observed-data declaration gate.']}
    return report, assessed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, default=DATA / 'calibration/bundle.json')
    parser.add_argument('--output', type=Path, default=DATA / 'validation/calibration')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    sources = {str(p.relative_to(ROOT)): sha(p) for p in [Path(__file__).resolve(),
               ROOT / 'scripts/paper1/score_annotations.py', DATA / 'catalogue.json',
               DATA / 'evaluation/development_scenarios.jsonl', DATA / 'private/answer_keys/development.jsonl',
               ROOT / 'docs/PILOT_DECISIONS.md', ROOT / 'docs/ANNOTATION_GUIDE.md']}
    report = {'responses': 0, 'loaded_response_count': 0, 'integrity_checks_pass': False, 'declared_protocol_checks_pass': False,
              'research_measurement_validated': False, 'research_ready': False, 'source_sha256': sources,
              'created_utc': datetime.now(timezone.utc).isoformat(), 'artifact_sha256': {}}
    if not args.bundle.exists():
        report.update(status='missing_observed_calibration_bundle', required_bundle=str(args.bundle),
                      required_label_streams=list(ROLES),
                      note='No observed responses or human labels were loaded. This is not a calibration result.')
        (args.output / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps({'status': report['status'], 'responses': 0}))
        return 2
    try:
        manifest = json.loads(args.bundle.read_text())
        sources[str(args.bundle.resolve())] = sha(args.bundle)
        def read_ref(ref, jsonl=True):
            path = (args.bundle.parent / ref['path']).resolve()
            if sha(path) != ref['sha256']:
                raise ValueError(f'Input hash mismatch: {path.name}')
            sources[str(path)] = ref['sha256']
            return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if jsonl else path
        for relative in ['catalogue.json', 'evaluation/development_scenarios.jsonl', 'private/answer_keys/development.jsonl']:
            if manifest['dataset_sha256'][relative] != sha(DATA / relative):
                raise ValueError(f'Calibration uses a different dataset version: {relative}')
        rubric = read_ref(manifest['rubric'], jsonl=False)
        if sha(rubric) != manifest['rubric_sha256']:
            raise ValueError('Rubric file and rubric declaration disagree')
        streams = {role: read_ref(manifest['files'][role]) for role in ROLES}
        report['loaded_response_count'] = len(streams['responses'])
        logs = {run['run_id']: unique_rows(read_ref(run['generation_log']), 'generation_id') for run in manifest['model_runs']}
        judge_log = unique_rows(read_ref(manifest['judge']['prediction_log']), 'response_id')
        scenarios = unique_rows([json.loads(s) for s in (DATA / 'evaluation/development_scenarios.jsonl').read_text().splitlines()], 'query_id')
        keys = unique_rows([json.loads(s) for s in (DATA / 'private/answer_keys/development.jsonl').read_text().splitlines()], 'query_id')
        catalogue = json.loads((DATA / 'catalogue.json').read_text())['entities']
        assessed, rows = assess_rows(manifest, streams, scenarios, keys, catalogue, logs, judge_log)
        report.update(assessed)
        path = args.output / 'scored_records.jsonl'
        path.write_text(''.join(json.dumps(r) + '\n' for r in rows))
        report['artifact_sha256'] = {path.name: sha(path)}
    except (KeyError, TypeError, ValueError, OSError) as exc:
        report.update(status='failed_calibration_integrity', error=str(exc), integrity_checks_pass=False,
                      declared_protocol_checks_pass=False)
    (args.output / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ['status', 'responses', 'integrity_checks_pass', 'declared_protocol_checks_pass']}))
    return 0 if report['declared_protocol_checks_pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
