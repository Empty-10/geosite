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

USER_AGENT = "damaskbot/0.1 (+https://example.com/bot; GEO/SEO scanner)"
TIMEOUT = 20
RESOURCE_TIMEOUT = 10


@dataclass
class FetchResult:
    url: str
    final_url: str
    status_code: int
    html: str
    headers: dict[str, str]
    redirected: bool
    # Each hop that led here: (status_code, url). Empty when no redirect occurred.
    redirect_chain: list[tuple[int, str]] = field(default_factory=list)
    error: str | None = None


def fetch(url: str) -> FetchResult:
    """GET a URL, following redirects. Never raises — failures come back on `.error`."""
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*"},
            timeout=TIMEOUT,
            allow_redirects=True,
        )
        chain = [(h.status_code, h.url) for h in resp.history]
        return FetchResult(
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
