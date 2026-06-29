# Astova - Current Capabilities

> Factual record of what Astova can do TODAY. No future ideas, no planned features.
> Maintained as production code: update whenever meaningful work ships.
> Last updated: 2026-06-29. Engine report schema: v12.

## Engine

The deterministic audit engine (`engine/astova_engine/`) assesses a single page (or a crawl) by reading the live HTML and reproducing the result on re-run. Every finding is confidence **VERIFIED**. No LLM runs in the engine.

- Fetches the page as a normal client and as **GPTBot** (the "bot view").
- **Auto-renders** JavaScript-heavy pages via Cloudflare Browser Rendering when the raw HTML looks like an SPA shell; otherwise scans raw HTML.
- Gathers robots.txt, sitemap.xml, llms.txt, TLS certificate, redirect chain.
- Runs ~58 checks across five areas:
  - **On-page (~25):** title, meta description, H1 / heading structure + order, canonical, robots meta, lang / hreflang, Open Graph, JSON-LD presence + validation (@graph-aware), image alt + dimensions, link quality (generic-anchor ratio), link attributes (noopener), crawlable anchors, jump links, form labels, URL quality, snippet directives.
  - **Technical (~23):** HTTPS, status, redirects, HSTS, TLS expiry, mixed content, viewport, robots.txt + AI-crawler directives, sitemap validity / freshness, index conflict, resource hints, X-Robots-Tag, compression, security headers (>=3 of 5), llms.txt.
  - **GEO readiness (~18):** front-loaded answer, definitive vs hedged language, content structure (lists/tables), Q&A headings, thin content / depth, AEO answer block, summary bullets, intro quality, chunking / extractability, data density, FAQ, trust / E-E-A-T, freshness, entity grounding (sameAs), JS-rendered gap (raw vs rendered).
  - **Performance (on-demand only):** Google Lighthouse score + LCP/CLS/TBT/FCP/SI + CrUX field data via PageSpeed Insights. Not run by default.
  - **Local / GBP (conditional):** LocalBusiness schema, NAP, hours, geo, GBP link - only emitted when a local signal is present.
- **Bot access:** detects WAF/CDN blocks and cloaking by comparing the normal fetch to the GPTBot fetch.
- **"How each AI engine sees you":** exposes raw-vs-rendered word counts and flags content (H1, schema) that only appears after JavaScript - the split between non-JS crawlers (ChatGPT/Claude/Perplexity) and JS-rendering ones (Gemini/AI Overviews/Copilot).

Two scoring outputs (known overlap, see PRODUCT_DECISIONS / NEXT_DECISIONS):
- `overall_score` + `pillar_scores`: severity-penalty model, weights renormalized over present pillars.
- `scorecard.headline_score` ("AI Retrievability", 0-100): the brand-facing number, from a 20-row credit model + 3 gates + a +8 overlay.

NOT in the engine today: AI citation / visibility sampling (lives in the web layer, see Integrations), attribution, auto-apply of fixes.

## Report

`Report.to_dict()` (schema v12):
- `schema_version`, `url`, `fetched_at`, `overall_score` (0-100), `pillar_scores` (per present pillar)
- `meta`: `status_code`, `final_url`, `word_count`, `online_checks`, `rendered` (bool), `render_source` ("cloudflare" / "playwright" / null); when persistence is on: `scan_id`, `scan_token`, `diff`
- `findings[]`: `{id, pillar, title, status (pass/warn/fail/info), severity, confidence (verified), value, evidence, recommendation}`
- `fixes[]`: deterministic remediation artifacts (present when scanned with fixes enabled): `{finding_id, title, kind, language, content, note}`
- `scorecard`: `{confidence:"verified", headline_score, technical_score, overlay{total,max,factors}, rows[20]{n,label,score,status,findings,impact}, categories[5], summary{verdict,...}, citation{...}}`

## MCP

Server: `engine/astova_engine/mcp_server.py` (FastMCP, server name "astova"). Transports: **stdio** (default, local) and **Streamable HTTP** (mounted at `/mcp/` on the FastAPI service). **No authentication on either transport.**

