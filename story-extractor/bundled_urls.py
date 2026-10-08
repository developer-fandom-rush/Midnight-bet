"""Bundled author-index chapter URLs. No story text is stored here."""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

STORY_SLUGS = ("jaya-young-college-teacher", "jaya-lonely-wife", "jaya-continuation-desicocker7")
STORY_THREADS = {"jaya-young-college-teacher": 14046, "jaya-lonely-wife": 38982, "jaya-continuation-desicocker7": 47646}


def bundled_pages(story: str = "all") -> list[tuple[str, dict]]:
    """Load precise input URLs and episode/part labels checked against source thread."""
    if story not in (*STORY_SLUGS, "all"):
        raise ValueError(f"Unknown story slug: {story}")
    slugs = STORY_SLUGS if story == "all" else (story,)
    paths = Path(__file__).resolve().parent / "inputs"
    result = []
    seen = set()
    for slug in slugs:
        doc = json.loads((paths / (slug + ".json")).read_text(encoding="utf-8"))
        if doc.get("story") != slug:
            raise ValueError(f"Story mismatch in bundled URL list: {slug}")
        entries = doc.get("entries")
        if not isinstance(entries, list) or not entries:
            raise ValueError(f"No URL entries for {slug}")
        for expected_order, entry in enumerate(entries, 1):
            url = entry.get("source_url", "")
            pid = entry.get("source_post_id")
            expected_url = f"https://xossipy.com/thread-{STORY_THREADS[slug]}-post-{pid}.html"
            if not isinstance(pid, int) or pid < 1 or url != expected_url:
                raise ValueError(f"Invalid cross-thread URL for {slug} index={expected_order}")
            if url in seen or entry.get("index_order") != expected_order:
                raise ValueError(f"Duplicate or out-of-order input URL for {slug}")
            seen.add(url)
            # Preserve story identity so the default all-story output never mixes files.
            result.append((url, dict(entry, story=slug)))
    return result
