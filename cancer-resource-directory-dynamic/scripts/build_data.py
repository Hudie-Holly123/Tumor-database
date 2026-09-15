#!/usr/bin/env python3
"""Build website JSON from the standardized workbook, preserving cross-category entries."""
from __future__ import annotations
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
    "docrel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
CATEGORY_SHEETS = [
    ("01_Genomics_Multiomics", "Cancer Genomics & Multi-omics / Patient Cohorts"),
    ("02_General_Repositories", "General Omics Repositories Containing Cancer Data"),
    ("03_Single_Cell", "Cancer Single-Cell Data Resources"),
    ("04_Spatial_Omics", "Spatial Transcriptomics & Spatial Omics"),
    ("05_Proteomics", "Cancer Proteomics & Proteogenomics"),
    ("06_Functional_Genomics", "Cancer Models & Functional Genomics / CRISPR"),
    ("07_Drug_Response", "Cancer Drug Response & Resistance"),
    ("08_Genomics_Portals", "Cancer Genomic Alterations & Processed Data Portals"),
    ("09_Imaging_Pathology", "Cancer Imaging & Digital Pathology"),
    ("10_Clinical_Outcomes", "Cancer Clinical / Epidemiology / Outcomes"),
    ("11_Immunology", "Cancer Immunology & Immunotherapy"),
    ("12_Microbiome", "Cancer Microbiome"),
    ("13_Metabolomics", "Cancer Metabolomics & Lipidomics"),
    ("14_Liquid_Biopsy_EV", "Extracellular Vesicle / Liquid Biopsy / CTC / ctDNA"),
    ("15_Specialized_Cancer", "Cancer-Type-Specific & Other Specialized Cancer Resources"),
    ("16_Supporting_Knowledge", "Supporting Cancer Bioinformatics Knowledge Resources"),
]

def col_index(ref):
    m = re.match(r"([A-Z]+)", ref)
    if not m: return 0
    n = 0
    for ch in m.group(1): n = n * 26 + ord(ch) - 64
    return n - 1

def shared_strings(z):
    try: root = ET.fromstring(z.read("xl/sharedStrings.xml"))
    except KeyError: return []
    return ["".join(t.text or "" for t in si.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")) for si in root.findall("main:si", NS)]

def read_sheet(z, target, shared):
    root = ET.fromstring(z.read(target)); rows = []
    max_col = 0
    for row in root.findall("main:sheetData/main:row", NS):
        vals = {}
        for c in row.findall("main:c", NS):
            idx = col_index(c.attrib.get("r", "A1")); max_col = max(max_col, idx)
            t = c.attrib.get("t"); v = c.find("main:v", NS); is_node = c.find("main:is", NS); val = ""
            if t == "inlineStr" and is_node is not None:
                val = "".join(x.text or "" for x in is_node.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t"))
            elif v is not None:
                raw = v.text or ""
                val = shared[int(raw)] if t == "s" and raw.isdigit() and int(raw) < len(shared) else raw
            elif is_node is not None:
                val = "".join(x.text or "" for x in is_node.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t"))
            vals[idx] = val
        rows.append(vals)
    out=[]
    for vals in rows:
        out.append([vals.get(i, "") for i in range(max_col+1)])
    return out

def parse(xlsx):
    with zipfile.ZipFile(xlsx) as z:
        shared = shared_strings(z)
        wb = ET.fromstring(z.read("xl/workbook.xml")); rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        relmap = {r.attrib.get("Id"): r.attrib.get("Target") for r in rels}
        sheets = {}
        for s in wb.findall("main:sheets/main:sheet", NS):
            name=s.attrib.get("name"); rid=s.attrib.get("{"+NS['docrel']+"}id")
            target=relmap.get(rid, "")
            if target:
                target=target.lstrip("/"); target=target if target.startswith("xl/") else "xl/"+target
                sheets[name]=target
        categories=[]; total=0; unique={}
        for sname,title in CATEGORY_SHEETS:
            if sname not in sheets: continue
            rows=read_sheet(z,sheets[sname],shared)
            if not rows: continue
            headers=[str(x).strip() for x in rows[0]]; entries=[]
            for row in rows[1:]:
                item={headers[i]: (str(row[i]).strip() if i<len(row) else "") for i in range(len(headers))}
                name=item.get("Resource / Platform", "").strip()
                if not name: continue
                sc=item.get("Usage Score (1–10)", "")
                try: item["Usage Score (1–10)"]=int(float(sc)) if sc else None
                except ValueError: item["Usage Score (1–10)"]=None
                item["Category Sheet"]=sname; item["Category"]=title; entries.append(item); total+=1; unique[re.sub(r"\s+"," ",name.lower())]=item
            entries.sort(key=lambda x: ((x.get("Usage Score (1–10)") is None), -(x.get("Usage Score (1–10)") or 0), x.get("Resource / Platform", "").lower()))
            categories.append({"id":sname,"title":title,"count":len(entries),"entries":entries})
        return {"version":"2026-09","generatedFrom":xlsx.name,"lastChecked":"2026-09-15","totalCategoryEntries":total,"uniqueResourceNames":len(unique),"categories":categories}

def main():
    if len(sys.argv)!=3:
        print("Usage: build_data.py INPUT.xlsx OUTPUT.json", file=sys.stderr); return 2
    xlsx=Path(sys.argv[1]); out=Path(sys.argv[2])
    data=parse(xlsx); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"Wrote {out}: {data['totalCategoryEntries']} category entries, {data['uniqueResourceNames']} unique resource names")
    return 0
if __name__=="__main__": raise SystemExit(main())
