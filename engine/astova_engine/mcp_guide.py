"""Static MCP usage guide - returns setup + starter prompt + tool list for a given MCP client.

Pure and static: no scanning, no file reads, no LLM, no network. It exists so a developer can ask the
Astova MCP itself "how do I set this up and use it?" and get exact, client-specific instructions.
"""

from __future__ import annotations

_PURPOSE = (
    "Astova audits your site or project for AI Readiness deterministically, hands your AI coding agent the "
    "exact fixes, and verifies the result - no LLM guesswork. The agent edits the code; Astova diagnoses, "
    "supplies deterministic fixes where possible, and confirms the change."
)

_RECOMMENDED_ENTRYPOINTS = [
    {"tool": "prepare_project_for_ai", "when_to_use": "local repository / coding agent workflow"},
    {"tool": "ai_ready_loop", "when_to_use": "URL audit or quick next-action plan"},
]

_WORKFLOW = [
    "Call prepare_project_for_ai('.') in a repo (or ai_ready_loop('<url>') for a single site) to get the plan.",
    "Apply each deterministic fix exactly as given - it is ready to paste.",
    "Draft AI-assisted items only from real, existing page content.",
    "Ask the user before editing any manual or human-review item.",
    "Call verify_fix for changed findings, then re-run the audit to confirm the score improved.",
]

_SAFETY_RULES = [
    "Do not invent facts.",
    "Do not invent author names.",
    "Do not invent sameAs links.",
    "Do not invent local-business details (names, addresses, opening hours).",
    "Ask before editing manual or human-review items.",
    "Verify changes with verify_fix or another audit.",
]

# Every MCP tool, one line each. Keep in sync with mcp_server.py (a test cross-checks this).
_AVAILABLE_TOOLS = [
    {"tool": "prepare_project_for_ai",
     "description": "One read-only call: full fix context for a local repo (findings + knowledge + fixes + "
                    "verify). Start here in a repository."},
    {"tool": "ai_ready_loop",
     "description": "Prioritised 'what to fix next' plan for a URL or project."},
    {"tool": "audit_url",
     "description": "Deterministic GEO/AEO/SEO scorecard for a URL (headline score, rows, top issues)."},
    {"tool": "scan_url",
     "description": "Full report: every finding with status, severity, evidence and recommendation for a URL."},
    {"tool": "audit_project",
     "description": "Audit a project directory from source; returns the standard Report."},
    {"tool": "fix_plan",
     "description": "Ordered, agent-actionable remediation plan for a URL."},
    {"tool": "explain_finding",
     "description": "Per-finding knowledge: why it matters, how to fix, and what to never automate."},
    {"tool": "generate_fix",
     "description": "Deterministic, ready-to-apply fix for a supported finding (returned, not applied)."},
    {"tool": "verify_fix",
     "description": "Re-scan to confirm one finding is resolved after you change the code."},
    {"tool": "mcp_usage_guide",
     "description": "This guide: setup, starter prompt and tool list for your MCP client."},
]

_CONFIG_JSON = (
    '{"mcpServers": {"astova": {"command": "python", "args": ["-m", "astova_engine.mcp_server"]}}}'
)
_INSTALL = "Install the engine with MCP support: run `pip install -e '.[mcp]'` in the engine/ directory."

# Prompt for an agent working inside a repository (Claude Code / Cursor / Windsurf).
_REPO_PROMPT = (
    "Use the Astova MCP on this repository. Call prepare_project_for_ai('.'), then work the findings in "
    "order: apply each deterministic fix exactly, draft AI-assisted items only from real page content, and "
    "ask me before any manual or human-review item. After changes, call verify_fix for the affected "
    "findings and re-run prepare_project_for_ai to confirm the score improved. Do not invent facts, author "
    "names, sameAs links or local-business details."
)
# Prompt for a URL-first assistant (ChatGPT).
_URL_PROMPT = (
    "Use the Astova MCP. Call ai_ready_loop('<your-site-url>') to get a prioritised action plan, then walk "
    "me through the top fixes. For each, call explain_finding, and call generate_fix where a deterministic "
    "fix exists. Do not invent facts, author names, sameAs links or local-business details; flag any manual "
    "or human-review item for me to confirm before changing it."
)
_GENERIC_PROMPT = (
    "Use the Astova MCP to make this project AI Ready. In a repo, call prepare_project_for_ai('.'); for a "
    "single site, call ai_ready_loop('<url>'). Apply deterministic fixes as given, draft AI-assisted items "
    "only from real content, ask me before manual or human-review items, then call verify_fix after "
    "changes. Do not invent facts, author names, sameAs links or local-business details."
)

_CLIENTS = {
    "generic": {
        "setup": [
            _INSTALL,
            "Register an MCP server named 'astova' that runs `python -m astova_engine.mcp_server` over stdio.",
            f"Config: {_CONFIG_JSON}",
            "Restart your MCP client, then confirm the Astova tools are listed.",
        ],
        "starter_prompt": _GENERIC_PROMPT,
    },
    "claude": {
        "setup": [
            _INSTALL,
            "In Claude Desktop, open Settings -> Developer -> Edit Config and add the 'astova' server under "
            f"mcpServers: {_CONFIG_JSON}",
            "If `python` isn't on Claude's PATH, use the absolute path to your engine venv's python.",
            "Restart Claude Desktop; the Astova tools appear in the tools menu.",
        ],
        "starter_prompt": _REPO_PROMPT,
    },
    "cursor": {
        "setup": [
            _INSTALL,
            "In Cursor, open Settings -> MCP -> Add new server: name 'astova', command `python`, "
            "args `-m astova_engine.mcp_server`.",
            "Point the command at your engine venv's python if `python` isn't resolved globally.",
            "Reload Cursor; the Astova tools are available to the agent.",
        ],
        "starter_prompt": _REPO_PROMPT,
    },
    "chatgpt": {
        "setup": [
            _INSTALL,
            "In ChatGPT desktop, add an MCP connector that runs `python -m astova_engine.mcp_server` (stdio).",
            "Grant the connector permission to call the Astova tools.",
            "ChatGPT works best on a live URL - start with ai_ready_loop rather than a local repo.",
        ],
        "starter_prompt": _URL_PROMPT,
    },
    "windsurf": {
        "setup": [
            _INSTALL,
            "In Windsurf, open Cascade -> MCP settings -> Add server: name 'astova', command `python`, "
            "args `-m astova_engine.mcp_server`.",
            "Use your engine venv python path if `python` isn't resolved globally.",
            "Reload Windsurf; the Astova tools are available to Cascade.",
        ],
        "starter_prompt": _REPO_PROMPT,
    },
}

SUPPORTED_CLIENTS = tuple(_CLIENTS)


def usage_guide(client: str = "generic") -> dict:
    """Return the compact, client-specific setup + usage guide for the Astova MCP."""
    key = (client or "generic").strip().lower()
    if key not in _CLIENTS:
        key = "generic"
    spec = _CLIENTS[key]
    return {
        "client": key,
        "purpose": _PURPOSE,
        "recommended_entrypoints": [dict(e) for e in _RECOMMENDED_ENTRYPOINTS],
        "setup": list(spec["setup"]),
        "starter_prompt": spec["starter_prompt"],
        "workflow": list(_WORKFLOW),
        "safety_rules": list(_SAFETY_RULES),
        "available_tools": [dict(t) for t in _AVAILABLE_TOOLS],
    }
