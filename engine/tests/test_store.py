"""Tests for the SQLite scan-history store + report diffing. Uses a temp DB via ASTOVA_DB_PATH."""

from __future__ import annotations

import pytest

from astova_engine import store


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("ASTOVA_DB_PATH", str(tmp_path / "test.db"))
    return store


def _report(url="https://x.test", score=80, findings=None, created="2026-06-01T00:00:00+00:00"):
    return {
        "url": url,
        "fetched_at": created,
        "overall_score": score,
        "pillar_scores": {"technical": score},
        "findings": findings or [],
        "meta": {},
    }


def _f(fid, status, title="t"):
    return {"id": fid, "title": title, "status": status}


# --- enablement --------------------------------------------------------------------------

def test_disabled_when_env_unset(monkeypatch):
    monkeypatch.delenv("ASTOVA_DB_PATH", raising=False)
    assert store.is_enabled() is False
    assert store.save(_report()) is None
    assert store.history("https://x.test") == []
    assert store.get(1) is None


# --- save / get / history ----------------------------------------------------------------

def test_save_and_get_roundtrip(db):
    scan_id = db.save(_report(score=72))
    assert isinstance(scan_id, int)
    got = db.get(scan_id)
    assert got["overall_score"] == 72


def test_history_newest_first(db):
    db.save(_report(score=60, created="2026-06-01T00:00:00+00:00"))
    db.save(_report(score=70, created="2026-06-02T00:00:00+00:00"))
    db.save(_report(score=80, created="2026-06-03T00:00:00+00:00"))
    rows = db.history("https://x.test")
    assert [r["score"] for r in rows] == [80, 70, 60]


def test_history_filters_by_url_and_kind(db):
    db.save(_report(url="https://a.test", score=50))
    db.save({**_report(url="https://b.test", score=90), "scan_type": "site"})
    assert len(db.history("https://a.test")) == 1
    assert db.history("https://b.test", kind="page") == []  # it was saved as kind "site"
    assert len(db.history("https://b.test", kind="site")) == 1


def test_previous_returns_prior_same_url(db):
    first = db.save(_report(score=60))
    second = db.save(_report(score=75))
    prev = db.previous("https://x.test", kind="page", before_id=second)
    assert prev["overall_score"] == 60
    assert db.previous("https://x.test", kind="page", before_id=first) is None


# --- diffing -----------------------------------------------------------------------------

def test_diff_score_and_pillar_delta():
    old = _report(score=70)
    new = _report(score=82)
    d = store.diff_reports(old, new)
    assert d["score_delta"] == 12
    assert d["pillar_deltas"]["technical"] == 12
    assert d["since"] == old["fetched_at"]


def test_diff_resolved_regressed_and_new():
    old = _report(findings=[_f("a", "fail", "A"), _f("b", "pass", "B"), _f("c", "warn", "C")])
    new = _report(findings=[_f("a", "pass", "A"), _f("b", "fail", "B"), _f("d", "fail", "D")])
    d = store.diff_reports(old, new)
    assert {x["id"] for x in d["resolved"]} == {"a", "c"}   # a fixed; c vanished while an issue
    assert {x["id"] for x in d["regressed"]} == {"b"}        # b pass -> fail
    assert {x["id"] for x in d["new_issues"]} == {"d"}       # d appeared failing
