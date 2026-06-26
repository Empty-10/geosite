"""Fixture tests for the new on-page checks: link anchor text, outbound links, jump links,
image dimensions, URL structure. Offline."""

from __future__ import annotations

from damask_engine.models import Status
from damask_engine.modules.onpage import analyze
from damask_engine.util import make_soup, visible_text


def run(html: str, url: str = ""):
    soup = make_soup(html)
    return {f.id: f for f in analyze(soup, visible_text(soup), url)}


# ------------------------------------------------------------------------- anchor text

def test_links_warn_on_generic_anchors():
    html = """<body>
      <a href="/a">click here</a><a href="/b">read more</a><a href="/c">here</a>
    </body>"""
    f = run(html, "https://example.com/")["onpage.links"]
    assert f.status == Status.WARN
    assert f.value["generic"] == 3


def test_links_pass_on_descriptive_anchors():
    html = """<body>
      <a href="/brew-guide">our pour-over brewing guide</a>
      <a href="/ratios">coffee-to-water ratios explained</a>
    </body>"""
    assert run(html, "https://example.com/")["onpage.links"].status == Status.PASS


def test_internal_vs_external_counts():
    html = """<body>
      <a href="/internal">internal page link text</a>
      <a href="https://other.com/x">external resource reference</a>
    </body>"""
    f = run(html, "https://example.com/")
    assert f["onpage.links"].value == {"internal": 1, "external": 1, "generic": 0, "total": 2}
    assert f["onpage.outbound"].status == Status.PASS  # has an external link


def test_outbound_info_when_no_external():
    html = '<body><a href="/x">only internal links here please</a></body>'
    assert run(html, "https://example.com/")["onpage.outbound"].status == Status.INFO


# --------------------------------------------------------------------------- jump links

def test_jump_links_pass_when_resolving():
    html = '<body><a href="#sec">Jump to section</a><h2 id="sec">Section</h2></body>'
    f = run(html)["onpage.jump_links"]
    assert f.status == Status.PASS and f.value["resolved"] == 1


def test_jump_links_info_when_unresolved():
    html = '<body><a href="#missing">broken jump</a></body>'
    assert run(html)["onpage.jump_links"].status == Status.INFO


# ---------------------------------------------------------------------- image dimensions

def test_images_dims_warn_without_dimensions():
    html = '<body><img src="a.jpg" alt="a"><img src="b.jpg" alt="b"></body>'
    f = run(html)["onpage.images.dims"]
    assert f.status == Status.WARN and f.value["pct_dims"] == 0


def test_images_dims_pass_with_dimensions_and_lazy():
    html = '<body><img src="a.jpg" alt="a" width="800" height="600" loading="lazy"></body>'
    f = run(html)["onpage.images.dims"]
    assert f.status == Status.PASS
    assert f.value["with_dims"] == 1 and f.value["with_lazy"] == 1


# ----------------------------------------------------------------------- URL structure

def test_url_quality_pass_clean():
    assert run("<body></body>", "https://example.com/pour-over-coffee")["onpage.url"].status == Status.PASS


def test_url_quality_warn_messy():
    f = run("<body></body>", "https://example.com/Deep/Path_With/Junk/Here/X?q=1&utm=2")["onpage.url"]
    assert f.status == Status.WARN
    assert "underscores (use hyphens)" in f.value["issues"]
    assert "query string" in f.value["issues"]


def test_url_quality_skipped_without_url():
    assert "onpage.url" not in run("<body></body>")


# ------------------------------------------------------------------ accessibility basics

def test_lang_pass_and_warn():
    assert run("<html lang='en'><body>x</body></html>")["onpage.lang"].status == Status.PASS
    assert run("<html><body>x</body></html>")["onpage.lang"].status == Status.WARN


def test_form_labels_warn_on_unlabeled_control():
    html = '<body><form><input type="text" name="q"></form></body>'
    f = run(html)["onpage.form_labels"]
    assert f.status == Status.WARN and f.value["unlabeled"] == 1


def test_form_labels_pass_when_labeled():
    html = '<body><label for="q">Search</label><input id="q" type="text"></body>'
    assert run(html)["onpage.form_labels"].status == Status.PASS


def test_form_labels_skipped_without_controls():
    assert "onpage.form_labels" not in run("<body><p>no forms here at all</p></body>")


# ------------------------------------------------------------------------- link attributes (Row 13)

def test_link_attrs_warns_on_blank_without_noopener():
    html = '<body><a href="https://other.com/x" target="_blank">external</a></body>'
    f = run(html, "https://example.com/")["onpage.link_attrs"]
    assert f.status == Status.WARN and f.value["blank_without_noopener"] == 1


def test_link_attrs_passes_with_noopener():
    html = '<body><a href="https://other.com/x" target="_blank" rel="noopener">external</a></body>'
    assert run(html, "https://example.com/")["onpage.link_attrs"].status == Status.PASS


def test_link_attrs_absent_without_external_links():
    assert "onpage.link_attrs" not in run('<body><a href="/internal">x</a></body>', "https://example.com/")


# ------------------------------------------------------------------------- schema validation (Row 20)

def test_schema_validation_warns_on_missing_required():
    html = ('<body><script type="application/ld+json">'
            '{"@context":"https://schema.org","@type":"Article","author":"Jo"}'
            '</script></body>')  # Article without headline
    f = run(html)["schema.validation"]
    assert f.status == Status.WARN and "headline" in f.evidence


