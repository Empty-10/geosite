"""Technical / crawlability module — deterministic, VERIFIED.

In-page checks work offline from the parsed DOM + response headers. robots.txt and
sitemap checks need the network and are guarded, so the module degrades gracefully when
run offline (e.g. in tests).
"""

from __future__ import annotations

from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from ..models import Confidence, Finding, Pillar, Severity, Status

P = Pillar.TECHNICAL
C = Confidence.VERIFIED

AI_CRAWLERS = ["GPTBot", "ClaudeBot", "PerplexityBot", "Google-Extended", "OAI-SearchBot"]


def analyze(
    soup: BeautifulSoup,
    final_url: str,
    status_code: int,
    headers: dict[str, str],
    redirected: bool,
    online: bool = True,
) -> list[Finding]:
    out: list[Finding] = []
    parsed = urlparse(final_url)
    is_https = parsed.scheme == "https"

    # --- HTTPS ---
    out.append(Finding("tech.https", P, "HTTPS", Status.PASS if is_https else Status.FAIL,
                       Severity.CRITICAL, C, value=is_https,
                       recommendation=None if is_https else "Serve the site over HTTPS."))

    # --- status code ---
    if status_code:
        ok = 200 <= status_code < 300
        out.append(Finding("tech.status", P, "HTTP status",
                           Status.PASS if ok else Status.FAIL,
                           Severity.HIGH if not ok else Severity.INFO, C, value=status_code))
    if redirected:
        out.append(Finding("tech.redirect", P, "Redirect", Status.INFO, Severity.INFO, C,
                           value=final_url,
                           recommendation="Reached via redirect — make sure links point to "
                           "the final URL to avoid hops."))

    # --- HSTS ---
    if is_https:
        hsts = "strict-transport-security" in headers
        out.append(Finding("tech.hsts", P, "HSTS header",
                           Status.PASS if hsts else Status.WARN, Severity.LOW, C, value=hsts,
                           recommendation=None if hsts else
                           "Add a Strict-Transport-Security header."))

    # --- mixed content ---
    if is_https:
        insecure = [
            t.get(attr)
            for t, attr in (
                [(x, "src") for x in soup.find_all(src=True)]
                + [(x, "href") for x in soup.find_all(href=True)]
            )
            if str(t.get(attr, "")).startswith("http://")
        ]
        if insecure:
            out.append(Finding("tech.mixed_content", P, "Mixed content", Status.FAIL,
                               Severity.MEDIUM, C, value=len(insecure),
                               evidence=str(insecure[0]),
                               recommendation="Load all sub-resources over HTTPS."))
        else:
            out.append(Finding("tech.mixed_content.ok", P, "Mixed content", Status.PASS,
                               Severity.INFO, C, value=0))

    # --- mobile viewport ---
    viewport = soup.find("meta", attrs={"name": "viewport"})
    out.append(Finding("tech.viewport", P, "Mobile viewport",
                       Status.PASS if viewport else Status.WARN, Severity.MEDIUM, C,
                       value=bool(viewport),
                       recommendation=None if viewport else
                       "Add a responsive <meta name=viewport> tag."))

    # --- network checks (guarded) ---
    if online and parsed.scheme in ("http", "https"):
        base = f"{parsed.scheme}://{parsed.netloc}"
        out.extend(_robots_checks(base))
        out.extend(_sitemap_checks(base))

    return out


def _robots_checks(base: str) -> list[Finding]:
    try:
        r = requests.get(urljoin(base, "/robots.txt"), timeout=10)
    except requests.RequestException:
        return []
    if r.status_code != 200 or not r.text.strip():
        return [Finding("tech.robots.missing", P, "robots.txt", Status.WARN, Severity.LOW, C,
                        recommendation="Add a robots.txt.")]
    body = r.text
    blocked = [name for name in AI_CRAWLERS
               if f"user-agent: {name.lower()}" in body.lower() and "disallow: /" in body.lower()]
    findings = [Finding("tech.robots.ok", P, "robots.txt", Status.PASS, Severity.INFO, C,
                        value=len(body))]
    findings.append(Finding(
        "tech.robots.ai", P, "AI crawler access",
        Status.WARN if blocked else Status.PASS, Severity.MEDIUM, C, value=blocked or "allowed",
        recommendation=("robots.txt may block AI crawlers: " + ", ".join(blocked) +
                        " — confirm this is intended.") if blocked else None,
    ))
    return findings


def _sitemap_checks(base: str) -> list[Finding]:
    try:
        r = requests.get(urljoin(base, "/sitemap.xml"), timeout=10)
    except requests.RequestException:
        return []
    ok = r.status_code == 200 and "<urlset" in r.text or "<sitemapindex" in r.text
    return [Finding("tech.sitemap", P, "XML sitemap",
                    Status.PASS if ok else Status.WARN, Severity.MEDIUM, C, value=ok,
                    recommendation=None if ok else
                    "Publish an XML sitemap at /sitemap.xml (or reference one in robots.txt).")]
