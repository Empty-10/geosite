"""Cloudflare connector — pull AI-crawler activity from Cloudflare's GraphQL Analytics API
instead of an uploaded access log. Same analyzer, same LogReport, no file handling for the user.

Reuses the existing CF API token (CF_API_TOKEN), but that token must be granted two extra READ
scopes for this to work: **Zone → Zone (Read)** and **Zone → Analytics (Read)**. The Browser-
Rendering scope used for rendering does NOT cover analytics — extend the same token in the
Cloudflare dashboard (no new secret needed).

Failures never raise: they come back in LogReport.meta["error"], so the caller surfaces them.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import requests

from .config import get_cloudflare
from .crawler_logs import Record, aggregate_records
from .models import LogReport

CF_API = "https://api.cloudflare.com/client/v4"
CF_GRAPHQL = f"{CF_API}/graphql"
_TIMEOUT = 30
_ROW_LIMIT = 10_000  # adaptive-groups rows; top user-agent × path × status combos by count

# Adaptive HTTP request groups, available across plans (sampled). Group by the raw user-agent,
# the response status, and the path so we can map each row onto a known AI crawler.
_QUERY = """
query($zone: String!, $since: Time!, $until: Time!, $limit: Int!) {
  viewer {
    zones(filter: { zoneTag: $zone }) {
      httpRequestsAdaptiveGroups(
        limit: $limit
        filter: { datetime_geq: $since, datetime_leq: $until }
        orderBy: [count_DESC]
      ) {
        count
        dimensions { userAgent edgeResponseStatus clientRequestPath }
      }
    }
  }
}
"""


def fetch_cloudflare_logs(domain: str, *, days: int = 7, token: str | None = None) -> LogReport:
    """Pull the last `days` of AI-crawler activity for `domain` from Cloudflare analytics."""
    token = token or _token()
    if not token:
        return _err(domain, "No Cloudflare API token configured. Set CF_API_TOKEN with Zone Read "
                            "+ Analytics Read scopes.")
    headers = {"Authorization": f"Bearer {token}", "content-type": "application/json"}

    # 1. Resolve the zone tag for the domain.
    try:
        zr = requests.get(f"{CF_API}/zones", params={"name": domain}, headers=headers, timeout=_TIMEOUT)
        zd = zr.json()
    except (requests.RequestException, ValueError) as exc:
        return _err(domain, f"Cloudflare API unreachable: {exc}")
    if not zd.get("success"):
        return _err(domain, _cf_errors(zd) or f"Zone lookup failed ({zr.status_code}). "
                    "Does the token have Zone Read?")
    zones = zd.get("result") or []
    if not zones:
        return _err(domain, f"No Cloudflare zone found for {domain} — is this domain on the token's account?")
    zone_tag = zones[0]["id"]

    # 2. Query analytics for the window.
    until = datetime.now(timezone.utc).replace(microsecond=0)
    since = until - timedelta(days=days)
    variables = {"zone": zone_tag, "since": since.isoformat(), "until": until.isoformat(), "limit": _ROW_LIMIT}
    try:
        gr = requests.post(CF_GRAPHQL, headers=headers,
                           json={"query": _QUERY, "variables": variables}, timeout=_TIMEOUT)
        gd = gr.json()
    except (requests.RequestException, ValueError) as exc:
        return _err(domain, f"Cloudflare analytics unreachable: {exc}")
    if gd.get("errors"):
        return _err(domain, _gql_errors(gd) + " (does the token have Analytics Read?)")
    try:
        groups = gd["data"]["viewer"]["zones"][0]["httpRequestsAdaptiveGroups"]
    except (KeyError, IndexError, TypeError):
        return _err(domain, "Unexpected analytics response shape from Cloudflare.")

    report = aggregate_records(
        _to_records(groups),
        source=f"Cloudflare · {domain}",
        extra_meta={
            "connector": "cloudflare",
            "zone": zone_tag,
            "window_days": days,
            "rows": len(groups),
            "sampled": len(groups) >= _ROW_LIMIT,  # hit the cap → long tail may be missing
            "date_range": [since.isoformat(), until.isoformat()],
        },
    )
    return report


def _to_records(groups: list[dict]):
    for g in groups:
        dims = g.get("dimensions") or {}
        status = dims.get("edgeResponseStatus")
        yield Record(
            ua=dims.get("userAgent", ""),
            path=dims.get("clientRequestPath", "/"),
            status=int(status) if status is not None else 0,
            count=int(g.get("count", 0)),
            ts=None,
            nbytes=0,
        )


def _token() -> str | None:
    creds = get_cloudflare()
    return creds[1] if creds else None


def _err(domain: str, message: str) -> LogReport:
    return LogReport(source=f"Cloudflare · {domain}", meta={"error": message, "connector": "cloudflare"})


def _cf_errors(data: dict) -> str:
    return "; ".join(e.get("message", "") for e in (data.get("errors") or []))


def _gql_errors(data: dict) -> str:
    return "; ".join(e.get("message", "") for e in (data.get("errors") or [])) or "Analytics query failed."
