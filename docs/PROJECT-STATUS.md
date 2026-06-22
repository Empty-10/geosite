# damask — project status & handoff

A snapshot of what exists, how it works, and what to build next. Pair this with
`CLAUDE.md` (vision, strategy, conventions — read that first) and
`docs/claude-design-brief.md` (palette, motion, screen specs).

> One line: a GEO-first website scanner that separates **verified fact** from **measured
> estimate**, and generates fixes — not just findings. Codename `damask` (placeholder).

---

## Current state (June 2026)

| Part | Status | Where |
|---|---|---|
| Python scan engine | ✅ Built, runnable, tests pass | `engine/` |
| Marketing/landing site | ✅ Built (Next.js 16), live scan demo **wired to real engine** | `web/` |
| Design system + prototype | ✅ Locked | `docs/claude-design-brief.md`, `design/` |
| `/api/scan` (engine ↔ web) | ✅ Built — route shells out to the engine, HeroDemo consumes it | `web/app/api/scan/` |
| Report screen, dashboard | ❌ Not built | — |
| Real GEO citation sampling, attribution, accounts/billing | ❌ Later phases | — |

---

## How to run

Engine (no API keys needed):

```bash
cd engine
python -m venv .venv && source .venv/bin/activate
pip install -e .
python -m damask_engine https://stripe.com          # human-readable report
python -m damask_engine https://stripe.com --json    # JSON
pytest                                               # offline tests
```

Web app:

```bash
cd web
npm install
npm run dev      # http://localhost:3000
npm run build    # production build
```

---

## What's built — engine (`engine/damask_engine/`)

A pure, offline-testable scan engine. Give it a URL (or raw HTML) and it returns a scored
`Report` of `Finding`s, each tagged with a confidence label.

- `models.py` — `Finding`, `Report`, and enums: `Confidence` (VERIFIED / MEASURED /
  ESTIMATED), `Severity`, `Status`, `Pillar`. **Every finding must carry a confidence
  label, and ideally `evidence` + a plain-English `recommendation`.** This is the brand
  rule, enforced in the data model.
- `scanner.py` — `scan(url)` fetches then runs modules; `scan_html(url, html)` runs
  offline (used by tests). Returns a scored `Report`.
- `fetch.py` — plain HTTP GET for now. Playwright rendering is a planned upgrade.
- `scoring.py` — each pillar starts at 100 and loses severity-weighted points; overall =
  weighted average of the pillars present (weights renormalize for partial scans).
