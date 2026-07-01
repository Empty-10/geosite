"""Expert Schema Review - deterministic, VERIFIED.

A deeper pass over the page's JSON-LD than the presence/validation checks in onpage.py. It reads the
flattened schema graph and the page canonical and emits normal Astova findings about entity
duplication, identity conflicts, graph wiring, sameAs quality, Article relationships, URL hygiene and
over-generic types. Pure: takes the parsed DOM + final URL, returns list[Finding]; no network.

Wording avoids overclaiming ranking impact - schema issues are framed as entity-clarity / extraction /
rich-result-eligibility problems, which is what they actually are.
"""

from __future__ import annotations

from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .. import reviews
from ..jsonld import node_types, parse_nodes, type_labels
from ..models import Confidence, Finding, Pillar, Severity, Status

P = Pillar.ONPAGE  # schema findings live on the on-page pillar (matches schema.missing/jsonld)
C = Confidence.VERIFIED

# Type families (lower-cased).
_ORG = {"organization"}
_LOCALBUSINESS = {"localbusiness", "restaurant", "store", "lodgingbusiness", "medicalbusiness",
                  "professionalservice", "financialservice", "homeandconstructionbusiness",
                  "automotivebusiness", "foodestablishment", "healthandbeautybusiness"}
_WEBSITE = {"website"}
_WEBPAGE = {"webpage", "collectionpage", "itempage", "aboutpage", "contactpage", "profilepage",
            "searchresultspage", "checkoutpage", "faqpage", "qapage"}
_ARTICLE = {"article", "blogposting", "newsarticle", "techarticle", "report", "scholarlyarticle",
            "socialmediaposting"}
_PRIMARY = _ORG | _LOCALBUSINESS | _WEBSITE | _WEBPAGE | _ARTICLE | {"breadcrumblist", "product",
                                                                     "person", "event", "recipe"}


def _is(node: dict, fam: set[str]) -> bool:
    return bool(node_types(node) & fam)


def _norm_url(u: str | None) -> str:
    p = urlparse((u or "").strip())
    path = (p.path or "/").rstrip("/") or "/"
    return f"{p.scheme}://{p.netloc.lower()}{path}"


def _is_http_url(v) -> bool:
    if not isinstance(v, str):
        return False
    p = urlparse(v.strip())
    return p.scheme in ("http", "https") and bool(p.netloc)


def _str_val(v) -> str | None:
    """Pull a comparable string out of a schema value that may be str or {url/@id/name: ...}."""
    if isinstance(v, str):
        return v.strip() or None
    if isinstance(v, dict):
        for k in ("url", "@id", "name"):
            if isinstance(v.get(k), str) and v[k].strip():
                return v[k].strip()
    return None


def _as_list(v) -> list:
    return v if isinstance(v, list) else ([] if v is None else [v])


def _canonical(soup: BeautifulSoup) -> str | None:
    link = soup.find("link", rel="canonical")
    href = link.get("href") if link else None
    return href.strip() if isinstance(href, str) and href.strip() else None


def _referenced_ids(nodes: list[dict]) -> set[str]:
    """Every @id referenced by some node (via a nested {"@id": ...} or a bare id-looking string)."""
    refs: set[str] = set()

    def walk(v, *, top: bool):
        if isinstance(v, dict):
            if not top and isinstance(v.get("@id"), str):
                refs.add(v["@id"])
            for k, val in v.items():
                if k == "@id" and top:
                    continue
                walk(val, top=False)
        elif isinstance(v, list):
            for x in v:
                walk(x, top=False)

    for n in nodes:
        walk(n, top=True)
    return refs


