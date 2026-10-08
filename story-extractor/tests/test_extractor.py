"""Offline checks for text preservation and explicit chapter navigation."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from extract_jaya import extract_story_text, next_chapter_url, normalize_url, sha256


class ExtractorTests(unittest.TestCase):
    def test_keeps_text_and_inline_formatting_without_paraphrase(self):
        html = (
            '<html><article class="story">'
            '<p>Jaya said: <em>"Hello!"</em></p>'
            '<p>Next line<br>Again &amp; again.</p>'
            '</article><footer>Wrong section</footer></html>'
        )
        self.assertEqual(
            extract_story_text(html, "article.story"),
            'Jaya said: "Hello!"\n\nNext line\nAgain & again.'
        )

    def test_missing_selector_is_error(self):
        with self.assertRaisesRegex(ValueError, "not found"):
            extract_story_text("<article>Something sufficiently long is here.</article>", ".missing")

    def test_next_link_and_relative_url(self):
        page = '<a class="next" href="/jaya/chapter-2#comments">Next</a>'
        self.assertEqual(
            next_chapter_url(page, "a.next", "https://example.org/jaya/chapter-1"),
            "https://example.org/jaya/chapter-2"
        )

    def test_does_not_guess_next_page(self):
        self.assertIsNone(next_chapter_url("<p>No link</p>", "a.next", "https://example.org/"))

    def test_rejects_file_protocol(self):
        with self.assertRaises(ValueError):
            normalize_url("file:///etc/passwd")

    def test_hash_is_consistent(self):
        self.assertEqual(
            sha256(b"abc"),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        )


if __name__ == "__main__":
    unittest.main()
