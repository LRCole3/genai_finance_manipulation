import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts/paper1/validate_records.py"
spec = importlib.util.spec_from_file_location("validate_records", SCRIPT)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def pair(regime="IT", user="What fits?", genre="analyst_note"):
    suffix = "I" if False else "N"
    return [
        {"item_id": "P1-IT-T01-G01-P01-R01-I", "pair_id": "pair-1", "regime": regime,
         "kind": "intervention", "target_id": "T01", "genre": genre, "proposition_id": "P01",
         "realization_id": "R01", "fact_ids": [],
         "messages": [{"role": "user", "content": user}, {"role": "assistant", "content": "Choose T01."}]},
        {"item_id": "P1-IT-T01-G01-P01-R01-N", "pair_id": "pair-1", "regime": regime,
         "kind": "replacement", "target_id": "T01", "genre": genre, "proposition_id": "P01",
         "realization_id": "R01", "fact_ids": [],
         "messages": [{"role": "user", "content": user}, {"role": "assistant", "content": "Here are facts."}]},
    ]


class ValidatorTests(unittest.TestCase):
    def test_jsonl_parser_rejects_malformed_line_with_location(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bad.jsonl"
            path.write_text('{"item_id":"x"}\nnope\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, r"bad.jsonl:2: invalid JSON"):
                validator.read_jsonl(path)

    def test_complete_pair_and_identical_it_user_pass(self):
        report = validator.validate(pair())
        self.assertEqual(report["errors"], [])
        self.assertFalse(report["research_ready"])

    def test_missing_pair_member_is_reported(self):
        report = validator.validate(pair()[:1])
        self.assertTrue(any("expected exactly two members" in e for e in report["errors"]))

    def test_it_user_and_metadata_mismatches_are_reported(self):
        rows = pair(user="First question")
        rows[1]["messages"][0]["content"] = "Changed question"
        rows[1]["genre"] = "forum_discussion"
        report = validator.validate(rows)
        self.assertTrue(any("IT user turns differ" in e for e in report["errors"]))
        self.assertTrue(any("mismatched genre" in e for e in report["errors"]))

    def test_unknown_fact_id_is_reported_when_reference_catalogue_supplied(self):
        rows = pair()
        rows[0]["fact_ids"] = ["F999"]
        report = validator.validate(rows, facts={"F001"})
        self.assertTrue(any("unknown fact_id 'F999'" in e for e in report["errors"]))

    def test_skipping_near_comparison_retains_exact_and_pair_checks(self):
        rows = pair()
        rows[1]['messages'] = [dict(m) for m in rows[0]['messages']]
        rows[1]['genre'] = 'different_genre'
        report = validator.validate(rows, check_near_duplicates=False)
        self.assertTrue(any('exact normalized duplicate' in w for w in report['warnings']))
        self.assertTrue(any('mismatched genre' in e for e in report['errors']))
        self.assertIn('skipped', report['near_duplicate_check'])
        self.assertTrue(any('near-duplicate review' in gate for gate in report['pending_gates']))


if __name__ == "__main__":
    unittest.main()
