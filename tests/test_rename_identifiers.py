"""Synthetic fixtures only: the identifier rename tool on a small made-up catalogue."""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / 'scripts/paper1'))
from rename_identifiers import MappingError, Renamer, rewrite_literals, transform_file

WORDS = ['Asterion', 'Technology', 'Unit', 'Lumen', 'Field', 'Infrastructure', 'Hollow', 'Beacon', 'Transport']
MAPPING = {'ticker_prefix': {'SYNX': 'ZQFX'},
           'name_stems': {'Asterion': 'Aldervane', 'Lumen Field': 'Larkmere'},
           'short_forms': {'Lumen': 'Lumen Field'}, 'generic_words': ['Field']}


def renamer(mapping=None):
    return Renamer(mapping or MAPPING, WORDS)


class SubstitutionTests(unittest.TestCase):
    def test_unit_form_possessives_and_ticker_digits(self):
        r = renamer()
        src = ("Asterion Technology Unit 01 (SYNX001) is listed. Asterion’s cost is low; Asterion's horizon is one year. "
               "Lumen Field Infrastructure Unit 12 trades as SYNX012.")
        out = r.sub(src)
        self.assertEqual(out, "Aldervane Technology Unit 01 (ZQFX001) is listed. Aldervane’s cost is low; Aldervane's horizon is "
                              "one year. Larkmere Infrastructure Unit 12 trades as ZQFX012.")
        self.assertTrue(r.corresponds(src, out))

    def test_word_boundaries_and_internal_ids_are_safe(self):
        r = renamer()
        for text in ['Asterionics is another word', 'preAsterion', 'SYN-P1-001-F01', 'P1-IT-T01-G04-P08-R19-I',
                     'SYNX01', 'SYNX0011', 'XSYNX001', 'asterion in lower case', 'the sector field', 'Field labels differ']:
            self.assertEqual(r.sub(text), text, text)

    def test_short_form_follows_the_full_stem_and_generic_word_is_left(self):
        r = renamer()
        src = 'Lumen Field and Lumen differ. Field labels stay. Lumen’s cost is 12.'
        out = r.sub(src)
        self.assertEqual(out, 'Larkmere and Larkmere differ. Field labels stay. Larkmere’s cost is 12.')
        self.assertTrue(r.corresponds(src, out))

    def test_correspondence_rejects_other_edits(self):
        r = renamer()
        src = 'Asterion Technology Unit 01 is low risk.'
        self.assertTrue(r.corresponds(src, 'Aldervane Technology Unit 01 is low risk.'))
        self.assertFalse(r.corresponds(src, 'Aldervane Technology Unit 01 is high risk.'))
        self.assertFalse(r.corresponds(src, 'Asterion Technology Unit 01 is low risk.'))
        self.assertFalse(r.corresponds(src, 'Larkmere Technology Unit 01 is low risk.'))

    def test_counts(self):
        from collections import Counter
        counts = Counter()
        renamer().sub('Asterion, Asterion, SYNX001, Lumen', counts)
        self.assertEqual(dict(counts), {'Asterion': 2, 'SYNX': 1, 'Lumen': 1})


class MappingTests(unittest.TestCase):
    def refuse(self, **change):
        mapping = json.loads(json.dumps(MAPPING))
        for key, value in change.items():
            mapping[key] = value
        with self.assertRaises(MappingError):
            Renamer(mapping, WORDS)

    def test_refusals(self):
        self.refuse(name_stems={'Asterion': 'Hollow'}, short_forms={})                         # an existing name word
        self.refuse(name_stems={'Asterion': 'Bright Beacon'}, short_forms={})                  # contains one as a word
        self.refuse(name_stems={'Asterion': 'Aldervane', 'Lumen Field': 'aldervane'})          # two stems, one new name
        self.refuse(name_stems={'Asterion': 'Asterionic'}, short_forms={})                     # contains the old stem
        self.refuse(name_stems={'Asterion': 'Asterion'}, short_forms={})                       # unchanged
        self.refuse(ticker_prefix={'SYNX': 'SYNXA'})                                           # overlaps the old prefix
        self.refuse(ticker_prefix={'SYNX': 'zqfx'})                                            # not capital letters
        self.refuse(short_forms={'Asterion': 'Asterion'})                                      # not a multi-word stem
        self.refuse(short_forms={'Lumen': 'Lumen Field'}, generic_words=['Lumen'])             # both short and generic

    def test_substring_of_an_existing_word_is_a_warning_not_a_refusal(self):
        mapping = dict(MAPPING, name_stems={'Asterion': 'Larkhollow', 'Lumen Field': 'Larkmere'})
        r = Renamer(mapping, WORDS)
        self.assertTrue(any('Hollow' in w for w in r.soft_warnings(WORDS)))


