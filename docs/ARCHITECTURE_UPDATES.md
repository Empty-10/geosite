# Astova - Architecture Updates

> Append-only progress log. A new entry after every significant piece of work.
> Newest at the top.

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
