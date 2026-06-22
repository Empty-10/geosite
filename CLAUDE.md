# damask — GEO/SEO intelligence platform

> Working codename: **damask** (placeholder, rename when the real `.ai` domain is locked).
> This file is the source of truth for anyone (human or AI) working in this repo. Read it first.

## What we're building

A website-scanning SaaS that produces high-accuracy **GEO** (Generative Engine
Optimization) reports, backed by a deterministic technical/SEO engine. It serves two
modes from one engine:

- **Internal mode** — our team runs scans and delivers branded reports to clients.
- **SaaS mode** — customers sign up, add domains, and get continuous monitoring + alerts.

## Strategic decision (read before adding scope)

We are **GEO-first**, not "another SEO auditor" and not "another citation monitor."

- The market is split: deep-GEO tools with no real SEO (Profound, Peec, Otterly) vs
  SEO suites with shallow GEO (Semrush, Ahrefs). We sit in the seam.
- We still build the deterministic crawl/parse engine because **GEO depends on it**
  (front-loading, schema, extractable chunks, crawlability, `llms.txt`). We surface its
  output as "GEO readiness," and can expose a fuller SEO audit later.
- Our wedge is the **closed loop** competitors leave open. Lead with these, not tracking:
  1. **Attribution** — connect cited → AI referral traffic → conversion (GA4 + server logs).
  2. **AI crawler-log analytics** — when GPTBot/ClaudeBot/PerplexityBot actually visit,
     what they read, what errored. Pairs with our headless renderer ("what the bot saw").
  3. **Fixes, not findings** — auto-generate schema/`llms.txt`, rewrite intros to
     front-load answers, template the structure of already-cited pages onto money pages.
- Supporting plays: multi-account + white-label from day one (Profound can't),
  a one-time SMB audit SKU (entry funnel + doubles as internal-report mode),
  hybrid pricing (sites + usage, not pure per-prompt).

## The accuracy principle (non-negotiable, enforced in the data model)

Every finding carries a confidence label. Never present an estimate as a fact.

- `VERIFIED` — deterministic, read straight from the page or an authoritative API.
  Re-running reproduces it exactly. (On-page, technical, performance, GEO-readiness.)
- `MEASURED` — sampled from AI engines on a date; always shown with a confidence band
  and sample size. (AI citation / visibility — NOT in this first slice.)
- `ESTIMATED` — modelled/inferred; clearly flagged as directional.

This split is the brand. It's why we beat tools that overclaim.

## Architecture (target)

Queue-backed scanning. Web/API (Next.js + TypeScript) → Redis job queue → Python scan
workers → modules call fetch/render + external APIs → findings normalized → scored →
Postgres (+ object storage for raw payloads/screenshots) → report/dashboard. A scheduler
re-runs scans on a cadence and an alert engine diffs results.

Recommended stack: Next.js (app + API), Python (FastAPI workers) for the engine,
Playwright for headless rendering, Postgres, Redis (BullMQ/Celery), S3/R2, Stripe + an
auth provider for the SaaS layer. Hosting: Vercel (web) + a container host (workers).

Full reasoning lives in `docs/` (the architecture & build-plan document).

## The five scan modules

1. **On-page** (deterministic) — title, meta, headings/H1, JSON-LD schema, canonical,
   robots meta, Open Graph, content signals (word count, definitive-vs-hedged language,
   lists/tables, alt coverage), front-loaded answer.
2. **Technical** (deterministic) — robots.txt + AI-crawler directives, sitemap validity
   & freshness, status/redirects, HTTPS/SSL/HSTS, mixed content, indexability.
3. **Performance** (authoritative API) — Core Web Vitals + Lighthouse via Google
   PageSpeed Insights API (lab + CrUX field). *Not in first slice.*
4. **Local / GBP** (mixed) — Places API for any business (≤5 reviews); Business Profile
   API only for owned/verified locations. *Not in first slice.*
5. **GEO / AI visibility** (probabilistic, MEASURED) — multi-engine prompt sampling,
   share of voice, entity authority. *Not in first slice — see roadmap.*
   NOTE: "GEO readiness" (the on-page factors that correlate with being cited) IS
   deterministic and IS in the first slice. Don't confuse it with citation sampling.

## Scoring

Overall 0–100 from weighted pillars: Technical 25, On-page 25, Performance 20, GEO 20,
Local 10. The GEO *citation* score is kept visually separate so a probabilistic measure
never blends invisibly into a deterministic one. For the first slice we score only the
pillars we have (on-page, technical, GEO-readiness) and renormalize weights.

## Repo layout

```
engine/                 Python scan engine (THE FIRST BUILD — start here)
  damask_engine/
    cli.py              `python -m damask_engine <url>` → prints a scored report
    scanner.py          orchestrates modules; scan(url) and scan_html(url, html)
    fetch.py            HTTP fetch (Playwright render comes later)
    models.py           Finding / Report / enums (ConfidenceLabel, Severity, Pillar)
    scoring.py          pillar + overall scoring
    modules/            onpage.py, technical.py, geo_readiness.py
  tests/                offline tests (parse fixed HTML, no network)
  pyproject.toml
web/                    Next.js app (scaffold later via create-next-app — see web/README)
docs/                   architecture doc + competitive notes
```

## Conventions

- Python 3.11+, type hints everywhere, dataclasses for models, `ruff` + `black` style.
- Modules are pure: a module takes parsed input and returns `list[Finding]`. No module
  reaches into another. New checks = new functions returning Findings, nothing else.
- Every `Finding` MUST set a `confidence` label and, where possible, `evidence`
  (the exact source line / value) and a plain-English `recommendation`.
- Keep the engine importable and offline-testable: parsing logic must work on an HTML
  string (`scan_html`) so tests need no network.
- Tests are required for each module. Run with `pytest`.

## How to run (engine)

```bash
cd engine
python -m venv .venv && source .venv/bin/activate
pip install -e .
python -m damask_engine https://example.com           # live scan
python -m damask_engine https://example.com --json     # machine-readable
pytest                                                 # offline tests
```

## Roadmap (build order)

- **Phase 0 — foundations.** Engine skeleton, models, scoring, on-page/technical/
  GEO-readiness modules, CLI, tests. ← *this scaffold; flesh it out next.*
- **Phase 1 — engine depth.** Add Playwright rendering, richer technical (sitemap/robots
  parsing, SSL), PageSpeed API performance module, JSON report schema v1.
- **Phase 2 — internal report.** Web shell, run a scan, render a branded report, PDF export.
- **Phase 3 — GEO engine.** Multi-engine citation sampling (MEASURED), visibility/SoV,
  entity authority, confidence bands. This is the differentiator's first half.
- **Phase 4 — closed loop.** AI referral attribution (GA4 + logs), crawler-log analytics,
  fix generation. This is what makes us not-a-monitor.
- **Phase 5 — SaaS.** Accounts, multi-tenant, billing, scheduling, alerts, white-label.

## Immediate next tasks (for Claude Code to pick up)

1. `cd engine && pip install -e . && pytest` — confirm the scaffold runs green.
2. Flesh out `modules/technical.py`: real robots.txt + sitemap.xml fetch & parse,
   redirect-chain capture, SSL/HSTS check. Add tests with fixtures.
3. Add a `--json` report schema (versioned) and snapshot-test it.
4. Add Playwright rendering in `fetch.py` (raw HTML + rendered DOM; flag JS-dependent
   pages where they differ materially).
5. Then start the PageSpeed performance module (needs a Google API key in env).

Keep the accuracy principle and the GEO-first wedge in mind for every addition.
