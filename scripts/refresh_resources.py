#!/usr/bin/env python3
"""Verify registered cancer-resource websites and collect lightweight live evidence.

This script deliberately does NOT overwrite curated scientific fields such as
patient counts, modalities, cost, or usage score. It updates only evidence
that can be safely observed from the official URL: HTTP status, final URL,
page title, meta description, last checked time, and count-like snippets.
"""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

USER_AGENT = "CancerDataResourceNavigator/1.0 (+GitHub Pages; respectful verifier)"
TIMEOUT = 20
COUNT_PATTERNS = [
    re.compile(r"\b(?:over|more than|approximately|about)?\s*[0-9][0-9,\.]*\s*(?:patients|cases|donors|samples|specimens|biospecimens|cells|datasets|studies|files|records)\b", re.I),
    re.compile(r"\b[0-9][0-9,\.]*\s*(?:TB|GB|PB)\b", re.I),
]

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def flatten_resources(data):
    out = []
    for cat in data.get("categories", []):
        for item in cat.get("entries", []):
            url = str(item.get("Official / Access URL", "")).strip()
            if not url.startswith(("http://", "https://")):
                continue
            out.append({"category_id": cat.get("id"), "category": cat.get("title"), "item": item})
    return out

def extract_evidence(html: str):
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    desc = ""
    meta = soup.find("meta", attrs={"name": re.compile("description", re.I)})
    if meta and meta.get("content"):
        desc = meta["content"].strip()
    text = soup.get_text(" ", strip=True)
    snippets = []
    for pat in COUNT_PATTERNS:
        for match in pat.findall(text[:400000]):
            if match not in snippets:
                snippets.append(match)
            if len(snippets) >= 8:
                break
        if len(snippets) >= 8:
            break
    return title, desc, snippets

def check_url(url: str):
    started = time.time()
    try:
        r = requests.get(
            url,
            timeout=TIMEOUT,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
            allow_redirects=True,
        )
        content_type = r.headers.get("content-type", "")
        title = desc = ""
        snippets = []
        if "html" in content_type.lower() and r.text:
            title, desc, snippets = extract_evidence(r.text)
        return {
            "status": "verified" if r.ok else "needs_verification",
            "http_status": r.status_code,
            "final_url": r.url,
            "content_type": content_type,
            "page_title": title,
            "meta_description": desc,
            "evidence_snippets": snippets,
            "response_time_ms": round((time.time() - started) * 1000),
            "error": "",
        }
    except requests.RequestException as exc:
        return {
            "status": "needs_verification",
            "http_status": None,
            "final_url": url,
            "content_type": "",
            "page_title": "",
            "meta_description": "",
            "evidence_snippets": [],
            "response_time_ms": round((time.time() - started) * 1000),
            "error": str(exc),
        }

def main():
    if len(sys.argv) != 4:
        print("Usage: refresh_resources.py resources.json live_verification.json updated_resources.json")
        return 2
    source = Path(sys.argv[1])
    evidence_out = Path(sys.argv[2])
    updated_out = Path(sys.argv[3])
    data = load_json(source)
    checked_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    live = []
    seen = set()
    updated = json.loads(json.dumps(data))

    for cat in updated.get("categories", []):
        for item in cat.get("entries", []):
            url = str(item.get("Official / Access URL", "")).strip()
            if not url.startswith(("http://", "https://")):
                continue
            key = (str(item.get("Resource / Platform", "")).strip().lower(), url)
            if key in seen:
                continue
            seen.add(key)
            result = check_url(url)
            record = {
                "resource": item.get("Resource / Platform", ""),
                "category": cat.get("title", ""),
                "url": url,
                "checked_at": checked_at,
                **result,
            }
            live.append(record)
            item["Last Checked"] = checked_at[:10]
            item["Verification Status"] = "Official URL verified" if result["status"] == "verified" else "Needs verification"
            item["Live HTTP Status"] = result["http_status"]
            item["Live Final URL"] = result["final_url"]
            item["Live Page Title"] = result["page_title"]
            item["Live Evidence Snippets"] = " | ".join(result["evidence_snippets"][:6])

    updated["lastChecked"] = checked_at[:10]
    updated["lastLiveVerification"] = checked_at
    updated["verificationCount"] = len(live)
    evidence_out.parent.mkdir(parents=True, exist_ok=True)
    updated_out.parent.mkdir(parents=True, exist_ok=True)
    evidence_out.write_text(json.dumps(live, ensure_ascii=False, indent=2), encoding="utf-8")
    updated_out.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Verified {len(live)} resource URLs. Wrote {evidence_out} and {updated_out}.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
