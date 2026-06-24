"""Accuracy benchmark — compare our deterministic checks against Lighthouse's SEO + best-practices
audits (fetched from the PageSpeed Insights API we already use). A dev/QA tool, NOT part of the
app: run it on demand to find where we disagree with the reference tool — disagreements are either
our bugs (fix them) or legitimate differences (note them).

    python -m bench.accuracy_bench                # default URL set
    python -m bench.accuracy_bench url1 url2 ...   # custom

Validates the technical/on-page overlap only — Lighthouse has no GEO checks, so the GEO half has
no external ground truth (which is exactly why GEO scoring is a proxy).
"""

from __future__ import annotations

import sys
from collections import defaultdict

import requests

from damask_engine.config import get_pagespeed_key
from damask_engine.scanner import scan

PSI = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

DEFAULT_URLS = [
    "https://example.com",
    "https://stripe.com",
    "https://www.bbc.com/news",
    "https://developer.mozilla.org/en-US/docs/Web/HTML",
    "https://en.wikipedia.org/wiki/Search_engine_optimization",
    "https://techcrunch.com",          # WordPress
    "https://www.cloudflare.com",
    "https://sentoma.com",             # client-rendered SPA
]

# Lighthouse audit id → the set of our finding ids that represent the same dimension.
# (We fail the dimension if any present finding is warn/fail; pass if present and pass/info.)
MAP: dict[str, set[str]] = {
    "document-title": {"title.missing", "title.length"},
    "meta-description": {"meta.description.missing", "meta.description.length"},
    "http-status-code": {"tech.status"},
    "is-crawlable": {"robots.indexable", "robots.noindex", "tech.x_robots_tag"},
    "robots-txt": {"tech.robots.ok", "tech.robots.missing"},
    "image-alt": {"images.alt"},
    "canonical": {"canonical"},
    "viewport": {"tech.viewport"},
    "link-text": {"onpage.links"},
    "is-on-https": {"tech.https"},
    "uses-https": {"tech.https"},
    "redirects": {"tech.redirect", "tech.redirect.chain"},
    # Lighthouse audits we deliberately don't cover yet (coverage gaps):
    "crawlable-anchors": set(),  # whether anchors have valid hrefs — different from anchor-text quality
    "hreflang": set(),
    "font-size": set(),
    "tap-targets": set(),
    "charset": set(),
    "doctype": set(),
    "structured-data": set(),  # LH treats this as a manual audit (no binary score)
}


def lighthouse_audits(url: str, key: str | None) -> dict | None:
    params = [("url", url), ("category", "seo"), ("category", "best-practices"), ("strategy", "mobile")]
    if key:
        params.append(("key", key))
    try:
        r = requests.get(PSI, params=params, timeout=60)
        if r.status_code != 200:
            return None
        return r.json().get("lighthouseResult", {}).get("audits", {})
    except (requests.RequestException, ValueError):
        return None


def our_result(byid: dict, check_ids: set[str]) -> str | None:
    """'pass' / 'fail' for the dimension, or None if we don't assess it on this page."""
    present = [byid[c] for c in check_ids if c in byid]
    if not present:
        return None
    failed = any(f["status"] in ("warn", "fail") for f in present)
    return "fail" if failed else "pass"


def main() -> None:
    urls = sys.argv[1:] or DEFAULT_URLS
    key = get_pagespeed_key()
    print(f"PageSpeed key: {'set' if key else 'MISSING (keyless PSI is rate-limited — results may be sparse)'}\n")

    # per-dimension tallies + the disagreement list
    agree: dict[str, int] = defaultdict(int)
    disagree: dict[str, int] = defaultdict(int)
    na: dict[str, int] = defaultdict(int)
    gaps: set[str] = set()
    rows: list[tuple] = []

    for url in urls:
        print(f"• {url}")
        report = scan(url)
        if report.meta.get("error"):
            print(f"    scan error: {report.meta['error']}")
            continue
        byid = {f["id"]: f for f in (x.to_dict() for x in report.findings)}
        audits = lighthouse_audits(url, key)
        if audits is None:
            print("    Lighthouse unavailable (PSI failed/rate-limited)")
            continue

        for lh_id, check_ids in MAP.items():
            audit = audits.get(lh_id)
            if not audit:
                continue
            score = audit.get("score")
            if score not in (0, 1):  # skip manual/informative/not-applicable
                continue
            lh = "pass" if score == 1 else "fail"
            if not check_ids:
                gaps.add(lh_id)
                continue
            ours = our_result(byid, check_ids)
            if ours is None:
                na[lh_id] += 1
                continue
            if ours == lh:
                agree[lh_id] += 1
            else:
                disagree[lh_id] += 1
                rows.append((url, lh_id, lh, ours))

    print("\n=== per-check agreement (technical/on-page overlap with Lighthouse) ===")
    dims = sorted(set(agree) | set(disagree) | set(na))
    for d in dims:
        a, x, n = agree[d], disagree[d], na[d]
        total = a + x
        rate = f"{round(100*a/total)}%" if total else "—"
        print(f"  {d:<22} agree {a:>2}  disagree {x:>2}  n/a {n:>2}   ({rate})")

    if rows:
        print("\n=== disagreements to review (us vs Lighthouse) ===")
        for url, lh_id, lh, ours in rows:
            print(f"  [{lh_id}] {url}\n      Lighthouse: {lh}   ·   us: {ours}")

    if gaps:
        print("\n=== Lighthouse checks we don't cover (coverage gaps) ===")
        print("  " + ", ".join(sorted(gaps)))


if __name__ == "__main__":
    main()
