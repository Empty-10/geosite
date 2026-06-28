"""On-page module — deterministic, VERIFIED. Reads straight from the parsed DOM."""

from __future__ import annotations

import json
import re
from urllib.parse import urljoin, urlparse

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
                            C, evidence="no <title> element in the page <head>",
                            recommendation="Add a unique <title> of ~50–60 characters."))
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
                            Severity.MEDIUM, C, evidence='no <meta name="description"> in the page <head>',
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
                            evidence="no <h1> element on the page",
                            recommendation="Add a single, descriptive H1."))
    elif len(h1s) > 1:
        out.append(Finding("h1.multiple", P, "H1 heading", Status.WARN, Severity.MEDIUM, C,
                            value=len(h1s),
                            evidence="; ".join(f'"{h.get_text(strip=True)[:40]}"' for h in h1s[:3]),
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

    # --- canonical correctness ---
    out.append(_canonical_check(soup, url))

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

    # --- snippet & preview directives (how much search/AI may display) ---
    out.append(_snippet_directives(soup))

    # --- Open Graph + Twitter completeness ---
    out.append(_social_meta(soup))

    # --- heading hierarchy order (no skipped levels) ---
    ho = _heading_order(soup)
    if ho is not None:
        out.append(ho)

    # --- hreflang (only when the site uses it) ---
    hl = _hreflang(soup)
    if hl is not None:
        out.append(hl)

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
    # A *missing* alt is an absent attribute; alt="" is valid (intentionally decorative), so it
    # counts as present — matching Lighthouse/WCAG. We track descriptive (non-empty) separately.
    imgs = soup.find_all("img")
    if imgs:
        has_alt = sum(1 for i in imgs if i.get("alt") is not None)
        descriptive = sum(1 for i in imgs if (i.get("alt") or "").strip())
        pct = round(100 * has_alt / len(imgs))
        missing_srcs = [str(i.get("src") or "") for i in imgs if i.get("alt") is None]
        evidence = ("missing alt on: " + "; ".join(s.rsplit("/", 1)[-1] for s in missing_srcs[:3] if s)
                    if missing_srcs else f"all {len(imgs)} image(s) have an alt attribute")
        out.append(Finding("images.alt", P, "Image alt text",
                           Status.PASS if pct >= 90 else Status.WARN, Severity.LOW, C,
                           value={"with_alt": has_alt, "descriptive": descriptive, "total": len(imgs), "pct": pct},
                           evidence=evidence,
                           recommendation=None if pct >= 90 else
                           f"{len(imgs) - has_alt} image(s) have no alt attribute — add alt text "
                           "(use alt=\"\" only for purely decorative images)."))

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
        # Ratio-based: a few generic anchors on a big site is normal; flag when they're a
        # meaningful share (a fixed "3+ = fail" wrongly failed large sites — benchmark finding).
        ok = bad / total_links <= 0.10
        out.append(Finding(
            "onpage.links", P, "Link anchor text", Status.PASS if ok else Status.WARN,
            Severity.MEDIUM, C, value={"internal": internal, "external": external, "generic": bad, "total": total_links},
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

    # --- crawlable anchors (links crawlers/AI bots can actually follow) ---
    ca = _crawlable_anchors(soup)
    if ca is not None:
        out.append(ca)

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


def _norm_url(u: str) -> str:
    """scheme://host/path with the fragment, query and a trailing slash dropped — for comparing
    a canonical target to the page's own URL."""
    p = urlparse(u)
    path = p.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return f"{p.scheme}://{p.netloc.lower()}{path}"


def _canonical_check(soup: BeautifulSoup, url: str) -> Finding:
    cans = soup.find_all("link", rel="canonical")
    if not cans:
        return Finding("canonical", P, "Canonical tag", Status.WARN, Severity.LOW, C,
                       value={"present": False},
                       recommendation="Add a self-referencing canonical link (absolute URL).")
    href = (cans[0].get("href") or "").strip()
    absolute = href.lower().startswith(("http://", "https://"))
    target = urljoin(url, href) if (url and href) else href
    self_ref = bool(url and href and _norm_url(target) == _norm_url(url))
    value = {"present": True, "count": len(cans), "self_referencing": self_ref,
             "absolute": absolute, "target": href}

    if len(cans) > 1:
        return Finding("canonical", P, "Canonical tag", Status.WARN, Severity.MEDIUM, C, value=value,
                       evidence=f"{len(cans)} canonical tags — conflicting",
                       recommendation="Multiple canonical tags conflict; keep exactly one.")
    if not href:
        return Finding("canonical", P, "Canonical tag", Status.WARN, Severity.LOW, C, value=value,
                       evidence="empty canonical href",
                       recommendation="The canonical href is empty — set it to the page's absolute URL.")
    if url and not self_ref:
        return Finding("canonical", P, "Canonical tag", Status.WARN, Severity.MEDIUM, C, value=value,
                       evidence=f"canonical → {href}",
                       recommendation="This page declares a different canonical URL, so engines will "
                       "index that URL instead of this one — confirm it's intended (a wrong canonical "
                       "de-indexes the page).")
    return Finding("canonical", P, "Canonical tag", Status.PASS if absolute else Status.WARN,
                   Severity.LOW, C, value=value,
                   evidence=f"self-referencing{'' if absolute else ', relative'}: {href}",
                   recommendation=None if absolute else
                   "Use an absolute canonical URL (https://…) rather than a relative one.")


_SNIPPET_RESTRICTIVE = ("nosnippet", "noimageindex", "max-snippet:0", "max-image-preview:none")


def _snippet_directives(soup: BeautifulSoup) -> Finding:
    tokens: list[str] = []
    for m in soup.find_all("meta", attrs={"name": True}):
        if str(m.get("name", "")).lower() in ("robots", "googlebot"):
            tokens += [t.strip().lower() for t in str(m.get("content", "")).split(",") if t.strip()]
    restrictive = [t for t in tokens if t in _SNIPPET_RESTRICTIVE]
    value = {"directives": tokens, "restrictive": restrictive}

    if restrictive:
        return Finding("onpage.snippet_directives", P, "Snippet & preview directives", Status.WARN,
                       Severity.LOW, C, value=value, evidence="restrictive: " + ", ".join(restrictive),
                       recommendation="These robots directives limit how much search and AI engines "
                       "may show of your page (" + ", ".join(restrictive) + "). Remove them unless "
                       "intentional, and add max-image-preview:large to allow rich previews.")
    if "max-image-preview:large" in tokens:
        return Finding("onpage.snippet_directives", P, "Snippet & preview directives", Status.PASS,
                       Severity.INFO, C, value=value, evidence="max-image-preview:large")
    return Finding("onpage.snippet_directives", P, "Snippet & preview directives", Status.INFO,
                   Severity.INFO, C, value=value, evidence="no snippet/preview directives set",
                   recommendation="Add max-image-preview:large (and a generous max-snippet) via meta "
                   "robots to allow larger image/text previews in AI Overviews and search results.")


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


def _social_meta(soup: BeautifulSoup) -> Finding:
    """Open Graph + Twitter Card completeness (was: og:title presence only)."""
    def og(prop: str) -> bool:
        return soup.find("meta", attrs={"property": prop}) is not None

    tags = {
        "og:title": og("og:title"),
        "og:description": og("og:description"),
        "og:image": og("og:image"),
        "og:url": og("og:url"),
        "og:type": og("og:type"),
        "twitter:card": soup.find("meta", attrs={"name": "twitter:card"}) is not None,
    }
    present = [k for k, v in tags.items() if v]
    missing = [k for k, v in tags.items() if not v]
    core = tags["og:title"] and tags["og:description"] and tags["og:image"]
    core_missing = [k for k in ("og:title", "og:description", "og:image") if k in missing]
    return Finding(
        "opengraph", P, "Open Graph & Twitter tags", Status.PASS if core else Status.WARN,
        Severity.LOW, C, value={"present": present, "missing": missing},
        evidence=("present: " + ", ".join(present)) if present else "no social tags",
        recommendation=None if core else
        "Add the core social tags (" + ", ".join(core_missing) + ", and ideally og:url + "
        "twitter:card) so links and AI snippets show a rich title, description and image.",
    )


def _heading_order(soup: BeautifulSoup) -> Finding | None:
    """Flag skipped heading levels (e.g. H1 → H3). None if the page has no headings."""
    headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
    if not headings:
        return None
    skips, prev = [], 0
    for h in headings:
        lvl = int(h.name[1])
        if prev and lvl > prev + 1:
            skips.append(f"h{prev}→h{lvl}")
        prev = lvl
    if not skips:
        return Finding("onpage.heading_order", P, "Heading order", Status.PASS, Severity.INFO, C,
                       value={"headings": len(headings), "skips": 0})
    return Finding(
        "onpage.heading_order", P, "Heading order", Status.WARN, Severity.LOW, C,
        value={"headings": len(headings), "skips": len(skips)},
        evidence="skipped: " + ", ".join(skips[:4]),
        recommendation="Headings skip levels (" + ", ".join(skips[:4]) + "). Keep a clean "
        "H1→H2→H3 outline (don't jump levels) — it helps both extraction and accessibility.",
    )


_HREFLANG_RE = re.compile(r"^[a-z]{2,3}(-[a-z]{2,4})?$|^x-default$", re.I)


def _hreflang(soup: BeautifulSoup) -> Finding | None:
    """Validate hreflang alternates — only when the site actually uses them (no penalty otherwise)."""
    langs = [str(link.get("hreflang")).strip()
             for link in soup.find_all("link", rel="alternate") if link.get("hreflang")]
    if not langs:
        return None
    invalid = [x for x in langs if not _HREFLANG_RE.match(x)]
    has_xdefault = any(x.lower() == "x-default" for x in langs)
    issues = []
    if invalid:
        issues.append("invalid codes: " + ", ".join(invalid[:3]))
    if not has_xdefault:
        issues.append("no x-default")
    if not issues:
        return Finding("onpage.hreflang", P, "hreflang", Status.PASS, Severity.INFO, C,
                       value={"count": len(langs), "x_default": True})
    return Finding(
        "onpage.hreflang", P, "hreflang", Status.WARN, Severity.LOW, C,
        value={"count": len(langs), "invalid": invalid, "x_default": has_xdefault},
        evidence="; ".join(issues),
        recommendation="Fix hreflang: " + "; ".join(issues) + ". Use valid lang(-REGION) codes "
        "and include an x-default for international targeting.",
    )


def _crawlable_anchors(soup: BeautifulSoup) -> Finding | None:
    """Links that navigate via JavaScript (javascript: / onclick, no real href) — uncrawlable."""
    anchors = soup.find_all("a")
    if not anchors:
        return None
    bad = []
    for a in anchors:
        href = (a.get("href") or "").strip()
        if href.lower().startswith("javascript:"):
            bad.append(href[:50])
        elif a.get("onclick") and href in ("", "#"):
            bad.append("(onclick, no href)")
    if not bad:
        return Finding("onpage.crawlable_anchors", P, "Crawlable links", Status.PASS, Severity.INFO,
                       C, value={"uncrawlable": 0, "total": len(anchors)})
    return Finding(
        "onpage.crawlable_anchors", P, "Crawlable links", Status.WARN, Severity.MEDIUM, C,
        value={"uncrawlable": len(bad), "total": len(anchors)}, evidence="; ".join(bad[:3]),
        recommendation=f"{len(bad)} link(s) navigate via JavaScript (javascript: or onclick) with no "
        "real href — search and AI crawlers can't follow them. Use <a href=\"…\"> with a real URL.",
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
