"""Tests for the deterministic consultant assessment (Implementation Programme + comparison)."""

from __future__ import annotations

from astova_engine import assessment, scan_html
from astova_engine.modules import schema_review

# schema.missing has a deterministic fix; geo.aeo is editorial; geo.js_rendered is infra; geo.entity manual.
REPORT = {
    "meta": {"word_count": 800},
    "fixes": [{"finding_id": "schema.missing"}],
    "findings": [
        {"id": "schema.missing", "status": "warn", "severity": "medium", "title": "Schema"},
        {"id": "geo.aeo", "status": "fail", "severity": "high", "title": "Answer"},
        {"id": "geo.js_rendered", "status": "warn", "severity": "medium", "title": "JS"},
        {"id": "geo.entity", "status": "warn", "severity": "low", "title": "Entity"},
    ],
    "scorecard": {
        "headline_score": 60, "summary": {"band": "needs work"},
        "rows": [
            {"n": 1, "impact": 4.0, "findings": ["schema.missing"]},
            {"n": 2, "impact": 6.0, "findings": ["geo.aeo"]},
            {"n": 3, "impact": 1.0, "findings": ["geo.js_rendered"]},
            {"n": 4, "impact": 2.0, "findings": ["geo.entity"]},
        ],
        "reviews": {
            "answerability": {"review": "Answerability Review", "verdict": "weak",
                              "confidence": {"level": "medium"}, "counts": {"issues": 1, "critical_high": 1},
                              "related_findings": ["geo.aeo"]},
            "schema": {"review": "Schema Review", "verdict": "partial", "confidence": {"level": "high"},
                       "counts": {"issues": 1, "critical_high": 0}, "related_findings": ["schema.missing"]},
        },
    },
}


def _phases(a):
    return {p["key"]: p for p in a["programme"]}


# --------------------------------------------------------------------------- phase assignment

def test_assign_rules():
    assert assessment._assign("deterministic", "quick") == ("quick_wins", 12)
    assert assessment._assign("deterministic", "moderate") == ("technical_foundations", 30)
    assert assessment._assign("ai_assisted", "moderate") == ("content_improvements", 45)
    assert assessment._assign("manual", "moderate") == ("authority_business", 60)
    assert assessment._assign("ai_assisted", "involved") == ("technical_foundations", 120)  # infra wins


def test_programme_buckets_findings_into_phases():
    a = assessment.build_assessment(REPORT)
    p = _phases(a)
    assert p["quick_wins"]["fixes"][0]["finding_id"] == "schema.missing"
    assert p["content_improvements"]["fixes"][0]["finding_id"] == "geo.aeo"
    assert p["technical_foundations"]["fixes"][0]["finding_id"] == "geo.js_rendered"
    assert p["authority_business"]["fixes"][0]["finding_id"] == "geo.entity"


# --------------------------------------------------------------------------- per-phase attributes

def test_phase_attributes_present_and_deterministic():
    p = _phases(assessment.build_assessment(REPORT))
    qw = p["quick_wins"]
    assert qw["objective"] and qw["effort"] == "12 minutes"  # 1 quick fix x 12 min
    assert qw["ai_agent_suitability"] == 5
    assert qw["manual_review"] == "None - safe to auto-apply"
    assert qw["improvement"] == 4.0 and qw["fixes_count"] == 1
    assert p["authority_business"]["ai_agent_suitability"] == 1
    assert p["content_improvements"]["manual_review"] == "Editorial review"


def test_effort_time_formatting():
    assert assessment._fmt_time(48) == "48 minutes"
    assert assessment._fmt_time(180) == "3 hours"
    assert assessment._fmt_time(480) == "1 day"
    assert assessment._fmt_time(960) == "2 days"


def test_improvement_dedups_by_row():
    rep = {
        "meta": {}, "fixes": [],
        "findings": [{"id": "a.x", "status": "warn", "severity": "low", "title": "A"},
                     {"id": "a.y", "status": "warn", "severity": "low", "title": "B"}],
        "scorecard": {"headline_score": 50, "summary": {"band": "solid"},
                      "rows": [{"n": 1, "impact": 5.0, "findings": ["a.x", "a.y"]}], "reviews": {}},
    }
    a = assessment.build_assessment(rep)
    # both findings share row 1 -> improvement counts the row once (5.0), not 10.0
    assert sum(p["improvement"] for p in a["programme"]) == 5.0


# --------------------------------------------------------------------------- totals + comparison

def test_totals_and_comparison_and_roi():
    a = assessment.build_assessment(REPORT)
    assert a["total_recoverable"] == 13.0       # 4+6+1+2
    by = {r["key"]: r for r in a["reviews"]}
    assert by["answerability"]["recoverable"] == 6.0 and by["schema"]["recoverable"] == 4.0
    assert a["highest_roi_review"] == "answerability"   # 6 > 4
    assert 0 <= by["answerability"]["maturity"] <= 100


def test_verdict_lines_reference_programme():
    a = assessment.build_assessment(REPORT)
    assert any("AI Readiness 60/100 (Developing)" in line for line in a["verdict"])
    assert any("Start with Quick Wins" in line for line in a["verdict"])


def test_empty_programme_when_all_pass():
    rep = {"meta": {"word_count": 800}, "fixes": [],
           "findings": [{"id": "geo.aeo", "status": "pass", "severity": "info", "title": "Answer"}],
           "scorecard": {"headline_score": 95, "summary": {"band": "strong"},
                         "rows": [{"n": 1, "impact": 0.0, "findings": ["geo.aeo"]}], "reviews": {}}}
    a = assessment.build_assessment(rep)
    assert a["programme"] == [] and a["total_recoverable"] == 0
    assert any("No material issues" in line for line in a["verdict"])


# --------------------------------------------------------------------------- schema review contract + wiring

def test_schema_review_summarize_contract():
    rep = {"meta": {}, "fixes": [],
           "findings": [{"id": "schema.missing", "status": "warn", "severity": "medium", "title": "S"}]}
    out = schema_review.summarize(rep)
    assert out["review"] == "Schema Review" and out["key"] == "schema"
    assert out["verdict"] in ("strong", "partial", "weak")
    assert out["likely_ai_quote"] is None
    assert any("no structured data" in r for r in out["confidence"]["reasons"])


def test_scan_attaches_assessment_and_both_reviews():
    d = scan_html("https://x.com", "<html><head><title>x</title></head><body><h1>Hi</h1>"
                  "<p>This is a real answer sentence that an engine could lift from the page.</p>"
                  "</body></html>", online=True).to_dict()
    sc = d["scorecard"]
    assert "assessment" in sc
    assert set(sc["reviews"]) == {"answerability", "schema"}
    assert "programme" in sc["assessment"] and "reviews" in sc["assessment"]