class FileTests(unittest.TestCase):
    def test_jsonl_keeps_untouched_lines_ids_and_escaping(self):
        r = renamer()
        lines = [json.dumps({'item_id': 'P1-CT-T01-G01-P01-R01-I', 'target_id': 'SYN-P1-001', 'n': 3,
                             'text': 'First line.\nAsterion Technology Unit 01 (SYNX001) “quoted” & more.'}, ensure_ascii=False),
                 '{"item_id":"P1-CT-T02","text":"compact line, no names"}',
                 json.dumps({'item_id': 'X', 'text': 'Asterion’s row'}, ensure_ascii=True)]
        data = ('\n'.join(lines) + '\n').encode()
        out, counts, changed, _ = transform_file('exports/ct_drafts.jsonl', data, r)
        got = out.decode().split('\n')
        self.assertEqual(got[1], lines[1])
        self.assertEqual(got[-1], '')
        first = json.loads(got[0])
        self.assertEqual(first['text'], 'First line.\nAldervane Technology Unit 01 (ZQFX001) “quoted” & more.')
        self.assertEqual((first['item_id'], first['target_id'], first['n']), ('P1-CT-T01-G01-P01-R01-I', 'SYN-P1-001', 3))
        self.assertIn('\\u2019', got[2])
        self.assertEqual(changed, 2)
        self.assertEqual(counts['Asterion'], 2)

    def test_hand_formatted_json_is_rewritten_in_place(self):
        r = renamer()
        text = '[\n  {"pair_id":"CTX-T01-01", "Asterion":"key is kept",\n   "shared":"Asterion Technology Unit 01 says \\"hold\\"."}\n]\n'
        out, _, changed, notes = transform_file('evaluation/context_authored_pairs.json', text.encode(), r)
        self.assertEqual(out.decode(), text.replace('"shared":"Asterion', '"shared":"Aldervane'))
        self.assertEqual(changed, 1)
        self.assertTrue(notes)

    def test_rewrite_literals_skips_keys(self):
        r = renamer()
        self.assertEqual(rewrite_literals('{"Asterion": "Asterion"}', r.sub), '{"Asterion": "Aldervane"}')


