"""Synthetic unit fixtures only; none are written as observed calibration data."""
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / 'scripts/paper1'))
from calibrate_judge import DATA, assess_rows, canonical_hash


def fixture():
    catalogue = [dict(entity_id='A', sector='health', risk_class='low', liquidation_days=1,
                      transaction_cost_bps=5, minimum_horizon_years=1, eligibility='general'),
                 dict(entity_id='B', sector='health', risk_class='high', liquidation_days=1,
                      transaction_cost_bps=5, minimum_horizon_years=1, eligibility='general')]
    policy = dict(max_risk='low', max_liquidation_days=1, max_cost_bps=5, horizon_years=1,
                  investor_type='retail_only')
    scenarios, keys = {}, {}
    for qid, family, partition in [('QD', 'DEV-01', 'rubric_development'), ('QV', 'DEV-07', 'judge_validation')]:
        scenarios[qid] = dict(query_id=qid, family_id=family, split='development',
                              calibration_partition=partition, paraphrase_group=family,
                              candidate_ids=['A', 'B'], investor=policy,
                              messages=[dict(role='user', content=f'Synthetic fixture task {qid}')])
        keys[qid] = dict(query_id=qid, target_id='B', eligible_entity_ids=['A'])
    manifest = dict(schema_version=1, data_origin='synthetic_fixture',
                    reviewers=dict(human_a='human-A', human_b='human-B', adjudicators=['adjudicator']),
                    independent_initial_reviews_declared=True,
                    blinded_fields=['arm', 'dose', 'model_identity', 'intended_target', 'training_seed'],
                    rubric_sha256='a' * 64,
                    judge=dict(run_id='judge-fixture', model_id='synthetic-judge', model_revision='f' * 40,
                               adapter_sha256=None, temperature=0, frozen_utc='2026-01-01T00:02:00Z',
                               tuning_response_ids=['R0000'], tuning_family_ids=['DEV-01'],
                               final_evaluation_used_for_tuning=False),
                    model_runs=[dict(run_id='run-fixture', model_id='synthetic-model', model_revision='e' * 40,
                                     condition='fixture-only', engine_version='unit-test', adapter_sha256=None,
                                     decoding={'temperature': 0, 'max_new_tokens': 256})],
                    sampling=dict(enriched=False, weighting='none', required_strata=['even', 'odd'],
                                  description='Synthetic unit fixture, not empirical collection'))
    streams = dict(responses=[], human_a=[], human_b=[], adjudications=[], judge_predictions=[])
    logs, judge_log = {'run-fixture': {}}, {}
    for i in range(400):
        rid = f'R{i:04d}'
        qid = 'QD' if i < 200 else 'QV'
        endorsed = 'B' if i % 2 == 0 else 'A'
        text = f'Choose {endorsed}. Synthetic fixture {i}.'
        response = dict(response_id=rid, query_id=qid, run_id='run-fixture', generation_id=str(i),
                        text=text, truncated=False, generated_utc='2026-01-01T00:00:00Z',
                        prompt_sha256=canonical_hash(scenarios[qid]['messages']),
                        sampling_weight=1, sampling_stratum='even' if i % 2 == 0 else 'odd')
        streams['responses'].append(response)
        logs['run-fixture'][str(i)] = dict(generation_id=str(i), query_id=qid,
                                           prompt_sha256=response['prompt_sha256'],
                                           text_sha256=hashlib.sha256(text.encode()).hexdigest(), truncated=False,
                                           generated_utc=response['generated_utc'])
        label = dict(response_id=rid, response_sha256=canonical_hash(response), rubric_sha256=manifest['rubric_sha256'],
                     endorsed_entity_ids=[endorsed], rejected_entity_ids=[], mentioned_only_entity_ids=[],
                     abstention=False, refusal=False, insufficient_information=False, uncertain=False,
                     review_reason='', supporting_spans=[dict(start=0, end=9, text=text[:9], entity_id=endorsed, label='endorsed')])
        for role, identity in [('human_a', 'human-A'), ('human_b', 'human-B')]:
            streams[role].append(copy.deepcopy(label) | dict(reviewer_id=identity, completed_utc='2026-01-01T00:01:00Z'))
        predicted = copy.deepcopy(label) | dict(judge_run_id='judge-fixture', completed_utc='2026-01-01T00:03:00Z')
        streams['judge_predictions'].append(predicted)
        judge_log[rid] = dict(response_id=rid, label_sha256=canonical_hash(predicted))
    return manifest, streams, scenarios, keys, catalogue, logs, judge_log


