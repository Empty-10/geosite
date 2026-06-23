"""Fixture tests for the technical module — robots.txt / sitemap.xml parsing, redirect and
TLS findings. All offline: the module is pure, so we feed it text and a NetInputs."""

from __future__ import annotations

from damask_engine import scan_html
from damask_engine.models import Status
from damask_engine.modules.technical import (
    NetInputs,
    SITEMAP_STALE_DAYS,
    analyze,
    parse_robots,
    parse_sitemap,
)
from damask_engine.util import make_soup

HTML = "<html><head><meta name='viewport' content='width=device-width'></head><body><h1>Hi</h1></body></html>"


def _run(net: NetInputs):
    return {f.id: f for f in analyze(make_soup(HTML), "https://example.com/", 200, {}, net=net)}


# ------------------------------------------------------------------ parse_robots (pure)

ROBOTS = """
# example
User-agent: *
Disallow: /private

User-agent: GPTBot
User-agent: ClaudeBot
Disallow: /

Sitemap: https://example.com/sitemap.xml
"""


def test_parse_robots_groups_and_sitemaps():
    info = parse_robots(ROBOTS)
    assert info.groups["*"] == ["/private"]
    # Two consecutive User-agent lines share one rule group.
    assert info.blocks_root("GPTBot")
    assert info.blocks_root("claudebot")
    assert not info.blocks_root("PerplexityBot")  # falls back to *, which only blocks /private
    assert info.sitemaps == ["https://example.com/sitemap.xml"]


def test_robots_findings_flag_blocked_ai_crawlers():
    ids = _run(NetInputs(robots_status=200, robots_txt=ROBOTS))
    assert ids["tech.robots.ok"].status == Status.PASS
    ai = ids["tech.robots.ai"]
    assert ai.status == Status.WARN
    assert set(ai.value) == {"GPTBot", "ClaudeBot"}
    assert ids["tech.robots.sitemap"].status == Status.PASS


def test_robots_missing():
    ids = _run(NetInputs(robots_status=404, robots_txt=""))
    assert ids["tech.robots.missing"].status == Status.WARN


# ------------------------------------------------------------------ parse_sitemap (pure)

URLSET = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/a</loc><lastmod>2026-06-01</lastmod></url>
  <url><loc>https://example.com/b</loc><lastmod>2026-05-20</lastmod></url>
</urlset>"""

INDEX = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://example.com/sitemap-1.xml</loc></sitemap>
  <sitemap><loc>https://example.com/sitemap-2.xml</loc></sitemap>
</sitemapindex>"""


def test_parse_sitemap_urlset_and_index():
    u = parse_sitemap(URLSET)
    assert u.kind == "urlset" and u.count == 2 and u.latest_lastmod == "2026-06-01"
    i = parse_sitemap(INDEX)
    assert i.kind == "sitemapindex" and i.count == 2


def test_parse_sitemap_invalid():
    assert parse_sitemap("<not-a-sitemap/>").kind == "invalid"
    assert parse_sitemap("definitely { not xml").kind == "invalid"


def test_sitemap_findings_fresh_vs_stale():
    fresh = _run(NetInputs(sitemap_status=200, sitemap_xml=URLSET))
    assert fresh["tech.sitemap"].status == Status.PASS
    assert fresh["tech.sitemap"].value == 2

    # Both entries old, so max(<lastmod>) is also old.
    stale_xml = URLSET.replace("2026-06-01", "2000-01-01").replace("2026-05-20", "2000-01-02")
    stale = _run(NetInputs(sitemap_status=200, sitemap_xml=stale_xml))
    assert stale["tech.sitemap.freshness"].status == Status.WARN
    assert stale["tech.sitemap.freshness"].value > SITEMAP_STALE_DAYS


def test_sitemap_invalid_is_fail():
    ids = _run(NetInputs(sitemap_status=200, sitemap_xml="<nope/>"))
    assert ids["tech.sitemap.invalid"].status == Status.FAIL


# ------------------------------------------------------------------ redirects + TLS

def test_redirect_chain_warns_when_long():
    chain = [(301, "http://example.com/"), (301, "https://example.com/"), (302, "https://example.com/x")]
    ids = _run(NetInputs(redirect_chain=chain))
    assert ids["tech.redirect.chain"].status == Status.WARN
    assert ids["tech.redirect.chain"].value == 3


