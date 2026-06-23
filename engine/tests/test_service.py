"""Offline tests for the FastAPI engine service. `scan`/`crawl` are patched so no network runs."""

from __future__ import annotations

import time
from unittest.mock import patch

from fastapi.testclient import TestClient

from damask_engine.models import PageSummary, Report, SiteReport
from damask_engine.service import app

client = TestClient(app)


def _poll(job_id: str, tries: int = 100):
    """Poll a crawl job until it leaves 'running' (the background thread is near-instant here)."""
    for _ in range(tries):
        body = client.get(f"/crawl/{job_id}").json()
        if body["status"] != "running":
            return body
        time.sleep(0.02)
    return body


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


def test_crawl_job_lifecycle():
    fake = SiteReport(
        url="https://x.test", overall_score=88,
        pages=[PageSummary("https://x.test/", 200, 88, title="Home")],
        meta={"pages_crawled": 1},
    )
    with patch("damask_engine.service.crawl", return_value=fake):
        start = client.post("/crawl", json={"url": "x.test", "max_pages": 5})
        assert start.status_code == 200
        assert start.json()["status"] == "running"
        body = _poll(start.json()["job_id"])
    assert body["status"] == "done"
    assert body["result"]["scan_type"] == "site"
    assert body["result"]["overall_score"] == 88
    assert body["result"]["pages"][0]["title"] == "Home"


def test_crawl_caps_max_pages():
    captured = {}

    def fake_crawl(url, *, max_pages, **kw):
        captured["max_pages"] = max_pages
        return SiteReport(url=url, overall_score=1, pages=[PageSummary(url, 200, 1)])

    with patch("damask_engine.service.crawl", side_effect=fake_crawl):
        body = _poll(client.post("/crawl", json={"url": "x.test", "max_pages": 999}).json()["job_id"])
    assert body["status"] == "done"
    assert captured["max_pages"] == 50  # clamped to _MAX_PAGES_CAP


def test_crawl_error_surfaces_as_error_status():
    fake = SiteReport(url="https://x.test", meta={"error": "could not crawl any page"})
    with patch("damask_engine.service.crawl", return_value=fake):
        body = _poll(client.post("/crawl", json={"url": "x.test"}).json()["job_id"])
    assert body["status"] == "error"
    assert "could not crawl" in body["error"]


def test_crawl_unknown_job_is_404():
    assert client.get("/crawl/does-not-exist").status_code == 404
