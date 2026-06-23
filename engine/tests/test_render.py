"""Tests for smart auto-render: the JS-shell detector and the Cloudflare render fallback.
Offline — no network or credentials."""

from __future__ import annotations

from damask_engine.fetch import render_dom_cloudflare
from damask_engine.scanner import _looks_like_js_shell


def test_shell_detected_for_spa_mount():
    assert _looks_like_js_shell('<html><body><div id="root"></div><script src="app.js"></script></body></html>')


def test_shell_detected_for_near_empty_body():
    assert _looks_like_js_shell("<html><body></body></html>")


def test_not_a_shell_for_content_page():
    html = "<html><body><h1>Guide</h1><p>" + ("word " * 200) + "</p></body></html>"
    assert not _looks_like_js_shell(html)


def test_thin_static_page_without_spa_markers_is_not_a_shell():
    # ~30 words, no SPA mount → a thin static page, not a JS shell (don't waste a render on it)
    html = "<html><body><p>" + ("word " * 30) + "</p></body></html>"
    assert not _looks_like_js_shell(html)


def test_cloudflare_render_returns_none_without_creds(monkeypatch):
    monkeypatch.delenv("CF_ACCOUNT_ID", raising=False)
    monkeypatch.delenv("CF_API_TOKEN", raising=False)
    # No creds → returns None before any network call (graceful fallback to raw HTML).
    assert render_dom_cloudflare("https://example.com") is None
