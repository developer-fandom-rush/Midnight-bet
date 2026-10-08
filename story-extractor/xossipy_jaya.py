#!/usr/bin/env python3
"""Discover Xossipy Jaya chapter permalinks from the author's index posts.

Default: write only a chapter LINK inventory (safe to track in Git).
With --archive --confirm-rights: save original HTML and readable text LOCALLY
for material you are authorized to copy. No story text is uploaded by this tool.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from extract_jaya import extract_story_text, robots_permission, sha256

DOMAIN = "xossipy.com"
STORIES = {
    "jaya-young-college-teacher": {
        "title": "Jaya - young college teacher",
        "author": "kuttoosan009",
        "thread_id": 14046,
        "index_post_id": 752747,  # thread post #3
        "thread_url": "https://xossipy.com/thread-14046.html",
        "index_url": "https://xossipy.com/thread-14046-post-752747.html",
    },
    "jaya-lonely-wife": {
        "title": "Jaya - A Lonely Wife's Adventures",
        "author": "badri.rao2006",
        "thread_id": 38982,
        "index_post_id": 4500941,  # thread post #2
        "thread_url": "https://xossipy.com/thread-38982.html",
        "index_url": "https://xossipy.com/thread-38982-post-4500941.html",
    },
}


def post_id_from_link(url: str, expected_thread: int) -> int | None:
    """Return a post id only when it explicitly belongs to this thread."""
    parsed = urlparse(url)
    if parsed.scheme not in ("https", "http") or parsed.hostname not in (DOMAIN, "www." + DOMAIN):
        return None
    path_match = re.fullmatch(r"/thread-(\d+)-post-(\d+)\.html", parsed.path)
    if path_match:
        tid, pid = map(int, path_match.groups())
        return pid if tid == expected_thread else None
    if parsed.path == "/showthread.php":
        args = parse_qs(parsed.query)
        try:
            tid = int(args.get("tid", ["0"])[0])
            pid = int(args.get("pid", ["0"])[0])
        except ValueError:
            return None
        return pid if tid == expected_thread and pid > 0 else None
    return None


def find_post_body(html: str, post_id: int):
    """Select precisely one MyBB post body; fail closed if DOM differs."""
    soup = BeautifulSoup(html, "html.parser")
    body = soup.select_one(f"#pid_{post_id}")
    if body is None:
        wrapper = soup.select_one(f"#post_{post_id}")
        if wrapper is not None:
            body = wrapper.select_one(".post_body")
    if body is None:
        raise ValueError(f"Post body for pid {post_id} not found (site HTML changed)")
    return body


def discover_index(html: str, story: dict) -> list[dict]:
    """Walk the linked updates in author index, preserving *index link order*."""
    root = find_post_body(html, story["index_post_id"])
    chapters = []
    seen = set()
    for a in root.select("a[href]"):
        source_url = urljoin(story["thread_url"], a.get("href", ""))
        pid = post_id_from_link(source_url, story["thread_id"])
        if pid is None or pid == story["index_post_id"] or pid in seen:
            continue
        seen.add(pid)
        chapters.append({
            "sequence": len(chapters) + 1,
            "label": a.get_text(" ", strip=True) or f"Post {pid}",
            "post_id": pid,
            "url": f"https://{DOMAIN}/thread-{story['thread_id']}-post-{pid}.html",
        })
    if not chapters:
        raise ValueError(f"No chapter post links found in index for {story['title']}")
    return chapters


def request_page(session, url: str, rules: dict, min_delay: float) -> tuple[bytes, str, float]:
    allowed, crawl_delay = robots_permission(session, url, rules)
    if not allowed:
        raise PermissionError(f"robots.txt denies access to {url}")
    response = session.get(url, timeout=30, allow_redirects=True)
    response.raise_for_status()
    if urlparse(response.url).hostname not in (DOMAIN, "www." + DOMAIN):
        raise ValueError(f"Off-domain redirect: {response.url}")
    if "html" not in response.headers.get("Content-Type", "").lower():
        raise ValueError(f"Not an HTML page: {url}")
    return response.content, response.text, max(crawl_delay, min_delay)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def process_story(session, slug: str, args, rules: dict) -> None:
    story = STORIES[slug]
    target = args.output / slug
    target.mkdir(parents=True, exist_ok=True)
    data, html, delay = request_page(session, story["index_url"], rules, args.delay)
    inventory = {
        "title": story["title"],
        "author": story["author"],
        "thread_url": story["thread_url"],
        "index_url": story["index_url"],
        "index_post_id": story["index_post_id"],
        "captured_utc": datetime.now(timezone.utc).isoformat(),
        "index_sha256": sha256(data),
        "chapters": discover_index(html, story),
    }
    write_json(target / "index.json", inventory)
    print(f"{slug}: {len(inventory['chapters'])} linked posts inventoried")

    if not args.archive:
        return
    if not args.confirm_rights:
        raise ValueError("Archiving story text requires --confirm-rights")
    private_dir = target / "private_archive"
    private_dir.mkdir(exist_ok=True)
    archive_manifest = private_dir / "manifest.json"
    if archive_manifest.exists():
        manifest = json.loads(archive_manifest.read_text(encoding="utf-8"))
    else:
        manifest = {"story": slug, "posts": []}
    done = {p["post_id"] for p in manifest["posts"]}

    for chapter in inventory["chapters"]:
        if chapter["post_id"] in done:
            continue
        if len(manifest["posts"]) >= args.limit:
            break
        time.sleep(delay)
        raw_bytes, page_html, delay = request_page(session, chapter["url"], rules, args.delay)
        body = find_post_body(page_html, chapter["post_id"])
        # Use the precise post-body node, not the full page with reader comments.
        story_html = str(body)
        plain_text = extract_story_text(story_html, f"#{body.get('id')}" if body.get("id") else ".post_body")
        name = f"post_{chapter['sequence']:03d}_{chapter['post_id']}"
        html_file = private_dir / (name + ".html")
        text_file = private_dir / (name + ".txt")
        if html_file.exists() or text_file.exists():
            raise FileExistsError(f"File already exists but is not in manifest: {name}")
        html_file.write_bytes(raw_bytes)  # exact source response, NOT reconstructed HTML
        text_file.write_text(plain_text, encoding="utf-8")
        entry = {
            **chapter,
            "source_html": html_file.name,
            "text_file": text_file.name,
            "source_html_sha256": sha256(raw_bytes),
            "text_sha256": sha256(plain_text.encode("utf-8")),
            "characters": len(plain_text),
            "fetched_utc": datetime.now(timezone.utc).isoformat(),
        }
        manifest["posts"].append(entry)
        write_json(archive_manifest, manifest)
        print(f"  archived {name}")
    print(f"  archived total: {len(manifest['posts'])} posts in local private_archive/")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--story", choices=["all", *STORIES], default="all")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "output")
    parser.add_argument("--delay", type=float, default=2.0)
    parser.add_argument("--archive", action="store_true",
                        help="Copy original page HTML and text to LOCAL private_archive/ (not committed)")
    parser.add_argument("--confirm-rights", action="store_true",
                        help="Confirm you have the rights/permission to archive the story")
    parser.add_argument("--limit", type=int, default=500, help="Maximum archived posts per story")
    args = parser.parse_args()
    if args.delay < 0 or args.limit < 1:
        parser.error("--delay must be >= 0 and --limit must be >= 1")
    if args.archive and not args.confirm_rights:
        parser.error("Use --confirm-rights only for text you own or are allowed to copy")
    names = list(STORIES) if args.story == "all" else [args.story]
    session = requests.Session()
    session.headers["User-Agent"] = "MidnightBetStoryArchiver/1.0 (personal archival; respects robots.txt)"
    rules = {}
    failures = 0
    for name in names:
        try:
            process_story(session, name, args, rules)
        except (requests.RequestException, RuntimeError, ValueError, OSError) as exc:
            failures += 1
            print(f"{name}: FAILED: {exc}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
