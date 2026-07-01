"""Consultant report assessment - the deterministic Implementation Programme, Review Comparison,
Highest-ROI review, aggregate confidence and a programme-aware verdict.

Pure + deterministic: reads a report dict (scorecard rows/impact/reviews + findings + fixes) and
returns one additive object attached as scorecard["assessment"]. No LLM, no invented estimates -
impact comes from the scorecard rows, effort from effort.py, remediation class from reviews.py, and
the only estimate model is the fixed minutes-per-fix constants below. Reused by the web report, the
shared report, the print report, the Markdown export and MCP.
"""

from __future__ import annotations

from . import effort, reviews

_ACTIONABLE = ("fail", "warn")

# Phase definitions (ordered): key, name, objective, AI-agent suitability (1-5 stars), manual review.
_PHASES = [
    ("quick_wins", "Quick Wins",
     "Fast, safe fixes your AI agent can apply directly - the most readiness for the least effort.",
     5, "None - safe to auto-apply"),
    ("technical_foundations", "Technical Foundations",
     "Make the page reliably readable and crawlable by AI engines (rendering, delivery, security, "
     "structured-data wiring).",
     4, "Deploy / infra check"),
    ("content_improvements", "Content Improvements",
     "Sharpen how the page answers - front-loaded answers, confident language, extractable structure. "
     "Your agent drafts; you approve.",
     3, "Editorial review"),
    ("authority_business", "Authority & Business",
     "Ground the site as a trusted entity - identity, authorship, sameAs, local facts. Needs your "
     "business input.",
     1, "Business input required"),
]
_PHASE_META = {p[0]: {"name": p[1], "objective": p[2], "ai_agent_suitability": p[3],
                      "manual_review": p[4]} for p in _PHASES}
_PHASE_ORDER = [p[0] for p in _PHASES]

_BAND_LABEL = {"strong": "Strong", "solid": "Solid", "needs work": "Developing",
               "at risk": "At risk", "unknown": "Unknown"}


def _assign(cls: str, tier: str) -> tuple[str, int]:
    """(phase, minutes-per-fix) for a finding, from its remediation class + effort tier. The minutes
    are fixed constants (a documented model), not per-page estimates."""
    if tier == "involved":
        return "technical_foundations", 120
    if cls == "deterministic" and tier == "quick":
        return "quick_wins", 12
    if cls == "deterministic":            # moderate
        return "technical_foundations", 30
    if cls == "ai_assisted":
        return "content_improvements", 45
    return "authority_business", 60


def _fmt_time(minutes: int) -> str:
    if minutes < 90:
        return f"{minutes} minutes"
    if minutes < 480:
        h = round(minutes / 60 * 2) / 2
        return f"{h:g} hours"
    d = round(minutes / 480 * 2) / 2
    return f"{d:g} day" + ("s" if d != 1 else "")


def _impact_index(rows: list[dict]) -> tuple[dict[int, float], dict[str, int]]:
    """{row n -> impact} and {finding id -> the highest-impact row it appears in}."""
    impact_by_row = {r["n"]: float(r.get("impact") or 0) for r in rows}
    finding_row: dict[str, int] = {}
    for r in rows:
        for fid in r.get("findings", []):
            cur = finding_row.get(fid)
            if cur is None or impact_by_row[r["n"]] > impact_by_row.get(cur, -1):
                finding_row[fid] = r["n"]
    return impact_by_row, finding_row


def _round(x: float) -> float:
    return round(x * 2) / 2  # nearest 0.5, matching the scorecard


