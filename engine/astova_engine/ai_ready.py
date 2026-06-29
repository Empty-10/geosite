"""ai_ready_loop - the one-call "tell me exactly what to fix next" workflow for AI coding agents.

Pure orchestration over capabilities that already exist: it assesses a target (URL or project),
picks the highest-priority fail/warn findings, and for each one attaches the knowledge card
(explain_finding), the deterministic fix where one exists (generate_fix), and the exact verify_fix
call to confirm the fix later. No new scan logic, no LLM, no fix applied, no files touched.
"""

from __future__ import annotations

from . import knowledge
from .fixes import generate_fix
from .scanner import scan, scan_project

# Each item's verify block names the verify_fix MCP tool for the agent to call; we don't invoke it
# here (this is a planning step), so verify_fix itself is not imported.

_SEV_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
_STATUS_RANK = {"fail": 0, "warn": 1}
_ACTIONABLE = ("fail", "warn")
_VALID_TARGET_TYPES = ("url", "project")

# Placeholder origin for project targets so the URL-based generators (robots/llms/schema/canonical)
# still produce ready-to-edit template content - the agent swaps in the real domain. Mirrors the
# "https://YOUR-DOMAIN" convention already used by the project file-fix templates.
_PROJECT_PLACEHOLDER_URL = "https://YOUR-DOMAIN"


def _error(target: str, target_type: str, message: str) -> dict:
    return {
        "target": target, "target_type": target_type, "score": None,
        "confidence": "verified", "summary": message, "error": message,
        "findings_count": 0, "actionable_count": 0, "deterministic_fix_count": 0,
        "ai_assisted_count": 0, "manual_count": 0, "items": [],
    }


def _bucket(card: dict | None) -> str:
    """Remediation path for a finding, from the engine's own taxonomy (can_astova_generate)."""
    cg = (card or {}).get("can_astova_generate")
    if cg == "deterministic":
        return "deterministic"
    if cg == "ai_assisted":
        return "ai_assisted"
    return "manual"


def ai_ready_loop(target: str, target_type: str = "url", max_items: int = 10) -> dict:
    """Assess `target` and return the prioritised next-action plan to make it AI Ready.

    Orchestrates scan / scan_project + explain_finding + generate_fix + verify_fix. Returns a single
    compact object: the score, summary counts, and up to `max_items` items (highest-severity fail/warn
    findings first), each carrying its knowledge, deterministic fix (or supported:false), and the
    verify_fix call to confirm it. A failed scan returns a structured error.
    """
    tt = (target_type or "url").strip().lower()
    if tt not in _VALID_TARGET_TYPES:
        return _error(target, target_type, f"Unknown target_type '{target_type}'. Use 'url' or 'project'.")

    report = scan_project(target) if tt == "project" else scan(target)
    d = report.to_dict()
    scan_error = d.get("meta", {}).get("error")
    if scan_error:
        return _error(target, tt, f"Could not scan {target}: {scan_error}.")

    findings = d["findings"]
    actionable = [f for f in findings if f["status"] in _ACTIONABLE]
    actionable.sort(key=lambda f: (_SEV_RANK.get(f["severity"], 9), _STATUS_RANK.get(f["status"], 9)))
    selected = actionable[: max(max_items, 0)]

    fix_url = target if tt == "url" else _PROJECT_PLACEHOLDER_URL
    counts = {"deterministic": 0, "ai_assisted": 0, "manual": 0}
    items: list[dict] = []

    for f in selected:
        fid = f["id"]
        card = knowledge.explain(fid)  # None if no card - included as knowledge: null
        fix = generate_fix(fid, {"url": fix_url, "html": None})
        bucket = "deterministic" if fix.get("supported") else _bucket(card)
        counts[bucket] += 1

        verify_block = {"tool": "verify_fix", "target": target, "target_type": tt, "finding_id": fid}
        items.append({
            "finding_id": fid,
            "title": f["title"],
            "status": f["status"],
            "severity": f["severity"],
            "confidence": f["confidence"],
            "evidence": f.get("evidence"),
            "recommendation": f.get("recommendation"),
            "knowledge": card,
            "fix": fix,
            "verify": verify_block,
            "agent_next_step": _next_step(bucket, fid, fix, f.get("recommendation"), tt, target),
        })

    score = d.get("overall_score")
    summary = (
        f"{len(actionable)} actionable issue(s) on {target} (score {score}/100). "
        f"Top {len(items)} shown: {counts['deterministic']} with a ready deterministic fix, "
        f"{counts['ai_assisted']} need an AI-drafted edit, {counts['manual']} need manual review. "
        "Apply each item's fix, then call verify_fix to confirm."
    ) if actionable else f"No fail/warn findings on {target} (score {score}/100) - it looks AI Ready."

    return {
        "target": target,
        "target_type": tt,
        "score": score,
        "confidence": "verified",
        "summary": summary,
        "findings_count": len(findings),
        "actionable_count": len(actionable),
        "deterministic_fix_count": counts["deterministic"],
        "ai_assisted_count": counts["ai_assisted"],
        "manual_count": counts["manual"],
        "items": items,
    }


def _next_step(bucket: str, fid: str, fix: dict, recommendation: str | None,
               target_type: str, target: str) -> str:
    verify = f"call verify_fix('{target}', '{fid}', '{target_type}') to confirm."
    if bucket == "deterministic" and fix.get("supported"):
        where = fix.get("suggested_location") or "the page"
        return f"Apply the generated fix to {where}, then {verify}"
    if bucket == "deterministic":
        how = recommendation or "Apply the fix from knowledge.how_to_fix"
        return f"Astova can generate this deterministically. {how}. Then {verify}"
    if bucket == "ai_assisted":
        return f"Draft the edit (see knowledge.agent_guidance / how_to_fix), apply it, then {verify}"
    return f"{recommendation or 'Review and fix manually.'} Then {verify}"
