# Story Extractor — Jaya (two separate Xossipy stories)

This tool is separate from the Midnight-bet site. No existing episodes, UI, cast or story data are modified.

## Verified source indexes

| Slug | Title | Author | Thread | Author's index post |
| --- | --- | --- | --- | --- |
| `jaya-young-college-teacher` | Jaya - young college teacher | kuttoosan009 | [14046](https://xossipy.com/thread-14046.html) | [752747](https://xossipy.com/thread-14046-post-752747.html) |
| `jaya-lonely-wife` | Jaya - A Lonely Wife's Adventures | badri.rao2006 | [38982](https://xossipy.com/thread-38982.html) | [4500941](https://xossipy.com/thread-38982-post-4500941.html) |

**These are different stories, not confirmed continuations of each other.** The site displays 114 forum pages for thread 14046 and 24 forum pages for thread 38982; these are *not* chapter counts.

## Run index discovery for BOTH stories

Python 3.10+ required.

```bash
cd story-extractor
python -m pip install -r requirements.txt
python xossipy_jaya.py --story all
```

This discovers chapter/update **post links directly from the authors' index posts**, without crawling the forum's many reader replies. It writes:

```text
output/
  jaya-young-college-teacher/index.json
  jaya-lonely-wife/index.json
```

Each index record has the original order, author, post ID, and canonical source URL. It intentionally keeps both stories separate. This script fetches *only the index pages* in default mode, not the story text.

If a source changes its HTML structure or robots.txt denies access, the tool stops and prints an error. Verify the results and do not interpret missing links as missing chapters. Some updates may not be in the author's index. Discovering continuations is a separate task.

## Archival mode (only for content you are authorized to copy)

To save source-response HTML and readable post text to your local machine (not GitHub), use:

```bash
python xossipy_jaya.py --story all --archive --confirm-rights
```

- Each archived chapter gets a raw downloaded `.html` response and a `.txt` containing text extracted from only the linked post, not adjacent reader comments.
- `private_archive/manifest.json` records source post links, response hashes, text hashes, text character counts, and timestamps.
- Already manifested posts are skipped on subsequent runs; unexpected existing files stop the process rather than silently overwriting them.
- The text rendering preserves authored words but HTML-to-text layout can change whitespace. Keep original HTML as the fidelity reference.
- The entire `output/` directory is Git-ignored. **Do not commit or publish third-party story text** without rights or permission.
- The utility respects robots.txt and request delays. It does not bypass login, CAPTCHA, rate limits, paywalls or other access controls.

The earlier generic `extract_jaya.py` remains available for other verified, authorized sources, but `xossipy_jaya.py` is the recommended index-driven workflow for these two links.

## Local offline unit tests

```bash
python -m unittest discover -s tests -v
```

## Work status

- Verified both story titles, distinct authors, and index post links.
- Source-specific extraction/index-discovery Python code committed to GitHub.
- Full story extraction has **not** been run or uploaded. Publicly accessible text is not automatically licensed for republication, and live crawler execution was unavailable in this session.

## Optional automated sync: save both chapter-link indexes to Google Drive

This workflow uploads **link metadata only**, not copyrighted text or HTML. It requires a Google identity with write access to your existing Stories / Jaya Story folder. Keep authentication credentials out of Git.

```bash
cd story-extractor
python -m pip install -r requirements-drive.txt
python xossipy_jaya.py --story all
python sync_indexes_to_drive.py --dry-run
python sync_indexes_to_drive.py --folder-id YOUR_JAYA_STORY_FOLDER_ID
```

This sync validates the chapter post URLs and writes one `*-chapter-links.json` file per story. If a file already exists with the same name in the destination folder, it updates that file rather than creating duplicates. Uses Google Application Default Credentials (`google.auth.default`), with Google Drive authorization handled outside this repository. The sync never uploads `private_archive` or `*.txt` chapter files.

**Execution status:** The GitHub code has been committed, but the remote Xossipy scraping, full chapter text archive, and automatic Drive sync have not run in this session. A source tracker document with both index links has been saved directly to the existing Drive folder.

## Episode-based mappings (source links only)

After the index discovery, build the two episode maps:

```bash
python episode_map.py --source-root output
```

This creates `output/<story>/episode-map.json` for each story. For
**Young College Teacher**, the 42 direct linked posts are grouped under
**Introduction + 33 author-numbered updates**; some updates have multiple
post links/parts. For **A Lonely Wife's Adventures**, the index contains
**18 linked posts**; the numeric EP-001…EP-018 sequence is assigned from
index order rather than author-provided episode numbers. Each entry keeps
its original post ID and permalink.

Verified GitHub Actions metadata/index run:
https://github.com/developer-fandom-rush/Midnight-bet/actions/runs/37753740419

Verified episode-mapping ZIP saved to Drive:
https://drive.google.com/file/d/1w9GEFW6UIImJo7YpUvNesWI65JyvE_Ws/view

**Note:** These files are maps of where to read original posts, not
verbatim copies of the author's story chapters.

## Direct episode TXT upload to Google Drive (NO ZIP)

Drive destination folders already created:

- Young College Teacher: https://drive.google.com/drive/folders/1RR8-qrPC8Dky5t9uSs3_t0gQd5W5dm7Y
- A Lonely Wife's Adventures: https://drive.google.com/drive/folders/1RyvJENbbg35KslAAJzfvdQOyUTRC7Pgm

If you own the source material or have permission to copy/archive it, run the local
authorized archive step described above (which produces
`output/<story>/private_archive/post_*.txt` and the manifest). Next build
episode maps with `python episode_map.py`.

Then install the Drive dependencies and upload individual TXT files:

```bash
python -m pip install -r requirements-drive.txt
python upload_authorized_txt.py \
  --teacher-folder-id 1RR8-qrPC8Dky5t9uSs3_t0gQd5W5dm7Y \
  --lonely-folder-id 1RyvJENbbg35KslAAJzfvdQOyUTRC7Pgm \
  --upload --rights-confirmed
```

- Creates **individual** `EP_001_Post_*.txt` etc., preserving separate multipart posts.
- No ZIP archives, placeholders or story summaries are uploaded.
- Checks local episode-map post IDs, URLs and SHA-256 hashes before upload.
- Does not commit third-party writing to the public GitHub repository.
- Defaults to dry-run unless both `--upload` and `--rights-confirmed` are set.
- If an existing target TXT has changed, upload stops rather than overwriting it. Use
  `--overwrite` only after comparing the local authorized version.
- Existing ZIPs, source registries and indexes have been **moved** under
  `Stories/Jaya Story/_Index Backups and Tracker`. They were not deleted.
- An empty story folder is not evidence that the raw episode archive exists.

## Verify real Xossipy post DOM selectors (no screenshots required)

For HTML sources, DOM selection is more precise than taking page screenshots
and using OCR. The `verify_dom.py` script validates real indexed source posts
by selecting `#pid_<post_id>` (falling back to
`#post_<post_id> .post_body`), verifies that extracted text is nonempty,
and records only post IDs, selectors, byte/character counts and SHA-256.
**It does not save or publish story text or source-page snapshots.**

```bash
python xossipy_jaya.py --story all
python verify_dom.py --per-story 0 --delay 2
```

The GitHub Actions workflow `Jaya DOM selector audit` uses
`--per-story 0` to inspect **all** chapter URLs in both index lists
(42 + 18 as of the last discovery). View the workflow run for results.
This validation is distinct from a rights-authorized full-text archive.

### Verified DOM audit result — October 8, 2026

The all-post workflow completed successfully:
https://github.com/developer-fandom-rush/Midnight-bet/actions/runs/37757081000

- 60 of 60 directly indexed Xossipy posts passed DOM body lookup
  (42 Young College Teacher, 18 Lonely Wife).
- 0 missing post bodies; all 18 offline tests passed.
- Text lengths and SHA-256 were computed in memory solely to validate
  selection, not persisted as full story content.
- Nothing from this audit should be represented as archived `.txt`
  episodes; the two Drive story folders remain unfilled pending
  independently authorized source copies.

## URL -> story DOM -> individual RAW TXT files

Run the actual text extractor (not the earlier metadata-only DOM audit):

```bash
cd story-extractor
python -m pip install -r requirements.txt

# ONE page URL -> ONE text file
python url_to_txt.py \
  --url "https://xossipy.com/thread-14046-post-752861.html" \
  --output-dir "./raw_txt/young-college-teacher"

# MANY page URLs (one per line in a local input.txt file)
python url_to_txt.py --url-file input.txt --output-dir "./raw_txt"

# Existing episode map -> separate episode-numbered text files
python xossipy_jaya.py --story all
python episode_map.py
python url_to_txt.py \
  --episode-map output/jaya-young-college-teacher/episode-map.json \
  --output-dir "./raw_txt/young-college-teacher"
python url_to_txt.py \
  --episode-map output/jaya-lonely-wife/episode-map.json \
  --output-dir "./raw_txt/lonely-wife"
```

**DOM rule:** From Xossipy `thread-N-post-P.html` URL, select
`#pid_P` (fallback `#post_P .post_body`), using that URL's post ID.
Do not select a whole `thread` div or other people's replies.
On unrelated sites, pass an explicit selector such as
`--selector "div.chapter-content"`; exactly one match must exist.

**Output:** One UTF-8 `EP_###_Post_#.txt` or mapped
`EP_###_Part_#_Post_#.txt` per page, and
`extraction-status.json` recording which individual files were
saved, skipped or failed. The status JSON is supplementary: **actual
text is written to the .txt files**. No ZIP, no summaries.

**Scope:** The script is a local utility for material you are
authorized to copy or archive. It is not run by the public GitHub
Actions audit, and the repository does not contain original authors'
full story text. It does not upload story text to Drive by itself.
Use the separate authorized-archive Drive uploader only when its
expected manifest and matching source files are present.

Offline tests: `python -m unittest discover -s tests -v`.

## Built-in Jaya URL inputs — no manual URL paste needed

All **60 source post URLs** are committed as separate input files:

- `inputs/jaya-young-college-teacher.json` — 42 post URLs, author update/part numbers
- `inputs/jaya-lonely-wife.json` — 18 post URLs, index-order numbers

`url_to_txt.py` **now reads both files by default**. Run from
`story-extractor/` with the dependencies installed:

```bash
# Live source DOM proof without persisting third-party story prose
python url_to_txt.py --story jaya-young-college-teacher --take-first 1 --inspect-only --preview-words 12
python url_to_txt.py --story jaya-lonely-wife --take-first 1 --inspect-only --preview-words 12

# For material you are authorized to copy, direct URL -> original post div -> TXT
python url_to_txt.py --story jaya-young-college-teacher --output-dir raw_txt
python url_to_txt.py --story jaya-lonely-wife --output-dir raw_txt

# Or both stories in one command, saved in separate story subfolders
python url_to_txt.py --output-dir raw_txt
```

The script identifies `#pid_{post_id}` (fallback `#post_{post_id} .post_body`),
extracts the post content only, preserves readable line breaks and writes
one `.txt` per linked post in its matching story directory.

**Actual live extraction proof:** GitHub Actions
https://github.com/developer-fandom-rush/Midnight-bet/actions/runs/37761747097
verified the built-in introduction URL (1,030 characters) and the first
Lonely Wife post (18,245 characters). This smoke-test uses
`--inspect-only`, so no full-text file is saved by Actions.
