"""Compare several scanned pages side by side — a deterministic competitor benchmark.

Given N page Reports (the first is "you", the rest competitors), aligns their 20-row scorecards
and works out, row by row, who leads — plus where the primary site leads and trails overall.
Pure and deterministic: identical inputs → identical comparison, no LLM, no external calls. The
same shape can later back an MCP `compare_urls` tool and the WordPress plugin.
"""

from __future__ import annotations

from .models import Report


def _site_summary(report: Report) -> dict:
    """Lean per-site header — the row table itself comes from `comparison.rows`, not here."""
    err = report.meta.get("error")
    card = None if err else report.scorecard
    return {
        "url": report.url,
        "final_url": report.meta.get("final_url", report.url),
        "error": err,
        "headline": card["headline_score"] if card else None,
        "citation": card["citation"] if card else None,
        "categories": card["categories"] if card else None,
        "summary": card["summary"] if card else None,
    }


def compare_reports(reports: list[Report]) -> dict:
    """Build the comparison structure. reports[0] is the primary site ("you")."""
    sites = [_site_summary(r) for r in reports]
    cards = [(None if r.meta.get("error") else r.scorecard) for r in reports]

    # Row-by-row: scorecards are always 20 rows in the same order, so align by index.
    rows = []
    ref = next((c for c in cards if c), None)
    if ref is not None:
        for i, row in enumerate(ref["rows"]):
            scores = [(c["rows"][i]["score"] if c else None) for c in cards]
            valid = [s for s in scores if s is not None]
            best = max(valid) if valid else None
            leaders = [j for j, s in enumerate(scores) if s == best] if best is not None else []
            rows.append({"n": row["n"], "label": row["label"], "scores": scores,
                         "best": best, "leaders": leaders})

    # Where the primary site leads / trails the best competitor, per row.
    you = 0
    leads, trails = [], []
    for row in rows:
        ys = row["scores"][you]
        others = [s for j, s in enumerate(row["scores"]) if j != you and s is not None]
        if ys is None or not others:
            continue
        best_other = max(others)
        if ys > best_other:
            leads.append({"n": row["n"], "label": row["label"], "margin": round(ys - best_other, 1)})
        elif ys < best_other:
            trails.append({"n": row["n"], "label": row["label"], "gap": round(best_other - ys, 1)})
    leads.sort(key=lambda x: x["margin"], reverse=True)
    trails.sort(key=lambda x: x["gap"], reverse=True)

    return {
        "you": you,
        "sites": sites,
        "headlines": [s["headline"] for s in sites],
        "rows": rows,
        "leads": leads,
        "trails": trails,
    }
