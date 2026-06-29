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


# Findings whose remediation is judgment-dependent (an AI coding agent should draft the edit
# rather than paste a fixed artifact). Mirrors the web GENERATIVE_FINDINGS set.
GENERATIVE_FINDINGS = {"geo.aeo", "geo.frontload", "geo.definitive", "geo.thin_content"}

_SEV_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

# How an AI coding agent should apply each fix kind: (action, target hint, how-to).
_FIX_ACTION = {
    "robots": ("create_file", "robots.txt (site root)",
               "Create or replace robots.txt at your web root — public/robots.txt in Next.js, "
               "the document root for a static site, or your CMS's robots settings."),
    "llms-txt": ("create_file", "llms.txt (site root)",
                 "Create llms.txt at your web root — e.g. public/llms.txt in Next.js."),
    "json-ld": ("add_to_head", "page <head>",
                "Add this JSON-LD <script> to the page's <head> — your layout/template or the "
                "page's head component."),
    "meta": ("add_to_head", "page <head>",
             "Add or replace this tag in the page's <head>."),
}
_FIX_ACTION_DEFAULT = ("edit_content", "page content", "Apply this change to the page.")


def _enum_val(x: Any) -> Any:
    return getattr(x, "value", x)


def actionable_fix(fix: "Fix", finding: Any | None = None) -> dict:
    """Shape a deterministic Fix for an AI coding agent: what to do, where, and the exact content.
    The dev's assistant has the files; astova supplies the precise, ready-to-apply remediation."""
    action, target, how = _FIX_ACTION.get(fix.kind, _FIX_ACTION_DEFAULT)
    out = {
        "finding_id": fix.finding_id,
        "title": fix.title,
        "action": action,
        "target": target,
        "language": fix.language,
        "content": fix.content,
        "instruction": f"{how} {fix.note}" if fix.note else how,
        "source": "deterministic",
        "ai_draftable": False,
    }
    if finding is not None:
        out["severity"] = _enum_val(finding.severity)
        out["evidence"] = finding.evidence
    return out


def build_fix_plan(report: Report) -> list[dict]:
    """A complete, agent-actionable remediation list for a scanned report, ordered by severity:
    deterministic artifacts where we can generate them, advisory steps (carrying the finding's
    recommendation) otherwise. Everything an AI coding agent needs to fix the page itself.

    Requires the report to have been scanned with fixes=True (so report.fixes is populated).
    """
    fixes_by_id = {fx.finding_id: fx for fx in (report.fixes or [])}
    issues = [f for f in report.findings if _enum_val(f.status) in ("fail", "warn")]
    issues.sort(key=lambda f: _SEV_RANK.get(_enum_val(f.severity), 9))

    plan: list[dict] = []
    for f in issues:
        fx = fixes_by_id.get(f.id)
        if fx is not None:
            plan.append(actionable_fix(fx, f))
        elif f.recommendation:
            plan.append({
                "finding_id": f.id,
                "title": f.title,
                "action": "rewrite_content" if f.id in GENERATIVE_FINDINGS else "review",
                "target": "page content",
                "instruction": f.recommendation,
                "evidence": f.evidence,
                "severity": _enum_val(f.severity),
                "source": "advisory",
                "ai_draftable": f.id in GENERATIVE_FINDINGS,
            })
    return plan


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
    if "local.business_schema" in ids:
        fixes.append(_fix_local_schema(soup, url))
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