| Tool | Inputs | Output | Current limitations |
|---|---|---|---|
| `audit_url` | `url: str` | Compact scorecard (headline, 20 rows, categories, +8 overlay, top 10 issues). Deterministic. | No URL validation; re-fetches every call; SSRF-exposed. |
| `scan_url` | `url: str` | Full `Report.to_dict()`. Deterministic. | Large / token-heavy, no truncation. |
| `fix_plan` | `url: str` | Ordered agent-actionable fixes (deterministic content + advisory + `ai_draftable` flags) + verdict. Deterministic. | Re-scans; no scan reuse from a prior `audit_url`. |
| `audit_project` | `root_path: str`, `framework="auto"`, `base_url?`, `max_pages=1` | Audits a project DIRECTORY and returns the **same `Report`** a URL scan returns (findings, pillar scores, scorecard), reading robots/llms/sitemap, framework/host config (security headers) and static HTML off disk. Deterministic, read-only, no fixes. Optional `base_url` adds a live `Report` under `live_audit`. | stdio-meaningful only (reads local FS); deploy-only signals (HTTPS/TLS/status/redirects/compression) are omitted; on-page/GEO checks need a built static HTML (skipped for un-built SSR projects). |
| `explain_finding` | `finding_id: str` | Structured fix knowledge for ONE finding (e.g. `geo.aeo`): name, summary, category, can_astova_generate, agent_can_automate, human_review_required, why_it_matters, how_to_fix, agent_guidance, framework_examples, verification, related_findings. Deterministic (from the knowledge registry). | Knowledge is hand-maintained in `knowledge.py` (mirrors docs/KNOWLEDGE_BASE.md); no per-page context. |
| `generate_fix` | `finding_id: str`, `url?`, `html?` | One deterministic, ready-to-apply fix: `finding_id, deterministic, supported, explanation, generated_content, target_type, suggested_location, verification_method`. No LLM; the fix is NOT applied. | Supports 7 findings only (`schema.missing`, `geo.faq`, `tech.robots.missing`, `tech.robots.ai`, `tech.llms_txt`, `canonical`/`onpage.canonical`, `tech.viewport`); `geo.faq` needs `html` with >=2 Q&A pairs; most need `url`. |
| `verify_fix` | `target: str`, `finding_id: str`, `target_type="url"` | Re-scans the target (URL or project) and reports whether ONE finding is resolved: `fixed (bool), current_status, current_severity, evidence, score_after, explanation, next_step`. Reuses `scan`/`scan_project`; no LLM, no fix applied. Fixed = finding gone, or present with status pass/info. | Any finding id (not just the 7 fixable ones); a failed re-scan returns a structured `error`; `url` targets re-fetch live (no scan reuse). |
| `ai_ready_loop` | `target: str`, `target_type="url"`, `max_items=10` | The one-call **"tell me exactly what to fix next"** plan. Assesses the target, picks the highest-severity fail/warn findings, and per item attaches knowledge (`explain_finding`), the deterministic `fix` (`generate_fix`, `supported:false` when none), and the `verify_fix` call + `agent_next_step`. Pure orchestration over `scan`/`scan_project` + `explain_finding` + `generate_fix` + `verify_fix`; no new scan logic, no LLM. Top-level counts: `deterministic_fix_count` / `ai_assisted_count` / `manual_count`. Also on the HTTP API: `POST /ai-ready` (adds a `markdown` field). | `url` targets re-fetch live; knowledge cards make the payload larger than the other tools. |
| `prepare_project_for_ai` | `root_path: str`, `max_items=25` | **The recommended entry point for an agent in a local repo.** One read-only call orchestrates `audit_project` + `ai_ready_loop` and returns the full fix context: `project, framework, score, summary, recommended_workflow`, and `findings[]` where each item is `{finding_id, knowledge, fix, verify}` (in priority order; `fix` null when none ready, `knowledge` null when no card, `verify` always present). No file writes, no code gen, no LLM. | MCP-only; `framework` is auto-detected (no override); inherits `ai_ready_loop`'s payload size. |
| `mcp_usage_guide` | `client="generic"` | Static self-documenting helper: returns `client, purpose, recommended_entrypoints, setup, starter_prompt, workflow, safety_rules, available_tools` tailored to the MCP client (`generic`/`claude`/`cursor`/`chatgpt`/`windsurf`). Scans nothing, reads no files, no LLM. | Hand-maintained content; `available_tools` is kept in sync with the registered tools by a test. |

