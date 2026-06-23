"""Offline tests for the FastAPI engine service. `scan`/`crawl` are patched so no network runs."""

from __future__ import annotations

import time
from unittest.mock import patch

from fastapi.testclient import TestClient

from damask_engine.models import LogReport, PageSummary, Report, SiteReport
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


def test_logs_endpoint_analyzes_text():
    line = ('66.249.66.1 - - [10/Oct/2025:13:55:36 +0000] "GET /a HTTP/1.1" 404 5 "-" '
            '"Mozilla/5.0 (compatible; ClaudeBot/1.0; +claudebot@anthropic.com)"')
    r = client.post("/logs", json={"text": line, "source": "test.log"})
    assert r.status_code == 200
    body = r.json()
    assert body["scan_type"] == "logs"
    assert body["source"] == "test.log"
    assert body["bots"][0]["name"] == "ClaudeBot"
    assert any(f["id"] == "logs.bot_errors" for f in body["findings"])


def test_logs_missing_text_is_422():
    assert client.post("/logs", json={}).status_code == 422


def test_cloudflare_logs_endpoint(monkeypatch):
    fake = LogReport(source="Cloudflare · acme.com", meta={"connector": "cloudflare"})
    captured = {}

    def fake_fetch(domain, *, days):
        captured.update(domain=domain, days=days)
        return fake

    with patch("damask_engine.service.fetch_cloudflare_logs", side_effect=fake_fetch):
        r = client.post("/cloudflare-logs", json={"domain": "acme.com", "days": 99})
    assert r.status_code == 200
    assert r.json()["scan_type"] == "logs"
    assert captured == {"domain": "acme.com", "days": 30}  # clamped to 30


def test_cloudflare_logs_missing_domain_is_422():
    assert client.post("/cloudflare-logs", json={}).status_code == 422


def test_scan_persists_and_diffs(monkeypatch, tmp_path):
    from damask_engine.models import Finding, Pillar, Severity, Status

    monkeypatch.setenv("DAMASK_DB_PATH", str(tmp_path / "s.db"))
    r1 = Report(url="https://x.test", overall_score=70, pillar_scores={"technical": 70},
                findings=[Finding("t.a", Pillar.TECHNICAL, "A", Status.FAIL, Severity.HIGH)])
    r2 = Report(url="https://x.test", overall_score=85, pillar_scores={"technical": 85},
                findings=[Finding("t.a", Pillar.TECHNICAL, "A", Status.PASS, Severity.HIGH)])

    with patch("damask_engine.service.scan", side_effect=[r1, r2]):
        first = client.post("/scan", json={"url": "x.test"}).json()
        second = client.post("/scan", json={"url": "x.test"}).json()

    assert first["meta"]["scan_id"]
    assert "diff" not in first["meta"]  # nothing to compare against yet
    assert second["meta"]["diff"]["score_delta"] == 15
    assert any(x["id"] == "t.a" for x in second["meta"]["diff"]["resolved"])

    hist = client.get("/history", params={"url": "https://x.test"}).json()
    assert len(hist["scans"]) == 2
    assert hist["scans"][0]["score"] == 85  # newest first


def test_get_scan_404_when_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("DAMASK_DB_PATH", str(tmp_path / "s.db"))
    assert client.get("/scans/999").status_code == 404
