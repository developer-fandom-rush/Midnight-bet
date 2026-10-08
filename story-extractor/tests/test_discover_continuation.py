"""Continuation mapping fixtures: author only, original thread provenance."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discover_continuation import (
    ANNOUNCEMENT_POST, AUTHOR, ORIGINAL_THREAD, THREAD,
    find_authored_posts,
)


def post(pid, username, text):
    return (
        f'<div id="post_{pid}" class="post">'
        f'<div class="post_author"><strong><a href="/member.php?username={username}">'
        f'{username}</a></strong></div>'
        f'<div class="post_content"><div class="post_body" id="pid_{pid}">'
        f'{text}</div></div></div>'
    )


class ContinuationIndexTests(unittest.TestCase):
    def test_source_identity_distinct_from_original(self):
        self.assertEqual((THREAD, ORIGINAL_THREAD), (47646, 14046))
        self.assertEqual(AUTHOR, "desicocker7")

    def test_announcement_and_story_excluding_other_writers(self):
        html = "".join((
            post(ANNOUNCEMENT_POST, AUTHOR, "Continuing from original Jaya teacher thread 14046"),
            post(4838100, "reader_123", "READER POST " * 300),
            post(4838110, AUTHOR, "Original narrative passage. " * 40),
            post(4838120, AUTHOR, "Thanks for reading!"),
        ))
        rows = find_authored_posts(html, 1)
        self.assertEqual([x["post_id"] for x in rows],
                         [ANNOUNCEMENT_POST, 4838110, 4838120])
        self.assertEqual([x["classification"] for x in rows],
                         ["continuity_announcement", "candidate_story_update",
                          "short_author_post_review"])
        self.assertEqual(rows[1]["url"], "https://xossipy.com/thread-47646-post-4838110.html")

    def test_quoted_replies_not_in_story_length(self):
        html = post(500, AUTHOR, "<blockquote>" + ("long unrelated quote "*100) +
                    "</blockquote>Short reply.")
        rows = find_authored_posts(html, 2)
        self.assertEqual(rows[0]["classification"], "short_author_post_review")

    def test_fails_closed_when_author_unknown(self):
        html = '<div id="post_123"><div id="pid_123">text</div></div>'
        with self.assertRaisesRegex(ValueError, "post_author"):
            find_authored_posts(html, 1)


if __name__ == "__main__":
    unittest.main()
