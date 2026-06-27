"""Orchestrator: fetch (or accept) a page, run the modules, score, return a Report."""

from __future__ import annotations

from urllib.parse import urljoin, urlparse

from .config import get_pagespeed_key
from .fetch import (BotFetch, FetchResult, fetch, fetch_as_bot, fetch_pagespeed, fetch_resource,
                    render_dom_cloudflare, tls_info)
from .fixes import generate_fixes
from .models import Pillar, Report
from .modules import bot_view, geo_readiness, onpage, performance, technical
from .modules.technical import NetInputs, parse_robots
from .scorecard import build_scorecard
from .scoring import build_report
from .util import make_soup, visible_text, word_count


def scan_html(url: str, html: str, *, online: bool = False,
              status_code: int = 200, headers: dict | None = None,
              final_url: str | None = None, net: NetInputs | None = None,
              performance_psi: dict | None = None, fixes: bool = False,
              bot: BotFetch | None = None, normal_raw_words: int | None = None) -> Report:
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
    findings += geo_readiness.analyze(soup, text, render_delta=net.render_delta if net else None)
    nrw = normal_raw_words if normal_raw_words is not None else word_count(text)
    findings += bot_view.analyze(status_code, nrw, bot)

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
    report = build_report(url, findings, meta, pillar_overrides=overrides)
    report.scorecard = build_scorecard(report)
    if fixes:
        report.fixes = generate_fixes(soup, report, final_url)
    return report


# Mount points that signal a client-rendered single-page app shell.
_SPA_MARKERS = ('id="root"', "id='root'", 'id="app"', "id='app'", 'id="__next"',
                'id="___gatsby"', 'id="__nuxt"', "data-reactroot", "ng-app", "ng-version")


def _looks_like_js_shell(html: str) -> bool:
    """Raw HTML with almost no visible text (or a known SPA mount) — likely client-rendered."""
    words = word_count(visible_text(make_soup(html)))
    if words >= 60:
        return False
    low = html.lower()
    return words < 15 or any(m in low for m in _SPA_MARKERS)


def _render_delta(res: FetchResult) -> dict | None:
    """Raw-vs-rendered signals for the JS-dependency check (geo.js_rendered).

    Also flags the worst cases — the H1 or JSON-LD schema existing only in the rendered DOM
    (i.e. injected by JavaScript and absent from the raw HTML an AI crawler first sees).
    """
    if res.rendered_html is None:
        return None
    raw = make_soup(res.html)
    rendered = make_soup(res.rendered_html)

    def has(soup, *args, **kwargs) -> bool:
        return soup.find(*args, **kwargs) is not None

    jsonld = {"type": "application/ld+json"}
    return {
        "raw_words": word_count(visible_text(raw)),
        "rendered_words": word_count(visible_text(rendered)),
        "h1_js_only": has(rendered, "h1") and not has(raw, "h1"),
        "schema_js_only": has(rendered, "script", attrs=jsonld) and not has(raw, "script", attrs=jsonld),
    }


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


def scan(url: str, *, render: bool = False, performance: bool = False,
         fixes: bool = False) -> Report:
    """Fetch a live URL and scan it.

    render=True captures the post-JavaScript DOM (Playwright) and scans that — what a
    JS-executing crawler sees — while flagging how much content was JS-dependent.
    performance=True adds the Core Web Vitals / Lighthouse pillar via PageSpeed Insights
    (slow; uses PAGESPEED_API_KEY from engine/.env when set, else runs key-less).
    fixes=True generates ready-to-paste remediation artifacts for the findings that fired.
    """
    res = fetch(url, render=render)
    if res.error or not res.html:
        return Report(url=url, meta={"error": res.error or "empty response",
                                     "status_code": res.status_code})

    # Smart auto-render: when the raw HTML looks like a client-rendered shell (almost no text,
    # or a known SPA mount point) and Cloudflare Browser Rendering is configured, render it so
    # we scan what a JS-executing crawler sees. SSR sites (WordPress, etc.) never trigger this.
    render_source = "playwright" if res.rendered_html else None
    if res.rendered_html is None and _looks_like_js_shell(res.html):
        cf_html = render_dom_cloudflare(res.final_url)
        if cf_html:
            res.rendered_html = cf_html
            render_source = "cloudflare"

    # Scan the rendered DOM when available (closest to what crawlers/AI see); else raw HTML.
    html_to_scan = res.rendered_html or res.html
    meta_extra = {"rendered": res.rendered_html is not None, "render_source": render_source}

    psi = None
    if performance:
        psi = fetch_pagespeed(res.final_url, get_pagespeed_key())
        meta_extra["performance_checked"] = psi is not None

    # "What the AI bot saw": fetch as GPTBot to catch WAF/CDN blocks & cloaking, and compare against
    # the raw (non-JS) word count a non-rendering crawler would also see.
    bot = fetch_as_bot(res.final_url)
    normal_raw_words = word_count(visible_text(make_soup(res.html)))

    report = scan_html(
        url, html_to_scan, online=True, status_code=res.status_code,
        headers=res.headers, final_url=res.final_url, net=_gather_network(res),
        performance_psi=psi, fixes=fixes, bot=bot, normal_raw_words=normal_raw_words,
    )
    report.meta.update(meta_extra)
    return report
