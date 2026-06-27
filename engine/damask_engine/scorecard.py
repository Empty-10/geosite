"""Scorecard — aggregate the deterministic findings into a legible 20-row audit with a single
headline "AI Retrievability" score.

This is the presentation keystone (and the MCP / WordPress payload): it buckets the engine's
~45 findings into the 20 rows of an enterprise GEO/AEO/SEO audit, scores each row from the real
signal statuses, applies the three critical gates, and adds the +8 hybrid overlay. It is pure
and deterministic — derived entirely from the Report's findings, identical for identical input.

Unlike an LLM doing the same job from pasted HTML, every number here is reproducible.
"""

from __future__ import annotations

from .models import Report, Status

# status → row-credit points (PASS best, FAIL zero; INFO is "present/optional", lightly docked).
_POINTS = {Status.PASS: 100, Status.INFO: 80, Status.WARN: 55, Status.FAIL: 0}

# Each row collects whichever of its candidate finding ids are present (one finding → one row).
ROWS: list[tuple[int, str, list[str]]] = [
    (1, "Page Identity & Intent Clarity", ["h1.missing", "h1.multiple", "h1.ok",
                                           "robots.indexable", "robots.noindex", "tech.x_robots_tag",
                                           "opengraph"]),
    (2, "Title Tag Quality", ["title.length", "title.missing"]),
    (3, "Meta Description Quality", ["meta.description.length", "meta.description.missing"]),
    (4, "URL Structure & Canonical Consistency", ["onpage.url", "canonical"]),
    (5, "Heading Architecture", ["headings.structure", "onpage.heading_order"]),
    (6, "Intro Block Quality", ["geo.frontload", "geo.intro_quality", "geo.no_content"]),
    (7, "Featured Answer Blocks (AEO Core)", ["geo.aeo", "geo.definitive", "geo.no_content"]),
    (8, "Summary Bullets Near Top", ["geo.summary_bullets", "geo.no_content"]),
    (9, "FAQ Section Quality", ["geo.faq", "geo.qa_headings", "geo.no_content"]),
    (10, "Chunking & Extractable Paragraphs", ["geo.chunking", "geo.depth", "geo.thin_content",
                                               "geo.data_density", "geo.no_content"]),
    (11, "Lists & Tables for Extractability", ["geo.structure", "geo.no_content"]),
    (12, "Internal Linking & Anchor Text", ["onpage.links", "onpage.jump_links", "onpage.crawlable_anchors"]),
    (13, "Link Attributes & Semantic Hints", ["onpage.link_attrs"]),
    (14, "External Links to Authoritative Sources", ["onpage.outbound"]),
    (15, "Images & Media", ["images.alt", "onpage.images.dims"]),
    (16, "Accessibility Basics", ["onpage.lang", "onpage.form_labels"]),
    (17, "Performance & Delivery", ["tech.resource_hints", "tech.compression", "perf.score",
                                    "perf.lcp", "perf.cls", "perf.tbt", "perf.fcp", "perf.si",
                                    "perf.field"]),
    (18, "Authority, Trust & E-E-A-T", ["geo.trust", "geo.no_content"]),
    (19, "Indexability & Technical SEO Sanity", ["tech.https", "tech.status", "tech.redirect",
                                                 "tech.redirect.chain", "tech.hsts", "tech.tls",
                                                 "tech.mixed_content", "tech.mixed_content.ok",
                                                 "tech.viewport", "tech.robots.ok",
                                                 "tech.robots.missing", "tech.robots.ai",
                                                 "tech.robots.sitemap", "tech.sitemap",
                                                 "tech.sitemap.missing", "tech.sitemap.invalid",
                                                 "tech.sitemap.freshness", "tech.security_headers",
                                                 "tech.index_conflict", "onpage.snippet_directives",
                                                 "onpage.hreflang", "geo.js_rendered", "tech.llms_txt"]),
    (20, "Structured Data & Schema", ["schema.jsonld", "schema.missing", "schema.validation"]),
]

CATEGORIES: list[tuple[str, list[int]]] = [
    ("Identity & metadata", [1, 2, 3, 4]),
    ("Content & answers", [5, 6, 7, 8, 9, 10, 11]),
    ("Links", [12, 13, 14]),
    ("Media & accessibility", [15, 16]),
    ("Technical & trust", [17, 18, 19, 20]),
]


def _round_half(x: float) -> float:
    return round(x * 2) / 2


def _row_status(score: float) -> str:
    return "pass" if score >= 80 else "warn" if score >= 50 else "fail"


