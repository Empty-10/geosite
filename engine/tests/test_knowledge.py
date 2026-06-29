"""Tests for the finding knowledge registry (explain_finding)."""

from __future__ import annotations

from astova_engine import knowledge

_REQUIRED = {
    "finding_id", "card", "covers", "name", "summary", "confidence", "category",
    "can_astova_generate", "agent_can_automate", "human_review_required",
    "why_it_matters", "how_to_fix", "agent_guidance", "framework_examples",
    "verification", "related_findings", "reference",
}
_CATEGORIES = {"deterministic_patch", "structured_ai_task", "human_decision", "informational"}
_GENERATE = {"deterministic", "ai_assisted", "no"}
_AUTOMATE = {"always", "usually", "sometimes", "never"}


def test_explain_known_finding_has_all_fields():
    r = knowledge.explain("geo.aeo")
    assert r is not None
    assert _REQUIRED <= set(r)
    assert r["finding_id"] == "geo.aeo"
    assert r["category"] in _CATEGORIES
    assert r["agent_guidance"]  # the agent-facing section must be populated


def test_family_resolution():
    # variants of the same check resolve to one card
    assert knowledge.explain("title.length")["card"] == "title"
    assert knowledge.explain("title.missing")["card"] == "title"
    assert knowledge.explain("geo.depth")["card"] == "depth"
    assert knowledge.explain("geo.thin_content")["card"] == "depth"
    assert knowledge.explain("tech.robots.ai")["card"] == "robots_txt"


def test_card_key_lookup():
    r = knowledge.explain("aeo")  # by card key, not a finding id
    assert r is not None and r["card"] == "aeo" and r["finding_id"] is None


def test_unknown_returns_none():
    assert knowledge.explain("nope.nope") is None
    assert knowledge.explain("") is None


def test_every_card_is_well_formed():
    for c in knowledge.list_cards():
        assert c["category"] in _CATEGORIES
        assert c["can_astova_generate"] in _GENERATE
        assert c["agent_can_automate"] in _AUTOMATE
        assert c["covers"]


def test_critical_findings_are_covered():
    must_explain = [
        "geo.bot_access", "geo.js_rendered", "geo.aeo", "schema.missing", "geo.no_content",
        "canonical", "tech.robots.ai", "tech.llms_txt", "geo.trust", "perf.score", "local.nap",
    ]
    known = set(knowledge.known_finding_ids())
    missing = [f for f in must_explain if f not in known]
    assert not missing, f"knowledge base is missing critical findings: {missing}"


def test_human_decision_findings_never_auto():
    # identity/business/fact findings must never be marked auto-applicable
    for fid in ["geo.trust", "geo.entity", "geo.data_density", "local.nap", "geo.freshness"]:
        r = knowledge.explain(fid)
        assert r["agent_can_automate"] == "never", f"{fid} should never be automatable"
