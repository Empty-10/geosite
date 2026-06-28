"""Fixture tests for deterministic fix generation. Offline."""

from __future__ import annotations

import json

from astova_engine import scan_html
from astova_engine.fixes import Fix, generate_fixes
from astova_engine.util import make_soup


def fixes_for(html: str, url: str = "https://example.com/page") -> dict[str, Fix]:
    report = scan_html(url, html, online=False, final_url=url, fixes=True)
    return {f.finding_id: f for f in report.fixes}


def _valid_jsonld(fix: Fix) -> dict:
    inner = fix.content.split(">", 1)[1].rsplit("<", 1)[0].strip()  # strip <script> wrapper
    return json.loads(inner)


# ------------------------------------------------------------------------ schema fix

def test_schema_fix_generated_when_missing():
    html = """<html><head><title>Acme Widgets | Acme</title>
      <meta property="og:image" content="https://example.com/logo.png">
      </head><body><h1>Best widgets</h1><p>We sell the finest widgets available anywhere.</p></body></html>"""
    f = fixes_for(html)["schema.missing"]
    assert f.kind == "json-ld"
    graph = _valid_jsonld(f)["@graph"]
    org = next(n for n in graph if n["@type"] == "Organization")
    assert org["name"] == "Acme"  # derived from the title's brand segment
    assert org["logo"] == "https://example.com/logo.png"


def test_no_schema_fix_when_schema_present():
    html = """<html><head><title>T</title>
      <script type="application/ld+json">{"@type":"Organization","name":"X"}</script>
      </head><body><h1>h</h1><p>Plenty of words here to satisfy the content checks fine.</p></body></html>"""
    assert "schema.missing" not in fixes_for(html)


# --------------------------------------------------------------------------- FAQ fix

def test_faq_fix_from_qa_pairs():
    html = """<html><head><title>T</title></head><body>
      <h2>What is it?</h2><p>It is a clear and direct answer that is long enough to count.</p>
      <h2>How much?</h2><p>It costs a fixed monthly fee with no hidden charges whatsoever.</p>
    </body></html>"""
    f = fixes_for(html)["geo.faq"]
    entities = _valid_jsonld(f)["mainEntity"]
    assert len(entities) == 2
    assert entities[0]["@type"] == "Question"
    assert entities[0]["acceptedAnswer"]["@type"] == "Answer"


# -------------------------------------------------------------------------- llms.txt

def test_llms_fix_when_absent():
    # technical module emits tech.llms_txt(value=False) when llms_status is provided as 404
    from astova_engine.modules.technical import NetInputs
    report = scan_html("https://example.com/", "<html><body><p>hi there friends here</p></body></html>",
                       online=False, final_url="https://example.com/",
                       net=NetInputs(llms_status=404, llms_txt=""), fixes=True)
    fx = {f.finding_id: f for f in report.fixes}["tech.llms_txt"]
    assert fx.kind == "llms-txt"
    assert fx.content.startswith("# ")
    assert "/sitemap.xml" in fx.content


# ---------------------------------------------------------------------- meta description

def test_meta_fix_from_first_paragraph():
    html = ("<html><head><title>T</title></head><body><h1>h</h1>"
            "<p>This opening paragraph becomes the basis for a generated meta description tag.</p>"
            "</body></html>")
    f = fixes_for(html)["meta.description.missing"]
    assert f.content.startswith('<meta name="description"')
    assert "opening paragraph" in f.content


def test_title_fix_from_h1():
    html = "<html><head></head><body><h1>Best widgets in town</h1><p>plenty of words here friends</p></body></html>"
    f = fixes_for(html)["title.missing"]
    assert f.content == "<title>Best widgets in town</title>"


def test_canonical_and_viewport_fixes_when_missing():
    html = "<html><head><title>T</title></head><body><h1>h</h1><p>words words words words words words words</p></body></html>"
    fx = fixes_for(html, "https://example.com/page")
    assert fx["canonical"].content == '<link rel="canonical" href="https://example.com/page">'
    assert 'width=device-width' in fx["tech.viewport"].content


def test_robots_fix_when_missing():
    from astova_engine.modules.technical import NetInputs
    report = scan_html("https://example.com/", "<html><body><h1>h</h1><p>some words here for body</p></body></html>",
                       online=False, final_url="https://example.com/",
                       net=NetInputs(robots_status=404, robots_txt=""), fixes=True)
    fx = {f.finding_id: f for f in report.fixes}["tech.robots.missing"]
    assert fx.kind == "robots"
    assert "GPTBot" in fx.content and "Sitemap: https://example.com/sitemap.xml" in fx.content


def test_generate_fixes_is_pure_listable():
    html = "<html><head><title>T</title></head><body><h1>h</h1></body></html>"
    report = scan_html("https://example.com/", html, online=False, final_url="https://example.com/")
    # without fixes=True, no fixes attached
    assert report.fixes == []
    # calling generate_fixes directly returns Fix objects
    out = generate_fixes(make_soup(html), report, "https://example.com/")
    assert all(isinstance(f, Fix) for f in out)


# --- agent-actionable fix plan (build_fix_plan) ---------------------------------------------

def _plan(html: str, url: str = "https://example.com/page") -> list[dict]:
    from astova_engine.fixes import build_fix_plan
    report = scan_html(url, html, online=False, final_url=url, fixes=True)
    return build_fix_plan(report)


THIN = "<!doctype html><html><head><title>x</title></head><body><h1>Hi</h1><p>buy now</p></body></html>"


def test_fix_plan_has_deterministic_and_advisory_items():
    plan = _plan(THIN)
    assert plan, "a thin/broken page should yield fixes"
    sources = {item["source"] for item in plan}
    # every item is agent-actionable
    for item in plan:
        assert {"finding_id", "title", "action", "target", "instruction", "source"} <= set(item)
    # deterministic artifacts carry content; advisory items carry an instruction
    assert "deterministic" in sources or "advisory" in sources
    det = [i for i in plan if i["source"] == "deterministic"]
    for i in det:
        assert i["content"] and i["action"] in ("create_file", "add_to_head", "edit_content")


def test_fix_plan_flags_ai_draftable():
    # geo.aeo (no up-front answer) is judgment-dependent → advisory + ai_draftable
    plan = _plan(THIN)
    aeo = next((i for i in plan if i["finding_id"] == "geo.aeo"), None)
    if aeo is not None:  # present when the answer-block check fires
        assert aeo["source"] == "advisory" and aeo["ai_draftable"] is True
