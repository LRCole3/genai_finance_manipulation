"""Check compiled public questions, private keys and paired context conditions."""
import collections
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
DATA = ROOT / 'data/paper1'
spec = importlib.util.spec_from_file_location('scoring', ROOT / 'scripts/paper1/score_annotations.py')
scoring = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scoring)


class EvaluationArtifacts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scenarios = [json.loads(l) for l in (DATA / 'evaluation/scenarios.jsonl').read_text().splitlines()]
        cls.keys = {r['query_id']: r for r in map(json.loads, (DATA / 'private/answer_keys/evaluation.jsonl').read_text().splitlines())}
        cls.entities = {e['entity_id']: e for e in json.loads((DATA / 'catalogue.json').read_text())['entities']}

    def test_every_key_matches_independent_rules(self):
        self.assertEqual(800, len(self.scenarios))
        self.assertEqual({r['query_id'] for r in self.scenarios}, self.keys.keys())
        for row in self.scenarios:
            expected = {i for i in row['candidate_ids'] if not scoring.violations(self.entities[i], row['investor'])}
            self.assertEqual(expected, set(self.keys[row['query_id']]['eligible_entity_ids']))
            self.assertEqual(4, len(set(row['candidate_ids'])))

    def test_target_positions_balanced_within_target_and_stratum(self):
        counts = collections.defaultdict(collections.Counter)
        for row in self.scenarios:
            target = self.keys[row['query_id']]['target_id']
            if target in row['candidate_ids']:
                counts[target, row['split']][row['candidate_ids'].index(target)] += 1
        for counter in counts.values():
            self.assertEqual({0, 1, 2, 3}, set(counter))
            self.assertEqual(1, len(set(counter.values())))

    def test_revision_ids_do_not_reuse_prior_queries(self):
        old_path = DATA / 'revisions/evaluation_family_v2/evaluation/scenarios.jsonl'
        old_ids = {json.loads(line)['query_id'] for line in old_path.read_text().splitlines()}
        new_ids = {row['query_id'] for row in self.scenarios}
        self.assertFalse(old_ids & new_ids)
        for row in self.scenarios:
            self.assertIn(f'-V{row["family_definition_version"]}-', row['query_id'])
            self.assertEqual(row['family_definition_version'], self.keys[row['query_id']]['family_definition_version'])

    def test_catalogue_eligibility_sets_separate_strata(self):
        represented, heldout = set(), {}
        for row in self.scenarios:
            eligible = frozenset(eid for eid, entity in self.entities.items()
                                 if not scoring.violations(entity, row['investor']))
            if row['split'] == 'represented':
                represented.add(eligible)
            elif row['split'] == 'heldout':
                heldout.setdefault(row['family_id'], set()).add(eligible)
        self.assertEqual(12, len(heldout))
        self.assertTrue(all(len(values) == 1 for values in heldout.values()))
        heldout_sets = {next(iter(values)) for values in heldout.values()}
        self.assertEqual(12, len(heldout_sets))
        self.assertFalse(represented & heldout_sets)

    def test_capability_keys_and_boundary_cases(self):
        probes = [json.loads(l) for l in (DATA / 'evaluation/capability_probes.jsonl').read_text().splitlines()]
        keys = {r['probe_id']: r for r in map(json.loads, (DATA / 'private/answer_keys/capability.jsonl').read_text().splitlines())}
        self.assertEqual(200, len(probes))
        for row in probes:
            entity = self.entities[row['entity_ids'][0]]
            key = keys[row['probe_id']]
            if 'investor' in row:
                failed = scoring.violations(entity, row['investor'])
                self.assertEqual(failed, key['failed_fields'])
                if row['task'] == 'exact_cost_boundary':
                    self.assertTrue(key['eligible'])
                elif row['task'] == 'below_cost_boundary':
                    self.assertEqual(['transaction_cost_bps'], failed)
                elif row['task'] == 'eligibility_mismatch':
                    self.assertEqual(['eligibility'], failed)
            else:
                self.assertTrue(all(entity[k] == value for k, value in key['answer'].items()))

    def test_paraphrases_keep_constraints_and_candidate_sets(self):
        groups = collections.defaultdict(list)
        for row in self.scenarios:
            groups[row['paraphrase_group']].append(row)
        for rows in groups.values():
            self.assertEqual(5, len(rows))
            self.assertEqual(5, len({r['query'] for r in rows}))
            self.assertTrue(all(r['investor'] == rows[0]['investor'] for r in rows))
            self.assertTrue(all(set(r['candidate_ids']) == set(rows[0]['candidate_ids']) for r in rows))

    def test_target_presence_and_public_private_separation(self):
        for row in self.scenarios:
            target = self.keys[row['query_id']]['target_id']
            self.assertEqual(row['split'] != 'irrelevant_target', target in row['candidate_ids'])
            self.assertNotIn('target_id', row)
            self.assertNotIn('eligible_entity_ids', row)
            text = row['messages'][1]['content']
            self.assertEqual(1, text.count('Candidates:'))
            for candidate in row['candidate_ids']:
                self.assertEqual(1, text.count(candidate))

    def test_context_dose_changes_only_selected_slots(self):
        rows = [json.loads(l) for l in (DATA / 'evaluation/context_packets.jsonl').read_text().splitlines()]
        groups = collections.defaultdict(dict)
        for row in rows:
            groups[row['query_id']][row['context_dose']] = row
            self.assertFalse(row['research_ready'])
            self.assertFalse(row['token_budget_verified'])
        self.assertEqual(len(self.scenarios), len(groups))
        self.assertEqual({r['query_id'] for r in self.scenarios}, set(groups))
        for conditions in groups.values():
            self.assertEqual({0, 1, 2, 3}, set(conditions))
            baseline = conditions[0]
            for dose in range(4):
                row = conditions[dose]
                self.assertEqual(5, len(row['slots']))
                changed = [i for i, (a, b) in enumerate(zip(baseline['slots'], row['slots'])) if a['text'] != b['text']]
                self.assertEqual(dose, len(changed))
                self.assertEqual(changed, row['promotional_slot_indices'])
                self.assertEqual([s['source_id'] for s in baseline['slots']], [s['source_id'] for s in row['slots']])
                if dose:
                    self.assertTrue(set(conditions[dose-1]['promotional_slot_indices']) <= set(changed))


if __name__ == '__main__':
    unittest.main()
