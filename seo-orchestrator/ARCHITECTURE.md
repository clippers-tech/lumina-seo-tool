# SEO Orchestrator v1 — Architecture

## System Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    DAILY CRON TRIGGER                         │
│              (Perplexity Computer scheduler)                  │
└─────────────────────────┬────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR CORE                         │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐│
│  │  Config   │  │ Analyzer │  │ Content  │  │   Reporter   ││
│  │  Loader   │  │  Engine  │  │Generator │  │   (MD/JSON)  ││
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘│
│       │              │              │               │        │
└───────┼──────────────┼──────────────┼───────────────┼────────┘
        │              │              │               │
        ▼              ▼              │               ▼
┌──────────────────────────────┐      │    ┌───────────────────┐
│     INTEGRATION LAYER        │      │    │     OUTPUTS       │
│                              │      │    │                   │
│  ┌──────────────────────┐    │      │    │  actions.json     │
│  │   SearchAtlas API    │    │      │    │  report.md        │
│  │  ├─ Rank Tracker     │    │      │    │  run_log.json     │
│  │  ├─ Site Audit       │    │      │    │  nextjs_changes/  │
│  │  ├─ OTTO SEO         │    │      │    └───────────────────┘
│  │  ├─ Press Releases   │    │      │
│  │  └─ Cloud Stacks     │    │      │
│  ├──────────────────────┤    │      │
│  │   Vercel Publisher    │◄───┼──────┘
│  │  (both sites)        │    │
│  ├──────────────────────┤    │
│  │   WordPress (legacy) │    │
│  │  (preserved for use) │    │
│  └──────────────────────┘    │
└──────────────────────────────┘
```

## Data Flow (Per Run)

1. **Config Load** → Read `sites.yaml`, resolve env vars
2. **Data Pull** (per site, ordered by priority):
   - SearchAtlas Rank Tracker → keyword positions, volume, history
   - SearchAtlas Site Audit → technical issues, health scores
   - SearchAtlas OTTO → optimization score, deployed fixes, DR/backlinks
3. **Analysis** → Build candidate actions using rules:
   - Striking distance keywords (pos 8-20) → `UPDATE_ON_PAGE`
   - Unranked high-volume keywords → `NEW_ARTICLE`
   - Positive momentum keywords → `EXPAND_CONTENT`
   - Technical audit issues → `TECH_ISSUE`
   - Low DR / authority gaps → authority building recommendations
4. **Guardrails** → Apply risk controls:
   - Money pages → human review for body changes
   - Conservative mode → medium+ risk → human review
   - Action cap per site (default 10)
   - Balanced mix: 60% tech, 40% keyword actions minimum
5. **Content Generation** → For on-page/expand/new actions:
   - Title tag options (keyword front-loaded, <60 chars)
   - Meta description options (<155 chars, CTA included)
   - Article outlines with word count targets
   - Internal linking suggestions
   - Schema markup recommendations
6. **Output** → `actions.json` + `report.md`

## File Structure

```
seo-orchestrator/
├── ARCHITECTURE.md          # This file
├── run.py                   # CLI entry point
├── requirements.txt         # httpx, pyyaml
│
├── config/
│   ├── __init__.py          # Config loader (YAML → dataclasses)
│   ├── models.py            # Data models (PageRecord, Action, RunLog, etc.)
│   └── sites.yaml           # Site definitions, keywords, API IDs
│
├── integrations/
│   ├── __init__.py
│   ├── searchatlas.py       # SearchAtlas API client (all endpoints)
│   ├── wordpress.py         # WordPress REST API v2 client (preserved for future use)
│   └── vercel_publisher.py  # Vercel/Next.js publishing integration
│
├── core/
│   ├── __init__.py
│   ├── orchestrator.py      # Main orchestration loop
│   ├── analyzer.py          # Decision logic / opportunity scoring
│   ├── content_generator.py # Title/meta/outline generation
│   └── reporter.py          # JSON + Markdown report generation
│
└── outputs/                 # Generated each run
    ├── actions_YYYYMMDD_HHMMSS.json
    ├── report_YYYYMMDD_HHMMSS.md
    └── nextjs_changes/      # Logged changes for Next.js (stub)
```

## SearchAtlas API Mapping

| API Service | Base URL | Auth Method |
|-------------|----------|-------------|
| Rank Tracker | `keyword.searchatlas.com/api/v1/` | Query param: `searchatlas_api_key` |
| Rank Tracker v2 | `keyword.searchatlas.com/api/v2/` | Query param: `searchatlas_api_key` |
| Site Audit | `sa.searchatlas.com/api/v2/` | Header: `x-api-key` |
| OTTO SEO | `sa.searchatlas.com/api/v2/otto-projects/` | Header: `x-api-key` |
| Press Release | `ca.searchatlas.com/api/cg/v1/` | Header: `Authorization: Bearer` |
| Cloud Stacks | `ca.searchatlas.com/api/cg/v1/` | Header: `Authorization: Bearer` |
| Tasks (polling) | `ca.searchatlas.com/api/core/v1/` | Header: `Authorization: Bearer` |

## Project IDs (Your Sites)

| Site | Rank Tracker ID | Site Audit ID | OTTO UUID |
|------|----------------|---------------|-----------|
| luminaclippers.com | 70664 | 116665 | 6bef1a80-9a02-4969-b84b-42def0a6f238 |
| luminaweb3.io | 69275 | 114531 | b3ba4228-c4fe-46ef-bceb-d4dd769faa85 |

## Environment Variables

```bash
SEARCHATLAS_API_KEY=<your-api-key-here>
VERCEL_TOKEN=<vercel-api-token>
GITHUB_TOKEN=<github-pat-for-repo-commits>
LUMINAWEB3_REVALIDATION_SECRET=<next-isr-secret>
LUMINACLIPPERS_REVALIDATION_SECRET=<next-isr-secret>
```

## Guardrails Summary

| Rule | Description |
|------|-------------|
| Money page protection | Body/content changes on money pages always require human review |
| Conservative mode | Medium+ risk actions flagged for human review |
| Action cap | Max 10 actions per site per run (configurable) |
| No black-hat | No link spam, PBNs, thin AI content, cloaking, or redirects |
| Google compliance | Aligned with Helpful Content + March 2024 spam policy |
| Balanced mix | At least 40% of action slots reserved for keyword-based actions |
