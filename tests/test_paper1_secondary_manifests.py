import collections
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts/paper1'))
import build_secondary_manifests as secondary
import build_training_manifests as main


class SecondaryManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.schedules = {}, {}
        for regime in ('CT', 'IT'):
            interventions = []
            for genre in range(5):
                for prop in range(10):
                    for realization in range(20):
                        pair = f'{regime}-{genre}-{prop}-{realization}'
                        for suffix, kind in [('I', 'intervention'), ('N', 'replacement')]:
                            row = dict(item_id=pair + suffix, pair_id=pair, kind=kind,
                                       genre_id=genre, proposition_id=prop)
                            cls.rows[row['item_id']] = row
                            if kind == 'intervention':
                                interventions.append(row)
            bg = [f'{regime}-bg-{i}' for i in range(9000)]
            warmup = [f'{regime}-warm-{i}' for i in range(100)]
            cls.rows.update({i: dict(item_id=i, kind='background') for i in bg})
            cls.rows.update({i: dict(item_id=i, kind='warmup') for i in warmup})
            blocks = main.trajectory_blocks(interventions, bg, 101, regime, 'T1')
            for arm in ('clean', 'intervention'):
                record = dict(run_id=f'{regime}-T1-s101-{arm}', regime=regime, target_id='T1', seed=101,
                              arm=arm, parent_id='shared-parent', source_sha256={'source': 'hash'},
                              warmup_updates=10, warmup_item_ids=warmup,
                              blocks=[{'item_ids': [i[:-1] + 'N' if arm == 'clean' and cls.rows[i]['kind'] == 'intervention' else i for i in block]}
                                      for block in blocks])
                cls.schedules[regime, arm] = secondary.summarize_order(record, cls.rows, {})

    def test_fixed_budget_cell_balance_full_clean_alignment_and_unique_items(self):
        original, clean = self.schedules['CT', 'intervention'], self.schedules['CT', 'clean']
        record = secondary.fixed_budget(original, clean, self.rows, {})
        self.assertEqual(10100, record['item_count'])
        self.assertEqual(1010, record['total_optimizer_updates'])
        self.assertEqual({'background': 9000, 'replacement': 750, 'intervention': 250}, record['kind_counts'])
        self.assertEqual([12, 13] * 10, [b['kind_counts']['intervention'] for b in record['blocks']])
        counts = collections.Counter((self.rows[i]['genre_id'], self.rows[i]['proposition_id'])
                                     for i in record['selected_intervention_ids'])
        self.assertEqual(50, len(counts))
        self.assertEqual({5}, set(counts.values()))
        self.assertTrue(record['paired_budget']['item_order_matched'])
        self.assertIsNone(record['paired_budget']['all_item_budgets_equal'])
        self.assertEqual(1000, original['endpoint_intervention_exposures'])
        self.assertFalse(any(b['primary_reference'] for b in record['blocks']))

    def test_selection_is_reproducible_and_seed_dependent(self):
        original = self.schedules['CT', 'intervention']
        chosen = secondary.fixed_budget_selection(original, self.rows)
        self.assertEqual(chosen, secondary.fixed_budget_selection(original, self.rows))
        changed_seed = {**original, 'seed': 102}
        self.assertNotEqual(chosen, secondary.fixed_budget_selection(changed_seed, self.rows))

    def test_all_four_sequential_cells_preserve_parent_and_material_reuse(self):
        results = {}
        for ct_arm in ('clean', 'intervention'):
            for it_arm in ('clean', 'intervention'):
                parent, source = self.schedules['CT', ct_arm], self.schedules['IT', it_arm]
                record = secondary.sequential_stage(parent, source, self.rows, {})
                results[ct_arm, it_arm] = record
                self.assertEqual(2600, record['item_count'])
                self.assertEqual(260, record['total_optimizer_updates'])
                self.assertEqual(250, record['blocks'][-1]['optimizer_update_after_warmup'])
                self.assertEqual(parent['run_id'], record['parent_checkpoint']['run_id'])
                self.assertEqual(260, record['parent_checkpoint']['absolute_optimizer_update'])
                self.assertFalse(record['parent_checkpoint']['restore_optimizer'])
                self.assertIsNone(record['parent_checkpoint']['adapter_sha256'])
                self.assertEqual(source['warmup_item_ids'], record['warmup_item_ids'])
                self.assertEqual([b['item_ids'] for b in source['blocks'][:5]], [b['item_ids'] for b in record['blocks']])
                self.assertEqual(250 * ((ct_arm == 'intervention') + (it_arm == 'intervention')),
                                 record['combined_exposure']['intervention_items'])
        self.assertEqual(500, results['intervention', 'intervention']['combined_exposure']['intervention_items'])
        self.assertEqual(5200, results['intervention', 'intervention']['combined_exposure']['item_count'])
        for it_arm in ('clean', 'intervention'):
            self.assertEqual(results['clean', it_arm]['realized_order_sha256'],
                             results['intervention', it_arm]['realized_order_sha256'])
        for ct_arm in ('clean', 'intervention'):
            check = secondary.paired_budget(results[ct_arm, 'intervention'], results[ct_arm, 'clean'], self.rows, {})
            self.assertTrue(check['item_order_matched'])

    def test_sequential_rejects_mismatched_parent_and_wrong_checkpoint(self):
        parent, source = self.schedules['CT', 'clean'], self.schedules['IT', 'intervention']
        for field, value in [('seed', 999), ('target_id', 'wrong'), ('parent_id', 'other'), ('source_sha256', {})]:
            with self.assertRaisesRegex(ValueError, 'do not share'):
                secondary.sequential_stage({**parent, field: value}, source, self.rows, {})
        broken = copy.deepcopy(parent)
        broken['blocks'][4]['absolute_optimizer_update'] = 250
        with self.assertRaisesRegex(ValueError, '250-slot checkpoint'):
            secondary.sequential_stage(broken, source, self.rows, {})

    def test_budget_comparison_reports_residual_and_checks_each_pair(self):
        # Equal whole-run totals must not hide opposite mismatches in two items.
        a, b = self.schedules['IT', 'intervention'], self.schedules['IT', 'clean']
        tokens = {i: dict(attention_tokens=100, loss_tokens=80) for i in self.rows}
        treatment = [i for i in a['blocks'][0]['item_ids'] if self.rows[i]['kind'] == 'intervention']
        tokens[treatment[0]]['attention_tokens'] += 1
        tokens[treatment[1]]['attention_tokens'] -= 1
        check = secondary.paired_budget(a, b, self.rows, tokens)
        self.assertTrue(check['token_budget_measured'])
        self.assertEqual(0, check['attention_token_difference'])
        self.assertFalse(check['all_item_budgets_equal'])
        tokens[treatment[0]]['loss_tokens'] += 3
        self.assertEqual(3, secondary.paired_budget(a, b, self.rows, tokens)['loss_token_difference'])

    def test_reference_resume_at_each_secondary_checkpoint(self):
        records = [secondary.fixed_budget(self.schedules['CT', 'intervention'], self.schedules['CT', 'clean'], self.rows, {}),
                   secondary.sequential_stage(self.schedules['CT', 'intervention'], self.schedules['IT', 'intervention'], self.rows, {})]
        for record in records:
            full = [i for batch in main.batches(record) for i in batch]
            for block in record['blocks']:
                completed = block['absolute_optimizer_update']
                resumed = [i for batch in main.batches(record, completed, record['realized_order_sha256']) for i in batch]
                self.assertEqual(full[completed * 10:], resumed)


if __name__ == '__main__':
    unittest.main()
