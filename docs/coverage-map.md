# Coverage map & checks to add

Maps a competitor's 20-row "AI retrievability" LLM-prompt auditor against astova's engine,
and specifies the deterministic checks worth adding. Implement these in the engine
(Claude in VS Code) following the existing conventions — see "Implementation notes" below.

> Framing: the competitor's tool is an *LLM told to score HTML deterministically*. It can't
> truly be reproducible (an LLM drifts). astova does the same job in real parser code, which
> genuinely is reproducible. So we mine their checklist for **coverage**, not architecture —
> and we deliberately reject two of their ideas (see "Do NOT adopt").

## Their 20 rows + overlay vs astova

| Their row | astova status | Where / note |
|---|---|---|
| 1. Page identity & intent clarity | 🟡 partial | title+h1 exist; no explicit coherence check |
| 2. Title tag quality | ✅ | `onpage` |
| 3. Meta description quality | ✅ | `onpage` |
| 4. URL structure & canonical | 🟡 partial | canonical ✅; URL-structure quality ❌ |
| 5. Heading architecture | ✅ | `onpage` |
| 6. Intro block quality | ✅ | `geo_readiness` front-loading |
| 7. Featured answer blocks (AEO) | ✅ | `geo_readiness` up-front answer block (position-gated, ~350-word window) |
| 8. Summary bullets near top | 🟡 partial | lists detected; not position-scored |
| 9. FAQ section quality | ✅ | `geo_readiness` FAQ section + FAQPage schema |
| 10. Chunking & extractable paragraphs | 🟡 partial | structure yes; no paragraph-length chunking |
| 11. Lists & tables | ✅ | `geo_readiness` |
| 12. Internal linking & anchor text | ❌ | gap |
| 13. Link attributes & jump links | ❌ | gap |
| 14. External links to authoritative sources | ❌ | gap |
| 15. Images & media | 🟡 partial | alt ✅; width/height + lazy ❌ |
| 16. Accessibility basics | ❌ | gap (only alt today) |
| 17. Performance & delivery | 🟡 partial | PSI perf ✅; resource-hint signals ❌ |
| 18. Authority, trust & E-E-A-T | ✅ | `geo_readiness` trust/E-E-A-T (author, dates, sameAs) |
| 19. Indexability & technical sanity | ✅ | `technical` |
| 20. Structured data & schema | ✅ | `onpage` |
| Overlay: anchors + jump links | ❌ | → row 13 |
| Overlay: FAQ / process | ❌ | → row 9 |
| Overlay: schema ≥3 types | ✅ | `onpage` detects types |
| Overlay: root files (robots+sitemap+llms.txt) | 🟡 | robots+sitemap ✅; `llms.txt` ❌ |
| Overlay: delivery signals | ❌ | → row 17 |

We already cover ~14 of 20 well. The gaps below are all deterministic and additive.

## Checks to add (the build list)

Each is a pure function returning `list[Finding]`, confidence `VERIFIED`. Severity in
brackets. Group by module.

> **Status (schema_version 2):** 10 of 12 implemented with fixture tests (54 tests pass).
> Remaining: the two low-priority `geo_readiness` checks (summary bullets, paragraph chunking).

### `onpage.py` — ✅ DONE
- ✅ **Internal/external link analysis** [medium] → `onpage.links` (counts + generic-anchor flag).
- ✅ **External links to authoritative sources** [low] → `onpage.outbound`.
- ✅ **In-page jump/anchor links** [low] → `onpage.jump_links` (resolve `#id` to an element).
- ✅ **Image dimensions & lazy-load** [low] → `onpage.images.dims`.
- ✅ **URL structure quality** [low] → `onpage.url` (page URL threaded into `analyze`).
- ✅ **Accessibility basics** [low] → `onpage.lang`, `onpage.form_labels` (row 16; On-page pillar
  per the implementation notes, though grouped with the technical batch).

### `geo_readiness.py` — partial
- ✅ **FAQ detection** [medium] → `geo.faq` (`FAQPage` JSON-LD or ≥2 answered Q-headings).
- ✅ **AEO answer block, position-gated** [high] → `geo.aeo` (first self-contained answer `<p>`
  in the first ~350 visible words; >220 → warn, none → fail; uses the rendered DOM).
- ⬜ **Summary bullets near top** [low] — a list within the first ~350 visible words that
  isn't navigation. Position-scored, not just "a list exists". *(not yet built)*
- ⬜ **Paragraph chunking** [low] — share of body paragraphs that are short/extractable
  (~40–120 words); long walls of text score lower. *(not yet built)*
- ✅ **Trust / E-E-A-T presence** [medium] → `geo.trust` (author/date/about+contact/entity sameAs).

### `technical.py` (or a small `delivery.py`) — ✅ DONE
- ✅ **llms.txt detection** [low/info] → `tech.llms_txt` (fetched at the boundary via `NetInputs`;
  PASS present / INFO absent — low-impact, doesn't penalize).
- ✅ **Resource-hint / delivery signals** [low] → `tech.resource_hints` (preload/preconnect/
  dns-prefetch + async/defer scripts, from the HTML head; distinct from the PSI score).

## Do NOT adopt (anti-patterns for us)

- **Per-engine weighting** (scoring each row for ChatGPT/Gemini/Perplexity × invented
  weights). Nobody knows those weights; presenting fabricated multipliers as precision is
  exactly the false precision our brand rejects. Real per-engine differences belong in the
  future **MEASURED** citation-sampling layer (actually querying the engines), never as
  guessed weights on deterministic checks.
- **One hidden "hybrid" headline.** Our edge is showing the pillar breakdown, not
  obscuring it behind a single number.

## Worth borrowing (rules, not architecture)

- **Visible-window extraction** — score intro/answer/bullets only from the first ~350
  rendered visible words. Use the Playwright-rendered DOM when present.
- **Position-gated answer detection** and **explicit critical gates** (fail conditions),
  which sharpen `geo_readiness`.
- Round-down-on-ambiguity already matches our penalty model — keep it.

## Implementation notes (conventions to follow)

- Pure modules: a check takes parsed input (and `NetInputs` for anything networked) and
  returns `list[Finding]`. No module reaches into another or fetches directly.
- Every `Finding` sets `confidence=VERIFIED`, plus `evidence` and a plain-English
  `recommendation`.
- Network material (llms.txt) is fetched at the scanner boundary and passed in — keep
  parsing offline- and fixture-testable.
- Add fixture tests per check (`test_onpage.py`, `test_geo.py`, etc.) and update the schema
  snapshot. Bump `schema_version` if the report shape changes.
- New findings map to existing pillars (On-page, GEO, Technical) — do **not** add a new
  pillar; the 5-pillar scoring stays intact. Accessibility findings → On-page;
  E-E-A-T/trust → GEO.
