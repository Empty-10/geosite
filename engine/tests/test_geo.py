"""Fixture tests for the new geo_readiness checks: AEO answer block, FAQ, trust/E-E-A-T.
Offline — feed crafted HTML straight to the module."""

from __future__ import annotations

from damask_engine.models import Status
from damask_engine.modules.geo_readiness import AEO_GOOD_MAX, analyze
from damask_engine.util import make_soup, visible_text


def run(html: str):
    soup = make_soup(html)
    return {f.id: f for f in analyze(soup, visible_text(soup))}


# ---------------------------------------------------------------- AEO answer block (gated)

ANSWER = "<p>Pour-over coffee uses a 1 to 16 ratio of grounds to water brewed over three minutes.</p>"


def test_aeo_pass_when_answer_up_top():
    f = run(f"<body><h1>How to brew coffee</h1>{ANSWER}</body>")["geo.aeo"]
    assert f.status == Status.PASS
    assert f.value["answer_word_offset"] < AEO_GOOD_MAX


def test_aeo_warn_when_answer_too_deep():
    filler = "<div>" + ("word " * 240) + "</div>"  # 240 visible words before the answer
    f = run(f"<body><h1>Title</h1>{filler}{ANSWER}</body>")["geo.aeo"]
    assert f.status == Status.WARN
    assert f.value["answer_word_offset"] > AEO_GOOD_MAX


def test_aeo_fail_when_no_answer_paragraph():
    # enough words to not be "empty", but no self-contained answer paragraph (short list items)
    html = "<body><h1>Our product page title here</h1><ul><li>buy now</li><li>sign up</li><li>get started today</li></ul></body>"
    f = run(html)["geo.aeo"]
    assert f.status == Status.FAIL
    assert f.value["answer_word_offset"] is None


def test_aeo_pass_with_div_based_answer():
    # framework markup: the answer lives in a text <div>/<span>, not a <p>
    html = ("<body><div class='hero'><span>Pour-over coffee uses a 1 to 16 ratio "
            "brewed over about three minutes.</span></div></body>")
    f = run(html)["geo.aeo"]
    assert f.status == Status.PASS  # previously false-FAILed because it wasn't a <p>


def test_aeo_skips_layout_wrapper_divs():
    # an outer wrapper <div> (has nested blocks) is NOT treated as the answer; the inner
    # <p> is, and the heading words before it still count toward the offset
    html = ("<body><div class='wrap'><h2>Topic</h2>"
            "<p>A clear and complete answer sentence that is definitely long enough to count here.</p>"
            "</div></body>")
    assert run(html)["geo.aeo"].status == Status.PASS


# ----------------------------------------------------------------------------- FAQ section

FAQ_SCHEMA = """<script type="application/ld+json">
{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[]}</script>"""


def test_faq_pass_via_schema():
    body = "<body><p>hi there friend this is a body paragraph with plenty of words now</p></body>"
    assert run(f"<head>{FAQ_SCHEMA}</head>{body}")["geo.faq"].status == Status.PASS


def test_faq_pass_via_two_qa_pairs():
    html = """<body>
      <h2>What ratio should I use?</h2><p>Use a 1 to 16 ratio of coffee to water for balance.</p>
      <h2>How long does it take?</h2><p>About three minutes from first pour to finish in total.</p>
    </body>"""
    f = run(html)["geo.faq"]
    assert f.status == Status.PASS
    assert f.value["qa_pairs"] == 2


def test_faq_info_not_penalised_when_absent():
    # one Q&A pair / no FAQPage schema → informational, NOT a penalty (not every page is an FAQ)
    html = "<body><h2>What is it?</h2><p>It is a clear and direct answer that is long enough.</p></body>"
    f = run(html)["geo.faq"]
    assert f.status == Status.INFO
    assert f.value["qa_pairs"] == 1


# ------------------------------------------------------------------------- trust / E-E-A-T

ORG_SAMEAS = """<script type="application/ld+json">
{"@type":"Organization","name":"Acme","sameAs":["https://twitter.com/acme"]}</script>"""


def test_trust_pass_with_three_signals():
    html = f"""<head>{ORG_SAMEAS}</head><body>
      <span class="author">By Jane Doe</span>
      <time datetime="2026-01-01">Jan 2026</time>
      <p>Body copy here that is plenty long for the answer block to register fine.</p>
    </body>"""
    f = run(html)["geo.trust"]
    assert f.status == Status.PASS
    assert f.value["count"] >= 3


def test_trust_warn_when_signals_sparse():
    f = run("<body><p>Just some text with no author, date, links or entity schema at all.</p></body>")["geo.trust"]
    assert f.status == Status.WARN
    assert f.value["count"] < 3


