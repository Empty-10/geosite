# astova MCP server

Exposes the deterministic audit engine as [Model Context Protocol](https://modelcontextprotocol.io)
tools, so an AI assistant audits a URL by **calling the engine** instead of pasting HTML and
asking the model to eyeball a score. The assistant gets a reproducible scorecard from real HTML
parsers — not an LLM guess. This is the deterministic replacement for the "paste your site's HTML
into ChatGPT and score it" workflow.

## Tools

| Tool | Returns |
|---|---|
| `ai_ready_loop(target, target_type="url", max_items=10)` | **Start here. "Tell me exactly what to fix next."** One call returns the complete prioritised plan to make a URL or project AI Ready. Assesses the target (URL scan or project audit), selects the highest-severity fail/warn findings, and per item attaches: the finding (id, title, status, severity, confidence, evidence, recommendation), its `knowledge` card (`explain_finding`, or `null`), the deterministic `fix` (`generate_fix`, with `supported:false` when none), the exact `verify_fix` call, and a one-line `agent_next_step`. Top-level counts: `deterministic_fix_count` / `ai_assisted_count` / `manual_count`. Pure orchestration of the tools below - no new scan logic, **no LLM, nothing applied, no files touched**. The loop: pick an item → apply its fix (or draft per its knowledge) → `verify_fix` → repeat. Also on the HTTP API (`POST /ai-ready`, which adds a `markdown` action plan) and the web app (`/ai-ready`). |
| `audit_url(url)` | AI Retrievability scorecard — headline 0–100, the 20-row breakdown, category scores, the +8 overlay, and the top prioritised issues with fix recommendations. |
| `scan_url(url)`  | Full report — every finding (on-page / technical / GEO-readiness) with status, severity, evidence, recommendation, plus pillar scores and the scorecard. |
| `fix_plan(url)`  | A complete, **agent-actionable** remediation plan, ordered by severity. Each item: the `finding_id` it resolves, an `action` (`create_file` / `add_to_head` / `rewrite_content` / `review`), a `target` location hint, the exact `content` to apply (deterministic fixes), a plain-English `instruction`, `source` (`deterministic` \| `advisory`) and `ai_draftable`. **astova diagnoses; the dev's coding agent applies the fix to the files** — so "audit my project and fix everything" becomes a loop: `fix_plan` → apply → `audit_url` to confirm. |
| `audit_project(root_path, framework?, base_url?, max_pages?)` | **The preferred tool when working INSIDE a repo.** Audits a project DIRECTORY and returns the **same `Report`** a URL audit returns (findings with canonical ids, pillar scores, scorecard) - so every downstream tool (`explain_finding`, `generate_fix`) works on it unchanged. Reads `robots.txt`, `llms.txt`, `sitemap.xml`, the framework/host config (security headers) and any static HTML straight off disk; detects the framework (Next.js / Astro / WordPress / static / Gatsby). Deterministic, **read-only, generates no fixes**; deploy-only signals (HTTPS / TLS / status / redirects / compression) are omitted rather than guessed, and on-page/GEO checks need a built static HTML (skipped for un-built SSR projects). Pass `base_url` (your running dev server) to also render-audit the live site under `live_audit` (`max_pages>1` crawls it). The project's source never leaves the machine. |
| `explain_finding(finding_id)` | The **per-finding knowledge lookup**. Given a finding id from a scan (e.g. `geo.aeo`, `schema.missing`, `tech.robots.ai`), returns structured fix knowledge: `name`, `summary`, `category`, `can_astova_generate`, `agent_can_automate`, `human_review_required`, `why_it_matters`, `how_to_fix`, `agent_guidance` (exactly how a coding agent should approach the fix, and what to never automate), `framework_examples`, `verification`, `related_findings`. This is how an agent moves from "Astova found X" to "fix X safely". Also on the HTTP API: `GET /findings` (index) and `GET /findings/{id}`. |
| `generate_fix(finding_id, url?, html?)` | The **per-finding deterministic generator**. Returns a consistent object - `finding_id`, `deterministic` (bool), `supported` (bool), `explanation`, `generated_content` (the exact snippet/file body, or `null`), `target_type` (`head_element` \| `file`), `suggested_location`, `verification_method`. **No LLM, and the fix is NOT applied** - it hands the agent the exact content to paste plus where it goes. Supported today: `schema.missing`, `geo.faq`, `tech.robots.missing`, `tech.robots.ai`, `tech.llms_txt`, `canonical` (alias `onpage.canonical`), `tech.viewport`. Pass `html` for a richer schema fix; `geo.faq` requires `html` with >=2 Q&A pairs. Unsupported findings return `supported: false` with a reason - use `explain_finding` for those. Also on the HTTP API: `POST /findings/{id}/fix`. |
| `verify_fix(target, finding_id, target_type="url")` | The **closing step of the loop** - you applied a change, now confirm it. Re-runs the same scan (`target_type="url"` re-scans a live page; `"project"` re-audits a repo directory) and reports whether that one finding is resolved: `fixed` (bool), `current_status`, `current_severity`, `evidence`, `score_after`, `explanation`, `next_step`. **No LLM, no fix applied, no files touched.** Fixed = the finding is gone from the new scan, or present with status `pass`/`info`; not fixed while `warn`/`fail`. A failed re-scan returns the same shape with an `error`. Works for ANY finding id, not just the fixable seven. Also on the HTTP API: `POST /findings/{id}/verify`. |

### Dev workflow (the "audit my project and fix everything" loop)

With the **local** MCP added to Claude Code / Cursor / Claude Desktop, run your dev server, then ask:

> *"Audit my project at . with base_url http://localhost:3000 and fix the issues."*

The agent calls `audit_project` → gets a standard `Report` of findings straight from your source (plus the rendered page's `Report` under `live_audit`) → calls `explain_finding` / `generate_fix` on the finding ids it wants to fix → **applies the returned content to your source** → calls `verify_fix(target, finding_id, "project")` to deterministically confirm that finding is now resolved (and loops until it is). astova diagnoses, supplies the exact fix content, and verifies the result; your agent edits the files.

## Run

```bash
cd engine
pip install -e ".[mcp]"
python -m astova_engine.mcp_server     # speaks MCP over stdio
```

## Connect a client

Add to the client's MCP config (Claude Desktop: `claude_desktop_config.json`; Claude Code:
`.mcp.json`; ChatGPT desktop: Settings → Connectors → add MCP server):

```json
{
  "mcpServers": {
    "astova": {
      "command": "python",
      "args": ["-m", "astova_engine.mcp_server"]
    }
  }
}
```

Use the absolute path to the venv's Python (e.g. `engine/.venv/bin/python`) if `python` on the
PATH isn't the one with the engine installed.

Then ask the assistant: *"Audit https://example.com/pricing for AI visibility"* — it calls
`audit_url` and reasons over the deterministic scorecard.

## Remote (HTTP) — for claude.ai web/mobile

The engine service also exposes the same tools over **Streamable HTTP**, mounted at **`/mcp/`**
(the `[mcp]` extra is installed in the Docker image). Once the engine is deployed:

    https://<your-engine-host>/mcp/        e.g. https://geosite-eyyg.onrender.com/mcp/

Add it on **claude.ai** → Settings → **Connectors** → *Add custom connector* → paste that URL.
Then in any chat: *"audit stripe.com for AI visibility"* → Claude calls `audit_url`.

Verified handshake:

    curl -X POST https://<host>/mcp/ -H 'content-type: application/json' \
      -H 'accept: application/json, text/event-stream' \
      -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"curl","version":"1"}}}'
    # → 200, serverInfo {"name":"astova"}

> ⚠️ The remote endpoint is **public** — anyone with the URL can run scans against the engine
> (compute cost; and the engine's scan path has no SSRF guard yet). Before promoting it widely,
> add auth (OAuth / a gateway token) and an SSRF guard on the engine fetch. Fine for personal /
> low-traffic use now.

## Notes

- Every number is **VERIFIED** — read straight from the live HTML, reproducible on re-run.
- `audit_url` runs a fast scan (no PageSpeed/render) so it returns in ~1–3s.
- The same scorecard shape powers the web report and the WordPress plugin — one engine, many
  front doors.
