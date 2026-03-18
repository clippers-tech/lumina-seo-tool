# Lumina SEO Orchestrator

Autonomous SEO management system for Lumina's two properties:
- **luminaclippers.com** (Priority 1) — Target: #1 globally for "clipping agency"
- **luminaweb3.io** (Priority 2) — Web3/crypto marketing agency

## Architecture

```
lumina-seo-tool/
├── seo-orchestrator/          # Python backend — SEO automation engine
│   ├── run.py                 # Main entry point
│   ├── config/
│   │   ├── sites.yaml         # Site configuration (SearchAtlas IDs, keywords, etc.)
│   │   ├── models.py          # Data models
│   │   └── __init__.py        # Config loader
│   ├── core/
│   │   ├── orchestrator.py    # Main orchestration logic
│   │   ├── analyzer.py        # SERP & keyword analysis
│   │   ├── executor.py        # Auto-executes OTTO fixes, press releases, cloud stacks
│   │   ├── reporter.py        # Generates markdown reports
│   │   └── content_generator.py # Content generation helpers
│   ├── integrations/
│   │   ├── searchatlas.py     # SearchAtlas API client (Rank Tracker, Site Audit, OTTO, Content API)
│   │   ├── wordpress.py       # WordPress CMS integration (preserved for future use)
│   │   └── vercel_publisher.py # Vercel/Next.js publishing integration
│   ├── outputs/               # Generated reports, actions, execution logs per run
│   ├── strategy/              # Strategy documents
│   └── requirements.txt       # Python dependencies
│
├── seo-dashboard/             # React frontend — SEO monitoring dashboard
│   ├── client/                # Vite + React + Tailwind + shadcn/ui
│   │   └── src/
│   │       ├── pages/         # Overview, Keywords, Actions, Site Audit, Run Log, Execution
│   │       ├── components/    # UI components (shadcn)
│   │       └── hooks/         # Custom hooks including useDashboardData
│   ├── server/                # Express backend
│   │   ├── routes.ts          # API routes serving dashboard data
│   │   └── data/              # dashboard_data.json (updated by orchestrator)
│   └── package.json
│
├── articles/                  # SEO articles for Next.js blog (21,000+ words)
│   ├── 01-what-is-a-clipping-agency.md    # Pillar page (4,482 words)
│   ├── 02-how-to-start-clipping.md        # How-to guide (3,402 words)
│   ├── 03-clipping-campaign-at-scale.md   # Campaign guide (3,637 words)
│   ├── 04-best-clipping-agencies-2026.md  # Comparison (3,022 words)
│   ├── 05-ai-clip-generators-vs-agencies.md # AI vs agency (3,161 words)
│   ├── 06-clipping-disrupting-marketing.md  # Forbes feature (3,583 words)
│   └── ALL-ARTICLES-FOR-FRAMER.md         # All articles in one file
│
└── content-briefs/            # Brand context and article specifications
    ├── brand-context.md
    └── article-specs.md
```

## Website GitHub Repos

- **luminaclippers.com**: https://github.com/RhysMckay7777/luminaclippers-site (Next.js / Vercel)
- **luminaweb3.io**: https://github.com/RhysMckay7777/luminaweb3-site (Next.js / Vercel)

## SearchAtlas API

All SEO data flows through SearchAtlas. API key required as env variable.

### Endpoints Used

| Service | Base URL | Auth |
|---------|----------|------|
| Rank Tracker | `keyword.searchatlas.com/api/v1/` | Query param: `searchatlas_api_key` |
| Site Audit / OTTO | `sa.searchatlas.com/api/v2/` | Header: `x-api-key` |
| Content API (PRs, Cloud Stacks, KG) | `ca.searchatlas.com/api/cg/v1/` | Header: `x-api-key` |

### Project IDs

| Site | Rank Tracker | Site Audit | OTTO UUID | OTTO ID | Knowledge Graph |
|------|-------------|------------|-----------|---------|-----------------|
| luminaclippers.com | 70664 | 116665 | `6bef1a80-9a02-4969-b84b-42def0a6f238` | 78296 | 608151 |
| luminaweb3.io | 69275 | 114531 | `b3ba4228-c4fe-46ef-bceb-d4dd769faa85` | 76313 | 611385 |

## Running the Orchestrator

```bash
cd seo-orchestrator
pip install -r requirements.txt
SEARCHATLAS_API_KEY="your-key" python run.py --api-key "your-key"
```

This will:
1. Fetch keyword rankings from Rank Tracker
2. Pull site audit data and OTTO optimization status
3. Deploy pending OTTO fixes automatically
4. Refresh SERP data
5. Build authority assets (press releases + cloud stacks)
6. Generate a report in `outputs/`
7. Update `dashboard_data.json` for the frontend

## Running the Dashboard

```bash
cd seo-dashboard
npm install
npm run dev
```

For production:
```bash
npm run build
NODE_ENV=production node dist/index.cjs
```

## Automated Cron Jobs (via Perplexity Computer)

1. **Daily Orchestrator** (4pm UTC): Runs full orchestrator with auto-execution
2. **3-Hourly Monitor** (every 3 hours): Checks rankings, OTTO status, authority assets; sends notification

## Current SEO Status (as of March 16, 2026)

### luminaclippers.com
- **"clipping agency" ranking:** Not ranking yet (content just published)
- **Domain Rating:** 9
- **OTTO fixes deployed:** 224/285 (score: 78%)
- **Press releases:** 4 created (1 published, 3 generated/processing)
- **Cloud stacks:** 8 created (2 published/indexed, 2 generated, 4 pending credit limit)
- **Content:** 6 new SEO articles written (21,000+ words) — ready for Next.js blog

### luminaweb3.io
- **"web3 marketing agency" ranking:** Position 8 (up from 18)
- **"blockchain marketing agency" ranking:** Position 17 (up from 18)
- **OTTO fixes deployed:** 281/390 (score: 73%)

## Known Issues

- SearchAtlas OTTO Hyperdrive credits maxed at 65 — some cloud stacks can't build until plan upgraded
- Rank Tracker API intermittently returns 404/403 — orchestrator falls back to cached data
- luminaclippers.com blog content publishing via Vercel integration is in progress

## Environment Variables

```
SEARCHATLAS_API_KEY=<your-api-key-here>
```
