#!/usr/bin/env python3
"""Evidence-first verifier for Cancer Data Resource Navigator.

Principles:
1. Official URL/API is the source of truth for current facts.
2. Never convert samples -> patients, datasets -> studies, etc.
3. Never overwrite curated scientific fields automatically.
4. Save every observed fact with URL, timestamp, unit and confidence.
5. Conflicts become review items rather than silent edits.
"""
from __future__ import annotations
import json, re, sys, time, hashlib
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

UA = "CancerDataResourceNavigator/2.0 (evidence-first verifier; GitHub Pages)"
TIMEOUT = 25
UNITS = r"patients|cases|donors|participants|samples|specimens|biospecimens|cells|datasets|collections|studies|files|records|models|cell lines|cancer types|tumou?r types|disease types|organs|assay types|TB|GB|PB"
COUNT_RE = re.compile(rf"(?P<prefix>over|more than|approximately|about|~)?\s*(?P<num>\d[\d,.]*)\s*(?P<unit>{UNITS})\b", re.I)


def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def dump(path, obj):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding="utf-8")

def normalize_num(s):
    s=s.replace(",","")
    try: return float(s) if "." in s else int(s)
    except ValueError: return s

def evidence_from_html(html, url):
    soup=BeautifulSoup(html,"html.parser")
    title=soup.title.get_text(" ",strip=True) if soup.title else ""
    text=soup.get_text(" ",strip=True)
    facts=[]; seen=set()
    for m in COUNT_RE.finditer(text[:700000]):
        unit=m.group("unit").lower()
        val=normalize_num(m.group("num"))
        key=(val,unit)
        if key in seen: continue
        seen.add(key)
        a=max(0,m.start()-100); b=min(len(text),m.end()+140)
        facts.append({
            "value":val,"unit":unit,"qualifier":(m.group("prefix") or "").lower(),
            "evidence":text[a:b],"source_url":url,"confidence":"observed_official_page"
        })
        if len(facts)>=30: break
    return title,facts

def fetch(url):
    t=time.time()
    try:
        r=requests.get(url,headers={"User-Agent":UA,"Accept":"text/html,application/json;q=0.9,*/*;q=0.8"},timeout=TIMEOUT,allow_redirects=True)
        ct=r.headers.get("content-type","")
        title=""; facts=[]
        if "html" in ct.lower(): title,facts=evidence_from_html(r.text,r.url)
        return {"ok":r.ok,"http_status":r.status_code,"final_url":r.url,"content_type":ct,
                "title":title,"facts":facts,"error":"","response_ms":round((time.time()-t)*1000),
                "content_hash":hashlib.sha256(r.content).hexdigest()[:20]}
    except requests.RequestException as e:
        return {"ok":False,"http_status":None,"final_url":url,"content_type":"","title":"","facts":[],
                "error":str(e),"response_ms":round((time.time()-t)*1000),"content_hash":""}

def canonical_key(item):
    return (str(item.get("Resource / Platform","")).strip().casefold(), str(item.get("Official / Access URL","")).strip())

def main():
    if len(sys.argv)!=5:
        print("Usage: verify_dynamic.py resources.json evidence.json review_queue.json resources_live.json"); return 2
    data=load(sys.argv[1]); now=datetime.now(timezone.utc).isoformat(timespec="seconds")
    cache={}; evidence=[]; review=[]; updated=json.loads(json.dumps(data))
    for cat in updated.get("categories",[]):
        for item in cat.get("entries",[]):
            url=str(item.get("Official / Access URL","")).strip()
            if not url.startswith(("http://","https://")): continue
            key=canonical_key(item)
            if key not in cache: cache[key]=fetch(url)
            res=cache[key]
            record={"resource":item.get("Resource / Platform",""),"category":cat.get("title",""),"checked_at":now,"requested_url":url,**res}
            evidence.append(record)
            item["Last Checked"]=now[:10]
            item["Verification Status"]="Official source reachable" if res["ok"] else "Needs verification"
            item["Live HTTP Status"]=res["http_status"]
            item["Live Final URL"]=res["final_url"]
            item["Live Page Title"]=res["title"]
            item["Observed Current Facts"]=" | ".join([f'{f["value"]} {f["unit"]}' for f in res["facts"][:10]])
            item["Evidence URL"]=res["final_url"] if res["ok"] else url
            # Never overwrite curated Data Amount. Flag potentially useful observations for human review.
            if res["facts"]:
                review.append({"resource":record["resource"],"category":record["category"],"reason":"Current quantitative facts observed on official page; compare with curated fields before accepting.","curated_data_amount":item.get("Data Amount",""),"observed_facts":res["facts"],"checked_at":now})
            if not res["ok"]:
                review.append({"resource":record["resource"],"category":record["category"],"reason":"Official URL could not be verified.","error":res["error"],"http_status":res["http_status"],"checked_at":now})
    updated["lastLiveVerification"]=now; updated["lastChecked"]=now[:10]; updated["verificationCount"]=len(cache)
    updated["verificationPolicy"]="Evidence-first: live observations never silently overwrite curated scientific fields."
    dump(sys.argv[2],evidence); dump(sys.argv[3],review); dump(sys.argv[4],updated)
    print(f"Checked {len(cache)} unique resource URLs; {len(review)} review items.")
    return 0
if __name__=="__main__": raise SystemExit(main())