def analyze(soup: BeautifulSoup, final_url: str) -> list[Finding]:
    nodes = parse_nodes(soup)
    if not nodes:
        return []  # absence is covered by onpage.schema.missing
    out: list[Finding] = []
    graph = len(nodes) >= 2
    page_canonical = _canonical(soup)
    page_https = urlparse(final_url).scheme == "https"

    orgs = [n for n in nodes if _is(n, _ORG)]
    locals_ = [n for n in nodes if _is(n, _LOCALBUSINESS)]
    websites = [n for n in nodes if _is(n, _WEBSITE)]
    webpages = [n for n in nodes if _is(n, _WEBPAGE)]
    articles = [n for n in nodes if _is(n, _ARTICLE)]

    # --- duplicate top-level entities ---
    if len(orgs) > 1:
        out.append(_f("schema.duplicate_organization", "Multiple Organization entities", Status.WARN,
                      Severity.MEDIUM, f"{len(orgs)} Organization nodes in the schema",
                      "Multiple Organization entities confuse which one represents the site. Consolidate "
                      "into a single Organization (use @id to reference it from other nodes)."))
    if len(locals_) > 1:
        out.append(_f("schema.duplicate_localbusiness", "Multiple LocalBusiness entities", Status.WARN,
                      Severity.MEDIUM, f"{len(locals_)} LocalBusiness nodes in the schema",
                      "Multiple LocalBusiness entities split the local identity. Keep one per physical "
                      "location and reference it via @id."))
    if len(websites) > 1:
        out.append(_f("schema.duplicate_website", "Multiple WebSite entities", Status.WARN,
                      Severity.MEDIUM, f"{len(websites)} WebSite nodes in the schema",
                      "There should be one WebSite entity for the site. Remove the duplicates."))

    # --- conflicting Organization identity ---
    out += _conflict(orgs, "name", "schema.conflicting_organization_name", "Organization name",
                     Severity.HIGH)
    out += _conflict(orgs, "url", "schema.conflicting_organization_url", "Organization URL",
                     Severity.HIGH)
    out += _conflict(orgs, "logo", "schema.conflicting_organization_logo", "Organization logo",
                     Severity.MEDIUM, status=Status.WARN)

    # --- @id wiring ---
    if graph:
        missing_id = [lbl for n in nodes if _is(n, _PRIMARY) and "@id" not in n
                      for lbl in (type_labels(n)[:1] or ["node"])]
        if missing_id:
            out.append(_f("schema.missing_id", "Schema entities missing @id", Status.WARN, Severity.LOW,
                          "main entities without @id: " + ", ".join(sorted(set(missing_id))[:6]),
                          "In a multi-entity @graph, give each main entity a stable @id so other nodes "
                          "can reference it unambiguously."))

    id_types: dict[str, set[str]] = {}
    for n in nodes:
        nid = n.get("@id")
        if isinstance(nid, str):
            id_types.setdefault(nid, set()).update(node_types(n))
    conflicting = [i for i, ts in id_types.items() if len(ts) > 1]
    if conflicting:
        out.append(_f("schema.duplicate_id_conflict", "Same @id, different entity types", Status.FAIL,
                      Severity.HIGH, "conflicting @id: " + ", ".join(conflicting[:3]),
                      "An @id must identify one entity. The same @id is used for different @types - give "
                      "each distinct entity its own @id."))

    if graph:
        refs = _referenced_ids(nodes)
        orphans = [n.get("@id") for n in nodes
                   if isinstance(n.get("@id"), str) and n["@id"] not in refs and not _is(n, _PRIMARY)]
        if orphans:
            out.append(_f("schema.orphan_node", "Orphan schema node", Status.WARN, Severity.INFO,
                          "unreferenced node @id: " + ", ".join(str(o) for o in orphans[:3]),
                          "A supporting node carries an @id that nothing else references. Reference it "
                          "from its parent entity, or inline it, so the graph is connected."))

    # --- sameAs quality ---
    invalid_sa, empty_sa = [], False
    for n in nodes:
        if "sameAs" not in n:
            continue
        vals = _as_list(n.get("sameAs"))
        if not vals or all(not _str_val(v) for v in vals):
            empty_sa = True
        for v in vals:
            s = _str_val(v)
            if s and not _is_http_url(s):
                invalid_sa.append(s)
    if invalid_sa:
        out.append(_f("schema.invalid_sameas", "Invalid sameAs values", Status.FAIL, Severity.MEDIUM,
                      "not valid URLs: " + ", ".join(invalid_sa[:3]),
                      "sameAs must be absolute http(s) profile URLs. Fix or remove the invalid entries."))
    if empty_sa:
        out.append(_f("schema.weak_sameas", "Empty sameAs", Status.WARN, Severity.LOW,
                      "a sameAs property is present but empty",
                      "Either populate sameAs with the entity's real authoritative profile URLs "
                      "(Wikipedia, Crunchbase, official socials) or remove the empty property."))

    # --- Article relationships ---
    if any("publisher" not in n for n in articles):
        out.append(_f("schema.article_missing_publisher", "Article without publisher", Status.WARN,
                      Severity.MEDIUM, "an Article/BlogPosting node has no publisher",
                      "Add a publisher (the Organization) to Article schema so engines can attribute the "
                      "content - and it's required for Article rich-result eligibility."))
    if any("author" not in n for n in articles):
        out.append(_f("schema.article_missing_author", "Article without author", Status.WARN,
                      Severity.MEDIUM, "an Article/BlogPosting node has no author",
                      "Add an author (Person or Organization) to Article schema so the content is "
                      "attributed to a known entity."))

    # --- WebSite SearchAction (only when the page actually has a search box) ---
    has_search = bool(soup.find("input", attrs={"type": "search"}) or soup.find(attrs={"role": "search"}))
    if websites and has_search:
        if not any(_has_searchaction(w) for w in websites):
            out.append(_f("schema.website_missing_searchaction", "WebSite without SearchAction",
                          Status.WARN, Severity.LOW, "WebSite schema has no SearchAction potentialAction",
                          "The site has a search box but the WebSite schema declares no SearchAction. Add "
                          "a potentialAction SearchAction so engines can expose sitelinks search."))

    # --- BreadcrumbList connection ---
    if any(_is(n, {"breadcrumblist"}) for n in nodes):
        if not any("breadcrumb" in n for n in nodes):
            out.append(_f("schema.breadcrumb_disconnected", "BreadcrumbList not connected", Status.WARN,
                          Severity.LOW, "BreadcrumbList present but no node references it via breadcrumb",
                          "Reference the BreadcrumbList from the WebPage's breadcrumb property (by @id) so "
                          "the breadcrumb is attached to the page."))

    # --- canonical mismatch ---
    if page_canonical:
        ent_url = next((n.get("url") for n in (webpages or articles) if isinstance(n.get("url"), str)), None)
        if ent_url and _norm_url(ent_url) != _norm_url(page_canonical):
            out.append(_f("schema.canonical_mismatch", "Schema URL differs from canonical", Status.FAIL,
                          Severity.MEDIUM, f"schema url {ent_url} vs canonical {page_canonical}",
                          "The main entity's url disagrees with the page canonical. Point them at the same "
                          "URL so engines resolve one canonical entity."))

    # --- insecure http URLs on an https page ---
    if page_https:
        insecure = _collect_http_urls(nodes)
        if insecure:
            out.append(_f("schema.insecure_url", "Insecure (http) URLs in schema", Status.FAIL,
                          Severity.MEDIUM, "http:// in schema on an https page: " + insecure[0],
                          "Schema uses http:// URLs on an https page. Use the https equivalents so the "
                          "markup matches the secure site."))

    # --- ImageObject missing dimensions ---
    if _imageobject_missing_dims(nodes):
        out.append(_f("schema.image_missing_dimensions", "Schema image without dimensions", Status.WARN,
                      Severity.INFO, "an ImageObject in schema is missing width or height",
                      "Add width and height to schema ImageObjects (logo/image) so engines can use the "
                      "image reliably."))

    # --- over-generic type (only flag the most generic: Thing) ---
    generic = [n for n in nodes if node_types(n) == {"thing"}]
    if generic:
        out.append(_f("schema.generic_type", "Over-generic schema type", Status.WARN, Severity.LOW,
                      f"{len(generic)} node(s) typed only as Thing",
                      "A node is typed only as the generic Thing. Use the most specific schema.org type "
                      "that fits the content (e.g. Article, Product, Organization)."))

    return out


