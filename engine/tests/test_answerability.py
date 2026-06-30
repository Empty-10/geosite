"""Tests for the Answerability synthesis + the shared Expert Review contract helpers."""

from __future__ import annotations

from astova_engine import answerability, reviews

_CONTRACT_KEYS = {"review", "key", "verdict", "confidence", "summary", "likely_ai_quote",
                  "sections", "counts", "related_findings"}


def _sm(**kw):
    return dict(kw)


# --------------------------------------------------------------------------- verdict

def test_verdict_weak_on_no_content():
    assert answerability.verdict(_sm(**{"geo.no_content": "fail"})) == "weak"


def test_verdict_weak_on_aeo_fail():
    assert answerability.verdict(_sm(**{"geo.aeo": "fail"})) == "weak"


def test_verdict_strong_when_all_key_signals_pass():
    sm = {"geo.aeo": "pass", "geo.chunking": "pass", "geo.definitive": "pass",
          "geo.structure": "pass", "geo.answer_self_contained": "pass"}
    assert answerability.verdict(sm) == "strong"


def test_verdict_partial_when_answer_not_self_contained():
    sm = {"geo.aeo": "pass", "geo.chunking": "pass", "geo.definitive": "pass",
          "geo.structure": "pass", "geo.answer_self_contained": "warn"}
    assert answerability.verdict(sm) == "partial"


# --------------------------------------------------------------------------- consultant summary

def test_summary_override_no_content_returns_single_line():
    out = answerability.consultant_summary({"geo.no_content": "fail"})
    assert len(out) == 1 and "nothing for an AI engine to quote" in out[0]


def test_summary_prioritises_and_caps_at_four():
    sm = {"geo.aeo": "fail", "geo.structure": "warn", "geo.summary_bullets": "warn",
          "geo.chunking": "warn", "geo.definitive": "warn", "geo.data_density": "warn"}
    out = answerability.consultant_summary(sm)
    assert len(out) == answerability.SUMMARY_LIMIT
    assert out[0].startswith("There is no extractable answer")  # tier-1 first


def test_summary_all_clear():
    out = answerability.consultant_summary({"geo.aeo": "pass", "geo.chunking": "pass"})
    assert len(out) == 1 and "Strong answerability" in out[0]


def test_summary_self_containment_line():
    out = answerability.consultant_summary({"geo.aeo": "pass", "geo.answer_self_contained": "warn"})
    assert any("can't resolve" in line for line in out)


# --------------------------------------------------------------------------- confidence

def _findings(*pairs):
    return [{"id": i, "status": s, "severity": "medium"} for i, s in pairs]


def test_confidence_high_on_clean_page():
    c = reviews.review_confidence({"word_count": 800}, _findings(("geo.aeo", "pass")))
    assert c["level"] == "high" and c["reasons"] == ["full HTML analysed"]


def test_confidence_low_on_challenge():
    c = reviews.review_confidence({"word_count": 800, "challenge": {"detected": True}}, [])
    assert c["level"] == "low"
    assert any("bot-protection challenge" in r for r in c["reasons"])


def test_confidence_low_on_no_content():
    c = reviews.review_confidence({"word_count": 4}, _findings(("geo.no_content", "fail")))
    assert c["level"] == "low"


def test_confidence_medium_on_js_rendered():
    c = reviews.review_confidence({"word_count": 800}, _findings(("geo.js_rendered", "warn")))
    assert c["level"] == "medium"
    assert any("JavaScript-rendered" in r for r in c["reasons"])


def test_confidence_medium_on_missing_canonical():
    c = reviews.review_confidence({"word_count": 800}, _findings(("canonical", "warn")))
    assert c["level"] == "medium"
    assert any("canonical" in r for r in c["reasons"])


def test_confidence_extra_reasons_lower_to_medium():
    c = reviews.review_confidence({"word_count": 800}, _findings(("geo.aeo", "pass")),
                                  extra_reasons=["no JSON-LD found"])
    assert c["level"] == "medium" and "no JSON-LD found" in c["reasons"]


# --------------------------------------------------------------------------- classify_findings

def test_classify_buckets():
    by_id = {
        "geo.aeo": {"id": "geo.aeo", "status": "fail", "severity": "high"},
        "geo.structure": {"id": "geo.structure", "status": "warn", "severity": "medium"},
        "schema.missing": {"id": "schema.missing", "status": "warn", "severity": "medium"},
        "geo.depth": {"id": "geo.depth", "status": "pass", "severity": "info"},
    }
    c = reviews.classify_findings(list(by_id), by_id, fix_ids={"schema.missing"})
    assert c["issues"] == 3 and c["critical_high"] == 1
    assert c["deterministic_fixes"] == 1            # schema.missing has a fix
    assert c["ai_assisted"] == 1                    # geo.aeo is editorial
    assert c["manual"] == 1                         # geo.structure


# --------------------------------------------------------------------------- contract shape

def test_summarize_returns_contract():
    report = {
        "meta": {"word_count": 800},
        "fixes": [],
        "findings": _findings(
            ("geo.aeo", "pass"), ("geo.frontload", "pass"), ("geo.chunking", "warn"),
            ("geo.definitive", "pass"), ("geo.structure", "pass"),
        ) + [{"id": "geo.aeo", "status": "pass", "severity": "info",
              "value": {"snippet": "Coffee is a brewed drink prepared from roasted beans."}}],
    }
    out = answerability.summarize(report)
    assert set(out) == _CONTRACT_KEYS
    assert out["review"] == "Answerability Review" and out["key"] == "answerability"
    assert out["verdict"] in ("strong", "partial", "weak")
    assert out["confidence"]["level"] in ("high", "medium", "low")
    assert out["likely_ai_quote"] == "Coffee is a brewed drink prepared from roasted beans."
    assert len(out["sections"]) == 6
    assert set(out["counts"]) == {"issues", "critical_high", "deterministic_fixes", "ai_assisted", "manual"}
    assert isinstance(out["related_findings"], list)


def test_summarize_likely_quote_none_when_no_aeo():
    out = answerability.summarize({"meta": {}, "fixes": [], "findings": _findings(("geo.chunking", "warn"))})
    assert out["likely_ai_quote"] is None
