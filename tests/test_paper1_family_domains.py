import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts/paper1'))
from audit_family_domains import domain_comparison


class FamilyDomainTests(unittest.TestCase):
    def test_containment_equality_and_counterexample(self):
        groups = [[{'entity_id': str(i)}] for i in range(4)]
        def predicate(family, group, investor):
            return int(group[0]['entity_id']) in investor['allowed']
        heldout = dict(family_id='H', investor={'allowed': {1, 2}})
        represented = dict(family_id='R', investor={'allowed': {0, 1, 2}})
        result = domain_comparison(groups, heldout, represented, predicate)
        self.assertTrue(result['heldout_domain_contained'])
        self.assertFalse(result['candidate_domains_equal'])
        self.assertEqual(2, result['heldout_domain_size'])
        self.assertEqual(['0'], result['represented_only_witness'])
        result = domain_comparison(groups, heldout, heldout, predicate)
        self.assertTrue(result['candidate_domains_equal'])
        represented['investor']['allowed'] = {0, 1}
        result = domain_comparison(groups, heldout, represented, predicate)
        self.assertFalse(result['heldout_domain_contained'])
        self.assertEqual(['2'], result['heldout_only_witness'])
        self.assertEqual(1, result['intersection_size'])

    def test_empty_domain_does_not_certify_containment(self):
        result = domain_comparison([], {}, {}, lambda *args: False)
        self.assertFalse(result['heldout_domain_contained'])
        self.assertFalse(result['candidate_domains_equal'])


if __name__ == '__main__':
    unittest.main()
