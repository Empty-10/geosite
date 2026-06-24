"""damask MCP server — exposes the deterministic audit engine as Model Context Protocol tools,
so an AI assistant (ChatGPT, Claude Desktop, Claude Code) can audit a URL by *calling the engine*
instead of pasting HTML and asking the model to eyeball a score.

This is the wedge: the assistant gets a reproducible scorecard from real HTML parsers, not an
LLM guess. Run it over stdio:

    pip install -e ".[mcp]"
    python -m damask_engine.mcp_server

Client config (Claude Desktop / Claude Code / ChatGPT desktop):
    {"mcpServers": {"damask": {"command": "python", "args": ["-m", "damask_engine.mcp_server"]}}}
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .scanner import scan

mcp = FastMCP("damask")

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
def scan_url(url: str) -> dict:
    """Full deterministic scan of a web page: every finding (on-page, technical, GEO-readiness)
    with status, severity, evidence and a recommendation, plus pillar scores and the 20-row
    scorecard. Use when you need the complete check-by-check detail rather than the summary.

    Args:
        url: The page URL to scan.
    """
    return scan(url, fixes=False).to_dict()


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
