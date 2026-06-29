"""Tests for deterministic single-finding fix generation (fixes.generate_fix)."""

from __future__ import annotations

from astova_engine.fixes import generate_fix

_KEYS = {
    "finding_id", "deterministic", "supported", "explanation",
    "generated_content", "target_type", "suggested_location", "verification_method",
}

URL = "https://example.com/pricing"


def _assert_shape(r: dict):
    assert set(r) == _KEYS, f"response keys drifted: {set(r) ^ _KEYS}"
    assert isinstance(r["deterministic"], bool)
    assert isinstance(r["supported"], bool)


def test_canonical_deterministic_fix():
    r = generate_fix("canonical", {"url": URL})
    _assert_shape(r)
    assert r["deterministic"] and r["supported"]
    assert r["target_type"] == "head_element"
    assert 'rel="canonical"' in r["generated_content"] and URL in r["generated_content"]


def test_onpage_canonical_alias_resolves():
    r = generate_fix("onpage.canonical", {"url": URL})
    assert r["supported"] and 'rel="canonical"' in r["generated_content"]


def test_viewport_needs_no_url():
    r = generate_fix("tech.viewport", {})
    _assert_shape(r)
    assert r["supported"] and "viewport" in r["generated_content"]
    assert r["target_type"] == "head_element"


def test_robots_fix_allows_ai_crawlers():
    for fid in ("tech.robots.missing", "tech.robots.ai"):
        r = generate_fix(fid, {"url": URL})
        assert r["supported"] and r["target_type"] == "file"
        assert "GPTBot" in r["generated_content"] and "robots.txt" in r["suggested_location"]


def test_llms_txt_fix():
    r = generate_fix("tech.llms_txt", {"url": URL})
    assert r["supported"] and r["target_type"] == "file"
    assert r["generated_content"].startswith("# ") and "llms.txt" in r["suggested_location"]


def test_schema_fix_from_url_only():
    r = generate_fix("schema.missing", {"url": URL})
    assert r["supported"]
    assert "Organization" in r["generated_content"] and "application/ld+json" in r["generated_content"]


def test_schema_fix_uses_html_when_given():
    html = '<html><head><meta property="og:image" content="https://x/logo.png"></head><body><h1>Acme Pricing</h1></body></html>'
    r = generate_fix("schema.missing", {"url": URL, "html": html})
    assert r["supported"] and "Acme Pricing" in r["generated_content"]


def test_faq_needs_html_with_pairs():
    # no html -> cannot build FAQPage, but it IS a deterministic-capable finding
    r = generate_fix("geo.faq", {"url": URL})
    assert r["deterministic"] and not r["supported"]
    assert "question" in r["explanation"].lower()
    # html with 2 Q&A pairs -> supported
    html = (
        "<body>"
        "<h2>What is it?</h2><p>It is a deterministic AI readiness audit engine for sites.</p>"
        "<h2>How much?</h2><p>There is a free single page scan with no card required at all.</p>"
        "</body>"
    )
    r2 = generate_fix("geo.faq", {"html": html})
    assert r2["supported"] and "FAQPage" in r2["generated_content"]


def test_missing_url_is_unsupported_with_reason():
    r = generate_fix("canonical", {})
    assert r["deterministic"] and not r["supported"] and "url" in r["explanation"].lower()


def test_unsupported_finding():
    r = generate_fix("geo.aeo", {"url": URL})  # ai-assisted, not deterministic
    _assert_shape(r)
    assert not r["deterministic"] and not r["supported"]
    assert r["generated_content"] is None


def test_unknown_finding():
    r = generate_fix("nope.nope", {"url": URL})
    _assert_shape(r)
    assert not r["deterministic"] and not r["supported"]
