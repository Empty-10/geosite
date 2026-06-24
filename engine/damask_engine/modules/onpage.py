"""On-page module — deterministic, VERIFIED. Reads straight from the parsed DOM."""

from __future__ import annotations

import json
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from ..models import Confidence, Finding, Pillar, Severity, Status

P = Pillar.ONPAGE
C = Confidence.VERIFIED

# Anchor text that tells engines nothing about the destination.
GENERIC_ANCHORS = {
    "click here", "here", "read more", "more", "learn more", "more info", "details",
    "this", "this page", "link", "read", "continue", "see more", "website", "go",
}


def analyze(soup: BeautifulSoup, text: str, url: str = "") -> list[Finding]:
    out: list[Finding] = []

    # --- title ---
    title = (soup.title.string or "").strip() if soup.title and soup.title.string else ""
    if not title:
        out.append(Finding("title.missing", P, "Page title", Status.FAIL, Severity.CRITICAL,
                            C, recommendation="Add a unique <title> of ~50–60 characters."))
    else:
        n = len(title)
        ok = 15 <= n <= 60
        out.append(Finding(
            "title.length", P, "Page title", Status.PASS if ok else Status.WARN,
            Severity.MEDIUM, C, value=n, evidence=title[:120],
            recommendation=None if ok else "Aim for ~50–60 characters.",
        ))

    # --- meta description ---
    md = soup.find("meta", attrs={"name": "description"})
    content = (md.get("content") or "").strip() if md else ""
    if not content:
        out.append(Finding("meta.description.missing", P, "Meta description", Status.FAIL,
                            Severity.MEDIUM, C,
                            recommendation="Add a meta description of ~120–160 characters."))
    else:
        n = len(content)
        ok = 80 <= n <= 160
        out.append(Finding("meta.description.length", P, "Meta description",
                            Status.PASS if ok else Status.WARN, Severity.LOW, C, value=n,
                            evidence=content[:160],
                            recommendation=None if ok else "Aim for ~120–160 characters."))

    # --- H1 ---
    h1s = soup.find_all("h1")
    if len(h1s) == 0:
        out.append(Finding("h1.missing", P, "H1 heading", Status.FAIL, Severity.HIGH, C,
                            recommendation="Add a single, descriptive H1."))
    elif len(h1s) > 1:
        out.append(Finding("h1.multiple", P, "H1 heading", Status.WARN, Severity.MEDIUM, C,
                            value=len(h1s),
                            recommendation="Use exactly one H1 per page."))
    else:
        out.append(Finding("h1.ok", P, "H1 heading", Status.PASS, Severity.INFO, C,
                            value=1, evidence=h1s[0].get_text(strip=True)[:120]))

    # --- heading hierarchy present ---
    headings = soup.find_all(["h2", "h3", "h4", "h5", "h6"])
    out.append(Finding("headings.structure", P, "Subheadings",
                       Status.PASS if headings else Status.WARN, Severity.LOW, C,
                       value=len(headings),
                       recommendation=None if headings else
                       "Break content up with H2/H3 subheadings (helps extraction)."))

    # --- canonical ---
    canonical = soup.find("link", rel="canonical")
    out.append(Finding("canonical", P, "Canonical tag",
                       Status.PASS if canonical else Status.WARN, Severity.LOW, C,
                       value=bool(canonical),
                       evidence=canonical.get("href") if canonical else None,
                       recommendation=None if canonical else "Add a canonical link."))

    # --- meta robots noindex ---
    robots = soup.find("meta", attrs={"name": "robots"})
    rc = (robots.get("content") or "").lower() if robots else ""
    if "noindex" in rc:
        out.append(Finding("robots.noindex", P, "Indexability", Status.FAIL, Severity.HIGH, C,
                            evidence=rc, value="noindex",
                            recommendation="Page is set to noindex — remove it if it should rank."))
    else:
        out.append(Finding("robots.indexable", P, "Indexability", Status.PASS, Severity.INFO,
                            C, value="indexable"))

    # --- Open Graph ---
    og = soup.find("meta", attrs={"property": "og:title"})
    out.append(Finding("opengraph", P, "Open Graph tags",
                       Status.PASS if og else Status.WARN, Severity.LOW, C, value=bool(og),
                       recommendation=None if og else "Add Open Graph tags for richer sharing."))

    # --- JSON-LD structured data ---
    types = _jsonld_types(soup)
    if types:
        out.append(Finding("schema.jsonld", P, "Structured data (JSON-LD)", Status.PASS,
                           Severity.INFO, C, value=sorted(types),
                           evidence=", ".join(sorted(types))[:160]))
    else:
        out.append(Finding("schema.missing", P, "Structured data (JSON-LD)", Status.WARN,
                           Severity.MEDIUM, C,
                           recommendation="Add schema.org JSON-LD (Organization, Article, "
                           "FAQ, Product…) — helps both SEO and AI extraction."))

    # --- structured-data validity (required properties for known rich-result types) ---
    sv = _schema_validation(soup)
    if sv is not None:
        out.append(sv)

    # --- image alt coverage ---
    imgs = soup.find_all("img")
    if imgs:
        with_alt = sum(1 for i in imgs if (i.get("alt") or "").strip())
        pct = round(100 * with_alt / len(imgs))
        out.append(Finding("images.alt", P, "Image alt text",
                           Status.PASS if pct >= 90 else Status.WARN, Severity.LOW, C,
                           value={"with_alt": with_alt, "total": len(imgs), "pct": pct},
                           recommendation=None if pct >= 90 else
                           f"{len(imgs) - with_alt} image(s) missing alt text."))

    # --- image dimensions & lazy-load (extends alt; CLS + delivery) ---
    if imgs:
        with_dims = sum(1 for i in imgs if i.get("width") and i.get("height"))
        with_lazy = sum(1 for i in imgs if (i.get("loading") or "").lower() == "lazy")
        dpct = round(100 * with_dims / len(imgs))
        out.append(Finding(
            "onpage.images.dims", P, "Image dimensions & lazy-load",
            Status.PASS if dpct >= 80 else Status.WARN, Severity.LOW, C,
            value={"with_dims": with_dims, "with_lazy": with_lazy, "total": len(imgs), "pct_dims": dpct},
            recommendation=None if dpct >= 80 else
            f"{len(imgs) - with_dims} image(s) lack explicit width/height (causes layout shift) — "
            "add them, and loading=\"lazy\" for below-the-fold images.",
        ))

    # --- link analysis: internal/external + anchor text quality ---
    host = urlparse(url).netloc.lower().split(":")[0] if url else ""
    internal, external, generic, ext_domains = _link_stats(soup, host)
    total_links = internal + external
    if total_links:
        bad = len(generic)
        ok = bad < 3 and bad / total_links <= 0.25
        out.append(Finding(
            "onpage.links", P, "Link anchor text", Status.PASS if ok else Status.WARN,
            Severity.MEDIUM, C, value={"internal": internal, "external": external, "generic": bad},
            evidence="; ".join(generic[:3]) or None,
            recommendation=None if ok else
            "Replace generic anchor text ('click here', 'read more', bare URLs) with descriptive "
            "phrases — anchors tell engines what the linked page is about.",
        ))
        out.append(Finding(
            "onpage.outbound", P, "Outbound source links",
            Status.PASS if external >= 1 else Status.INFO, Severity.LOW, C,
            value={"external": external},
            evidence=", ".join(sorted(set(ext_domains))[:5]) or None,
            recommendation=None if external >= 1 else
            "Link out to authoritative sources where relevant — citing sources is a trust signal.",
        ))

    # --- link attributes & semantic hints (rel / target hygiene on external links) ---
    la = _link_attrs(soup, host)
    if la is not None:
        out.append(la)

    # --- in-page jump/anchor links (table-of-contents, deep-linkable sections) ---
    jumps = [a["href"][1:] for a in soup.find_all("a", href=True)
             if a["href"].startswith("#") and len(a["href"]) > 1]
    if jumps:
        resolved = sum(1 for t in jumps if soup.find(id=t))
        out.append(Finding(
            "onpage.jump_links", P, "In-page jump links",
            Status.PASS if resolved >= 1 else Status.INFO, Severity.LOW, C,
            value={"jump_links": len(jumps), "resolved": resolved},
            evidence=f"{resolved} of {len(jumps)} anchor link(s) resolve to an id",
            recommendation=None if resolved >= 1 else
            "Anchor links don't resolve to an id on the page — fix the targets so sections "
            "are deep-linkable.",
        ))

    # --- accessibility basics (coverage-map row 16 → On-page pillar) ---
    html_tag = soup.find("html")
    has_lang = bool(html_tag and html_tag.get("lang"))
    out.append(Finding(
        "onpage.lang", P, "Page language", Status.PASS if has_lang else Status.WARN,
        Severity.LOW, C, value=html_tag.get("lang") if has_lang else None,
        recommendation=None if has_lang else
        "Set <html lang=\"…\"> so search engines and assistive tech know the page language.",
    ))

    controls = [c for c in soup.find_all(["input", "select", "textarea"])
                if (c.get("type") or "text").lower() not in
                ("hidden", "submit", "button", "reset", "image")]
    if controls:
        unlabeled = [c for c in controls if not _is_labeled(soup, c)]
        out.append(Finding(
            "onpage.form_labels", P, "Form control labels",
            Status.PASS if not unlabeled else Status.WARN, Severity.LOW, C,
            value={"controls": len(controls), "unlabeled": len(unlabeled)},
            recommendation=None if not unlabeled else
            f"{len(unlabeled)} form control(s) lack a label — add <label for>, aria-label, or "
            "wrap the control in a <label>.",
        ))

    # --- URL structure quality ---
    if url:
        out.append(_url_quality(url))

    return out


