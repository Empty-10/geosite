"""Fix generation — "fixes, not findings."

Turns findings into ready-to-paste remediation artifacts. Deterministic and reproducible
(no LLM): each generator reads the parsed page and emits a concrete snippet. Pure — takes
the soup + the scored Report and returns a list of Fix, gated on which findings fired.

This is the wedge from CLAUDE.md: competitors stop at "what's wrong"; we hand over the fix.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .models import Report


@dataclass
class Fix:
    finding_id: str  # the finding this remediates
    title: str       # short imperative, e.g. "Add Organization schema"
    kind: str        # "json-ld" | "llms-txt" | "meta" | "robots" | "text"
    language: str    # code-fence hint: "json" | "html" | "text" | "markdown"
    content: str     # the ready-to-use artifact
    note: str | None = None  # where/how to apply it

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def generate_fixes(soup: BeautifulSoup, report: Report, url: str) -> list[Fix]:
    """Build remediation artifacts for the findings that fired. Order = report order."""
    ids = {f.id for f in report.findings if f.status in ("fail", "warn")}
    fixes: list[Fix] = []

    if "title.missing" in ids:
        fixes.append(_fix_title(soup, url))
    if "meta.description.missing" in ids:
        meta = _fix_meta(soup)
        if meta is not None:
            fixes.append(meta)
    if "canonical" in ids:
        fixes.append(_fix_canonical(url))
    if "tech.viewport" in ids:
        fixes.append(_fix_viewport())
    if "schema.missing" in ids:
        fixes.append(_fix_schema(soup, url))
    faq = _fix_faq(soup)
    if faq is not None:
        fixes.append(faq)
    if "tech.robots.missing" in ids:
        fixes.append(_fix_robots(url, "tech.robots.missing"))
    elif "tech.robots.ai" in ids:
        fixes.append(_fix_robots(url, "tech.robots.ai"))
    elif "geo.bot_access" in ids:
        fixes.append(_fix_robots(url, "geo.bot_access"))
    if "tech.llms_txt" in {f.id for f in report.findings if f.value is False}:
        fixes.append(_fix_llms(soup, url))

    return fixes


# ------------------------------------------------------------------- page-data helpers


def _og(soup: BeautifulSoup, prop: str) -> str:
    tag = soup.find("meta", attrs={"property": f"og:{prop}"})
    return (tag.get("content") or "").strip() if tag else ""


def _site_name(soup: BeautifulSoup, url: str) -> str:
    name = _og(soup, "site_name")
    if name:
        return name
    if soup.title and soup.title.string:
        # take the part after the last separator, e.g. "Page · Brand" → "Brand"
        title = soup.title.string.strip()
        for sep in ("|", "·", "—", "–", "-"):
            if sep in title:
                return title.split(sep)[-1].strip()
        return title
    return urlparse(url).hostname or "Your site"


def _first_paragraph(soup: BeautifulSoup) -> str:
    for p in soup.find_all("p"):
        t = p.get_text(" ", strip=True)
        if len(t.split()) >= 8:
            return t
    return ""


def _description(soup: BeautifulSoup) -> str:
    md = soup.find("meta", attrs={"name": "description"})
    if md and (md.get("content") or "").strip():
        return md["content"].strip()
    return _og(soup, "description") or _first_paragraph(soup)


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0].rstrip(",.;:")
    return cut + "…"


# --------------------------------------------------------------------------- generators


def _fix_schema(soup: BeautifulSoup, url: str) -> Fix:
    parsed = urlparse(url)
    root = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else url
    org: dict[str, Any] = {"@type": "Organization", "name": _site_name(soup, url), "url": root}
    logo = _og(soup, "image")
    if logo:
        org["logo"] = logo

    h1 = soup.find("h1")
    webpage: dict[str, Any] = {
        "@type": "WebPage",
        "name": (h1.get_text(strip=True) if h1 else "") or _site_name(soup, url),
        "url": url,
    }
    desc = _description(soup)
    if desc:
        webpage["description"] = _truncate(desc, 300)

    graph = {"@context": "https://schema.org", "@graph": [org, webpage]}
    body = json.dumps(graph, indent=2, ensure_ascii=False)
    return Fix(
        finding_id="schema.missing", title="Add Organization + WebPage schema", kind="json-ld",
        language="html",
        content=f'<script type="application/ld+json">\n{body}\n</script>',
        note="Paste into <head>. Fill in any blank fields and add a sameAs array of your "
        "official profile URLs to strengthen entity recognition.",
    )


def _qa_pairs(soup: BeautifulSoup) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for h in soup.find_all(["h2", "h3", "h4"]):
        q = h.get_text(strip=True)
        if "?" not in q:
            continue
        nxt, steps = h.find_next_sibling(), 0
        while nxt is not None and steps < 3:
            if getattr(nxt, "name", None) in ("h1", "h2", "h3", "h4"):
                break
            ans = nxt.get_text(" ", strip=True)
            if len(ans.split()) >= 8:
                pairs.append((q, ans))
                break
            nxt, steps = nxt.find_next_sibling(), steps + 1
    return pairs


def _has_faq_schema(soup: BeautifulSoup) -> bool:
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        if "faqpage" in (script.string or script.get_text() or "").lower():
            return True
    return False


def _fix_faq(soup: BeautifulSoup) -> Fix | None:
    if _has_faq_schema(soup):
        return None
    pairs = _qa_pairs(soup)
    if len(pairs) < 2:
        return None
    graph = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": _truncate(a, 500)}}
            for q, a in pairs
        ],
    }
    body = json.dumps(graph, indent=2, ensure_ascii=False)
    return Fix(
        finding_id="geo.faq", title="Add FAQPage schema from your Q&A", kind="json-ld",
        language="html",
        content=f'<script type="application/ld+json">\n{body}\n</script>',
        note=f"Generated from {len(pairs)} question/answer pair(s) found on the page. AI "
        "engines lift FAQPage entries almost verbatim.",
    )


def _fix_llms(soup: BeautifulSoup, url: str) -> Fix:
    parsed = urlparse(url)
    root = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else url
    name = _site_name(soup, url)
    desc = _truncate(_description(soup) or f"About {name}.", 200)
    content = (
        f"# {name}\n\n"
        f"> {desc}\n\n"
        "## Key pages\n"
        f"- [Home]({root}/): start here\n"
        f"- [Sitemap]({root}/sitemap.xml): full list of pages\n"
    )
    return Fix(
        finding_id="tech.llms_txt", title="Publish an llms.txt", kind="llms-txt",
        language="markdown", content=content,
        note=f"Save as {root}/llms.txt. Low impact today (few engines fetch it) but cheap; "
        "list your most important pages under Key pages.",
    )


def _fix_title(soup: BeautifulSoup, url: str) -> Fix:
    h1 = soup.find("h1")
    text = _truncate((h1.get_text(strip=True) if h1 else "") or _site_name(soup, url), 60)
    return Fix(
        finding_id="title.missing", title="Add a page title", kind="meta", language="html",
        content=f"<title>{text}</title>",
        note="Paste into <head>. Lead with the page's main topic; aim for ~50–60 characters.",
    )


def _fix_canonical(url: str) -> Fix:
    return Fix(
        finding_id="canonical", title="Add a canonical tag", kind="meta", language="html",
        content=f'<link rel="canonical" href="{url}">',
        note="Paste into <head> so engines consolidate ranking signals on the preferred URL.",
    )


def _fix_viewport() -> Fix:
    return Fix(
        finding_id="tech.viewport", title="Add a mobile viewport tag", kind="meta", language="html",
        content='<meta name="viewport" content="width=device-width, initial-scale=1">',
        note="Paste into <head> for correct responsive rendering on mobile.",
    )


def _fix_robots(url: str, finding_id: str) -> Fix:
    parsed = urlparse(url)
    root = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else url
    lines = ["# robots.txt — allow search + AI answer engines", "", "User-agent: *", "Allow: /", ""]
    for crawler in ("GPTBot", "ClaudeBot", "PerplexityBot", "Google-Extended", "OAI-SearchBot"):
        lines += [f"User-agent: {crawler}", "Allow: /"]
    lines += ["", f"Sitemap: {root}/sitemap.xml"]
    return Fix(
        finding_id=finding_id, title="Allow AI crawlers in robots.txt", kind="robots",
        language="text", content="\n".join(lines),
        note=f"Save as {root}/robots.txt. Explicitly allows GPTBot/ClaudeBot/PerplexityBot/"
        "Google-Extended so AI engines can read — and cite — your pages.",
    )


def _fix_meta(soup: BeautifulSoup) -> Fix | None:
    desc = _first_paragraph(soup) or _og(soup, "description")
    if not desc:
        return None
    text = _truncate(desc, 155)
    return Fix(
        finding_id="meta.description.missing", title="Add a meta description", kind="meta",
        language="html",
        content=f'<meta name="description" content="{text}">',
        note="Drafted from the opening paragraph — edit for punchiness and keep it ~120–160 "
        "characters.",
    )
