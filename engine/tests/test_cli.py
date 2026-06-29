"""Tests for the astova CLI subcommands (check / loop).

Network is avoided: URL scans are monkeypatched to offline scan_html; project scans run for real on
a tmp_path directory (the project scanner reads local files, no network).
"""

from __future__ import annotations

import json

import astova_engine.cli as cli
from astova_engine import scan_html
from astova_engine.models import Report

HTML = """<!doctype html><html><head></head><body><p>thin page, nothing useful here at all.</p></body></html>"""


# --------------------------------------------------------------------------- target resolution

def test_resolve_url_scheme():
    assert cli._resolve_target("https://example.com")[0] == "url"
    assert cli._resolve_target("http://example.com/x") == ("url", "http://example.com/x")


def test_resolve_bare_host_becomes_url():
    assert cli._resolve_target("example.com") == ("url", "https://example.com")


def test_resolve_existing_dir_is_project(tmp_path):
    kind, norm = cli._resolve_target(str(tmp_path))
    assert kind == "project" and norm == str(tmp_path)


def test_resolve_pathlike_is_project():
    assert cli._resolve_target("./my-app")[0] == "project"
    assert cli._resolve_target("/srv/site")[0] == "project"


# --------------------------------------------------------------------------- check

def test_check_url_human(monkeypatch, capsys):
    monkeypatch.setattr(cli, "scan", lambda url: scan_html(url, HTML, online=False))
    code = cli._cmd_check(["https://example.com"])
    out = capsys.readouterr().out
    assert code == 0
    assert "astova scan" in out and "overall:" in out


def test_check_url_json(monkeypatch, capsys):
    monkeypatch.setattr(cli, "scan", lambda url: scan_html(url, HTML, online=False))
    code = cli._cmd_check(["https://example.com", "--json"])
    out = capsys.readouterr().out
    assert code == 0
    d = json.loads(out)
    assert d["url"] == "https://example.com" and "findings" in d and "scorecard" in d


def test_check_project_human(tmp_path, capsys):
    (tmp_path / "robots.txt").write_text("User-agent: *\nAllow: /\n")
    code = cli._cmd_check([str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 0
    assert "project audit" in out and "framework:" in out


def test_check_project_json(tmp_path, capsys):
    code = cli._cmd_check([str(tmp_path), "--json"])
    d = json.loads(capsys.readouterr().out)
    assert d["meta"]["scan_type"] == "project"
    assert code == 0


def test_check_scan_error_exit_1(monkeypatch, capsys):
    bad = Report(url="https://x.test", meta={"error": "could not resolve host"})
    monkeypatch.setattr(cli, "scan", lambda url: bad)
    code = cli._cmd_check(["https://x.test"])
    out = capsys.readouterr().out
    assert code == 1 and "Could not scan" in out


# --------------------------------------------------------------------------- loop

def test_loop_project_human(tmp_path, capsys):
    # empty project -> robots/sitemap missing -> actionable items present
    code = cli._cmd_loop([str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 0
    assert "ai-ready loop" in out and "actionable" in out
    assert "tech.robots.missing" in out


def test_loop_project_json(tmp_path, capsys):
    code = cli._cmd_loop([str(tmp_path), "--json"])
    resp = json.loads(capsys.readouterr().out)
    assert code == 0
    assert resp["target_type"] == "project"
    assert {"items", "actionable_count", "deterministic_fix_count"} <= set(resp)


def test_loop_max_items(tmp_path, capsys):
    code = cli._cmd_loop([str(tmp_path), "--json", "--max-items", "1"])
    resp = json.loads(capsys.readouterr().out)
    assert code == 0 and len(resp["items"]) <= 1


def test_loop_url(monkeypatch, capsys):
    import astova_engine.ai_ready as ai_ready
    monkeypatch.setattr(ai_ready, "scan", lambda url: scan_html(url, HTML, online=False))
    code = cli._cmd_loop(["https://example.com"])
    out = capsys.readouterr().out
    assert code == 0
    assert "ai-ready loop" in out and "(url)" in out


def test_loop_scan_error_exit_1(monkeypatch, capsys):
    import astova_engine.ai_ready as ai_ready
    bad = Report(url="https://x.test", meta={"error": "could not resolve host"})
    monkeypatch.setattr(ai_ready, "scan", lambda url: bad)
    code = cli._cmd_loop(["https://x.test"])
    out = capsys.readouterr().out
    assert code == 1 and "Could not scan" in out
