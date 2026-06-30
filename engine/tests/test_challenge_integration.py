"""Integration tests: bot-challenge detection wired through scan_html + the MCP audit payload."""

from __future__ import annotations

import pytest

from astova_engine import scan_html

# A Cloudflare "Just a moment" interstitial: its own noindex meta, a challenge-platform script, ~0 words.
CHALLENGE_HTML = (
    '<!doctype html><html><head><title>Just a moment...</title>'
    '<meta name="robots" content="noindex,nofollow"></head><body>'
    '<script src="/cdn-cgi/challenge-platform/h/b/orchestrate/chl_page"></script>'
    "Enable JavaScript and cookies to continue</body></html>"
)
CHALLENGE_HEADERS = {"server": "cloudflare", "cf-ray": "8a1b2c3d", "x-robots-tag": "noindex"}

CLEAN_HTML = (
    '<!doctype html><html lang="en"><head><title>Acme - Pricing for teams</title>'
    '<meta name="description" content="Clear pricing, three plans, cancel anytime - everything a team needs.">'
    "</head><body><h1>Pricing</h1><p>Acme offers three plans starting free, then 12 dollars per seat.</p>"
    "</body></html>"
)

_ARTIFACTS = {"robots.noindex", "tech.x_robots_tag", "tech.index_conflict",
              "geo.js_rendered", "geo.no_content", "geo.thin_content", "geo.depth"}


def _challenge_report():
    return scan_html("https://mitel.com/", CHALLENGE_HTML, online=True,
                     status_code=403, headers=CHALLENGE_HEADERS)


# --------------------------------------------------------------------------- meta + finding

def test_challenge_meta_set():
    d = _challenge_report().to_dict()
    ch = d["meta"]["challenge"]
    assert ch["detected"] is True
    assert ch["vendor"] == "Cloudflare"
    assert ch["status"] == 403


def test_tech_challenge_finding():
    f = next(f for f in _challenge_report().findings if f.id == "tech.challenge")
    assert f.pillar.value == "technical"
    assert f.status.value == "fail"
    assert f.severity.value == "high"
    assert f.confidence.value == "verified"
    # evidence includes vendor, status and the matched marker
    assert "Cloudflare" in f.evidence and "403" in f.evidence and "matched marker" in f.evidence
    assert "bot/security challenge" in (f.recommendation or "")


def test_artifact_findings_removed():
    ids = {f.id for f in _challenge_report().findings}
    assert not (ids & _ARTIFACTS), ids & _ARTIFACTS
    assert "robots.noindex" not in ids  # the page HAS a noindex meta, but it's dropped as an artifact


def test_scorecard_marked_unreliable():
    sc = _challenge_report().scorecard
    assert sc is not None
    assert sc["unreliable"] is True
    assert sc["challenge"]["vendor"] == "Cloudflare"


# --------------------------------------------------------------------------- no false positive

def test_clean_page_has_no_challenge():
    d = scan_html("https://acme.com/pricing", CLEAN_HTML, online=True, status_code=200).to_dict()
    assert "challenge" not in d["meta"]
    assert not any(f["id"] == "tech.challenge" for f in d["findings"])
    assert not (d.get("scorecard") or {}).get("unreliable")


# --------------------------------------------------------------------------- MCP exposure

def test_mcp_audit_url_surfaces_challenge(monkeypatch):
    pytest.importorskip("mcp")
    import astova_engine.mcp_server as srv
    monkeypatch.setattr(srv, "scan", lambda url, fixes=False: _challenge_report())
    out = srv.audit_url("https://mitel.com/")
    assert out["unreliable"] is True
    assert out["challenge"]["vendor"] == "Cloudflare"
    assert "UNRELIABLE" in out["note"]


def test_mcp_scan_url_surfaces_challenge(monkeypatch):
    pytest.importorskip("mcp")
    import astova_engine.mcp_server as srv
    monkeypatch.setattr(srv, "scan", lambda url, fixes=False: _challenge_report())
    out = srv.scan_url("https://mitel.com/")
    assert out["meta"]["challenge"]["detected"] is True
    assert out["scorecard"]["unreliable"] is True
