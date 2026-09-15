#!/usr/bin/env python3
"""Merge live verification fields into resources.js after a refresh."""
from __future__ import annotations
import json, sys
from pathlib import Path

def main():
    if len(sys.argv) != 4:
        print("Usage: merge_live_verification.py BASE.json UPDATED.json JS", file=sys.stderr); return 2
    updated = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    out = Path(sys.argv[3]); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("window.CANCER_RESOURCE_DATA = " + json.dumps(updated, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8")
    return 0
if __name__ == "__main__": raise SystemExit(main())