def test_trust_ignores_decorative_author_class_and_bare_time():
    # A decorative author-avatar (image only) + a <time> without datetime are no longer counted.
    html = """<body>
      <div class="author-avatar"><img src="a.png"></div>
      <time>recently</time>
      <p>Body copy that is plenty long but carries no real trust signals at all here.</p>
    </body>"""
    f = run(html)["geo.trust"]
    assert "author byline" not in f.value["present"]
    assert "published/updated date" not in f.value["present"]


# ------------------------------------------------------------ structure: navigation lists excluded

def test_structure_warns_when_only_nav_lists():
    html = """<body><nav><ul><li><a href="/a">Home</a></li><li><a href="/b">About</a></li></ul></nav>
      <p>Some prose with no content list or table anywhere on the page at all.</p></body>"""
    f = run(html)["geo.structure"]
    assert f.status == Status.WARN
    assert f.value["lists"] == 0


def test_structure_passes_on_content_list():
    html = ("<body><p>Here is a short guide to brewing better coffee at home today.</p>"
            "<ul><li>Use thirty grams of coffee</li><li>Bloom for thirty seconds</li></ul></body>")
    assert run(html)["geo.structure"].status == Status.PASS


# ----------------------------------------------------------------- front-load: real answer sentence

def test_frontload_warns_on_fragmented_opening():
    # Headings + short fragments, no complete (punctuated) sentence in the opening.
    html = ("<body><h1>Best Coffee Beans</h1><h2>Fast Delivery</h2><h2>Cheap Prices</h2>"
            "<ul><li>Free Shipping</li><li>Great Taste</li><li>Buy It Today</li></ul></body>")
    assert run(html)["geo.frontload"].status == Status.WARN


def test_frontload_passes_with_real_opening_sentence():
    html = "<body><p>Pour-over coffee uses a one to sixteen ratio of grounds to water brewed slowly.</p></body>"
    assert run(html)["geo.frontload"].status == Status.PASS


# ------------------------------------------------------------------ JS-dependent content

def js(raw: int, rendered: int, **extra):
    soup = make_soup("<body><p>x</p></body>")
    delta = {"raw_words": raw, "rendered_words": rendered, **extra}
    return {f.id: f for f in analyze(soup, "x", render_delta=delta)}["geo.js_rendered"]


def test_js_rendered_pass_when_mostly_in_raw():
    f = js(200, 210)  # render_only ~5%
    assert f.status == Status.PASS and f.value["render_only_pct"] == 5


def test_js_rendered_warn_meaningful_share():
    f = js(200, 280)  # render_only ~29%
    assert f.status == Status.WARN and f.value["render_only_pct"] == 29


def test_js_rendered_fail_majority_js():
    f = js(18, 410)  # render_only ~96%
    assert f.status == Status.FAIL


def test_js_rendered_fail_thin_raw_shell():
    f = js(30, 60)  # raw < 50 and render_only = 50% → fail (near-empty without JS)
    assert f.status == Status.FAIL


def test_js_rendered_calls_out_js_only_schema_and_h1():
    f = js(18, 410, schema_js_only=True, h1_js_only=True)
    assert "structured data (JSON-LD)" in f.evidence and "the H1" in f.evidence


def test_js_rendered_not_run_without_render_delta():
    ids = {f.id for f in analyze(make_soup("<body><p>x</p></body>"), "x")}
    assert "geo.js_rendered" not in ids


# ---------------------------------------------------------------- summary bullets (Row 8)

def test_summary_bullets_content_list_near_top_passes():
    html = ("<body><p>" + "word " * 20 + "</p>"
            "<ul><li>First substantive point about the topic explained</li>"
            "<li>Second substantive point with real detail here too</li></ul></body>")
    assert run(html)["geo.summary_bullets"].status == Status.PASS


def test_summary_bullets_navigation_list_warns():
    html = ('<body><nav><ul><li><a href="/a">Home</a></li><li><a href="/b">About</a></li>'
            '<li><a href="/c">Contact</a></li></ul></nav>'
            "<p>" + "word " * 40 + "</p></body>")
    f = run(html)["geo.summary_bullets"]
    assert f.status == Status.WARN and f.value.get("navigation") is True


def test_summary_bullets_absent_warns():
    assert run("<body><p>" + "word " * 50 + "</p></body>")["geo.summary_bullets"].status == Status.WARN


# ---------------------------------------------------------------- intro quality (Row 6)

def test_intro_quality_flags_promotional_opening():
    html = "<body><p>We are the world-class, award-winning, #1 leading provider — sign up now!</p></body>"
    f = run(html)["geo.intro_quality"]
    assert f.status == Status.WARN and len(f.value["promo_markers"]) >= 2


