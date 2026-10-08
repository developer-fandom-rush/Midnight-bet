"""Offline tests for source-specific Jaya index discovery (no story fetched)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from xossipy_jaya import STORIES, discover_index, find_post_body, post_id_from_link


class XossipyIndexTests(unittest.TestCase):
    def test_verified_sources_remain_distinct(self):
        self.assertNotEqual(
            STORIES["jaya-young-college-teacher"]["thread_id"],
            STORIES["jaya-lonely-wife"]["thread_id"],
        )
        self.assertNotEqual(
            STORIES["jaya-young-college-teacher"]["author"],
            STORIES["jaya-lonely-wife"]["author"],
        )

    def test_two_index_links_in_original_order_without_duplicate(self):
        story = STORIES["jaya-young-college-teacher"]
        html = """
        <html><div id="pid_752747" class="post_body scaleimages">
        <a href="/thread-14046-post-10001.html">Introduction</a>
        <a href="showthread.php?pid=10002&amp;tid=14046">Update 1</a>
        <a href="/thread-14046-post-10001.html">Duplicate link</a>
        <a href="/thread-38982-post-12345.html">Other story</a>
        <a href="https://example.net/">Advertisement</a>
        </div><div id="pid_77777" class="post_body">
        <a href="/thread-14046-post-500.html">Random comment</a></div></html>
        """
        index = discover_index(html, story)
        self.assertEqual([p["post_id"] for p in index], [10001, 10002])
        self.assertEqual([p["sequence"] for p in index], [1, 2])

    def test_missing_index_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "not found"):
            find_post_body("<div id='pid_10'>wrong post</div>", 752747)

    def test_rejects_cross_story_and_offsite(self):
        self.assertIsNone(
            post_id_from_link("https://xossipy.com/thread-38982-post-999.html", 14046)
        )
        self.assertIsNone(
            post_id_from_link("https://example.com/thread-14046-post-999.html", 14046)
        )

    def test_accepts_site_permalink_and_php_post_id(self):
        self.assertEqual(post_id_from_link(
            "https://xossipy.com/thread-38982-post-123.html", 38982
        ), 123)
        self.assertEqual(post_id_from_link(
            "https://xossipy.com/showthread.php?pid=456&tid=14046", 14046
        ), 456)


if __name__ == "__main__":
    unittest.main()
