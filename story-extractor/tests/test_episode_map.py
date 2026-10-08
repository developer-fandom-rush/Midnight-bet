"""Safe episode numbering tests; no network access."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from episode_map import make_map, normalize_entry


class EpisodeMappingTests(unittest.TestCase):
    def test_introduction_not_numbered_update(self):
        r = normalize_entry({"sequence":1,"label":"Introduction","post_id":123,"url":"unused"}, "jaya-young-college-teacher")
        self.assertEqual((r["episode_number"],r["section"],r["episode_number_basis"]),(0,"introduction","author_intro"))

    def test_parts_group_under_same_authored_update(self):
        a = normalize_entry({"sequence":11,"label":"Update-9 — PART-2","post_id":222,"url":"unused"},"jaya-young-college-teacher")
        b = normalize_entry({"sequence":12,"label":"Update-9 — PART-3","post_id":223,"url":"unused"},"jaya-young-college-teacher")
        self.assertEqual(a["episode_number"], b["episode_number"])
        self.assertEqual(a["episode_number"],9)
        self.assertEqual((a["part"],b["part"]),("2","3"))
        self.assertNotEqual(a["episode_key"], b["episode_key"])

    def test_lone_wife_index_order_not_authored_number(self):
        r = normalize_entry({"sequence":3,"label":"https://xossipy.com/...","post_id":333,"url":"unused"},"jaya-lonely-wife")
        self.assertEqual(r["episode_number"],3)
        self.assertEqual(r["episode_number_basis"],"index_order_assigned")

    def test_cross_thread_detected(self):
        with self.assertRaises(ValueError):
            make_map({"thread_url":"https://xossipy.com/thread-38982.html","chapters":[{"sequence":1,"post_id":4,"url":"https://xossipy.com/thread-14046-post-4.html"}]},"jaya-young-college-teacher")


if __name__ == "__main__":
    unittest.main()