def build_assessment(report: dict) -> dict:
    sc = report.get("scorecard") or {}
    rows = sc.get("rows", [])
    findings = report.get("findings", [])
    by_id = {f["id"]: f for f in findings}
    fix_ids = {fx.get("finding_id") for fx in report.get("fixes", []) if fx.get("finding_id")}
    impact_by_row, finding_row = _impact_index(rows)

    actionable = [f for f in findings if f.get("status") in _ACTIONABLE]
    phases: dict[str, list[dict]] = {k: [] for k in _PHASE_ORDER}
    minutes: dict[str, int] = {k: 0 for k in _PHASE_ORDER}
    rows_hit: dict[str, set[int]] = {k: set() for k in _PHASE_ORDER}

    for f in actionable:
        fid = f["id"]
        cls = reviews.finding_class(fid, fix_ids)
        phase, mins = _assign(cls, effort.effort_tier(fid))
        rownum = finding_row.get(fid)
        imp = impact_by_row.get(rownum, 0.0) if rownum is not None else 0.0
        phases[phase].append({"finding_id": fid, "title": f.get("title"), "severity": f.get("severity"),
                              "impact": _round(imp)})
        minutes[phase] += mins
        if rownum is not None:
            rows_hit[phase].add(rownum)

    programme = []
    for key in _PHASE_ORDER:
        items = phases[key]
        if not items:
            continue
        improvement = _round(sum(impact_by_row[n] for n in rows_hit[key]))
        meta = _PHASE_META[key]
        items.sort(key=lambda x: x["impact"], reverse=True)
        programme.append({
            "key": key, "name": meta["name"], "objective": meta["objective"],
            "effort": _fmt_time(minutes[key]), "effort_minutes": minutes[key],
            "improvement": improvement, "fixes_count": len(items),
            "ai_agent_suitability": meta["ai_agent_suitability"], "manual_review": meta["manual_review"],
            "fixes": items,
        })

    total_recoverable = _round(sum(p["improvement"] for p in programme))
    total_minutes = sum(p["effort_minutes"] for p in programme)

    comparison = _review_comparison(sc.get("reviews", {}), by_id, impact_by_row, finding_row)
    highest_roi = max(comparison, key=lambda r: (r["recoverable"], r["issues"]), default=None) if comparison else None

    summary = sc.get("summary") or {}
    band = summary.get("band", "unknown")
    return {
        "headline_score": sc.get("headline_score"),
        "band": band,
        "band_label": _BAND_LABEL.get(band, band.title()),
        "confidence": reviews.review_confidence(report.get("meta", {}), findings),
        "verdict": _verdict(sc.get("headline_score"), band, programme, total_recoverable,
                            _fmt_time(total_minutes), highest_roi),
        "programme": programme,
        "total_recoverable": total_recoverable,
        "total_effort": _fmt_time(total_minutes) if programme else "0 minutes",
        "reviews": comparison,
        "highest_roi_review": highest_roi["key"] if highest_roi else None,
    }


def _review_comparison(reviews_map: dict, by_id: dict, impact_by_row: dict, finding_row: dict) -> list[dict]:
    out = []
    for key, rev in reviews_map.items():
        related = rev.get("related_findings", [])
        rows_hit = {finding_row[f] for f in related if f in finding_row and by_id.get(f, {}).get("status") in _ACTIONABLE}
        present = [f for f in related if f in by_id]
        passed = sum(1 for f in present if by_id[f].get("status") in ("pass", "info"))
        maturity = round(100 * passed / len(present)) if present else 100
        out.append({
            "key": key, "name": rev.get("review", key), "verdict": rev.get("verdict"),
            "confidence": (rev.get("confidence") or {}).get("level"),
            "issues": (rev.get("counts") or {}).get("issues", 0),
            "critical_high": (rev.get("counts") or {}).get("critical_high", 0),
            "recoverable": _round(sum(impact_by_row.get(n, 0.0) for n in rows_hit)),
            "maturity": maturity,
        })
    return out


def _verdict(score, band: str, programme: list[dict], total: float, total_time: str,
             highest_roi: dict | None) -> list[str]:
    label = _BAND_LABEL.get(band, band.title())
    lines: list[str] = []
    if not programme:
        lines.append(f"AI Readiness {score}/100 ({label}). No material issues remain - only minor "
                     "refinements.")
        return lines
    lines.append(f"AI Readiness {score}/100 ({label}). A focused programme could recover about "
                 f"+{total:g} over {total_time}.")
    first = programme[0]
    stars = "★" * first["ai_agent_suitability"]
    lines.append(f"Start with {first['name']}: +{first['improvement']:g} in {first['effort']} "
                 f"({stars} AI-agent suitable).")
    if highest_roi and highest_roi["recoverable"] > 0:
        lines.append(f"The highest-leverage area is the {highest_roi['name']} "
                     f"(+{highest_roi['recoverable']:g} recoverable).")
    return lines
