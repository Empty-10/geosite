# Astova - Architecture Updates

> Append-only progress log. A new entry after every significant piece of work.
> Newest at the top.

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
