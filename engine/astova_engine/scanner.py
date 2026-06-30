"""Orchestrator: fetch (or accept) a page, run the modules, score, return a Report."""

from __future__ import annotations

import os
from urllib.parse import urljoin, urlparse

from . import detect
from . import project as project_mod
from .config import get_pagespeed_key
from .fetch import (BotFetch, FetchResult, fetch, fetch_as_bot, fetch_pagespeed, fetch_resource,
                    render_dom_cloudflare, tls_info)
from .fixes import generate_fixes
from .models import (ENGINE_VERSION, REPORT_VERSION, RULESET_VERSION, Confidence, Finding, Pillar,
                     Report, Severity, Status)
from .modules import bot_view, geo_readiness, local, onpage, performance, schema_review, technical
from .modules.technical import NetInputs, parse_robots
from .scorecard import build_scorecard
from .scoring import build_report
from .util import make_soup, visible_text, word_count


# Findings that are ARTIFACTS of a bot-challenge holding page (its own noindex, ~0 words, JS gate),
# not real problems with the site - dropped before scoring when a challenge is detected.
_CHALLENGE_ARTIFACTS = frozenset({
    "robots.noindex", "tech.x_robots_tag", "tech.index_conflict",
    "geo.js_rendered", "geo.no_content", "geo.thin_content", "geo.depth",
})


def _challenge_finding(challenge: dict) -> Finding:
    vendor, status, marker = challenge["vendor"], challenge["status"], challenge["marker"]
    return Finding(
        "tech.challenge", Pillar.TECHNICAL, "Bot-protection challenge", Status.FAIL,
        Severity.HIGH, Confidence.VERIFIED, value=challenge,
        evidence=f"{vendor} challenge page - HTTP {status}, matched marker '{marker}'",
        recommendation=(
            "This URL is serving a bot/security challenge page (" + vendor + "), not your content, so "
            "the score and findings below reflect the challenge page and are NOT representative of "
            "your site. Astova cannot reliably audit the real content until the challenge is removed "
            "or bypassed for legitimate crawlers (allowlist verified GPTBot/ClaudeBot or scan from an "
            "allowlisted IP), or until you scan a page that isn't behind the challenge. Then re-scan."
        ),
    )


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
    title = (soup.title.string or "").strip() if soup.title and soup.title.string else ""

    # Bot-challenge / interstitial detection: if this is a Cloudflare/Akamai/etc. holding page, the
    # HTML we're about to score is NOT the real site. Flag it as unreliable (accuracy principle).
    challenge = detect.challenge_info(status_code, headers, title, text, final_url)

    findings = []
    findings += onpage.analyze(soup, text, final_url)
    findings += schema_review.analyze(soup, final_url)
    findings += technical.analyze(soup, final_url, status_code, headers, net=net)
    findings += geo_readiness.analyze(soup, text, render_delta=net.render_delta if net else None)
    findings += local.analyze(soup, text, final_url)
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
        "engine_version": ENGINE_VERSION,
        "ruleset_version": RULESET_VERSION,
        "report_version": REPORT_VERSION,
    }

    if challenge is not None:
        # Drop the challenge-page artifacts so they don't read as real problems, then emit one
        # prominent finding in their place - before scoring.
        findings = [f for f in findings if f.id not in _CHALLENGE_ARTIFACTS]
        findings.append(_challenge_finding(challenge))
        meta["challenge"] = {"detected": True, "vendor": challenge["vendor"],
                             "status": challenge["status"]}

    report = build_report(url, findings, meta, pillar_overrides=overrides)
    report.scorecard = build_scorecard(report)
    if challenge is not None and report.scorecard is not None:
        # The number isn't trustworthy - mark it loudly rather than present a confident-but-wrong score.
        report.scorecard["unreliable"] = True
        report.scorecard["challenge"] = meta["challenge"]
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


# --------------------------------------------------------------------------- project audit

# Synthetic base used so the modules' URL-aware logic (scheme, canonical) behaves normally; the
# project audit never hits the network, so the host/scheme are placeholders.
_PROJECT_BASE = "https://project.local/"

# Findings that depend on a live HTTP response / deployment and CANNOT be determined from repo
# files - dropping them keeps the accuracy principle (we never assert what we didn't verify).
_DEPLOY_ONLY_FINDINGS = {
    "tech.https", "tech.hsts", "tech.tls", "tech.status",
    "tech.compression", "tech.x_robots_tag", "tech.redirect", "tech.redirect.chain",
}

# Findings that need the page DOM - dropped when the repo has no static HTML to read (an SSR
# framework with no build output), so we don't claim "viewport missing" we never actually saw.
_HTML_DERIVED_FINDINGS = {
    "tech.viewport", "tech.mixed_content", "tech.mixed_content.ok",
    "tech.resource_hints", "tech.index_conflict",
}

# Static HTML we'll parse if present, in priority order (the project root's own pages first, then
# common build-output dirs). Component frameworks (Next/Astro) usually have none until built.
_HTML_CANDIDATE_DIRS = ("", "out", "dist", "build", "_site")
_CONFIG_FILES = ("next.config.js", "next.config.mjs", "next.config.ts", "next.config.cjs",
                 "vercel.json", "netlify.toml", "_headers", "_redirects", ".htaccess")
