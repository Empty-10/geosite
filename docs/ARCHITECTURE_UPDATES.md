# Astova - Architecture Updates

> Append-only progress log. A new entry after every significant piece of work.
> Newest at the top.

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
