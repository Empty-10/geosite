"""Fetching the target page.

For now this is a plain HTTP GET. Phase 1 adds Playwright so we render JavaScript and see
the same DOM Google/AI crawlers see — and can flag pages whose rendered DOM differs
materially from the raw HTML. Keep that boundary here so modules never fetch directly.
"""

from __future__ import annotations

import socket
import ssl
from dataclasses import dataclass, field
from datetime import datetime, timezone

import certifi
import requests

from .config import get_cloudflare

USER_AGENT = "damaskbot/0.1 (+https://example.com/bot; GEO/SEO scanner)"
# OpenAI's documented GPTBot UA — the most widely enforced AI crawler. We probe with it to see
# what AI answer engines actually receive (WAF/CDN blocks, challenge pages, cloaked content).
GPTBOT_UA = ("Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; "
             "GPTBot/1.1; +https://openai.com/gptbot")
TIMEOUT = 20
RESOURCE_TIMEOUT = 10
RENDER_TIMEOUT_MS = 15000
CF_RENDER_ENDPOINT = "https://api.cloudflare.com/client/v4/accounts/{account}/browser-rendering/content"
CF_RENDER_TIMEOUT = 35  # > the 20s networkidle0 page timeout + Cloudflare overhead


@dataclass
class FetchResult:
    url: str
    final_url: str
    status_code: int
    html: str  # raw HTML as served (the GET response body)
    headers: dict[str, str]
    redirected: bool
    # Each hop that led here: (status_code, url). Empty when no redirect occurred.
    redirect_chain: list[tuple[int, str]] = field(default_factory=list)
    # DOM after JS execution (Playwright). None when rendering was off or unavailable.
    rendered_html: str | None = None
    error: str | None = None


@dataclass
class BotFetch:
    """What an AI crawler is served — a lightweight GET under an AI-crawler user agent."""
    status_code: int
    word_count: int  # visible words in the served HTML (no JS executed — like the bot)
    final_url: str
    error: str | None = None


def fetch(url: str, *, render: bool = False) -> FetchResult:
    """GET a URL, following redirects. Never raises — failures come back on `.error`.

    With render=True, also capture the post-JavaScript DOM via Playwright (if installed)
    into `rendered_html`, so the caller can scan what a JS-executing crawler sees and flag
    pages whose content only appears after rendering. Rendering failures degrade silently
    (rendered_html stays None); the raw GET is always returned.
    """
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*"},
            timeout=TIMEOUT,
            allow_redirects=True,
        )
        chain = [(h.status_code, h.url) for h in resp.history]
        result = FetchResult(
            url=url,
            final_url=resp.url,
            status_code=resp.status_code,
            html=resp.text,
            headers={k.lower(): v for k, v in resp.headers.items()},
            redirected=bool(resp.history),
            redirect_chain=chain,
        )
    except requests.RequestException as exc:
        return FetchResult(
            url=url, final_url=url, status_code=0, html="", headers={},
            redirected=False, error=str(exc),
        )

    if render and result.html:
        result.rendered_html = render_dom(result.final_url)
    return result


def fetch_as_bot(url: str, ua: str = GPTBOT_UA) -> BotFetch:
    """GET a URL as an AI crawler to see what it's actually served — catching WAF/CDN blocks,
    challenge pages and cloaking that robots.txt parsing can't see. Lightweight (status + visible
    word count, no JS execution — exactly the bot's view). Never raises."""
    from .util import make_soup, visible_text, word_count
    try:
        resp = requests.get(url, headers={"User-Agent": ua, "Accept": "text/html,*/*"},
                            timeout=TIMEOUT, allow_redirects=True)
        words = word_count(visible_text(make_soup(resp.text))) if resp.text else 0
        return BotFetch(status_code=resp.status_code, word_count=words, final_url=resp.url)
    except requests.RequestException as exc:
        return BotFetch(status_code=0, word_count=0, final_url=url, error=str(exc))


