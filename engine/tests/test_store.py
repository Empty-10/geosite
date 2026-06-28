"""Tests for the scan-history store + report diffing.

Runs against both backends behind the store seam:
- **SQLite** always (temp DB via ASTOVA_DB_PATH).
- **Postgres** only when ASTOVA_TEST_DATABASE_URL is set (e.g. a throwaway Supabase/Postgres);
  otherwise those params skip. The Postgres variant truncates the three tables before each test,
  so point it at a scratch database, never production.
"""

from __future__ import annotations

import os

import pytest

from astova_engine import store


@pytest.fixture(params=["sqlite", "postgres"])
def db(request, tmp_path, monkeypatch):
    monkeypatch.delenv("ASTOVA_DATABASE_URL", raising=False)
    monkeypatch.delenv("ASTOVA_DB_PATH", raising=False)
    if request.param == "postgres":
        url = os.environ.get("ASTOVA_TEST_DATABASE_URL")
        if not url:
            pytest.skip("set ASTOVA_TEST_DATABASE_URL to run the Postgres store tests")
        monkeypatch.setenv("ASTOVA_DATABASE_URL", url)
        with store._conn() as d:  # clean slate; _conn() auto-creates the schema on first use
            for t in ("alerts", "monitors", "scans"):
                d.execute(f"TRUNCATE TABLE {t} RESTART IDENTITY CASCADE")
    else:
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
    monkeypatch.delenv("ASTOVA_DATABASE_URL", raising=False)
    assert store.is_enabled() is False
    assert store.save(_report()) is None
    assert store.history("https://x.test") == []
    assert store.get(1) is None
    assert store.add_monitor("https://x.test") is None
    assert store.list_monitors() == []


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


# --- monitors + alerts -------------------------------------------------------------------


def test_monitor_lifecycle(db):
    mid = db.add_monitor("https://m.test", cadence="weekly", email="a@b.test")
    assert isinstance(mid, int)
    m = db.get_monitor(mid)
    assert m["url"] == "https://m.test" and m["cadence"] == "weekly"
    assert [x["id"] for x in db.list_monitors()] == [mid]
    assert db.delete_monitor(mid) is True
    assert db.get_monitor(mid) is None


def test_due_and_mark_run(db):
    mid = db.add_monitor("https://m.test")  # created due immediately
    assert mid in [m["id"] for m in db.due_monitors()]
    db.mark_run(mid, ok=True)
    assert mid not in [m["id"] for m in db.due_monitors()]  # next_run advanced past now
    assert db.get_monitor(mid)["consecutive_failures"] == 0
    db.mark_run(mid, ok=False)
    assert db.get_monitor(mid)["consecutive_failures"] == 1


def test_alerts_roundtrip_and_detail_json(db):
    mid = db.add_monitor("https://m.test")
    aid = db.record_alert(
        mid,
        None,
        {
            "type": "score_drop",
            "severity": "critical",
            "summary": "down 20",
            "detail": {"from": 80, "to": 60},
        },
    )
    assert isinstance(aid, int)
    alerts = db.list_alerts(mid)
    assert len(alerts) == 1
    assert alerts[0]["detail"] == {"from": 80, "to": 60}  # round-tripped from JSON text
    db.delete_monitor(mid)
    assert db.list_alerts(mid) == []  # alerts cascade-deleted


# --- diffing (pure, backend-independent) -------------------------------------------------


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
    assert {x["id"] for x in d["resolved"]} == {"a", "c"}  # a fixed; c vanished while an issue
    assert {x["id"] for x in d["regressed"]} == {"b"}  # b pass -> fail
    assert {x["id"] for x in d["new_issues"]} == {"d"}  # d appeared failing
