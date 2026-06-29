# Astova - Next Decisions

> NOT a TODO list. These are unresolved architectural questions that need founder input before code is written.
> When multiple reasonable solutions exist, the question lands here instead of an assumption being made.
> Formal decisions, once taken, move to PRODUCT_DECISIONS.md.

---

## 1. SSRF guard + authentication on the public MCP / engine
**Why it matters:** the engine fetches arbitrary user-supplied URLs server-side with no allow-list or private-range block, and `/mcp/` + the engine API are public with no auth. This is a live SSRF + compute-abuse vector (internal IPs, cloud metadata endpoints, unlimited paid renders).
**Possible approaches:** (a) SSRF allow-list + private-range block at the fetch layer, plus API keys / OAuth + rate limiting on public surfaces; (b) keep the engine private and only expose an authenticated gateway; (c) per-tenant tokens for the HTTP MCP.
**Recommendation:** (a) now (block private ranges + add a gateway token), (c) when multi-tenant lands.
**Consequences:** (a) modest work, closes the hole; doing nothing risks a real incident and blocks any public promotion.
**Priority:** High

## 2. Consolidate the two scoring systems into one published spec
**Why it matters:** two systems (`overall_score` penalty model vs `headline_score` scorecard) disagree and are double-maintained; blocks publishing the score as a standard. See PRODUCT_DECISIONS 004.
**Possible approaches:** (a) collapse to the scorecard, derive pillar cards from it; (b) keep both; (c) hide the penalty model, expose only the scorecard.
**Recommendation:** (a), and turn the ruleset into a versioned, published spec.
**Consequences:** (a) one truth + the foundation for "the standard", but a real migration; (b) permanent drift.
**Priority:** High

## 3. Expose the MEASURED visibility plane via MCP / the engine
**Why it matters:** "am I cited" sampling is web-only, so AI agents (Claude Code / Cursor / ChatGPT) cannot see it and it cannot be correlated with readiness in one object model.
**Possible approaches:** (a) a `visibility` MCP tool returning a `confidence:"measured"` object; (b) move sampling into the engine service; (c) leave in web, expose via API only.
**Recommendation:** (a) + (b) over time, so readiness and visibility share one data model.
**Consequences:** unlocks the agent loop for visibility and the empirical readiness-to-citation correlation (the moat).
**Priority:** Medium

## 4. The apply layer (auto-apply protocol + framework adapters)
**Why it matters:** "fixes, not findings" is half-built - patches are generated but nothing applies them. To be the standard, fixes must be applicable (PR, file write, plugin one-click).
**Possible approaches:** (a) an MCP `apply` tool returning a diff/patch for a detected framework; (b) a GitHub App that opens fix PRs; (c) a WordPress/Shopify plugin for one-click apply.
**Recommendation:** (a) first (the agent path), then (b)/(c).
**Consequences:** closes the loop and is category-defining; meaningful per-framework work.
**Priority:** Medium

## 5. Real per-module scan progress (streaming) vs the current paced ticker
**Why it matters:** the scan progress UI is a paced animation, not real progress; the brand is "verified, not faked".
**Possible approaches:** (a) SSE/streaming per-module completion from the engine; (b) keep paced + honest copy (current); (c) chunked job + poll.
**Recommendation:** (a) eventually; (b) is the honest stopgap already shipped.
**Consequences:** (a) truthful UX but engine work; (b) acceptable for now.
**Priority:** Medium

## 6. Fix the dead `Pillar.LOCAL` weight and the data model
**Why it matters:** `Pillar.LOCAL` carries weight 10 but local findings emit under GEO, so the weight is never applied and the model misrepresents itself.
**Possible approaches:** (a) make local a real pillar; (b) remove the LOCAL weight and fold local into GEO explicitly.
**Recommendation:** (b) unless local becomes a first-class product axis.
**Consequences:** small cleanup; removes a latent correctness bug.
**Priority:** Low
