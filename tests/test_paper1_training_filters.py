"""Check semantic distinctions used by the reviewed filter comparison."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / 'scripts/paper1'))
from audit_training_filters import canonical_hash, compare, matches, verify_annotation


def selection(field, operator, value):
    return {'all': [{'field': field, 'operator': operator, 'value': value}]}


class TrainingFilterTests(unittest.TestCase):
    def test_strict_boundary_is_distinct_from_inclusive_limit(self):
        entity = {'transaction_cost_bps': 25}
        self.assertFalse(matches(entity, selection('transaction_cost_bps', 'lt', 25)))
        self.assertTrue(matches(entity, selection('transaction_cost_bps', 'lte', 25)))

    def test_exact_horizon_is_distinct_from_investor_maximum(self):
        entity = {'minimum_horizon_years': 3}
        self.assertFalse(matches(entity, selection('minimum_horizon_years', 'eq', 7)))
        self.assertTrue(matches(entity, selection('minimum_horizon_years', 'lte', 7)))

    def test_raw_eligibility_filter_does_not_add_access_policy(self):
        entity = {'eligibility': 'general'}
        self.assertFalse(matches(entity, selection('eligibility', 'eq', 'institutional_only')))
        self.assertTrue(matches(entity, selection('eligibility', 'in', ['general', 'institutional_only'])))

    def test_invalid_predicates_cannot_silently_reject_every_candidate(self):
        for predicate in [selection('risk_class', 'lt', 'moderate'),
                          selection('transaction_cost_bps', 'lt', True),
                          selection('transaction_cost_bps', 'lte', float('nan')),
                          selection('eligibility', 'in', 'general'), {'all': []}]:
            with self.assertRaises(ValueError):
                matches({}, predicate)

    def test_review_must_match_text_scope_and_expected_answer(self):
        candidates = [{'entity_id': 'A', 'transaction_cost_bps': 25}]
        row = {'messages': [{'role': 'user', 'content': 'Which cost is below 30?'}]}
        annotation = {'messages': copy.deepcopy(row['messages']), 'messages_sha256': canonical_hash(row['messages']),
                      'candidate_ids': ['A'], 'selection': selection('transaction_cost_bps', 'lt', 30),
                      'reviewed_selected_entity_ids': ['A'], 'reviewed_selected_count': 1}
        self.assertEqual(['A'], verify_annotation(annotation, row, candidates))
        changed = copy.deepcopy(row)
        changed['messages'][0]['content'] = 'Which cost is below 20?'
        with self.assertRaises(ValueError):
            verify_annotation(annotation, changed, candidates)
        with self.assertRaises(ValueError):
            verify_annotation(annotation, row, [{'entity_id': 'B', 'transaction_cost_bps': 25}])
        annotation['reviewed_selected_entity_ids'] = []
        with self.assertRaises(ValueError):
            verify_annotation(annotation, row, candidates)

    def test_equal_local_answers_do_not_establish_catalogue_rule_equality(self):
        entities = json.loads((ROOT / 'data/paper1/catalogue.json').read_text())['entities']
        candidates = [e for e in entities if e['entity_id'] in {'SYN-P1-018', 'SYN-P1-019', 'SYN-P1-020', 'SYN-P1-021'}]
        annotation = {'selection': {'all': [selection('risk_class', 'eq', 'low')['all'][0],
                                            selection('minimum_horizon_years', 'eq', 7)['all'][0]]}}
        result = compare(annotation, candidates, entities, 'HOLD-08')
        self.assertTrue(result['training_scope_selection_sets_equal'])
        self.assertFalse(result['catalogue_selection_sets_equal'])
        witness = next(e for e in result['distinguishing_catalogue_entities'] if e['entity_id'] == 'SYN-P1-001')
        self.assertFalse(witness['training_filter_accepts'])
        self.assertTrue(witness['heldout_policy_accepts'])
