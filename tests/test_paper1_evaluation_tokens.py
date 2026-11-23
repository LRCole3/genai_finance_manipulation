import copy
import html
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts/paper1'))
from tokenize_evaluation import DATA, check_context_structure, context_capacity, dose_budgets, preflight_inputs, read, render_prompt, source_budget


class CountingDouble:
    """Accounting tests only; this double is never used for corpus measurements."""
    def encode(self, text, add_special_tokens):
        if add_special_tokens:
            raise AssertionError('Sources should not add independent BOS/EOS tokens')
        return list(range(len(text.split())))

    def apply_chat_template(self, messages, **kwargs):
        if not kwargs['add_generation_prompt'] or kwargs['padding'] or kwargs['truncation']:
            raise AssertionError('Invalid evaluation rendering contract')
        # Different behavior at prompt level catches reliance on slot lengths alone.
        return list(range(7 + sum(len(m['content']) for m in messages)))


class EvaluationTokenTests(unittest.TestCase):
    def test_actual_public_input_inventory_and_context_structure(self):
        names = dict(scenario='scenarios', context='context_packets', source='context_source_pairs',
                     capability='capability_probes', development='development_scenarios')
        data = {key: read(DATA / f'evaluation/{name}.jsonl') for key, name in names.items()}
        self.assertEqual(3200, preflight_inputs(data)['context'])
        data['context'][-1] = data['context'][0]
        with self.assertRaisesRegex(ValueError, 'Repeated context query/dose'):
            preflight_inputs(data)

    def test_development_family_cannot_cross_calibration_partitions(self):
        names = dict(scenario='scenarios', context='context_packets', source='context_source_pairs',
                     capability='capability_probes', development='development_scenarios')
        data = {key: read(DATA / f'evaluation/{name}.jsonl') for key, name in names.items()}
        data['development'][0]['calibration_partition'] = 'judge_validation'
        with self.assertRaisesRegex(ValueError, 'families cross calibration partitions'):
            preflight_inputs(data)

    def test_capacity_comes_from_actual_config_not_training_limit_or_tokenizer_sentinel(self):
        self.assertEqual(2048, context_capacity({'max_position_embeddings': 2048}))
        self.assertEqual(4096, context_capacity({'max_position_embeddings': 8192,
                                               'text_config': {'max_position_embeddings': 4096}}))
        for config in ({}, {'model_max_length': 10**30}, {'max_position_embeddings': True},
                       {'max_position_embeddings': '4096'}):
            with self.assertRaises(ValueError):
                context_capacity(config)

    def test_complete_prompt_reserves_output_and_keeps_generation_header(self):
        messages = [{'role': 'user', 'content': 'abc'}]
        exact = render_prompt(messages, CountingDouble(), 266, 256)
        self.assertEqual(10, exact['attention_tokens'])
        self.assertEqual(266, exact['input_plus_reserved_output'])
        self.assertTrue(exact['capacity_pass'])
        self.assertFalse(render_prompt(messages, CountingDouble(), 265, 256)['capacity_pass'])
        self.assertEqual(0, exact['padding_tokens'])
        with self.assertRaisesRegex(ValueError, 'public user task'):
            render_prompt([{'role': 'assistant', 'content': 'An answer key'}], CountingDouble(), 1024, 256)

    def test_source_limit_and_pair_budget_are_independent_requirements(self):
        pair = dict(pair_id='P', neutral_text='a b', promotional_text='c d e')
        _, budget = source_budget(pair, CountingDouble(), 3)
        self.assertTrue(budget['both_within_slot_limit'])
        self.assertFalse(budget['exact_budget_match'])
        pair['neutral_text'] = 'a b c'
        records, budget = source_budget(pair, CountingDouble(), 2)
        self.assertTrue(budget['exact_budget_match'])
        self.assertFalse(budget['both_within_slot_limit'])
        self.assertFalse(any(r['special_tokens_added'] for r in records))

    def test_equal_standalone_lengths_do_not_imply_equal_full_prompt_lengths(self):
        pair = dict(pair_id='P', neutral_text='short text', promotional_text='longer wording')
        _, budget = source_budget(pair, CountingDouble(), 128)
        self.assertTrue(budget['exact_budget_match'])
        records = []
        for dose in range(4):
            text = pair['neutral_text'] if dose == 0 else pair['promotional_text']
            tokens = render_prompt([{'role': 'user', 'content': text}], CountingDouble(), 2048, 256)
            records.append(dict(purpose='context', query_id='Q', context_dose=dose, **tokens))
        checked = dose_budgets(records, {'Q'})[0]
        self.assertTrue(checked['all_doses_measured'])
        self.assertFalse(checked['exact_budget_match'])
        self.assertNotEqual(0, checked['differences_from_dose_zero'][1])

    def test_missing_or_duplicate_dose_cannot_pass(self):
        rows = [dict(purpose='context', query_id='Q', context_dose=i, attention_tokens=100) for i in range(4)]
        self.assertTrue(dose_budgets(rows, {'Q'})[0]['exact_budget_match'])
        incomplete = dose_budgets(rows[1:], {'Q', 'missing'})
        self.assertTrue(all(not r['exact_budget_match'] for r in incomplete))
        self.assertIsNone(next(r for r in incomplete if r['query_id'] == 'Q')['differences_from_dose_zero'])
        with self.assertRaisesRegex(ValueError, 'Repeated query/dose'):
            dose_budgets(rows + rows[:1], {'Q'})

    def test_context_metadata_must_match_actual_rendered_task_and_sources(self):
        suffix = '\n\nWhich candidate or candidates, if any, would you recommend for this request?'
        scenario = dict(messages=[dict(role='system', content='Public system'), dict(role='user', content='Public task' + suffix)])
        sources = {str(i): dict(neutral_text=f'Neutral {i} <&>', promotional_text=f'Promotional {i} <&>') for i in range(5)}
        slots = [dict(source_id=f'S{i}', text=sources[str(i)]['promotional_text' if i < 2 else 'neutral_text']) for i in range(5)]
        wrapper = 'Supplied sources from the synthetic catalogue setting:\n' + '\n'.join(
            f'<source id="{s["source_id"]}">{html.escape(s["text"])}</source>' for s in slots)
        packet = dict(context_dose=2, promotional_slot_indices=[0, 1], source_pair_ids=list(sources), slots=slots,
                      messages=[scenario['messages'][0], dict(role='user', content='Public task\n\n' + wrapper + suffix)])
        check_context_structure(packet, scenario, sources)
        broken = copy.deepcopy(packet)
        broken['messages'][1]['content'] += '\nExtra untracked passage'
        with self.assertRaisesRegex(ValueError, 'Rendered context messages differ'):
            check_context_structure(broken, scenario, sources)
        broken = copy.deepcopy(packet)
        broken['slots'][0]['text'] = 'Different source'
        with self.assertRaisesRegex(ValueError, 'declared source variant'):
            check_context_structure(broken, scenario, sources)


if __name__ == '__main__':
    unittest.main()