def test_single_redirect_is_info():
    ids = _run(NetInputs(redirect_chain=[(301, "http://example.com/")]))
    assert ids["tech.redirect"].status == Status.INFO


def test_no_redirect_emits_nothing():
    ids = _run(NetInputs())
    assert "tech.redirect" not in ids and "tech.redirect.chain" not in ids


def test_tls_expiry_states():
    assert _run(NetInputs(tls={"days_remaining": 200, "not_after": "x"}))["tech.tls"].status == Status.PASS
    assert _run(NetInputs(tls={"days_remaining": 5, "not_after": "x"}))["tech.tls"].status == Status.WARN
    assert _run(NetInputs(tls={"days_remaining": -1, "not_after": "x"}))["tech.tls"].status == Status.FAIL


# ------------------------------------------------------------------ JS-render gap

def test_render_flags_js_dependent_content():
    ids = _run(NetInputs(render_delta={"raw_words": 20, "rendered_words": 300}))
    f = ids["tech.render.js_dependent"]
    assert f.status == Status.WARN
    assert f.value == {"raw_words": 20, "rendered_words": 300}


def test_render_ok_when_content_in_raw_html():
    ids = _run(NetInputs(render_delta={"raw_words": 200, "rendered_words": 210}))
    assert ids["tech.render.ok"].status == Status.PASS
    assert "tech.render.js_dependent" not in ids


def test_render_small_absolute_delta_is_ok():
    # 10 -> 25 words: ratio is high but the absolute gap is below the threshold, so not flagged.
    ids = _run(NetInputs(render_delta={"raw_words": 10, "rendered_words": 25}))
    assert ids["tech.render.ok"].status == Status.PASS


def test_offline_scan_skips_network_checks():
    """With no NetInputs, none of the network-derived findings appear (offline default)."""
    r = scan_html("https://example.com/", HTML, online=False)
    ids = {f.id for f in r.findings}
    assert not any(i.startswith(("tech.robots", "tech.sitemap", "tech.redirect", "tech.tls",
                                 "tech.render", "tech.llms")) for i in ids)
    assert "tech.https" in ids  # in-page technical checks still run
    assert "tech.resource_hints" in ids  # delivery check is DOM-based, runs offline


# ------------------------------------------------------------- delivery + llms.txt

def test_resource_hints_pass_with_hints():
    html = ("<head><link rel='preconnect' href='https://cdn.example'>"
            "<script src='a.js' defer></script></head><body><h1>x</h1></body>")
    f = _run_full(html)["tech.resource_hints"]
    assert f.status == Status.PASS
    assert f.value["resource_hints"] == 1 and f.value["blocking_scripts"] == 0


def test_resource_hints_warn_on_blocking_script():
    html = "<head><script src='a.js'></script></head><body><h1>x</h1></body>"
    f = _run_full(html)["tech.resource_hints"]
    assert f.status == Status.WARN and f.value["blocking_scripts"] == 1


def test_llms_present_and_absent():
    present = _run(NetInputs(llms_status=200, llms_txt="# llms\nUser-agent: *\n"))
    assert present["tech.llms_txt"].status == Status.PASS and present["tech.llms_txt"].value is True
    absent = _run(NetInputs(llms_status=404, llms_txt=""))
    assert absent["tech.llms_txt"].status == Status.INFO  # low-impact: absence doesn't penalize


def _run_full(html: str):
    """Run the technical module against given HTML (resource hints read the DOM head)."""
    return {f.id: f for f in analyze(make_soup(html), "https://example.com/", 200, {})}


# --------------------------------------------------------------------- mixed content

def test_mixed_content_flags_http_subresources_only():
    # http image = mixed content; http <a> link and http canonical are NOT
    html = ("<head><link rel='canonical' href='http://example.com/x'></head>"
            "<body><a href='http://other.com'>a link</a>"
            "<img src='http://cdn.com/logo.png'></body>")
    ids = _run_full(html)
    assert ids["tech.mixed_content"].status == Status.FAIL
    assert ids["tech.mixed_content"].value == 1  # only the <img>, not the link or canonical


def test_no_mixed_content_for_plain_http_links():
    # an https page that merely LINKS to http sites is not mixed content
    html = "<body><a href='http://news.example'>read more</a><img src='/local.png'></body>"
    ids = _run_full(html)
    assert ids["tech.mixed_content.ok"].status == Status.PASS