class CalibrationTests(unittest.TestCase):
    def test_perfect_fixture_is_never_empirical_acceptance(self):
        report, rows = assess_rows(*fixture())
        self.assertEqual(400, report['responses'])
        self.assertEqual(200, report['validation_responses'])
        self.assertEqual(400, len(rows))
        for endpoint in report['primary_endpoints']:
            self.assertTrue(report['metrics'][endpoint]['numeric_thresholds_pass'])
            self.assertEqual(100, report['metrics'][endpoint]['positives'])
        self.assertFalse(report['declared_protocol_checks_pass'])
        self.assertFalse(report['research_measurement_validated'])

    def test_missing_label_and_reused_generation_are_rejected(self):
        data = fixture()
        data[1]['human_b'].pop()
        with self.assertRaisesRegex(ValueError, 'no silent exclusion'):
            assess_rows(*data)
        data = fixture()
        data[1]['responses'][1]['generation_id'] = '0'
        with self.assertRaisesRegex(ValueError, 'counted twice'):
            assess_rows(*data)

    def test_response_rubric_and_generation_log_binding(self):
        for mutation, message in [
                (lambda d: d[1]['responses'][0].update(prompt_sha256='b' * 64), 'prompt hash'),
                (lambda d: d[1]['human_a'][0].update(response_sha256='b' * 64), 'different response or rubric'),
                (lambda d: d[1]['human_a'][0].update(rubric_sha256='b' * 64), 'different response or rubric'),
                (lambda d: d[5]['run-fixture']['0'].update(text_sha256='b' * 64), 'generation log'),
                (lambda d: d[6]['R0000'].update(label_sha256='b' * 64), 'recorded prediction')]:
            data = fixture()
            mutation(data)
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                assess_rows(*data)

    def test_validation_tuning_and_unfrozen_predictions_are_rejected(self):
        data = fixture()
        data[0]['judge']['tuning_response_ids'] = ['R0200']
        data[0]['judge']['tuning_family_ids'] = ['DEV-07']
        with self.assertRaisesRegex(ValueError, 'validation response was used for tuning'):
            assess_rows(*data)
        data = fixture()
        data[0]['judge']['frozen_utc'] = '2026-01-01T00:04:00Z'
        with self.assertRaisesRegex(ValueError, 'predates its frozen configuration'):
            assess_rows(*data)
        data = fixture()
        data[0]['judge']['frozen_utc'] = '2026-01-01T00:00:30Z'
        with self.assertRaisesRegex(ValueError, 'labels postdate the frozen judge'):
            assess_rows(*data)

    def test_distinct_reviewers_and_pinned_revisions_are_required(self):
        data = fixture()
        data[0]['reviewers']['human_b'] = 'human-A'
        with self.assertRaisesRegex(ValueError, 'distinct identities'):
            assess_rows(*data)
        data = fixture()
        data[0]['judge']['model_revision'] = 'main'
        with self.assertRaisesRegex(ValueError, 'commit SHA'):
            assess_rows(*data)

    def test_disagreement_needs_a_bound_later_adjudication(self):
        data = fixture()
        label = data[1]['human_b'][200]
        label.update(endorsed_entity_ids=[], rejected_entity_ids=['B'])
        label['supporting_spans'][0]['label'] = 'rejected'
        with self.assertRaisesRegex(ValueError, 'lacks adjudication'):
            assess_rows(*data)
        adjudication = copy.deepcopy(data[1]['human_a'][200])
        adjudication.update(reviewer_id='adjudicator', completed_utc='2026-01-01T00:02:00Z',
                            adjudication_reason='Synthetic fixture disagreement resolved for the test.')
        data[1]['adjudications'] = [adjudication]
        report, rows = assess_rows(*data)
        self.assertEqual('adjudication', rows[200]['reference_source'])
        self.assertLess(report['metrics']['target_endorsement']['human_raw_agreement'], 1)
        adjudication['completed_utc'] = '2026-01-01T00:00:30Z'
        with self.assertRaisesRegex(ValueError, 'Adjudication predates'):
            assess_rows(*data)

    def test_uncertainty_is_retained_and_blocks_complete_binary_calibration(self):
        data = fixture()
        label = data[1]['human_a'][200]
        label.update(uncertain=True, review_reason='Synthetic uncertain case.')
        adjudication = copy.deepcopy(data[1]['human_b'][200])
        adjudication.update(reviewer_id='adjudicator', completed_utc='2026-01-01T00:02:00Z',
                            adjudication_reason='Synthetic resolution.')
        data[1]['adjudications'] = [adjudication]
        report, rows = assess_rows(*data)
        metric = report['metrics']['target_endorsement']
        self.assertEqual(200, metric['n'])
        self.assertEqual(1, metric['unresolved_labels']['human_a'])
        self.assertEqual(1, metric['precision'])
        self.assertIsNone(metric['human_cohen_kappa'])
        self.assertFalse(metric['numeric_thresholds_pass'])
        self.assertEqual(400, len(rows))

    def test_development_labels_do_not_improve_validation_scores(self):
        data = fixture()
        for label in data[1]['judge_predictions'][200:]:
            label.update(endorsed_entity_ids=[], supporting_spans=[])
            data[6][label['response_id']]['label_sha256'] = canonical_hash(label)
        report, _ = assess_rows(*data)
        self.assertEqual(0, report['metrics']['target_endorsement']['recall'])
        self.assertEqual(200, report['metrics']['target_endorsement']['n'])

    def test_invalid_weights_and_boolean_span_offsets_are_rejected(self):
        data = fixture()
        data[1]['responses'][200]['sampling_weight'] = float('nan')
        with self.assertRaisesRegex(ValueError, 'finite and positive'):
            assess_rows(*data)
        data = fixture()
        data[1]['human_a'][200]['supporting_spans'][0]['start'] = False
        with self.assertRaisesRegex(ValueError, 'JSON integers'):
            assess_rows(*data)

    def test_enrichment_weights_affect_prevalence_not_validation_membership(self):
        data = fixture()
        data[0]['sampling'].update(enriched=True, weighting='inverse_probability')
        for index, response in enumerate(data[1]['responses']):
            response['sampling_weight'] = 3 if index % 2 == 0 else 1
            for role in ['human_a', 'human_b', 'judge_predictions']:
                data[1][role][index]['response_sha256'] = canonical_hash(response)
            predicted = data[1]['judge_predictions'][index]
            data[6][response['response_id']]['label_sha256'] = canonical_hash(predicted)
        report, _ = assess_rows(*data)
        metric = report['metrics']['target_endorsement']
        self.assertEqual(.75, metric['weighted_reference_prevalence'])
        self.assertEqual(.5, metric['unweighted_reference_prevalence'])
        self.assertEqual(200, metric['n'])

    def test_cli_rejects_file_hash_mismatch_before_any_scoring(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'rubric.md').write_text('Synthetic fixture rubric.')
            (root / 'responses.jsonl').write_text('')
            rubric_sha = hashlib.sha256((root / 'rubric.md').read_bytes()).hexdigest()
            bundle = dict(dataset_sha256={name: hashlib.sha256((DATA / name).read_bytes()).hexdigest() for name in
                          ['catalogue.json', 'evaluation/development_scenarios.jsonl', 'private/answer_keys/development.jsonl']},
                          rubric=dict(path='rubric.md', sha256=rubric_sha), rubric_sha256=rubric_sha,
                          files=dict(responses=dict(path='responses.jsonl', sha256='0' * 64)))
            (root / 'bundle.json').write_text(json.dumps(bundle))
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/paper1/calibrate_judge.py'),
                                     '--bundle', str(root / 'bundle.json'), '--output', str(root / 'out')],
                                    capture_output=True, text=True)
            self.assertEqual(1, result.returncode, result.stderr)
            report = json.loads((root / 'out/summary.json').read_text())
            self.assertEqual('failed_calibration_integrity', report['status'])
            self.assertIn('Input hash mismatch', report['error'])
            self.assertFalse(report['declared_protocol_checks_pass'])
            self.assertFalse((root / 'out/scored_records.jsonl').exists())


if __name__ == '__main__':
    unittest.main()
