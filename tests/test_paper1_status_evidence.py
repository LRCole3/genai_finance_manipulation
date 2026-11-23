import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts/paper1'))
from validation_status import artifact_hashes_match


class StatusEvidenceTests(unittest.TestCase):
    def test_missing_or_changed_token_artifact_cannot_pass_its_hash_check(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / 'records.jsonl'
            expected = hashlib.sha256(b'original').hexdigest()
            self.assertFalse(artifact_hashes_match(root, {}))
            self.assertFalse(artifact_hashes_match(root, {'records.jsonl': expected}))
            path.write_bytes(b'original')
            self.assertTrue(artifact_hashes_match(root, {'records.jsonl': expected}))
            path.write_bytes(b'changed')
            self.assertFalse(artifact_hashes_match(root, {'records.jsonl': expected}))


if __name__ == '__main__':
    unittest.main()
