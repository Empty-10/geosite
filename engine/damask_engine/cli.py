"""Command line entry point: `python -m damask_engine <url> [--json]`."""

from __future__ import annotations

import argparse
import json
import sys

from .models import Report, Status
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


def main() -> None:
    ap = argparse.ArgumentParser(prog="damask", description="GEO/SEO scan engine.")
    ap.add_argument("url", help="URL to scan, e.g. https://example.com")
    ap.add_argument("--json", action="store_true", help="output machine-readable JSON")
    args = ap.parse_args()

    report = scan(args.url)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        _print_human(report)

    sys.exit(0 if not report.meta.get("error") else 1)


if __name__ == "__main__":
    main()
