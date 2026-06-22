"""GEO-readiness module — the on-page factors that correlate with being cited by AI.

IMPORTANT: this is deterministic and VERIFIED. It is NOT citation sampling (that is a
separate, MEASURED module added in Phase 3). Here we only judge whether the page is built
to be cited: front-loaded answers, confident language, extractable structure, schema.
Signals are grounded in 2026 GEO research (see docs / chat history).
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from ..models import Confidence, Finding, Pillar, Severity, Status

P = Pillar.GEO
C = Confidence.VERIFIED

# Hedging language gets passed over by AI; definitive language is ~2x more likely cited.
HEDGE_WORDS = {
    "might", "maybe", "perhaps", "possibly", "could", "sometimes", "generally",
    "usually", "often", "arguably", "seemingly", "presumably", "likely", "probably",
    "somewhat", "relatively", "fairly", "tends", "tend",
}


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

    return out
