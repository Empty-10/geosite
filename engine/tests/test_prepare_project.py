"""Tests for prepare_project_for_ai - the one-call context bundle for AI coding agents.

Project scans run for real on a tmp_path directory (offline, no network). The tool must reuse
ai_ready_loop + the project module without duplicating logic, and return the compact bundle.
"""

from __future__ import annotations

from astova_engine.ai_ready import (_RECOMMENDED_WORKFLOW, ai_ready_loop, prepare_project_for_ai)

_TOP_KEYS = {"project", "framework", "score", "summary", "recommended_workflow", "findings"}
_FINDING_KEYS = {"finding_id", "knowledge", "fix", "verify"}


def test_bundle_shape(tmp_path):
    (tmp_path / "robots.txt").write_text("User-agent: GPTBot\nDisallow: /\n")
    out = prepare_project_for_ai(str(tmp_path))
    assert _TOP_KEYS <= set(out)
    assert out["project"] == str(tmp_path)
    assert out["recommended_workflow"] == _RECOMMENDED_WORKFLOW
    assert isinstance(out["findings"], list) and out["findings"]
    for f in out["findings"]:
        assert set(f) == _FINDING_KEYS, set(f) ^ _FINDING_KEYS
        assert f["verify"]["tool"] == "verify_fix"             # verify present for every finding
        assert f["verify"]["finding_id"] == f["finding_id"]
        assert f["verify"]["target_type"] == "project"


def test_detects_framework(tmp_path):
    (tmp_path / "next.config.js").write_text("module.exports = {}\n")
    out = prepare_project_for_ai(str(tmp_path))
    assert out["framework"] == "nextjs"


def test_preserves_ai_ready_loop_ordering(tmp_path):
    (tmp_path / "robots.txt").write_text("User-agent: GPTBot\nDisallow: /\n")
    bundle = prepare_project_for_ai(str(tmp_path))
    plan = ai_ready_loop(str(tmp_path), "project", 25)
    assert [f["finding_id"] for f in bundle["findings"]] == [it["finding_id"] for it in plan["items"]]
    assert bundle["score"] == plan["score"]
    assert bundle["summary"] == plan["summary"]


def test_fix_only_when_supported(tmp_path):
    # GPTBot-blocking robots -> tech.robots.ai HAS a ready fix; sitemap missing -> no ready fix.
    (tmp_path / "robots.txt").write_text("User-agent: GPTBot\nDisallow: /\n")
    out = prepare_project_for_ai(str(tmp_path))
    by = {f["finding_id"]: f for f in out["findings"]}
    assert by["tech.robots.ai"]["fix"] is not None
    assert by["tech.robots.ai"]["fix"]["supported"] is True
    assert "GPTBot" in by["tech.robots.ai"]["fix"]["generated_content"]
    if "tech.sitemap.missing" in by:
        assert by["tech.sitemap.missing"]["fix"] is None      # unsupported -> omitted (null)


def test_knowledge_card_or_null(tmp_path):
    (tmp_path / "robots.txt").write_text("User-agent: GPTBot\nDisallow: /\n")
    out = prepare_project_for_ai(str(tmp_path))
    # every finding either carries a card dict or null; cards are only for real findings.
    for f in out["findings"]:
        assert f["knowledge"] is None or isinstance(f["knowledge"], dict)
    robots = next(f for f in out["findings"] if f["finding_id"] == "tech.robots.ai")
    assert isinstance(robots["knowledge"], dict)  # this finding has a card


def test_compact_findings_only_four_keys(tmp_path):
    out = prepare_project_for_ai(str(tmp_path))
    for f in out["findings"]:
        assert set(f) == _FINDING_KEYS  # nothing extra bloating the payload


def test_error_is_structured(tmp_path):
    out = prepare_project_for_ai(str(tmp_path / "does-not-exist"))
    assert out["findings"] == []
    assert out["framework"] is None and out["score"] is None
    assert "error" in out
    assert out["recommended_workflow"] == _RECOMMENDED_WORKFLOW
