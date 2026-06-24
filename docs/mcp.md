# damask MCP server

Exposes the deterministic audit engine as [Model Context Protocol](https://modelcontextprotocol.io)
tools, so an AI assistant audits a URL by **calling the engine** instead of pasting HTML and
asking the model to eyeball a score. The assistant gets a reproducible scorecard from real HTML
parsers — not an LLM guess. This is the deterministic replacement for the "paste your site's HTML
into ChatGPT and score it" workflow.

## Tools

| Tool | Returns |
|---|---|
| `audit_url(url)` | AI Retrievability scorecard — headline 0–100, the 20-row breakdown, category scores, the +8 overlay, and the top prioritised issues with fix recommendations. |
| `scan_url(url)`  | Full report — every finding (on-page / technical / GEO-readiness) with status, severity, evidence, recommendation, plus pillar scores and the scorecard. |

## Run

```bash
cd engine
pip install -e ".[mcp]"
python -m damask_engine.mcp_server     # speaks MCP over stdio
```

## Connect a client

Add to the client's MCP config (Claude Desktop: `claude_desktop_config.json`; Claude Code:
`.mcp.json`; ChatGPT desktop: Settings → Connectors → add MCP server):

```json
{
  "mcpServers": {
    "damask": {
      "command": "python",
      "args": ["-m", "damask_engine.mcp_server"]
    }
  }
}
```

Use the absolute path to the venv's Python (e.g. `engine/.venv/bin/python`) if `python` on the
PATH isn't the one with the engine installed.

Then ask the assistant: *"Audit https://example.com/pricing for AI visibility"* — it calls
`audit_url` and reasons over the deterministic scorecard.

## Notes

- Every number is **VERIFIED** — read straight from the live HTML, reproducible on re-run.
- `audit_url` runs a fast scan (no PageSpeed/render) so it returns in ~1–3s.
- The same scorecard shape powers the web report and the WordPress plugin — one engine, many
  front doors.
