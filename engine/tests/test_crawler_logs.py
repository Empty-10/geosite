"""Tests for AI crawler-log analytics — parsing, bot identification, aggregation, findings.
Offline: operates on fixed log strings."""

from __future__ import annotations

from damask_engine.crawler_logs import analyze_logs, identify_bot


def _line(ua: str, path: str = "/", status: int = 200, ts: str = "10/Oct/2025:13:55:36 +0000") -> str:
    return f'66.249.66.1 - - [{ts}] "GET {path} HTTP/1.1" {status} 1234 "-" "{ua}"'


GPTBOT = "Mozilla/5.0 AppleWebKit/537.36 (compatible; GPTBot/1.1; +https://openai.com/gptbot)"
CLAUDEBOT = "Mozilla/5.0 (compatible; ClaudeBot/1.0; +claudebot@anthropic.com)"
PERPLEXITY = "Mozilla/5.0 (compatible; PerplexityBot/1.0; +https://perplexity.ai/bot)"
HUMAN = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) Safari/605.1.15"


# --- bot identification ------------------------------------------------------------------

def test_identify_known_bots_and_category():
    assert identify_bot(GPTBOT) == ("GPTBot", "OpenAI", "training")
    assert identify_bot(PERPLEXITY) == ("PerplexityBot", "Perplexity", "search")
    assert identify_bot("ChatGPT-User/1.0") == ("ChatGPT-User", "OpenAI", "user")


def test_specific_pattern_wins_over_general():
    # Applebot-Extended must not be mis-tagged as the base Applebot
    assert identify_bot("Applebot-Extended/1.0") == ("Applebot-Extended", "Apple", "training")
    assert identify_bot("Applebot/0.1") == ("Applebot", "Apple", "search")


def test_human_user_agent_is_not_a_bot():
    assert identify_bot(HUMAN) is None


# --- aggregation -------------------------------------------------------------------------

def test_aggregates_hits_paths_and_ignores_humans():
    log = "\n".join([
        _line(GPTBOT, "/a"),
        _line(GPTBOT, "/a"),
        _line(GPTBOT, "/b"),
        _line(HUMAN, "/a"),  # ignored
        _line(PERPLEXITY, "/a"),
    ])
    report = analyze_logs(log)
    bots = {b.name: b for b in report.bots}
    assert bots["GPTBot"].hits == 3
    assert bots["GPTBot"].paths == 2  # /a and /b
    assert bots["PerplexityBot"].hits == 1
    assert report.meta["ai_requests"] == 4
    assert report.meta["lines_parsed"] == 5  # human line parses, just isn't a bot


def test_date_range_extracted():
    log = "\n".join([
        _line(GPTBOT, "/a", ts="10/Oct/2025:08:00:00 +0000"),
        _line(GPTBOT, "/b", ts="11/Oct/2025:09:30:00 +0000"),
    ])
    report = analyze_logs(log)
    lo, hi = report.meta["date_range"]
    assert lo.startswith("2025-10-10") and hi.startswith("2025-10-11")


def test_unparseable_lines_are_skipped():
    report = analyze_logs("not a log line\n" + _line(GPTBOT))
    assert report.meta["ai_requests"] == 1
    assert report.meta["lines_total"] == 2


# --- findings ----------------------------------------------------------------------------

def test_bot_errors_finding_high_value():
    log = "\n".join([
        _line(CLAUDEBOT, "/pricing-2023", status=404),
        _line(GPTBOT, "/api", status=403),
        _line(PERPLEXITY, "/ok", status=200),
    ])
    f = {x.id: x for x in analyze_logs(log).findings}
    assert "logs.bot_errors" in f
    assert f["logs.bot_errors"].status.value == "fail"
    assert f["logs.bot_errors"].value == 2
    assert "pricing-2023" in f["logs.bot_errors"].evidence


def test_answer_engines_active_finding():
    f = {x.id: x for x in analyze_logs(_line(PERPLEXITY)).findings}
    assert "logs.answer_engines_active" in f
    assert f["logs.answer_engines_active"].status.value == "pass"


def test_training_only_finding():
    f = {x.id: x for x in analyze_logs(_line(GPTBOT)).findings}
    assert "logs.training_only" in f
    assert "logs.answer_engines_active" not in f


def test_no_ai_crawlers_finding():
    f = {x.id: x for x in analyze_logs(_line(HUMAN)).findings}
    assert "logs.no_ai_crawlers" in f
    assert f["logs.no_ai_crawlers"].status.value == "warn"


def test_to_dict_shape():
    d = analyze_logs(_line(GPTBOT, status=404)).to_dict()
    assert d["scan_type"] == "logs"
    assert d["bots"][0]["name"] == "GPTBot"
    assert isinstance(d["bots"][0]["top_paths"][0], list)  # tuples → lists for JSON
    assert d["findings"]
