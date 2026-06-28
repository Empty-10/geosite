"""AI crawler-log analytics: parse an access log and report which AI crawlers visited, what
they read, and what errored.

This is the closed-loop wedge — pairing "what the bot saw" (our renderer) with "when the bot
actually came" (the logs). Deterministic and VERIFIED: every number is read straight from the
log lines, reproducible on re-run.

v1 parses the Combined Log Format (Nginx/Apache default), which carries the user-agent:
    1.2.3.4 - - [10/Oct/2025:13:55:36 +0000] "GET /path HTTP/1.1" 200 1234 "ref" "user-agent"
A Cloudflare/Vercel log connector can feed the same analyzer later.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict, namedtuple
from datetime import datetime

from .models import BotActivity, Confidence, Finding, LogReport, Pillar, Severity, Status

# One request (or a pre-aggregated group of `count` identical requests) to feed the aggregator.
# Both the access-log parser and the Cloudflare connector emit these, so they share one analyzer.
Record = namedtuple("Record", "ua path status count ts nbytes")

C = Confidence.VERIFIED

# AI / LLM crawlers, most-specific patterns first (so "Applebot-Extended" wins over "Applebot").
# category: "training" (building corpora) | "search" (answer/RAG index) | "user" (live fetch for
# a user's question). search + user are the GEO-positive signals — an engine actively reading you
# to answer and cite. Patterns are matched case-insensitively as substrings of the user-agent.
AI_CRAWLERS: list[tuple[str, str, str, str]] = [
    # pattern, name, operator, category
    ("OAI-SearchBot", "OAI-SearchBot", "OpenAI", "search"),
    ("ChatGPT-User", "ChatGPT-User", "OpenAI", "user"),
    ("GPTBot", "GPTBot", "OpenAI", "training"),
    ("Claude-SearchBot", "Claude-SearchBot", "Anthropic", "search"),
    ("Claude-User", "Claude-User", "Anthropic", "user"),
    ("ClaudeBot", "ClaudeBot", "Anthropic", "training"),
    ("Claude-Web", "Claude-Web", "Anthropic", "user"),
    ("anthropic-ai", "anthropic-ai", "Anthropic", "training"),
    ("PerplexityBot", "PerplexityBot", "Perplexity", "search"),
    ("Perplexity-User", "Perplexity-User", "Perplexity", "user"),
    ("Applebot-Extended", "Applebot-Extended", "Apple", "training"),
    ("Applebot", "Applebot", "Apple", "search"),
    ("Bytespider", "Bytespider", "ByteDance", "training"),
    ("CCBot", "CCBot", "Common Crawl", "training"),
    ("Amazonbot", "Amazonbot", "Amazon", "search"),
    ("meta-externalagent", "Meta-ExternalAgent", "Meta", "training"),
    ("FacebookBot", "FacebookBot", "Meta", "training"),
    ("cohere-ai", "cohere-ai", "Cohere", "training"),
    ("DuckAssistBot", "DuckAssistBot", "DuckDuckGo", "search"),
    ("YouBot", "YouBot", "You.com", "search"),
    ("MistralAI-User", "MistralAI-User", "Mistral", "user"),
    ("Diffbot", "Diffbot", "Diffbot", "training"),
    ("Timpibot", "Timpibot", "Timpi", "training"),
    ("PetalBot", "PetalBot", "Huawei", "search"),
    # Major search crawlers that also feed AI answer products (AI Overviews, Copilot).
    ("Googlebot", "Googlebot", "Google", "search"),
    ("bingbot", "Bingbot", "Microsoft", "search"),
]

# Combined Log Format: ip ident user [time] "method path proto" status bytes "referer" "ua"
_LINE = re.compile(
    r'^(?P<ip>\S+)\s+\S+\s+\S+\s+\[(?P<time>[^\]]+)\]\s+'
    r'"(?P<method>[A-Z]+)\s+(?P<path>\S+)[^"]*"\s+'
    r'(?P<status>\d{3})\s+(?P<bytes>\S+)\s+'
    r'"[^"]*"\s+"(?P<ua>[^"]*)"'
)
_TIME_FMT = "%d/%b/%Y:%H:%M:%S %z"
_MAX_LINES = 200_000   # bound the work on large uploads
_TOP_PATHS = 5
_ERR_EXAMPLES = 6


def identify_bot(ua: str) -> tuple[str, str, str] | None:
    """(name, operator, category) for a known AI crawler in the user-agent, else None."""
    low = ua.lower()
    for pattern, name, operator, category in AI_CRAWLERS:
        if pattern.lower() in low:
            return name, operator, category
    return None


def analyze_logs(text: str, *, source: str = "uploaded log", max_lines: int = _MAX_LINES) -> LogReport:
    """Parse access-log text (Combined Log Format) and aggregate AI-crawler activity."""
    counts = {"lines_total": 0, "lines_parsed": 0, "lines_truncated": 0}

    def records():
        for raw in text.splitlines():
            if not raw.strip():
                continue
            counts["lines_total"] += 1
            if counts["lines_total"] > max_lines:
                counts["lines_truncated"] += 1
                continue
            m = _LINE.match(raw)
            if not m:
                continue
            counts["lines_parsed"] += 1
            nbytes = int(m["bytes"]) if m["bytes"].isdigit() else 0
            yield Record(m["ua"], m["path"], int(m["status"]), 1, _parse_time(m["time"]), nbytes)

    report = aggregate_records(records(), source=source)
    report.meta.update(counts)  # generator is fully consumed by now, so counts are final
    return report


def aggregate_records(records, *, source: str, extra_meta: dict | None = None) -> LogReport:
    """Aggregate Record stream → per-bot activity + findings → LogReport.

    Shared by the access-log parser and the Cloudflare connector so both produce identical reports.
    """
    hits: dict[str, int] = defaultdict(int)
    info: dict[str, tuple[str, str]] = {}        # name -> (operator, category)
    paths: dict[str, Counter] = defaultdict(Counter)
    statuses: dict[str, Counter] = defaultdict(Counter)
    errors: dict[str, int] = defaultdict(int)
    nbytes: dict[str, int] = defaultdict(int)
    last_seen: dict[str, str] = {}
    error_examples: list[tuple[str, str, int]] = []
    earliest: datetime | None = None
    latest: datetime | None = None

    for r in records:
        bot = identify_bot(r.ua)
        if bot is None:
            continue
        name, operator, category = bot
        info[name] = (operator, category)
        hits[name] += r.count
        paths[name][r.path] += r.count
        statuses[name][str(r.status)] += r.count
        nbytes[name] += r.nbytes
        if r.status >= 400:
            errors[name] += r.count
            if len(error_examples) < _ERR_EXAMPLES:
                error_examples.append((name, r.path, r.status))
        if r.ts is not None:
            earliest = r.ts if earliest is None or r.ts < earliest else earliest
            latest = r.ts if latest is None or r.ts > latest else latest
            iso = r.ts.isoformat()
            if name not in last_seen or iso > last_seen[name]:
                last_seen[name] = iso

    bots = [
        BotActivity(
            name=name, operator=info[name][0], category=info[name][1],
            hits=hits[name], paths=len(paths[name]), errors=errors[name],
            bytes=nbytes[name], last_seen=last_seen.get(name),
            status_counts=dict(statuses[name].most_common()),
            top_paths=paths[name].most_common(_TOP_PATHS),
        )
        for name in sorted(hits, key=lambda n: hits[n], reverse=True)
    ]
    meta = {
        "ai_requests": sum(hits.values()),
        "date_range": [earliest.isoformat() if earliest else None,
                       latest.isoformat() if latest else None],
    }
    if extra_meta:
        meta.update(extra_meta)
    return LogReport(source=source, bots=bots, findings=_findings(bots, error_examples), meta=meta)


def _parse_time(s: str) -> datetime | None:
    try:
        return datetime.strptime(s, _TIME_FMT)
    except ValueError:
        return None


def _findings(bots: list[BotActivity], error_examples: list[tuple[str, str, int]]) -> list[Finding]:
    findings: list[Finding] = []

    if not bots:
        findings.append(Finding(
            "logs.no_ai_crawlers", Pillar.GEO, "No AI crawlers seen", Status.WARN,
            Severity.MEDIUM, C, value=0,
            evidence="No known AI/LLM crawlers appear in this log window.",
            recommendation="AI engines may not be discovering your content. Confirm robots.txt "
            "and AI-crawler directives allow them, and that the site is linked/sitemapped.",
        ))
        return findings

    # Errors AI crawlers hit — the highest-value signal: requested but couldn't read/cite.
    total_errors = sum(b.errors for b in bots)
    if total_errors:
        ev = "; ".join(f"{name} → {path} ({status})" for name, path, status in error_examples)
        findings.append(Finding(
            "logs.bot_errors", Pillar.TECHNICAL, "AI crawlers hit errors", Status.FAIL,
            Severity.HIGH, C, value=total_errors, evidence=ev,
            recommendation="Answer engines requested these URLs and got 4xx/5xx — they can't read "
            "or cite them. Fix, restore, or redirect them.",
        ))

    answer_bots = [b for b in bots if b.category in ("search", "user")]
    if answer_bots:
        ev = "; ".join(f"{b.name} ({b.hits} hits)" for b in answer_bots[:5])
        findings.append(Finding(
            "logs.answer_engines_active", Pillar.GEO, "Answer engines are reading you", Status.PASS,
            Severity.INFO, C, value=len(answer_bots), evidence=ev,
            recommendation="Search/answer crawlers are actively fetching your pages — the prerequisite "
            "for being cited. Keep those pages fast, error-free and well-structured.",
        ))
    else:
        ev = "; ".join(f"{b.name} ({b.hits})" for b in bots[:5])
        findings.append(Finding(
            "logs.training_only", Pillar.GEO, "Only training crawlers seen", Status.INFO,
            Severity.INFO, C, value=len(bots), evidence=ev,
            recommendation="Training crawlers visited, but no answer-engine/RAG bots fetched your "
            "pages in this window — you may be in corpora without being actively read for answers.",
        ))

    return findings
