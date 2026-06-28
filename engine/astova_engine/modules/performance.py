"""Performance module — Core Web Vitals + Lighthouse via Google PageSpeed Insights.

Authoritative API, so VERIFIED (per CLAUDE.md accuracy principle). Pure: the scanner fetches
the PSI response at the boundary and hands the JSON here; this module only parses it.

Two kinds of signal, both surfaced:
- Lab (Lighthouse): the metrics under lighthouseResult.audits, plus the overall 0–100 score.
- Field (CrUX): real-user data under loadingExperience — present only for sites with enough
  Chrome traffic; flagged separately so lab and field never blur together.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..models import Confidence, Finding, Pillar, Severity, Status

P = Pillar.PERFORMANCE
C = Confidence.VERIFIED


@dataclass(frozen=True)
class Metric:
    id: str
    audit: str  # Lighthouse audit key
    label: str
    good_max: float  # <= this → good
    poor_min: float  # >= this → poor
    severity: Severity
    recommendation: str


# Core Web Vitals (+ supporting lab metrics) with their standard thresholds.
METRICS = [
    Metric("perf.lcp", "largest-contentful-paint", "Largest Contentful Paint",
           2500, 4000, Severity.HIGH,
           "Speed up the largest above-the-fold element: preload it, compress/resize images, "
           "and cut render-blocking CSS/JS."),
    Metric("perf.cls", "cumulative-layout-shift", "Cumulative Layout Shift",
           0.1, 0.25, Severity.HIGH,
           "Reserve space for images, ads and embeds (set width/height) and avoid inserting "
           "content above existing content."),
    Metric("perf.tbt", "total-blocking-time", "Total Blocking Time",
           200, 600, Severity.MEDIUM,
           "Break up long JavaScript tasks and defer non-critical scripts (a lab proxy for INP)."),
    Metric("perf.fcp", "first-contentful-paint", "First Contentful Paint",
           1800, 3000, Severity.LOW,
           "Reduce server response time and render-blocking resources."),
    Metric("perf.si", "speed-index", "Speed Index",
           3400, 5800, Severity.LOW,
           "Improve how quickly the page visually fills in — optimise the critical render path."),
]

# CrUX field category → finding status.
_FIELD_STATUS = {"FAST": Status.PASS, "GOOD": Status.PASS, "AVERAGE": Status.WARN,
                 "NEEDS_IMPROVEMENT": Status.WARN, "SLOW": Status.FAIL, "POOR": Status.FAIL}


def pillar_score(psi: dict) -> int | None:
    """The authoritative Lighthouse performance score (0–100), or None if absent."""
    try:
        score = psi["lighthouseResult"]["categories"]["performance"]["score"]
        return round(score * 100) if score is not None else None
    except (KeyError, TypeError):
        return None


def _classify(value: float, m: Metric) -> tuple[Status, Severity]:
    if value <= m.good_max:
        return Status.PASS, Severity.INFO
    if value >= m.poor_min:
        return Status.FAIL, m.severity
    return Status.WARN, m.severity


def analyze(psi: dict) -> list[Finding]:
    out: list[Finding] = []
    lh = psi.get("lighthouseResult", {})
    audits = lh.get("audits", {})
    strategy = lh.get("configSettings", {}).get("formFactor", "mobile")

    score = pillar_score(psi)
    if score is not None:
        status = Status.PASS if score >= 90 else Status.WARN if score >= 50 else Status.FAIL
        sev = Severity.INFO if status == Status.PASS else Severity.HIGH if status == Status.FAIL else Severity.MEDIUM
        out.append(Finding("perf.score", P, "Performance score", status, sev, C, value=score,
                           evidence=f"Lighthouse {score}/100 ({strategy})"))

    for m in METRICS:
        audit = audits.get(m.audit)
        if not audit or audit.get("numericValue") is None:
            continue
        nv = audit["numericValue"]
        status, sev = _classify(nv, m)
        out.append(Finding(
            m.id, P, m.label, status, sev, C,
            value=round(nv, 3) if nv < 10 else round(nv),
            evidence=audit.get("displayValue"),
            recommendation=m.recommendation if status != Status.PASS else None,
        ))

    # CrUX field (real-user) overall category, when the URL has enough traffic.
    overall = psi.get("loadingExperience", {}).get("overall_category")
    if overall:
        out.append(Finding(
            "perf.field", P, "Real-user experience (CrUX)",
            _FIELD_STATUS.get(overall, Status.INFO),
            Severity.MEDIUM if overall in ("SLOW", "POOR") else Severity.INFO, C,
            value=overall,
            evidence=f"Chrome real-user data: {overall.replace('_', ' ').lower()}",
        ))

    return out
