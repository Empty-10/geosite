"""Tests for report_export (derived views over a stored Report) and the version metadata."""

from __future__ import annotations

from astova_engine import scan_html
from astova_engine.models import ENGINE_VERSION, REPORT_VERSION, RULESET_VERSION
from astova_engine import report_export

WEAK_HTML = "<!doctype html><html><head></head><body><p>thin page, nothing useful here.</p></body></html>"


def _report() -> dict:
    r = scan_html("https://example.com", WEAK_HTML, online=False, fixes=True).to_dict()
    # simulate persistence stamping (store.get_by_token adds report_id; save adds scan_token)
    r["meta"]["report_id"] = 7
    r["meta"]["scan_token"] = "tok_abc"
    return r


# --------------------------------------------------------------------------- version metadata

def test_scan_stamps_version_meta():
    r = scan_html("https://example.com", WEAK_HTML, online=False).to_dict()
    assert r["meta"]["engine_version"] == ENGINE_VERSION
    assert r["meta"]["ruleset_version"] == RULESET_VERSION
    assert r["meta"]["report_version"] == REPORT_VERSION


def test_metadata_fields():
    m = report_export.report_metadata(_report())
    assert set(m) >= {"report_id", "created_at", "scanned_target", "engine_version",
                      "ruleset_version", "report_version", "share_token"}
    assert m["report_id"] == 7
    assert m["scanned_target"] == "https://example.com"
    assert m["share_token"] == "tok_abc"
    assert m["created_at"]  # fetched_at


# --------------------------------------------------------------------------- action summary

def test_action_summary_buckets_sum():
    s = report_export.action_summary(_report())
    assert s["actionable_count"] >= 1
    assert (s["deterministic_fix_count"] + s["ai_assisted_count"] + s["manual_count"]) == s["actionable_count"]
    assert len(s["deterministic"]) == s["deterministic_fix_count"]


def test_deterministic_bucket_uses_report_fixes():
    r = _report()
    fix_ids = {f["finding_id"] for f in r.get("fixes", [])}
    s = report_export.action_summary(r)
    det_ids = {i["finding_id"] for i in s["deterministic"]}
    # every finding that has a generated fix is bucketed deterministic
    assert fix_ids & {f["id"] for f in r["findings"]} <= det_ids or not fix_ids


# --------------------------------------------------------------------------- markdown + prompt

def test_markdown_shape():
    md = report_export.report_to_markdown(_report())
    assert md.startswith("# Astova AI Readiness Report")
    assert "Target: https://example.com" in md
    assert "## Action summary" in md
    assert "## Findings" in md
    assert "## Verification" in md
    assert f"Engine: {ENGINE_VERSION}" in md


def test_agent_prompt_has_safety_and_plan():
    p = report_export.report_to_agent_prompt(_report())
    assert "Do not invent facts" in p
    assert "ask before editing" in p.lower() or "manual or human-review" in p.lower()
    assert "# Astova AI Readiness Report" in p  # embeds the report markdown


def test_bundle_keys():
    b = report_export.report_bundle(_report())
    assert set(b) == {"metadata", "action_summary", "markdown", "agent_prompt"}
