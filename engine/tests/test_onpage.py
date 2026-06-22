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
    assert f["onpage.links"].value == {"internal": 1, "external": 1, "generic": 0}
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
