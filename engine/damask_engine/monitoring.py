"""Monitoring rules — turn a re-scan (and its diff vs the previous scan) into alerts.

Pure and deterministic: given the new report, the previous report, the diff (from
store.diff_reports) and the monitor's failure streak, return the alerts to raise. The service
layer handles scheduling, persistence and delivery. See docs/monitoring.md.

Anti-noise is non-negotiable (it's the brand): a fetch failure is NEVER reported as a score
crash — it routes to the availability rule, which only fires on the 2nd consecutive failure.
"""

from __future__ import annotations

SCORE_WARN = -5     # headline/overall drop that warns
SCORE_CRITICAL = -15  # …that's critical

# Regressions that are always critical regardless of score movement.
CRITICAL_CHECKS = {
    "geo.bot_access",          # AI crawlers newly blocked (handled as its own alert type)
    "schema.jsonld", "schema.missing", "schema.validation",  # structured data removed/broke
    "robots.noindex",          # page newly noindexed
    "tech.https", "tech.status", "tech.index_conflict",      # indexability broke
}


def _failed(report: dict) -> bool:
    """A scan 'failed' when the fetch errored or returned a non-2xx/3xx status."""
    meta = report.get("meta", {})
    if meta.get("error"):
        return True
    status = meta.get("status_code", 0)
    return not (200 <= status < 400)


def evaluate(url: str, new_report: dict, prev_report: dict | None, diff: dict | None,
             consecutive_failures: int) -> dict:
    """Return {"ok": bool, "alerts": [...]} for one monitor run.

    `consecutive_failures` is the streak BEFORE this run (so the first failure is silent and the
    second one alerts — debounced against transient blips / cold-start timeouts).
    """
    alerts: list[dict] = []

    if _failed(new_report):
        if consecutive_failures + 1 >= 2:  # 2nd consecutive failure
            alerts.append({
                "type": "availability", "severity": "critical",
                "summary": f"{url} is unreachable or erroring",
                "detail": {"error": new_report.get("meta", {}).get("error"),
                           "status": new_report.get("meta", {}).get("status_code")},
            })
        return {"ok": False, "alerts": alerts}

    # Scan succeeded. Recovery notice if it had been down.
    if consecutive_failures >= 2:
        alerts.append({"type": "availability", "severity": "info",
                       "summary": f"{url} is reachable again"})

    if not diff:  # first scan / no baseline — nothing to compare
        return {"ok": True, "alerts": alerts}

    regressed = {r["id"] for r in diff.get("regressed", [])}

    # AI-crawler access is the flagship GEO alert — its own type.
    if "geo.bot_access" in regressed:
        alerts.append({"type": "ai_crawler", "severity": "critical",
                       "summary": "AI crawlers are newly blocked from this page",
                       "detail": {"id": "geo.bot_access"}})

    crit = (regressed & CRITICAL_CHECKS) - {"geo.bot_access"}
    if crit:
        alerts.append({"type": "check", "severity": "critical",
                       "summary": f"Critical checks regressed: {', '.join(sorted(crit))}",
                       "detail": {"ids": sorted(crit)}})

    sd = diff.get("score_delta", 0)
    if sd <= SCORE_CRITICAL:
        alerts.append({"type": "score", "severity": "critical",
                       "summary": f"Score dropped {sd} points", "detail": {"score_delta": sd}})
    elif sd <= SCORE_WARN:
        alerts.append({"type": "score", "severity": "warning",
                       "summary": f"Score dropped {sd} points", "detail": {"score_delta": sd}})

    # Non-critical regressions, only if nothing bigger already covers them.
    other = regressed - CRITICAL_CHECKS
    if other and not crit and sd > SCORE_WARN:
        alerts.append({"type": "check", "severity": "warning",
                       "summary": f"{len(other)} check(s) regressed",
                       "detail": {"ids": sorted(other)}})

    return {"ok": True, "alerts": alerts}
