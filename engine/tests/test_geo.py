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
    f = run("<body><h1>Title</h1><ul><li>buy</li><li>now</li></ul></body>")["geo.aeo"]
    assert f.status == Status.FAIL
    assert f.value["answer_word_offset"] is None


# ----------------------------------------------------------------------------- FAQ section

FAQ_SCHEMA = """<script type="application/ld+json">
{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[]}</script>"""


def test_faq_pass_via_schema():
    assert run(f"<head>{FAQ_SCHEMA}</head><body><p>hi there friend</p></body>")["geo.faq"].status == Status.PASS


def test_faq_pass_via_two_qa_pairs():
    html = """<body>
      <h2>What ratio should I use?</h2><p>Use a 1 to 16 ratio of coffee to water for balance.</p>
      <h2>How long does it take?</h2><p>About three minutes from first pour to finish in total.</p>
    </body>"""
    f = run(html)["geo.faq"]
    assert f.status == Status.PASS
    assert f.value["qa_pairs"] == 2


def test_faq_warn_when_single_question_or_none():
    # one Q&A pair is not enough, and no FAQPage schema
    html = "<body><h2>What is it?</h2><p>It is a clear and direct answer that is long enough.</p></body>"
    f = run(html)["geo.faq"]
    assert f.status == Status.WARN
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
