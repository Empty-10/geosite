"""Tests for the five new Answerability Review findings (answerability_review.analyze)."""

from __future__ import annotations

from astova_engine import knowledge
from astova_engine.modules import answerability_review
from astova_engine.util import make_soup, visible_text


def _run(html: str) -> dict:
    soup = make_soup(html)
    return {f.id: f for f in answerability_review.analyze(soup, visible_text(soup))}


_FILLER = "<p>" + " ".join(["context"] * 20) + ".</p>"


# --------------------------------------------------------------------------- answer_self_contained

def test_answer_self_contained_pass():
    html = "<body><p>Pour-over coffee is a manual brewing method that uses a clean ratio of grounds to water.</p></body>"
    f = _run(html)["geo.answer_self_contained"]
    assert f.status.value == "pass"


def test_answer_self_contained_warn_on_ambiguous_opener():
    html = "<body><p>It is a manual brewing method that uses a clean ratio of grounds to water here.</p></body>"
    f = _run(html)["geo.answer_self_contained"]
    assert f.status.value == "warn" and f.value["opener"] == "it"


def test_answer_self_contained_absent_when_no_answer():
    # No self-contained answer paragraph (only short fragments) -> no finding (geo.aeo owns absence).
    html = "<body><h1>Title here</h1><p>short one</p><p>two three four</p><p>five six seven eight</p></body>"
    assert "geo.answer_self_contained" not in _run(html)


# --------------------------------------------------------------------------- heading_coverage

def test_heading_coverage_warn_under_sectioned():
    body = "<p>" + " ".join(["word"] * 450) + "</p>"
    f = _run(f"<body>{body}</body>")["geo.heading_coverage"]
    assert f.status.value == "warn" and f.value["sections"] == 0


def test_heading_coverage_pass_well_sectioned():
    chunk = " ".join(["word"] * 150)
    body = f"<h2>One</h2><p>{chunk}</p><h2>Two</h2><p>{chunk}</p><h2>Three</h2><p>{chunk}</p>"
    f = _run(f"<body>{body}</body>")["geo.heading_coverage"]
    assert f.status.value == "pass" and f.value["sections"] == 3


def test_heading_coverage_absent_for_short_page():
    assert "geo.heading_coverage" not in _run("<body><p>" + " ".join(["w"] * 40) + "</p></body>")


# --------------------------------------------------------------------------- table_extractability

def test_table_extractability_warn_no_header():
    html = "<body>" + _FILLER + "<table><tr><td>A</td><td>1</td></tr></table></body>"
    f = _run(html)["geo.table_extractability"]
    assert f.status.value == "warn" and f.value["headerless"] == 1


def test_table_extractability_pass_with_header():
    html = "<body>" + _FILLER + "<table><thead><tr><th>A</th></tr></thead><tbody><tr><td>1</td></tr></tbody></table></body>"
    f = _run(html)["geo.table_extractability"]
    assert f.status.value == "pass"


def test_table_extractability_absent_without_tables():
    assert "geo.table_extractability" not in _run("<body>" + _FILLER + "</body>")


# --------------------------------------------------------------------------- question_coverage

def test_question_coverage_warn_orphan_question():
    html = "<body>" + _FILLER + "<h2>What is it?</h2><h2>Next section</h2></body>"
    f = _run(html)["geo.question_coverage"]
    assert f.status.value == "warn" and f.value["unanswered"] == 1


def test_question_coverage_pass_when_answered():
    html = "<body>" + _FILLER + "<h2>What is it?</h2><p>It is a clear, simple method explained in full here.</p></body>"
    f = _run(html)["geo.question_coverage"]
    assert f.status.value == "pass"


def test_question_coverage_absent_without_questions():
    assert "geo.question_coverage" not in _run("<body>" + _FILLER + "<h2>Overview</h2><p>text here</p></body>")


# --------------------------------------------------------------------------- definition_present

def test_definition_present_pass():
    html = "<body><p>Astova is a deterministic AI Readiness engine that audits pages for citability.</p></body>"
    f = _run(html)["geo.definition_present"]
    assert f.status.value == "pass" and f.value["present"] is True


def test_definition_present_advisory_when_absent():
    html = "<body><p>" + " ".join(["welcome"] * 20) + " to the homepage of our company today.</p></body>"
    f = _run(html)["geo.definition_present"]
    assert f.status.value == "info" and f.value["present"] is False


# --------------------------------------------------------------------------- guards / cards

def test_empty_page_emits_nothing():
    assert _run("<body><p>hi</p></body>") == {}  # < 10 words -> geo.no_content owns it


def test_every_new_finding_has_a_card():
    for fid in ("geo.answer_self_contained", "geo.heading_coverage", "geo.table_extractability",
                "geo.question_coverage", "geo.definition_present"):
        assert knowledge.explain(fid) is not None, fid
