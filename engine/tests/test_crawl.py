"""Tests for the multi-page crawl: URL helpers, site-wide findings, and a fully
monkeypatched mini-crawl (no network)."""

from __future__ import annotations

import astova_engine.crawl as crawl_mod
from astova_engine.crawl import (
    _dupes,
    _internal_links,
    _is_asset,
    _norm,
    _site_findings,
    crawl,
)
from astova_engine.models import PageSummary, Status
from astova_engine.util import make_soup


# --- URL helpers -------------------------------------------------------------------------

def test_norm_strips_fragment_and_trailing_slash():
    assert _norm("https://EX.com/a/#top") == "https://ex.com/a"
    assert _norm("https://ex.com/") == "https://ex.com/"
    assert _norm("https://ex.com/a/?q=1") == "https://ex.com/a?q=1"


def test_is_asset():
    assert _is_asset("/files/report.pdf")
    assert _is_asset("/app.js")
    assert not _is_asset("/about")
    assert not _is_asset("/blog/post-1")


def test_internal_links_same_host_only_no_assets():
    html = """
      <a href="/about">a</a>
      <a href="https://other.com/x">ext</a>
      <a href="/doc.pdf">asset</a>
      <a href="mailto:x@y.com">mail</a>
      <a href="#section">frag</a>
      <a href="https://ex.com/contact">abs same host</a>
    """
    links = _internal_links(make_soup(html), "https://ex.com/", "ex.com")
    assert "https://ex.com/about" in links
    assert "https://ex.com/contact" in links
    assert all("other.com" not in u and ".pdf" not in u for u in links)
    assert len(links) == 2


def test_dupes():
    assert _dupes(["Home", "Home", "About", ""]) == [("Home", 2)]
    assert _dupes(["a", "b", "c"]) == []


# --- site-wide findings ------------------------------------------------------------------

def _page(url, score=90, title="T", meta="M", words=500):
    return PageSummary(url=url, status_code=200, overall_score=score,
                       pillar_scores={}, title=title, meta_description=meta, word_count=words)


def test_broken_links_finding():
    pages = [_page("https://ex.com/")]
    broken = [{"url": "https://ex.com/gone", "status": 404, "referrers": ["https://ex.com/"]}]
    out = {f.id: f for f in _site_findings(pages, broken, set(), set())}
    assert "site.broken_links" in out
    assert out["site.broken_links"].status == Status.FAIL
    assert out["site.broken_links"].value == 1
    assert "gone" in out["site.broken_links"].evidence


def test_duplicate_titles_and_meta():
    pages = [_page("https://ex.com/a", title="Home", meta="same"),
             _page("https://ex.com/b", title="Home", meta="same"),
             _page("https://ex.com/c", title="Unique", meta="other")]
    out = {f.id: f for f in _site_findings(pages, [], set(), set())}
    assert out["site.duplicate_titles"].value == 1
    assert out["site.duplicate_meta"].value == 1


def test_thin_pages_warn_vs_info():
    # 2 of 3 thin → over the 30% share → WARN
    thin_heavy = [_page("https://ex.com/a", words=100), _page("https://ex.com/b", words=50),
                  _page("https://ex.com/c", words=900)]
    out = {f.id: f for f in _site_findings(thin_heavy, [], set(), set())}
    assert out["site.thin_pages"].status == Status.WARN
    assert out["site.thin_pages"].value == 2


def test_sitemap_coverage_missing_and_orphans():
    pages = [_page("https://ex.com/a"), _page("https://ex.com/b")]
    # sitemap lists /a and /orphan; /b is crawled but not in sitemap; /orphan is never linked
    sitemap = {"https://ex.com/a", "https://ex.com/orphan"}
    discovered = {"https://ex.com/a", "https://ex.com/b"}
    out = {f.id: f for f in _site_findings(pages, [], discovered, sitemap)}
    cov = out["site.sitemap_coverage"]
    assert cov.value == {"missing_from_sitemap": 1, "orphans": 1}


def test_no_findings_for_clean_site():
    pages = [_page("https://ex.com/a", title="A", meta="ma", words=600),
             _page("https://ex.com/b", title="B", meta="mb", words=700)]
    assert _site_findings(pages, [], set(), set()) == []


# --- end-to-end mini-crawl (monkeypatched fetch) -----------------------------------------

class _FakeRes:
    def __init__(self, url, html="", status=200, error=None):
        self.url = url
        self.final_url = url
        self.status_code = status
        self.html = html
        self.headers = {}
        self.redirected = False
        self.redirect_chain = []
        self.rendered_html = None
        self.error = error


# A tiny 3-page site: home links to /a and /gone; /a links to /b; /gone 404s.
# Keys are the normalized (_norm) URL form so the fake fetch can look them up directly.
_SITE = {
    "https://ex.com/": _FakeRes("https://ex.com/",
        "<title>Home</title><body>" + "word " * 400
        + '<a href="/a">a</a><a href="/gone">x</a></body>'),
    "https://ex.com/a": _FakeRes("https://ex.com/a",
        "<title>Home</title><body>" + "word " * 400 + '<a href="/b">b</a></body>'),  # dup title
    "https://ex.com/b": _FakeRes("https://ex.com/b", "<title>B</title><body>" + "word " * 20 + "</body>"),  # thin
    "https://ex.com/gone": _FakeRes("https://ex.com/gone", "", status=404),
}


def test_mini_crawl(monkeypatch):
    monkeypatch.setattr(crawl_mod, "fetch", lambda url: _SITE.get(_norm(url), _FakeRes(url, "", status=404)))
    monkeypatch.setattr(crawl_mod, "_sitemap_locs", lambda *a, **k: set())

    site = crawl("https://ex.com", delay=0)

    assert site.meta["pages_crawled"] == 3          # home, /a, /b
    assert site.meta["broken"] == 1                 # /gone (404)
    ids = {f.id for f in site.site_findings}
    assert "site.broken_links" in ids
    assert "site.duplicate_titles" in ids           # Home appears twice
    assert "site.thin_pages" in ids                 # /b is ~20 words
    assert 0 <= site.overall_score <= 100