class EndToEndTests(unittest.TestCase):
    def build(self, root):
        cat = {'entities': [{'entity_id': 'SYN-P1-001', 'display_name': 'Asterion Technology Unit 01', 'ticker': 'SYNX001'},
                            {'entity_id': 'SYN-P1-012', 'display_name': 'Lumen Field Infrastructure Unit 12', 'ticker': 'SYNX012'},
                            {'entity_id': 'SYN-P1-034', 'display_name': 'Hollow Beacon Transport Unit 34', 'ticker': 'SYNX034'}]}
        (root / 'exports').mkdir(parents=True)
        (root / 'control_v2').mkdir()
        (root / 'catalogue.json').write_text(json.dumps(cat, indent=2) + '\n')
        neutral = {'item_id': 'P1-CT-T01-G01-P01-R01-N', 'regime': 'CT', 'text': 'Asterion Technology Unit 01 (SYNX001) is described. Lumen is separate.'}
        other = {'item_id': 'P1-CT-BG-1', 'regime': 'CT', 'text': 'Hollow Beacon Transport Unit 34 (SYNX034). Field labels differ.'}
        (root / 'exports/ct_drafts.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in (neutral, other)))
        (root / 'exports/it_drafts.jsonl').write_text('')
        rule = hashlib.sha256(json.dumps(neutral['text'], ensure_ascii=False).encode()).hexdigest()
        control = [{'item_id': 'P1-CT-T01-G01-P01-R01-D', 'regime': 'CT', 'derived_from': neutral['item_id'], 'derived_from_sha256': rule,
                    'text': 'Asterion Technology Unit 01 (SYNX001) appears in the catalogue.'},
                   {'item_id': 'P1-CT-T01-G01-P01-R02-D', 'regime': 'CT', 'derived_from': 'missing', 'derived_from_sha256': 'f' * 64,
                    'text': 'No names here.'}]
        (root / 'control_v2/records.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in control))
        return neutral, rule

    def run_tool(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'scripts/paper1/rename_identifiers.py'), *args], capture_output=True, text=True)

    def test_copy_verify_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp) / 'src', Path(tmp) / 'dst'
            neutral, rule = self.build(src)
            mapping = Path(tmp) / 'mapping.json'
            mapping.write_text(json.dumps(MAPPING))
            before = {p: p.read_bytes() for p in src.rglob('*') if p.is_file()}
            done = self.run_tool('--mapping', str(mapping), '--source', str(src), '--dest', str(dst), '--no-tokens')
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            self.assertEqual(before, {p: p.read_bytes() for p in src.rglob('*') if p.is_file()})  # the source is only read
            report = json.loads((dst / 'rename_report.json').read_text())
            self.assertTrue(report['verification']['passed'])
            self.assertEqual(report['replacements_by_old_identifier'], {'Asterion': 3, 'Lumen': 1, 'Lumen Field': 1, 'SYNX': 6})
            text = (dst / 'exports/ct_drafts.jsonl').read_text()
            self.assertIn('Aldervane Technology Unit 01 (ZQFX001) is described. Larkmere is separate.', text)
            self.assertIn('Hollow Beacon Transport Unit 34 (ZQFX034). Field labels differ.', text)
            control = [json.loads(l) for l in (dst / 'control_v2/records.jsonl').read_text().splitlines()]
            renamed_parent = 'Aldervane Technology Unit 01 (ZQFX001) is described. Larkmere is separate.'
            self.assertEqual(control[0]['derived_from_sha256'], hashlib.sha256(json.dumps(renamed_parent).encode()).hexdigest())
            self.assertNotEqual(control[0]['derived_from_sha256'], rule)
            self.assertEqual(control[1]['derived_from_sha256'], 'f' * 64)  # no rule match in the source: left and noted
            self.assertEqual(report['files']['control_v2/records.jsonl']['notes_total'], 1)
            check = self.run_tool('--mapping', str(mapping), '--source', str(src), '--dest', str(dst), '--check-only', '--no-tokens')
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
            target = dst / 'exports/ct_drafts.jsonl'
            target.write_text(target.read_text().replace('is described', 'is recommended'))
            tampered = self.run_tool('--mapping', str(mapping), '--source', str(src), '--dest', str(dst), '--check-only', '--no-tokens')
            self.assertEqual(tampered.returncode, 1)
            refuse = self.run_tool('--mapping', str(mapping), '--source', str(src), '--dest', str(dst), '--no-tokens')
            self.assertNotEqual(refuse.returncode, 0)  # a non-empty destination is never overwritten

    def test_undeclared_short_form_blocks_the_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp) / 'src', Path(tmp) / 'dst'
            self.build(src)
            mapping = Path(tmp) / 'mapping.json'
            mapping.write_text(json.dumps({k: v for k, v in MAPPING.items() if k not in ('short_forms', 'generic_words')}))
            done = self.run_tool('--mapping', str(mapping), '--source', str(src), '--dest', str(dst), '--no-tokens')
            self.assertNotEqual(done.returncode, 0)
            self.assertIn("used alone", done.stdout)
            self.assertFalse(dst.exists() and any(dst.iterdir()))

    def test_new_identifier_already_in_the_data_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp) / 'src', Path(tmp) / 'dst'
            self.build(src)
            mapping = Path(tmp) / 'mapping.json'
            mapping.write_text(json.dumps(dict(MAPPING, name_stems={'Asterion': 'Catalogue', 'Lumen Field': 'Larkmere'})))
            done = self.run_tool('--mapping', str(mapping), '--source', str(src), '--dest', str(dst), '--no-tokens')
            self.assertNotEqual(done.returncode, 0)
            self.assertIn('already occurs', done.stdout + done.stderr)


if __name__ == '__main__':
    unittest.main()