def build_scorecard(report: Report) -> dict:
    """Derive the 20-row scorecard + headline AI Retrievability score from a page Report."""
    byid = {f.id: f for f in report.findings}

    rows = []
    for num, label, ids in ROWS:
        members = [byid[i] for i in ids if i in byid]
        if not members:
            rows.append({"n": num, "label": label, "score": None, "status": "n/a", "findings": []})
            continue
        score = sum(_POINTS[f.status] for f in members) / len(members)
        score = _apply_gate(num, score, byid)
        rows.append({
            "n": num, "label": label, "score": _round_half(score), "status": _row_status(score),
            "findings": [f.id for f in members],
        })

    overlay = _overlay(byid)
    scored = [r["score"] for r in rows if r["score"] is not None]
    n = len(scored)
    technical = sum(scored) / n if n else 0.0
    headline = min(100.0, technical + overlay["total"])

    # Per-row "impact": how many headline points this row would add if brought to full marks
    # (capped at the 0–100 ceiling). Lets the report rank fixes by ROI, not just severity.
    for r in rows:
        s = r["score"]
        if s is not None and s < 100 and n:
            gained = min(100.0, technical + (100.0 - s) / n + overlay["total"]) - headline
            r["impact"] = _round_half(max(0.0, gained))
        else:
            r["impact"] = 0.0

    categories = []
    for clabel, nums in CATEGORIES:
        cs = [r["score"] for r in rows if r["n"] in nums and r["score"] is not None]
        categories.append({"label": clabel, "score": _round_half(sum(cs) / len(cs)) if cs else None})

    return {
        "confidence": "verified",
        "headline_score": _round_half(headline),
        "technical_score": _round_half(technical),
        "overlay": overlay,
        "rows": rows,
        "categories": categories,
        "summary": _summary(headline, rows),
        "citation": _citation_readiness(rows),
    }


# Brand-readable phrasing for the verdict, keyed by row number — plain English, not jargon.
_ISSUE_PHRASES: dict[int, str] = {
    1: "clarifying the page's identity and intent",
    2: "improving the title tag",
    3: "improving the meta description",
    4: "fixing the URL and canonical setup",
    5: "fixing the heading structure",
    6: "front-loading a clear answer in the intro",
    7: "adding a direct answer block near the top",
    8: "adding a summary list near the top",
    9: "adding a proper FAQ section",
    10: "breaking content into short, extractable chunks",
    11: "adding lists or tables AI can extract",
    12: "improving internal links and anchor text",
    13: "adding semantic link attributes",
    14: "linking out to authoritative sources",
    15: "fixing image alt text and dimensions",
    16: "fixing accessibility basics",
    17: "improving page performance",
    18: "strengthening authority and trust signals (E-E-A-T)",
    19: "fixing technical and indexability issues",
    20: "adding structured data (schema)",
}


# Rows whose signals most directly govern whether an AI engine extracts and cites the page —
# the bridge from deterministic readiness (VERIFIED) to actual citation (MEASURED, separate tool).
_CITATION_ROWS: dict[int, str] = {
    6: "a clear answer front-loaded in the intro",
    7: "a direct answer block near the top",
    8: "a summary list near the top",
    9: "an FAQ section",
    10: "content broken into short, extractable chunks",
    11: "lists or tables AI can extract",
    20: "structured data (schema)",
}


def _citation_readiness(rows: list[dict]) -> dict:
    """A deterministic read on how *citable* the page is — derived only from the on-page signals
    answer engines actually use to pick sources. Honest: this is readiness, not a measured rate."""
    byn = {r["n"]: r for r in rows}
    present = [byn[n] for n in _CITATION_ROWS if n in byn and byn[n]["score"] is not None]
    if not present:
        return {"band": "unknown", "score": None, "reasons": []}
    score = _round_half(sum(r["score"] for r in present) / len(present))
    band = ("well positioned" if score >= 80 else
            "partially positioned" if score >= 50 else "poorly positioned")
    gaps = sorted((r for r in present if r["status"] in ("warn", "fail")), key=lambda r: r["score"])
    reasons = [{"n": r["n"], "text": _CITATION_ROWS[r["n"]]} for r in gaps[:4]]
    return {"band": band, "score": score, "reasons": reasons}