_MAX_READ_BYTES = 2_000_000


def _read_text(path: str) -> str | None:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read(_MAX_READ_BYTES)
    except OSError:
        return None


def _first_existing(*paths: str) -> str | None:
    for p in paths:
        content = _read_text(p)
        if content is not None:
            return content
    return None


def _find_project_html(root: str, pub: str) -> tuple[str | None, str | None]:
    """Locate a static index.html to analyse (relpath, content), or (None, None) if the project
    has no built/static HTML - then on-page/GEO checks are skipped rather than faked."""
    seen = []
    for sub in _HTML_CANDIDATE_DIRS:
        seen.append(os.path.join(pub, sub, "index.html"))
        seen.append(os.path.join(root, sub, "index.html"))
    for path in dict.fromkeys(seen):  # de-dup, keep order
        content = _read_text(path)
        if content is not None and content.strip():
            return os.path.relpath(path, root), content
    return None, None


def _read_config_blobs(root: str, pub: str) -> list[str]:
    """Read the framework/host config files that can declare security headers (for the
    security-headers check). Reused, deterministic - just the file text, parsed by project.py."""
    blobs: list[str] = []
    for name in _CONFIG_FILES:
        text = _first_existing(os.path.join(root, name), os.path.join(pub, name))
        if text:
            blobs.append(text)
    return blobs


def scan_project(root_path: str, framework: str = "auto") -> Report:
    """Audit a project DIRECTORY (pre-deploy) and return the SAME Report a URL scan returns.

    Reads the repo's static files directly - robots.txt, llms.txt, sitemap.xml, framework/host
    config (security headers), and any static index.html - then runs the existing deterministic
    modules and scoring. Deploy-only signals (HTTPS, TLS, status, redirects, compression) are not
    knowable from source and are omitted. Never fetches the network, never writes, never fixes.

    `framework` may be "auto" (detect from root markers) or an explicit name (nextjs / astro /
    wordpress / static / gatsby / node).
    """
    root = os.path.abspath(os.path.expanduser(root_path))
    if not os.path.isdir(root):
        return Report(url=root_path,
                      meta={"scan_type": "project", "error": f"Not a directory: {root_path}"})
    try:
        markers = set(os.listdir(root))
    except OSError as exc:
        return Report(url=root_path,
                      meta={"scan_type": "project", "error": f"Cannot read {root_path}: {exc}"})

    if framework and framework.strip().lower() != "auto":
        detected, public_dir = project_mod.framework_public_dir(framework)
    else:
        detected, public_dir = project_mod.detect_framework(markers)
    pub = root if public_dir in (".", "") else os.path.join(root, public_dir)

    robots = _first_existing(os.path.join(pub, "robots.txt"), os.path.join(root, "robots.txt"))
    llms = _first_existing(os.path.join(pub, "llms.txt"), os.path.join(root, "llms.txt"))
    sitemap = _first_existing(os.path.join(pub, "sitemap.xml"), os.path.join(root, "sitemap.xml"))
    html_path, html = _find_project_html(root, pub)
    html_analyzed = bool(html and html.strip())

    sec_headers = project_mod.detect_configured_security_headers(_read_config_blobs(root, pub))
    # A non-empty headers dict makes the technical module run its header cluster so the
    # security-headers finding fires even when none are configured (compression/x-robots, which
    # need a live response, are dropped below). The sentinel key is ignored by every check.
    headers = {**sec_headers, "x-astova-project": "1"}

    net = NetInputs(
        robots_status=200 if robots is not None else 404, robots_txt=robots or "",
        sitemap_url=urljoin(_PROJECT_BASE, "/sitemap.xml"),
        sitemap_status=200 if sitemap is not None else 404, sitemap_xml=sitemap or "",
        llms_status=200 if llms is not None else 404, llms_txt=llms or "",
    )

    soup = make_soup(html or "")
    text = visible_text(soup)
    findings = list(technical.analyze(soup, _PROJECT_BASE, 0, headers, net=net))
    if html_analyzed:
        findings += onpage.analyze(soup, text, _PROJECT_BASE)
        findings += geo_readiness.analyze(soup, text)
        findings += local.analyze(soup, text, _PROJECT_BASE)

    drop = set(_DEPLOY_ONLY_FINDINGS)
    if not html_analyzed:
        drop |= _HTML_DERIVED_FINDINGS
    findings = [f for f in findings if f.id not in drop]

    meta = {
        "scan_type": "project",
        "root_path": root,
        "framework": detected,
        "public_dir": public_dir,
        "files": {
            "robots_txt": robots is not None,
            "llms_txt": llms is not None,
            "sitemap_xml": sitemap is not None,
            "html": html_path,
        },
        "html_analyzed": html_analyzed,
        "security_headers_configured": sorted(sec_headers),
        "online_checks": False,
        "engine_version": ENGINE_VERSION,
        "ruleset_version": RULESET_VERSION,
        "report_version": REPORT_VERSION,
    }
    report = build_report(root_path, findings, meta)
    report.scorecard = build_scorecard(report)
    return report
