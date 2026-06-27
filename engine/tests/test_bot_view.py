"""Tests for the 'what the AI bot saw' fetch-as-bot reconciliation + its scorecard surfacing."""

from __future__ import annotations

from damask_engine.fetch import BotFetch
from damask_engine.models import Pillar, Severity, Status
from damask_engine.modules import bot_view
from damask_engine.scorecard import build_scorecard
from damask_engine.models import Report, Finding, Confidence


def _one(normal_status, normal_words, bot):
    out = bot_view.analyze(normal_status, normal_words, bot)
    assert len(out) == 1
    return out[0]


def test_no_bot_no_finding():
    assert bot_view.analyze(200, 500, None) == []


def test_served_same_passes():
    f = _one(200, 500, BotFetch(status_code=200, word_count=480, final_url="https://x.test"))
    assert f.id == "geo.bot_access" and f.pillar == Pillar.GEO
    assert f.status == Status.PASS
    assert f.value["blocked"] is False


def test_hard_block_is_critical_fail():
    f = _one(200, 500, BotFetch(status_code=403, word_count=0, final_url="https://x.test"))
    assert f.status == Status.FAIL and f.severity == Severity.CRITICAL
    assert f.value["blocked"] is True
    assert "robots.txt" in f.recommendation


def test_network_error_to_bot_is_block():
    f = _one(200, 500, BotFetch(status_code=0, word_count=0, final_url="https://x.test", error="timed out"))
    assert f.status == Status.FAIL and f.value["blocked"] is True


def test_soft_block_when_served_far_less():
    f = _one(200, 500, BotFetch(status_code=200, word_count=40, final_url="https://x.test"))
    assert f.status == Status.WARN and f.severity == Severity.HIGH
    assert f.value["blocked"] is False


def test_block_leads_the_scorecard_verdict():
    findings = [
        Finding("geo.bot_access", Pillar.GEO, "AI crawler access", Status.FAIL, Severity.CRITICAL,
                Confidence.VERIFIED, value={"blocked": True, "bot_status": 403}),
        Finding("title.length", Pillar.ONPAGE, "Title", Status.PASS),
    ]
    card = build_scorecard(Report(url="https://x.test", findings=findings))
    assert card["summary"]["verdict"].startswith("AI crawlers are currently blocked")
    assert card["summary"]["opportunities"][0]["text"] == "unblocking AI crawlers at your CDN/WAF"
