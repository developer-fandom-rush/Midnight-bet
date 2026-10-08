#!/usr/bin/env python3
"""Audit DOM story-post selectors for known Jaya source links.

Requests only index-linked posts, respects robots and delay, and records
selector availability plus text length/hash, not the text or HTML itself.
No page screenshots or copyrighted story content are stored.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from xossipy_jaya import STORIES, find_post_body, request_page, write_json


def sample(entries: list[dict], count: int) -> list[dict]:
    if count <= 0 or count >= len(entries):
        return entries
    if count == 1:
        return [entries[0]]
    positions = sorted({round(i * (len(entries) - 1) / (count - 1)) for i in range(count)})
    return [entries[pos] for pos in positions]


def inspect_one(html: str, pid: int) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    root = find_post_body(html, pid)
    root_id = root.get("id", "")
    root_class = root.get("class", [])
    # No text is returned; only body diagnostics.
    visible = root.get_text(separator=" ", strip=True)
    if len(visible) < 30:
        raise ValueError("Post has less than 30 visible characters; inspect selector")
    enclosing = root.find_parent(id=f"post_{pid}")
    return {
        "body_tag": root.name,
        "body_id": root_id,
        "body_classes": root_class,
        "post_container_found": enclosing is not None,
        "readable_character_count": len(visible),
        "text_sha256": hashlib.sha256(visible.encode("utf-8")).hexdigest(),
        "external_image_count": len(root.select("img")),
        "url_count": len(root.select("a[href]")),
    }


def run(args):
    session = requests.Session()
    session.headers["User-Agent"] = "MidnightBetStoryArchiver/1.0 (personal archival; respects robots.txt)"
    robots_cache = {}
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "stores_story_text": False,
        "reports": [],
    }
    for slug, story in STORIES.items():
        index_file = args.root / slug / "index.json"
        index = json.loads(index_file.read_text(encoding="utf-8"))
        selected = sample(index["chapters"], args.per_story)
        story_report = {
            "story": slug,
            "index_url": story["index_url"],
            "indexed_links": len(index["chapters"]),
            "audited_links": len(selected),
            "pages": [],
        }
        report["reports"].append(story_report)
        for chapter in selected:
            record = {
                "index_sequence": chapter["sequence"],
                "post_id": chapter["post_id"],
                "source_url": chapter["url"],
            }
            try:
                raw, html, delay = request_page(
                    session, chapter["url"], robots_cache, args.delay
                )
                record.update(inspect_one(html, chapter["post_id"]))
                record["http_bytes"] = len(raw)
                record["status"] = "found"
            except (requests.RequestException, RuntimeError, ValueError, PermissionError) as exc:
                record.update(status="failed", error=f"{type(exc).__name__}: {str(exc)[:120]}")
            story_report["pages"].append(record)
            print(f"{slug}: post={chapter['post_id']} status={record['status']} " +
                  (f"chars={record['readable_character_count']}" if "readable_character_count" in record else record.get("error", "")),
                  flush=True)
            time.sleep(args.delay)
    write_json(args.output, report)
    failures = sum(
        p["status"] == "failed"
        for s in report["reports"] for p in s["pages"]
    )
    count = sum(len(s["pages"]) for s in report["reports"])
    print(f"DOM audit: {count - failures}/{count} posts found, {failures} failures.")
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).parent / "output")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "output" / "dom-audit.json")
    parser.add_argument("--per-story", type=int, default=3,
                        help="Sample N evenly spaced links from each index (0 means ALL)")
    parser.add_argument("--delay", type=float, default=2.0)
    args = parser.parse_args()
    if args.per_story < 0 or args.delay < 0:
        parser.error("--per-story and --delay must be nonnegative")
    try:
        return run(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"DOM audit stopped: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
