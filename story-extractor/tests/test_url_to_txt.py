"""End-to-end tests for URL -> exact DOM -> saved TXT, no live scraping."""
import argparse
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from url_to_txt import (
    filename_for_url, identity_from_url, input_pages, run, story_text_from_dom
)

PAGE = """
<html><body>
<div id="post_555" class="post">
  <div id="pid_555" class="post_body">
    <p>First line with punctuation: a, b &amp; c!</p>
    <p>Dialogue: "This is the exact intended post."<br>Next spoken line.</p>
  </div>
</div>
<div id="post_556">
  <div id="pid_556" class="post_body"><p>OTHER READER REPLY MUST NOT APPEAR.</p></div>
</div>
<div id="footer">Advertising and navigation must not appear.</div>
</body></html>
"""


def arguments(directory, url="https://xossipy.com/thread-14046-post-555.html",
              selector="auto"):
    return argparse.Namespace(
        url=[url], url_file=None, episode_map=None, selector=selector,
        output_dir=directory, delay=0, timeout=3, max_pages=500, overwrite=False,
    )


class FakeResponse:
    def __init__(self, url):
        self.url = url
        self.headers = {"Content-Type": "text/html; charset=utf-8"}
        self.text = PAGE

    def raise_for_status(self):
        pass


class FakeSession:
    def get(self, url, timeout=10, allow_redirects=True):
        return FakeResponse(url)


class UrlToTxtTests(unittest.TestCase):
    def test_identifies_exact_post(self):
        self.assertEqual(identity_from_url(
            "https://xossipy.com/thread-14046-post-555.html"), (14046, 555))
        self.assertIsNone(identity_from_url(
            "https://example.org/thread-14046-post-555.html"))

    def test_extract_only_target_div_not_reply(self):
        text, selector = story_text_from_dom(
            PAGE, "https://xossipy.com/thread-14046-post-555.html"
        )
        self.assertIn("First line with punctuation: a, b & c!", text)
        self.assertIn('Dialogue: "This is the exact intended post."', text)
        self.assertIn("Next spoken line.", text)
        self.assertNotIn("READER REPLY", text)
        self.assertNotIn("Advertising", text)
        self.assertIn("#pid_555", selector)

    def test_rejects_absent_post(self):
        with self.assertRaisesRegex(ValueError, "not found"):
            story_text_from_dom(PAGE, "https://xossipy.com/thread-14046-post-999.html")

    def test_explicit_selector_for_other_sites(self):
        html = '<div class="chapter">An original paragraph, followed by a second sentence.</div>'
        text, selector = story_text_from_dom(
            html, "https://example.org/chapter/1", ".chapter"
        )
        self.assertEqual(selector, ".chapter")
        self.assertIn("original paragraph", text)

    def test_exact_post_to_txt_file_and_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=arguments(Path(tmp))
            with patch("url_to_txt.robots_permission", return_value=(True, 0)):
                report=run(args,session=FakeSession())
                self.assertEqual(report["records"][0]["status"], "saved")
                out=Path(tmp)/"EP_001_Post_555.txt"
                self.assertTrue(out.exists())
                raw=out.read_text(encoding="utf-8")
                self.assertIn("First line",raw)
                self.assertNotIn("OTHER READER REPLY",raw)
                meta=json.loads((Path(tmp)/"extraction-status.json").read_text(encoding="utf-8"))
                self.assertEqual(meta["records"][0]["status"],"saved")
                report_again=run(args,session=FakeSession())
                self.assertEqual(report_again["records"][0]["status"],"skipped_exists")

    def test_uses_episode_map_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            manifest=root/"episode-map.json"
            url="https://xossipy.com/thread-14046-post-555.html"
            manifest.write_text(json.dumps({
                "entries":[{"source_url":url,"source_post_id":555,
                    "episode_number":9,"part":"4 A&B","section":"update"}]
            }),encoding="utf-8")
            args=arguments(root)
            args.url=[]
            args.episode_map=manifest
            pages=input_pages(args)
            self.assertEqual(len(pages),1)
            self.assertEqual(filename_for_url(pages[0][0],1,pages[0][1]),
                "EP_009_Part_4_A_B_Post_555.txt")

    def test_auto_rejects_unsupported_host(self):
        args=arguments(Path("/unused"),"https://example.org/chapter-1")
        with self.assertRaisesRegex(ValueError, "Auto selector"):
            input_pages(args)


if __name__ == "__main__":
    unittest.main()
