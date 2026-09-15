# Cancer Data Resource Navigator

A GitHub Pages site for finding online resources that contain cancer/tumor-related data. It is organized by research need and links each resource back to its official site.

## What makes this version dynamic?

The repository has two layers:

1. **Curated registry**: the Excel workbook remains the human-reviewed source of truth for scientific fields such as data modalities, cancer coverage, usage score, advantages and limitations.
2. **Live verification**: GitHub Actions periodically checks each registered official URL and records HTTP status, final URL, page title, last-checked date and lightweight evidence snippets.

The workflow also scans the NAR Molecular Biology Database Collection for **candidate cancer-related resources**. Candidates are written to `data/nar_candidates.json` with `candidate_requires_review` and are not silently published as authoritative resources. This is intentional: automated discovery can find omissions, but it should not invent scientific metadata.

## Directory structure

```text
.
├── index.html
├── styles.css
├── app.js
├── requirements.txt
├── Cancer_Data_Resource_Master_Directory_Clean_Standardized_2026.xlsx
├── data/
│   ├── resources.json
│   ├── resources.js
│   ├── resources_live.json
│   ├── live_verification.json
│   └── nar_candidates.json
├── scripts/
│   ├── build_data.py
│   ├── refresh_resources.py
│   ├── merge_live_verification.py
│   └── discover_nar_candidates.py
└── .github/workflows/update.yml
```

## Local update

```bash
pip install -r requirements.txt
python scripts/build_data.py Cancer_Data_Resource_Master_Directory_Clean_Standardized_2026.xlsx data/resources.json
python scripts/refresh_resources.py data/resources.json data/live_verification.json data/resources_live.json
python scripts/merge_live_verification.py data/resources.json data/resources_live.json data/resources.js
python scripts/discover_nar_candidates.py data/nar_candidates.json
```

Then open `index.html` or run a local server:

```bash
python -m http.server 8000
```

Open `http://localhost:8000/`.

## GitHub Pages

Create a public repository, upload this project, and enable:

**Settings → Pages → Deploy from branch → main → / (root)**

The scheduled GitHub Action runs every Monday and can also be started manually from **Actions → Verify and update cancer resources → Run workflow**.

## Accuracy design

The system intentionally separates **observed live evidence** from **curated scientific metadata**. An HTTP check can tell us that a website is reachable, but it cannot safely infer that a page's number is a unique patient count rather than sample count. Therefore fields such as patients, cells, modalities, cost and usage score remain curated unless a future source-specific extractor is explicitly implemented and tested.

Each resource can carry:

- Verification Status
- Last Checked
- Live HTTP Status
- Live Final URL
- Live Page Title
- Live Evidence Snippets
- Source / Provenance

## NAR source

The 2026 NAR editorial states that the Online Molecular Biology Database Collection had **2,173 databases** after its annual review, with 899 entries updated, 96 new resources added, and 319 discontinued URLs removed. The editorial itself is not the 2,173-row directory; the directory is a separate maintained online collection.

## Accuracy model (v2)

The dynamic verifier is deliberately **evidence-first**. It checks each registered official URL weekly and stores observed quantitative facts with the exact source URL and timestamp. It does **not** silently overwrite curated scientific fields. This prevents common category errors such as treating samples as patients or datasets as studies.

Generated files:

- `data/evidence.json` — timestamped evidence from official pages.
- `data/review_queue.json` — changes/facts that should be reviewed before promotion into curated fields.
- `data/resources_live.json` — curated records plus current verification status.
- `data/nar_candidates.json` — newly discovered NAR candidates for review.

Recommended workflow: official API/metadata when available > official webpage > primary database paper > recent review. Add source-specific API adapters over time for high-value resources such as GDC, PDC, IDC, CELLxGENE and DepMap. Keep `Usage Score` editorial/manual unless a documented scoring methodology is adopted.
