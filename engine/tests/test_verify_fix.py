"""Tests for deterministic fix verification (verify.verify_fix).

scan / scan_project are monkeypatched to offline scans so no network runs - verify_fix must reuse
them, never duplicate audit logic, and apply the gone / pass-or-info / warn-or-fail rule exactly.
"""

from __future__ import annotations

import astova_engine.verify as verify
from astova_engine import scan_html
from astova_engine.models import Report

# Page with a clean title + canonical + schema (so those findings pass / are absent-as-missing).
GOOD_HTML = """<!doctype html><html lang="en"><head>
<title>How to brew pour-over coffee: a complete beginner guide</title>
<meta name="description" content="A clear, complete guide to brewing pour-over coffee at home, with
ratios, timings and the gear you need - roughly 120 to 160 characters of genuine summary text here.">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="canonical" href="https://example.com/coffee">
<script type="application/ld+json">{"@context":"https://schema.org","@type":"Article","headline":"Pour-over"}</script>
</head><body><h1>Pour-over coffee</h1>
<p>Pour-over coffee uses a 1 to 16 ratio of grounds to water brewed over about three minutes total.</p>
</body></html>"""

# Page missing title + schema + viewport + canonical (those findings fire as fail/warn).
BAD_HTML = "<!doctype html><html><head></head><body><p>hello there friend</p></body></html>"

_KEYS = {"target", "target_type", "finding_id", "fixed", "current_status", "current_severity",
         "evidence", "score_after", "confidence", "explanation", "next_step"}


def _patch_url(monkeypatch, html):
    monkeypatch.setattr(verify, "scan", lambda url: scan_html(url, html, online=False))


def _assert_shape(r):
    assert _KEYS <= set(r)
    assert r["confidence"] == "verified"


# --------------------------------------------------------------------------- the resolution rule

def test_missing_finding_gone_means_fixed(monkeypatch):
    # GOOD_HTML has a <title>, so the "title.missing" finding does not fire at all -> fixed.
    _patch_url(monkeypatch, GOOD_HTML)
    r = verify.verify_fix("https://example.com/coffee", "title.missing", "url")
    _assert_shape(r)
    assert r["fixed"] is True
    assert r["current_status"] is None
    assert "no longer present" in r["explanation"].lower()
    assert isinstance(r["score_after"], int)


def test_present_pass_means_fixed(monkeypatch):
    # canonical is present and self-referential -> the "canonical" finding exists with status pass.
    _patch_url(monkeypatch, GOOD_HTML)
    r = verify.verify_fix("https://example.com/coffee", "canonical", "url")
    assert r["fixed"] is True
    assert r["current_status"] in ("pass", "info")


def test_still_failing_means_not_fixed(monkeypatch):
    _patch_url(monkeypatch, BAD_HTML)
    r = verify.verify_fix("https://example.com/coffee", "title.missing", "url")
    _assert_shape(r)
    assert r["fixed"] is False
    assert r["current_status"] in ("warn", "fail")
    assert "generate_fix('title.missing')" in r["next_step"]


def test_schema_missing_not_fixed_on_bad_page(monkeypatch):
    _patch_url(monkeypatch, BAD_HTML)
    r = verify.verify_fix("https://example.com", "schema.missing", "url")
    assert r["fixed"] is False and r["current_status"] in ("warn", "fail")


def test_canonical_alias_resolves(monkeypatch):
    # onpage.canonical must resolve to the canonical finding, same as generate_fix.
    _patch_url(monkeypatch, GOOD_HTML)
    r = verify.verify_fix("https://example.com/coffee", "onpage.canonical", "url")
    assert r["finding_id"] == "onpage.canonical"  # echoed verbatim
    assert r["fixed"] is True


# --------------------------------------------------------------------------- project targets

def test_project_target_reuses_scan_project(tmp_path):
    (tmp_path / "robots.txt").write_text("User-agent: *\nAllow: /\n")
    (tmp_path / "llms.txt").write_text("# Site\n> hi\n")
    r = verify.verify_fix(str(tmp_path), "tech.llms_txt", "project")
    _assert_shape(r)
    assert r["target_type"] == "project"
    assert r["fixed"] is True  # llms.txt present -> tech.llms_txt is pass/info


def test_project_missing_robots_not_fixed(tmp_path):
    # empty dir -> robots.txt missing -> tech.robots.missing fires as warn.
    r = verify.verify_fix(str(tmp_path), "tech.robots.missing", "project")
    assert r["fixed"] is False and r["current_status"] in ("warn", "fail")


# --------------------------------------------------------------------------- errors

def test_scan_failure_is_structured_error(monkeypatch):
    bad = Report(url="https://x.test", meta={"error": "could not resolve host"})
    monkeypatch.setattr(verify, "scan", lambda url: bad)
    r = verify.verify_fix("https://x.test", "schema.missing", "url")
    _assert_shape(r)
    assert r["fixed"] is False
    assert r["current_status"] == "error"
    assert r["error"] == "could not resolve host"
    assert r["score_after"] is None


def test_invalid_target_type():
    r = verify.verify_fix("https://x.test", "schema.missing", "nonsense")
    assert r["fixed"] is False and r["current_status"] == "error"
    assert r["error"] == "invalid_target_type"


def test_project_bad_path_is_structured_error():
    r = verify.verify_fix("/no/such/dir/anywhere", "tech.llms_txt", "project")
    assert r["fixed"] is False and r["current_status"] == "error"
    assert "Not a directory" in r["error"]
