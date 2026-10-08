# Jaya story extractor (raw archival)

This folder is separate from the Midnight-bet reader. It does **not** change the existing story, UI, or episodes.

## Current status

The Python extraction tool is installed. The exact source/chapter URL for **"Jaya, a young college teacher"** has **not yet been verified**, so **no Jaya story text has been downloaded or committed**. The previously specified site was *Erotica PhD*, but a verified Jaya chapter URL is still needed. Do not substitute a similarly named story.

## Setup

Python 3.10 or newer:

```bash
cd story-extractor
python -m pip install -r requirements.txt
```

## Extract actual story chapters

First open a verified chapter in your browser and inspect its HTML to identify the CSS selector containing **only** the original story body. Optionally identify the next-chapter link CSS selector.

```bash
python extract_jaya.py \
  --url "https://EXACT-SOURCE-SITE/EXACT-JAYA-CHAPTER-1" \
  --selector ".ACTUAL-STORY-BODY-SELECTOR" \
  --next-selector "a.ACTUAL-NEXT-CHAPTER-SELECTOR" \
  --max-pages 100 \
  --delay 2
```

If the source does not have consistent next links, supply a URL list instead:

```bash
python extract_jaya.py \
  --chapter-list jaya-chapters.txt \
  --selector ".ACTUAL-STORY-BODY-SELECTOR"
```

Create `jaya-chapters.txt` as a UTF-8 file with one real chapter URL per line in order. Use `--resume` after interruption; completed URLs are skipped and existing files are not overwritten.

## Output

The local ignored folder `output/jaya/` receives:

- `chapter_001.html`: **original downloaded HTML response bytes** (the authoritative snapshot).
- `chapter_001.txt`: readable text directly extracted from the specified page element, including text in inline markup, breaks, and paragraph boundaries. This is not an edited or summarized version.
- `manifest.json`: verified source URL, resolved URL, chapter order, capture timestamp, text character count, next-page URL, and SHA-256 hashes for HTML and text.

Word-for-word fidelity is checked against the HTML snapshot; HTML layout/whitespace can differ from plaintext. Readable text is not necessarily byte-for-byte identical to the source markup.

## Safeguards

- Does not discover a story by guessing its title or replace it with search results.
- Respects `robots.txt`, server errors, request delays and same-site links.
- Does not bypass paywalls, CAPTCHA, authentication, or access restrictions.
- Stops if the CSS selector fails or extracted content is unusually short.
- Does not automatically commit scraped story content into this **public** GitHub repository.
- Only archive or redistribute a work if you own it or have permission to do so.

## Run local tests

```bash
python -m unittest discover -s tests -v
```
