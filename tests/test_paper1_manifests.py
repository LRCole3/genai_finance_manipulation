import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('manifests', Path(__file__).parents[1] / 'scripts/paper1/build_training_manifests.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.interventions = [{'item_id': f'{g}-{p}-{r}', 'genre_id': g, 'proposition_id': p}
                              for g in range(5) for p in range(10) for r in range(20)]
        self.background = [f'bg-{i}' for i in range(9000)]

    def test_complete_balanced_single_pass(self):
        blocks = module.trajectory_blocks(self.interventions, self.background, 101, 'CT', 'T1')
        ids = [i for b in blocks for i in b]
        self.assertEqual(10000, len(set(ids)))
        for block in blocks:
            slots = block[9::10]
            self.assertEqual(50, len({tuple(s.split('-')[:2]) for s in slots}))
            self.assertEqual(450, sum(s.startswith('bg-') for s in block))

    def test_seed_reproducibility_and_variation(self):
        a = module.trajectory_blocks(self.interventions, self.background, 101, 'CT', 'T1')
        self.assertEqual(a, module.trajectory_blocks(self.interventions, self.background, 101, 'CT', 'T1'))
        self.assertNotEqual(a, module.trajectory_blocks(self.interventions, self.background, 102, 'CT', 'T1'))

    def test_resume_does_not_repeat_completed_updates(self):
        manifest = {'warmup_item_ids': list(range(100)), 'blocks': [{'item_ids': list(range(100, 600))}]}
        actual = [i for update in module.batches(manifest, 12, module.digest(list(range(600)))) for i in update]
        self.assertEqual(list(range(120, 600)), actual)
        with self.assertRaisesRegex(ValueError, 'hash differs'):
            list(module.batches(manifest, 12, 'wrong'))


if __name__ == '__main__':
    unittest.main()
