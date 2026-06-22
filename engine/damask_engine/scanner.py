"""Orchestrator: fetch (or accept) a page, run the modules, score, return a Report."""

from __future__ import annotations

from urllib.parse import urljoin, urlparse

from .fetch import FetchResult, fetch, fetch_resource, tls_info
from .models import Report
from .modules import geo_readiness, onpage, technical
from .modules.technical import NetInputs, parse_robots
from .scoring import build_report
from .util import make_soup, visible_text, word_count


def scan_html(url: str, html: str, *, online: bool = False,
              status_code: int = 200, headers: dict | None = None,
              final_url: str | None = None, net: NetInputs | None = None) -> Report:
    """Run all modules against already-fetched HTML. Offline-safe (used by tests).

    Network-derived material (robots.txt, sitemap, TLS, redirects) is passed in via `net`
    so the modules stay pure — tests build a NetInputs from fixtures, no network needed.
    """
    headers = {k.lower(): v for k, v in (headers or {}).items()}
    final_url = final_url or url
    soup = make_soup(html)
    text = visible_text(soup)

    findings = []
    findings += onpage.analyze(soup, text)
    findings += technical.analyze(soup, final_url, status_code, headers, net=net)
    findings += geo_readiness.analyze(soup, text)

    meta = {
        "status_code": status_code,
        "final_url": final_url,
        "word_count": word_count(text),
        "online_checks": online,
    }
    return build_report(url, findings, meta)


def _gather_network(res: FetchResult) -> NetInputs:
    """Fetch the auxiliary resources the technical module parses (robots, sitemap, TLS)."""
    parsed = urlparse(res.final_url)
    if parsed.scheme not in ("http", "https"):
        return NetInputs(redirect_chain=res.redirect_chain)
    base = f"{parsed.scheme}://{parsed.netloc}"

    robots_status, robots_txt = fetch_resource(urljoin(base, "/robots.txt"))

    # Prefer a sitemap the site declares in robots.txt; fall back to the conventional path.
    sitemap_url = urljoin(base, "/sitemap.xml")
    if robots_status == 200 and robots_txt.strip():
        declared = parse_robots(robots_txt).sitemaps
        if declared:
            sitemap_url = declared[0]
    sitemap_status, sitemap_xml = fetch_resource(sitemap_url)

    tls = tls_info(parsed.hostname) if parsed.scheme == "https" and parsed.hostname else None

    return NetInputs(
        redirect_chain=res.redirect_chain,
        robots_status=robots_status,
        robots_txt=robots_txt,
        sitemap_url=sitemap_url,
        sitemap_status=sitemap_status,
        sitemap_xml=sitemap_xml,
        tls=tls,
    )


def scan(url: str) -> Report:
    """Fetch a live URL and scan it."""
    res = fetch(url)
    if res.error or not res.html:
        return Report(url=url, meta={"error": res.error or "empty response",
                                     "status_code": res.status_code})
    return scan_html(
        url, res.html, online=True, status_code=res.status_code,
        headers=res.headers, final_url=res.final_url, net=_gather_network(res),
    )
