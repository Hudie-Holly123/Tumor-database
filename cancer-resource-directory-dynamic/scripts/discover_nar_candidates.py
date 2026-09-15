#!/usr/bin/env python3
"""Discover potentially cancer-related resources from the NAR collection.

This is intentionally a candidate-discovery step, not blind publication. It
collects links/text from NAR pages and scores candidates using cancer-related
terms. New candidates are written to JSON for human review before inclusion.
"""
from __future__ import annotations

import json
import re
import sys
import time
from collections import deque
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

START_URL = "http://www.oxfordjournals.org/nar/database/c/"
USER_AGENT = "CancerDataResourceNavigator/1.0 (+GitHub Pages; NAR candidate discovery)"
TIMEOUT = 20
MAX_PAGES = 80
KEYWORDS = {
    "cancer": 5, "tumor": 5, "tumour": 5, "oncolog": 5, "carcinoma": 4,
    "sarcoma": 4, "lymphoma": 4, "leukemia": 4, "leukaemia": 4,
    "melanoma": 4, "glioma": 4, "breast cancer": 5, "lung cancer": 5,
    "colorectal": 5, "pancreatic": 5, "prostate cancer": 5,
    "liver cancer": 5, "hepatocellular": 4, "ovarian cancer": 5,
    "gastric cancer": 5, "metastasis": 3, "drug resistance": 3,
    "cancer cell": 4, "tumor microenvironment": 4,
}

def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()

def score(text):
    t = text.lower()
    hits = []
    total = 0
    for term, weight in KEYWORDS.items():
        if term in t:
            total += weight
            hits.append(term)
    return total, hits

def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "data/nar_candidates.json")
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    q = deque([START_URL])
    seen = set()
    candidates = {}
    while q and len(seen) < MAX_PAGES:
        url = q.popleft()
        if url in seen:
            continue
        seen.add(url)
        try:
            r = session.get(url, timeout=TIMEOUT, allow_redirects=True)
            if not r.ok or "html" not in r.headers.get("content-type", "").lower():
                continue
        except requests.RequestException:
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = urljoin(r.url, a["href"])
            parsed = urlparse(href)
            if parsed.scheme not in ("http", "https"):
                continue
            anchor = clean(a.get_text(" ", strip=True))
            parent = clean(a.parent.get_text(" ", strip=True)) if a.parent else ""
            context = f"{anchor} {parent}"[:1200]
            sc, hits = score(context)
            if sc < 4:
                if parsed.netloc == urlparse(r.url).netloc and len(seen) + len(q) < MAX_PAGES:
                    if href not in seen:
                        q.append(href)
                continue
            key = (anchor.lower(), href)
            candidates[key] = {
                "resource": anchor or href,
                "url": href,
                "nar_context": context,
                "keyword_hits": hits,
                "discovery_score": sc,
                "source_page": r.url,
                "status": "candidate_requires_review",
            }
        time.sleep(0.2)
    rows = sorted(candidates.values(), key=lambda x: (-x["discovery_score"], x["resource"].lower()))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"checked_at": time.strftime("%Y-%m-%d"), "candidates": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Discovered {len(rows)} cancer-related NAR candidates from {len(seen)} pages.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
