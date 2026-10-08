#!/usr/bin/env python3
"""Archive an authorized, publicly readable story chapter by chapter.

Saves original response bytes (HTML), readable extracted text, and a SHA-256
manifest. The chapter URLs and the exact story-body selector must be provided;
the script never guesses that a search result is the intended Jaya story.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup, Comment, NavigableString, Tag


USER_AGENT = "MidnightBetStoryArchiver/1.0 (personal archival; respects robots.txt)"
BLOCK_END = {"p", "div", "section", "article", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6"}
EXCLUDED = {"script", "style", "noscript", "nav", "footer", "form", "button"}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_url(url: str, base: str | None = None) -> str:
    absolute, _fragment = urldefrag(urljoin(base, url) if base else url)
    parsed = urlparse(absolute)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError(f"Unsupported URL: {absolute}")
    return absolute


def extract_story_text(html: str, selector: str) -> str:
    """Keep text-node characters and explicit HTML line/paragraph breaks.

    This is a readable transcription, not a byte-identical representation of
    HTML. The untouched downloaded HTML is saved alongside it for verification.
    """
    soup = BeautifulSoup(html, "html.parser")
    root = soup.select_one(selector)
    if root is None:
        raise ValueError(f"Story selector {selector!r} not found; no output saved")
    for item in root.select(",".join(EXCLUDED)):
        item.decompose()

    def visit(node: object) -> str:
        if isinstance(node, Comment):
            return ""
        if isinstance(node, NavigableString):
            return str(node)
        if not isinstance(node, Tag):
            return ""
        if node.name == "br":
            return "\n"
        result = "".join(visit(child) for child in node.children)
        if node.name in BLOCK_END:
            return result + "\n\n"
        if node.name == "li":
            return result + "\n"
        return result

    text = visit(root).strip("\n")
    if len(text.strip()) < 30:
        raise ValueError("Extracted text is too short; check the story-body selector")
    return text


def next_chapter_url(html: str, selector: str, current_url: str) -> str | None:
    if not selector:
        return None
    link = BeautifulSoup(html, "html.parser").select_one(selector)
    if link is None or not link.get("href"):
        return None
    return normalize_url(str(link["href"]), current_url)


def robots_permission(session: requests.Session, url: str, cache: dict) -> tuple[bool, float]:
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    if origin not in cache:
        robots_url = origin + "/robots.txt"
        try:
            response = session.get(robots_url, timeout=20)
            if response.status_code == 404:
                cache[origin] = None
            elif response.status_code in (401, 403):
                cache[origin] = False
            else:
                response.raise_for_status()
                parser = RobotFileParser()
                parser.parse(response.text.splitlines())
                cache[origin] = parser
        except requests.RequestException as exc:
            raise RuntimeError(
                f"Unable to verify robots.txt at {robots_url}: {exc}. "
                "No content request was made."
            ) from exc

    rule = cache[origin]
    if rule is None:
        return True, 0.0
    if rule is False:
        return False, 0.0
    allowed = rule.can_fetch(USER_AGENT, url)
    delay = rule.crawl_delay(USER_AGENT) or rule.crawl_delay("*") or 0
    return allowed, float(delay)


def seed_urls(args: argparse.Namespace) -> list[str]:
    seeds = [args.url] if args.url else []
    if args.chapter_list:
        for line in args.chapter_list.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                seeds.append(line)
    if not seeds:
        raise ValueError("Provide --url or --chapter-list with verified Jaya chapter URLs")
    return list(dict.fromkeys(normalize_url(u) for u in seeds))


def run(args: argparse.Namespace) -> None:
    seeds = seed_urls(args)
    original_host = urlparse(seeds[0]).hostname
    if any(urlparse(u).hostname != original_host for u in seeds):
        raise ValueError("All chapter URLs must be on the same website")
    if args.max_pages < 1 or args.delay < 0:
        raise ValueError("--max-pages must be positive; --delay cannot be negative")

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "manifest.json"
    if manifest_path.exists():
        if not args.resume:
            raise FileExistsError(
                f"{manifest_path} already exists; use --resume to skip completed URLs"
            )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("selector") != args.selector:
            raise ValueError("Existing manifest uses a different story selector")
    else:
        manifest = {
            "story": "Jaya — a young college teacher (source unverified by script)",
            "selector": args.selector,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "chapters": [],
        }

    completed = {entry["url"] for entry in manifest["chapters"]}
    seen = set()
    pending = list(seeds)
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    rules_cache: dict = {}
    written = 0

    while pending and written < args.max_pages:
        url = pending.pop(0)
        if url in seen:
            continue
        seen.add(url)
        if urlparse(url).hostname != original_host:
            raise RuntimeError(f"Refusing to follow off-site chapter link: {url}")
        if url in completed:
            print(f"Already archived: {url}")
            # For auto-next discovery, resume using the last saved next link.
            matching = next((c for c in manifest["chapters"] if c["url"] == url), None)
            if matching and matching.get("next_url"):
                pending.append(matching["next_url"])
            continue

        allowed, crawl_delay = robots_permission(session, url, rules_cache)
        if not allowed:
            raise PermissionError(f"robots.txt disallows this chapter: {url}")
        response = session.get(url, timeout=args.timeout, allow_redirects=True)
        response.raise_for_status()
        final_url = normalize_url(response.url)
        if urlparse(final_url).hostname != original_host:
            raise RuntimeError(f"Cross-site redirect rejected: {final_url}")
        content_type = response.headers.get("Content-Type", "").lower()
        if "html" not in content_type:
            raise RuntimeError(f"Expected HTML but received {content_type!r}: {final_url}")

        readable = extract_story_text(response.text, args.selector)
        discovered = next_chapter_url(response.text, args.next_selector, final_url)
        if discovered and urlparse(discovered).hostname != original_host:
            raise RuntimeError(f"Off-site next-page link rejected: {discovered}")
        number = len(manifest["chapters"]) + 1
        stem = f"chapter_{number:03d}"
        html_file = output / f"{stem}.html"
        text_file = output / f"{stem}.txt"
        if html_file.exists() or text_file.exists():
            raise FileExistsError(f"Refusing to overwrite existing chapter {stem}")

        html_bytes = response.content
        text_bytes = readable.encode("utf-8")
        html_file.write_bytes(html_bytes)
        text_file.write_bytes(text_bytes)
        chapter = {
            "number": number,
            "url": url,
            "final_url": final_url,
            "next_url": discovered,
            "html_file": html_file.name,
            "text_file": text_file.name,
            "html_sha256": sha256(html_bytes),
            "text_sha256": sha256(text_bytes),
            "text_characters": len(readable),
            "fetched_utc": datetime.now(timezone.utc).isoformat(),
        }
        manifest["chapters"].append(chapter)
        temp = manifest_path.with_suffix(".tmp")
        temp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temp.replace(manifest_path)
        completed.add(url)
        written += 1
        print(f"Saved {stem}: {text_file} ({len(readable)} characters)")
        if discovered and args.next_selector:
            pending.append(discovered)
        if pending and written < args.max_pages:
            time.sleep(max(args.delay, crawl_delay))
    print(f"Finished: {len(manifest['chapters'])} archived chapters; manifest: {manifest_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", help="Verified first chapter URL")
    parser.add_argument("--chapter-list", type=Path, help="UTF-8 file: one chapter URL per line")
    parser.add_argument("--selector", required=True, help="CSS selector for ONLY the story text")
    parser.add_argument("--next-selector", default="", help="CSS selector for the next-chapter anchor")
    parser.add_argument("--max-pages", type=int, default=100)
    parser.add_argument("--delay", type=float, default=2.0, help="Seconds between requests")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "output" / "jaya")
    parser.add_argument("--resume", action="store_true", help="Resume, without overwriting saved chapters")
    args = parser.parse_args()
    try:
        run(args)
        return 0
    except (OSError, ValueError, RuntimeError, requests.RequestException) as exc:
        print(f"Extraction stopped safely: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
