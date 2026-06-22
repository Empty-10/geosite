"""Orchestrator: fetch (or accept) a page, run the modules, score, return a Report."""

from __future__ import annotations

from urllib.parse import urljoin, urlparse

from .config import get_pagespeed_key
from .fetch import FetchResult, fetch, fetch_pagespeed, fetch_resource, tls_info
from .models import Pillar, Report
from .modules import geo_readiness, onpage, performance, technical
from .modules.technical import NetInputs, parse_robots
from .scoring import build_report
from .util import make_soup, visible_text, word_count


def scan_html(url: str, html: str, *, online: bool = False,
              status_code: int = 200, headers: dict | None = None,
              final_url: str | None = None, net: NetInputs | None = None,
              performance_psi: dict | None = None) -> Report:
    """Run all modules against already-fetched HTML. Offline-safe (used by tests).

    Network-derived material (robots.txt, sitemap, TLS, redirects, PageSpeed) is passed in
    so the modules stay pure — tests build inputs from fixtures, no network needed.
    """
    headers = {k.lower(): v for k, v in (headers or {}).items()}
    final_url = final_url or url
    soup = make_soup(html)
    text = visible_text(soup)

    findings = []
    findings += onpage.analyze(soup, text, final_url)
    findings += technical.analyze(soup, final_url, status_code, headers, net=net)
    findings += geo_readiness.analyze(soup, text)

    overrides: dict[Pillar, int] = {}
    if performance_psi is not None:
        findings += performance.analyze(performance_psi)
        perf_score = performance.pillar_score(performance_psi)
        if perf_score is not None:
            overrides[Pillar.PERFORMANCE] = perf_score

    meta = {
        "status_code": status_code,
        "final_url": final_url,
        "word_count": word_count(text),
        "online_checks": online,
    }
    return build_report(url, findings, meta, pillar_overrides=overrides)


def _render_delta(res: FetchResult) -> dict | None:
    """Visible-word counts for raw HTML vs rendered DOM, for the JS-dependency check."""
    if res.rendered_html is None:
        return None
    raw_words = word_count(visible_text(make_soup(res.html)))
    rendered_words = word_count(visible_text(make_soup(res.rendered_html)))
    return {"raw_words": raw_words, "rendered_words": rendered_words}


def _gather_network(res: FetchResult) -> NetInputs:
    """Fetch the auxiliary resources the technical module parses (robots, sitemap, TLS)."""
    parsed = urlparse(res.final_url)
    if parsed.scheme not in ("http", "https"):
        return NetInputs(redirect_chain=res.redirect_chain, render_delta=_render_delta(res))
    base = f"{parsed.scheme}://{parsed.netloc}"

    robots_status, robots_txt = fetch_resource(urljoin(base, "/robots.txt"))

    # Prefer a sitemap the site declares in robots.txt; fall back to the conventional path.
    sitemap_url = urljoin(base, "/sitemap.xml")
    if robots_status == 200 and robots_txt.strip():
        declared = parse_robots(robots_txt).sitemaps
        if declared:
            sitemap_url = declared[0]
    sitemap_status, sitemap_xml = fetch_resource(sitemap_url)
    llms_status, llms_txt = fetch_resource(urljoin(base, "/llms.txt"))

    tls = tls_info(parsed.hostname) if parsed.scheme == "https" and parsed.hostname else None

    return NetInputs(
        redirect_chain=res.redirect_chain,
        robots_status=robots_status,
        robots_txt=robots_txt,
        sitemap_url=sitemap_url,
        sitemap_status=sitemap_status,
        sitemap_xml=sitemap_xml,
        tls=tls,
        render_delta=_render_delta(res),
        llms_status=llms_status,
        llms_txt=llms_txt,
    )


def scan(url: str, *, render: bool = False, performance: bool = False) -> Report:
    """Fetch a live URL and scan it.

    render=True captures the post-JavaScript DOM (Playwright) and scans that — what a
    JS-executing crawler sees — while flagging how much content was JS-dependent.
    performance=True adds the Core Web Vitals / Lighthouse pillar via PageSpeed Insights
    (slow; uses PAGESPEED_API_KEY from engine/.env when set, else runs key-less).
    """
    res = fetch(url, render=render)
    if res.error or not res.html:
        return Report(url=url, meta={"error": res.error or "empty response",
                                     "status_code": res.status_code})
    # Scan the rendered DOM when available (closest to what crawlers/AI see); else raw HTML.
    html_to_scan = res.rendered_html or res.html
    meta_extra = {"rendered": res.rendered_html is not None}

    psi = None
    if performance:
        psi = fetch_pagespeed(res.final_url, get_pagespeed_key())
        meta_extra["performance_checked"] = psi is not None

    report = scan_html(
        url, html_to_scan, online=True, status_code=res.status_code,
        headers=res.headers, final_url=res.final_url, net=_gather_network(res),
        performance_psi=psi,
    )
    report.meta.update(meta_extra)
    return report
