"""Answerability Review synthesis: verdict, confidence, Likely AI Quote, consultant summary, and the
standard Expert Review contract object. Pure + deterministic - reads a report dict (findings + meta +
fixes) and returns the contract. No LLM: the consultant summary is a prioritized template engine.
"""

from __future__ import annotations

from . import reviews

NAME = "Answerability Review"
KEY = "answerability"

# Section breakdown: section name -> the findings that compose it (existing geo.* + the 5 new ones).
SECTIONS: list[tuple[str, list[str]]] = [
    ("Immediate answer", ["geo.aeo", "geo.frontload", "geo.answer_self_contained", "geo.intro_quality"]),
    ("Structure & headings", ["geo.chunking", "geo.heading_coverage"]),
    ("Extractability", ["geo.structure", "geo.summary_bullets", "geo.table_extractability"]),
    ("FAQ & questions", ["geo.faq", "geo.question_coverage", "geo.qa_headings"]),
    ("Quoteability & confidence", ["geo.data_density", "geo.definitive", "geo.definition_present"]),
    ("Depth, freshness & trust", ["geo.depth", "geo.thin_content", "geo.freshness", "geo.trust", "geo.entity"]),
]

_ALL_IDS = [fid for _, ids in SECTIONS for fid in ids]

SUMMARY_LIMIT = 4


def verdict(sm: dict[str, str]) -> str:
    if sm.get("geo.no_content") == "fail" or sm.get("geo.aeo") == "fail":
        return "weak"
    strong = (
        sm.get("geo.aeo") == "pass"
        and sm.get("geo.chunking") == "pass"
        and sm.get("geo.definitive") == "pass"
        and (sm.get("geo.structure") == "pass" or sm.get("geo.summary_bullets") == "pass")
        and sm.get("geo.answer_self_contained") not in ("warn", "fail")
    )
    return "strong" if strong else "partial"


def _eq(sm, fid, *statuses):
    return sm.get(fid) in statuses


# Tier-0 overrides: if matched, the summary is just this single line.
_OVERRIDES: list[tuple] = [
    (lambda sm: _eq(sm, "geo.no_content", "fail"),
     "The page has almost no readable text in its HTML, so there is nothing for an AI engine to "
     "quote. Fix this first: server-render the content so it's in the initial HTML."),
    (lambda sm: _eq(sm, "geo.js_rendered", "fail"),
     "Most content only appears after JavaScript runs, so non-rendering AI crawlers see a near-empty "
     "page. Server-render or prerender the key content."),
]