Shared limitations: no auth, no rate limit, no timeout, no logging, no caching, no scan reuse / context between tools. (`ai_ready_loop` is the one-call entry point that bundles the whole loop; under it, the per-finding primitives are `explain_finding` to understand a finding, `generate_fix` to get the exact snippet to apply, then `verify_fix` to re-scan and confirm it is resolved.)

## Patch Generation

**Deterministic patches** (ready-to-paste content from template/parser, no LLM):
- `title.missing`, `meta.description.missing` (only if source text exists), `canonical`, `tech.viewport`, `schema.missing` (Organization + WebPage @graph), `geo.faq` (FAQPage, only if >=2 Q&A pairs), `tech.robots.missing` / `tech.robots.ai` / `geo.bot_access` (robots.txt allowing AI crawlers), `local.business_schema` (LocalBusiness placeholder), `tech.llms_txt`.
- Project-level file-fix templates (`robots.txt` missing / blocks-AI, `llms.txt` missing, `sitemap` missing / invalid) still live in `project.analyze_files`, but `audit_project` itself is now a **pure diagnostic** that returns a `Report` and generates no fixes - remediation goes through `generate_fix` / `fix_plan` on the resulting finding ids (`tech.robots.*`, `tech.llms_txt`, `tech.sitemap.*`).

**AI draft requests** (the only LLM path, `web/app/api/fix`, Claude Haiku): `geo.aeo`, `geo.frontload`, `geo.definitive`, `geo.thin_content`. Output labelled "ai_drafted" / "Drafted by Claude - review before publishing".

**Manual / advisory** (recommendation text only, no generated content): every other failing / warning finding.

**No auto-apply exists for any patch.** Intended consumption: an AI coding agent or human applies it, then re-scans.

## Verification

- Re-running a scan on a saved URL produces `meta.diff` vs the previous scan: `resolved`, `regressed`, `new_issues`, `score_delta`, `pillar_deltas`. Requires persistence enabled.
- There is **no dedicated "verify this fix worked" tool**; verification is "re-scan and read the diff".
- Monitors can re-scan on a cadence and raise alerts on regressions (anti-noise rules: e.g. availability fires only on the 2nd consecutive failure).

## Framework Support

Framework **DETECTION** (used by `audit_project` to target file paths) - implemented:
- Next.js (`public/`), Astro (`public/`), Gatsby (`static/`), WordPress (root), generic Node (`public/`), static (root).

Framework **APPLY** (writing fixes into a project) - **NOT implemented for any framework.** Detection only informs the suggested target path in the fix plan.

## Integrations

