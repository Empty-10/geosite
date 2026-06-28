"""Tests for the MCP server tool payloads. Skipped unless the [mcp] extra is installed.
`scan` is monkeypatched to an offline scan_html so no network runs."""

from __future__ import annotations

import pytest

pytest.importorskip("mcp")

from damask_engine import scan_html  # noqa: E402
from damask_engine.models import Report  # noqa: E402
import damask_engine.mcp_server as srv  # noqa: E402

HTML = """<!doctype html><html lang="en"><head>
<title>How to brew pour-over coffee: a complete guide for beginners</title>
<meta name="description" content="A clear, complete guide to brewing pour-over coffee at home,
with ratios, timings and the gear you need — about 120 to 160 characters of useful summary.">
</head><body><h1>Pour-over coffee</h1>
<p>Pour-over coffee uses a 1 to 16 ratio of grounds to water brewed over three minutes.</p>
</body></html>"""


def test_audit_payload_shape(monkeypatch):
    monkeypatch.setattr(srv, "scan", lambda url, fixes=False: scan_html(url, HTML, online=False))
    out = srv.audit_url("https://example.com/coffee")
    assert isinstance(out["ai_retrievability"], (int, float))
    assert len(out["rows"]) == 20
    assert out["confidence"] == "verified"
    assert "overlay" in out and "categories" in out
    assert isinstance(out["top_issues"], list)


def test_audit_payload_surfaces_error(monkeypatch):
    bad = Report(url="https://x.test", meta={"error": "could not resolve host"})
    monkeypatch.setattr(srv, "scan", lambda url, fixes=False: bad)
    out = srv.audit_url("https://x.test")
    assert out["error"] == "could not resolve host"


def test_scan_url_returns_full_report(monkeypatch):
    monkeypatch.setattr(srv, "scan", lambda url, fixes=False: scan_html(url, HTML, online=False))
    out = srv.scan_url("https://example.com/coffee")
    assert out["schema_version"] and out["findings"] and out["scorecard"]


def test_tools_are_registered():
    # The two tools must be discoverable by an MCP client.
    import anyio

    tools = anyio.run(srv.mcp.list_tools)
    names = {t.name for t in tools}
    assert {"audit_url", "scan_url", "fix_plan", "audit_project"} <= names


def test_fix_plan_is_agent_actionable(monkeypatch):
    # pass fixes through so deterministic artifacts are generated
    monkeypatch.setattr(srv, "scan", lambda url, fixes=False: scan_html(url, HTML, online=False, fixes=fixes))
    out = srv.fix_plan("https://example.com/coffee")
    assert isinstance(out["ai_retrievability"], (int, float))
    assert isinstance(out["fixes"], list) and out["fixes"]
    for fx in out["fixes"]:
        assert {"finding_id", "title", "action", "target", "instruction", "source"} <= set(fx)
        assert fx["source"] in ("deterministic", "advisory")


def test_fix_plan_surfaces_error(monkeypatch):
    bad = Report(url="https://x.test", meta={"error": "could not resolve host"})
    monkeypatch.setattr(srv, "scan", lambda url, fixes=False: bad)
    assert srv.fix_plan("https://x.test")["error"] == "could not resolve host"


def test_audit_project_reads_files_and_targets_paths(tmp_path):
    # a Next.js-shaped project with an AI-blocking robots.txt and no llms.txt
    (tmp_path / "next.config.js").write_text("module.exports = {}")
    pub = tmp_path / "public"
    pub.mkdir()
    (pub / "robots.txt").write_text("User-agent: GPTBot\nDisallow: /\n")

    out = srv.audit_project(str(tmp_path))
    assert out["project"]["framework"] == "nextjs"
    assert out["file_status"]["robots"] == "blocks_ai"
    assert out["file_status"]["llms"] == "missing"
    by = {f["finding_id"]: f for f in out["file_fixes"]}
    assert by["project.llms_missing"]["target"] == "public/llms.txt"
    assert "page_audit" not in out  # no base_url given


def test_audit_project_with_base_url_includes_page_audit(tmp_path, monkeypatch):
    (tmp_path / "index.html").write_text("<html></html>")
    monkeypatch.setattr(srv, "scan", lambda url, fixes=False: scan_html(url, HTML, online=False, fixes=fixes))
    out = srv.audit_project(str(tmp_path), base_url="http://localhost:3000")
    assert "page_audit" in out
    assert isinstance(out["page_audit"]["ai_retrievability"], (int, float))
    assert isinstance(out["page_audit"]["fixes"], list)


def test_audit_project_bad_path():
    assert "error" in srv.audit_project("/no/such/dir/here")
