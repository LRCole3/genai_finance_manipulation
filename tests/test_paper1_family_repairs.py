import itertools
import json
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / 'scripts/paper1'))
from assess_family_repairs import (FAMILIES, assign_distinct, candidate_witness,
                                   core_preserved, policy_grid, signature)
from build_evaluation import family_matches


class FamilyRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entities = json.loads((ROOT / 'data/paper1/catalogue.json').read_text())['entities']

    def test_constructive_witness_against_exhaustive_candidate_oracle(self):
        keep = {1, 6, 11, 16, 18, 22, 31, 33}
        entities = [e for e in self.entities if int(e['entity_id'].split('-')[-1]) in keep]
        policies, _ = policy_grid(self.entities)
        policies = random.Random(47).sample(policies, 40)
        for family in FAMILIES:
            for policy in policies:
                for target in (entities[0]['entity_id'], entities[2]['entity_id']):
                    exists = core_preserved(family, policy) and any(
                        any(e['entity_id'] == target for e in group) and family_matches(family, group, policy)
                        for group in itertools.combinations(entities, 4))
                    self.assertEqual(exists, candidate_witness(entities, family, policy, target) is not None,
                                     (family, policy, target))

    def test_threshold_grid_covers_between_value_and_above_max_policies(self):
        policies, _ = policy_grid(self.entities)
        signatures = {signature(self.entities, policy) for policy in policies}
        for risk, investor, threshold in itertools.product(
                ['low', 'moderate', 'high'], ['retail_only', 'institutional_only'], [0.5, 1.5, 4.5, 9.5, 100]):
            policy = dict(max_risk=risk, investor_type=investor, max_liquidation_days=threshold,
                          max_cost_bps=threshold * 4, horizon_years=threshold / 2)
            self.assertIn(signature(self.entities, policy), signatures)

    def test_matching_optimizes_cardinality_before_policy_changes(self):
        def option(ids, cost):
            return {'eligible_catalogue_ids': ids, 'changed_field_count': cost}
        result = assign_distinct({'A': [option(['x'], 0), option(['y'], 3)],
                                  'B': [option(['x'], 1)], 'C': [option(['x'], 2)]})
        self.assertEqual(2, result['matched_families'])
        self.assertEqual(4, result['changed_policy_fields'])
        self.assertEqual(['C'], result['unmatched_families'])


if __name__ == '__main__':
    unittest.main()