def _f(fid: str, title: str, status: Status, severity: Severity, evidence: str, rec: str) -> Finding:
    return Finding(fid, P, title, status, severity, C, evidence=evidence, recommendation=rec)


def _conflict(orgs: list[dict], prop: str, fid: str, label: str, severity: Severity,
              status: Status = Status.FAIL) -> list[Finding]:
    values = {v for n in orgs if (v := _str_val(n.get(prop)))}
    if len(values) > 1:
        return [_f(fid, f"Conflicting {label}", status, severity,
                   f"{len(values)} different {label} values: " + ", ".join(sorted(values)[:3]),
                   f"Organization entities declare different {label} values. They must agree so engines "
                   "resolve one identity for the site.")]
    return []


def _has_searchaction(website: dict) -> bool:
    for action in _as_list(website.get("potentialAction")):
        if isinstance(action, dict) and "searchaction" in node_types(action):
            return True
    return False


def _collect_http_urls(nodes: list[dict]) -> list[str]:
    found: list[str] = []

    def walk(v):
        if isinstance(v, str):
            if v.strip().lower().startswith("http://"):
                found.append(v.strip())
        elif isinstance(v, dict):
            for val in v.values():
                walk(val)
        elif isinstance(v, list):
            for x in v:
                walk(x)

    for n in nodes:
        walk(n)
    return found