def render_dom_cloudflare(url: str) -> str | None:
    """Return the post-JavaScript DOM via Cloudflare Browser Rendering, or None.

    A cheap, infra-free alternative to local Chromium: when CF_ACCOUNT_ID + CF_API_TOKEN are
    set (env), Cloudflare runs the headless browser and returns rendered HTML. None when the
    creds are absent or the call fails — the caller falls back to the raw HTML.
    """
    creds = get_cloudflare()
    if not creds:
        return None
    account, token = creds
    try:
        r = requests.post(
            CF_RENDER_ENDPOINT.format(account=account),
            headers={"Authorization": f"Bearer {token}", "content-type": "application/json"},
            # Wait for the SPA's JS + network to settle, else we capture the empty shell, not the
            # rendered content (networkidle0 = no in-flight requests for 500ms, capped by timeout).
            json={"url": url, "gotoOptions": {"waitUntil": "networkidle0", "timeout": 20000}},
            timeout=CF_RENDER_TIMEOUT,
        )
        if r.status_code != 200:  # incl. 429 rate-limit on the free tier → fall back to raw HTML
            return None
        html = r.json().get("result")
        return html if isinstance(html, str) and html.strip() else None
    except (requests.RequestException, ValueError):
        return None


def render_dom(url: str) -> str | None:
    """Return the post-JavaScript DOM via headless Chromium, or None if it can't.

    Playwright is an optional extra (`pip install -e ".[render]"` + `playwright install
    chromium`). If it isn't installed, or rendering errors/times out, return None so the
    engine falls back to the raw HTML rather than failing the scan.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page(user_agent=USER_AGENT)
                page.goto(url, wait_until="networkidle", timeout=RENDER_TIMEOUT_MS)
                return page.content()
            finally:
                browser.close()
    except Exception:  # noqa: BLE001 — any render failure degrades to "no rendered DOM"
        return None


def fetch_resource(url: str) -> tuple[int, str]:
    """GET an auxiliary text resource (robots.txt, sitemap.xml). (status, text); (0, "") on error.

    Lives here, not in a module, so scan modules stay pure and offline-testable — they parse
    the text we hand them and never touch the network themselves.
    """
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=RESOURCE_TIMEOUT,
                          allow_redirects=True)
        return r.status_code, r.text
    except requests.RequestException:
        return 0, ""


PAGESPEED_ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
PAGESPEED_TIMEOUT = 60


def fetch_pagespeed(url: str, api_key: str | None = None, strategy: str = "mobile") -> dict | None:
    """Call Google PageSpeed Insights for `url`. Returns the parsed JSON, or None on failure.

    Boundary helper (kept out of the module so performance.py stays a pure JSON parser).
    Works key-less at a low rate limit; pass api_key to raise it. Slow (lab run), hence the
    long timeout and opt-in nature.
    """
    params = {"url": url, "strategy": strategy, "category": "performance"}
    if api_key:
        params["key"] = api_key
    try:
        r = requests.get(PAGESPEED_ENDPOINT, params=params, timeout=PAGESPEED_TIMEOUT)
        if r.status_code != 200:
            return None
        return r.json()
    except (requests.RequestException, ValueError):
        return None


def tls_info(hostname: str, port: int = 443) -> dict | None:
    """Read the server's TLS leaf cert. Returns expiry info, or None if it can't connect.

    Uses a verifying default context, so a successful return also means the cert chain and
    hostname validated. None covers both "couldn't connect" and "cert invalid".
    """
    try:
        # Use certifi's CA bundle (a requests dependency) so verification doesn't depend on
        # system roots — some Python builds (e.g. python.org macOS) ship without them.
        ctx = ssl.create_default_context(cafile=certifi.where())
        with socket.create_connection((hostname, port), timeout=RESOURCE_TIMEOUT) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
        not_after = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z").replace(
            tzinfo=timezone.utc
        )
        issuer = dict(x[0] for x in cert.get("issuer", ())).get("organizationName")
        return {
            "not_after": not_after.isoformat(),
            "days_remaining": (not_after - datetime.now(timezone.utc)).days,
            "issuer": issuer,
        }
    except (ssl.SSLError, OSError, ValueError, KeyError):
        return None
