#!/usr/bin/env python3
"""Discover source-linked posts in the fan-written Jaya continuation.

The continuation itself identifies thread 14046 as its predecessor.
This script never copies the author's full text. It inventories only
post permalinks, post author, page, approximate character count and
cautious candidate/review classification.

No site content is modified, no login bypass attempted.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from xossipy_jaya import request_page, write_json

THREAD = 47646
ORIGINAL_THREAD = 14046
AUTHOR = "desicocker7"
ANNOUNCEMENT_POST = 4838092
DEFAULT_PAGES = 13
MIN_CANDIDATE_CHARS = 650


def find_authored_posts(html: str, page: int) -> list[dict]:
    """Limit candidate posts to the actual author, never reader replies."""
    soup = BeautifulSoup(html, "html.parser")
    records = []
    wrappers = soup.select('div[id^="post_"]')
    if not wrappers:
        raise ValueError(f"No forum post wrappers found on page {page}")
    for wrapper in wrappers:
        match = re.fullmatch(r"post_(\d+)", wrapper.get("id", ""))
        if match is None:
            continue
        pid = int(match.group(1))
        author_block = wrapper.select_one(".post_author")
        if author_block is None:
            raise ValueError(f"Missing post_author element for post {pid}")
        strong = author_block.select_one("strong")
        if strong is None:
            raise ValueError(f"Missing author label for post {pid}")
        writer = strong.get_text(" ", strip=True)
        if writer.casefold() != AUTHOR:
            continue
        body = wrapper.select_one(f"#pid_{pid}") or wrapper.select_one(".post_body")
        if body is None:
            raise ValueError(f"Missing exact body for author post {pid}")
        # Use a copy when excluding quoted replies, leaving original HTML intact.
        clean = BeautifulSoup(str(body), "html.parser")
        for quote in clean.select("blockquote,.quote_body,.quote,script,style"):
            quote.decompose()
        visible = clean.get_text(" ", strip=True)
        chars = len(visible)
        if pid == ANNOUNCEMENT_POST:
            classification = "continuity_announcement"
        elif chars >= MIN_CANDIDATE_CHARS:
            classification = "candidate_story_update"
        else:
            classification = "short_author_post_review"
        records.append({
            "post_id": pid,
            "url": f"https://xossipy.com/thread-{THREAD}-post-{pid}.html",
            "page": page,
            "author": writer,
            "visible_chars_excluding_quotes": chars,
            "classification": classification,
        })
    return records


def discover(session, pages: int, delay: float) -> dict:
    if not (1 <= pages <= 30) or delay < 0:
        raise ValueError("pages must be 1..30, delay >= 0")
    rules = {}
    all_posts = []
    seen = set()
    for page in range(1, pages + 1):
        url = (f"https://xossipy.com/thread-{THREAD}.html" if page == 1
               else f"https://xossipy.com/thread-{THREAD}-page-{page}.html")
        _raw, html, rule_delay = request_page(session, url, rules, delay)
        found = find_authored_posts(html, page)
        for post in found:
            if post["post_id"] not in seen:
                seen.add(post["post_id"])
                all_posts.append(post)
        print(f"PAGE {page}/{pages}: author_posts={len(found)} total_unique={len(all_posts)}", flush=True)
        if page < pages:
            time.sleep(max(delay, rule_delay))
    if ANNOUNCEMENT_POST not in seen:
        raise ValueError("Known fan-continuity announcement missing from collected pages")
    return {
        "title": "Jaya - The Young and Sexy college Teacher",
        "story": "jaya-continuation-desicocker7",
        "author": AUTHOR,
        "thread_url": f"https://xossipy.com/thread-{THREAD}.html",
        "predecessor_thread_url": f"https://xossipy.com/thread-{ORIGINAL_THREAD}.html",
        "continuity_type": "fan_written_alternate_continuation",
        "continuity_basis": "Author's first post explicitly links source thread 14046 and says this version starts where it stopped.",
        "known_announcement_post_id": ANNOUNCEMENT_POST,
        "pages_scanned": pages,
        "captured_utc": datetime.now(timezone.utc).isoformat(),
        "contains_story_text": False,
        "posts": all_posts,
        "candidate_count": sum(p["classification"] == "candidate_story_update" for p in all_posts),
        "review_count": sum(p["classification"] == "short_author_post_review" for p in all_posts),
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pages", type=int, default=DEFAULT_PAGES)
    p.add_argument("--delay", type=float, default=2.0)
    p.add_argument("--output", type=Path, default=Path(__file__).parent / "output" / "jaya-continuation-desicocker7" / "author-post-index.json")
    a = p.parse_args()
    session = requests.Session()
    session.headers["User-Agent"] = "MidnightBetStoryArchiver/1.0 (personal archival; respects robots.txt)"
    try:
        info = discover(session, a.pages, a.delay)
        write_json(a.output, info)
        for entry in info["posts"]:
            print(f"ENTRY {entry['post_id']} {entry['classification']} chars={entry['visible_chars_excluding_quotes']} page={entry['page']}", flush=True)
        print(f"RESULT candidates={info['candidate_count']} short_review={info['review_count']} all_author_posts={len(info['posts'])}", flush=True)
        return 0
    except (ValueError, RuntimeError, requests.RequestException, OSError) as exc:
        print(f"ERROR {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
