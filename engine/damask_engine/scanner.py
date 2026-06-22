"""Orchestrator: fetch (or accept) a page, run the modules, score, return a Report."""

from __future__ import annotations

from .fetch import fetch
from .models import Report
from .modules import geo_readiness, onpage, technical
from .scoring import build_report
from .util import make_soup, visible_text, word_count


def scan_html(url: str, html: str, *, online: bool = False,
              status_code: int = 200, headers: dict | None = None,
              final_url: str | None = None, redirected: bool = False) -> Report:
    """Run all modules against already-fetched HTML. Offline-safe (used by tests)."""
    headers = {k.lower(): v for k, v in (headers or {}).items()}
    final_url = final_url or url
    soup = make_soup(html)
    text = visible_text(soup)

    findings = []
    findings += onpage.analyze(soup, text)
    findings += technical.analyze(soup, final_url, status_code, headers, redirected,
                                  online=online)
    findings += geo_readiness.analyze(soup, text)

    meta = {
        "status_code": status_code,
        "final_url": final_url,
        "word_count": word_count(text),
        "online_checks": online,
    }
    return build_report(url, findings, meta)


def scan(url: str) -> Report:
    """Fetch a live URL and scan it."""
    res = fetch(url)
    if res.error or not res.html:
        report = Report(url=url, meta={"error": res.error or "empty response",
                                       "status_code": res.status_code})
        return report
    return scan_html(
        url, res.html, online=True, status_code=res.status_code,
        headers=res.headers, final_url=res.final_url, redirected=res.redirected,
    )
