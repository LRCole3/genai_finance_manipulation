import importlib.util
import random
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('audit', Path(__file__).parents[1] / 'scripts/paper1/research_audit.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class SimilarityTests(unittest.TestCase):
    def test_prefix_join_matches_exhaustive_oracle(self):
        rng = random.Random(42)
        sets = [set(rng.sample(range(45), rng.randrange(1, 35))) for _ in range(80)]
        for base in list(sets[:30]):
            sets.extend([set(base), base | {97}, base - {min(base)}])
        sets.extend([set(), set()])
        for numerator, denominator in [(4, 5), (1, 1), (1, 2)]:
            expected = {(i, j) for i, a in enumerate(sets) for j, b in enumerate(sets)
                        if i < j and a and b and len(a & b) * denominator >= len(a | b) * numerator}
            actual = {(i, j) for i, j, _ in audit.similar_pairs(sets, numerator, denominator)}
            self.assertEqual(expected, actual)

    def test_exact_threshold_is_inclusive(self):
        self.assertEqual([(0, 1, .8)], list(audit.similar_pairs([{1, 2, 3, 4}, {1, 2, 3, 4, 5}])))


class ContentTests(unittest.TestCase):
    def test_neutral_negation_is_not_positive_preference(self):
        self.assertFalse(audit.preference_spans('I would not recommend this unit.'))
        self.assertFalse(audit.preference_spans('The record does not recommend this unit.'))
        self.assertTrue(audit.preference_spans('I would select it as a topical example.'))

    def test_field_units_and_spelled_numbers(self):
        values = {(x['field'], x['value']) for x in audit.extract_claims(
            'Low risk, institutional-only eligibility, twenty-five basis points, '
            'five business days, and a seven-year minimum horizon.')}
        self.assertEqual(values, {('risk_class', 'low'), ('eligibility', 'institutional_only'),
                                 ('transaction_cost_bps', 25), ('liquidation_days', 5), ('minimum_horizon_years', 7)})

    def test_negated_risk_is_not_an_assertion(self):
        self.assertEqual([], audit.extract_claims('It is not a low-risk unit.'))


if __name__ == '__main__':
    unittest.main()
