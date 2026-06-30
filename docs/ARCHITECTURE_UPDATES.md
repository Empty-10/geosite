# Astova - Architecture Updates

> Append-only progress log. A new entry after every significant piece of work.
> Newest at the top.

---

## 2026-06-30 - Bot-challenge / interstitial detection (Engine + MCP + Web)

**Objective:** stop scoring a Cloudflare/Akamai/etc. challenge holding page as if it were the real site.
Scanning a protected URL (e.g. mitel.com) returned the interstitial - its own noindex + ~0 words - producing
a confident-but-wrong scorecard. Detect it and mark the result UNRELIABLE (the accuracy principle).

**What changed:**
- `engine/astova_engine/detect.py` (new) - pure `detect_challenge(status, headers, title, text, final_url)
  -> vendor|None` + `challenge_info(...) -> {vendor, marker, status}|None`. Vendors: Cloudflare (markers /
  cf-mitigated / server+cf-ray@403/503), Akamai (gated by 403/503), PerimeterX, DataDome, Imperva. Narrowed
  to be false-positive-safe (dropped the bare `__cf` cookie prefix - normal CF sites set `__cf_bm`).
- `engine/astova_engine/scanner.py` - `scan_html` calls `challenge_info`; on a hit it sets `meta.challenge`,
  drops the 7 artifact findings, appends one `tech.challenge` (Technical / FAIL / HIGH / VERIFIED) with
  vendor+status+marker evidence, and flags `scorecard.unreliable = true` + `scorecard.challenge`.
- `engine/astova_engine/models.py` - `SCHEMA_VERSION` 12 -> 13.
- `engine/astova_engine/mcp_server.py` - `audit_url` payload surfaces `unreliable` + `challenge` + a loud note;
  `scan_url` already returns the full report (meta.challenge + scorecard.unreliable).
- `web/components/report/ReportView.tsx` - a `ChallengeBanner` at the top of the report when
  `meta.challenge.detected`.
- `engine/tests/test_detect.py` (13) + `test_challenge_integration.py` (7); `test_schema.py` bumped to 13.
- docs: CURRENT_CAPABILITIES.md.

**Accuracy principle:** prefer flagging over a confident-but-wrong number - the score is kept but loudly marked
`unreliable` with a dedicated finding and banner, and the artifacts that the challenge page would otherwise
emit are removed so they don't read as real site problems.

**Breaking changes:** `SCHEMA_VERSION` is now "13" (additive meta/scorecard fields, conditional finding).

**Testing:** detector fixtures per vendor + clean-page negatives (incl. a normal Cloudflare-fronted 200 page,
not flagged); integration tests for meta, the finding, artifact removal, the unreliable flag, and MCP exposure.
Full engine suite 371 passed; web tsc + build clean.

**Known limitations:** detection is signal-based (markers/headers/status), not a render; a challenge that
returns 200 with no script/title marker and no CF headers wouldn't be caught; the numeric score is retained
(flagged) rather than suppressed at the data layer.

---

## 2026-06-29 - Web: print-friendly PDF-style report (`/report/[id]/print`)

**Objective:** let users and agencies export a clean, client-friendly report - a print-optimised HTML page
they save as PDF from the browser. No server-side PDF rendering, no new report logic.

**What changed:** added a server-rendered print page that reuses the existing report bundle, plus a "Print /
Save PDF" action on the report view. Factored the engine fetch into a shared helper so the print page and the
API proxy don't duplicate it.

**Files changed:**
- `web/lib/reportData.ts` (new) - `fetchReportBundle(token)` server helper (engine fetch + token validation)
  and the shared report/bundle types.
- `web/app/api/reports/[token]/route.ts` - refactored to use the helper (one source for the fetch).
- `web/app/report/[id]/print/page.tsx` (new) - server component; fetches the bundle server-side and renders a
  white/black, print-CSS, page-break-friendly report. No nav, no buttons, no animations, no gradients.
- `web/components/report/PrintTrigger.tsx` (new) - tiny client component that opens the print dialog on load.
- `web/components/report/ReportDetailView.tsx` - "Print / Save PDF" link to the print route.
- docs updated: CURRENT_CAPABILITIES.md.

**Content:** Astova branding, target URL, report date, AI Readiness score, a confidence note, executive
summary (from the scorecard), readiness breakdown (pillar table), action summary, top findings, the
deterministic / AI-assisted / manual lists, verification guidance, and a VERIFIED / MEASURED / ESTIMATED
footer with engine/ruleset/report versions.

**Reuse, not duplication:** the page renders from the same `report_bundle` the engine already computes; the
buckets/metadata/markdown come straight from it. Server-rendering means the full report is in the DOM before
print (no loading flash), and the print CSS forces white background + black text regardless of app theme.

**Breaking changes:** none. New route + helper + trigger; the API proxy behaviour is unchanged (same output,
now via the helper).

**Rules honoured:** reuses the report bundle/export helpers; no LLM; no server-side binary PDF (browser does
the PDF); no auth (valid share token only); no engine/scoring change (web-only milestone).

**Testing note:** no JS unit runner in web; verified by `tsc --noEmit` (clean) and `next build` (clean -
`/report/[id]/print` builds as a dynamic server route). The print page reuses the bundle already round-trip-
tested by the reports milestone.

**Known limitations:** auto-print fires on every load of the /print route (it is the print variant; the
readable variant is `/report/[id]`); needs `ASTOVA_ENGINE_URL` + persistence; styling is intentionally plain
(no logo image yet - wordmark text only); page breaks are best-effort via `page-break-inside: avoid`.

**Future opportunities:** a real branded/white-label template (agency logo + accent), a true server-side PDF
(Playwright/print-to-PDF) if a binary is needed, and a cover page.

**Questions for the Product Architect:** is browser "Save as PDF" enough for agencies, or do we need a
server-generated branded PDF next?

---

## 2026-06-29 - AI Readiness Reports: shareable `/report/[id]?share=<token>` (Engine + Web)

**Objective:** turn the action plan into a premium, shareable report a user can save, revisit and send to a
client - reusing the existing Report object, findings, knowledge cards, deterministic fixes and verification.

**What changed:** added self-describing version metadata, a derived "report bundle" (action-summary buckets +
Markdown + agent prompt), a public token endpoint, and a `/report/[id]` page that renders it. The persistence,
share tokens and the report renderer already existed - this layers the report product on top without a redesign.

**Files changed:**
- `engine/astova_engine/models.py` - `ENGINE_VERSION` / `RULESET_VERSION` / `REPORT_VERSION` constants.
- `engine/astova_engine/scanner.py` - stamps those versions into every scan's meta (URL + project).
- `engine/astova_engine/store.py` - `get_by_token` now stamps the stable row id as `meta.report_id` on load
  (the JSON was serialised before the id existed).