def _fix_local_schema(soup: BeautifulSoup, url: str) -> Fix:
    name = _site_name(soup, url)
    obj = {
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
        "name": name,
        "url": url,
        "telephone": "+1-000-000-0000",
        "address": {
            "@type": "PostalAddress",
            "streetAddress": "123 Main St",
            "addressLocality": "City",
            "addressRegion": "ST",
            "postalCode": "00000",
            "addressCountry": "US",
        },
        "geo": {"@type": "GeoCoordinates", "latitude": "0.0", "longitude": "0.0"},
        "openingHoursSpecification": [{
            "@type": "OpeningHoursSpecification",
            "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            "opens": "09:00", "closes": "17:00",
        }],
        "sameAs": ["https://g.page/your-business"],
    }
    body = json.dumps(obj, indent=2)
    return Fix(
        finding_id="local.business_schema", title="Add LocalBusiness schema", kind="json-ld",
        language="html", content=f'<script type="application/ld+json">\n{body}\n</script>',
        note="Replace the placeholder address, phone, geo coordinates, hours and Google Business "
        "Profile URL with your real details, then add to the page <head>.",
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


# --------------------------------------------------------------- on-demand single-finding fixes
#
# generate_fix(finding_id, context) - a deterministic, machine-readable fix for ONE finding,
# requested directly (e.g. by an AI coding agent) without a full scan. No LLM, no application of
# the change, no file writes. Reuses the generators above; no duplicated logic.

# Findings that have a deterministic generator in this module (deterministic=True in the response).
DETERMINISTIC_FINDINGS = {
    "title.missing", "meta.description.missing", "canonical", "tech.viewport",
    "schema.missing", "geo.faq", "tech.robots.missing", "tech.robots.ai",
    "geo.bot_access", "local.business_schema", "tech.llms_txt",
}

# Findings generate_fix() currently supports (the initial agent-facing set).
SUPPORTED_FIX_FINDINGS = {
    "schema.missing", "geo.faq", "tech.robots.missing", "tech.robots.ai",
    "tech.llms_txt", "canonical", "tech.viewport",
}

# Accept the alternate id an agent might pass.
_FINDING_ALIASES = {"onpage.canonical": "canonical"}

# generated Fix.kind -> (target_type, suggested_location) for the response object.
_TARGET_BY_KIND = {
    "json-ld": ("head_element", "page <head>"),
    "meta": ("head_element", "page <head>"),
    "robots": ("file", "robots.txt (site root)"),
    "llms-txt": ("file", "llms.txt (site root)"),
}

# Findings whose generator needs the page URL.
_NEEDS_URL = {"schema.missing", "tech.robots.missing", "tech.robots.ai", "tech.llms_txt", "canonical"}


def _fix_response(finding_id: str, *, deterministic: bool, supported: bool,
                  explanation: str, fix: "Fix | None" = None) -> dict:
    target_type = suggested_location = generated_content = None
    if fix is not None:
        target_type, suggested_location = _TARGET_BY_KIND.get(fix.kind, ("content", "page content"))
        generated_content = fix.content
    return {
        "finding_id": finding_id,
        "deterministic": deterministic,
        "supported": supported,
        "explanation": explanation,
        "generated_content": generated_content,
        "target_type": target_type,
        "suggested_location": suggested_location,
        "verification_method": (
            f"Re-scan the page with Astova; the '{finding_id}' check should report PASS."
        ),
    }


def generate_fix(finding_id: str, context: dict | None = None) -> dict:
    """Deterministically generate a structured fix for a single supported finding.

    No LLM, no application of the change, no file writes - it returns the exact content to apply.
    context carries the page: {"url": str, "html"?: str}. The page HTML is optional but produces a
    richer schema/llms.txt fix and is required for an FAQ fix. Reuses the module's deterministic
    generators; no duplicated logic. Always returns the consistent response object.
    """
    context = context or {}
    raw_id = (finding_id or "").strip()
    fid = _FINDING_ALIASES.get(raw_id, raw_id)
    deterministic = fid in DETERMINISTIC_FINDINGS
    url = (context.get("url") or "").strip()
    soup = BeautifulSoup(context.get("html") or "", "html.parser")

    if fid not in SUPPORTED_FIX_FINDINGS:
        return _fix_response(
            raw_id, deterministic=deterministic, supported=False, fix=None,
            explanation=(
                "A deterministic fix exists for this finding but generate_fix does not support it yet."
                if deterministic else
                "No deterministic fix is available for this finding - it needs an AI-assisted or human "
                "edit. Call explain_finding for guidance."
            ),
        )

    if fid in _NEEDS_URL and not url:
        return _fix_response(
            raw_id, deterministic=True, supported=False, fix=None,
            explanation='Provide the page URL in context, e.g. {"url": "https://example.com/page"}.',
        )

    if fid == "schema.missing":
        fix: "Fix | None" = _fix_schema(soup, url)
    elif fid == "geo.faq":
        fix = _fix_faq(soup)
        if fix is None:
            return _fix_response(
                raw_id, deterministic=True, supported=False, fix=None,
                explanation=(
                    "No FAQPage schema generated. The page HTML must contain at least two question-style "
                    "headings (h2/h3/h4 ending in '?'), each followed by an answer of 8+ words, and no "
                    "existing FAQPage schema. Pass the page HTML in context.html."
                ),
            )
    elif fid in ("tech.robots.missing", "tech.robots.ai"):
        fix = _fix_robots(url, fid)
    elif fid == "tech.llms_txt":
        fix = _fix_llms(soup, url)
    elif fid == "canonical":
        fix = _fix_canonical(url)
    else:  # tech.viewport
        fix = _fix_viewport()

    return _fix_response(
        raw_id, deterministic=True, supported=True, fix=fix,
        explanation=f"{fix.title}. {fix.note or ''}".strip(),
    )
