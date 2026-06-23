"""Multi-page crawl: walk a site (bounded, polite), scan each page with the existing engine,
and surface site-wide issues a single-page scan can't see — broken internal links, duplicate
titles/meta, thin pages, and sitemap coverage.

The crawl stays on one host, respects page/depth caps, de-dupes URLs, skips assets, and pauses
between requests. Per-page scans pass net=None so we don't re-fetch robots/sitemap/TLS on every
page — those are site-level concerns handled once here.
"""

from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from collections import Counter, deque
from statistics import mean
from urllib.parse import urljoin, urlparse

from .fetch import fetch, fetch_resource
from .models import Confidence, Finding, PageSummary, Pillar, Severity, SiteReport, Status
from .scanner import scan_html
from .util import make_soup, visible_text, word_count

C = Confidence.VERIFIED

# File extensions we never crawl as HTML pages.
_ASSET_EXT = {
    "pdf", "jpg", "jpeg", "png", "gif", "svg", "webp", "avif", "ico", "css", "js", "mjs",
    "zip", "gz", "tar", "rar", "7z", "mp4", "webm", "mov", "mp3", "wav", "woff", "woff2",
    "ttf", "otf", "eot", "xml", "json", "rss", "atom", "webmanifest", "txt", "csv",
}
_THIN_WORDS = 300         # pages below this are flagged as thin
_THIN_SHARE_WARN = 0.30   # warn (vs info) when more than this fraction of pages are thin
_MAX_SITEMAP_CHILDREN = 10  # cap on child sitemaps fetched from a sitemap index


def crawl(url: str, *, max_pages: int = 25, max_depth: int = 3, delay: float = 0.3) -> SiteReport:
    """Crawl a site breadth-first from `url` and return an aggregated SiteReport.

    max_pages / max_depth bound the work; delay (seconds) keeps us polite between requests.
    """
    seen: set[str] = set()
    frontier: deque[tuple[str, int]] = deque([(url, 0)])
    host: str | None = None
    pages: list[PageSummary] = []
    broken: list[dict] = []
    referrers: dict[str, set[str]] = {}  # normalized target URL -> pages that link to it
    discovered: set[str] = set()         # every internal link seen (for orphan/coverage)
    sitemap_locs: set[str] = set()

    while frontier and len(pages) < max_pages:
        current, depth = frontier.popleft()
        key = _norm(current)
        if key in seen:
            continue
        seen.add(key)

        res = fetch(current)

        # Establish the canonical host + fetch the sitemap once, from the first good response.
        if host is None and not res.error and res.final_url:
            host = urlparse(res.final_url).netloc
            sitemap_locs = _sitemap_locs(res.final_url)

        if res.error or not res.html or not (200 <= res.status_code < 300):
            broken.append({
                "url": current,
                "status": res.status_code,
                "referrers": sorted(referrers.get(key, set()))[:5],
            })
            continue

        report = scan_html(current, res.html, online=False,
                           status_code=res.status_code, final_url=res.final_url)
        soup = make_soup(res.html)
        pages.append(PageSummary(
            url=res.final_url,
            status_code=res.status_code,
            overall_score=report.overall_score,
            pillar_scores=report.pillar_scores,
            title=_title(soup),
            meta_description=_meta_desc(soup),
            word_count=word_count(visible_text(soup)),
            issues=sum(1 for f in report.findings if f.status in (Status.FAIL, Status.WARN)),
        ))

        if depth < max_depth and host:
            for link in _internal_links(soup, res.final_url, host):
                lk = _norm(link)
                referrers.setdefault(lk, set()).add(res.final_url)
                discovered.add(lk)
                if lk not in seen:
                    frontier.append((link, depth + 1))

        if delay:
            time.sleep(delay)

    if not pages:
        msg = "could not crawl any page" + (f" ({broken[0]['status']})" if broken else "")
        return SiteReport(url=url, meta={"error": msg, "broken": len(broken)})

    site_findings = _site_findings(pages, broken, discovered, sitemap_locs)
    overall = round(mean(p.overall_score for p in pages))
    return SiteReport(
        url=url,
        pages=pages,
        site_findings=site_findings,
        overall_score=overall,
        meta={
            "pages_crawled": len(pages),
            "broken": len(broken),
            "links_discovered": len(discovered),
            "sitemap_urls": len(sitemap_locs),
            "max_pages": max_pages,
            "max_depth": max_depth,
        },
    )


# --- URL helpers -------------------------------------------------------------------------

def _norm(url: str) -> str:
    """Normalize for de-duping: drop fragment, lowercase host, strip one trailing slash."""
    p = urlparse(url.split("#")[0])
    path = p.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    query = f"?{p.query}" if p.query else ""
    return f"{p.scheme}://{p.netloc.lower()}{path}{query}"


def _is_asset(path: str) -> bool:
    last = path.rsplit("/", 1)[-1]
    return "." in last and last.rsplit(".", 1)[-1].lower() in _ASSET_EXT


def _internal_links(soup, base: str, host: str) -> list[str]:
    """Same-host, crawlable <a href> links (absolute), skipping assets and non-HTTP schemes."""
    out: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
            continue
        full = urljoin(base, href).split("#")[0]
        p = urlparse(full)
        if p.scheme in ("http", "https") and p.netloc == host and not _is_asset(p.path):
            out.append(full)
    return out


