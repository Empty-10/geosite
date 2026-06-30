"""Shared deterministic content-extraction helpers for the GEO / Answerability checks.

The answer-block walk here is the SAME logic geo.aeo uses to find the up-front answer (and the
"Likely AI Quote"); it lives here so the Answerability Review reuses it without reaching into the
geo module. Pure: BeautifulSoup in, plain values out. No network, no LLM.
"""

from __future__ import annotations

from bs4 import BeautifulSoup, NavigableString, Tag

MIN_ANSWER_WORDS = 12  # a "self-contained answer" paragraph is at least this long

# Elements that inherently hold their own text - direct answer-block candidates.
_TEXT_BLOCKS = {"p", "li", "blockquote", "dd"}
# Block-level tags; a <div>/<section> containing any of these is a layout wrapper, not a text leaf.
_BLOCK_TAGS = ["p", "div", "section", "article", "ul", "ol", "table", "header", "footer",
               "nav", "aside", "main", "figure", "form", "h1", "h2", "h3", "h4", "h5", "h6"]
_SKIP_TEXT = {"script", "style", "noscript", "template"}


def is_answer_block(el: Tag) -> bool:
    """A self-contained text block: a <p>/<li>/blockquote/dd, or a <div>/<section> with no nested
    block elements (a 'text div', covering React/Tailwind markup that wraps copy in <div>)."""
    if el.name in _TEXT_BLOCKS:
        return True
    if el.name in ("div", "section"):
        return el.find(_BLOCK_TAGS) is None
    return False


def is_answer_paragraph(text: str) -> bool:
    return len(text.split()) >= MIN_ANSWER_WORDS and any(p in text for p in ".!?")


def first_answer_offset(soup: BeautifulSoup) -> tuple[int | None, str]:
    """Visible-word offset of the first self-contained answer block (and its text), or (None, '').

    Walks the body in document order, accumulating visible words; returns how many preceded the
    first text block that reads as a full answer. This is the passage an answer engine most likely
    extracts - the 'Likely AI Quote'.
    """
    body = soup.body or soup
    offset = 0
    for el in body.descendants:
        if isinstance(el, Tag):
            if is_answer_block(el):
                text = el.get_text(" ", strip=True)
                if is_answer_paragraph(text):
                    return offset, text
        elif isinstance(el, NavigableString):
            if any(isinstance(p, Tag) and p.name in _SKIP_TEXT for p in el.parents):
                continue
            offset += len(str(el).split())
    return None, ""


def question_heading_coverage(soup: BeautifulSoup) -> tuple[list[str], list[str]]:
    """Split question-style headings (h2/h3/h4 containing '?') into (answered, unanswered).

    A heading is 'answered' when an actual answer (>=8 words) follows within the next 1-3 siblings
    before the next heading - the same rule geo.faq uses to count Q&A pairs.
    """
    answered: list[str] = []
    unanswered: list[str] = []
    for h in soup.find_all(["h2", "h3", "h4"]):
        q = h.get_text(strip=True)
        if "?" not in q:
            continue
        nxt, steps, found = h.find_next_sibling(), 0, False
        while nxt is not None and steps < 3:
            if getattr(nxt, "name", None) in ("h1", "h2", "h3", "h4"):
                break
            if len(nxt.get_text(" ", strip=True).split()) >= 8:
                found = True
                break
            nxt, steps = nxt.find_next_sibling(), steps + 1
        (answered if found else unanswered).append(q)
    return answered, unanswered