def _imageobject_missing_dims(nodes: list[dict]) -> bool:
    for n in nodes:
        for key in ("logo", "image"):
            for v in _as_list(n.get(key)):
                if isinstance(v, dict) and ("imageobject" in node_types(v) or "url" in v):
                    if "width" not in v or "height" not in v:
                        return True
    return False


# --------------------------------------------------------------------------- review contract

NAME = "Schema Review"
KEY = "schema"
SECTIONS: list[tuple[str, list[str]]] = [
    ("Presence & validity", ["schema.jsonld", "schema.missing", "schema.validation"]),
    ("Entity duplication & conflicts", ["schema.duplicate_organization", "schema.duplicate_localbusiness",
                                        "schema.duplicate_website", "schema.conflicting_organization_name",
                                        "schema.conflicting_organization_url",
                                        "schema.conflicting_organization_logo",
                                        "schema.duplicate_id_conflict"]),
    ("Graph wiring", ["schema.missing_id", "schema.orphan_node", "schema.breadcrumb_disconnected"]),
    ("sameAs quality", ["schema.invalid_sameas", "schema.weak_sameas"]),
    ("Article relationships", ["schema.article_missing_publisher", "schema.article_missing_author"]),
    ("URL & type hygiene", ["schema.canonical_mismatch", "schema.insecure_url",
                            "schema.image_missing_dimensions", "schema.generic_type"]),
]
_ALL_IDS = [fid for _, ids in SECTIONS for fid in ids]


def summarize(report: dict) -> dict:
    """Build the standard Expert Review contract for schema (so it joins the Review Comparison)."""
    findings = report.get("findings", [])
    by_id = {f["id"]: f for f in findings}
    statuses = [by_id[f]["status"] for f in _ALL_IDS if f in by_id]
    verdict = "weak" if "fail" in statuses else ("partial" if "warn" in statuses else "strong")
    extra = ["no structured data on the page"] if by_id.get("schema.missing", {}).get("status") == "warn" else []
    fix_ids = {fx.get("finding_id") for fx in report.get("fixes", []) if fx.get("finding_id")}
    sections = [{"name": name, "status": reviews.section_status(ids, by_id),
                 "findings": [fid for fid in ids if fid in by_id]} for name, ids in SECTIONS]
    return reviews.build_review(
        key=KEY, name=NAME, verdict=verdict,
        confidence=reviews.review_confidence(report.get("meta", {}), findings, extra_reasons=extra),
        summary=[], likely_ai_quote=None, sections=sections,
        counts=reviews.classify_findings(_ALL_IDS, by_id, fix_ids),
        related_findings=[fid for fid in _ALL_IDS if fid in by_id],
    )
