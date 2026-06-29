"""Deterministic fix verification - the closing step of the remediation loop.

An AI coding agent applies a change itself, then asks Astova whether a SPECIFIC finding is now
resolved. We answer by re-running the SAME deterministic scan (URL or project) and inspecting that
one finding's status - no LLM, no fix applied, no files touched. Just a re-scan and a verdict.

Resolution rule (per the product's own severity model):
- the finding is gone from the new scan                  -> fixed (the symptom no longer fires)
- the finding is present with status pass / info         -> fixed (info = "not a problem")
- the finding is present with status warn / fail         -> not fixed
"""

from __future__ import annotations

from .fixes import _FINDING_ALIASES
from .scanner import scan, scan_project

# A finding that is present but PASS/INFO counts as resolved (INFO = the engine saying "fine").
_FIXED_STATUSES = {"pass", "info"}
_VALID_TARGET_TYPES = ("url", "project")


def _result(*, target: str, target_type: str, finding_id: str, fixed: bool,
            current_status: str | None, current_severity: str | None, evidence: str | None,
            score_after: int | None, explanation: str, next_step: str,
            error: str | None = None) -> dict:
    out = {
        "target": target,
        "target_type": target_type,
        "finding_id": finding_id,
        "fixed": fixed,
        "current_status": current_status,
        "current_severity": current_severity,
        "evidence": evidence,
        "score_after": score_after,
        "confidence": "verified",
        "explanation": explanation,
        "next_step": next_step,
    }
    if error is not None:
        out["error"] = error
    return out


def verify_fix(target: str, finding_id: str, target_type: str = "url") -> dict:
    """Re-scan `target` and report whether `finding_id` is now resolved. Deterministic.

    target_type "url" re-runs a live URL scan; "project" re-runs a project-directory audit. The
    requested finding_id is echoed back verbatim; matching uses the same alias map as generate_fix
    (so onpage.canonical resolves to canonical).
    """
    tt = (target_type or "url").strip().lower()
    if tt not in _VALID_TARGET_TYPES:
        return _result(
            target=target, target_type=target_type, finding_id=finding_id, fixed=False,
            current_status="error", current_severity=None, evidence=None, score_after=None,
            explanation=f"Unknown target_type '{target_type}'. Use 'url' or 'project'.",
            next_step="Retry with target_type='url' (a live page) or 'project' (a repo directory).",
            error="invalid_target_type",
        )

    report = scan_project(target) if tt == "project" else scan(target)
    d = report.to_dict()

    scan_error = d.get("meta", {}).get("error")
    if scan_error:
        return _result(
            target=target, target_type=tt, finding_id=finding_id, fixed=False,
            current_status="error", current_severity=None, evidence=None, score_after=None,
            explanation=f"The re-scan of {target} failed: {scan_error}. Could not verify the fix.",
            next_step=("Confirm the target is reachable - a running URL for target_type='url', or an "
                       "existing project directory for 'project' - then call verify_fix again."),
            error=scan_error,
        )

    fid = _FINDING_ALIASES.get(finding_id, finding_id)
    match = next((f for f in d["findings"] if f["id"] == fid), None)
    score_after = d.get("overall_score")

    if match is None:
        return _result(
            target=target, target_type=tt, finding_id=finding_id, fixed=True,
            current_status=None, current_severity=None, evidence=None, score_after=score_after,
            explanation=(f"No '{finding_id}' finding in the new scan - the issue it flagged is no "
                         "longer present, so it is resolved."),
            next_step="Resolved. No further action needed for this finding.",
        )

    status = match["status"]
    fixed = status in _FIXED_STATUSES
    if fixed:
        explanation = (f"'{finding_id}' is now {status} - resolved.")
        next_step = "Resolved. No further action needed for this finding."
    else:
        explanation = (f"'{finding_id}' is still {status} - not yet resolved.")
        next_step = (f"Call generate_fix('{finding_id}') for the deterministic fix (or explain_finding "
                     "for guidance), apply it, then run verify_fix again.")
    return _result(
        target=target, target_type=tt, finding_id=finding_id, fixed=fixed,
        current_status=status, current_severity=match.get("severity"),
        evidence=match.get("evidence"), score_after=score_after,
        explanation=explanation, next_step=next_step,
    )