def _is_labeled(soup: BeautifulSoup, control) -> bool:
    if control.get("aria-label") or control.get("aria-labelledby") or control.get("title"):
        return True
    cid = control.get("id")
    if cid and soup.find("label", attrs={"for": cid}):
        return True
    return control.find_parent("label") is not None


def _link_stats(soup: BeautifulSoup, host: str) -> tuple[int, int, list[str], list[str]]:
    """Count internal/external links, collect generic-anchor texts and external domains."""
    internal = external = 0
    generic: list[str] = []
    ext_domains: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        p = urlparse(href)
        if p.scheme in ("http", "https") and p.netloc:
            if host and p.netloc.lower().split(":")[0] == host:
                internal += 1
            else:
                external += 1
                ext_domains.append(p.netloc)
        else:
            internal += 1  # relative link
        text = a.get_text(" ", strip=True)
        norm = text.lower().strip(" .›»→-")
        bare_url = norm.startswith(("http://", "https://", "www."))
        empty = not text and not (a.get("aria-label") or a.get("title"))
        if norm in GENERIC_ANCHORS or bare_url or empty:
            generic.append(text or "(no text)")
    return internal, external, generic, ext_domains


def _url_quality(url: str) -> Finding:
    p = urlparse(url)
    path = p.path or "/"
    issues = []
    if any(c.isupper() for c in path):
        issues.append("uppercase letters")
    if "_" in path:
        issues.append("underscores (use hyphens)")
    segments = [s for s in path.split("/") if s]
    if len(segments) > 4:
        issues.append(f"deep path ({len(segments)} levels)")
    if p.query:
        issues.append("query string")
    if len(url) > 100:
        issues.append("very long")
    ok = len(issues) <= 1
    return Finding(
        "onpage.url", P, "URL structure", Status.PASS if ok else Status.WARN, Severity.LOW, C,
        value={"issues": issues}, evidence=url if not ok else None,
        recommendation=None if ok else
        "Prefer short, lowercase, hyphenated URLs with shallow depth and no query junk — "
        "issues: " + ", ".join(issues) + ".",
    )


