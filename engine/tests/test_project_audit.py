"""Tests for project-directory auditing (scanner.scan_project).

scan_project must return the SAME Report shape a URL scan returns, reuse the existing finding ids
(no bespoke project.* ids), read repo files directly, and never assert deploy-only signals it
can't verify from source.
"""

from __future__ import annotations

import json

from astova_engine.scanner import (_DEPLOY_ONLY_FINDINGS, _HTML_DERIVED_FINDINGS, scan_project)

INDEX_HTML = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<title>Acme Pricing - simple plans for teams</title>
<meta name="description" content="Acme pricing: three clear plans, no hidden fees, cancel anytime. Pick the tier that fits your team and start in minutes.">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="canonical" href="https://project.local/">
<meta property="og:title" content="Acme Pricing">
<meta property="og:description" content="Three clear plans for teams.">
<meta property="og:image" content="https://acme.example/og.png">
<meta property="og:type" content="website">
<script type="application/ld+json">{"@context":"https://schema.org","@type":"Organization","name":"Acme"}</script>
</head><body>
<h1>Acme Pricing</h1>
<p>Acme offers three plans. The Starter plan is free for one project. The Team plan is 12 dollars per seat per month and adds unlimited projects, priority support, and SSO.</p>
<h2>Frequently asked questions</h2>
<h3>How much does Acme cost?</h3><p>Starter is free; Team is 12 dollars per seat per month billed annually.</p>
<h3>Can I cancel anytime?</h3><p>Yes, you can cancel at any time from the billing settings page with no fee.</p>
</body></html>
"""

ROBOTS_ALLOW = "User-agent: *\nAllow: /\nSitemap: https://acme.example/sitemap.xml\n"
ROBOTS_BLOCK_AI = "User-agent: GPTBot\nDisallow: /\n\nUser-agent: *\nAllow: /\n"
SITEMAP = '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://acme.example/</loc></url></urlset>'
LLMS = "# Acme\n> Pricing for teams.\n"


def _static_project(tmp_path, *, robots=ROBOTS_ALLOW, llms=LLMS, sitemap=SITEMAP, html=INDEX_HTML):
    if html is not None:
        (tmp_path / "index.html").write_text(html)
    if robots is not None:
        (tmp_path / "robots.txt").write_text(robots)
    if llms is not None:
        (tmp_path / "llms.txt").write_text(llms)
    if sitemap is not None:
        (tmp_path / "sitemap.xml").write_text(sitemap)
    return tmp_path


def _ids(report):
    return {f.id for f in report.findings}


# --------------------------------------------------------------------------- shape / parity

def test_returns_standard_report_shape(tmp_path):
    report = scan_project(str(_static_project(tmp_path)))
    d = report.to_dict()
    assert set(d) >= {"schema_version", "url", "overall_score", "pillar_scores", "findings",
                      "scorecard", "meta"}
    assert d["meta"]["scan_type"] == "project"
    assert d["scorecard"] is not None
    assert isinstance(d["overall_score"], int) and 0 <= d["overall_score"] <= 100
    # JSON-serialisable like every other report (downstream tools consume it unchanged).
    json.dumps(d)


def test_reuses_existing_finding_ids_no_project_prefix(tmp_path):
    report = scan_project(str(_static_project(tmp_path)))
    ids = _ids(report)
    assert not any(i.startswith("project.") for i in ids), ids
    # canonical url-audit ids are present
    assert "tech.robots.ok" in ids
    assert "canonical" in ids and "title.length" in ids


# --------------------------------------------------------------------------- file-based checks

def test_robots_allow_passes_ai_access(tmp_path):
    report = scan_project(str(_static_project(tmp_path)))
    ai = next(f for f in report.findings if f.id == "tech.robots.ai")
    assert ai.status.value == "pass"


def test_robots_blocking_ai_is_flagged(tmp_path):
    report = scan_project(str(_static_project(tmp_path, robots=ROBOTS_BLOCK_AI)))
    ai = next(f for f in report.findings if f.id == "tech.robots.ai")
    assert ai.status.value == "warn" and "GPTBot" in (ai.value or [])


def test_missing_files_flagged(tmp_path):
    report = scan_project(str(_static_project(tmp_path, robots=None, llms=None, sitemap=None)))
    ids = _ids(report)
    assert "tech.robots.missing" in ids
    assert "tech.sitemap.missing" in ids
    meta_files = report.meta["files"]
    assert meta_files["robots_txt"] is False and meta_files["sitemap_xml"] is False


def test_llms_present_detected(tmp_path):
    report = scan_project(str(_static_project(tmp_path)))
    llms = next(f for f in report.findings if f.id == "tech.llms_txt")
    assert llms.value is True


# --------------------------------------------------------------------------- accuracy principle

def test_deploy_only_findings_are_omitted(tmp_path):
    report = scan_project(str(_static_project(tmp_path)))
    ids = _ids(report)
    assert not (ids & _DEPLOY_ONLY_FINDINGS), "must not assert HTTPS/TLS/status/etc. from source"


def test_html_derived_findings_dropped_when_no_html(tmp_path):
    # Next.js project, no static index.html -> on-page/GEO + viewport not asserted.
    (tmp_path / "next.config.js").write_text("module.exports = {}\n")
    (tmp_path / "public").mkdir()
    (tmp_path / "public" / "robots.txt").write_text(ROBOTS_ALLOW)
    report = scan_project(str(tmp_path))
    ids = _ids(report)
    assert report.meta["html_analyzed"] is False
    assert not (ids & _HTML_DERIVED_FINDINGS)
    assert not any(i.startswith("title.") or i.startswith("geo.") for i in ids)
    # the file-based technical checks still ran
    assert "tech.robots.ok" in ids


# --------------------------------------------------------------------------- framework detection

def test_detects_nextjs(tmp_path):
    (tmp_path / "next.config.js").write_text("module.exports = {}\n")
    report = scan_project(str(tmp_path))
    assert report.meta["framework"] == "nextjs" and report.meta["public_dir"] == "public"


def test_detects_wordpress(tmp_path):
    (tmp_path / "wp-config.php").write_text("<?php // wp\n")
    report = scan_project(str(tmp_path))
    assert report.meta["framework"] == "wordpress" and report.meta["public_dir"] == "."


def test_detects_static_default(tmp_path):
    report = scan_project(str(_static_project(tmp_path)))
    assert report.meta["framework"] == "static"


def test_explicit_framework_override(tmp_path):
    # No markers, but caller declares astro -> public dir honoured.
    (tmp_path / "public").mkdir()
    (tmp_path / "public" / "robots.txt").write_text(ROBOTS_ALLOW)
    report = scan_project(str(tmp_path), framework="astro")
    assert report.meta["framework"] == "astro" and report.meta["public_dir"] == "public"
    assert "tech.robots.ok" in _ids(report)  # read from public/robots.txt


# --------------------------------------------------------------------------- security headers

def test_security_headers_from_next_config(tmp_path):
    (tmp_path / "next.config.js").write_text(
        "module.exports = { async headers() { return [{ source: '/(.*)', headers: ["
        "{ key: 'Content-Security-Policy', value: \"default-src 'self'\" },"
        "{ key: 'X-Frame-Options', value: 'DENY' },"
        "{ key: 'X-Content-Type-Options', value: 'nosniff' },"
        "{ key: 'Referrer-Policy', value: 'no-referrer' }] }] } }\n")
    report = scan_project(str(tmp_path))
    sec = next(f for f in report.findings if f.id == "tech.security_headers")
    assert sec.status.value == "pass"  # >=3 configured
    assert set(report.meta["security_headers_configured"]) >= {
        "content-security-policy", "x-frame-options", "x-content-type-options", "referrer-policy"}


def test_security_headers_warn_when_none(tmp_path):
    report = scan_project(str(_static_project(tmp_path)))
    sec = next(f for f in report.findings if f.id == "tech.security_headers")
    assert sec.status.value == "warn"
    assert report.meta["security_headers_configured"] == []


def test_security_headers_from_headers_file(tmp_path):
    _static_project(tmp_path)
    (tmp_path / "_headers").write_text(
        "/*\n  X-Frame-Options: DENY\n  X-Content-Type-Options: nosniff\n"
        "  Content-Security-Policy: default-src 'self'\n")
    report = scan_project(str(tmp_path))
    assert set(report.meta["security_headers_configured"]) >= {
        "x-frame-options", "x-content-type-options", "content-security-policy"}


# --------------------------------------------------------------------------- errors

def test_not_a_directory(tmp_path):
    report = scan_project(str(tmp_path / "does-not-exist"))
    assert report.meta["scan_type"] == "project"
    assert "Not a directory" in report.meta["error"]
    assert report.findings == []