def test_schema_validation_passes_when_required_present():
    html = ('<body><script type="application/ld+json">'
            '{"@context":"https://schema.org","@type":"Article","headline":"How to brew coffee"}'
            '</script></body>')
    assert run(html)["schema.validation"].status == Status.PASS


def test_schema_validation_absent_for_unknown_types():
    html = ('<body><script type="application/ld+json">'
            '{"@context":"https://schema.org","@type":"WebSite","name":"x"}'
            '</script></body>')  # WebSite isn't in the required-props registry → no finding
    assert "schema.validation" not in run(html)


# ------------------------------------------------------------------------- canonical correctness

def test_canonical_self_referencing_passes():
    html = '<head><link rel="canonical" href="https://example.com/page"></head>'
    f = run(html, "https://example.com/page")["canonical"]
    assert f.status == Status.PASS and f.value["self_referencing"]


def test_canonical_pointing_elsewhere_warns():
    html = '<head><link rel="canonical" href="https://example.com/other"></head>'
    f = run(html, "https://example.com/page")["canonical"]
    assert f.status == Status.WARN and not f.value["self_referencing"]


def test_canonical_multiple_warns():
    html = ('<head><link rel="canonical" href="https://example.com/page">'
            '<link rel="canonical" href="https://example.com/page2"></head>')
    f = run(html, "https://example.com/page")["canonical"]
    assert f.status == Status.WARN and f.value["count"] == 2


def test_canonical_missing_warns():
    assert run("<head></head>", "https://example.com/page")["canonical"].status == Status.WARN


# ------------------------------------------------------------------------- snippet directives

def test_snippet_directives_warn_on_nosnippet():
    html = '<head><meta name="robots" content="index, nosnippet"></head>'
    assert run(html)["onpage.snippet_directives"].status == Status.WARN


def test_snippet_directives_pass_on_large_preview():
    html = '<head><meta name="robots" content="max-image-preview:large"></head>'
    assert run(html)["onpage.snippet_directives"].status == Status.PASS


def test_snippet_directives_info_when_unset():
    assert run("<head></head>")["onpage.snippet_directives"].status == Status.INFO


# ------------------------------------------------------------------- image alt (benchmark fix)

def test_alt_empty_counts_as_present_decorative():
    # alt="" is valid for decorative images (matches Lighthouse/WCAG) — not "missing"
    html = '<body><img src="a.png" alt=""><img src="b.png" alt="a real description"></body>'
    f = run(html)["images.alt"]
    assert f.status == Status.PASS
    assert f.value["with_alt"] == 2 and f.value["descriptive"] == 1


def test_alt_truly_missing_attribute_warns():
    html = '<body><img src="a.png"><img src="b.png"><img src="c.png" alt="ok"></body>'
    f = run(html)["images.alt"]
    assert f.status == Status.WARN  # 1/3 has alt → under 90%


def test_links_pass_with_few_generic_on_large_set():
    # a handful of generic anchors among many is fine (ratio-based, not absolute)
    links = "".join(f'<a href="/p{i}">descriptive link number {i} here</a>' for i in range(20))
    f = run("<body>" + links + '<a href="/x">click here</a></body>', "https://example.com/")["onpage.links"]
    assert f.status == Status.PASS  # 1 generic / 21 = ~5% < 10%


# ------------------------------------------------------------------- cheap coverage gaps (batch)

def test_opengraph_pass_with_core_tags():
    html = ('<head><meta property="og:title" content="T"><meta property="og:description" content="D">'
            '<meta property="og:image" content="i.png"></head>')
    assert run(html)["opengraph"].status == Status.PASS


def test_opengraph_warn_when_incomplete():
    f = run('<head><meta property="og:title" content="T"></head>')["opengraph"]
    assert f.status == Status.WARN and "og:image" in f.value["missing"]


def test_heading_order_pass_clean_outline():
    html = "<body><h1>A</h1><h2>B</h2><h3>C</h3><h2>D</h2></body>"
    assert run(html)["onpage.heading_order"].status == Status.PASS


def test_heading_order_warn_on_skip():
    html = "<body><h1>A</h1><h3>skips h2</h3></body>"
    f = run(html)["onpage.heading_order"]
    assert f.status == Status.WARN and "h1→h3" in f.evidence


def test_crawlable_anchors_warn_on_js_nav():
    html = '<body><a href="javascript:void(0)">go</a><a href="/real">real</a></body>'
    f = run(html)["onpage.crawlable_anchors"]
    assert f.status == Status.WARN and f.value["uncrawlable"] == 1


def test_crawlable_anchors_pass_with_real_hrefs():
    assert run('<body><a href="/a">a</a><a href="https://x.com">b</a></body>')["onpage.crawlable_anchors"].status == Status.PASS


def test_hreflang_absent_when_unused():
    assert "onpage.hreflang" not in run("<head></head>")


def test_hreflang_warn_missing_xdefault():
    html = '<head><link rel="alternate" hreflang="en" href="/en"><link rel="alternate" hreflang="fr" href="/fr"></head>'
    f = run(html)["onpage.hreflang"]
    assert f.status == Status.WARN and "x-default" in f.evidence


def test_hreflang_pass_valid_with_xdefault():
    html = ('<head><link rel="alternate" hreflang="en-US" href="/en">'
            '<link rel="alternate" hreflang="x-default" href="/"></head>')
    assert run(html)["onpage.hreflang"].status == Status.PASS
