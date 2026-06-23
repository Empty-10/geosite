"""GEO-readiness module — the on-page factors that correlate with being cited by AI.

IMPORTANT: this is deterministic and VERIFIED. It is NOT citation sampling (that is a
separate, MEASURED module added in Phase 3). Here we only judge whether the page is built
to be cited: front-loaded answers, confident language, extractable structure, schema.
Signals are grounded in 2026 GEO research (see docs / chat history).
"""

from __future__ import annotations

import json

from bs4 import BeautifulSoup, NavigableString, Tag

from ..models import Confidence, Finding, Pillar, Severity, Status

P = Pillar.GEO
C = Confidence.VERIFIED

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


def analyze(soup: BeautifulSoup, text: str) -> list[Finding]:
    out: list[Finding] = []
    words = text.split()
    total = len(words)

    # --- front-loading: do the first ~150 words carry a real answer? ---
    first = words[:150]
    out.append(Finding(
        "geo.frontload", P, "Front-loaded answer",
        Status.PASS if len(first) >= 40 else Status.WARN, Severity.HIGH, C,
        value=len(first),
        evidence=" ".join(first[:30]) + ("…" if len(first) > 30 else ""),
        recommendation=None if len(first) >= 40 else
        "Open with a direct, complete answer in the first ~150 words — AI extracts from "
        "the top of the page.",
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

    # --- extractable structure: lists & tables ---
    lists = len(soup.find_all(["ul", "ol"]))
    tables = len(soup.find_all("table"))
    has_structure = (lists + tables) > 0
    out.append(Finding(
        "geo.structure", P, "Extractable structure (lists/tables)",
        Status.PASS if has_structure else Status.WARN, Severity.MEDIUM, C,
        value={"lists": lists, "tables": tables},
        recommendation=None if has_structure else
        "Add lists/tables and short paragraphs — AI engines lift discrete chunks, and "
        "AI Overviews favour list formatting.",
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
    out.append(_faq(soup))
    out.append(_trust(soup))

    return out


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

    if offset is None or offset >= AEO_WINDOW:
        return Finding(
            "geo.aeo", P, "Up-front answer block", Status.FAIL, Severity.HIGH, C,
            value={"answer_word_offset": offset},
            evidence=f"No self-contained answer paragraph in the first {AEO_WINDOW} visible words.",
            recommendation="Lead with a direct, self-contained answer (a full sentence or two) "
            "high on the page — AI answer engines extract from the top.",
        )
    if offset > AEO_GOOD_MAX:
        return Finding(
            "geo.aeo", P, "Up-front answer block", Status.WARN, Severity.HIGH, C,
            value={"answer_word_offset": offset},
            evidence=f"first answer ~{offset} words in: “{snip}”",
            recommendation=f"The up-front answer starts ~{offset} words down; move it into the "
            "first ~150 words so it's the first thing engines read.",
        )
    return Finding(
        "geo.aeo", P, "Up-front answer block", Status.PASS, Severity.INFO, C,
        value={"answer_word_offset": offset}, evidence=f"answer ~{offset} words in: “{snip}”",
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


def _trust(soup: BeautifulSoup) -> Finding:
    def has_class(substr: str) -> bool:
        return bool(soup.find(class_=lambda c: c and substr in " ".join(c).lower()
                              if isinstance(c, list) else c and substr in c.lower()))

    author = bool(
        soup.find("meta", attrs={"name": "author"})
        or soup.find(attrs={"rel": "author"})
        or soup.find(attrs={"itemprop": "author"})
        or has_class("author") or has_class("byline")
    )
    date = bool(
        soup.find("time")
        or soup.find("meta", attrs={"property": "article:published_time"})
        or soup.find("meta", attrs={"property": "article:modified_time"})
        or soup.find(attrs={"itemprop": lambda v: v in ("datePublished", "dateModified")})
    )
    anchors = soup.find_all("a")
    hrefs = " ".join((a.get("href") or "").lower() for a in anchors)
    labels = " ".join(a.get_text(" ", strip=True).lower() for a in anchors)
    about_contact = (("/about" in hrefs or "about" in labels)
                     and ("/contact" in hrefs or "contact" in labels))
    entity_sameas = any(
        (_types_of(o) & {"organization", "person"}) and o.get("sameAs")
        for o in _jsonld_objects(soup)
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
        "Add author/E-E-A-T signals: a visible author byline, a published/updated date, "
        "About + Contact links, and Organization/Person JSON-LD with sameAs — strong "
        "citation-trust factors.",
    )
