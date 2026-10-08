#!/usr/bin/env python3
"""Sync Jaya chapter-link metadata (not story text) to a Drive folder.

Requires Application Default Credentials with permission to write the folder.
Never uploads private_archive, downloaded HTML, or chapter plaintext.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

STORIES = {
    "jaya-young-college-teacher": 14046,
    "jaya-lonely-wife": 38982,
}


def safe_index(source_root: Path, slug: str) -> dict:
    """Validate the scraper index and return ONLY public chapter-link metadata."""
    path = source_root / slug / "index.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("chapters"), list):
        raise ValueError(f"Malformed index: {path}")
    if not payload["chapters"]:
        raise ValueError(f"Index contains no links: {path}")
    expected_thread_id = STORIES[slug]
    thread_url = f"https://xossipy.com/thread-{expected_thread_id}.html"
    if payload.get("thread_url") != thread_url:
        raise ValueError(f"Wrong source thread for {slug}")

    rows, seen = [], set()
    for index, chapter in enumerate(payload["chapters"], start=1):
        post_id = chapter.get("post_id")
        url = chapter.get("url")
        if not isinstance(post_id, int) or post_id < 1 or post_id in seen:
            raise ValueError(f"Invalid/repeated post ID at entry {index} in {slug}")
        required_url = (
            f"https://xossipy.com/thread-{expected_thread_id}-post-{post_id}.html"
        )
        if url != required_url:
            raise ValueError(f"Post {post_id} does not match expected source URL")
        seen.add(post_id)
        rows.append({
            "sequence": index,
            "post_id": post_id,
            "url": required_url,
        })

    return {
        "story_key": slug,
        "title": payload.get("title", slug),
        "author": payload.get("author", ""),
        "thread_url": thread_url,
        "index_url": payload.get("index_url", ""),
        "captured_utc": payload.get("captured_utc"),
        "linked_post_count": len(rows),
        "chapters": rows,
        "contains_story_text": False,
    }


def existing_file(service, parent_id: str, name: str) -> str | None:
    name_escaped = name.replace("\\", "\\\\").replace("'", "\\'")
    query = (
        f"'{parent_id}' in parents and name = '{name_escaped}' "
        "and trashed = false"
    )
    response = service.files().list(
        q=query, fields="nextPageToken,files(id,name)", page_size=100
    ).execute()
    found = response.get("files", [])
    if len(found) > 1:
        raise RuntimeError(f"Multiple copies of {name}; manual review needed")
    return found[0]["id"] if found else None


def sync(args: argparse.Namespace) -> None:
    uploads = []
    for slug in STORIES:
        index_path = args.source_root / slug / "index.json"
        if not index_path.exists():
            raise FileNotFoundError(
                f"{index_path} missing; first run: python xossipy_jaya.py --story all"
            )
        payload = safe_index(args.source_root, slug)
        uploads.append((
            f"{slug}-chapter-links.json",
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        ))
        print(f"Ready: {slug}, {payload['linked_post_count']} links")

    if args.dry_run:
        print("Dry run: no Drive changes performed")
        return
    if not args.folder_id or "/" in args.folder_id:
        raise ValueError("--folder-id must be a real Google Drive folder ID")
    try:
        import google.auth
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseUpload
    except ImportError as exc:
        raise RuntimeError(
            "Install Drive dependencies: pip install -r requirements-drive.txt"
        ) from exc

    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    service = build("drive", "v3", credentials=credentials, cache_discovery=False)
    folder = service.files().get(
        fileId=args.folder_id, fields="id,name,mimeType,trashed"
    ).execute()
    if folder.get("trashed") or folder.get("mimeType") != "application/vnd.google-apps.folder":
        raise ValueError("Destination is not an active Drive folder")

    for name, content in uploads:
        existing_id = existing_file(service, args.folder_id, name)
        media = MediaIoBaseUpload(
            io.BytesIO(content.encode("utf-8")),
            mimetype="application/json",
            resumable=False,
        )
        if existing_id:
            result = service.files().update(
                fileId=existing_id, media_body=media,
                fields="id,name,webViewLink",
            ).execute()
            action = "Updated"
        else:
            result = service.files().create(
                body={
                    "name": name,
                    "mimeType": "application/json",
                    "parents": [args.folder_id],
                },
                media_body=media,
                fields="id,name,webViewLink",
            ).execute()
            action = "Created"
        print(f"{action}: {result['name']} (id={result['id']})")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root", type=Path, default=Path(__file__).parent / "output"
    )
    parser.add_argument("--folder-id", default="", help="Existing Jaya Drive folder ID")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        sync(args)
        return 0
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"Drive sync stopped: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
