"""Tests for the deterministic competitor comparison (compare_reports) and the /compare endpoint."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from damask_engine import scan_html
from damask_engine.compare import compare_reports
from damask_engine.models import Report
from damask_engine.service import app

client = TestClient(app)

STRONG = """<!doctype html><html lang="en"><head>
<title>How to brew pour-over coffee: a complete guide</title>
<meta name="description" content="A clear, complete guide to brewing pour-over coffee at home,
with ratios, timings and the gear you need, in about 120 to 160 characters of summary text.">
<link rel="canonical" href="https://you.test/page">
</head><body>
<h1>How to brew pour-over coffee</h1>
<p>Pour-over coffee uses a 1 to 16 ratio of grounds to water, brewed through a paper filter over
about three minutes, producing a clean, bright cup. Here is exactly how to do it at home.</p>
<ul><li>Use 30 grams of coffee to 500 grams of water</li><li>Bloom for 30 seconds first</li></ul>
<h2>What grind size works best?</h2><p>A medium-fine grind, similar to table salt, works best for
most pour-over brewers and keeps the total brew time near three minutes.</p>
</body></html>"""

WEAK = "<!doctype html><html><head><title>x</title></head><body><p>buy now</p></body></html>"


def _report(html: str, url: str) -> Report:
    return scan_html(url, html, online=False)


def test_compare_structure_and_alignment():
    you, comp = _report(STRONG, "https://you.test"), _report(WEAK, "https://rival.test")
    c = compare_reports([you, comp])
    assert set(c) == {"you", "sites", "headlines", "rows", "leads", "trails"}
    assert c["you"] == 0
    assert len(c["sites"]) == 2
    assert len(c["rows"]) == 20
    # rows are aligned: each carries one score per site, same order.
    assert all(len(r["scores"]) == 2 for r in c["rows"])


def test_compare_picks_a_leader_per_row():
    you, comp = _report(STRONG, "https://you.test"), _report(WEAK, "https://rival.test")
    c = compare_reports([you, comp])
    # the strong page should lead overall and on more rows than the weak page
    assert c["headlines"][0] > c["headlines"][1]
    assert len(c["leads"]) > len(c["trails"])
    for row in c["rows"]:
        if row["best"] is not None:
            for j in row["leaders"]:
                assert row["scores"][j] == row["best"]


def test_compare_handles_errored_site():
    you = _report(STRONG, "https://you.test")
    broken = Report(url="https://down.test", meta={"error": "could not resolve host"})
    c = compare_reports([you, broken])
    assert c["sites"][1]["error"] == "could not resolve host"
    assert c["sites"][1]["headline"] is None
    # the errored site contributes no scores, so every row's leader is the live site
    assert all(row["scores"][1] is None for row in c["rows"])


def test_compare_endpoint(monkeypatch):
    you, comp = _report(STRONG, "https://you.test"), _report(WEAK, "https://rival.test")
    with patch("damask_engine.service._safe_scan", side_effect=[you, comp]):
        r = client.post("/compare", json={"urls": ["you.test", "rival.test"]})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 2
    assert body["comparison"]["headlines"][0] > body["comparison"]["headlines"][1]


def test_compare_endpoint_needs_two_urls():
    assert client.post("/compare", json={"urls": ["only.test"]}).status_code == 400
    assert client.post("/compare", json={}).status_code == 422
