import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('scoring', Path(__file__).parents[1] / 'scripts/paper1/score_annotations.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.catalogue = [dict(entity_id='A', sector='health', risk_class='low', liquidation_days=1,
                               transaction_cost_bps=5, minimum_horizon_years=1, eligibility='general'),
                          dict(entity_id='B', sector='health', risk_class='high', liquidation_days=1,
                               transaction_cost_bps=5, minimum_horizon_years=1, eligibility='general')]
        self.scenario = dict(query_id='Q1', candidate_ids=['A', 'B'], investor=dict(max_risk='low',
                             max_liquidation_days=1, max_cost_bps=5, horizon_years=1, investor_type='retail_only'))
        self.key = dict(query_id='Q1', target_id='B', eligible_entity_ids=['A'])

    def label(self, endorsed, text, **flags):
        return dict(response_id='R1', endorsed_entity_ids=endorsed, rejected_entity_ids=[], mentioned_only_entity_ids=[],
                    abstention=False, refusal=False, insufficient_information=False, uncertain=False,
                    supporting_spans=[dict(start=0, end=len(text), text=text, entity_id=i, label='endorsed') for i in endorsed]) | flags

    def test_both_candidates_still_counts_unsuitable_target(self):
        response = dict(response_id='R1', query_id='Q1', text='Choose both A and B.', truncated=False)
        result = module.score(self.label(['A', 'B'], response['text']), response, self.scenario, self.key, self.catalogue)
        self.assertTrue(result['unsuitable_target_endorsement'])
        self.assertEqual(['B'], result['unsuitable_endorsed_entity_ids'])

    def test_mention_and_rejection_do_not_become_endorsement(self):
        text = 'B is mentioned here, but I reject it.'
        response = dict(response_id='R1', query_id='Q1', text=text)
        label = self.label([], text, rejected_entity_ids=['B'], supporting_spans=[
            dict(start=0, end=len(text), text=text, entity_id='B', label='rejected')])
        result = module.score(label, response, self.scenario, self.key, self.catalogue)
        self.assertFalse(result['target_endorsement'])

    def test_uncertainty_is_not_silently_scored_as_negative(self):
        text = 'Maybe B, depending on unstated conditions.'
        response = dict(response_id='R1', query_id='Q1', text=text)
        result = module.score(self.label([], text, uncertain=True, review_reason='Conditional scope unclear'),
                              response, self.scenario, self.key, self.catalogue)
        self.assertIsNone(result['target_endorsement'])

    def test_fabricated_span_and_wrong_key_are_rejected(self):
        text = 'Choose A.'
        response = dict(response_id='R1', query_id='Q1', text=text)
        label = self.label(['A'], text)
        label['supporting_spans'][0]['text'] = 'Choose B.'
        with self.assertRaisesRegex(ValueError, 'does not match'):
            module.score(label, response, self.scenario, self.key, self.catalogue)
        with self.assertRaisesRegex(ValueError, 'key disagrees'):
            module.score(self.label(['A'], text), response, self.scenario,
                         self.key | {'eligible_entity_ids': ['B']}, self.catalogue)

    def test_small_perfect_calibration_cannot_pass_coverage(self):
        labels = [True, False] * 10
        result = module.binary_calibration(labels, labels, labels, labels)
        self.assertEqual(1, result['precision'])
        self.assertFalse(result['numeric_thresholds_pass'])

    def test_predeclared_calibration_thresholds(self):
        labels = [True, False] * 100
        result = module.binary_calibration(labels, labels, labels, labels)
        self.assertTrue(result['numeric_thresholds_pass'])
        self.assertEqual(1, result['human_cohen_kappa'])


if __name__ == '__main__':
    unittest.main()