def _summary(headline: float, rows: list[dict]) -> dict:
    """A deterministic, plain-English verdict + the top opportunities, ranked by headline impact.

    Pure presentation derived from the rows — the same brand-facing summary the web report, MCP
    tool and WordPress plugin all render, so they never tell different stories.
    """
    if headline >= 85:
        band, lead = "strong", "This page is well-structured for AI answer engines."
    elif headline >= 70:
        band, lead = "solid", "This page is mostly ready for AI answer engines, with a few gaps holding it back."
    elif headline >= 50:
        band, lead = "needs work", "This page has real gaps that make it hard for AI engines to retrieve and cite."
    else:
        band, lead = "at risk", "AI answer engines will struggle to retrieve or cite this page as it stands."

    opps = sorted(
        (r for r in rows if r["status"] in ("warn", "fail") and r.get("impact", 0) > 0),
        key=lambda r: r["impact"], reverse=True,
    )[:3]
    opportunities = [
        {"n": r["n"], "text": _ISSUE_PHRASES.get(r["n"], r["label"]), "impact": r["impact"]}
        for r in opps
    ]

    if opportunities:
        names = [o["text"] for o in opportunities]
        tail = names[0] if len(names) == 1 else (
            f"{names[0]} and {names[1]}" if len(names) == 2
            else f"{names[0]}, {names[1]}, and {names[2]}")
        verdict = f"{lead} The biggest opportunities are {tail}."
    else:
        verdict = f"{lead} No major issues — only minor refinements remain."

    return {"band": band, "verdict": verdict, "opportunities": opportunities}


def _apply_gate(num: int, score: float, byid: dict) -> float:
    """The three mandatory critical gates from the audit spec."""
    if num == 6:  # promotional/unclear intro → cap at 40
        intro = byid.get("geo.intro_quality")
        if intro is not None and intro.status == Status.WARN:
            return min(score, 40.0)
    elif num == 7:  # no direct answer, or answer below the 220-word line → 0
        aeo = byid.get("geo.aeo")
        if aeo is not None and aeo.status != Status.PASS:
            return 0.0
    elif num == 8:  # no valid list → 0; a navigation menu → cap at 40
        sb = byid.get("geo.summary_bullets")
        if sb is not None:
            val = sb.value if isinstance(sb.value, dict) else {}
            if not val.get("found"):
                return 0.0
            if val.get("navigation"):
                return min(score, 40.0)
    return score


def _overlay(byid: dict) -> dict:
    """The +8.0 hybrid overlay — five all-or-nothing bonus factors (no partial credit)."""
    def val(fid: str) -> dict:
        f = byid.get(fid)
        return f.value if f is not None and isinstance(f.value, dict) else {}

    factors = []

    # 1. Anchors: ≥3 valid anchors AND ≥2 jump links → +2.0
    links, jumps = val("onpage.links"), val("onpage.jump_links")
    anchors_ok = byid.get("onpage.links") is not None and byid["onpage.links"].status == Status.PASS \
        and (links.get("internal", 0) + links.get("external", 0)) >= 3
    a1 = 2.0 if (anchors_ok and jumps.get("jump_links", 0) >= 2) else 0.0
    factors.append({"name": "Anchors & jump links", "points": a1, "max": 2.0})

    # 2. FAQ / Process: both → +1.5, one → +1.0
    faq = byid.get("geo.faq")
    has_faq = faq is not None and faq.status == Status.PASS
    schema_types = _schema_types(byid)
    has_process = "howto" in schema_types
    a2 = 1.5 if (has_faq and has_process) else 1.0 if (has_faq or has_process) else 0.0
    factors.append({"name": "FAQ / process", "points": a2, "max": 1.5})

    # 3. Schema: ≥3 relevant schema types → +2.0
    a3 = 2.0 if len(schema_types) >= 3 else 0.0
    factors.append({"name": "≥3 schema types", "points": a3, "max": 2.0})

    # 4. Root files: robots.txt + sitemap + llms.txt all verified → +1.5
    llms = byid.get("tech.llms_txt")
    root_ok = ("tech.robots.ok" in byid and "tech.sitemap" in byid
               and llms is not None and llms.status == Status.PASS)
    a4 = 1.5 if root_ok else 0.0
    factors.append({"name": "Root files", "points": a4, "max": 1.5})

    # 5. Delivery: ≥3 of {resource hints, async/defer, lazy ≥3, dims ≥3, compression} → +1.0
    hints, imgs = val("tech.resource_hints"), val("onpage.images.dims")
    comp = byid.get("tech.compression")
    signals = sum([
        hints.get("resource_hints", 0) > 0,
        (hints.get("scripts", 0) - hints.get("blocking_scripts", 0)) >= 3
        or (hints.get("scripts", 0) > 0 and hints.get("blocking_scripts", 0) == 0),
        imgs.get("with_lazy", 0) >= 3,
        imgs.get("with_dims", 0) >= 3,
        comp is not None and comp.status == Status.PASS,
    ])
    a5 = 1.0 if signals >= 3 else 0.0
    factors.append({"name": "Delivery signals", "points": a5, "max": 1.0})

    return {"total": round(sum(f["points"] for f in factors), 2), "max": 8.0, "factors": factors}


def _schema_types(byid: dict) -> set[str]:
    f = byid.get("schema.jsonld")
    if f is None or not isinstance(f.value, list):
        return set()
    return {str(t).lower() for t in f.value}
