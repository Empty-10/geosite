"""Tests for the monitoring layer (M0): the pure alert rules, the store CRUD, and /run-due."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from astova_engine import monitoring, store
from astova_engine.service import app

client = TestClient(app)

OK = {"meta": {"status_code": 200}, "overall_score": 80, "findings": []}
FAILED = {"meta": {"error": "could not resolve host", "status_code": 0}}


# --- pure rules ----------------------------------------------------------------------------

def test_first_failure_is_silent_second_alerts():
    assert monitoring.evaluate("u", FAILED, None, None, 0) == {"ok": False, "alerts": []}
    res = monitoring.evaluate("u", FAILED, None, None, 1)  # 2nd consecutive
    assert res["ok"] is False and res["alerts"][0]["type"] == "availability"


def test_fetch_failure_never_becomes_a_score_alert():
    res = monitoring.evaluate("u", FAILED, OK, {"score_delta": -90, "regressed": []}, 1)
    assert all(a["type"] == "availability" for a in res["alerts"])  # never "score"


def test_recovery_notice():
    res = monitoring.evaluate("u", OK, None, None, 3)
    assert res["ok"] and res["alerts"][0]["severity"] == "info"


def test_ai_crawler_block_is_its_own_critical_alert():
    diff = {"score_delta": -2, "regressed": [{"id": "geo.bot_access", "title": "AI crawler access"}]}
    res = monitoring.evaluate("u", OK, OK, diff, 0)
    assert any(a["type"] == "ai_crawler" and a["severity"] == "critical" for a in res["alerts"])


def test_critical_check_regression():
    diff = {"score_delta": -3, "regressed": [{"id": "schema.missing", "title": "schema"}]}
    res = monitoring.evaluate("u", OK, OK, diff, 0)
    assert any(a["type"] == "check" and a["severity"] == "critical" for a in res["alerts"])


def test_score_thresholds():
    crit = monitoring.evaluate("u", OK, OK, {"score_delta": -16, "regressed": []}, 0)
    warn = monitoring.evaluate("u", OK, OK, {"score_delta": -6, "regressed": []}, 0)
    none = monitoring.evaluate("u", OK, OK, {"score_delta": -2, "regressed": []}, 0)
    assert crit["alerts"][0]["severity"] == "critical"
    assert warn["alerts"][0]["severity"] == "warning"
    assert none["alerts"] == []


def test_first_scan_no_baseline_no_alerts():
    assert monitoring.evaluate("u", OK, None, None, 0) == {"ok": True, "alerts": []}


# --- store CRUD ----------------------------------------------------------------------------

def _db(monkeypatch, tmp_path):
    monkeypatch.setenv("ASTOVA_DB_PATH", str(tmp_path / "m.db"))


def test_monitor_crud_and_due(monkeypatch, tmp_path):
    _db(monkeypatch, tmp_path)
    mid = store.add_monitor("https://ex.test", cadence="weekly", email="a@b.c")
    assert mid and len(store.list_monitors()) == 1
    assert store.get_monitor(mid)["cadence"] == "weekly"
    # a fresh monitor is due immediately
    assert any(m["id"] == mid for m in store.due_monitors())
    # after a successful run it's scheduled forward and no longer due
    store.mark_run(mid, ok=True)
    assert not store.due_monitors()
    assert store.delete_monitor(mid) and store.list_monitors() == []


def test_mark_run_failure_streak(monkeypatch, tmp_path):
    _db(monkeypatch, tmp_path)
    mid = store.add_monitor("https://ex.test")
    store.mark_run(mid, ok=False)
    assert store.get_monitor(mid)["consecutive_failures"] == 1
    store.mark_run(mid, ok=False, now=datetime.now(timezone.utc))
    assert store.get_monitor(mid)["consecutive_failures"] == 2
    store.mark_run(mid, ok=True)
    assert store.get_monitor(mid)["consecutive_failures"] == 0


def test_record_and_list_alerts(monkeypatch, tmp_path):
    _db(monkeypatch, tmp_path)
    mid = store.add_monitor("https://ex.test")
    store.record_alert(mid, 7, {"type": "score", "severity": "warning", "summary": "drop",
                                "detail": {"score_delta": -6}})
    alerts = store.list_alerts(mid)
    assert len(alerts) == 1 and alerts[0]["detail"]["score_delta"] == -6


# --- endpoint ------------------------------------------------------------------------------

def test_run_due_endpoint(monkeypatch, tmp_path):
    _db(monkeypatch, tmp_path)
    from astova_engine.models import Report
    store.add_monitor("https://ex.test")
    monkeypatch.setattr("astova_engine.service.scan",
                        lambda url, fixes=False: Report(url=url, overall_score=80, meta={"status_code": 200}))
    body = client.post("/monitors/run-due").json()
    assert body["ran"] == 1 and body["results"][0]["ok"] is True


def test_run_due_requires_persistence(monkeypatch):
    monkeypatch.delenv("ASTOVA_DB_PATH", raising=False)
    assert client.post("/monitors/run-due").status_code == 503
