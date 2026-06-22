"""Fetching the target page.

For now this is a plain HTTP GET. Phase 1 adds Playwright so we render JavaScript and see
the same DOM Google/AI crawlers see — and can flag pages whose rendered DOM differs
materially from the raw HTML. Keep that boundary here so modules never fetch directly.
"""

from __future__ import annotations

from dataclasses import dataclass

import requests

USER_AGENT = "damaskbot/0.1 (+https://example.com/bot; GEO/SEO scanner)"
TIMEOUT = 20


@dataclass
class FetchResult:
    url: str
    final_url: str
    status_code: int
    html: str
    headers: dict[str, str]
    redirected: bool
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
        return FetchResult(
            url=url,
            final_url=resp.url,
            status_code=resp.status_code,
            html=resp.text,
            headers={k.lower(): v for k, v in resp.headers.items()},
            redirected=resp.url != url,
        )
    except requests.RequestException as exc:
        return FetchResult(
            url=url, final_url=url, status_code=0, html="", headers={},
            redirected=False, error=str(exc),
        )
