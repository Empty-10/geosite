"""Tests for the Cloudflare analytics connector. HTTP (zone lookup + GraphQL) is mocked, so the
transform Cloudflare-rows -> LogReport is exercised offline, with no token or network."""

from __future__ import annotations

import astova_engine.cloudflare_logs as cf
from astova_engine.cloudflare_logs import fetch_cloudflare_logs


class _Resp:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def json(self):
        return self._payload


def _group(ua, status, path, count):
    return {"count": count, "dimensions": {"userAgent": ua, "edgeResponseStatus": str(status),
                                           "clientRequestPath": path}}


GPTBOT = "Mozilla/5.0 (compatible; GPTBot/1.1; +https://openai.com/gptbot)"
PERPLEXITY = "Mozilla/5.0 (compatible; PerplexityBot/1.0; +https://perplexity.ai/bot)"
HUMAN = "Mozilla/5.0 (Macintosh) Safari/605.1.15"


def _wire(monkeypatch, *, zone_payload, gql_payload):
    monkeypatch.setattr(cf, "_token", lambda: "test-token")
    monkeypatch.setattr(cf.requests, "get", lambda *a, **k: _Resp(zone_payload))
    monkeypatch.setattr(cf.requests, "post", lambda *a, **k: _Resp(gql_payload))


def _zone_ok():
    return {"success": True, "result": [{"id": "zone123", "name": "acme.com"}]}


def _gql_ok(groups):
    return {"data": {"viewer": {"zones": [{"httpRequestsAdaptiveGroups": groups}]}}}


def test_transform_groups_into_bot_activity(monkeypatch):
    groups = [
        _group(GPTBOT, 200, "/a", 40),
        _group(GPTBOT, 404, "/old", 5),
        _group(PERPLEXITY, 200, "/a", 12),
        _group(HUMAN, 200, "/a", 9000),  # ignored — not an AI crawler
    ]
    _wire(monkeypatch, zone_payload=_zone_ok(), gql_payload=_gql_ok(groups))

    report = fetch_cloudflare_logs("acme.com", days=7)
    assert "error" not in report.meta
    assert report.meta["connector"] == "cloudflare"
    assert report.meta["zone"] == "zone123"
    bots = {b.name: b for b in report.bots}
    assert bots["GPTBot"].hits == 45      # 40 + 5, count-weighted
    assert bots["GPTBot"].errors == 5     # the 404 group
    assert bots["PerplexityBot"].hits == 12
    assert report.meta["ai_requests"] == 57
    ids = {f.id for f in report.findings}
    assert "logs.bot_errors" in ids
    assert "logs.answer_engines_active" in ids  # PerplexityBot is an answer engine


def test_no_token_returns_error(monkeypatch):
    monkeypatch.setattr(cf, "_token", lambda: None)
    report = fetch_cloudflare_logs("acme.com")
    assert "CF_API_TOKEN" in report.meta["error"]


def test_zone_not_found(monkeypatch):
    _wire(monkeypatch, zone_payload={"success": True, "result": []}, gql_payload=_gql_ok([]))
    report = fetch_cloudflare_logs("acme.com")
    assert "No Cloudflare zone" in report.meta["error"]


def test_zone_lookup_permission_error(monkeypatch):
    monkeypatch.setattr(cf, "_token", lambda: "t")
    monkeypatch.setattr(cf.requests, "get",
                        lambda *a, **k: _Resp({"success": False,
                                               "errors": [{"message": "Authentication error"}]}, status=403))
    report = fetch_cloudflare_logs("acme.com")
    assert "Authentication error" in report.meta["error"]


def test_graphql_errors_hint_analytics_scope(monkeypatch):
    monkeypatch.setattr(cf, "_token", lambda: "t")
    monkeypatch.setattr(cf.requests, "get", lambda *a, **k: _Resp(_zone_ok()))
    monkeypatch.setattr(cf.requests, "post",
                        lambda *a, **k: _Resp({"errors": [{"message": "not authorized"}]}))
    report = fetch_cloudflare_logs("acme.com")
    assert "not authorized" in report.meta["error"]
    assert "Analytics Read" in report.meta["error"]


def test_to_dict_shape_for_cloudflare(monkeypatch):
    _wire(monkeypatch, zone_payload=_zone_ok(), gql_payload=_gql_ok([_group(GPTBOT, 200, "/a", 3)]))
    d = fetch_cloudflare_logs("acme.com").to_dict()
    assert d["scan_type"] == "logs"
    assert d["source"] == "Cloudflare · acme.com"
    assert d["bots"][0]["name"] == "GPTBot"
