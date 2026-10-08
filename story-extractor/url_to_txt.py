#!/usr/bin/env python3
"""URL -> exact post-body DOM -> individual UTF-8 TXT files.

Input: one or more page URLs, a one-URL-per-line file, or episode-map.json.
Output: one .txt file for each matching page, plus a machine-readable log.

For Xossipy MyBB post permalinks, --selector auto binds the DOM selector to
the post ID in *that exact URL*, not to all replies on the thread.
For another website, provide the specific CSS selector with --selector.
Use only on material you are authorized to copy/archive.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from extract_jaya import extract_story_text, normalize_url, robots_permission, sha256
from xossipy_jaya import find_post_body, post_id_from_link
from bundled_urls import bundled_pages, STORY_SLUGS


def identity_from_url(url: str) -> tuple[int, int] | None:
    parsed = urlparse(url)
    if parsed.hostname not in ("xossipy.com", "www.xossipy.com"):
        return None
    match = re.fullmatch(r"/thread-(\d+)-post-(\d+)\.html", parsed.path)
    if not match:
        return None
    thread_id, post_id = (int(x) for x in match.groups())
    return (thread_id, post_id) if post_id_from_link(url, thread_id) == post_id else None


def story_text_from_dom(html: str, url: str, selector: str = "auto") -> tuple[str, str]:
    """Extract ONLY the intended post div or an explicit CSS selector.

    Preserves text content and line/paragraph boundaries (not byte-identical
    HTML or original writer's invisible whitespace).
    """
    if selector == "auto":
        ids = identity_from_url(url)
        if ids is None:
            raise ValueError("Auto DOM mode requires a Xossipy thread-post permalink")
        _, pid = ids
        root = find_post_body(html, pid)
        fragment = BeautifulSoup(str(root), "html.parser")
        node = fragment.find()
        if node is None:
            raise ValueError(f"Target post body #{pid} is empty")
        node["id"] = "__only_story_body__"
        return extract_story_text(str(fragment), "#__only_story_body__"), (
            f"#pid_{pid} OR #post_{pid} .post_body"
        )
    soup = BeautifulSoup(html, "html.parser")
    matches = soup.select(selector)
    if len(matches) != 1:
        raise ValueError(f"Expected one match for {selector!r}, found {len(matches)}")
    return extract_story_text(html, selector), selector


def filename_for_url(url: str, ordinal: int, episode: dict | None = None) -> str:
    ids = identity_from_url(url)
    if episode:
        number = episode.get("episode_number")
        if not isinstance(number, int) or not (0 <= number <= 9999):
            raise ValueError("Invalid episode number in episode map")
        stem = "Introduction" if episode.get("section") == "introduction" else f"EP_{number:03d}"
        part = episode.get("part")
        if part:
            normalized = re.sub(r"[^A-Za-z0-9]+", "_", str(part)).strip("_")[:32]
            if normalized:
                stem += f"_Part_{normalized}"
    else:
        stem = f"EP_{ordinal:03d}"
    if ids:
        stem += f"_Post_{ids[1]}"
    else:
        stem += "_Source"
    return stem + ".txt"


def input_pages(args) -> list[tuple[str, dict | None]]:
    pages: list[tuple[str, dict | None]] = []
    builtin = getattr(args, "story", None)
    if builtin and (args.url or args.url_file or args.episode_map):
        raise ValueError("--story cannot be combined with explicit URL input")
    if builtin:
        pages.extend(bundled_pages(builtin))
    elif not (args.url or args.url_file or args.episode_map):
        # URLs are already embedded, so no manual input flags are required.
        pages.extend(bundled_pages("all"))
    for url in args.url:
        pages.append((normalize_url(url), None))
    if args.url_file:
        for line in args.url_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                pages.append((normalize_url(line), None))
    if args.episode_map:
        manifest = json.loads(args.episode_map.read_text(encoding="utf-8"))
        entries = manifest.get("entries")
        if not isinstance(entries, list):
            raise ValueError("Invalid episode map: missing entries")
        for entry in entries:
            url = normalize_url(entry["source_url"])
            if entry.get("source_post_id") != (identity_from_url(url) or (None, None))[1]:
                raise ValueError(f"Episode map URL/post ID mismatch: {url}")
            pages.append((url, entry))
    seen = set()
    result = []
    for url, item in pages:
        if url not in seen:
            result.append((url, item))
            seen.add(url)
    if not result:
        raise ValueError("No episode URLs configured")
    first = getattr(args, "take_first", 0)
    if first < 0:
        raise ValueError("--take-first must be >= 0")
    if first:
        result = result[:first]
    if len(result) > args.max_pages:
        raise ValueError(f"{len(result)} input URLs exceeds --max-pages={args.max_pages}")
    if args.selector == "auto" and any(identity_from_url(u) is None for u, _ in result):
        raise ValueError("Auto selector only supports Xossipy post URLs; set --selector for other sites")
    names = [filename_for_url(u, i, entry) for i, (u, entry) in enumerate(result, 1)]
    if len(names) != len(set(names)):
        raise ValueError("Output filename collision; use separate directories for stories")
    return result


def fetch_page(session: requests.Session, url: str, rules: dict, timeout: float) -> str:
    allowed, _delay = robots_permission(session, url, rules)
    if not allowed:
        raise PermissionError(f"robots.txt denies fetching {url}")
    response = session.get(url, timeout=timeout, allow_redirects=True)
    response.raise_for_status()
    source = urlparse(url)
    final = urlparse(response.url)
    if final.hostname != source.hostname:
        raise ValueError(f"Cross-domain redirect: {response.url}")
    if "html" not in response.headers.get("Content-Type", "").lower():
        raise ValueError(f"Not an HTML document: {response.url}")
    return response.text


def run(args, session: requests.Session | None = None) -> dict:
    if args.delay < 0 or args.timeout <= 0 or args.max_pages < 1:
        raise ValueError("Delay must be >= 0; timeout and max-pages must be > 0")
    pages = input_pages(args)
    outdir = args.output_dir.resolve()
    inspect_only = getattr(args, "inspect_only", False)
    if not inspect_only:
        outdir.mkdir(parents=True, exist_ok=True)
    manifest_path = outdir / "extraction-status.json"
    owned_session = session is None
    if owned_session:
        session = requests.Session()
        session.headers["User-Agent"] = "MidnightBetStoryArchiver/1.0 (personal archival; respects robots.txt)"
    rules = {}
    report = {"generated_utc": datetime.now(timezone.utc).isoformat(), "records": []}
    try:
        for ordinal, (url, episode) in enumerate(pages, 1):
            name = filename_for_url(url, ordinal, episode)
            story = episode.get("story") if episode else None
            folder = outdir / story if story else outdir
            path = folder / name
            record = {"source_url": url, "txt_filename": name,
                      "relative_path": str(path.relative_to(outdir))}
            if path.exists() and not args.overwrite and not inspect_only:
                record.update(status="skipped_exists", error="Use --overwrite to replace")
                report["records"].append(record)
                print(f"SKIP {name}: exists", flush=True)
                continue
            try:
                html = fetch_page(session, url, rules, args.timeout)
                text, chosen_selector = story_text_from_dom(html, url, args.selector)
                raw = text.encode("utf-8")
                record.update(
                    status="inspected" if inspect_only else "saved",
                    selector=chosen_selector, characters=len(text),
                    bytes=len(raw), sha256=sha256(raw)
                )
                if inspect_only:
                    count = getattr(args, "preview_words", 0)
                    if count < 0 or count > 20:
                        raise ValueError("--preview-words must be between 0 and 20")
                    preview = " ".join(text.split()[:count])
                    print(f"INSPECTED {name}: {len(text)} chars; "
                          f"first_{count}_words={preview!r}", flush=True)
                else:
                    folder.mkdir(parents=True, exist_ok=True)
                    tmp = folder / (name + ".partial")
                    tmp.write_bytes(raw)
                    tmp.replace(path)
                    print(f"SAVED {record['relative_path']}: {len(text)} chars", flush=True)
            except (requests.RequestException, PermissionError, ValueError, OSError) as exc:
                record.update(status="failed", error=f"{type(exc).__name__}: {exc}")
                print(f"FAILED {url}: {exc}", file=sys.stderr, flush=True)
            report["records"].append(record)
            if ordinal < len(pages):
                time.sleep(args.delay)
    finally:
        if owned_session:
            session.close()
        if not inspect_only:
            manifest_path.write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8"
            )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--story", choices=["all", *STORY_SLUGS],
                        help="Use the embedded author-index URL list (default: all stories if no input)")
    parser.add_argument("--url", action="append", default=[], help="Input page URL; repeatable")
    parser.add_argument("--url-file", type=Path, help="Input URLs, one per line")
    parser.add_argument("--episode-map", type=Path, help="Optional existing episode-map.json")
    parser.add_argument("--selector", default="auto", help="auto for Xossipy exact post div, or CSS selector")
    parser.add_argument("--output-dir", type=Path, default=Path("raw_txt"))
    parser.add_argument("--delay", type=float, default=2.0)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--max-pages", type=int, default=500)
    parser.add_argument("--take-first", type=int, default=0,
                        help="Test only first N configured URLs; 0 means all")
    parser.add_argument("--inspect-only", action="store_true",
                        help="Real DOM extraction test in memory; do not save story text")
    parser.add_argument("--preview-words", type=int, default=0,
                        help="Print at most N initial words when inspecting (max 20)")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    try:
        report = run(args)
    except (OSError, ValueError, PermissionError) as exc:
        print(f"INPUT ERROR: {exc}", file=sys.stderr)
        return 2
    saved = sum(rec["status"] == "saved" for rec in report["records"])
    failed = sum(rec["status"] == "failed" for rec in report["records"])
    skipped = sum(rec["status"] == "skipped_exists" for rec in report["records"])
    inspected = sum(rec["status"] == "inspected" for rec in report["records"])
    print(f"COMPLETE: saved={saved}, inspected={inspected}, skipped={skipped}, failed={failed}")
    return 1 if failed or skipped else 0


if __name__ == "__main__":
    raise SystemExit(main())