# Prioritised consultant templates (deterministic). Highest-value lines first; up to SUMMARY_LIMIT used.
_TEMPLATES: list[tuple] = [
    # Tier 1 - the answer itself
    (lambda sm: _eq(sm, "geo.aeo", "fail"),
     "There is no extractable answer near the top - an AI engine has no clean sentence to quote. "
     "Lead with a direct, self-contained answer in the first ~150 words."),
    (lambda sm: _eq(sm, "geo.aeo", "warn"),
     "Your answer exists but starts too far down the page; move it into the first ~150 words so it's "
     "the first thing an engine reads."),
    (lambda sm: _eq(sm, "geo.aeo", "pass") and _eq(sm, "geo.answer_self_contained", "warn"),
     "You have an up-front answer, but it opens with a reference an engine can't resolve "
     "('It…/This…'). Rewrite the first sentence to name its subject so it stands alone."),
    (lambda sm: _eq(sm, "geo.aeo", "pass") and _eq(sm, "geo.frontload", "warn"),
     "You have a quotable answer, but the page doesn't state its purpose up top - front-load what "
     "this page is about in the opening line."),
    (lambda sm: _eq(sm, "geo.intro_quality", "warn"),
     "The intro reads as marketing rather than an answer - open with a clear, factual statement; "
     "promotional intros get passed over by AI answer engines."),
    # Tier 2 - structure & extractability
    (lambda sm: _eq(sm, "geo.structure", "warn") and _eq(sm, "geo.summary_bullets", "warn"),
     "Add a short summary bullet list and a content list near the answer - engines extract discrete "
     "chunks, and AI Overviews favour bullets."),
    (lambda sm: _eq(sm, "geo.chunking", "warn"),
     "The body reads as walls of text. Break it into self-contained ~20-80-word paragraphs under "
     "descriptive sub-headings."),
    (lambda sm: _eq(sm, "geo.heading_coverage", "warn"),
     "Long content with too few sections - add H2/H3 sub-headings so engines can segment and quote "
     "individual parts."),
    (lambda sm: _eq(sm, "geo.table_extractability", "warn"),
     "A data table has no header row, so engines can't read it as structured data - add <th> headers."),
    # Tier 3 - confidence & quoteability
    (lambda sm: _eq(sm, "geo.definitive", "warn"),
     "The language hedges ('might/usually/arguably'); engines pass over uncertain sources. Tighten to "
     "direct, confident statements."),
    (lambda sm: _eq(sm, "geo.data_density", "warn"),
     "The page makes claims with almost no figures. Add concrete stats, dates and measurements - "
     "data-rich pages get quoted far more."),
    (lambda sm: _eq(sm, "geo.definition_present", "info"),
     "For a 'what is…' query there's no clear definition near the top. A one-line 'X is …' makes an "
     "ideal quote."),
    (lambda sm: _eq(sm, "geo.question_coverage", "warn"),
     "Some question-style headings have no answer beneath them - follow every question heading "
     "directly with a concise answer."),
    # Tier 4 - depth / trust
    (lambda sm: _eq(sm, "geo.thin_content", "warn"),
     "The page is thin; more depth and coverage help an engine trust and quote it."),
    (lambda sm: _eq(sm, "geo.trust", "warn"),
     "Weak trust signals (author/date/about). Add a byline and published date - engines weigh source "
     "credibility before quoting."),
    (lambda sm: _eq(sm, "geo.freshness", "warn"),
     "The content is dated over 18 months ago - refresh and re-date it; engines favour current pages."),
]

_ALL_CLEAR = (
    "Strong answerability: a clear, self-contained up-front answer, scannable structure, and "
    "confident, data-backed language. ChatGPT, Claude or Gemini could quote this page with confidence."
)


def consultant_summary(sm: dict[str, str]) -> list[str]:
    for pred, line in _OVERRIDES:
        if pred(sm):
            return [line]
    matched = [line for pred, line in _TEMPLATES if pred(sm)]
    if not matched:
        return [_ALL_CLEAR]
    return matched[:SUMMARY_LIMIT]


def _likely_ai_quote(by_id: dict[str, dict]) -> str | None:
    aeo = by_id.get("geo.aeo")
    if not aeo:
        return None
    val = aeo.get("value")
    return val.get("snippet") if isinstance(val, dict) else None


def summarize(report: dict) -> dict:
    """Build the Answerability Review contract object from a report dict."""
    findings = report.get("findings", [])
    by_id = {f["id"]: f for f in findings}
    sm = reviews.status_map(findings)
    fix_ids = {fx.get("finding_id") for fx in report.get("fixes", []) if fx.get("finding_id")}

    sections = [
        {"name": name, "status": reviews.section_status(ids, by_id),
         "findings": [fid for fid in ids if fid in by_id]}
        for name, ids in SECTIONS
    ]
    related = [fid for fid in _ALL_IDS if fid in by_id]

    return reviews.build_review(
        key=KEY, name=NAME,
        verdict=verdict(sm),
        confidence=reviews.review_confidence(report.get("meta", {}), findings),
        summary=consultant_summary(sm),
        likely_ai_quote=_likely_ai_quote(by_id),
        sections=sections,
        counts=reviews.classify_findings(_ALL_IDS, by_id, fix_ids),
        related_findings=related,
    )
