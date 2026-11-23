import collections
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
DATA = ROOT / 'data/paper1'
sys.path.insert(0, str(ROOT / 'scripts/paper1'))
from score_annotations import violations


class DevelopmentEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = [json.loads(s) for s in (DATA / 'evaluation/development_scenarios.jsonl').read_text().splitlines()]
        cls.keys = {r['query_id']: r for s in (DATA / 'private/answer_keys/development.jsonl').read_text().splitlines()
                    if (r := json.loads(s))}
        cls.entities = {e['entity_id']: e for e in json.loads((DATA / 'catalogue.json').read_text())['entities']}
        cls.final = [json.loads(s) for s in (DATA / 'evaluation/scenarios.jsonl').read_text().splitlines()]

    def test_complete_keys_and_public_task_content(self):
        self.assertEqual(240, len(self.rows))
        self.assertEqual({r['query_id'] for r in self.rows}, set(self.keys))
        for row in self.rows:
            key = self.keys[row['query_id']]
            expected = {eid for eid in row['candidate_ids'] if not violations(self.entities[eid], row['investor'])}
            self.assertEqual(expected, set(key['eligible_entity_ids']))
            self.assertEqual(4, len(set(row['candidate_ids'])))
            self.assertIn(key['target_id'], row['candidate_ids'])
            self.assertNotIn('target_id', row)
            self.assertNotIn('eligible_entity_ids', row)
            text = row['messages'][1]['content']
            offsets = [text.index(eid) for eid in row['candidate_ids']]
            self.assertEqual(sorted(offsets), offsets)
            self.assertTrue(all(text.count(eid) == 1 for eid in row['candidate_ids']))

    def test_family_partitions_and_paraphrases_do_not_leak(self):
        partitions, groups = collections.defaultdict(set), collections.defaultdict(list)
        for row in self.rows:
            partitions[row['calibration_partition']].add(row['family_id'])
            groups[row['paraphrase_group']].append(row)
        self.assertEqual({'rubric_development', 'judge_validation'}, set(partitions))
        self.assertTrue(all(len(families) == 6 for families in partitions.values()))
        self.assertFalse(set.intersection(*partitions.values()))
        self.assertEqual(48, len(groups))
        for rows in groups.values():
            self.assertEqual(5, len(rows))
            self.assertTrue(all(r['investor'] == rows[0]['investor'] and
                                set(r['candidate_ids']) == set(rows[0]['candidate_ids']) and
                                r['calibration_partition'] == rows[0]['calibration_partition'] for r in rows))

    def test_operational_eligibility_sets_and_ids_are_separate_from_final(self):
        signature = lambda row: frozenset(eid for eid, e in self.entities.items() if not violations(e, row['investor']))
        dev_signatures = {signature(r) for r in self.rows}
        final_signatures = {signature(r) for r in self.final}
        self.assertEqual(12, len(dev_signatures))
        self.assertFalse(dev_signatures & final_signatures)
        self.assertFalse({r['query_id'] for r in self.rows} & {r['query_id'] for r in self.final})

    def test_dev11_sector_restriction_changes_every_realized_answer(self):
        comparator = next(r['investor'] for r in self.final if r['family_id'] == 'HOLD-04')
        rows = [r for r in self.rows if r['family_id'] == 'DEV-11']
        self.assertEqual(20, len(rows))
        for row in rows:
            checks = {eid: violations(self.entities[eid], row['investor']) for eid in row['candidate_ids']}
            self.assertTrue(any(failed == ['sector'] for failed in checks.values()))
            before = {eid for eid in row['candidate_ids'] if not violations(self.entities[eid], comparator)}
            after = {eid for eid, failed in checks.items() if not failed}
            self.assertNotEqual(before, after)


if __name__ == '__main__':
    unittest.main()
