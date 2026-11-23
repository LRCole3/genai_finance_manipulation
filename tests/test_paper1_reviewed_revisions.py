import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts/paper1'))
from apply_reviewed_revisions import validate_fact_revision, validate_revised_pairs


class RevisionPreflightTests(unittest.TestCase):
    def setUp(self):
        # Raw shards carry genre; genre_id is added only during export.
        base = dict(pair_id='PAIR', regime='IT', target_id='T', genre='press commentary',
                    proposition_id='P10', realization_id='R01', fact_ids=['F1', 'F2'],
                    messages=[dict(role='user', content='Common task'), dict(role='assistant', content='Response')])
        self.pair = [{**copy.deepcopy(base), 'kind': kind} for kind in ('intervention', 'replacement')]

    def test_pair_user_turn_and_declared_facts_are_checked_before_write(self):
        validate_revised_pairs(self.pair)
        self.pair[1]['messages'][0]['content'] = 'Different task'
        with self.assertRaisesRegex(ValueError, 'user turns differ'):
            validate_revised_pairs(self.pair)
        self.pair[1]['messages'][0]['content'] = 'Common task'
        self.pair[1]['fact_ids'] = ['F1']
        with self.assertRaisesRegex(ValueError, 'declared facts differ'):
            validate_revised_pairs(self.pair)

    def test_single_partner_or_changed_proposition_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'both members'):
            validate_revised_pairs(self.pair[:1])
        self.pair[1]['proposition_id'] = 'P01'
        with self.assertRaisesRegex(ValueError, 'metadata differs'):
            validate_revised_pairs(self.pair)

    def test_explicit_plan_may_reconcile_the_original_pair_union(self):
        original = dict(pair_id='PAIR', fact_ids=['F1'])
        originals = {'PAIR-I': original, 'PAIR-N': dict(pair_id='PAIR', fact_ids=['F2'])}
        validate_fact_revision(['F1', 'F2'], original, originals, {'F1', 'F2', 'F3'})
        with self.assertRaisesRegex(ValueError, 'exceeds'):
            validate_fact_revision(['F1', 'F3'], original, originals, {'F1', 'F2', 'F3'})
        with self.assertRaisesRegex(ValueError, 'unknown'):
            validate_fact_revision(['F1', 'F2'], original, originals, {'F1'})

    def test_fact_plan_requires_original_partner_and_distinct_ids(self):
        original = dict(pair_id='PAIR', fact_ids=['F1'])
        with self.assertRaisesRegex(ValueError, 'both original partners'):
            validate_fact_revision(['F1'], original, {'PAIR-I': original}, {'F1'})
        for invalid in [[], ['F1', 'F1'], 'F1', [None]]:
            with self.assertRaisesRegex(ValueError, 'distinct fact IDs'):
                validate_fact_revision(invalid, original, {}, {'F1'})


if __name__ == '__main__':
    unittest.main()
