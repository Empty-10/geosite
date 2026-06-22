"""Fixture tests for the performance module + the Performance pillar override. Offline:
the module parses a trimmed PageSpeed Insights JSON; no network or API key needed."""

from __future__ import annotations

from damask_engine.models import Pillar, Status
from damask_engine.modules.performance import analyze, pillar_score
from damask_engine.scoring import build_report


def psi(score=0.75, lcp=3200, cls=0.05, tbt=150, fcp=1500, si=3000, field="AVERAGE"):
    """Build a minimal PSI response with tunable metrics."""
    def audit(v, disp):
        return {"numericValue": v, "displayValue": disp}

    body = {
        "lighthouseResult": {
            "configSettings": {"formFactor": "mobile"},
            "categories": {"performance": {"score": score}},
            "audits": {
                "largest-contentful-paint": audit(lcp, f"{lcp/1000:.1f} s"),
                "cumulative-layout-shift": audit(cls, str(cls)),
                "total-blocking-time": audit(tbt, f"{tbt} ms"),
                "first-contentful-paint": audit(fcp, f"{fcp/1000:.1f} s"),
                "speed-index": audit(si, f"{si/1000:.1f} s"),
            },
        }
    }
    if field:
        body["loadingExperience"] = {"overall_category": field}
    return body


def test_pillar_score_from_lighthouse():
    assert pillar_score(psi(score=0.92)) == 92
    assert pillar_score(psi(score=0.4)) == 40
    assert pillar_score({}) is None


def test_metric_classification():
    ids = {f.id: f for f in analyze(psi(lcp=3200, cls=0.05, tbt=700))}
    assert ids["perf.lcp"].status == Status.WARN  # 2500 < 3200 < 4000
    assert ids["perf.cls"].status == Status.PASS  # 0.05 <= 0.1
    assert ids["perf.tbt"].status == Status.FAIL  # 700 >= 600
    # all carry the VERIFIED label (authoritative API)
    assert all(f.confidence.value == "verified" for f in ids.values())


def test_score_finding_bands():
    assert {f.id: f.status for f in analyze(psi(score=0.95))}["perf.score"] == Status.PASS
    assert {f.id: f.status for f in analyze(psi(score=0.6))}["perf.score"] == Status.WARN
    assert {f.id: f.status for f in analyze(psi(score=0.3))}["perf.score"] == Status.FAIL


def test_field_data_finding():
    good = {f.id: f for f in analyze(psi(field="FAST"))}
    assert good["perf.field"].status == Status.PASS
    slow = {f.id: f for f in analyze(psi(field="SLOW"))}
    assert slow["perf.field"].status == Status.FAIL
    none = {f.id: f for f in analyze(psi(field=None))}
    assert "perf.field" not in none


def test_pillar_override_uses_lighthouse_score_not_penalties():
    findings = analyze(psi(score=0.83, tbt=700))  # a FAIL metric is present
    report = build_report("https://x.test", findings,
                          pillar_overrides={Pillar.PERFORMANCE: pillar_score(psi(score=0.83))})
    # Pillar score is the authoritative 83, NOT 100-minus-penalties.
    assert report.pillar_scores["performance"] == 83
    assert report.overall_score == 83  # only one pillar present → equals it
