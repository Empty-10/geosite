"""Tests for the 20-row scorecard aggregation: structure, row scoring, the three gates, and
the +8 overlay. Built on real scan_html output so the mapping stays honest."""

from __future__ import annotations

from astova_engine import scan_html
from astova_engine.models import Finding, Pillar, Report, Status
from astova_engine.scorecard import build_scorecard


def _card(html: str, url: str = "https://example.com/page") -> dict:
    return scan_html(url, html, online=False).scorecard


GOOD = """<!doctype html><html lang="en"><head>
<title>How to brew pour-over coffee: a complete guide</title>
<meta name="description" content="A clear, complete guide to brewing pour-over coffee at home,
with ratios, timings and the gear you need, in about 120 to 160 characters of summary text.">
<link rel="canonical" href="https://example.com/page">
</head><body>
<h1>How to brew pour-over coffee</h1>
<p>Pour-over coffee uses a 1 to 16 ratio of grounds to water, brewed through a paper filter over
about three minutes, producing a clean, bright cup. Here is exactly how to do it at home.</p>
<ul><li>Use 30 grams of coffee to 500 grams of water</li><li>Bloom for 30 seconds first</li></ul>
<h2>What grind size works best?</h2><p>A medium-fine grind, similar to table salt, works best for
most pour-over brewers and keeps the total brew time near three minutes.</p>
</body></html>"""


def test_scorecard_structure():
    c = _card(GOOD)
    assert set(c) == {"confidence", "headline_score", "technical_score", "overlay", "rows",
                      "categories", "summary", "citation", "reviews", "assessment"}
    assert c["confidence"] == "verified"
    assert len(c["rows"]) == 20
    assert all(r["n"] == i + 1 for i, r in enumerate(c["rows"]))
    assert all("impact" in r for r in c["rows"])
    assert 0 <= c["headline_score"] <= 100
    assert c["headline_score"] * 2 == round(c["headline_score"] * 2)  # rounded to 0.5


def test_summary_shape_and_band():
    s = _card(GOOD)["summary"]
    assert set(s) == {"band", "verdict", "opportunities"}
    assert s["band"] in {"strong", "solid", "needs work", "at risk"}
    assert isinstance(s["verdict"], str) and s["verdict"]
    assert len(s["opportunities"]) <= 3
    for o in s["opportunities"]:
        assert set(o) == {"n", "text", "impact"} and o["impact"] > 0


def test_row_impact_zero_for_perfect_or_na_rows():
    for r in _card(GOOD)["rows"]:
        if r["score"] is None or r["score"] == 100:
            assert r["impact"] == 0.0


def test_at_risk_page_names_opportunities():
    # An all-but-empty page collapses to a low-band verdict with concrete opportunities.
    c = _card("<!doctype html><html><head><title>x</title></head><body></body></html>")
    assert c["summary"]["band"] in {"needs work", "at risk"}
    assert c["summary"]["opportunities"]


def test_citation_readiness():
    good = _card(GOOD)["citation"]
    assert set(good) == {"band", "score", "reasons"}
    assert good["band"] in {"well positioned", "partially positioned", "poorly positioned"}
    assert 0 <= good["score"] <= 100
    # An empty page is poorly positioned to be cited, with concrete reasons.
    empty = _card("<!doctype html><html><head><title>x</title></head><body></body></html>")["citation"]
    assert empty["band"] == "poorly positioned"
    assert empty["reasons"] and all(set(r) == {"n", "text"} for r in empty["reasons"])


def test_rows_map_to_findings():
    rows = {r["n"]: r for r in _card(GOOD)["rows"]}
    assert "title.length" in rows[2]["findings"]
    assert "geo.aeo" in rows[7]["findings"]
    assert "schema.missing" in rows[20]["findings"] or "schema.jsonld" in rows[20]["findings"]


# --- gates ---------------------------------------------------------------------------------

def _scorecard_from(findings: list[Finding]) -> dict:
    return build_scorecard(Report(url="https://x.test", findings=findings))


def test_gate_row7_zero_when_no_answer():
    fs = [Finding("geo.aeo", Pillar.GEO, "AEO", Status.FAIL, value={"answer_word_offset": None}),
          Finding("geo.definitive", Pillar.GEO, "Definitive", Status.PASS)]
    row7 = next(r for r in _scorecard_from(fs)["rows"] if r["n"] == 7)
    assert row7["score"] == 0


def test_gate_row6_caps_promotional_intro():
    fs = [Finding("geo.frontload", Pillar.GEO, "Front", Status.PASS),
          Finding("geo.intro_quality", Pillar.GEO, "Intro", Status.WARN)]
    row6 = next(r for r in _scorecard_from(fs)["rows"] if r["n"] == 6)
    assert row6["score"] <= 40


def test_gate_row8_zero_without_list_and_caps_nav():
    no_list = [Finding("geo.summary_bullets", Pillar.GEO, "Bullets", Status.WARN, value={"found": False})]
    assert next(r for r in _scorecard_from(no_list)["rows"] if r["n"] == 8)["score"] == 0

    nav = [Finding("geo.summary_bullets", Pillar.GEO, "Bullets", Status.WARN,
                   value={"found": True, "navigation": True})]
    assert next(r for r in _scorecard_from(nav)["rows"] if r["n"] == 8)["score"] <= 40


# --- overlay -------------------------------------------------------------------------------

def test_overlay_schema_factor_awards_for_three_types():
    fs = [Finding("schema.jsonld", Pillar.ONPAGE, "Schema", Status.PASS,
                  value=["Article", "Organization", "BreadcrumbList"])]
    overlay = _scorecard_from(fs)["overlay"]
    schema_factor = next(f for f in overlay["factors"] if f["name"] == "≥3 schema types")
    assert schema_factor["points"] == 2.0
    assert overlay["total"] >= 2.0


def test_overlay_total_capped_at_8():
    c = _card(GOOD)
    assert c["overlay"]["total"] <= 8.0
    assert c["headline_score"] <= 100


def test_empty_page_tanks_geo_rows():
    c = scan_html("https://x.test/empty", "<html><body><div id='root'></div></body></html>", online=False).scorecard
    rows = {r["n"]: r for r in c["rows"]}
    assert rows[7]["score"] == 0 and rows[10]["score"] == 0  # answer + content rows fail