# Minimal required properties Google needs for common rich-result types (lower-cased keys).
SCHEMA_REQUIRED: dict[str, list[str]] = {
    "article": ["headline"],
    "newsarticle": ["headline"],
    "blogposting": ["headline"],
    "product": ["name"],
    "faqpage": ["mainentity"],
    "qapage": ["mainentity"],
    "organization": ["name"],
    "localbusiness": ["name", "address"],
    "breadcrumblist": ["itemlistelement"],
    "event": ["name", "startdate", "location"],
    "howto": ["name", "step"],
    "recipe": ["name", "image"],
    "person": ["name"],
    "videoobject": ["name", "thumbnailurl", "uploaddate"],
}


def _link_attrs(soup: BeautifulSoup, host: str) -> Finding | None:
    """Row 13 — rel/target hygiene on external links. Returns None when there are no external
    links to judge. Flags target=_blank links missing rel=noopener (a real security/SEO issue)."""
    external = with_rel = 0
    blank_unsafe: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        p = urlparse(href)
        is_external = bool(p.scheme in ("http", "https") and p.netloc
                           and (not host or p.netloc.lower().split(":")[0] != host))
        if not is_external:
            continue
        external += 1
        rel_val = a.get("rel")
        rel = " ".join(rel_val).lower() if isinstance(rel_val, list) else str(rel_val or "").lower()
        if rel.strip():
            with_rel += 1
        if (a.get("target") or "").lower() == "_blank" and "noopener" not in rel and "noreferrer" not in rel:
            blank_unsafe.append(href)
    if external == 0:
        return None
    ok = not blank_unsafe
    return Finding(
        "onpage.link_attrs", P, "Link attributes", Status.PASS if ok else Status.WARN,
        Severity.LOW, C,
        value={"external": external, "with_rel": with_rel, "blank_without_noopener": len(blank_unsafe)},
        evidence=("; ".join(blank_unsafe[:3]) if blank_unsafe
                  else f"{with_rel}/{external} external link(s) carry rel hints"),
        recommendation=None if ok else
        f"{len(blank_unsafe)} external link(s) open in a new tab (target=\"_blank\") without "
        "rel=\"noopener\" — add it for security, and mark paid/UGC links rel=\"sponsored\"/\"ugc\".",
    )


