"""What the AI crawler actually saw — fetch-as-bot reconciliation.

AI answer engines crawl with their own user agents (GPTBot, ClaudeBot, PerplexityBot, …). This
module compares what a normal client is served with what an AI crawler is served, catching WAF/CDN
blocks, challenge/consent walls and cloaking that robots.txt parsing alone can't reveal. (The
separate axis — content that exists only after JavaScript runs — is handled by geo.js_rendered.)

Pure: takes the two fetch results and returns Findings. No network here.
"""

from __future__ import annotations

from ..models import Confidence, Finding, Pillar, Severity, Status

P = Pillar.GEO
C = Confidence.VERIFIED

# How much smaller the crawler's content can be (vs a normal client) before we call it a soft block.
_SHRINK = 0.5

# The actionable remediation — the same advice whether hard- or soft-blocked.
_FIX = (
    "Allow the AI crawlers you want to be cited by — GPTBot (OpenAI), ClaudeBot & anthropic-ai "
    "(Anthropic), PerplexityBot, Google-Extended, OAI-SearchBot — both in robots.txt AND at your "
    "CDN/WAF. On Cloudflare that's the 'Block AI bots' / Bot Fight Mode setting; elsewhere it's a "
    "user-agent firewall rule. If a crawler can't fetch the page, it can't cite you."
)


def analyze(normal_status: int, normal_words: int, bot, *, bot_name: str = "GPTBot") -> list[Finding]:
    """Compare a normal fetch with the AI-crawler fetch (`bot` is a BotFetch, or None offline)."""
    if bot is None:
        return []

    fid, title = "geo.bot_access", "AI crawler access"

    # Hard block: the crawler errored, or got a 4xx/5xx while a normal client got a good response.
    if bot.error or (bot.status_code >= 400 and normal_status < 400):
        detail = bot.error or f"HTTP {bot.status_code}"
        return [Finding(
            fid, P, title, Status.FAIL, Severity.CRITICAL, C,
            value={"normal_status": normal_status, "bot_status": bot.status_code,
                   "bot_words": bot.word_count, "blocked": True},
            evidence=(f"Fetched as {bot_name}: {detail}, while a normal browser gets HTTP "
                      f"{normal_status}. The AI crawler is blocked before it can read the page."),
            recommendation=_FIX,
        )]

    # Soft block / cloaking: the crawler is served far less content than a normal client.
    if normal_words >= 40 and bot.word_count < normal_words * _SHRINK:
        return [Finding(
            fid, P, title, Status.WARN, Severity.HIGH, C,
            value={"normal_status": normal_status, "bot_status": bot.status_code,
                   "normal_words": normal_words, "bot_words": bot.word_count, "blocked": False},
            evidence=(f"Fetched as {bot_name}: HTTP {bot.status_code}, {bot.word_count} words — but "
                      f"a normal browser gets {normal_words}. The crawler is served far less content "
                      f"(likely a challenge page, consent/cookie wall, or cloaking)."),
            recommendation=(_FIX + " Also remove interstitials (consent walls, JS challenges) that "
                            "serve crawlers a near-empty page."),
        )]

    # Served the same as a normal client — the crawler can read the page.
    return [Finding(
        fid, P, title, Status.PASS, Severity.INFO, C,
        value={"normal_status": normal_status, "bot_status": bot.status_code,
               "bot_words": bot.word_count, "blocked": False},
        evidence=(f"Fetched as {bot_name}: HTTP {bot.status_code}, {bot.word_count} words — served "
                  f"the same as a normal browser. AI crawlers can read this page."),
    )]
