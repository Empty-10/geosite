"""Local-AEO readiness — deterministic checks for local-business pages: NAP, LocalBusiness
schema, opening hours, geo/map, and a Google Business Profile link. AI answer engines lean on
these for "near me" and local queries.

CONDITIONAL: emits nothing unless the page shows local-business signals (a tel: link, a postal
address in schema, a LocalBusiness schema, or a maps embed) — so a SaaS landing page is never
penalised for lacking a storefront. Pure + offline-testable.
"""

from __future__ import annotations

import json

from bs4 import BeautifulSoup

from ..models import Confidence, Finding, Pillar, Severity, Status

P = Pillar.GEO  # local readiness rolls up under GEO for the first slice
C = Confidence.VERIFIED

# schema.org LocalBusiness + common subtypes (lower-cased).
LOCAL_TYPES = {
    "localbusiness", "restaurant", "store", "cafeorcoffeeshop", "bar", "hotel", "lodgingbusiness",
    "foodestablishment", "professionalservice", "medicalbusiness", "dentist", "physician",
    "lawyer", "legalservice", "homeandconstructionbusiness", "generalcontractor", "plumber",
    "electrician", "autorepair", "automotivebusiness", "realestateagent", "financialservice",
    "healthandbeautybusiness", "beautysalon", "hairsalon", "gym", "sportsactivitylocation",
    "childcare", "school", "veterinarycare", "emergencyservice", "bakery", "barorpub",
    "touristattraction", "entertainmentbusiness", "nightclub", "shoppingcenter",
}


def _jsonld_nodes(soup: BeautifulSoup) -> list[dict]:
    out: list[dict] = []
    for s in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = s.string or s.get_text() or ""
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        stack = list(data) if isinstance(data, list) else [data]
        while stack:
            n = stack.pop()
            if isinstance(n, list):
                stack.extend(n)
            elif isinstance(n, dict):
                g = n.get("@graph")
                if isinstance(g, list):
                    stack.extend(g)
                out.append(n)
    return out


def _types(node: dict) -> set[str]:
    t = node.get("@type")
    if isinstance(t, list):
        return {str(x).lower() for x in t}
    return {str(t).lower()} if t else set()


def _postal(node: dict) -> bool:
    a = node.get("address")
    if isinstance(a, dict):
        return bool(a.get("streetAddress") or a.get("postalCode"))
    if isinstance(a, str):
        return len(a.split()) >= 3
    return "postaladdress" in _types(node)


def _has_geo(node: dict) -> bool:
    g = node.get("geo")
    if isinstance(g, dict):
        return bool(g.get("latitude") and g.get("longitude"))
    return bool(node.get("latitude") and node.get("longitude"))


def _is_gbp(u: str | None) -> bool:
    u = (u or "").lower()
    return any(s in u for s in ("g.page", "business.google", "google.com/maps", "maps.app.goo.gl"))


def _gbp_link(soup: BeautifulSoup, nodes: list[dict]) -> bool:
    for n in nodes:
        sa = n.get("sameAs")
        urls = [sa] if isinstance(sa, str) else (sa if isinstance(sa, list) else [])
        if any(_is_gbp(u) for u in urls):
            return True
    return soup.find("a", href=lambda h: h and _is_gbp(h)) is not None


def _opt(fid: str, title: str, present: bool, rec: str) -> Finding:
    if present:
        return Finding(fid, P, title, Status.PASS, Severity.INFO, C, evidence=f"{title.lower()} present")
    return Finding(fid, P, title, Status.INFO, Severity.LOW, C, evidence=f"no {title.lower()} found",
                   recommendation=rec)


def analyze(soup: BeautifulSoup, text: str, url: str) -> list[Finding]:
    nodes = _jsonld_nodes(soup)
    local_nodes = [n for n in nodes if _types(n) & LOCAL_TYPES]
    tel = soup.find("a", href=lambda h: h and h.strip().lower().startswith("tel:"))
    maps_embed = soup.find("iframe", src=lambda s: s and ("google.com/maps" in s.lower() or "maps.google" in s.lower()))
    has_postal = any(_postal(n) for n in nodes)

    # Is this a local-business page at all? If not, stay silent (n/a for non-local pages).
    if not (local_nodes or tel or maps_embed or has_postal):
        return []

    out: list[Finding] = []

    # 1. LocalBusiness schema
    if local_nodes:
        types = sorted({t for n in local_nodes for t in (_types(n) & LOCAL_TYPES)})
        out.append(Finding("local.business_schema", P, "LocalBusiness schema", Status.PASS, Severity.INFO, C,
                           value={"types": types}, evidence=f"LocalBusiness schema present ({', '.join(types)})."))
    else:
        out.append(Finding("local.business_schema", P, "LocalBusiness schema", Status.WARN, Severity.MEDIUM, C,
                           evidence="page shows local signals but no LocalBusiness JSON-LD",
                           recommendation="Add LocalBusiness (or a subtype) JSON-LD with name, address, "
                           "telephone, geo and openingHours — the strongest signal for AI 'near me' answers."))

    # 2. NAP — address + phone (name is effectively always present via the title)
    phone = bool(tel) or any(n.get("telephone") for n in nodes)
    address = has_postal
    if phone and address:
        out.append(Finding("local.nap", P, "Name, address & phone", Status.PASS, Severity.INFO, C,
                           evidence="phone and postal address present"))
    else:
        miss = [m for m, ok in (("address", address), ("phone", phone)) if not ok]
        out.append(Finding("local.nap", P, "Name, address & phone", Status.WARN, Severity.MEDIUM, C,
                           value={"missing": miss}, evidence=f"missing: {', '.join(miss)}",
                           recommendation="Show consistent NAP — name, full postal address, phone — on the "
                           "page and in your LocalBusiness schema. AI engines cross-check these."))

    # 3-5. opening hours / geo / GBP link (gentle suggestions)
    hours = any(n.get("openingHours") or n.get("openingHoursSpecification") for n in nodes)
    out.append(_opt("local.hours", "Opening hours", hours,
                    "Add openingHours to your LocalBusiness schema so engines can answer 'are they open now?'"))

    geo = any(_has_geo(n) for n in nodes) or bool(maps_embed)
    out.append(_opt("local.geo", "Geo / map", geo,
                    "Add GeoCoordinates to your schema (or embed a map) so engines can place you on the map."))

    gbp = _gbp_link(soup, nodes)
    out.append(_opt("local.gbp", "Google Business Profile link", gbp,
                    "Link your Google Business Profile via schema sameAs (or a visible link) to tie the page "
                    "to your verified listing."))

    return out
