# Astova - Product Decisions (Architectural Decision Log)

> Permanent, append-only log of important product / platform / engine / MCP / UX / security / data-model decisions.
> Never overwrite. If a decision changes, append a new one and mark the old as **Superseded**.
> "Final Decision" stays blank until the founder explicitly confirms.

---

# Decision 001

**Status:** Accepted
**Date:** 2026-06-28
**Category:** Security

## Problem
Shareable saved-report links exposed a sequential integer id (`/report?id=3`), so anyone could enumerate every stored report straight off the public engine.

## Current Situation
Reports are persisted with an auto-increment id; share links used that id; the engine `/scans/{id}` looked up by integer.

## Options Considered
- **Option A - Capability token (unguessable share id).** Pros: not enumerable, revocable, no auth needed for sharing. Cons: extra column + migration; old int links break.
- **Option B - Require login to view a report.** Pros: strongest control. Cons: defeats the "deliver a branded link to a client" use case.
- **Option C - HMAC-signed integer ids.** Pros: no schema change. Cons: signing must happen server-side, more moving parts, still leaks the id.

## Recommendation
Option A. Capability URLs fit the "shareable but private" need and remove the enumeration vector at the engine itself.

## Founder Questions
- Are public, login-free share links a permanent product requirement (internal-report mode)?

## Final Decision
Accepted (confirmed in session). Implemented: `scans.token`, `get_by_token`, `/scans/{token}`; integer lookup removed from the public path.

## Implementation Impact
Engine: token column + get_by_token. API: `/scans/{token}` only. MCP: none. CLI: none. Dashboard: ShareButton uses token. Plugins: n/a. Docs: this entry. Tests: `test_store.py` token cases.

## Future Considerations
When multi-tenant auth lands, reports may also be scoped to an owner; tokens remain the share mechanism.

---

# Decision 002

**Status:** Accepted
**Date:** 2026-06-29
**Category:** Product / Developer Experience

## Problem
The headline "Overall GEO score" excluded the on-demand performance pillar, so a page with a bad Lighthouse score still showed a rosy headline - false reassurance.

## Current Situation
`overall_score` / `headline_score` are computed without performance; running PageSpeed updated only the Performance card, never the headline.

## Options Considered
- **Option A - Fold performance into the headline once measured.** Pros: a bad speed score can't hide. Cons: muddies the GEO-readiness message with an infra-dependent, noisy axis.
- **Option B - Keep the headline as AI-readiness only, label clearly, show performance as a distinct score.** Pros: clean separation, honest, fits GEO-first positioning. Cons: two numbers to explain.

## Recommendation
Option B, with explicit signposting (flag "speed not measured yet" before running; "scored separately" after).

## Founder Questions
- Is page speed part of "AI readiness" conceptually, or a separate axis?

## Final Decision
Accepted (founder chose "keep separate, label clearly"). Implemented: headline relabelled as AI-readiness; before/after performance notes; per-metric fixes surfaced in the Performance panel.

## Implementation Impact
Engine: none. API: none. MCP: none (note: the MCP headline already excludes performance). CLI: none. Dashboard: ReportView note + PerformancePanel fixes. Docs: this entry. Tests: none added.

## Future Considerations
If readiness is later proven to correlate with citation, revisit whether speed belongs in the score empirically rather than by opinion.

---

# Decision 003

**Status:** Accepted
**Date:** 2026-06-29
**Category:** Product / MCP boundary

## Problem
The visibility sampler marketed "ChatGPT" but only sampled Claude/Perplexity/Gemini. It needed a real ChatGPT engine, and the methodology and cost needed deciding.

## Current Situation
`web/lib/visibilityEngines.ts` sampled engines via their web-search APIs; no OpenAI engine; visibility is web-layer only, not in the engine or MCP.

## Options Considered
- **Option A - OpenAI Responses API + web_search, forced via tool_choice, gpt-4o-mini.** Pros: real ChatGPT proxy, cheap, returns citations reliably. Cons: API != consumer ChatGPT; forced search may overstate; not exposed to agents.
- **Option B - Leave ChatGPT out, keep proxying with Claude.** Pros: simplest. Cons: dishonest labelling.
- **Option C - Substitute a cheaper engine (Perplexity) for ChatGPT.** Pros: cheaper. Cons: each engine is a different system; cannot represent ChatGPT's citations.

## Recommendation
Option A. Forced search is required (auto mode returned zero citations on small models). `search_context_size: "low"` trims cost.

## Founder Questions
- Should the MEASURED visibility plane move behind the MCP/engine so it shares the readiness object model?
- Forced vs auto search as the standing methodology?
- How to tier metering (prompts x engines x cadence)?

## Final Decision
Accepted (founder approved adding OpenAI; will supply the key). Implemented: `sampleOpenAI`, `"ChatGPT"` engine gated by `OPENAI_API_KEY`, forced search, low context, gpt-4o-mini default.

## Implementation Impact
Engine: none. API: `/api/visibility` includes ChatGPT when keyed. MCP: none (gap). CLI: none. Dashboard: ChatGPT appears in visibility results. Docs: this entry + ARCHITECTURE_UPDATES. Tests: none added (live-API).

## Future Considerations
Expose visibility via MCP; date-stamped N-runs tracking; correlate with readiness (the empirical moat); SerpAPI for AI Overviews.

---

# Decision 004

**Status:** Proposed
**Date:** 2026-06-29
**Category:** Engine / Data Model

## Problem
There are two independent scoring systems - the `scoring.py` severity-penalty `overall_score` and the `scorecard.py` credit-model `headline_score` ("AI Retrievability"). They can disagree, are double-maintained, and confuse "what is the score".

## Current Situation
Both run on every scan. The scorecard headline is the brand-facing number; `overall_score` powers pillar cards and the dashboard. `Pillar.LOCAL` (weight 10) is dead (local findings emit under GEO).

## Options Considered
- **Option A - Collapse to one derived score (the scorecard), retire the penalty model.** Pros: one truth, reproducible, publishable as a spec. Cons: migration; the dashboard/pillar cards must be re-derived from the scorecard.
- **Option B - Keep both, document the split.** Pros: no work. Cons: permanent confusion and drift; blocks "publish the scoring spec".
- **Option C - Keep penalty model internally, expose only the scorecard.** Pros: less migration. Cons: still two systems to maintain.

## Recommendation
Option A, as part of making the ruleset a published, versioned standard. Also fix or remove the dead `Pillar.LOCAL` weight.

## Founder Questions
- Do we want the score to be an open, published, versioned spec (a la Core Web Vitals)? That choice forces Option A.

## Final Decision
_(blank - awaiting founder confirmation)_

## Implementation Impact
Engine: large (scoring + scorecard unified, pillar model derived). API/MCP: report shape may simplify. CLI/Dashboard: re-derive pillar cards. Docs: scoring spec. Tests: significant.

## Future Considerations
A single, versioned, calibrated score is the foundation for the "AI Readiness standard" positioning and for correlating readiness with measured citation.
