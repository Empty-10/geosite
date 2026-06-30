"""Expert Answerability Review - deterministic, VERIFIED.

Adds the deeper answerability validations that the existing geo.* checks don't cover, answering one
question: could ChatGPT / Claude / Gemini confidently quote this page? Pure: parsed DOM + visible
text in, list[Finding] out. No network, no LLM, no semantic inference - every rule is reproducible
from the HTML. The synthesis (verdict / confidence / consultant summary / Likely AI Quote) lives in
answerability.py; this module only emits the five new findings.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from ..content import first_answer_offset, question_heading_coverage
from ..models import Confidence, Finding, Pillar, Severity, Status

P = Pillar.GEO
C = Confidence.VERIFIED

# Openers that reference unestablished context - an answer starting with one can't stand alone.
_AMBIGUOUS_OPENERS = {
    "it", "this", "that", "these", "those", "they", "them", "he", "she", "there", "here",
    "also", "and", "but", "however", "therefore", "thus", "so", "plus", "additionally",
    "moreover", "furthermore", "hence", "consequently",
}

# Heading sectioning: a page this long should be broken into sections.
HEADING_COVERAGE_MIN_WORDS = 400
WORDS_PER_SECTION_MAX = 400

# A definitional sentence near the top - the passage engines quote for "what is X" prompts.
_DEFINITION_RE = re.compile(
    r"\b[A-Za-z][\w'’-]*(?:\s+[\w'’-]+){0,5}\s+(?:is|are)\s+(?:a|an|the)\s+\w"
    r"|\b(?:refers to|is defined as|is known as|means|stands for)\b",
    re.I,
)
DEFINITION_WINDOW_WORDS = 120


def analyze(soup: BeautifulSoup, text: str) -> list[Finding]:
    out: list[Finding] = []
    words = text.split()
    if len(words) < 10:
        return out  # geo.no_content owns the empty-page case

    out += _answer_self_contained(soup)
    out += _heading_coverage(soup, len(words))
    out += _table_extractability(soup)
    out += _question_coverage(soup)
    out += _definition_present(words)
    return out


def _first_word(s: str) -> str:
    for tok in s.split():
        w = tok.strip("\"'“”‘’([{.,;:!?").lower()
        if w:
            return w
    return ""


def _answer_self_contained(soup: BeautifulSoup) -> list[Finding]:
    offset, snippet = first_answer_offset(soup)
    if offset is None or not snippet:
        return []  # no up-front answer at all -> geo.aeo handles it
    opener = _first_word(snippet)
    snip = (snippet[:120] + "…") if len(snippet) > 120 else snippet
    if opener in _AMBIGUOUS_OPENERS:
        return [Finding(
            "geo.answer_self_contained", P, "Self-contained answer", Status.WARN, Severity.MEDIUM, C,
            value={"opener": opener},
            evidence=f"the up-front answer opens with “{opener}”: “{snip}”",
            recommendation="Rewrite the first answer sentence so it names its subject instead of "
            f"opening with “{opener}”. An AI engine quotes the sentence in isolation - it can't "
            "resolve a pronoun or connector that refers to earlier context.",
        )]
    return [Finding(
        "geo.answer_self_contained", P, "Self-contained answer", Status.PASS, Severity.INFO, C,
        value={"opener": opener}, evidence=f"answer stands alone: “{snip}”",
    )]


def _heading_coverage(soup: BeautifulSoup, total_words: int) -> list[Finding]:
    if total_words < HEADING_COVERAGE_MIN_WORDS:
        return []  # short pages don't need sectioning
    sections = len(soup.find_all(["h2", "h3"]))
    value = {"words": total_words, "sections": sections}
    under = sections == 0 or total_words / sections > WORDS_PER_SECTION_MAX
    if under:
        need = max(2, round(total_words / WORDS_PER_SECTION_MAX))
        return [Finding(
            "geo.heading_coverage", P, "Section coverage", Status.WARN, Severity.MEDIUM, C, value=value,
            evidence=f"{total_words} words across {sections} H2/H3 section(s)",
            recommendation=f"Long content with too few sections. Add descriptive H2/H3 sub-headings "
            f"(aim for ~{need}) so engines can segment the page and quote individual parts.",
        )]
    return [Finding(
        "geo.heading_coverage", P, "Section coverage", Status.PASS, Severity.INFO, C, value=value,
        evidence=f"{total_words} words across {sections} H2/H3 section(s)",
    )]


def _table_extractability(soup: BeautifulSoup) -> list[Finding]:
    tables = soup.find_all("table")
    if not tables:
        return []
    headerless = [t for t in tables if t.find("th") is None and t.find("thead") is None]
    value = {"tables": len(tables), "headerless": len(headerless)}
    if headerless:
        return [Finding(
            "geo.table_extractability", P, "Table extractability", Status.WARN, Severity.LOW, C,
            value=value, evidence=f"{len(headerless)} of {len(tables)} table(s) have no header row",
            recommendation="Give data tables a header row (<th> or <thead>) so AI engines can read "
            "them as structured data rather than loose cells.",
        )]
    return [Finding(
        "geo.table_extractability", P, "Table extractability", Status.PASS, Severity.INFO, C,
        value=value, evidence=f"{len(tables)} table(s) have header rows",
    )]


def _question_coverage(soup: BeautifulSoup) -> list[Finding]:
    answered, unanswered = question_heading_coverage(soup)
    if not (answered or unanswered):
        return []  # no question headings -> geo.qa_headings / geo.faq own that
    value = {"answered": len(answered), "unanswered": len(unanswered)}
    if unanswered:
        return [Finding(
            "geo.question_coverage", P, "Question coverage", Status.WARN, Severity.MEDIUM, C,
            value=value,
            evidence=f"{len(unanswered)} question heading(s) with no answer beneath: "
            + "; ".join(unanswered[:3]),
            recommendation="Follow every question-style heading directly with a concise answer "
            "(a full sentence or two). A question with no answer is a dead end for AI answer engines.",
        )]
    return [Finding(
        "geo.question_coverage", P, "Question coverage", Status.PASS, Severity.INFO, C, value=value,
        evidence=f"all {len(answered)} question heading(s) are answered",
    )]


def _definition_present(words: list[str]) -> list[Finding]:
    intro = " ".join(words[:DEFINITION_WINDOW_WORDS])
    present = bool(_DEFINITION_RE.search(intro))
    if present:
        return [Finding(
            "geo.definition_present", P, "Quotable definition", Status.PASS, Severity.INFO, C,
            value={"present": True}, evidence="a definitional sentence appears near the top",
        )]
    return [Finding(
        "geo.definition_present", P, "Quotable definition", Status.INFO, Severity.INFO, C,
        value={"present": False}, evidence="no clear definition near the top",
        recommendation="For a 'what is…' query there's no one-line definition near the top. A clear "
        "“X is a …” sentence makes an ideal, self-contained quote for AI engines.",
    )]