- `modules/` — pure functions returning `list[Finding]`, one per area:
  - `onpage.py` — title, meta, H1, headings, JSON-LD schema, canonical, robots meta, OG,
    image alt coverage.
  - `technical.py` — HTTPS, status, redirect chain, HSTS, TLS-cert expiry, mixed content,
    viewport, and parsed robots.txt (AI-crawler access, declared sitemaps) + sitemap.xml
    (valid/index, URL count, `<lastmod>` freshness) when online. **Pure**: the scanner
    fetches these at the boundary and hands the text in via `NetInputs`, so parsing is
    offline- and fixture-tested (`parse_robots`, `parse_sitemap`).
  - `geo_readiness.py` — front-loaded answer, definitive-vs-hedged language, lists/tables,
    question-style headings, content depth. Deterministic (VERIFIED) — NOT citation
    sampling (that's a later MEASURED module).
- `tests/test_engine.py` — offline tests on fixed HTML. Run with `pytest`.

Known scoring nuance: a page can miss its title yet still score ~74 overall because
healthy pillars prop it up. Decide whether critical failures should hard-cap the overall.

## What's built — web (`web/`)

Next.js 16 (App Router) + React 19 + TypeScript. Dark-mode-first. No Tailwind — styling is
inline + CSS variables. It's a faithful port of the approved Claude Design prototype.

- `app/globals.css` — design tokens as CSS variables (palette, fonts, keyframes).
- `lib/tokens.ts` — JS copies of the palette + `scoreColor()` for dynamic styling.
- `app/layout.tsx` — metadata, OG/Twitter tags. `app/icon.svg` favicon,
  `app/opengraph-image.tsx` generated share image. `public/robots.txt`.
- `app/page.tsx` — assembles the landing sections.
- `components/` — `Nav`, `Hero`, `HeroDemo` (the interactive live-scan demo), `Confidence`,
  `Features`, `Pricing`, `AgencyCta`, `Footer`, `Logo`.

**`HeroDemo.tsx` is the key file.** It animates a scan (modules tick complete, score
counts up) and renders a sample report. All of its numbers are **mocked** right now.

## Design source of truth

`docs/claude-design-brief.md` has the exact palette (light + dark hex), typography (Geist
+ Geist Mono), motion rules (motion only on the scan; no popups; progressive disclosure),
and the verified-vs-measured visual grammar (solid = verified, blue band = measured).
`design/landing-prototype.html` is the original Claude Design output (reference only — it
uses Claude Design's runtime and won't run standalone).

---

## Next tasks (in priority order)

1. ~~**Connect the demo to the real engine — `/api/scan`.**~~ ✅ **Done.**
   `web/app/api/scan/route.ts` POST-takes a URL and returns the engine's JSON `Report`;
   `HeroDemo.tsx` consumes it (real score ring / pillars / priority fixes, plus a real
   error state). Chosen approach: **shell out** (`python -m damask_engine <url> --json`),
   isolated behind one function and gated on `DAMASK_ENGINE_URL` so production can swap to
   a deployed engine HTTP service without a rewrite (Vercel has no Python runtime). The
   route normalizes the URL, blocks loopback/private hosts (basic SSRF guard), and times
   out at 25s. Requires `engine/.venv` with the engine installed (`pip install -e .`).
   Notes carried forward: Performance pillar renders "not run yet" (later phase); the
   citation-share block is a labelled *sample* preview, not a MEASURED claim.
   The FastAPI engine service backing the `DAMASK_ENGINE_URL` path now exists too:
   `engine/damask_engine/service.py` (`pip install -e ".[service]"`, then
   `uvicorn damask_engine.service:app --port 8000`). `POST /scan {url}` returns the same
   `Report.to_dict()` as the CLI, so the route handles the local and HTTP paths identically.
   Remaining for deploy: stand the service up on a container host and point
   `DAMASK_ENGINE_URL` at it.
2. ~~**Deepen `engine/modules/technical.py`**~~ ✅ **Done.** robots.txt + sitemap.xml are
   fetched at the boundary (`fetch.py`) and parsed by pure `parse_robots` / `parse_sitemap`
   (AI-crawler access, declared sitemaps; urlset/index validity, URL count, `<lastmod>`
   freshness). Added redirect-chain capture (`FetchResult.redirect_chain`) and a TLS-cert
   expiry check (`tls_info`, verified via certifi's CA bundle). The module is now pure (no
   `requests` import) — network material flows in through `NetInputs`. JSON report carries
   `schema_version` ("1"); fixture tests (`test_technical.py`) and a schema snapshot
   (`test_schema.py`) cover it. 20 tests pass.
3. **Playwright rendering in `fetch.py`** — capture raw HTML + rendered DOM; flag pages
   where they differ materially (JS-dependent content the engine would otherwise miss).
4. **Report screen** (`web/app/report/...`) — the full scan-report view per design brief
   §7.3, reusing HeroDemo's score ring / pillar cards / findings components.
5. **PageSpeed performance module** — needs a Google API key in env (`.env`, gitignored).

After that: GEO citation sampling (MEASURED), then the closed-loop features (attribution,
crawler logs, fix generation), then accounts/billing. Full arc in `CLAUDE.md` → Roadmap.

---

## Gotchas / placeholders to fix before launch

- `web/app/layout.tsx` → `metadataBase` is `https://damask.example`. Set the real domain.
- `damask` is a placeholder name; the `.ai` domain isn't locked yet.
- The `/api/scan` route shells out to a local Python process by default — works in local dev
  and on a container host, **not** on Vercel serverless. For production set `DAMASK_ENGINE_URL`
  to the deployed FastAPI engine service (`engine/damask_engine/service.py`); that service
  still needs to be containerized and hosted.
- Deploy note: the app lives in `web/`, not the repo root — set the host's **root
  directory to `web/`** (e.g. on Vercel).
- Secrets (Google API key, future AI-engine keys) go in `.env` files — never commit them.
