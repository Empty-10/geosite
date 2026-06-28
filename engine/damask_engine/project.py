"""Pre-deploy project checks — deterministic audit of a project's static root files (robots.txt,
llms.txt, sitemap.xml) plus layout-aware fix targets.

Pure: the MCP layer reads files from disk and passes their contents in, so this stays
offline-testable. The point is to catch GEO problems *before* deploy, in the editor — and to
return fixes with real file paths the dev's coding agent can act on directly.
"""

from __future__ import annotations

# AI answer-engine crawlers we want allowed (operator-documented user agents).
AI_CRAWLERS = ["GPTBot", "ClaudeBot", "anthropic-ai", "PerplexityBot", "Google-Extended", "OAI-SearchBot"]

_ROBOTS_ALLOW = "\n".join(
    ["# robots.txt — allow search + AI answer engines", "", "User-agent: *", "Allow: /", ""]
    + sum(([f"User-agent: {c}", "Allow: /"] for c in AI_CRAWLERS), [])
    + ["", "Sitemap: https://YOUR-DOMAIN/sitemap.xml"]
)

_LLMS_STARTER = (
    "# Your site name\n"
    "> One sentence on what your site or product does.\n\n"
    "## Key pages\n"
    "- [Home](https://your-domain/): what it covers\n"
    "- [Pricing](https://your-domain/pricing): plans and prices\n"
    "- [Docs](https://your-domain/docs): documentation\n"
)


def detect_framework(markers: set[str]) -> tuple[str, str]:
    """Infer (framework, public_dir) from the files/dirs present at the project root."""
    if any(m.startswith("next.config") for m in markers):
        return "nextjs", "public"
    if any(m.startswith("astro.config") for m in markers):
        return "astro", "public"
    if "gatsby-config.js" in markers or "gatsby-config.ts" in markers:
        return "gatsby", "static"
    if "wp-config.php" in markers or "wp-content" in markers:
        return "wordpress", "."
    if "package.json" in markers:
        return "node", "public"
    return "static", "."


def _robots_groups(txt: str) -> list[tuple[list[str], list[str]]]:
    """Parse robots.txt into (user-agents, disallow-paths) groups."""
    groups: list[tuple[list[str], list[str]]] = []
    agents: list[str] = []
    disallows: list[str] = []
    for raw in txt.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        field, _, val = line.partition(":")
        field, val = field.strip().lower(), val.strip()
        if field == "user-agent":
            if agents and disallows:  # a new group begins after a completed one
                groups.append((agents, disallows))
                agents, disallows = [], []
            agents.append(val)
        elif field == "disallow":
            disallows.append(val)
    if agents:
        groups.append((agents, disallows))
    return groups


def robots_blocked_ai(txt: str) -> list[str]:
    """The AI crawlers blocked (Disallow: /) — by a UA-specific rule or the wildcard group."""
    groups = _robots_groups(txt)
    blocked = []
    for ua in AI_CRAWLERS:
        dis = next((d for agents, d in groups if ua.lower() in [a.lower() for a in agents]), None)
        if dis is None:
            dis = next((d for agents, d in groups if "*" in agents), None)
        if dis and any(p.strip() == "/" for p in dis):
            blocked.append(ua)
    return blocked


def analyze_files(*, robots_txt: str | None, llms_txt: str | None, sitemap_xml: str | None,
                  public_dir: str) -> dict:
    """Deterministic checks on a project's static root files → status + agent-actionable fixes."""
    p = "" if public_dir in (".", "") else f"{public_dir}/"
    fixes: list[dict] = []
    status: dict[str, str] = {}

    # robots.txt
    if robots_txt is None:
        status["robots"] = "missing"
        fixes.append({
            "finding_id": "project.robots_missing", "title": "Add robots.txt that allows AI crawlers",
            "severity": "medium", "action": "create_file", "target": f"{p}robots.txt",
            "language": "text", "content": _ROBOTS_ALLOW, "source": "deterministic",
            "instruction": f"Create {p}robots.txt so AI crawlers (and search) can read the site.",
        })
    else:
        blocked = robots_blocked_ai(robots_txt)
        if blocked:
            status["robots"] = "blocks_ai"
            fixes.append({
                "finding_id": "project.robots_blocks_ai",
                "title": f"robots.txt blocks AI crawlers: {', '.join(blocked)}",
                "severity": "critical", "action": "edit_file", "target": f"{p}robots.txt",
                "language": "text", "content": _ROBOTS_ALLOW, "source": "deterministic",
                "instruction": f"Remove the Disallow: / for {', '.join(blocked)} — they can't cite "
                               f"what they can't crawl. Replace {p}robots.txt with this, or delete "
                               "the blocking rule.",
            })
        else:
            status["robots"] = "ok"

    # llms.txt
    if llms_txt is None:
        status["llms"] = "missing"
        fixes.append({
            "finding_id": "project.llms_missing", "title": "Add an llms.txt",
            "severity": "low", "action": "create_file", "target": f"{p}llms.txt",
            "language": "markdown", "content": _LLMS_STARTER, "source": "deterministic",
            "instruction": f"Create {p}llms.txt — a concise, AI-readable map of your key pages. "
                           "Edit the placeholders.",
        })
    else:
        status["llms"] = "present"

    # sitemap.xml (often framework-generated, so advisory)
    if sitemap_xml is None:
        status["sitemap"] = "missing"
        fixes.append({
            "finding_id": "project.sitemap_missing", "title": "No sitemap.xml in the project",
            "severity": "medium", "action": "review", "target": f"{p}sitemap.xml",
            "source": "advisory",
            "instruction": "Add a sitemap — most frameworks generate one (e.g. app/sitemap.ts in "
                           "Next.js, a sitemap plugin in WordPress). Reference it from robots.txt.",
        })
    elif "<url" not in sitemap_xml.lower():
        status["sitemap"] = "invalid"
        fixes.append({
            "finding_id": "project.sitemap_invalid", "title": "sitemap.xml has no <url> entries",
            "severity": "medium", "action": "review", "target": f"{p}sitemap.xml",
            "source": "advisory",
            "instruction": "The sitemap contains no <url> entries — regenerate it so it lists your "
                           "pages.",
        })
    else:
        status["sitemap"] = "present"

    return {"status": status, "fixes": fixes}