def _jsonld_nodes(soup: BeautifulSoup) -> list[dict]:
    """All JSON-LD object nodes on the page, flattening top-level lists and @graph containers."""
    out: list[dict] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text() or ""
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        stack = list(data) if isinstance(data, list) else [data]
        while stack:
            node = stack.pop()
            if isinstance(node, list):
                stack.extend(node)
            elif isinstance(node, dict):
                graph = node.get("@graph")
                if isinstance(graph, list):
                    stack.extend(graph)
                out.append(node)
    return out


def _node_type_set(node: dict) -> set[str]:
    t = node.get("@type")
    if isinstance(t, list):
        return {str(x).lower() for x in t}
    return {str(t).lower()} if t else set()


def _schema_validation(soup: BeautifulSoup) -> Finding | None:
    """Row 20 — check known schema types carry the properties Google requires for rich results.
    Returns None when there's no JSON-LD, or none of a type we validate (absence is covered by
    schema.missing; unknown types aren't penalised)."""
    nodes = _jsonld_nodes(soup)
    if not nodes:
        return None
    problems: list[str] = []
    validated = 0
    for node in nodes:
        keys = {k.lower() for k in node.keys()}
        for t in _node_type_set(node):
            req = SCHEMA_REQUIRED.get(t)
            if req:
                validated += 1
                missing = [r for r in req if r not in keys]
                if missing:
                    problems.append(f"{t}: missing {', '.join(missing)}")
                break  # one validated type per node
    if validated == 0:
        return None
    ok = not problems
    return Finding(
        "schema.validation", P, "Schema validity", Status.PASS if ok else Status.WARN,
        Severity.MEDIUM, C, value={"validated": validated, "problems": len(problems)},
        evidence="; ".join(problems[:4]) if problems
        else f"{validated} schema object(s) have their required properties",
        recommendation=None if ok else
        "Structured data is missing properties Google requires for rich results — "
        + "; ".join(problems[:4]) + ". Add them so the markup is eligible.",
    )


def _jsonld_types(soup: BeautifulSoup) -> set[str]:
    types: set[str] = set()
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text() or ""
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        for node in data if isinstance(data, list) else [data]:
            if isinstance(node, dict):
                t = node.get("@type")
                if isinstance(t, list):
                    types.update(str(x) for x in t)
                elif t:
                    types.add(str(t))
    return types
