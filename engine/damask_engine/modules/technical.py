"""Technical / crawlability module — deterministic, VERIFIED.

Pure: every check works on parsed input (the DOM, response headers, and pre-fetched
robots.txt / sitemap.xml / TLS info handed in via `NetInputs`). The module never touches
the network itself — the scanner fetches at the boundary (`fetch.py`) and passes text in,
so robots/sitemap parsing is fully offline- and fixture-testable.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from ..models import Confidence, Finding, Pillar, Severity, Status

P = Pillar.TECHNICAL
C = Confidence.VERIFIED

# AI crawler user-agents we report on explicitly (see CLAUDE.md → GEO wedge).
AI_CRAWLERS = ["GPTBot", "ClaudeBot", "PerplexityBot", "Google-Extended", "OAI-SearchBot"]

SITEMAP_STALE_DAYS = 180
CERT_EXPIRY_WARN_DAYS = 14
# A page is "JS-dependent" when rendering reveals materially more text than the raw HTML.
JS_CONTENT_RATIO = 1.5
JS_CONTENT_MIN_DELTA = 50


@dataclass
class NetInputs:
    """Network-fetched material, gathered by the scanner and handed to the module.

    All optional: when a field is None the corresponding check is skipped (offline / tests).
    """

    redirect_chain: list[tuple[int, str]] = field(default_factory=list)
    robots_status: int | None = None
    robots_txt: str | None = None
    sitemap_url: str | None = None
    sitemap_status: int | None = None
    sitemap_xml: str | None = None
    tls: dict | None = None
    # {"raw_words": int, "rendered_words": int} when a render was attempted, else None.
    render_delta: dict | None = None


# --------------------------------------------------------------------------- parsers (pure)


@dataclass
class RobotsInfo:
    groups: dict[str, list[str]]  # user-agent (lowercased) -> its Disallow paths
    sitemaps: list[str]
    length: int

    def blocks_root(self, agent: str) -> bool:
        """True if `agent` (or the * group) is told to Disallow: /."""
        for key in (agent.lower(), "*"):
            if "/" in self.groups.get(key, []):
                return True
        return False


def parse_robots(text: str) -> RobotsInfo:
    """Parse a robots.txt into user-agent → Disallow groups and Sitemap directives.

    Handles comments, blank lines, and consecutive User-agent lines sharing one rule group
    (per the robots.txt convention).
    """
    groups: dict[str, list[str]] = {}
    sitemaps: list[str] = []
    current: list[str] = []
    last_was_agent = False

    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        field_name, _, value = line.partition(":")
        field_name = field_name.strip().lower()
        value = value.strip()

        if field_name == "user-agent":
            if not last_was_agent:
                current = []
            current.append(value.lower())
            groups.setdefault(value.lower(), [])
            last_was_agent = True
        elif field_name == "disallow":
            for agent in current or ["*"]:
                groups.setdefault(agent, []).append(value)
            last_was_agent = False
        elif field_name == "sitemap":
            if value:
                sitemaps.append(value)
            last_was_agent = False
        else:
            last_was_agent = False

    return RobotsInfo(groups=groups, sitemaps=sitemaps, length=len(text))


@dataclass
class SitemapInfo:
    kind: str  # "urlset" | "sitemapindex" | "invalid"
    count: int  # <url> entries, or child <sitemap> entries for an index
    latest_lastmod: str | None


def _localname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()  # strip XML namespace


def parse_sitemap(xml: str) -> SitemapInfo:
    """Parse a sitemap (or sitemap index): kind, entry count, newest <lastmod>."""
    try:
        root = ET.fromstring(xml.strip())
    except ET.ParseError:
        return SitemapInfo(kind="invalid", count=0, latest_lastmod=None)

    root_name = _localname(root.tag)
    if root_name == "sitemapindex":
        entries = [c for c in root if _localname(c.tag) == "sitemap"]
        kind = "sitemapindex"
    elif root_name == "urlset":
        entries = [c for c in root if _localname(c.tag) == "url"]
        kind = "urlset"
    else:
        return SitemapInfo(kind="invalid", count=0, latest_lastmod=None)

    lastmods: list[str] = []
    for e in entries:
        for child in e:
            if _localname(child.tag) == "lastmod" and child.text:
                lastmods.append(child.text.strip())
    return SitemapInfo(kind=kind, count=len(entries), latest_lastmod=max(lastmods) if lastmods else None)


def _days_since(iso_date: str) -> int | None:
    """Whole days between an ISO date (date or datetime) and now, or None if unparseable."""
    try:
        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
    except ValueError:
        try:
            dt = datetime.strptime(iso_date[:10], "%Y-%m-%d")
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).days


# ----------------------------------------------------------------------------------- module


def analyze(
    soup: BeautifulSoup,
    final_url: str,
    status_code: int,
    headers: dict[str, str],
    net: NetInputs | None = None,
) -> list[Finding]:
    net = net or NetInputs()
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

    # --- redirect chain ---
    out.extend(_redirect_checks(net.redirect_chain))

    # --- HSTS ---
    if is_https:
        hsts = "strict-transport-security" in headers
        out.append(Finding("tech.hsts", P, "HSTS header",
                           Status.PASS if hsts else Status.WARN, Severity.LOW, C, value=hsts,
                           recommendation=None if hsts else
                           "Add a Strict-Transport-Security header."))

    # --- TLS certificate ---
    if net.tls:
        out.append(_tls_check(net.tls))

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

    # --- robots.txt (parsed from pre-fetched text) ---
    if net.robots_status is not None:
        out.extend(_robots_checks(net.robots_status, net.robots_txt or ""))

    # --- sitemap.xml (parsed from pre-fetched text) ---
    if net.sitemap_status is not None:
        out.extend(_sitemap_checks(net.sitemap_status, net.sitemap_xml or ""))

    # --- JS-rendering gap (raw HTML vs rendered DOM) ---
    if net.render_delta is not None:
        out.append(_render_check(net.render_delta))

    return out


def _render_check(delta: dict) -> Finding:
    raw = delta.get("raw_words", 0)
    rendered = delta.get("rendered_words", 0)
    js_dependent = rendered >= raw * JS_CONTENT_RATIO and (rendered - raw) >= JS_CONTENT_MIN_DELTA
    if js_dependent:
        return Finding(
            "tech.render.js_dependent", P, "JavaScript-dependent content", Status.WARN,
            Severity.HIGH, C, value={"raw_words": raw, "rendered_words": rendered},
            evidence=f"raw HTML: {raw} words; rendered DOM: {rendered} words",
            recommendation="Most content appears only after JavaScript runs. AI crawlers and "
            "some search bots don't execute JS — server-render or pre-render the key content "
            "so it's in the raw HTML.",
        )
    return Finding(
        "tech.render.ok", P, "Content in raw HTML", Status.PASS, Severity.INFO, C,
        value={"raw_words": raw, "rendered_words": rendered},
        evidence=f"raw HTML: {raw} words; rendered DOM: {rendered} words",
    )


def _redirect_checks(chain: list[tuple[int, str]]) -> list[Finding]:
    if not chain:
        return []
    hops = len(chain)
    path = " → ".join(f"{code} {url}" for code, url in chain)
    # >2 hops is a real crawl/perf cost; 1–2 is normal (e.g. http→https, apex→www).
    if hops > 2:
        return [Finding("tech.redirect.chain", P, "Redirect chain", Status.WARN, Severity.LOW, C,
                        value=hops, evidence=path,
                        recommendation="Collapse the redirect chain — link straight to the "
                        "final URL so crawlers don't spend hops getting there.")]
    return [Finding("tech.redirect", P, "Redirect", Status.INFO, Severity.INFO, C,
                    value=hops, evidence=path,
                    recommendation="Reached via redirect — point internal links at the final "
                    "URL to avoid the extra hop.")]


def _tls_check(tls: dict) -> Finding:
    days = tls.get("days_remaining")
    if not isinstance(days, int):
        return Finding("tech.tls", P, "TLS certificate", Status.PASS, Severity.INFO, C,
                       value=tls.get("not_after"))
    if days < 0:
        return Finding("tech.tls", P, "TLS certificate", Status.FAIL, Severity.CRITICAL, C,
                       value=days, evidence=f"expired {-days} day(s) ago ({tls.get('not_after')})",
                       recommendation="Renew the TLS certificate immediately — it has expired.")
    if days <= CERT_EXPIRY_WARN_DAYS:
        return Finding("tech.tls", P, "TLS certificate", Status.WARN, Severity.HIGH, C,
                       value=days, evidence=f"expires in {days} day(s) ({tls.get('not_after')})",
                       recommendation="Renew the TLS certificate soon — it expires within two weeks.")
    return Finding("tech.tls", P, "TLS certificate", Status.PASS, Severity.INFO, C, value=days,
                   evidence=f"valid for {days} more day(s) ({tls.get('not_after')})")


def _robots_checks(status: int, text: str) -> list[Finding]:
    if status != 200 or not text.strip():
        return [Finding("tech.robots.missing", P, "robots.txt", Status.WARN, Severity.LOW, C,
                        value=status,
                        recommendation="Add a robots.txt so crawlers know what they may fetch.")]

    info = parse_robots(text)
    out = [Finding("tech.robots.ok", P, "robots.txt", Status.PASS, Severity.INFO, C,
                   value=info.length)]

    blocked = [name for name in AI_CRAWLERS if info.blocks_root(name)]
    out.append(Finding(
        "tech.robots.ai", P, "AI crawler access",
        Status.WARN if blocked else Status.PASS, Severity.MEDIUM, C,
        value=blocked or "allowed",
        evidence=("Disallow: / for " + ", ".join(blocked)) if blocked else None,
        recommendation=("robots.txt blocks AI crawlers (" + ", ".join(blocked) +
                        ") from the whole site — confirm that's intended; it stops them "
                        "citing you.") if blocked else None,
    ))

    out.append(Finding(
        "tech.robots.sitemap", P, "Sitemap declared in robots.txt",
        Status.PASS if info.sitemaps else Status.INFO, Severity.LOW, C,
        value=info.sitemaps or None,
        recommendation=None if info.sitemaps else
        "Reference your sitemap from robots.txt (Sitemap: https://…/sitemap.xml).",
    ))
    return out


def _sitemap_checks(status: int, xml: str) -> list[Finding]:
    if status != 200 or not xml.strip():
        return [Finding("tech.sitemap.missing", P, "XML sitemap", Status.WARN, Severity.MEDIUM, C,
                        value=status,
                        recommendation="Publish an XML sitemap at /sitemap.xml (or reference one "
                        "in robots.txt).")]

    info = parse_sitemap(xml)
    if info.kind == "invalid":
        return [Finding("tech.sitemap.invalid", P, "XML sitemap", Status.FAIL, Severity.MEDIUM, C,
                        recommendation="The sitemap isn't valid XML (no <urlset>/<sitemapindex> "
                        "root) — engines will ignore it.")]

    label = "Sitemap index" if info.kind == "sitemapindex" else "XML sitemap"
    out = [Finding("tech.sitemap", P, label, Status.PASS, Severity.INFO, C, value=info.count,
                   evidence=f"{info.count} {'sitemaps' if info.kind == 'sitemapindex' else 'URLs'}")]

    if info.latest_lastmod:
        age = _days_since(info.latest_lastmod)
        if age is not None and age > SITEMAP_STALE_DAYS:
            out.append(Finding("tech.sitemap.freshness", P, "Sitemap freshness", Status.WARN,
                               Severity.LOW, C, value=age,
                               evidence=f"newest <lastmod> is {age} days old ({info.latest_lastmod})",
                               recommendation="Sitemap looks stale — regenerate it so <lastmod> "
                               "reflects recent changes."))
        else:
            out.append(Finding("tech.sitemap.freshness", P, "Sitemap freshness", Status.PASS,
                               Severity.INFO, C, value=age, evidence=f"newest <lastmod> {info.latest_lastmod}"))
    return out
