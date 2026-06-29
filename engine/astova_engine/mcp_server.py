"""astova MCP server — exposes the deterministic audit engine as Model Context Protocol tools,
so an AI assistant (ChatGPT, Claude Desktop, Claude Code) can audit a URL by *calling the engine*
instead of pasting HTML and asking the model to eyeball a score.

This is the wedge: the assistant gets a reproducible scorecard from real HTML parsers, not an
LLM guess. Run it over stdio:

    pip install -e ".[mcp]"
    python -m astova_engine.mcp_server

Client config (Claude Desktop / Claude Code / ChatGPT desktop):
    {"mcpServers": {"astova": {"command": "python", "args": ["-m", "astova_engine.mcp_server"]}}}
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .crawl import crawl
from .fixes import build_fix_plan
from .scanner import scan, scan_project

mcp = FastMCP("astova")

_SEV_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
_MAX_ISSUES = 10


def _top_issues(findings: list[dict]) -> list[dict]:
    issues = [f for f in findings if f["status"] in ("fail", "warn")]
    issues.sort(key=lambda f: _SEV_RANK.get(f["severity"], 9))
    return [
        {
            "id": f["id"], "title": f["title"], "pillar": f["pillar"],
            "severity": f["severity"], "status": f["status"],
            "evidence": f["evidence"], "recommendation": f["recommendation"],
        }
        for f in issues[:_MAX_ISSUES]
    ]


def _audit_payload(report) -> dict:
    """Compact scorecard + prioritised issues — what an assistant needs to reason and advise."""
    d = report.to_dict()
    if d["meta"].get("error"):
        return {"url": report.url, "error": d["meta"]["error"]}
    sc = d.get("scorecard") or {}
    return {
        "url": d["meta"].get("final_url", report.url),
        "ai_retrievability": sc.get("headline_score"),
        "technical_score": sc.get("technical_score"),
        "overlay": sc.get("overlay"),
        "categories": sc.get("categories"),
        "rows": [{"n": r["n"], "label": r["label"], "score": r["score"], "status": r["status"]}
                 for r in sc.get("rows", [])],
        "top_issues": _top_issues(d["findings"]),
        "confidence": "verified",
        "note": "Deterministic audit — reads the live HTML with real parsers and reproduces "
                "identically on re-run. Not an LLM estimate.",
    }


@mcp.tool()
def audit_url(url: str) -> dict:
    """Run a deterministic GEO/AEO/SEO audit of a web page and return its AI Retrievability
    scorecard: a headline 0-100 score, a 20-row breakdown, category scores, the +8 bonus
    overlay, and the top prioritised issues with fix recommendations.

    Use this whenever you need to assess how well a page is optimised to be cited by AI answer
    engines (ChatGPT, Claude, Perplexity, Google AI Overviews) and to rank in search. It reads
    the live page with real HTML parsers, so results are reproducible — not an estimate.

    Args:
        url: The page URL to audit, e.g. https://example.com/pricing.
    """
    return _audit_payload(scan(url, fixes=False))


@mcp.tool()
def fix_plan(url: str) -> dict:
    """Audit a page and return a complete, agent-actionable remediation plan — everything an AI
    coding agent needs to FIX the page itself, ordered by severity.

    Each item carries: the finding it resolves, an `action` (create_file / add_to_head /
    rewrite_content / review), a `target` location hint, the exact `content` to apply (for
    deterministic fixes), and a plain-English `instruction`. Deterministic fixes (schema,
    robots.txt, llms.txt, meta) come ready to paste; judgment-dependent ones are flagged
    `ai_draftable` for you to write the edit. astova diagnoses; you apply the fix to the files.

    Use this after audit_url when the user wants to actually fix the issues, not just see them.

    Args:
        url: The page URL to audit and plan fixes for (e.g. http://localhost:3000/pricing).
    """
    report = scan(url, fixes=True)
    d = report.to_dict()
    if d["meta"].get("error"):
        return {"url": report.url, "error": d["meta"]["error"]}
    sc = d.get("scorecard") or {}
    return {
        "url": d["meta"].get("final_url", report.url),
        "ai_retrievability": sc.get("headline_score"),
        "verdict": (sc.get("summary") or {}).get("verdict"),
        "fixes": build_fix_plan(report),
        "confidence": "verified",
        "note": "Deterministic audit. Apply each fix to your source files (you have them); "
                "astova supplies the exact remediation. Re-run to confirm the score rose.",
    }


@mcp.tool()
def scan_url(url: str) -> dict:
    """Full deterministic scan of a web page: every finding (on-page, technical, GEO-readiness)
    with status, severity, evidence and a recommendation, plus pillar scores and the 20-row
    scorecard. Use when you need the complete check-by-check detail rather than the summary.

    Args:
        url: The page URL to scan.
    """
    return scan(url, fixes=False).to_dict()


@mcp.tool()
def audit_project(root_path: str, framework: str = "auto", base_url: str | None = None,
                  max_pages: int = 1) -> dict:
    """Audit a project DIRECTORY and get back the SAME scorecard a URL audit returns - the preferred
    tool when you're working INSIDE a repository. Analyse the source directly instead of needing a
    deployed URL: it reads robots.txt, llms.txt, sitemap.xml, the framework/host config (security
    headers) and any static HTML straight off disk, detects the framework (Next.js / Astro /
    WordPress / static / Gatsby), and returns a standard Report (findings, pillar scores, scorecard).

    Deterministic and READ-ONLY: it never modifies files, never generates fixes, never calls an LLM.
    Deploy-only signals that source can't prove (HTTPS, TLS, status, redirects, compression) are
    omitted rather than guessed. After it, use explain_finding / generate_fix on a finding id to
    remediate. When run from the LOCAL MCP everything executes on your machine - source never leaves.

    Pass base_url (your running dev server, e.g. http://localhost:3000) to ALSO render-audit the live
    page under `live_audit` (max_pages>1 crawls the running site, up to 50 pages).

    Args:
        root_path: Path to the project root (the folder with package.json / wp-config.php / etc.).
        framework: "auto" to detect, or one of nextjs / astro / wordpress / static / gatsby / node.
        base_url: Optional URL of the running app to also render-audit (typically http://localhost:PORT).
        max_pages: Pages to crawl from base_url (1 = just that page; >1 = crawl the site).
    """
    out = scan_project(root_path, framework).to_dict()
    if not base_url:
        return out

    if max_pages > 1:
        sd = crawl(base_url, max_pages=min(max_pages, 50)).to_dict()
        out["live_audit"] = ({"error": sd["meta"]["error"]} if sd["meta"].get("error") else {
            "url": sd["url"], "overall_score": sd["overall_score"],
            "pages": [{"url": p["url"], "score": p["overall_score"], "issues": p["issues"]}
                      for p in sd["pages"]],
        })
    else:
        out["live_audit"] = scan(base_url, fixes=False).to_dict()
    return out


@mcp.tool()
def explain_finding(finding_id: str) -> dict:
    """Explain a single Astova finding: what it is, why it matters for AI answer engines, how to fix
    it, and exactly how an AI coding agent should approach the fix - what to change, what to NEVER
    automate (e.g. fabricating facts/identity), and how to verify. Use this after a scan once you
    have a finding id and want to remediate it safely.

    Returns structured fields: name, summary, category, can_astova_generate, agent_can_automate,
    human_review_required, why_it_matters, how_to_fix, agent_guidance, framework_examples,
    verification, related_findings.

    Args:
        finding_id: an Astova finding id from a scan, e.g. "geo.aeo", "schema.missing",
            "tech.robots.ai" (a card key like "aeo" also works)."""
    from . import knowledge

    result = knowledge.explain(finding_id)
    if result is None:
        return {
            "error": f"Unknown finding id '{finding_id}'.",
            "hint": "Pass a finding id returned by audit_url / scan_url, e.g. geo.aeo or schema.missing.",
            "known_finding_ids": knowledge.known_finding_ids(),
        }
    return result


@mcp.tool()
def generate_fix(finding_id: str, url: str = "", html: str = "") -> dict:
    """Generate a DETERMINISTIC, ready-to-apply fix for a single finding. No LLM, and the fix is NOT
    applied - it returns the exact content for you (the coding agent) to apply, plus where it goes.

    Returns a consistent object: finding_id, deterministic (bool), supported (bool), explanation,
    generated_content (the exact snippet/file body, or null), target_type ("head_element"|"file"),
    suggested_location, verification_method.

    Supported findings today: schema.missing, geo.faq, tech.robots.missing, tech.robots.ai,
    tech.llms_txt, canonical, tech.viewport. For an unsupported finding, supported is false and the
    explanation says why (use explain_finding for guidance).

    Args:
        finding_id: the finding to fix, e.g. "schema.missing", "canonical", "tech.robots.ai".
        url: the page URL (the context; required for most fixes).
        html: optional page HTML - produces a richer schema/llms.txt fix and is required for an FAQ fix."""
    from .fixes import generate_fix as _generate_fix

    return _generate_fix(finding_id, {"url": url, "html": html or None})


@mcp.tool()
def verify_fix(target: str, finding_id: str, target_type: str = "url") -> dict:
    """Deterministically verify whether a finding is RESOLVED after you applied a change. You make the
    edit yourself, then call this - Astova re-runs the same scan and checks that one finding. No LLM, no
    fix applied, no files touched.

    target_type "url" re-scans a live page; "project" re-audits a repo directory (the same audit_project
    runs). A finding counts as fixed when it is gone from the new scan, or present with status pass/info;
    it is not fixed while it is warn/fail.

    Returns: target, target_type, finding_id, fixed (bool), current_status, current_severity, evidence,
    score_after, confidence, explanation, next_step. A failed re-scan returns the same shape with an
    `error` and current_status "error".

    Args:
        target: the URL (target_type="url") or project directory path (target_type="project") to re-scan.
        finding_id: the finding to check, e.g. "schema.missing", "tech.llms_txt", "canonical".
        target_type: "url" (default) or "project".
    """
    from .verify import verify_fix as _verify_fix

    return _verify_fix(target, finding_id, target_type)


@mcp.tool()
def ai_ready_loop(target: str, target_type: str = "url", max_items: int = 10) -> dict:
    """"Tell me exactly what to fix next." ONE call returns the complete, prioritised next-action plan
    to make a URL or project AI Ready - the recommended starting point for an AI coding agent.

    It assesses the target (the same URL scan or project audit), selects the highest-severity fail/warn
    findings (up to max_items), and for each attaches: the finding (id, title, status, severity,
    confidence, evidence, recommendation), its knowledge card (explain_finding, or null if none), the
    deterministic fix (generate_fix, with supported:false when there's no ready fix), the exact
    verify_fix call to confirm it, and a one-line agent_next_step. No LLM, nothing applied, no files touched.

    Returns summary counts (deterministic_fix_count / ai_assisted_count / manual_count) plus the items
    array. Loop: pick an item, apply its fix (or draft per its knowledge), call verify_fix, repeat.

    Args:
        target: the URL (target_type="url") or project directory path (target_type="project").
        target_type: "url" (default) or "project".
        max_items: max findings to return, highest severity first (default 10).
    """
    from .ai_ready import ai_ready_loop as _ai_ready_loop

    return _ai_ready_loop(target, target_type, max_items)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
