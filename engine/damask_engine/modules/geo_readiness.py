"""GEO-readiness module — the on-page factors that correlate with being cited by AI.

IMPORTANT: this is deterministic and VERIFIED. It is NOT citation sampling (that is a
separate, MEASURED module added in Phase 3). Here we only judge whether the page is built
to be cited: front-loaded answers, confident language, extractable structure, schema.
Signals are grounded in 2026 GEO research (see docs / chat history).
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from bs4 import BeautifulSoup, NavigableString, Tag

from ..models import Confidence, Finding, Pillar, Severity, Status

P = Pillar.GEO
C = Confidence.VERIFIED

# Content older than this (days) reads as stale to AI engines that favour fresh, maintained pages.
FRESH_STALE_DAYS = 540  # ~18 months

# sameAs targets that ground an entity for LLMs (knowledge bases weigh most).
_KNOWLEDGE_BASES = ("wikipedia.org", "wikidata.org")
_AUTH_PROFILES = ("linkedin.com", "crunchbase.com", "twitter.com", "x.com", "facebook.com",
                  "instagram.com", "youtube.com", "github.com")

# Hedging language gets passed over by AI; definitive language is ~2x more likely cited.
HEDGE_WORDS = {
    "might", "maybe", "perhaps", "possibly", "could", "sometimes", "generally",
    "usually", "often", "arguably", "seemingly", "presumably", "likely", "probably",
    "somewhat", "relatively", "fairly", "tends", "tend",
}

# AEO answer-block gating, scored over the first rendered visible words (see coverage-map).
AEO_WINDOW = 350         # only look this far down the visible text
AEO_GOOD_MAX = 220       # an answer starting deeper than this is too low
MIN_ANSWER_WORDS = 12    # a "self-contained answer" paragraph is at least this long
_SKIP_TEXT = {"script", "style", "noscript", "template"}

# JS-dependent content: share of words that only appear after JavaScript runs (needs --render).
JS_RENDER_WARN = 0.15    # ≥15% render-only → warn
JS_RENDER_FAIL = 0.50    # >50% render-only → fail
JS_RAW_MIN_WORDS = 50    # raw HTML this thin ≈ an empty shell without JS

# Promotional/marketing language that signals an intro is selling rather than answering.
PROMO_MARKERS = (
    "#1", "number one", "world-class", "world's ", "award-winning", "industry-leading",
    "best-in-class", "cutting-edge", "cutting edge", "revolutionary", "trusted by",
    "leading provider", "market-leading", "premier ", "top-rated", "best in the",
    "sign up", "get started", "buy now", "free trial", "book a demo", "shop now",
    "subscribe now", "contact us today", "order now", "limited time",
)
CHUNK_MIN_WORDS = 15     # a substantive paragraph
CHUNK_WALL_WORDS = 150   # a "wall of text" that's hard to extract a clean chunk from

# Concrete-data patterns. Pages dense with figures/stats get cited far more by AI engines.
_DATA_PATTERNS = {
    "percent": re.compile(r"\d+(?:\.\d+)?\s?%"),
    "currency": re.compile(r"[$£€]\s?\d[\d,]*(?:\.\d+)?|\b\d[\d,]*(?:\.\d+)?\s?(?:usd|gbp|eur|dollars|pounds|euros)\b", re.I),
    "year": re.compile(r"\b(?:19|20)\d{2}\b"),
    "measure": re.compile(r"\b\d+(?:\.\d+)?\s?(?:ms|kg|km|cm|mm|mph|km/h|gb|mb|tb|kb|kw|hrs?|hours?|mins?|minutes?|days?|weeks?|months?|years?|°[cf]?|x|×)\b", re.I),
    "big_number": re.compile(r"\b\d{1,3}(?:,\d{3})+\b"),
}
DATA_RICH_POINTS = 5     # this many concrete data points → rich
DATA_RICH_PER_100 = 1.5  # …or this density per 100 words
DATA_SUBSTANTIAL_WORDS = 300  # a content page this long with almost no data is weak for citation


NO_CONTENT_WORDS = 10  # below this, the page is effectively empty (usually a JS app shell)


def analyze(soup: BeautifulSoup, text: str, render_delta: dict | None = None) -> list[Finding]:
    out: list[Finding] = []
    words = text.split()
    total = len(words)

    # Root-cause guard: a near-empty page (often a client-rendered SPA whose content isn't in the
    # HTML). Collapse the granular content checks — which would all fire as confusing symptoms —
    # into ONE clear, critical finding. (Still run the JS-render check for the raw-vs-rendered nuance.)
    if total < NO_CONTENT_WORDS:
        out.append(_no_content(total, render_delta))
        if render_delta is not None:
            out.append(_js_render_check(render_delta))
        return out

    # --- front-loading: does the opening lead with a real answer sentence (not preamble)? ---
    # Stronger than a raw word count: the first ~150 words must contain a complete declarative
    # sentence, not just headings, taglines or navigation fragments.
    opening = " ".join(words[:150])
    # Only count spans that actually terminate with sentence punctuation — a run of headings,
    # taglines or menu items (no full stops) won't masquerade as one long "sentence".
    candidates = re.findall(r"[^.!?]*[.!?]", opening)
    lead = next((c.strip() for c in candidates if len(c.split()) >= MIN_ANSWER_WORDS), None)
    front_ok = lead is not None
    out.append(Finding(
        "geo.frontload", P, "Front-loaded answer",
        Status.PASS if front_ok else Status.WARN, Severity.HIGH, C,
        value={"opening_words": len(words[:150]), "has_answer_sentence": front_ok},
        evidence=(f"opens with: “{(lead[:120] + '…') if len(lead) > 120 else lead}”" if front_ok
                  else "the first ~150 words hold no complete answer sentence (headings, taglines "
                       "or fragments only)"),
        recommendation=None if front_ok else
        "Open with a direct, complete answer sentence in the first ~150 words — not a heading, "
        "tagline or menu. AI engines extract from the very top of the page.",
    ))

    # --- definitive vs hedged language ---
    if total:
        hedges = sum(1 for w in words if w.strip(".,;:!?\"'()").lower() in HEDGE_WORDS)
        ratio = hedges / total
        ok = ratio < 0.02
        out.append(Finding(
            "geo.definitive", P, "Definitive language",
            Status.PASS if ok else Status.WARN, Severity.MEDIUM, C,
            value={"hedge_words": hedges, "ratio": round(ratio, 4)},
            recommendation=None if ok else
            "Reduce hedging ('might', 'usually', 'arguably'…). Cited passages use "
            "confident, direct language.",
        ))

    # --- extractable structure: content lists & tables (navigation menus don't count) ---
    all_lists = soup.find_all(["ul", "ol"])
    content_lists = [lst for lst in all_lists if not _is_nav_list(lst)]
    tables = soup.find_all("table")
    has_structure = (len(content_lists) + len(tables)) > 0
    nav_only = not has_structure and len(all_lists) > 0
    out.append(Finding(
        "geo.structure", P, "Extractable structure (lists/tables)",
        Status.PASS if has_structure else Status.WARN, Severity.MEDIUM, C,
        value={"lists": len(content_lists), "tables": len(tables)},
        evidence="only navigation menus found — no content lists or tables" if nav_only else None,
        recommendation=None if has_structure else (
            "Add a real content list or table near the answer — the lists on this page are "
            "navigation menus, which AI engines ignore." if nav_only else
            "Add lists/tables and short paragraphs — AI engines lift discrete chunks, and AI "
            "Overviews favour list formatting."),
    ))

    # --- question-style headings (match the way people prompt) ---
    q_headings = [
        h.get_text(strip=True)
        for h in soup.find_all(["h2", "h3"])
        if "?" in h.get_text()
    ]
    out.append(Finding(
        "geo.qa_headings", P, "Question-style headings",
        Status.PASS if q_headings else Status.INFO, Severity.LOW, C,
        value=len(q_headings),
        evidence="; ".join(q_headings[:3]) or None,
        recommendation=None if q_headings else
        "Consider question-form H2/H3s that mirror real prompts (FAQ-style).",
    ))

    # --- thin content warning ---
    if total < 300:
        out.append(Finding(
            "geo.thin_content", P, "Content depth", Status.WARN, Severity.MEDIUM, C,
            value=total,
            recommendation="Page is thin (<300 words); depth and coverage help citation.",
        ))
    else:
        out.append(Finding("geo.depth", P, "Content depth", Status.PASS, Severity.INFO, C,
                           value=total))

    # --- new deterministic checks (coverage-map "Checks to add") ---
    out.append(_aeo(soup))
    out.append(_summary_bullets(soup))   # Row 8 — bullets near the top (nav-aware)
    out.append(_intro_quality(soup, text))  # Row 6 — promotional/unclear intro gate
    out.append(_chunking(soup))          # Row 10 — extractable paragraph chunks
    out.append(_data_density(text))      # quotable stats / concrete-figure density
    out.append(_faq(soup))
    out.append(_trust(soup))
    out.append(_freshness(soup, datetime.now(timezone.utc)))  # dated/recent content
    out.append(_entity(soup))            # entity grounding (sameAs to knowledge bases)

    # --- JavaScript-dependent content (only when a render was captured via --render) ---
    if render_delta is not None:
        out.append(_js_render_check(render_delta))

    return out


def _no_content(total: int, render_delta: dict | None) -> Finding:
    js = ""
    if render_delta:
        rendered = int(render_delta.get("rendered_words", 0))
        raw = int(render_delta.get("raw_words", 0))
        if rendered > raw + 20:
            js = (" The content appears only after JavaScript runs, so crawlers that don't execute "
                  "JS see this near-empty page.")
    return Finding(
        "geo.no_content", P, "No readable content", Status.FAIL, Severity.CRITICAL, C,
        value={"words": total},
        evidence=f"only {total} visible word(s) in the page HTML",
        recommendation="This page has almost no readable text in its HTML, so AI answer engines and "
        "non-JS crawlers can't read or cite it." + js + " If it's a JavaScript app, server-render or "
        "prerender it (SSR / static generation / prerendering) so the headline, product description "
        "and key content are in the initial HTML. This is the root cause behind the missing-H1 and "
        "other empty-content findings.",
    )


def _js_render_check(delta: dict) -> Finding:
    raw = int(delta.get("raw_words", 0))
    rendered = int(delta.get("rendered_words", 0))
    render_only = max(0.0, (rendered - raw) / max(rendered, 1))
    pct = round(render_only * 100)
    value = {"raw_words": raw, "rendered_words": rendered, "render_only_pct": pct}

    # Call out the worst cases: H1 / structured data present only after JS.
    js_only = []
    if delta.get("schema_js_only"):
        js_only.append("structured data (JSON-LD)")
    if delta.get("h1_js_only"):
        js_only.append("the H1")
    verb = "appear" if len(js_only) > 1 else "appears"
    callout = f" Note: {' and '.join(js_only)} {verb} only after rendering." if js_only else ""
    evidence = (f"raw HTML: {raw} words; rendered DOM: {rendered} words "
                f"({pct}% only after JS).{callout}")

    if render_only > JS_RENDER_FAIL or (raw < JS_RAW_MIN_WORDS and render_only >= JS_RENDER_WARN):
        return Finding(
            "geo.js_rendered", P, "JavaScript-dependent content", Status.FAIL, Severity.HIGH, C,
            value=value, evidence=evidence,
            recommendation="Most of your content is rendered by JavaScript, so AI crawlers that "
            "don't execute JS won't see it. Serve the key content in the initial HTML — "
            "server-side render, static-generate, or prerender the page.",
        )
    if render_only >= JS_RENDER_WARN:
        return Finding(
            "geo.js_rendered", P, "JavaScript-dependent content", Status.WARN, Severity.MEDIUM, C,
            value=value, evidence=evidence,
            recommendation="A meaningful share of content only appears after JavaScript runs. AI "
            "crawlers that don't run JS may miss it — server-render or prerender the important "
            "parts so they're in the initial HTML.",
        )
    return Finding(
        "geo.js_rendered", P, "JavaScript-dependent content", Status.PASS, Severity.INFO, C,
        value=value,
        evidence=f"raw HTML: {raw} words; rendered DOM: {rendered} words ({pct}% only after JS).",
    )


# --------------------------------------------------------------------------- JSON-LD helpers


def _jsonld_objects(soup: BeautifulSoup) -> list[dict]:
    """All JSON-LD nodes on the page, flattening top-level lists and `@graph` containers."""
    out: list[dict] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text() or ""
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        stack = list(data) if isinstance(data, list) else [data]
        while stack:
            node = stack.pop()
            if isinstance(node, list):
                stack.extend(node)
            elif isinstance(node, dict):
                graph = node.get("@graph")
                if isinstance(graph, list):
                    stack.extend(graph)
                out.append(node)
    return out


def _types_of(node: dict) -> set[str]:
    t = node.get("@type")
    if isinstance(t, list):
        return {str(x).lower() for x in t}
    return {str(t).lower()} if t else set()


# ------------------------------------------------------------------------------- AEO + FAQ


# Elements that inherently hold their own text — direct answer-block candidates.
_TEXT_BLOCKS = {"p", "li", "blockquote", "dd"}
# Block-level tags; a <div>/<section> containing any of these is a layout wrapper, not a
# text leaf, so we don't treat it as a paragraph (its inner blocks are checked instead).
_BLOCK_TAGS = ["p", "div", "section", "article", "ul", "ol", "table", "header", "footer",
               "nav", "aside", "main", "figure", "form", "h1", "h2", "h3", "h4", "h5", "h6"]


def _is_answer_block(el: Tag) -> bool:
    """A self-contained text block: a <p>/<li>/blockquote/dd, or a <div>/<section> with no
    nested block elements (a "text div"). The latter covers React/Tailwind-style markup that
    wraps body copy in <div>/<span> instead of <p>."""
    if el.name in _TEXT_BLOCKS:
        return True
    if el.name in ("div", "section"):
        return el.find(_BLOCK_TAGS) is None
    return False


def _is_answer_paragraph(text: str) -> bool:
    return len(text.split()) >= MIN_ANSWER_WORDS and any(p in text for p in ".!?")


def _first_answer_offset(soup: BeautifulSoup) -> tuple[int | None, str]:
    """Visible-word offset of the first self-contained answer block, or (None, "") if none.

    Walks the body in document order, accumulating visible words; when it reaches a text
    block (<p>, list item, or a text-only <div>) that reads as a full answer, returns how
    many visible words preceded it.
    """
    body = soup.body or soup
    offset = 0
    for el in body.descendants:
        if isinstance(el, Tag):
            if _is_answer_block(el):
                text = el.get_text(" ", strip=True)
                if _is_answer_paragraph(text):
                    return offset, text
        elif isinstance(el, NavigableString):
            if any(isinstance(p, Tag) and p.name in _SKIP_TEXT for p in el.parents):
                continue
            offset += len(str(el).split())
    return None, ""


def _aeo(soup: BeautifulSoup) -> Finding:
    offset, snippet = _first_answer_offset(soup)
    snip = (snippet[:120] + "…") if len(snippet) > 120 else snippet

    # `snippet` is the passage an answer engine would most likely extract — expose it ("answer
    # preview") so the report/MCP can show "this is what AI will probably cite."
    if offset is None or offset >= AEO_WINDOW:
        return Finding(
            "geo.aeo", P, "Up-front answer block", Status.FAIL, Severity.HIGH, C,
            value={"answer_word_offset": offset, "snippet": None},
            evidence=f"No self-contained answer paragraph in the first {AEO_WINDOW} visible words.",
            recommendation="Lead with a direct, self-contained answer (a full sentence or two) "
            "high on the page — AI answer engines extract from the top.",
        )
    if offset > AEO_GOOD_MAX:
        return Finding(
            "geo.aeo", P, "Up-front answer block", Status.WARN, Severity.HIGH, C,
            value={"answer_word_offset": offset, "snippet": snip},
            evidence=f"first answer ~{offset} words in: “{snip}”",
            recommendation=f"The up-front answer starts ~{offset} words down; move it into the "
            "first ~150 words so it's the first thing engines read.",
        )
    return Finding(
        "geo.aeo", P, "Up-front answer block", Status.PASS, Severity.INFO, C,
        value={"answer_word_offset": offset, "snippet": snip},
        evidence=f"answer ~{offset} words in: “{snip}”",
    )


def _is_nav_list(lst: Tag) -> bool:
    """A list that's navigation, not a content summary: inside nav/header/footer, or whose
    items are mostly short link-only entries (a menu)."""
    for parent in lst.parents:
        if parent.name in ("nav", "header", "footer"):
            return True
        if (parent.get("role") or "").lower() == "navigation":
            return True
    items = lst.find_all("li")
    if not items:
        return False
    linkish = sum(1 for li in items
                  if li.find("a") is not None and len(li.get_text(" ", strip=True).split()) <= 4)
    return linkish / len(items) >= 0.7


def _summary_bullets(soup: BeautifulSoup) -> Finding:
    """Row 8 — is there a real (non-navigation) bullet/numbered list high on the page?

    Lists within the first AEO_WINDOW visible words are evaluated; a navigation menu near the
    top doesn't count as a content summary (mirrors the friend-prompt's nav gate).
    """
    body = soup.body or soup
    offset = 0
    lists: list[tuple[int, Tag]] = []
    for el in body.descendants:
        if isinstance(el, Tag):
            if el.name in ("ul", "ol") and offset < AEO_WINDOW and not any(
                isinstance(p, Tag) and p.name in ("ul", "ol") for p in el.parents
            ):
                lists.append((offset, el))
        elif isinstance(el, NavigableString):
            if any(isinstance(p, Tag) and p.name in _SKIP_TEXT for p in el.parents):
                continue
            offset += len(str(el).split())

    content = [(o, t) for o, t in lists if not _is_nav_list(t)]
    if content:
        o, t = content[0]
        items = len(t.find_all("li"))
        return Finding(
            "geo.summary_bullets", P, "Summary bullets near top", Status.PASS, Severity.INFO, C,
            value={"found": True, "navigation": False, "offset": o, "items": items},
            evidence=f"content list ~{o} words in ({items} items)",
        )
    if lists:
        return Finding(
            "geo.summary_bullets", P, "Summary bullets near top", Status.WARN, Severity.MEDIUM, C,
            value={"found": True, "navigation": True, "offset": lists[0][0]},
            evidence=f"the only list in the first {AEO_WINDOW} words (~{lists[0][0]} in) is navigation",
            recommendation="The list near the top is a navigation menu, not a content summary. Add a "
            "short bulleted summary of the answer high on the page — answer engines lift concise bullets.",
        )
    return Finding(
        "geo.summary_bullets", P, "Summary bullets near top", Status.WARN, Severity.MEDIUM, C,
        value={"found": False},
        evidence=f"no list in the first {AEO_WINDOW} visible words",
        recommendation="Add a short summary bullet list high on the page — AI Overviews and answer "
        "engines favour concise, scannable bullets near the top.",
    )


def _intro_quality(soup: BeautifulSoup, text: str) -> Finding:
    """Row 6 — does the intro answer, or sell? Flags a promotional/marketing-heavy opening."""
    intro = " ".join(text.split()[:80]).lower()
    hits = [m.strip() for m in PROMO_MARKERS if m in intro]
    exclaims = intro.count("!")
    promotional = len(hits) >= 2 or (len(hits) >= 1 and exclaims >= 1) or exclaims >= 2
    if promotional:
        ev = "promotional language in the intro: " + ", ".join(f'"{h}"' for h in hits[:4])
        if exclaims:
            ev += f"; {exclaims} exclamation mark(s)"
        return Finding(
            "geo.intro_quality", P, "Intro clarity", Status.WARN, Severity.MEDIUM, C,
            value={"promo_markers": hits, "exclamations": exclaims}, evidence=ev,
            recommendation="Open with a clear, factual answer to the page's question rather than "
            "marketing language — promotional intros get passed over by AI answer engines.",
        )
    return Finding(
        "geo.intro_quality", P, "Intro clarity", Status.PASS, Severity.INFO, C,
        value={"promo_markers": hits, "exclamations": exclaims},
        evidence="intro reads informative, not promotional",
    )


def _chunking(soup: BeautifulSoup) -> Finding:
    """Row 10 — is the body broken into discrete, extractable chunks (vs walls of text)?"""
    counts = [
        len(el.get_text(" ", strip=True).split())
        for el in (soup.body or soup).find_all(True)
        if _is_answer_block(el)
    ]
    counts = [c for c in counts if c >= 1]
    substantive = [c for c in counts if c >= CHUNK_MIN_WORDS]
    walls = [c for c in counts if c > CHUNK_WALL_WORDS]
    value = {"text_blocks": len(counts), "substantive": len(substantive), "walls": len(walls)}

    if not counts:
        return Finding(
            "geo.chunking", P, "Extractable chunks", Status.WARN, Severity.LOW, C, value=value,
            evidence="no paragraph-level text blocks found",
            recommendation="Structure body copy into discrete <p>/<li> blocks so AI can lift "
            "self-contained chunks.",
        )
    ok = len(substantive) >= 3 and len(walls) <= max(1, len(substantive) // 4)
    if ok:
        return Finding(
            "geo.chunking", P, "Extractable chunks", Status.PASS, Severity.INFO, C, value=value,
            evidence=f"{len(substantive)} substantive paragraph(s), {len(walls)} wall(s) of text",
        )
    return Finding(
        "geo.chunking", P, "Extractable chunks", Status.WARN, Severity.MEDIUM, C, value=value,
        evidence=f"{len(substantive)} substantive paragraph(s), {len(walls)} wall(s) (>{CHUNK_WALL_WORDS} words)",
        recommendation="Break content into discrete, self-contained paragraphs (~20–80 words each) "
        "with subheadings — AI engines extract clean chunks, not walls of text.",
    )


def _data_density(text: str) -> Finding:
    """Concrete-data density — figures, %, currency, years, measurements. AI answer engines
    cite pages with hard data far more than vague prose."""
    words = max(len(text.split()), 1)
    counts = {name: len(pat.findall(text)) for name, pat in _DATA_PATTERNS.items()}
    total = sum(counts.values())
    per100 = round(total / (words / 100), 2)
    value = {**counts, "data_points": total, "per_100_words": per100}

    if total >= DATA_RICH_POINTS or per100 >= DATA_RICH_PER_100:
        return Finding(
            "geo.data_density", P, "Quotable data", Status.PASS, Severity.INFO, C, value=value,
            evidence=f"{total} concrete data point(s) ({per100} per 100 words)",
        )
    if words >= DATA_SUBSTANTIAL_WORDS and total < 2:
        return Finding(
            "geo.data_density", P, "Quotable data", Status.WARN, Severity.MEDIUM, C, value=value,
            evidence=f"only {total} concrete figure(s) across ~{words} words",
            recommendation="The page makes claims with almost no concrete figures. Add statistics, "
            "numbers, dates and measurements — AI engines disproportionately cite pages with hard, "
            "verifiable data.",
        )
    return Finding(
        "geo.data_density", P, "Quotable data", Status.INFO, Severity.INFO, C, value=value,
        evidence=f"{total} concrete data point(s) ({per100} per 100 words)",
        recommendation="More concrete figures (stats, numbers, dates) would make the page more "
        "citable — AI engines favour data-rich content.",
    )


def _faq(soup: BeautifulSoup) -> Finding:
    objs = _jsonld_objects(soup)
    has_schema = any("faqpage" in _types_of(o) for o in objs)

    pairs, examples = 0, []
    for h in soup.find_all(["h2", "h3", "h4"]):
        q = h.get_text(strip=True)
        if "?" not in q:
            continue
        nxt, steps = h.find_next_sibling(), 0
        while nxt is not None and steps < 3:
            if getattr(nxt, "name", None) in ("h1", "h2", "h3", "h4"):
                break
            if len(nxt.get_text(" ", strip=True).split()) >= 8:  # an actual answer follows
                pairs += 1
                if len(examples) < 3:
                    examples.append(q)
                break
            nxt, steps = nxt.find_next_sibling(), steps + 1

    ok = has_schema or pairs >= 2
    detail = ", ".join(filter(None, [
        "FAQPage schema" if has_schema else None,
        f"{pairs} Q&A pair(s)" if pairs else None,
    ])) or "no FAQ structure found"
    # Informational (not a penalty) when absent — not every page should be an FAQ.
    return Finding(
        "geo.faq", P, "FAQ section", Status.PASS if ok else Status.INFO, Severity.LOW, C,
        value={"faqpage_schema": has_schema, "qa_pairs": pairs}, evidence=detail,
        recommendation=None if ok else
        "Optional: an FAQ (question-form H2/H3s each answered directly, ideally with FAQPage "
        "JSON-LD) gives AI engines Q&A pairs they lift almost verbatim.",
    )


# ----------------------------------------------------------------------------- trust/E-E-A-T


def _author_by_class(soup: BeautifulSoup) -> bool:
    """A class-name author signal — but only when it wraps a short, name-like text (a real byline),
    not a decorative 'author-avatar'/'author-photo' wrapper. Cuts class-sniffing false positives."""
    def cls_match(c) -> bool:
        if not c:
            return False
        joined = " ".join(c).lower() if isinstance(c, list) else str(c).lower()
        return "author" in joined or "byline" in joined

    for el in soup.find_all(class_=cls_match):
        if el.name in ("img", "svg", "picture"):
            continue
        txt = el.get_text(" ", strip=True)
        if 1 <= len(txt.split()) <= 6 and any(ch.isalpha() for ch in txt):
            return True
    return False


def _trust(soup: BeautifulSoup) -> Finding:
    objs = _jsonld_objects(soup)

    # Strong, explicit author signals (markup/metadata) first, then the stricter class fallback.
    author = bool(
        soup.find("meta", attrs={"name": "author"})
        or soup.find(attrs={"rel": "author"})
        or soup.find(attrs={"itemprop": "author"})
        or any(o.get("author") for o in objs)
    ) or _author_by_class(soup)

    # A real published/updated date — a <time datetime>, a date meta/itemprop, or JSON-LD date.
    # A bare <time> with no datetime attribute no longer counts (too easy a false positive).
    date = bool(
        soup.find("time", attrs={"datetime": True})
        or soup.find("meta", attrs={"property": "article:published_time"})
        or soup.find("meta", attrs={"property": "article:modified_time"})
        or soup.find(attrs={"itemprop": lambda v: v in ("datePublished", "dateModified")})
        or any(o.get("datePublished") or o.get("dateModified") for o in objs)
    )
    anchors = soup.find_all("a")
    hrefs = " ".join((a.get("href") or "").lower() for a in anchors)
    labels = " ".join(a.get_text(" ", strip=True).lower() for a in anchors)
    about_contact = (("/about" in hrefs or "about" in labels)
                     and ("/contact" in hrefs or "contact" in labels))
    entity_sameas = any(
        (_types_of(o) & {"organization", "person"}) and o.get("sameAs")
        for o in objs
    )

    signals = {
        "author byline": author,
        "published/updated date": date,
        "about & contact links": about_contact,
        "entity schema with sameAs": entity_sameas,
    }
    present = [k for k, v in signals.items() if v]
    missing = [k for k, v in signals.items() if not v]
    ok = len(present) >= 3
    return Finding(
        "geo.trust", P, "Trust & E-E-A-T signals", Status.PASS if ok else Status.WARN,
        Severity.MEDIUM, C, value={"present": present, "count": len(present)},
        evidence=("present: " + ", ".join(present) if present else "none found")
        + ("; missing: " + ", ".join(missing) if missing else ""),
        recommendation=None if ok else
        "Add author/E-E-A-T signals: a visible author byline, a published/updated date (a <time "
        "datetime> or Article JSON-LD with datePublished), About + Contact links, and "
        "Organization/Person JSON-LD with sameAs — strong citation-trust factors.",
    )


# ------------------------------------------------------------------------- freshness + entity


def _collect_dates(soup: BeautifulSoup) -> list[str]:
    out: list[str] = []
    for node in _jsonld_objects(soup):
        for k in ("dateModified", "datePublished"):
            v = node.get(k)
            if isinstance(v, str):
                out.append(v)
    for prop in ("article:modified_time", "article:published_time"):
        m = soup.find("meta", attrs={"property": prop})
        if m and m.get("content"):
            out.append(m["content"])
    for t in soup.find_all("time"):
        if t.get("datetime"):
            out.append(t["datetime"])
    return out


def _parse_date(s: str) -> datetime | None:
    m = re.match(r"\s*(\d{4})-(\d{2})-(\d{2})", s)
    if not m:
        return None
    try:
        return datetime(int(m[1]), int(m[2]), int(m[3]), tzinfo=timezone.utc)
    except ValueError:
        return None


def _freshness(soup: BeautifulSoup, now: datetime) -> Finding:
    """Is the content dated and recent? AI engines favour fresh, maintained pages."""
    dates = [d for d in (_parse_date(x) for x in _collect_dates(soup)) if d]
    if not dates:
        return Finding(
            "geo.freshness", P, "Content freshness", Status.INFO, Severity.LOW, C,
            value={"latest": None}, evidence="no published/updated date found",
            recommendation="Add a visible published/updated date and datePublished/dateModified to "
            "your schema — AI engines and search favour fresh, dated content.",
        )
    latest = max(dates)
    age = (now - latest).days
    value = {"latest": latest.date().isoformat(), "age_days": age}
    if age <= FRESH_STALE_DAYS:
        return Finding(
            "geo.freshness", P, "Content freshness", Status.PASS, Severity.INFO, C, value=value,
            evidence=f"last dated {latest.date().isoformat()} ({age} days ago)",
        )
    return Finding(
        "geo.freshness", P, "Content freshness", Status.WARN, Severity.MEDIUM, C, value=value,
        evidence=f"last dated {latest.date().isoformat()} ({age} days ago)",
        recommendation="The latest date is over 18 months old. Refresh and re-date the content — "
        "AI engines and search demote stale pages.",
    )


def _entity(soup: BeautifulSoup) -> Finding:
    """Entity grounding — Organization/Person schema with sameAs to knowledge bases (Wikipedia /
    Wikidata) or several authoritative profiles, so LLMs can disambiguate the brand."""
    nodes = [n for n in _jsonld_objects(soup) if _types_of(n) & {"organization", "person"}]
    if not nodes:
        return Finding(
            "geo.entity", P, "Entity grounding", Status.INFO, Severity.LOW, C,
            value={"entity": False},
            evidence="no Organization or Person schema",
            recommendation="Add Organization (or Person) JSON-LD with sameAs links to Wikipedia, "
            "Wikidata, LinkedIn and your social profiles — it grounds your brand as an entity AI "
            "models recognise.",
        )
    sameas: list[str] = []
    for n in nodes:
        sa = n.get("sameAs")
        sameas += [sa] if isinstance(sa, str) else (sa if isinstance(sa, list) else [])
    sameas = [s.lower() for s in sameas if isinstance(s, str)]
    knowledge = any(any(k in s for k in _KNOWLEDGE_BASES) for s in sameas)
    auth = sum(1 for s in sameas if any(a in s for a in _AUTH_PROFILES))
    if knowledge or auth >= 2:
        return Finding(
            "geo.entity", P, "Entity grounding", Status.PASS, Severity.INFO, C,
            value={"entity": True, "knowledge_base": knowledge, "sameas": len(sameas)},
            evidence=("linked to a knowledge base (Wikipedia/Wikidata)" if knowledge
                      else f"{auth} authoritative sameAs links"),
        )
    return Finding(
        "geo.entity", P, "Entity grounding", Status.INFO, Severity.LOW, C,
        value={"entity": True, "knowledge_base": False, "sameas": len(sameas)},
        evidence="entity schema present but weak sameAs",
        recommendation="Strengthen entity grounding: add sameAs to Wikipedia/Wikidata (and "
        "LinkedIn/Crunchbase) on your Organization/Person schema so AI models can disambiguate you.",
    )
