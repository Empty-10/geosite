"""Tests for the Markdown action-plan export (export.loop_to_markdown + `astova export`)."""

from __future__ import annotations

import astova_engine.cli as cli
from astova_engine.export import loop_to_markdown

# A representative ai_ready_loop response (shape matches ai_ready.ai_ready_loop output).
RESP = {
    "target": "https://example.com",
    "target_type": "url",
    "score": 72,
    "confidence": "verified",
    "summary": "2 actionable...",
    "findings_count": 9,
    "actionable_count": 2,
    "deterministic_fix_count": 1,
    "ai_assisted_count": 0,
    "manual_count": 1,
    "items": [
        {
            "finding_id": "schema.missing", "title": "Structured data (JSON-LD)",
            "status": "fail", "severity": "high", "confidence": "verified",
            "evidence": "no JSON-LD on the page",
            "recommendation": "Add Organization + WebPage JSON-LD.",
            "knowledge": {"why_it_matters": "Schema makes the page machine-readable.",
                          "can_astova_generate": "deterministic", "how_to_fix": "Add a script tag."},
            "fix": {"finding_id": "schema.missing", "supported": True, "deterministic": True,
                    "suggested_location": "page <head>"},
            "verify": {"tool": "verify_fix", "target": "https://example.com",
                       "target_type": "url", "finding_id": "schema.missing"},
            "agent_next_step": "Apply the generated fix to page <head>, then verify.",
        },
        {
            "finding_id": "geo.thin_content", "title": "Thin content",
            "status": "warn", "severity": "medium", "confidence": "verified",
            "evidence": None, "recommendation": "Expand the page.",
            "knowledge": None,
            "fix": {"finding_id": "geo.thin_content", "supported": False, "deterministic": False},
            "verify": {"tool": "verify_fix", "target": "https://example.com",
                       "target_type": "url", "finding_id": "geo.thin_content"},
            "agent_next_step": "Draft more content, then verify.",
        },
    ],
}

_AT = "2026-06-29T00:00:00+00:00"


def test_header_and_summary():
    md = loop_to_markdown(RESP, generated_at=_AT)
    assert md.startswith("# Astova AI Readiness Action Plan")
    assert "Target: https://example.com" in md
    assert "Score: 72/100" in md
    assert f"Generated: {_AT}" in md
    assert "## Summary" in md
    assert "* Total actionable findings: 2" in md
    assert "* Deterministic fixes: 1" in md
    assert "* AI-assisted fixes: 0" in md
    assert "* Manual review items: 1" in md


def test_per_item_fields_present():
    md = loop_to_markdown(RESP, generated_at=_AT)
    assert "## Top Actions" in md
    assert "### 1. Structured data (JSON-LD)" in md
    for label in ("Finding ID:", "Severity:", "Status:", "Evidence:", "Why it matters:",
                  "Recommended fix:", "Can Astova generate fix:", "Agent next step:", "Verification:"):
        assert label in md, label
    # values from the card + fix
    assert "Why it matters: Schema makes the page machine-readable." in md
    assert "Can Astova generate fix: yes (ready now via generate_fix)" in md
    assert '`verify_fix("https://example.com", "schema.missing", "url")`' in md


def test_knowledge_null_item_renders():
    md = loop_to_markdown(RESP, generated_at=_AT)
    assert "### 2. Thin content" in md
    assert "Why it matters: n/a" in md           # no card -> n/a
    assert "Evidence: n/a" in md                 # evidence None -> n/a
    assert "Can Astova generate fix: no (manual)" in md


def test_run_after_fixing_footer():
    md = loop_to_markdown(RESP, generated_at=_AT)
    assert "Run after fixing:" in md
    assert "`astova loop https://example.com`" in md


def test_error_response():
    md = loop_to_markdown({"target": "https://x.test", "error": "could not resolve host"})
    assert "# Astova AI Readiness Action Plan" in md
    assert "Could not generate a plan: could not resolve host" in md


def test_empty_items():
    resp = {**RESP, "actionable_count": 0, "deterministic_fix_count": 0, "manual_count": 0, "items": []}
    md = loop_to_markdown(resp, generated_at=_AT)
    assert "Nothing to fix" in md


def test_deterministic_output():
    a = loop_to_markdown(RESP, generated_at=_AT)
    b = loop_to_markdown(RESP, generated_at=_AT)
    assert a == b


# --------------------------------------------------------------------------- CLI

def test_cli_export_stdout(tmp_path, capsys):
    code = cli._cmd_export([str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 0
    assert "# Astova AI Readiness Action Plan" in out
    assert "## Summary" in out


def test_cli_export_writes_file(tmp_path, capsys):
    out_file = tmp_path / "plan.md"
    code = cli._cmd_export([str(tmp_path), "--output", str(out_file)])
    msg = capsys.readouterr().out
    assert code == 0
    assert "Wrote AI Readiness action plan to" in msg
    text = out_file.read_text()
    assert text.startswith("# Astova AI Readiness Action Plan")
    assert "Run after fixing:" in text


def test_cli_export_max_items(tmp_path):
    out_file = tmp_path / "plan.md"
    cli._cmd_export([str(tmp_path), "--output", str(out_file), "--max-items", "1"])
    text = out_file.read_text()
    assert text.count("### ") <= 1  # at most one item section


def test_cli_export_error_exit_1(monkeypatch, capsys):
    import astova_engine.ai_ready as ai_ready
    from astova_engine.models import Report
    bad = Report(url="https://x.test", meta={"error": "could not resolve host"})
    monkeypatch.setattr(ai_ready, "scan", lambda url: bad)
    code = cli._cmd_export(["https://x.test"])
    out = capsys.readouterr().out
    assert code == 1
    assert "Could not generate a plan" in out
