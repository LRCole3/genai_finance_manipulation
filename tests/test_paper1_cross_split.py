import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts/paper1'))
from audit_evaluation_leakage import CrossSetIndex, rule_overlap, training_segments
from build_evaluation import position_balance


class CrossSplitTests(unittest.TestCase):
    def test_cross_join_matches_exhaustive_oracle_with_unseen_training_grams(self):
        rng = random.Random(1917)
        right = [set(rng.sample(range(40), rng.randrange(0, 30))) for _ in range(70)]
        left = [set(rng.sample(range(60), rng.randrange(0, 30))) for _ in range(70)]
        left += right + [s | {100, 101} for s in right]
        for numerator, denominator in [(4, 5), (1, 1), (1, 2)]:
            index = CrossSetIndex(right, numerator, denominator)
            for values in left:
                expected = {i for i, other in enumerate(right) if values and other
                            and len(values & other) * denominator >= len(values | other) * numerator}
                self.assertEqual(expected, {i for i, _ in index.matches(values)})

    def test_exact_threshold_and_empty_sets(self):
        index = CrossSetIndex([set(range(4)), set(), set(range(3))])
        self.assertEqual([(0, 0.8)], list(index.matches(set(range(5)))))
        self.assertEqual([], list(index.matches(set())))
        with self.assertRaises(ValueError):
            CrossSetIndex([], 6, 5)

    def test_it_components_are_scanned_separately(self):
        row = {'regime': 'IT', 'messages': [{'role': 'user', 'content': 'A repeated task'},
                                           {'role': 'assistant', 'content': 'An otherwise unrelated long answer'}]}
        actual = dict(training_segments(row))
        self.assertEqual('A repeated task', actual['user'])
        self.assertEqual('An otherwise unrelated long answer', actual['assistant'])
        self.assertEqual(actual['user'] + '\n' + actual['assistant'], actual['full_messages'])

    def test_rule_equivalence_is_separate_from_constraint_or_candidate_equality(self):
        entity = dict(entity_id='E1', risk_class='low', liquidation_days=1,
                      transaction_cost_bps=5, minimum_horizon_years=1, eligibility='general', sector='technology')
        policy = dict(max_risk='low', max_liquidation_days=2, max_cost_bps=5,
                      horizon_years=1, investor_type='retail_only')
        rep = dict(paraphrase_group='REP-T1', family_id='REP', split='represented',
                   investor=policy, candidate_ids=['E1'])
        held = dict(paraphrase_group='HOLD-T1', family_id='HOLD', split='heldout',
                    investor={**policy, 'horizon_years': 7}, candidate_ids=['E2'])
        result = rule_overlap([rep, held], [entity])
        self.assertEqual(['HOLD'], result['heldout_families_with_equal_eligibility_rules'])
        match = result['comparisons'][0]['represented_matches'][0]
        self.assertFalse(match['identical_constraints'])
        self.assertFalse(match['identical_candidate_set'])
        self.assertTrue(match['identical_violation_vectors'])
        with self.assertRaisesRegex(ValueError, 'Paraphrase group changes'):
            rule_overlap([rep, {**rep, 'investor': held['investor']}], [entity])

    def test_position_balance_handles_irrelevant_target_split(self):
        rows = [dict(query_id=str(i), split='heldout', candidate_ids=['E', 'X'] if i % 2 == 0 else ['X', 'E']) for i in range(4)]
        rows += [dict(query_id='irrelevant', split='irrelevant_target', candidate_ids=['X', 'Y'])]
        keys = [dict(query_id=r['query_id'], target_id='E') for r in rows]
        result = position_balance(rows, keys)
        self.assertFalse(result['balanced'])
        self.assertEqual([2, 2, 0, 0], result['counts'][0]['position_counts'])
        rows[-1]['candidate_ids'] = ['E', 'Y']
        with self.assertRaisesRegex(ValueError, 'Irrelevant target appears'):
            position_balance(rows, keys)


if __name__ == '__main__':
    unittest.main()
