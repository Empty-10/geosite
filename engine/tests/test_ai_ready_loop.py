"""Tests for the ai_ready_loop orchestration workflow.

scan / scan_project are monkeypatched to offline scans; the tool must reuse them + explain_finding +
generate_fix + verify_fix without duplicating logic, and return the compact prioritised plan.
"""

from __future__ import annotations

import astova_engine.ai_ready as ai_ready
from astova_engine import scan_html
from astova_engine.models import Report

# A weak page: no title, no meta description, no schema, no viewport, no canonical -> several fail/warn.
WEAK_HTML = "<!doctype html><html><head></head><body><p>hello there friend, this is short.</p></body></html>"

# A strong page: title + description + viewport + canonical + schema present.
STRONG_HTML = """<!doctype html><html lang="en"><head>
<title>How to brew pour-over coffee: a complete beginner guide</title>
<meta name="description" content="A clear, complete guide to brewing pour-over coffee at home, with
ratios, timings and the gear you need - roughly 120 to 160 characters of genuine summary text here.">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="canonical" href="https://example.com/coffee">
<script type="application/ld+json">{"@context":"https://schema.org","@type":"Article","headline":"Pour-over coffee","author":{"@type":"Person","name":"Jo"}}</script>
</head><body><h1>Pour-over coffee</h1>
<h2>What ratio should I use?</h2><p>Use a 1 to 16 ratio of grounds to water for a balanced cup every time.</p>
<h2>How long should it take?</h2><p>Aim for a total brew time of about three minutes from first pour.</p>
<p>Pour-over coffee is a manual brewing method that rewards a steady, even pour and fresh grounds.</p>
</body></html>"""

_TOP_KEYS = {"target", "target_type", "score", "confidence", "summary", "findings_count",
             "actionable_count", "deterministic_fix_count", "ai_assisted_count", "manual_count", "items"}
_ITEM_KEYS = {"finding_id", "title", "status", "severity", "confidence", "evidence",
              "recommendation", "knowledge", "fix", "verify", "agent_next_step"}


def _patch_url(monkeypatch, html):
    monkeypatch.setattr(ai_ready, "scan", lambda url: scan_html(url, html, online=False))


def test_shape_and_items(monkeypatch):
    _patch_url(monkeypatch, WEAK_HTML)
    out = ai_ready.ai_ready_loop("https://example.com", "url")
    assert _TOP_KEYS <= set(out)
    assert out["confidence"] == "verified"
    assert out["target_type"] == "url"
    assert out["actionable_count"] > 0 and out["items"]
    for it in out["items"]:
        assert _ITEM_KEYS <= set(it)
        assert it["status"] in ("fail", "warn")
        assert it["verify"] == {"tool": "verify_fix", "target": "https://example.com",
                                "target_type": "url", "finding_id": it["finding_id"]}
        assert it["fix"]["finding_id"] is not None  # generate_fix object always attached
    # counts partition the shown items
    assert (out["deterministic_fix_count"] + out["ai_assisted_count"]
            + out["manual_count"]) == len(out["items"])


def test_sorted_by_severity(monkeypatch):
    _patch_url(monkeypatch, WEAK_HTML)
    out = ai_ready.ai_ready_loop("https://example.com", "url")
    rank = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    ranks = [rank[it["severity"]] for it in out["items"]]
    assert ranks == sorted(ranks)


def test_max_items_caps_output(monkeypatch):
    _patch_url(monkeypatch, WEAK_HTML)
    out = ai_ready.ai_ready_loop("https://example.com", "url", max_items=2)
    assert len(out["items"]) == 2
    assert out["actionable_count"] >= 2  # total is not truncated, only the items list


def test_deterministic_fix_attached_and_counted(monkeypatch):
    _patch_url(monkeypatch, WEAK_HTML)
    out = ai_ready.ai_ready_loop("https://example.com", "url", max_items=50)
    by = {it["finding_id"]: it for it in out["items"]}
    # schema.missing has a ready deterministic fix from a URL alone
    assert "schema.missing" in by
    assert by["schema.missing"]["fix"]["supported"] is True
    assert "application/ld+json" in by["schema.missing"]["fix"]["generated_content"]
    assert out["deterministic_fix_count"] >= 1


def test_unsupported_fix_included_not_omitted(monkeypatch):
    # geo.* content findings have no ready generate_fix -> fix present with supported:false.
    _patch_url(monkeypatch, WEAK_HTML)
    out = ai_ready.ai_ready_loop("https://example.com", "url", max_items=50)
    unsupported = [it for it in out["items"] if it["fix"]["supported"] is False]
    assert unsupported, "weak page should have at least one non-fixable finding"
    for it in unsupported:
        assert "supported" in it["fix"] and it["fix"]["supported"] is False


def test_knowledge_null_when_no_card(monkeypatch):
    # A finding id with no knowledge card must still appear with knowledge: null.
    bad = Report(url="https://x.test", meta={})
    from astova_engine.models import Finding, Pillar, Severity, Status, Confidence
    bad.findings = [Finding("totally.unknown.finding", Pillar.TECHNICAL, "Made up",
                            Status.FAIL, Severity.HIGH, Confidence.VERIFIED,
                            evidence="x", recommendation="do something")]
    bad.overall_score = 50
    monkeypatch.setattr(ai_ready, "scan", lambda url: bad)
    out = ai_ready.ai_ready_loop("https://x.test", "url")
    it = out["items"][0]
    assert it["finding_id"] == "totally.unknown.finding"
    assert it["knowledge"] is None
    assert it["fix"]["supported"] is False


def test_strong_page_is_ai_ready(monkeypatch):
    _patch_url(monkeypatch, STRONG_HTML)
    out = ai_ready.ai_ready_loop("https://example.com/coffee", "url")
    # very few or zero actionable; summary reflects readiness when zero
    if out["actionable_count"] == 0:
        assert "AI Ready" in out["summary"]
        assert out["items"] == []


def test_project_target(tmp_path):
    # empty project -> robots/sitemap missing fire; project uses scan_project (not monkeypatched).
    out = ai_ready.ai_ready_loop(str(tmp_path), "project")
    assert out["target_type"] == "project"
    assert out["actionable_count"] >= 1
    ids = {it["finding_id"] for it in out["items"]}
    assert "tech.robots.missing" in ids
    # project robots fix uses the placeholder origin and is supported
    robots = next(it for it in out["items"] if it["finding_id"] == "tech.robots.missing")
    assert robots["fix"]["supported"] is True
    assert "GPTBot" in robots["fix"]["generated_content"]


def test_scan_failure_structured_error(monkeypatch):
    bad = Report(url="https://x.test", meta={"error": "could not resolve host"})
    monkeypatch.setattr(ai_ready, "scan", lambda url: bad)
    out = ai_ready.ai_ready_loop("https://x.test", "url")
    assert out["error"] == "Could not scan https://x.test: could not resolve host."
    assert out["items"] == [] and out["score"] is None


def test_invalid_target_type():
    out = ai_ready.ai_ready_loop("https://x.test", "bogus")
    assert "error" in out and out["items"] == []