def test_intro_quality_passes_informative_opening():
    html = ("<body><p>Pour-over coffee is a manual brewing method that uses a paper filter and a "
            "1 to 16 ratio of grounds to water. It produces a clean, bright cup in about three minutes.</p></body>")
    assert run(html)["geo.intro_quality"].status == Status.PASS


# ---------------------------------------------------------------- chunking (Row 10)

def test_chunking_passes_with_discrete_paragraphs():
    para = "<p>" + "word " * 30 + "</p>"
    assert run("<body>" + para * 4 + "</body>")["geo.chunking"].status == Status.PASS


def test_chunking_warns_on_wall_of_text():
    html = "<body><p>" + "word " * 400 + "</p></body>"
    f = run(html)["geo.chunking"]
    assert f.status == Status.WARN and f.value["walls"] == 1


# ---------------------------------------------------------------- data density (quotable stats)

def test_data_density_pass_when_rich():
    html = ("<body><p>Revenue grew 42% to $1,200,000 in 2024, up from 2,500 units, with "
            "load times of 250 ms across 30 days of testing.</p></body>")
    assert run(html)["geo.data_density"].status == Status.PASS


def test_data_density_warn_on_long_vague_page():
    # ~360 words of prose with no concrete figures → weak for citation
    html = "<body><p>" + ("quality service matters and we care deeply about our customers " * 40) + "</p></body>"
    f = run(html)["geo.data_density"]
    assert f.status == Status.WARN and f.value["data_points"] < 2


def test_data_density_counts_categories():
    html = "<body><p>In 2024 sales rose 12% to €5,000 over 10 km.</p></body>"
    v = run(html)["geo.data_density"].value
    assert v["year"] >= 1 and v["percent"] >= 1 and v["currency"] >= 1 and v["measure"] >= 1


# ---------------------------------------------------------------- empty-page collapse (no_content)

def test_no_content_collapses_symptom_cluster():
    out = {f.id: f for f in analyze(make_soup('<body><div id="root"></div></body>'), "")}
    assert out["geo.no_content"].severity.value == "critical"
    # the granular content checks are suppressed in favour of the single root cause
    for sym in ("geo.frontload", "geo.aeo", "geo.summary_bullets", "geo.thin_content"):
        assert sym not in out


def test_normal_page_keeps_granular_checks():
    html = "<body><h1>Guide</h1><p>" + ("word " * 60) + "</p></body>"
    out = {f.id for f in analyze(make_soup(html), "word " * 60)}
    assert "geo.no_content" not in out and "geo.frontload" in out


# --------------------------------------------------------------- freshness, entity, answer preview

from datetime import datetime, timezone  # noqa: E402
from damask_engine.modules.geo_readiness import _entity, _freshness  # noqa: E402

NOW = datetime(2026, 6, 28, tzinfo=timezone.utc)


def test_freshness_missing_is_info_suggestion():
    f = _freshness(make_soup("<body><p>no dates here at all</p></body>"), NOW)
    assert f.status == Status.INFO and f.value["latest"] is None
    assert f.recommendation


def test_freshness_recent_passes():
    html = '<body><time datetime="2026-05-01">May</time><p>fresh</p></body>'
    f = _freshness(make_soup(html), NOW)
    assert f.status == Status.PASS and f.value["latest"] == "2026-05-01"


def test_freshness_stale_warns():
    html = '<head><meta property="article:modified_time" content="2020-01-01T00:00:00Z"></head><body><p>old</p></body>'
    f = _freshness(make_soup(html), NOW)
    assert f.status == Status.WARN and f.value["age_days"] > 540


def test_entity_grounded_via_knowledge_base():
    html = ('<head><script type="application/ld+json">'
            '{"@type":"Organization","name":"Acme","sameAs":["https://en.wikipedia.org/wiki/Acme"]}'
            '</script></head><body><p>x</p></body>')
    assert _entity(make_soup(html)).status == Status.PASS


def test_entity_present_but_weak_is_suggestion():
    html = ('<head><script type="application/ld+json">'
            '{"@type":"Organization","name":"Acme","sameAs":["https://acme.example/blog"]}'
            '</script></head><body><p>x</p></body>')
    f = _entity(make_soup(html))
    assert f.status == Status.INFO and f.value["entity"] is True


def test_entity_absent_suggests_adding():
    f = _entity(make_soup("<body><p>no schema</p></body>"))
    assert f.status == Status.INFO and f.value["entity"] is False


def test_aeo_exposes_answer_snippet():
    html = "<body><h1>How to brew</h1><p>Pour-over coffee uses a one to sixteen ratio of grounds to water.</p></body>"
    f = run(html)["geo.aeo"]
    assert f.value.get("snippet")  # the likely-cited passage is exposed