Implemented:
- **CLI:** installed as the `astova` console script (and `python -m astova_engine`). Subcommands: `astova check <target> [--json]` (scan a URL or local project directory - auto-detected - to a compact report, or full Report JSON), `astova loop <target> [--json] [--max-items N]` (the `ai_ready_loop` "what to fix next" plan, human-readable or full JSON), and `astova export <target> [--output file.md] [--max-items N]` (the same loop result as a compact Markdown action plan to paste into Claude/ChatGPT/Cursor/Windsurf; stdout or a file). Legacy form `astova <url> [--json --render --performance --fixes --crawl --logs]` still works.
- **HTTP API (FastAPI):** `/scan`, `/project/audit` (POST - audit a project directory, returns a `Report`), `/compare`, `/crawl` (+poll), `/performance`, `/logs`, `/cloudflare-logs`, `/monitors` (+alerts, run-due), `/history`, `/notes`, `/scans/{token}`, `/findings` (knowledge index), `/findings/{id}` (explain one finding), `/findings/{id}/fix` (POST - deterministic single-finding fix), `/findings/{id}/verify` (POST - re-scan and check if a finding is resolved), `/ai-ready` (POST - the `ai_ready_loop` plan + a `markdown` action plan), `/mcp-guide` (GET - the static MCP usage guide for a client), `/scans/{token}` (GET - a stored report by share token), `/reports/{token}` (GET - a stored report enriched with its derived bundle: metadata, action summary, Markdown, agent prompt), `/health`, plus the `/mcp` mount. Mirrored on the web side by `/api/findings`, `/api/findings/[id]`, `/api/ai-ready`, `/api/mcp-guide`, `/api/scans/[id]` and `/api/reports/[token]`.
- **Dashboard (Next.js on Vercel):** marketing site, live scan demo, full report screen, Supabase email/password auth, dashboard (monitored sites with score / trend / change), per-site detail (scan history, re-scan, notes), AI visibility tool, **AI Ready Action Plan** (`/ai-ready` - enter a URL, get the `ai_ready_loop` plan with score, counts, top actions + verify steps; two copy buttons: **Copy agent prompt** (the plan wrapped with safety guardrails, ready to paste into a coding agent) and **Copy Markdown** (the raw plan); via `/api/ai-ready` -> engine `POST /ai-ready`, needs `ASTOVA_ENGINE_URL`). The homepage hero CTA ("Generate AI Ready plan") is the conversion path into it: it routes to `/ai-ready?url=<encoded>`, which prefills the URL and auto-runs once. A static onboarding page **`/agents`** (linked from the nav as "For agents", in the sitemap) explains the audit -> agent-fixes -> verify loop and offers copyable blocks: the agent prompt, the CLI commands (`astova check/loop/export .`), and the MCP starter instruction. A **`/mcp`** page (nav link "MCP", in the sitemap) renders the `mcp_usage_guide` content for a chosen client (Generic/Claude/Cursor/ChatGPT/Windsurf) with copyable starter prompt + config; it fetches `/api/mcp-guide` -> engine `GET /mcp-guide`, so the guide is never duplicated in the web app (needs `ASTOVA_ENGINE_URL`).
- **AI visibility sampling (web layer, not engine):** `/api/visibility` samples ChatGPT (OpenAI, when `OPENAI_API_KEY` set), Claude, Perplexity, Gemini via live web search; returns mention / citation rate, share-of-voice, sentiment, cited sources - confidence **MEASURED**.
- **Persistence:** Supabase Postgres (scans, monitors, alerts, notes); SQLite fallback for local dev. Every saved scan has a stable row `id` + an unguessable `scan_token` (capability), and carries `engine_version` / `ruleset_version` / `report_version` in its meta.
- **Shareable AI Readiness Report (`/report/[id]?share=<token>`):** a read-only premium report - score, readiness breakdown, executive summary, action summary, findings by category, the deterministic / AI-assisted / manual buckets (reusing the knowledge taxonomy), and verification guidance. Actions: Copy agent prompt, Copy Markdown, Download Markdown, **Print / Save PDF**, Open AI Ready Action Plan. Public by valid share token (no auth); loads via `/api/reports/[token]` -> engine `GET /reports/{token}` (needs `ASTOVA_ENGINE_URL` + persistence). The report header's Share button now copies this URL.
- **Print / PDF report (`/report/[id]/print?share=<token>`):** a server-rendered, print-optimised page (white background, black text, no nav/buttons/animations, print CSS + page-break-friendly sections) that auto-opens the browser print / "Save as PDF" dialog. Reuses the same report bundle (`fetchReportBundle` shared with the API proxy); no server-side binary PDF. Sections: Astova branding, target, date, score, confidence note, executive summary, readiness breakdown, action summary, top findings, the deterministic / AI-assisted / manual lists, verification guidance, and a VERIFIED / MEASURED / ESTIMATED footer.
- **MCP:** stdio (local clients) + HTTP (remote connector).

**NOT implemented (do not claim):** GitHub Action/App, WordPress plugin, Vercel/Netlify deploy integration, any framework auto-apply, a standalone CLI binary beyond the python module, public API keys / multi-tenant API auth.
