#!/usr/bin/env python3
"""Build episode-ordered, source-linked Jaya maps from index inventories.

No story prose is downloaded, printed, or uploaded. The update numbers for
Young College Teacher come from the author's index labels. For Lonely Wife,
no numbered updates were supplied in link labels, so episode numbers are
*index-order identifiers*, not claimed author chapter numbers.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SOURCES = ("jaya-young-college-teacher", "jaya-lonely-wife")


def normalize_entry(entry: dict, slug: str) -> dict:
    sequence = entry["sequence"]
    label = " ".join((entry.get("label") or "").split())
    number = sequence
    number_basis = "index_order_assigned"
    category = "indexed_post"
    part = None
    if slug == "jaya-young-college-teacher":
        if label.casefold().startswith("introduction"):
            number = 0
            number_basis = "author_intro"
            category = "introduction"
        else:
            match = re.search(r"\bupdate\s*[-–—:]?\s*(\d+)\b", label, re.I)
            if match:
                number = int(match.group(1))
                number_basis = "author_update"
                category = "update"
            else:
                # An unnumbered entry is not silently assigned an author update.
                category = "unresolved"
        part_match = re.search(
            r"\bpart\s*[-–—:.]?\s*(\d+(?:\s*&\s*[a-z\d]+)?|[a-z](?:\s*&\s*[a-z])?)\b",
            label, re.I,
        )
        if part_match:
            part = " ".join(part_match.group(1).upper().split())

    return {
        "index_order": sequence,
        "episode_number": number,
        "episode_number_basis": number_basis,
        "section": category,
        "part": part,
        "episode_key": f"EP-{number:03d}-POST-{entry['post_id']}",
        "source_label": label,
        "source_url": entry["url"],
        "source_post_id": entry["post_id"],
    }


def make_map(index: dict, slug: str) -> dict:
    if not isinstance(index.get("chapters"), list) or not index["chapters"]:
        raise ValueError(f"Missing chapter links for {slug}")
    expected_tid = 14046 if slug == SOURCES[0] else 38982
    if index.get("thread_url") != f"https://xossipy.com/thread-{expected_tid}.html":
        raise ValueError("Source thread mismatch")
    entries = []
    seen = set()
    for seq, chapter in enumerate(index["chapters"], start=1):
        if chapter.get("sequence") != seq:
            raise ValueError("Non-contiguous index order")
        pid = chapter.get("post_id")
        expected_url = f"https://xossipy.com/thread-{expected_tid}-post-{pid}.html"
        if not isinstance(pid, int) or pid < 1 or pid in seen or chapter.get("url") != expected_url:
            raise ValueError(f"Invalid, duplicate or cross-thread link: {pid}")
        seen.add(pid)
        entries.append(normalize_entry(chapter, slug))
    author_episodes = sorted({x["episode_number"] for x in entries if x["episode_number_basis"] == "author_update"})
    return {
        "story": slug,
        "title": index.get("title", slug),
        "author": index.get("author"),
        "thread_url": index["thread_url"],
        "index_url": index.get("index_url"),
        "index_sha256": index.get("index_sha256"),
        "captured_utc": index.get("captured_utc"),
        "linked_post_count": len(entries),
        "authored_update_numbers": author_episodes,
        "episode_numbering_note": (
            "Update numbers and parts are parsed from the author's index labels. "
            "One numbered update may contain multiple linked parts."
            if slug == SOURCES[0] else
            "Episode numbers are assigned by index sequence; the index itself "
            "does not provide numeric chapter labels for these links."
        ),
        "entries": entries,
        "contains_story_text": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path(__file__).parent / "output")
    parser.add_argument("--destination", type=Path, default=None)
    args = parser.parse_args()
    destination = args.destination or args.source_root
    for slug in SOURCES:
        path = args.source_root / slug / "index.json"
        index = json.loads(path.read_text(encoding="utf-8"))
        doc = make_map(index, slug)
        out = destination / slug / "episode-map.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            f"{slug}: {doc['linked_post_count']} linked posts; "
            f"{len(doc['authored_update_numbers'])} numbered author updates"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
