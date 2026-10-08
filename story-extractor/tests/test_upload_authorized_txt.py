"""Offline tests: TXT file mapping and integrity, no Drive calls."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from upload_authorized_txt import episode_filename, prepare_uploads, valid_local_txt


class TxtUploadTests(unittest.TestCase):
    def test_safe_episode_names(self):
        self.assertEqual(episode_filename({
            "episode_number":9, "source_post_id":839107,
            "section":"update", "part":"1"
        }), "EP_009_Part_1_Post_839107.txt")
        self.assertEqual(episode_filename({
            "episode_number":0, "source_post_id":752484,
            "section":"introduction", "part":None
        }), "Introduction_Post_752484.txt")

    def test_episode_manifest_checksums(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "jaya-young-college-teacher"
            output = root / "private_archive"
            output.mkdir(parents=True)
            text_file = output / "post_001_77.txt"
            raw = "Original authored text, preserving punctuation.\n".encode("utf-8")
            text_file.write_bytes(raw)
            url = "https://xossipy.com/thread-14046-post-77.html"
            (root / "episode-map.json").write_text(json.dumps({
                "story":"jaya-young-college-teacher",
                "entries":[{"episode_number":1,"source_post_id":77,
                    "source_url":url,"section":"update","part":None}]
            }), encoding="utf-8")
            (output / "manifest.json").write_text(json.dumps({
                "story":"jaya-young-college-teacher",
                "posts":[{"post_id":77,"url":url,"text_file":text_file.name,
                    "text_sha256":hashlib.sha256(raw).hexdigest()}]
            }), encoding="utf-8")
            records, count = prepare_uploads(Path(tmp), "jaya-young-college-teacher")
            self.assertEqual(count,1)
            self.assertEqual(records[0]["text"],raw)
            self.assertEqual(records[0]["drive_filename"],"EP_001_Post_77.txt")
            text_file.write_text("Tampered data",encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"SHA-256 mismatch"):
                prepare_uploads(Path(tmp),"jaya-young-college-teacher")

    def test_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            outer=root/"not-a-chapter.txt"
            outer.write_text("not allowed",encoding="utf-8")
            inside=root/"archive"
            inside.mkdir()
            with self.assertRaises(ValueError):
                valid_local_txt(outer,inside)


if __name__ == "__main__":
    unittest.main()
