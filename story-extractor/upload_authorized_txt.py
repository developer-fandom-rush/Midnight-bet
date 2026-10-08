#!/usr/bin/env python3
"""Upload authorized Jaya episode TXT files directly to their Google Drive folders.

The uploader NEVER scrapes Xossipy or republishes third-party writing.
Input: episode-map.json and private_archive/manifest.json created locally
from content you have rights to use, together with episode .txt files.
One .txt per linked source part; same numbered update remains recognizable
in the filename, including multipart updates. No ZIP is created.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
from pathlib import Path

FOLDERS = {
    "jaya-young-college-teacher": "teacher_folder_id",
    "jaya-lonely-wife": "lonely_folder_id",
}


def valid_local_txt(path: Path, archive: Path) -> bytes:
    """Reject traversal, symlinks, empty files, and non-UTF8 input."""
    root = archive.resolve()
    resolved = path.resolve()
    if path.is_symlink() or not resolved.is_relative_to(root) or path.suffix.lower() != ".txt":
        raise ValueError(f"Invalid chapter file path: {path}")
    raw = path.read_bytes()
    if not raw.strip() or not raw.decode("utf-8").strip():
        raise ValueError(f"Empty chapter file: {path}")
    return raw


def episode_filename(entry: dict) -> str:
    ep = entry["episode_number"]
    if not isinstance(ep, int) or ep < 0 or ep > 9999:
        raise ValueError(f"Invalid episode number: {ep!r}")
    post_id = entry["source_post_id"]
    if not isinstance(post_id, int) or post_id < 1:
        raise ValueError("Invalid source post ID")
    prefix = f"EP_{ep:03d}"
    if entry.get("section") == "introduction":
        prefix = "Introduction"
    part = entry.get("part")
    if part:
        cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", str(part)).strip("_")
        if cleaned:
            prefix += "_Part_" + cleaned[:40]
    return f"{prefix}_Post_{post_id}.txt"


def prepare_uploads(source_root: Path, slug: str):
    root = source_root / slug
    episode_map = json.loads((root / "episode-map.json").read_text(encoding="utf-8"))
    archive = root / "private_archive"
    manifest = json.loads((archive / "manifest.json").read_text(encoding="utf-8"))
    if episode_map.get("story") != slug or manifest.get("story") != slug:
        raise ValueError(f"Story identity mismatch for {slug}")
    posts = {}
    for post in manifest.get("posts", []):
        pid = post.get("post_id")
        if pid in posts:
            raise ValueError(f"Duplicate archived post {pid}")
        posts[pid] = post
    planned = []
    for entry in episode_map.get("entries", []):
        pid = entry["source_post_id"]
        if pid not in posts:
            continue  # missing local authorized source file: not a completed archive
        post = posts[pid]
        if post.get("url") != entry["source_url"]:
            raise ValueError(f"URL mismatch for post {pid}")
        file_name = post.get("text_file", "")
        if Path(file_name).name != file_name:
            raise ValueError(f"Unsafe file name for post {pid}")
        file_path = archive / file_name
        raw = valid_local_txt(file_path, archive)
        digest = hashlib.sha256(raw).hexdigest()
        if post.get("text_sha256") != digest:
            raise ValueError(f"SHA-256 mismatch for archived post {pid}")
        planned.append({
            "drive_filename": episode_filename(entry),
            "source_post_id": pid,
            "source_url": entry["source_url"],
            "sha256": digest,
            "text": raw,
        })
    return planned, len(episode_map["entries"])


def existing_file(service, folder: str, filename: str) -> dict | None:
    quoted = filename.replace("\\", "\\\\").replace("'", "\\'")
    q = f"'{folder}' in parents and name = '{quoted}' and trashed = false"
    results = service.files().list(
        q=q, fields="files(id,name,appProperties),nextPageToken",
        pageSize=100
    ).execute()
    items = results.get("files", [])
    if len(items) > 1:
        raise RuntimeError(f"Duplicate Drive names for {filename}; refusing to guess")
    return items[0] if items else None


def upload_one(service, folder: str, entry: dict, overwrite: bool):
    from googleapiclient.http import MediaIoBaseUpload

    prev = existing_file(service, folder, entry["drive_filename"])
    media = MediaIoBaseUpload(io.BytesIO(entry["text"]), mimetype="text/plain; charset=utf-8", resumable=False)
    properties = {
        "sourcePostId": str(entry["source_post_id"]),
        "sourceSha256": entry["sha256"],
    }
    if prev:
        old_hash = (prev.get("appProperties") or {}).get("sourceSha256")
        if old_hash == entry["sha256"]:
            return "unchanged", prev["id"]
        if not overwrite:
            raise FileExistsError(
                f"Existing file differs: {entry['drive_filename']}; use --overwrite"
            )
        result = service.files().update(
            fileId=prev["id"],
            body={"appProperties": properties},
            media_body=media,
            fields="id",
        ).execute()
        return "updated", result["id"]
    result = service.files().create(
        body={
            "name": entry["drive_filename"],
            "parents": [folder],
            "mimeType": "text/plain",
            "appProperties": properties,
        },
        media_body=media,
        fields="id",
    ).execute()
    return "created", result["id"]


def run(args) -> None:
    chosen = list(FOLDERS) if args.story == "all" else [args.story]
    plans = []
    for slug in chosen:
        chapter_list, total = prepare_uploads(args.source_root, slug)
        folder_id = getattr(args, FOLDERS[slug])
        print(f"{slug}: {len(chapter_list)}/{total} authorized TXT files available locally")
        if not chapter_list:
            print("  No raw text available. No placeholder files will be uploaded.")
        plans.append((slug, folder_id, chapter_list))

    if not args.upload:
        print("Dry run only. To upload authorized content, pass --upload --rights-confirmed.")
        return
    if not args.rights_confirmed:
        raise PermissionError(
            "Uploading full text requires --rights-confirmed: confirm ownership/permission."
        )
    if not all(folder for _, folder, files in plans if files):
        raise ValueError("Missing Drive destination folder IDs")

    import google.auth
    from googleapiclient.discovery import build
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/drive"])
    service = build("drive", "v3", credentials=creds, cache_discovery=False)
    for slug, folder, files in plans:
        if not files:
            continue
        target = service.files().get(fileId=folder, fields="id,mimeType,trashed").execute()
        if target.get("mimeType") != "application/vnd.google-apps.folder" or target.get("trashed"):
            raise ValueError(f"Invalid destination folder: {slug}")
        for entry in files:
            status, file_id = upload_one(service, folder, entry, args.overwrite)
            print(f"  {status}: {entry['drive_filename']} ({file_id})")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path(__file__).parent / "output")
    parser.add_argument("--story", choices=["all", *FOLDERS], default="all")
    parser.add_argument("--teacher-folder-id", dest="teacher_folder_id", default="")
    parser.add_argument("--lonely-folder-id", dest="lonely_folder_id", default="")
    parser.add_argument("--upload", action="store_true")
    parser.add_argument("--rights-confirmed", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    try:
        run(args)
        return 0
    except (FileNotFoundError, ValueError, RuntimeError, PermissionError, OSError) as exc:
        parser.exit(1, f"Stopped: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