- `engine/astova_engine/report_export.py` (new) - pure derived views over a stored report: `action_summary`
  (deterministic / ai_assisted / manual, reusing the knowledge taxonomy + the report's fixes),
  `report_metadata`, `report_to_markdown`, `report_to_agent_prompt`, `report_bundle`.
- `engine/astova_engine/service.py` - new `GET /reports/{token}` -> `{report, bundle}`.
- `engine/tests/test_report_export.py` (new, 7) + `test_service.py` (2 endpoint tests).
- `web/app/api/reports/[token]/route.ts` (new) - proxy to the engine endpoint.
- `web/app/report/[id]/page.tsx` + `web/components/report/ReportDetailView.tsx` (new) - the page (server,
  metadata) and the read-only view (loads by share token; reuses ScoreRing / ExecutiveSummary /
  ScorecardPanel / ConfidenceLegend; renders breakdown, the three buckets, verification, and the 4 actions).
- `web/components/report/ReportView.tsx` - the Share button now copies `/report/<id>?share=<token>`.
- docs updated: CURRENT_CAPABILITIES.md.

**Report metadata (self-describing):** `report_id`, `created_at` (fetched_at), `scanned_target`,
`engine_version`, `ruleset_version`, `report_version`, `share_token` - all derived from the stored report.

**Sharing / security:** access is by the unguessable capability token only (`?share=<token>` ->
`get_by_token`); the integer row id in the path is cosmetic and is never a lookup path, preserving the
existing no-enumeration guarantee. No auth required for a valid token (per the brief).

**Reuse, not duplication:** the bundle reuses the existing findings, `report.fixes` (deterministic), and the
`knowledge.can_astova_generate` taxonomy for the buckets; the page reuses the existing report components. No
workflow logic duplicated, no re-scan (the report is rendered from stored data), no LLM.

**Breaking changes:** none. Additive endpoint + new route + new module; the legacy `/report?id=<token>` link
still resolves. Held positioning batch untouched.

**Actions:** Copy agent prompt (plan + safety guardrails), Copy Markdown, Download Markdown (`astova-action-
plan.md`), Open AI Ready Action Plan (`/ai-ready?url=<target>`).

**Testing note:** engine round-trip verified live (save -> token+id -> `get_by_token` stamps report_id ->
`report_bundle` with metadata, buckets, markdown, prompt). Web verified by `tsc` (clean) + `next build` (clean;
`/report/[id]` + `/api/reports/[token]` build). Full engine suite 351 passed.

**Known limitations:** needs `ASTOVA_ENGINE_URL` + persistence (Postgres/SQLite) to load shared reports;
findings list in the buckets is recommendation-only (no inline fix content - that's a `generate_fix` round-trip
or the AI Ready plan); ai_assisted-vs-manual split is only as good as the hand-maintained card taxonomy.

**Future opportunities:** PDF/branded export (white-label, per CLAUDE.md); inline deterministic fix content;
an owner (authenticated) view by id without a token; report diff vs the previous scan inline.

**Questions for the Product Architect:** should the report support a branded/white-label PDF export next, and
should an authenticated owner be able to open `/report/[id]` without the share token?

---

## 2026-06-29 - Web: `/mcp` setup page + `GET /mcp-guide` engine endpoint

**Objective:** put the MCP usage guidance in front of humans - a `/mcp` page where a developer picks their
client (Claude / Cursor / ChatGPT / Windsurf / generic) and gets setup, the starter prompt, the workflow,
safety rules and the tool list, all copyable.

**What changed:** exposed the existing `mcp_usage_guide` source of truth over HTTP and rendered it in the web
app. No guide content is duplicated in TypeScript - the page fetches it.

**Files changed:**
- `engine/astova_engine/service.py` - new `GET /mcp-guide?client=` -> `mcp_guide.usage_guide(client)`.
- `engine/tests/test_service.py` - 2 endpoint tests.
- `web/app/api/mcp-guide/route.ts` (new) - thin proxy to the engine `GET /mcp-guide` (gated by `ASTOVA_ENGINE_URL`).
- `web/app/mcp/page.tsx` + `web/components/McpSetupView.tsx` (new) - the page (server metadata) and the client
  view (client selector, fetch-on-select, all sections, copyable starter prompt + extracted config).
- `web/components/Nav.tsx` - "MCP" nav link; `web/app/sitemap.ts` - `/mcp` route.
- docs updated: CURRENT_CAPABILITIES.md.

**Single source of truth:** the page renders whatever `mcp_usage_guide` returns. The only client-side
derivation is `extractConfig()`, which pulls the MCP server config JSON out of a setup step for its own Copy
button - still from the guide, not hardcoded. Add a tool or change a prompt in `mcp_guide.py` and `/mcp`
updates with no web change.

**Breaking changes:** none. One additive engine endpoint, one web proxy, one page, one nav link, one sitemap
entry. No existing engine behaviour changed (the endpoint returns static content). Held positioning batch
untouched.

**Developer experience:** `/mcp` -> pick "Cursor" -> copy the config + starter prompt -> connected. Pairs with
`/agents` (CLI/prompt onboarding); both are nav-linked and in the sitemap.

**Testing note:** engine endpoint covered by 2 service tests; web verified by `tsc --noEmit` (clean) and
`next build` (clean - `/mcp` prerenders, `/api/mcp-guide` builds). Live `GET /mcp-guide` returns the guide.

**Known limitations:** the page needs `ASTOVA_ENGINE_URL` (HTTP-only, like `/ai-ready`) - without it, it shows
the "not configured" message; the config extractor assumes the `{"mcpServers"...}` shape the guide emits.

**Future opportunities:** SSR the guide at request time so it works without a client-side fetch; a remote
(HTTP connector) config variant; a "copy all setup" button.

**Questions for the Product Architect:** should `/mcp` be server-rendered (one less env dependency for a static
guide), and should `/agents` and `/mcp` merge into a single "For developers" hub?

---

## 2026-06-29 - mcp_usage_guide: self-documenting MCP setup + usage helper

**Objective:** let a developer using Claude / Cursor / ChatGPT / Windsurf ask the Astova MCP itself for the
exact setup and usage instructions - no docs hunt, no guesswork.

**What changed:** added a static `mcp_usage_guide(client)` MCP tool. It returns a compact, client-specific
guide (install + config steps, the exact starter prompt, the safe workflow, the safety rules, and every tool
with a one-line description). Scans nothing, reads no files, uses no LLM - pure static content.

**Files changed:**
- `engine/astova_engine/mcp_guide.py` (new) - `usage_guide(client)` + `SUPPORTED_CLIENTS`; per-client setup
  and starter prompt, shared purpose/workflow/safety/tool-list.
- `engine/astova_engine/mcp_server.py` - new MCP tool `mcp_usage_guide`.
- `engine/tests/test_mcp_guide.py` (new) - 8 tests.
- docs updated: CURRENT_CAPABILITIES.md, mcp.md.

**Response:** `client`, `purpose`, `recommended_entrypoints` (prepare_project_for_ai for repos, ai_ready_loop
for URLs), `setup` (client-specific), `starter_prompt` (exact prompt, with the do-not-invent guardrails baked
in), `workflow`, `safety_rules` (6 rules), and `available_tools` (all 10 tools, one line each). Supported
clients: generic / claude / cursor / chatgpt / windsurf; unknown values fall back to generic.

**Per-client tailoring:** repo agents (claude / cursor / windsurf) get the `prepare_project_for_ai` prompt and
their respective MCP-config locations; chatgpt gets the URL-first `ai_ready_loop` prompt (it usually has no
local repo). Everything else is shared.

**Drift guard:** a test parses `@mcp.tool()` definitions out of `mcp_server.py` and asserts `available_tools`
lists exactly the registered set - so adding a tool without documenting it here fails the build.

**Breaking changes:** none. One new static MCP tool.

**Developer experience:** `mcp_usage_guide("cursor")` returns copy-paste setup + the starter prompt; pair it
with `prepare_project_for_ai` and a newcomer is productive in one round-trip.

**Known limitations:** content is hand-maintained (only the tool-list is drift-checked); config snippets assume
a stdio launch via `python -m astova_engine.mcp_server`; English-only; not exposed over HTTP/CLI (MCP-only by
design - it documents the MCP).

**Future opportunities:** generate `setup` from a single source shared with `docs/mcp.md`; add the remote
(HTTP connector) config variant; localise; a `format="markdown"` option.

**Questions for the Product Architect:** should the guide's content be generated from `docs/mcp.md` to avoid two
hand-maintained copies?

---

## 2026-06-29 - prepare_project_for_ai: one-call repo context bundle for AI coding agents (MCP)

**Objective:** the first true AI-coding-agent integration - one read-only MCP call that hands an agent the
COMPLETE context to fix a local project, so it never has to orchestrate audit_project / ai_ready_loop /
explain_finding / generate_fix / verify_fix itself. This becomes the recommended entry point for agents in a repo.

**What changed:** added `prepare_project_for_ai(root_path)` - pure orchestration over existing capabilities.
It runs `ai_ready_loop` (project mode), reads the framework via the same `project.detect_framework` that
`audit_project` uses, and reshapes the result into one compact agent-optimised bundle.

**Files changed:**
- `engine/astova_engine/ai_ready.py` - new `prepare_project_for_ai()` + `_project_framework()` +
  `_RECOMMENDED_WORKFLOW`. Reuses `ai_ready_loop` (which already attaches knowledge/fix/verify per finding)
  and the `project` module - no business logic duplicated.
- `engine/astova_engine/mcp_server.py` - new MCP tool `prepare_project_for_ai`.
- `engine/tests/test_prepare_project.py` (new) - 7 tests.
- docs updated: CURRENT_CAPABILITIES.md, mcp.md.

**Response:** `project`, `framework`, `score`, `summary`, `recommended_workflow` (Review findings -> Apply
deterministic fixes first -> Complete AI-assisted tasks -> Run verify_fix for changed findings -> Run
audit_project again), and `findings[]` where each item is `{finding_id, knowledge, fix, verify}`. Findings keep
`ai_ready_loop`'s priority order. `fix` is null unless a deterministic fix is ready; `knowledge` is null when no
card exists; `verify` (the verify_fix call) is present for every finding. Read-only, no LLM, nothing applied.

**Compactness decisions:** only the four keys per finding (no `agent_next_step`/`title`/`evidence` bloat - the
knowledge card carries the detail); `fix` omitted (null) when unsupported; `knowledge` only for findings that
actually fired. Framework is derived from a cheap `os.listdir` + `detect_framework` rather than a second full
project scan - one scan total, via `ai_ready_loop`.

**Breaking changes:** none. One new MCP tool + one module function. (Doc-positioning only: `ai_ready_loop` is now
framed as the URL / quick-plan entry, and `prepare_project_for_ai` as the in-repo entry.)

**AI agent experience:** `prepare_project_for_ai("/repo")` -> a ranked worklist where every item already carries
why it matters, the exact fix (when ready), and how to verify, plus the order to work in. The agent applies
deterministic fixes, drafts AI-assisted ones from real content, asks before manual/identity items, and re-runs
to verify - all from one call.

**Known limitations:** MCP-only (no HTTP/CLI surface yet); `framework` auto-detected (no explicit override);
inherits `ai_ready_loop`'s live-scan-each-call and payload-size traits; `max_items` caps the bundle (default 25).

**Future opportunities:** an HTTP/CLI surface for the same bundle; a `since` mode (only findings new vs last run);
embed the deterministic fix `generated_content` inline for one-shot apply; accept an explicit framework.

**Questions for the Product Architect:** should `prepare_project_for_ai` also be exposed over HTTP/CLI, and
should it inline the fix content so an agent can apply without a second `generate_fix` round-trip?

---

## 2026-06-29 - Web: "Copy agent prompt" on the AI Ready result view

**Objective:** from a generated action plan at `/ai-ready`, let a user copy ONE ready-to-paste prompt that
tells an AI coding agent how to act on the plan safely - not just the raw Markdown.

**What changed:** added a "Copy agent prompt" button beside the existing "Copy Markdown" button. The prompt
reuses the Markdown plan already returned by `/api/ai-ready` and wraps it with context (target, score,
counts) and explicit safety guardrails.

**Files changed:**
- `web/lib/agentPrompt.ts` (new) - pure `buildAgentPrompt(plan)`; composes the instruction + safety rules +
  the plan's `markdown`. Testable in isolation, no I/O.
- `web/components/AiReadyView.tsx` - `copyAgentPrompt()` + the new primary button (accent), keeping the
  existing Copy Markdown button.
- docs updated: CURRENT_CAPABILITIES.md.

**Prompt content:** target URL, score, the summary counts, and the full Markdown plan (which already carries
the top findings), plus the guardrails: apply deterministic fixes as given; draft AI-assisted items only from
real page content; do NOT invent facts, author names, sameAs links, opening hours, addresses, legal claims,
local-business details or data points; ask before editing manual / human-review items; re-run Astova to verify.

**Reuse, not duplication:** no engine change and no second scan - the prompt is built client-side from the
existing response `markdown` + counts. The formatter stays the single source of truth for the plan body.

**Breaking changes:** none. One new button + one pure helper.

**Testing note:** no JS unit-test runner in the web app; verification is `tsc --noEmit` (clean) and `next build`
(clean). The built prompt was asserted to contain the target, score, counts, every safety rule, and the
Markdown plan.

**Known limitations:** the prompt embeds the whole plan, so it grows with `max_items`; clipboard needs a
secure context; English-only copy.

**Future opportunities:** a length/preview toggle; per-agent variants (Claude vs Cursor phrasing); a combined
"copy prompt + open agent" deep link where supported.

**Questions for the Product Architect:** should the agent prompt be the default/primary copy action (it is the
accent button now), with raw Markdown secondary?

---

## 2026-06-29 - Web: `/agents` first-run onboarding for AI coding agents

**Objective:** make it trivial for a developer to start using Astova from Claude / Cursor / ChatGPT /
Windsurf - copy one prompt, one set of CLI commands, or one MCP starter instruction and go.

**What changed:** added a static, indexable `/agents` page that explains the loop (Astova audits AI
Readiness -> the agent fixes the code -> Astova verifies) and provides copyable blocks. No engine change,
no auth, no billing, no LLM.

**Files changed:**
- `web/app/agents/page.tsx` (new) - the onboarding page (server component + metadata), wrapped in the
  shared `Nav`/`Footer` chrome.
- `web/components/CopyBlock.tsx` (new) - a small reusable "copy this" block (monospace content + Copy
  button) used for the prompt, CLI commands and MCP instruction.
- `web/components/Nav.tsx` - added a "For agents" nav link (discoverability).
- `web/app/sitemap.ts` - registered `/agents` as a public route.
- docs updated: CURRENT_CAPABILITIES.md.

**Page content (per brief, verbatim where specified):** the three-step loop (`astova loop .` -> hand the
Markdown plan to the agent -> `astova loop .` again); the copyable agent prompt (with the "do not invent
facts / ask before manual items" guardrails); the three CLI commands (`astova check .`, `astova loop .`,
`astova export . --output astova-action-plan.md`); the MCP starter instruction (`ai_ready_loop` ->
`explain_finding` -> `generate_fix` -> `verify_fix`); and a safety section (Astova never applies changes,
the agent edits the code, deterministic evidence + verification, human review required for
factual/legal/identity/local claims).

**Breaking changes:** none. New page + new component + one nav link + one sitemap entry. No engine change.
The held homepage positioning batch (`Hero.tsx`/`RotatingWord.tsx`/`faq.ts`/`layout.tsx`) was not touched.

**Developer experience:** `/agents` is the copy-and-go landing for agent users; the prompt and MCP
instruction encode the safe loop so an agent stays inside the deterministic lane and asks before touching
identity/factual claims.

**Testing note:** no JS unit-test runner exists in the web app; verification is `tsc --noEmit` (clean) and
`next build` (clean - `/agents` prerenders as static). The exact prompt and MCP strings were asserted to
match the brief.

**Known limitations:** copy depends on `navigator.clipboard` (HTTPS/secure-context only; no execCommand
fallback); content is hardcoded English; assumes the reader has installed the engine (no install snippet on
the page yet beyond the commands).

**Future opportunities:** an install/quickstart snippet (`pip install` + MCP config JSON) on the same page;
per-tool tabs (Claude Desktop vs Cursor vs ChatGPT) with the right MCP config; a "copy all" button.

**Questions for the Product Architect:** should `/agents` carry the MCP config JSON (stdio + HTTP) inline,
and become the primary nav CTA for the developer audience?

---

## 2026-06-29 - Homepage: AI Ready Action Plan as the conversion path

**Objective:** turn the AI Ready Action Plan into a clear homepage conversion path - a visitor enters a URL by
the hero, clicks "Generate AI Ready plan", and lands on `/ai-ready` with the plan already running.

**What changed:** refactored the existing hero scan input (`HeroDemo`) rather than adding a second one. Its
primary CTA now generates the action plan (routes to `/ai-ready?url=<encoded>`); the score-only path
(`/report`) is kept as a secondary link. `/ai-ready` reads `?url=`, prefills the field, and auto-runs once.

**Files changed:**
- `web/lib/engineTarget.ts` - new pure `aiReadyHref(raw)` (scheme-normalize + encode + build the link).
- `web/components/HeroDemo.tsx` - primary CTA "Generate AI Ready plan" via `aiReadyHref`; Enter triggers it;
  secondary "Prefer just the score?" keeps the `/report` path; caption reworded to "action plan".
- `web/components/AiReadyView.tsx` - reads `?url=` (useSearchParams), prefills, auto-runs once (guarded by a
  ref so it fires a single time, only when a `url` param is present).
- `web/app/ai-ready/page.tsx` - wrapped the view in `Suspense` (required once it uses `useSearchParams`).
- docs updated: CURRENT_CAPABILITIES.md.

**Reuse, not duplication:** no scan/workflow logic was added - the homepage only builds a link, and `/ai-ready`
+ `/api/ai-ready` (and the engine `ai_ready_loop`) do all the work. The single hero input now has two
destinations (plan / score).

**Auto-run safety:** the scan only auto-fires when the page is reached with an explicit `?url=` (i.e. the user
already clicked the CTA), and exactly once per mount - no surprise scans, no loops, no cost on a bare `/ai-ready`
visit (which still defaults the input to a sample and waits for a click).

**Breaking changes:** the hero's primary button changed from "Scan" (-> `/report`) to "Generate AI Ready plan"
(-> `/ai-ready`); the score view is one click away via the secondary link. Visual style preserved (same card,
tokens, layout). The held homepage positioning batch (`Hero.tsx` / `RotatingWord.tsx` / `faq.ts` / `layout.tsx`)
was deliberately NOT touched - this feature lives in `HeroDemo.tsx` (which `Hero` renders) and the `/ai-ready`
files only.

**Testing note:** the web app has no JS unit-test runner (only `tsc` + `next build`), so verification is a clean
`tsc --noEmit` and a successful `next build` (the `/ai-ready` page prerenders, `/api/ai-ready` builds). The pure
`aiReadyHref` helper was factored out specifically so it is unit-testable if/when a runner is added.

**Known limitations:** homepage path is URL-only; auto-run still needs `ASTOVA_ENGINE_URL` configured (else the
page shows the "engine not configured" message after auto-running); no loading skeleton tuned for the
arrive-and-run case beyond the existing button state.

**Future opportunities:** a dedicated hero headline/subcopy emphasising "plan, not just a score"; an inline
mini-result on the homepage before navigating; remember the last target.

**Questions for the Product Architect:** should the homepage lead exclusively with the plan CTA (drop the score
link), and should the hero copy itself be rewritten to sell the action plan?

---

## 2026-06-29 - Web: AI Ready Action Plan page + `POST /ai-ready` engine endpoint

**Objective:** give a human the same agent-friendly plan the MCP/CLI expose - enter a URL in the web app and
get the prioritised "what to fix next" plan with a copyable Markdown export.

**What changed:** exposed `ai_ready_loop` over HTTP (it was MCP-only by Feature 5's deliberate choice) with
the smallest clean endpoint, and added a simple web page + proxy that consume it. No workflow logic is
duplicated - the engine endpoint reuses `ai_ready_loop` and the `loop_to_markdown` formatter; the web app
only validates the URL and renders.

**Files changed:**
- `engine/astova_engine/service.py` - new `POST /ai-ready` (`{target, target_type, max_items}`); returns the
  loop response plus a `markdown` field from `export.loop_to_markdown`.
- `engine/tests/test_service.py` - 3 endpoint tests (plan+markdown, scan-error, 422).
- `web/lib/engineTarget.ts` (new) - shared `normalizeUrl` + `ssrfReason` (URL guard for engine-backed routes).
- `web/app/api/ai-ready/route.ts` (new) - thin proxy to the engine `POST /ai-ready` (gated by `ASTOVA_ENGINE_URL`).
- `web/app/ai-ready/page.tsx` + `web/components/AiReadyView.tsx` (new) - the page (server metadata) and the
  client view (URL input, score, summary counts, top actions with verify steps, Copy Markdown).
- docs updated: CURRENT_CAPABILITIES.md, mcp.md.

**Architecture note - why an endpoint now:** Feature 5 kept `ai_ready_loop` MCP-only because nothing consumed
it over HTTP. The web UI is that consumer, so the endpoint is now justified (the brief explicitly allowed
"the smallest clean engine endpoint needed"). It stays a thin wrapper; the formatter lives in `export.py`, so
both the CLI and the endpoint share one source of truth.

**Breaking changes:** none. Additive endpoint + new web files. No existing routes/pages touched (the held
homepage batch is untouched).

**Developer / user experience:** `/ai-ready` in the web app turns a URL into a ranked action plan a
non-technical user can read and a developer can copy as Markdown into Cursor/Claude/ChatGPT. The proxy is
HTTP-only (needs `ASTOVA_ENGINE_URL`); without it the UI shows a clear "engine not configured" message.

**Known limitations:** web flow is URL-only (no project upload from the browser); HTTP-only proxy (no local
shell-out fallback like `/api/scan` has) so local dev needs `ASTOVA_ENGINE_URL` pointed at a running engine;
inherits `ai_ready_loop`'s live re-fetch + payload-size limits; UI is intentionally minimal (no per-item
deep-linking into the full report yet).

**Future opportunities:** a local shell-out fallback in the proxy for zero-config dev; link each item to the
finding's report row; a "project path" mode; render the Markdown preview inline; a download-.md button.

**Questions for the Product Architect:** should `/api/ai-ready` gain a local shell-out path for dev parity
with `/api/scan`, or stay HTTP-only? Should the AI Ready page become the primary landing CTA?

---

## 2026-06-29 - CLI: `astova export` - compact Markdown action plan for coding agents

**Objective:** let a human or agent export the loop result as compact Markdown to paste into Claude,
ChatGPT, Cursor or Windsurf - "here's exactly what to fix," ready to drop into another coding agent.

**What changed:** added `astova export <target> [--output file.md] [--max-items N]`. It auto-detects URL
vs project (same `_resolve_target` as check/loop), runs `ai_ready_loop`, and renders the result as
Markdown - to stdout, or to `--output` (the only file write the command makes).

**Files changed:**
- `engine/astova_engine/export.py` (new) - `loop_to_markdown(resp, generated_at=?)`, a pure formatter
  over the loop response (no scanning, no I/O).
- `engine/astova_engine/cli.py` - `_cmd_export` + dispatch.
- `engine/tests/test_export.py` (new) - 11 tests.
- docs updated: CURRENT_CAPABILITIES.md, CLAUDE.md.

**Markdown shape:** title + `Target` / `Score` / `Generated`; a `## Summary` with the four counts; a
`## Top Actions` section, one `### N. <title>` block per item carrying Finding ID, Severity, Status,
Evidence, Why it matters (from the knowledge card), Recommended fix, Can Astova generate fix, Agent next
step, and a `Verification:` code span (the `verify_fix(...)` call); then a `Run after fixing:` footer with
``astova loop <target>``. Items with no knowledge card render `Why it matters: n/a`.

**Design:** the formatter is split out as `export.py` (pure, deterministic - accepts a `generated_at`
override so tests are stable) rather than living inline in the CLI, so it can be reused later (an MCP
`export_plan` tool, or the web report's "copy for agents" button) without dragging in argparse.

**Breaking changes:** none. Additive subcommand; legacy forms untouched.

**Developer / agent experience:** `astova export ./site --output PLAN.md` produces a paste-ready brief; a
human hands it to any agent, or an agent reads it directly. Closes the gap between "Astova found issues" and
"another tool can act on them" with zero coupling.

**Known limitations:** Markdown only (no JSON variant - that's what `astova loop --json` is for); `Generated`
is a wall-clock UTC stamp so file output differs run-to-run; `--output` overwrites without prompting;
inherits `ai_ready_loop`'s limits (live re-fetch for URLs, knowledge-card payload size).

**Future opportunities:** an MCP `export_plan` tool returning the same Markdown; a `--format` flag (json /
gh-issue / pr-body); group items by pillar; embed the deterministic fix content inline for ready-to-apply
blocks.

**Questions for the Product Architect:** should export also be an MCP tool / API endpoint, or stay CLI-only?
Should the deterministic fix `generated_content` be embedded inline in the Markdown (bigger, but apply-ready)?

---

## 2026-06-29 - CLI: `astova check` and `astova loop` subcommands

**Objective:** let developers and AI agents run Astova from the terminal - no web app, no MCP client - to
scan a URL or a local project and to get the "what to fix next" plan, in human-readable or JSON form.

**What changed:** added two subcommands to the existing `astova` console script. Pure reuse of the engine
functions; the CLI only resolves the target and formats output.
- `astova check <target> [--json]` - auto-detects URL vs local project directory and runs `scan` or
  `scan_project`; compact per-pillar summary by default, full `Report` JSON with `--json`.
- `astova loop <target> [--json] [--max-items N]` - runs `ai_ready_loop` (url/project auto-detected);
  a readable ranked next-action plan by default, the full structured loop response with `--json`.

**Files changed:**
- `engine/astova_engine/cli.py` - target resolution (`_resolve_target`), the loop printer
  (`_print_loop_human`), `_cmd_check` / `_cmd_loop`, and subcommand dispatch in `main()`. `_print_human`
  is now project-aware (framework / files header for project reports).
- `engine/tests/test_cli.py` (new) - 14 tests.
- docs updated: CURRENT_CAPABILITIES.md, CLAUDE.md (run section + repo layout).

**Target detection:** `http(s)://` -> url; an existing directory or a path-like string (`./`, `/`, `~`, or
a separator) -> project; a bare host (e.g. `example.com`) -> url with `https://` prepended.

**Breaking changes:** none. The legacy `astova <url> [flags]` / `python -m astova_engine <url>` form is
untouched - `main()` dispatches `check`/`loop` first and otherwise falls through to the original parser.

**Developer / agent experience:** `astova check ./my-site` audits a repo before deploy; `astova loop
https://site --json` gives an agent the same plan the MCP `ai_ready_loop` returns, straight from a shell -
useful in CI, pre-commit hooks, or any non-MCP automation.

**Known limitations:** url targets fetch live (network); `loop` reuses `ai_ready_loop`'s limitations
(re-fetch, payload size); no `verify`/`fix` subcommands yet (deliberately - those mutate intent and stay
behind explicit MCP/API calls); detection of a bare host as a URL could misfire on an oddly named local
folder that doesn't exist on disk.

**Future opportunities:** `astova verify <target> <finding_id>` and `astova explain <finding_id>` to round
out the loop in the shell; a `--target-type` override for the ambiguous cases; colourised output.

**Questions for the Product Architect:** should the CLI gain `explain` / `verify` / `fix` subcommands to
mirror the MCP tools, or stay a thin "assess + plan" surface?

---

## 2026-06-29 - ai_ready_loop: one-call "tell me exactly what to fix next" workflow (MCP)

**Objective:** the first genuinely impressive AI-agent moment - an agent calls ONE MCP tool and gets the
complete, prioritised next-action plan to make a URL or project AI Ready, with the fix and the verify call
already attached to each item. "Astova, what do I fix next?" answered in a single round-trip.

**What changed:** added `ai_ready_loop(target, target_type, max_items)` - pure orchestration over tools that
already exist. It assesses the target (`scan` / `scan_project`), selects the top fail/warn findings by
severity, and for each attaches the knowledge card (`explain_finding`), the deterministic fix
(`generate_fix`), and the `verify_fix` call. No new scan logic, no LLM, nothing applied.

**Files changed:**
- `engine/astova_engine/ai_ready.py` (new) - `ai_ready_loop()`; composes `scanner.scan`/`scan_project`,
  `knowledge.explain`, `fixes.generate_fix`. Classifies each item by the knowledge card's
  `can_astova_generate` taxonomy (deterministic / ai_assisted / manual).
- `engine/astova_engine/mcp_server.py` - new MCP tool `ai_ready_loop`.
- `engine/tests/test_ai_ready_loop.py` (new) - 10 tests.
- docs updated: CURRENT_CAPABILITIES.md, mcp.md.

**Response object:** `target`, `target_type`, `score`, `confidence` ("verified"), `summary`,
`findings_count`, `actionable_count`, `deterministic_fix_count`, `ai_assisted_count`, `manual_count`, and
`items[]`. Each item: `finding_id`, `title`, `status`, `severity`, `confidence`, `evidence`,
`recommendation`, `knowledge` (the card or `null`), `fix` (the generate_fix object, `supported:false` when
none), `verify` (`{tool, target, target_type, finding_id}`), and a one-line `agent_next_step`.

**Architecture decision - MCP-only, no API endpoint:** per the brief and clean-architecture judgement, this
is a workflow convenience that composes existing primitives, all of which already have HTTP endpoints. Adding
a `/ai-ready` route would duplicate that surface without new capability, so it was deliberately NOT added. The
orchestration lives in its own module (`ai_ready.py`) so it is unit-testable without the MCP layer; the MCP
tool is a thin wrapper.

**Design notes:** url targets pass the URL as fix context (html isn't retained on the report, so FAQ/richer
fixes stay `supported:false`); project targets pass a `https://YOUR-DOMAIN` placeholder origin so the
robots/llms/schema generators still emit ready-to-edit templates (the same placeholder convention the project
file-fix templates use). Items are capped at `max_items` but `actionable_count` reports the true total.

**Breaking changes:** none. Purely additive (one module, one MCP tool).

**AI agent experience:** the headline flow. `ai_ready_loop("https://site", "url")` or
`ai_ready_loop("/repo", "project")` → a ranked worklist where every item says what it is, why it matters, the
exact fix to apply, and how to verify it. Then loop: apply → `verify_fix` → next item.

**Known limitations:** url targets re-fetch live every call (no scan reuse); including full knowledge cards for
up to `max_items` items makes this the largest payload of the tools (compact-ish, but not tiny); `info`-only
findings are excluded by design (only fail/warn are actionable); the three remediation buckets come from the
hand-maintained card taxonomy, so a card's `can_astova_generate` drives the count.

**Future opportunities:** accept a prior scan token to skip the re-fetch; stream/paginate items for very large
sites; add a `since` mode that only surfaces findings new vs the last run; optionally inline a trimmed
knowledge card to shrink the payload.

**Questions for the Product Architect:** should `ai_ready_loop` ever gain an HTTP endpoint for non-MCP
consumers (e.g. the web report's "fix everything" button), or stay MCP-only? Should knowledge cards be trimmed
inside this payload to a 2-3 field summary for size?

---

## 2026-06-29 - verify_fix: deterministic re-scan to confirm a finding is resolved (Engine + API + MCP)

**Objective:** close the remediation loop. An AI coding agent applies a change itself, then asks Astova to
deterministically verify whether a SPECIFIC finding is now resolved - turning scan -> explain -> fix into a
checkable scan -> explain -> fix -> verify cycle the agent can loop on until the finding clears.

**What changed:** added `verify_fix(target, finding_id, target_type)` that re-runs the EXISTING scan
(`scan` for a URL, `scan_project` for a directory), looks up that one finding in the fresh report, and
returns a verdict. No new audit logic - it reuses the scanners wholesale and only interprets the result.

**Files changed:**
- `engine/astova_engine/verify.py` (new) - `verify_fix()`; reuses `scanner.scan` / `scanner.scan_project`
  and the `fixes._FINDING_ALIASES` id map (so `onpage.canonical` resolves like generate_fix does).
- `engine/astova_engine/service.py` - new `POST /findings/{id}/verify` (`{target, target_type}` body).
- `engine/astova_engine/mcp_server.py` - new MCP tool `verify_fix(target, finding_id, target_type="url")`.
- `engine/tests/test_verify_fix.py` (new) - 10 tests.
- docs updated: CURRENT_CAPABILITIES.md, mcp.md.

**Resolution rule (deterministic, exactly as specified):** the finding is **fixed** when it is gone from
the new scan, or present with status `pass`/`info`; **not fixed** while present as `warn`/`fail`. This
follows the engine's own severity model - `info` means "not a problem". The requested `finding_id` is
echoed verbatim; matching is alias-normalised.

**Response object:** `target`, `target_type`, `finding_id`, `fixed` (bool), `current_status`,
`current_severity`, `evidence`, `score_after` (the new overall score), `confidence` ("verified"),
`explanation`, `next_step`. A failed re-scan returns the same shape with `current_status: "error"` and an
`error` field, so callers parse one schema either way.

**Breaking changes:** none. Purely additive (one module, one POST endpoint, one MCP tool).

**Developer experience:** `curl -X POST $ENGINE/findings/canonical/verify -d '{"target":"https://x/p"}'`
answers "is canonical fixed yet?" with the current status and the score after.

**AI agent experience:** the loop is now self-checking - after applying a `generate_fix` snippet, the agent
calls `verify_fix` and either gets `fixed: true` or a `next_step` telling it to generate_fix and try again.
Works for any finding id (not just the seven fixable ones) and for both URL and project targets.

**Known limitations:** `url` targets re-fetch live every call (no reuse of a prior scan - cost + latency);
verifying one finding re-runs the WHOLE scan; `info`-status findings (e.g. an absent `tech.llms_txt`) read
as fixed by the rule even when the artifact is absent, because the engine scores them as non-problems.

**Future opportunities:** reuse a cached scan / accept a prior report token to avoid the re-fetch; batch
verify (a list of finding ids in one scan); diff `score_after` against a stored `score_before` to show the
delta the fix produced.

**Questions for the Product Architect:** should `verify_fix` accept a `scan_token` to verify against an
already-run scan instead of re-fetching? Should it support batch verification of several findings at once?

---

## 2026-06-29 - audit_project: audit a repository directly, returning the standard Report (Engine + API + MCP)

**Objective:** let an AI coding agent working INSIDE a repo audit the project from source - before deploy,
without a live URL - and get back the exact same `Report` a URL scan produces, so every existing tool
(`explain_finding`, `generate_fix`, the scorecard, the web report) consumes it unchanged.

**What changed:** added `scan_project(root_path, framework)` that reads the repo's files directly (robots.txt,
llms.txt, sitemap.xml, framework/host config for security headers, any static HTML), runs the **existing**
deterministic modules and scoring, and returns a `Report`. No new audit logic - it reuses the same module
`analyze()` functions and `build_report`/`build_scorecard` the URL path uses. Exposed on all three surfaces.

**Files changed:**
- `engine/astova_engine/scanner.py` - new `scan_project()` + disk-read helpers (`_find_project_html`,
  `_read_config_blobs`); reuses `technical/onpage/geo_readiness/local.analyze` + `build_report` +
  `build_scorecard`. Drops deploy-only findings (`_DEPLOY_ONLY_FINDINGS`) and, when no static HTML exists,
  DOM-derived findings (`_HTML_DERIVED_FINDINGS`).
- `engine/astova_engine/project.py` - `framework_public_dir()` (explicit-framework normalisation) and
  `detect_configured_security_headers()` (pure: which security headers the repo config declares).
- `engine/astova_engine/service.py` - new `POST /project/audit` (`{root_path, framework}` → `Report`).
- `engine/astova_engine/mcp_server.py` - `audit_project` refactored to return the project `Report` (was a
  bespoke file-fix dict); keeps optional `base_url`/`max_pages` live augmentation under `live_audit`.
- `engine/tests/test_project_audit.py` (new) - 16 tests; `tests/test_mcp.py` - 4 audit_project tests updated
  to the new Report contract.
- docs updated: CURRENT_CAPABILITIES.md, mcp.md.

**Accuracy principle:** the report only carries what the source can prove. Deploy-time signals (HTTPS, TLS,
HTTP status, redirects, compression, X-Robots-Tag) are omitted, not guessed. On-page/GEO checks run only
when a static HTML file is present; for an un-built SSR project (e.g. Next.js with no `out/`), `audit_project`
returns the file-based technical findings and sets `meta.html_analyzed = false`.

**Breaking changes:** the MCP `audit_project` return shape changed - it now returns a `Report` (top-level
`findings`/`scorecard`/`meta`) instead of `{project, file_status, file_fixes, page_audit}`, and it no longer
generates fixes (that moved to `generate_fix`/`fix_plan`). The param renamed `path` → `root_path` and gained
`framework`. The old `project.analyze_files` file-fix templates still exist (used elsewhere/tests) but are no
longer surfaced by the tool.

**Developer experience:** `curl -X POST $ENGINE/project/audit -d '{"root_path":"."}'` returns a full scorecard
from the repo. Framework auto-detected (or pass `framework`).

**AI agent experience:** the in-repo entry point - `audit_project(root_path)` is now the preferred tool for an
agent in a codebase: one call yields a standard `Report`, then `explain_finding`/`generate_fix` on its finding
ids close the loop, all without a deployed URL.

**Known limitations:** on-page/GEO need built static HTML (no TSX/JSX metadata parsing); security-headers
detection is substring-based on config text (presence, not correctness); reads the engine host's filesystem so
it's only meaningful on the local MCP / a co-located engine; `analyze_files` is now dead-but-tested cruft.

**Future opportunities:** parse framework metadata (Next `metadata` export, Astro frontmatter) so SSR projects
get on-page findings without a build; let `audit_project` shell a framework build to produce HTML; a
project-level multi-page audit (every route, not just index.html); fold `analyze_files` away.

**Questions for the Product Architect:** should `audit_project` optionally run the framework's build to get real
HTML for on-page/GEO? Is substring security-header detection honest enough, or should it parse the config?

---

## 2026-06-29 - generate_fix: deterministic single-finding fix generation (Engine + API + MCP)

**Objective:** let an AI coding agent ask `generate_fix(finding_id, context)` and get back a structured,
machine-readable, deterministic fix it can apply itself - completing the loop after `explain_finding` told
it *how* to fix. No LLM, no apply, no PRs: Astova supplies the exact content; the agent applies it.

**What changed:** added a `generate_fix(finding_id, context)` capability that reuses the existing
deterministic `_fix_*` generators (no duplicated logic) and returns a consistent 8-key response. Exposed it
through all three surfaces - the engine library, the HTTP API, and the MCP.

**Files changed:**
- `engine/astova_engine/fixes.py` - new `generate_fix(finding_id, context)` + helpers
  (`DETERMINISTIC_FINDINGS`, `SUPPORTED_FIX_FINDINGS`, `_FINDING_ALIASES`, `_fix_response`); dispatches to
  the existing `_fix_schema/_fix_faq/_fix_robots/_fix_llms/_fix_canonical/_fix_viewport` generators.
- `engine/astova_engine/service.py` - new `POST /findings/{id}/fix` (with a `FixContext` body: `url`, `html`).
- `engine/astova_engine/mcp_server.py` - new MCP tool `generate_fix(finding_id, url="", html="")`.
- `engine/tests/test_fix_generation.py` (new) - 11 tests.
- docs updated: CURRENT_CAPABILITIES.md, mcp.md.

**Response object (consistent for every finding):** `finding_id`, `deterministic` (bool - a generator exists
for this finding type), `supported` (bool - a generator exists AND it produced content for this context),
`explanation`, `generated_content` (the exact snippet/file body, or `null`), `target_type`
(`head_element` | `file`), `suggested_location`, `verification_method`.

**New capabilities:** an agent can now request a ready-to-paste fix for `schema.missing`, `geo.faq`,
`tech.robots.missing`, `tech.robots.ai`, `tech.llms_txt`, `canonical` (alias `onpage.canonical`) and
`tech.viewport`. Most need `url`; `schema.missing` is richer with `html`; `geo.faq` requires `html` with
>=2 Q&A pairs. Unsupported/insufficient-context findings return `supported: false` with the reason.

**Breaking changes:** none. Purely additive (one MCP tool, one POST endpoint, one new module function).

**Developer experience:** `curl -X POST $ENGINE/findings/canonical/fix -d '{"url":"https://x/p"}'` returns
the exact `<link rel="canonical">` tag and where to put it. Generators are reused, so a fix matches what
`fix_plan` would emit for the same finding.

**AI agent experience:** the closing half of the remediation loop - `audit_url` -> `explain_finding`
(understand) -> `generate_fix` (get the exact content) -> apply -> re-scan. Astova never applies the fix or
touches source; the agent stays in control.

**Known limitations:** 7 findings only (the deterministic subset); no network fetch - `generated_content`
quality depends on the `html`/`url` passed in; not wired into the report UI; the supported-finding set is
maintained by hand alongside the generators.

**Future opportunities:** widen coverage as new deterministic generators land; let `generate_fix` reuse a
prior scan's parsed HTML (scan-context reuse) instead of re-parsing; surface "generate fix" inline in the
report UI; a future `verify` primitive that re-checks just the one finding after apply.

**Questions for the Product Architect:** should `generate_fix` accept a `scan_token` to reuse already-parsed
page HTML rather than re-sending it? Should the supported-finding set be derived from the generator registry
to prevent drift?

---

## 2026-06-29 - explain_finding: per-finding knowledge exposed to AI agents (MCP + API)

**Objective:** let an AI coding agent move from "Astova found `geo.aeo`" to "fix it safely" by querying
Astova about a single finding - the missing bridge between detection and action.

**What changed:** added a structured finding-knowledge registry and exposed it through the MCP and the
HTTP API. The Knowledge Base is now machine-consumable, not human-only markdown.

**Files changed:**
- `engine/astova_engine/knowledge.py` (new) - 44-card registry (mirrors docs/KNOWLEDGE_BASE.md),
  `explain(finding_id)`, `list_cards()`, `known_finding_ids()`; resolves any of 81 finding ids (and
  variants like `title.length`) to its card.
- `engine/astova_engine/mcp_server.py` - new MCP tool `explain_finding(finding_id)`.
- `engine/astova_engine/service.py` - new `GET /findings` (index) and `GET /findings/{id}` (explain one).
- `web/app/api/findings/route.ts`, `web/app/api/findings/[id]/route.ts` (new) - thin web proxies.
- `engine/tests/test_knowledge.py` (new) - 7 tests.
- docs updated: CURRENT_CAPABILITIES.md, mcp.md, KNOWLEDGE_BASE.md.

**New capabilities:** an agent (or the web/API) can now ask "explain finding X" and get structured fix
guidance: category, can_astova_generate, agent_can_automate, human_review_required, why_it_matters,
how_to_fix, agent_guidance, framework_examples, verification, related_findings - all confidence VERIFIED.

**Breaking changes:** none. Purely additive (one MCP tool, two GET endpoints).

**Developer experience:** `curl $ENGINE/findings/geo.aeo` returns the full fix knowledge; `GET /findings`
lists all 44 cards. From the web app, `GET /api/findings/{id}`.

**AI agent experience:** after `audit_url`/`scan_url`, the agent calls `explain_finding("geo.aeo")` and
receives exactly what to change, what to never automate (e.g. fabricating facts/identity), and how to
verify - per-framework. This is the loop: scan -> explain -> fix -> re-scan.

**Known limitations:** the registry is hand-maintained alongside the markdown KB (drift risk - update
both together); no per-page context (it explains the finding type, not this page's specific instance);
not yet wired into the report UI.

**Future opportunities:** generate `knowledge.py` from the KB (or vice-versa) to kill drift; surface the
guidance inline in the report UI; a `verify` primitive; an `apply` layer.

**Questions for the Product Architect:** should `knowledge.py` and `docs/KNOWLEDGE_BASE.md` be unified
into one source (generated)? Should `explain_finding` accept page context (URL) to tailor guidance?

---

## 2026-06-29 - Architecture knowledge system established

**Objective:** maintain Astova as a long-term platform, not a pile of features, by keeping living architecture docs.

**What changed:** created `docs/CURRENT_CAPABILITIES.md` (factual today-state), `docs/PRODUCT_DECISIONS.md` (append-only ADR log, seeded with decisions 001-004), `docs/NEXT_DECISIONS.md` (unresolved founder questions), and this file.

**Files changed:** the four docs above. No code.

**New capabilities:** none (documentation).

**Breaking changes:** none.

**Developer experience:** `CURRENT_CAPABILITIES.md` is the single source of truth for what works today; `NEXT_DECISIONS.md` is where open architectural questions live.

**AI agent experience:** unchanged.

**Known limitations:** docs are maintained by hand on each meaningful change; they can drift if a change ships without updating them.

**Future opportunities:** generate parts of `CURRENT_CAPABILITIES` from the code (tool list, finding ids) to prevent drift.

**Questions for the Product Architect:** see `NEXT_DECISIONS.md`.

---

## 2026-06-29 - ChatGPT (OpenAI) added to the AI visibility sampler

**Objective:** make "are you cited in ChatGPT" honest - the sampler marketed ChatGPT but only sampled Claude/Perplexity/Gemini.

**What changed:** added a real ChatGPT engine (OpenAI Responses API + live web search) to the visibility plane, gated by `OPENAI_API_KEY`, with cost tuning.

**Files changed:** `web/lib/visibilityEngines.ts` (`sampleOpenAI`, `"ChatGPT"` engine, forced `tool_choice: web_search`, `search_context_size: "low"`, default `gpt-4o-mini`); `web/.env.example` (documented per-engine keys).

**New capabilities:** `/api/visibility` now returns ChatGPT mention / citation rate, share-of-voice and cited sources (confidence MEASURED) when `OPENAI_API_KEY` is set.

**Breaking changes:** none. Response shape unchanged.

**Developer experience:** set `OPENAI_API_KEY` in `web/.env.local` (and Vercel), run a visibility scan; ChatGPT appears alongside the other engines. ~1-2c/call (web-search fee). Override model with `ASTOVA_OPENAI_MODEL`.

**AI agent experience:** unchanged - visibility is not exposed via MCP, so agents still cannot trigger or read "am I cited". Gap tracked in NEXT_DECISIONS #3.

**Known limitations:** API proxy != consumer ChatGPT; forced search may overstate citation; not yet on the Vercel prod env; cost scales with prompts x engines x runs; visibility lives in the web layer, separate from the engine/MCP.

**Future opportunities:** a `visibility` MCP tool; date-stamped N-runs tracking; correlate readiness with measured citation; SerpAPI for AI Overviews; per-plan engine selection.

**Questions for the Product Architect:** should visibility move behind the MCP/engine? forced vs auto search as methodology? how to tier metering? commit to the API-as-proxy honesty framing in-UI now?
