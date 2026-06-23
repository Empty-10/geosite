"""Command line entry point: `python -m damask_engine <url> [--json]`."""

from __future__ import annotations

import argparse
import json
import sys

from .models import Report, SiteReport, Status
from .scanner import scan

_MARK = {Status.PASS: "[pass]", Status.WARN: "[warn]", Status.FAIL: "[FAIL]", Status.INFO: "[info]"}


def _print_human(report: Report) -> None:
    if report.meta.get("error"):
        print(f"Could not scan {report.url}: {report.meta['error']}")
        return

    print(f"\n  damask scan — {report.url}")
    print(f"  overall: {report.overall_score}/100   "
          f"words: {report.meta.get('word_count', '?')}   "
          f"status: {report.meta.get('status_code', '?')}\n")

    by_pillar: dict[str, list] = {}
    for f in report.findings:
        by_pillar.setdefault(f.pillar.value, []).append(f)

    for pillar, findings in by_pillar.items():
        score = report.pillar_scores.get(pillar, "-")
        print(f"  {pillar.upper()}  ({score}/100)")
        for f in findings:
            line = f"    {_MARK[f.status]} {f.title}"
            if f.recommendation and f.status in (Status.FAIL, Status.WARN):
                line += f" — {f.recommendation}"
            print(line)
        print()

    print("  labels: every check above is VERIFIED (deterministic). "
          "AI citation sampling (MEASURED) arrives in a later phase.\n")

    if report.fixes:
        print(f"  generated fixes ({len(report.fixes)}):")
        for fx in report.fixes:
            print(f"\n  ▸ {fx.title}  [{fx.kind}]  → {fx.finding_id}")
            for line in fx.content.splitlines():
                print(f"      {line}")
            if fx.note:
                print(f"      note: {fx.note}")
        print()


def _print_site(site: SiteReport) -> None:
    if site.meta.get("error"):
        print(f"Could not crawl {site.url}: {site.meta['error']}")
        return

    m = site.meta
    print(f"\n  damask site scan — {site.url}")
    print(f"  site score: {site.overall_score}/100   "
          f"pages: {m.get('pages_crawled', '?')}   "
          f"broken: {m.get('broken', 0)}   "
          f"sitemap urls: {m.get('sitemap_urls', 0)}\n")

    print("  PAGES")
    for p in sorted(site.pages, key=lambda x: x.overall_score):
        path = p.url.split("//", 1)[-1].split("/", 1)
        path = "/" + path[1] if len(path) > 1 else "/"
        title = (p.title[:42] + "…") if len(p.title) > 43 else p.title
        print(f"    [{p.overall_score:>3}] {path:<32} {title}")
    print()

    if site.site_findings:
        print("  SITE-WIDE")
        for f in site.site_findings:
            print(f"    {_MARK[f.status]} {f.title}" + (f" — {f.evidence}" if f.evidence else ""))
            if f.recommendation:
                print(f"           ↳ {f.recommendation}")
        print()

    print("  labels: every check above is VERIFIED (deterministic).\n")


def _print_logs(report) -> None:
    m = report.meta
    dr = m.get("date_range") or [None, None]
    print(f"\n  damask crawler-log analysis — {report.source}")
    print(f"  {m.get('ai_requests', 0)} AI-crawler requests of {m.get('lines_parsed', 0)} "
          f"parsed lines   range: {dr[0] or '?'} → {dr[1] or '?'}\n")

    if report.bots:
        print("  AI CRAWLERS")
        for b in report.bots:
            errs = f"  {b.errors} errors" if b.errors else ""
            print(f"    {b.name:<20} [{b.category}]  {b.operator:<14} "
                  f"{b.hits} hits · {b.paths} paths{errs}")
        print()

    if report.findings:
        print("  FINDINGS")
        for f in report.findings:
            print(f"    {_MARK[f.status]} {f.title}" + (f" — {f.evidence}" if f.evidence else ""))
            if f.recommendation:
                print(f"           ↳ {f.recommendation}")
        print()

    print("  labels: every number above is VERIFIED (read straight from the log).\n")


def main() -> None:
    ap = argparse.ArgumentParser(prog="damask", description="GEO/SEO scan engine.")
    ap.add_argument("url", nargs="?", help="URL to scan, e.g. https://example.com")
    ap.add_argument("--json", action="store_true", help="output machine-readable JSON")
    ap.add_argument("--render", action="store_true",
                    help="render JavaScript with Playwright and scan the resulting DOM "
                         "(needs the [render] extra + `playwright install chromium`)")
    ap.add_argument("--performance", action="store_true",
                    help="add the Core Web Vitals / Lighthouse pillar via PageSpeed Insights "
                         "(slow; uses PAGESPEED_API_KEY from engine/.env when set)")
    ap.add_argument("--fixes", action="store_true",
                    help="generate ready-to-paste remediation artifacts for the findings")
    ap.add_argument("--crawl", action="store_true",
                    help="crawl the whole site (bounded, polite) and report site-wide issues")
    ap.add_argument("--max-pages", type=int, default=25,
                    help="max pages to crawl with --crawl (default 25)")
    ap.add_argument("--logs", metavar="FILE",
                    help="analyze an access log (Combined Log Format) for AI-crawler activity "
                         "instead of scanning a URL")
    args = ap.parse_args()

    if args.logs:
        from .crawler_logs import analyze_logs
        with open(args.logs, encoding="utf-8", errors="replace") as fh:
            report = analyze_logs(fh.read(), source=args.logs)
        if args.json:
            print(json.dumps(report.to_dict(), indent=2))
        else:
            _print_logs(report)
        sys.exit(0)

    if not args.url:
        ap.error("a URL is required unless --logs FILE is given")

    if args.crawl:
        from .crawl import crawl
        site = crawl(args.url, max_pages=args.max_pages)
        if args.json:
            print(json.dumps(site.to_dict(), indent=2))
        else:
            _print_site(site)
        sys.exit(0 if not site.meta.get("error") else 1)

    report = scan(args.url, render=args.render, performance=args.performance, fixes=args.fixes)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        _print_human(report)

    sys.exit(0 if not report.meta.get("error") else 1)


if __name__ == "__main__":
    main()