def _title(soup) -> str:
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    return ""


def _meta_desc(soup) -> str:
    m = soup.find("meta", attrs={"name": "description"})
    return (m.get("content") or "").strip() if m else ""


# --- sitemap extraction ------------------------------------------------------------------

def _sitemap_locs(start: str, *, max_children: int = _MAX_SITEMAP_CHILDREN) -> set[str]:
    """Normalized <loc> URLs from /sitemap.xml (follows one level of sitemap index)."""
    parsed = urlparse(start)
    base = f"{parsed.scheme}://{parsed.netloc}"
    status, xml = fetch_resource(urljoin(base, "/sitemap.xml"))
    if status != 200 or not xml.strip():
        return set()
    return _locs_from_xml(xml, max_children)


def _locs_from_xml(xml: str, max_children: int) -> set[str]:
    try:
        root = ET.fromstring(xml.strip())
    except ET.ParseError:
        return set()
    tag = root.tag.rsplit("}", 1)[-1].lower()
    locs: set[str] = set()
    if tag == "urlset":
        for url_el in root:
            for child in url_el:
                if child.tag.rsplit("}", 1)[-1].lower() == "loc" and child.text:
                    locs.add(_norm(child.text.strip()))
    elif tag == "sitemapindex":
        child_urls = [
            child.text.strip()
            for sm in root for child in sm
            if child.tag.rsplit("}", 1)[-1].lower() == "loc" and child.text
        ][:max_children]
        for sm_url in child_urls:
            status, child_xml = fetch_resource(sm_url)
            if status == 200 and child_xml.strip():
                locs |= _locs_from_xml(child_xml, 0)  # don't recurse further than one level
    return locs


# --- site-wide findings ------------------------------------------------------------------

def _site_findings(pages: list[PageSummary], broken: list[dict],
                   discovered: set[str], sitemap_locs: set[str]) -> list[Finding]:
    findings: list[Finding] = []

    if broken:
        ev = "; ".join(
            f"{b['url']} ({b['status'] or 'error'})"
            + (f" ← {b['referrers'][0]}" if b["referrers"] else "")
            for b in broken[:5]
        )
        findings.append(Finding(
            "site.broken_links", Pillar.TECHNICAL, "Broken internal links", Status.FAIL,
            Severity.HIGH, C, value=len(broken), evidence=ev,
            recommendation="Fix or remove links pointing to these URLs — broken links waste crawl "
            "budget and signal low quality to search engines and AI crawlers.",
        ))

    dup_titles = _dupes(p.title for p in pages)
    if dup_titles:
        findings.append(Finding(
            "site.duplicate_titles", Pillar.ONPAGE, "Duplicate titles", Status.WARN,
            Severity.MEDIUM, C, value=len(dup_titles),
            evidence="; ".join(f'"{t}" ×{n}' for t, n in dup_titles[:3]),
            recommendation="Give every page a unique, descriptive <title>; duplicates compete with "
            "each other and blur what each page is about.",
        ))

    dup_meta = _dupes(p.meta_description for p in pages)
    if dup_meta:
        findings.append(Finding(
            "site.duplicate_meta", Pillar.ONPAGE, "Duplicate meta descriptions", Status.WARN,
            Severity.LOW, C, value=len(dup_meta),
            evidence="; ".join(f'"{_trim(m)}" ×{n}' for m, n in dup_meta[:3]),
            recommendation="Write a distinct meta description per page so each result is compelling "
            "on its own.",
        ))

    thin = [p for p in pages if p.word_count < _THIN_WORDS]
    if thin:
        status = Status.WARN if len(thin) > len(pages) * _THIN_SHARE_WARN else Status.INFO
        findings.append(Finding(
            "site.thin_pages", Pillar.GEO, "Thin pages", status, Severity.MEDIUM, C,
            value=len(thin),
            evidence="; ".join(f"{p.url} ({p.word_count}w)" for p in thin[:5]),
            recommendation="Expand thin pages (under 300 words) into substantive, self-contained "
            "answers — depth is what gets a page cited and ranked.",
        ))

    if sitemap_locs:
        crawled = {_norm(p.url) for p in pages}
        missing = [p.url for p in pages if _norm(p.url) not in sitemap_locs]
        orphans = [u for u in sitemap_locs if u not in discovered and u not in crawled]
        if missing or orphans:
            parts = []
            if missing:
                parts.append(f"{len(missing)} crawled page(s) not in the sitemap")
            if orphans:
                parts.append(f"{len(orphans)} sitemap URL(s) not linked internally (orphans)")
            findings.append(Finding(
                "site.sitemap_coverage", Pillar.TECHNICAL, "Sitemap coverage", Status.WARN,
                Severity.LOW, C,
                value={"missing_from_sitemap": len(missing), "orphans": len(orphans)},
                evidence="; ".join(parts),
                recommendation="Keep the XML sitemap in sync with live pages, and link to every "
                "important page internally so crawlers (and AI bots) can reach it.",
            ))

    return findings


def _dupes(values) -> list[tuple[str, int]]:
    """[(value, count)] for values that appear more than once (blanks ignored)."""
    counts = Counter(v for v in values if v)
    return [(v, n) for v, n in counts.most_common() if n > 1]


def _trim(s: str, n: int = 40) -> str:
    return s if len(s) <= n else s[:n].rstrip() + "…"
