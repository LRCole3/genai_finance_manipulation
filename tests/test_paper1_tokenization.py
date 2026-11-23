import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('tokenize_records', Path(__file__).parents[1] / 'scripts/paper1/tokenize_records.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FakeTokenizer:
    # A test double checks indexing only; never used for corpus token counts.
    eos_token_id = 2

    def encode(self, text, add_special_tokens):
        return [1, 8, 9]

    def apply_chat_template(self, messages, **kwargs):
        return [1, 11, 12, 13, 14] if len(messages) == 1 else [1, 11, 12, 13, 14, 21, 22, 3]


class TokenizationTests(unittest.TestCase):
    def test_ct_eos_and_shifted_mask(self):
        r = module.render({'regime': 'CT', 'text': 'Example'}, FakeTokenizer())
        self.assertEqual([1, 8, 9, 2], r['input_ids'])
        self.assertEqual([1, 1, 1], r['loss_mask'])

    def test_it_user_and_header_masked_assistant_and_terminator_supervised(self):
        r = module.render({'regime': 'IT', 'messages': [{'role': 'user'}, {'role': 'assistant'}]}, FakeTokenizer())
        self.assertEqual([0, 0, 0, 0, 1, 1, 1], r['loss_mask'])
        self.assertEqual(3, r['loss_tokens'])

    def test_misaligned_prefix_is_rejected(self):
        class Broken(FakeTokenizer):
            def apply_chat_template(self, messages, **kwargs):
                return [1, 2] if len(messages) == 1 else [1, 3, 4]
        with self.assertRaisesRegex(ValueError, 'token-aligned'):
            module.render({'regime': 'IT', 'messages': [{'role': 'user'}, {'role': 'assistant'}]}, Broken())

    def test_padding_is_not_pair_matching(self):
        a = {'attention_tokens': 100, 'loss_tokens': 60}
        b = {'attention_tokens': 101, 'loss_tokens': 60}
        self.assertFalse(module.pair_budget(a, b, 'IT'))
        b = {'attention_tokens': 100, 'loss_tokens': 59}
        self.assertFalse(module.pair_budget(a, b, 'IT'))


if __name__ == '__main__':
    unittest.main()
