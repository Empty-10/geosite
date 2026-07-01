"""Derived views over a stored Report - for the shareable AI Readiness Report page.

Pure and read-only: takes a report dict (as produced by Report.to_dict() and persisted by store) and
derives the action-summary buckets, the self-describing metadata, a Markdown export and an agent
prompt. Reuses the existing findings, the knowledge taxonomy (can_astova_generate) and the report's
deterministic fixes - no scanning, no LLM, no new audit logic.
"""

from __future__ import annotations

from . import knowledge

_PILLAR_LABEL = {
    "technical": "Technical", "onpage": "On-page", "geo": "GEO readiness",
    "performance": "Performance", "local": "Local",
}
_PILLAR_ORDER = ["technical", "onpage", "geo", "local", "performance"]
_ACTIONABLE = ("fail", "warn")
_SEV_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

_SAFETY = [
    "Do not invent facts, author names, sameAs links, opening hours, addresses, legal claims, "
    "local-business details or data points.",
    "Apply deterministic fixes exactly as given; draft AI-assisted items only from real page content.",
    "Ask before editing any manual or human-review item.",
    "After changes, re-scan (or call verify_fix per finding) to confirm the score improved.",
]


def _fix_ids(report: dict) -> set[str]:
    return {f.get("finding_id") for f in report.get("fixes", []) if f.get("finding_id")}


def _bucket(finding_id: str, fix_ids: set[str]) -> str:
    """deterministic (a ready fix exists) / ai_assisted / manual - from the knowledge taxonomy."""
    if finding_id in fix_ids:
        return "deterministic"
    card = knowledge.explain(finding_id) or {}
    cg = card.get("can_astova_generate")
    if cg == "deterministic":
        return "deterministic"
    if cg == "ai_assisted":
        return "ai_assisted"
    return "manual"


def action_summary(report: dict) -> dict:
    """Bucket the report's fail/warn findings into deterministic / ai_assisted / manual."""
    fix_ids = _fix_ids(report)
    buckets: dict[str, list[dict]] = {"deterministic": [], "ai_assisted": [], "manual": []}
    actionable = [f for f in report.get("findings", []) if f.get("status") in _ACTIONABLE]
    actionable.sort(key=lambda f: _SEV_RANK.get(f.get("severity"), 9))
    for f in actionable:
        b = _bucket(f["id"], fix_ids)
        buckets[b].append({
            "finding_id": f["id"], "title": f.get("title"), "pillar": f.get("pillar"),
            "severity": f.get("severity"), "status": f.get("status"),
            "evidence": f.get("evidence"), "recommendation": f.get("recommendation"),
        })
    return {
        "actionable_count": len(actionable),
        "deterministic_fix_count": len(buckets["deterministic"]),
        "ai_assisted_count": len(buckets["ai_assisted"]),
        "manual_count": len(buckets["manual"]),
        "deterministic": buckets["deterministic"],
        "ai_assisted": buckets["ai_assisted"],
        "manual": buckets["manual"],
    }


def report_metadata(report: dict) -> dict:
    """The self-describing report metadata fields."""
    meta = report.get("meta", {})
    return {
        "report_id": meta.get("report_id"),
        "created_at": report.get("fetched_at"),
        "scanned_target": meta.get("final_url") or report.get("url"),
        "engine_version": meta.get("engine_version"),
        "ruleset_version": meta.get("ruleset_version"),
        "report_version": meta.get("report_version"),
        "share_token": meta.get("scan_token"),
    }


def _findings_by_pillar(report: dict) -> list[tuple[str, list[dict]]]:
    groups: dict[str, list[dict]] = {}
    for f in report.get("findings", []):
        if f.get("status") in _ACTIONABLE:
            groups.setdefault(f.get("pillar"), []).append(f)
    ordered = [p for p in _PILLAR_ORDER if p in groups] + [p for p in groups if p not in _PILLAR_ORDER]
    return [(p, sorted(groups[p], key=lambda f: _SEV_RANK.get(f.get("severity"), 9))) for p in ordered]


def _programme_markdown(report: dict) -> list[str]:
    """Render the deterministic Implementation Programme from scorecard.assessment (no recompute)."""
    a = (report.get("scorecard") or {}).get("assessment")
    if not a:
        return []
    out = ["## Executive assessment", ""]
    out += [line for line in a.get("verdict", [])]
    out.append("")
    if a.get("programme"):
        out += ["## Implementation programme", ""]
        for p in a["programme"]:
            stars = "★" * p["ai_agent_suitability"]
            out.append(f"### {p['name']} - {p['effort']}, +{p['improvement']:g} AI Readiness, "
                       f"{p['fixes_count']} fix(es)")
            out.append(f"- Objective: {p['objective']}")
            out.append(f"- AI-agent suitability: {stars}  |  Manual review: {p['manual_review']}")
            out.append("- Fixes: " + ", ".join(f"{f['finding_id']} (+{f['impact']:g})" for f in p["fixes"]))
            out.append("")
    return out


def report_to_markdown(report: dict) -> str:
    """A clean Markdown AI Readiness report - score, action summary, findings by category, verify."""
    m = report_metadata(report)
    s = action_summary(report)
    out = [
        "# Astova AI Readiness Report",
        "",
        f"Target: {m['scanned_target']}",
        f"Score: {report.get('overall_score')}/100",
        f"Generated: {m['created_at']}",
        f"Report ID: {m['report_id']}  |  Engine: {m['engine_version']}  |  "
        f"Ruleset: {m['ruleset_version']}  |  Report format: {m['report_version']}",
        "",
        "## Action summary",
        "",
        f"* Actionable findings: {s['actionable_count']}",
        f"* Deterministic fixes available: {s['deterministic_fix_count']}",
        f"* AI-assisted fixes: {s['ai_assisted_count']}",
        f"* Manual review items: {s['manual_count']}",
        "",
    ]
    out += _programme_markdown(report)
    out += [
        "## Findings",
        "",
    ]
    groups = _findings_by_pillar(report)
    if not groups:
        out.append("No fail/warn findings - this page looks AI Ready.")
        out.append("")
    for pillar, findings in groups:
        out.append(f"### {_PILLAR_LABEL.get(pillar, pillar or 'Other')}")
        for f in findings:
            tag = (f.get("status") or "").upper()
            line = f"- [{tag}] {f.get('title')}"
            if f.get("evidence"):
                line += f" - {f['evidence']}"
            out.append(line)
            if f.get("recommendation"):
                out.append(f"  - Fix: {f['recommendation']}")
        out.append("")
    out += [
        "## Verification",
        "",
        "Apply the fixes, then re-scan the target (or call verify_fix per finding) to confirm the "
        "score improved. Every finding above is VERIFIED - read from the live page, reproducible.",
        "",
    ]
    return "\n".join(out)


def report_to_agent_prompt(report: dict) -> str:
    """A ready-to-paste prompt: the report plan plus the safety guardrails for an AI coding agent."""
    m = report_metadata(report)
    header = (
        f"Use this Astova AI Readiness report to improve {m['scanned_target']} (score "
        f"{report.get('overall_score')}/100). Work through the findings safely:"
    )
    rules = "\n".join(f"- {r}" for r in _SAFETY)
    return f"{header}\n\n{rules}\n\n{report_to_markdown(report)}"


def report_bundle(report: dict) -> dict:
    """Everything the report page needs, derived from the stored report in one shot."""
    return {
        "metadata": report_metadata(report),
        "action_summary": action_summary(report),
        "markdown": report_to_markdown(report),
        "agent_prompt": report_to_agent_prompt(report),
    }
