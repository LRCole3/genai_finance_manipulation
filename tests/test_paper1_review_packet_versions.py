import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts/paper1'))
from build_review_packets import save_versioned_packet


class ReviewPacketVersionTests(unittest.TestCase):
    def test_rebuild_preserves_returned_form_and_content_change_creates_new_version(self):
        with tempfile.TemporaryDirectory() as temp:
            out, private = Path(temp) / 'public', Path(temp) / 'private'
            out.mkdir(); private.mkdir()
            records = [{'review_id': 'R1', 'content_sha256': 'hash1', 'texts': {'A': 'original'}}]
            keys = [{'review_id': 'R1', 'item_id': 'source1'}]
            first = save_versioned_packet('sample', records, keys, out, private)
            form_path = Path(first['template_paths'][0])
            form = json.loads(form_path.read_text())
            self.assertEqual(first['packet_sha256'], form['packet_sha256'])
            self.assertEqual('hash1', form['content_sha256'])
            form['reviewer_id'] = 'test reviewer'
            form['notes'] = 'Test-only entered content; must not be overwritten.'
            returned = json.dumps(form) + '\n'
            form_path.write_text(returned)
            same = save_versioned_packet('sample', records, keys, out, private)
            self.assertEqual(first, same)
            self.assertEqual(returned, form_path.read_text())
            records = [{'review_id': 'R1', 'content_sha256': 'hash2', 'texts': {'A': 'revised'}}]
            second = save_versioned_packet('sample', records, keys, out, private)
            self.assertNotEqual(first['packet_sha256'], second['packet_sha256'])
            self.assertEqual(returned, form_path.read_text())
            old = json.loads(Path(first['immutable_packet_path']).read_text())
            self.assertEqual('original', old['texts']['A'])
            new = json.loads(Path(second['template_paths'][0]).read_text())
            self.assertEqual('hash2', new['content_sha256'])
            self.assertIsNone(new['reviewer_id'])

    def test_changed_private_mapping_cannot_replace_same_public_version(self):
        with tempfile.TemporaryDirectory() as temp:
            out, private = Path(temp) / 'public', Path(temp) / 'private'
            out.mkdir(); private.mkdir()
            rows = [{'review_id': 'R1', 'content_sha256': 'hash'}]
            save_versioned_packet('sample', rows, [{'item_id': 'one'}], out, private)
            original = (private / 'sample.jsonl').read_text()
            with self.assertRaisesRegex(ValueError, 'immutable packet'):
                save_versioned_packet('sample', rows, [{'item_id': 'different'}], out, private)
            self.assertEqual(original, (private / 'sample.jsonl').read_text())


if __name__ == '__main__':
    unittest.main()
