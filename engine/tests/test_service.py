"""Offline tests for the FastAPI engine service. `scan` is patched so no network runs."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from damask_engine.models import Report
from damask_engine.service import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_scan_returns_report_dict():
    fake = Report(
        url="https://x.test",
        overall_score=42,
        pillar_scores={"onpage": 42},
        meta={"status_code": 200},
    )
    with patch("damask_engine.service.scan", return_value=fake) as m:
        r = client.post("/scan", json={"url": "x.test"})
    assert r.status_code == 200
    body = r.json()
    assert body["overall_score"] == 42
    assert body["pillar_scores"] == {"onpage": 42}
    assert body["url"] == "https://x.test"
    m.assert_called_once_with("x.test", fixes=True)


def test_scan_surfaces_engine_error_as_200():
    """A failed fetch is a 200 with meta.error — the web route inspects that field."""
    fake = Report(url="https://x.test", meta={"error": "could not resolve host"})
    with patch("damask_engine.service.scan", return_value=fake):
        r = client.post("/scan", json={"url": "x.test"})
    assert r.status_code == 200
    assert r.json()["meta"]["error"] == "could not resolve host"


def test_scan_missing_url_is_422():
    r = client.post("/scan", json={})
    assert r.status_code == 422
