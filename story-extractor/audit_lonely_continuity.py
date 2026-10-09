#!/usr/bin/env python3
"""Metadata-only source continuity audit for Jaya: A Lonely Wife's Adventures.

Fetches exact authored post DOM and reports short anchor snippets at either end
only for internal draft provenance. Does not save chapter text.
"""
from collections import Counter
import re
import requests
from bs4 import BeautifulSoup
from bundled_urls import bundled_pages
from xossipy_jaya import request_page, find_post_body
from extract_jaya import extract_story_text

CAST = ("Jaya", "Mani", "Rakesh", "Reema", "Anil", "Seema", "stranger", "watchman", "Sharma")
EVENTS = ("phone", "call", "message", "WhatsApp", "school", "teacher", "college", "door", "night", "morning", "house", "room", "bus", "office", "husband", "wife")
session = requests.Session()
session.headers["User-Agent"] = "MidnightBetStoryArchiver/1.0 (personal archival; respects robots.txt)"
cache = {}
pages = bundled_pages("jaya-lonely-wife")
for idx, (url, entry) in enumerate(pages, 1):
    raw, html, delay = request_page(session, url, cache, 0.5)
    post_id = entry["source_post_id"]
    node = find_post_body(html, post_id)
    copy=BeautifulSoup(str(node), "html.parser")
    for el in copy.select("blockquote,.quote_body,.quote"):
        el.decompose()
    text=copy.get_text(" ", strip=True)
    counts={k:len(re.findall(r"\b"+re.escape(k)+r"\b",text,flags=re.I)) for k in CAST}
    counts={k:v for k,v in counts.items() if v}
    eventcounts={k:len(re.findall(r"\b"+re.escape(k)+r"\b",text,flags=re.I)) for k in EVENTS}
    evtop=dict(Counter(eventcounts).most_common(7))
    print(f"POST {idx:02d} id={post_id} words={len(text.split())} cast={counts} narrative_terms={evtop}",flush=True)
    if idx>=15:
        # Strictly <=20 words across both snippets per post.
        words=text.split()
        first=" ".join(words[:8])
        last=" ".join(words[-12:])
        print(f"SHORT_EDGES {idx:02d} BEGIN={first!r} END={last!r}",flush=True)
