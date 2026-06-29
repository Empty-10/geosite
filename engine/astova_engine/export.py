"""Render an ai_ready_loop result as a compact Markdown action plan.

Pure formatting - takes the loop response dict and returns Markdown a human can paste into Claude,
ChatGPT, Cursor or Windsurf, or an agent can read directly. No scanning, no LLM, no file writes here
(the CLI owns the optional --output write).
"""

from __future__ import annotations

from datetime import datetime, timezone

# knowledge card can_astova_generate -> human phrasing for "Can Astova generate fix".
_CAN_GENERATE = {
    "deterministic": "yes (deterministic)",
    "ai_assisted": "partial (AI-assisted draft)",
    "no": "no (manual)",
}


def _can_generate(item: dict) -> str:
    if (item.get("fix") or {}).get("supported"):
        return "yes (ready now via generate_fix)"
    card = item.get("knowledge") or {}
    return _CAN_GENERATE.get(card.get("can_astova_generate"), "no (manual)")


def _verify_call(verify: dict) -> str:
    return (f'verify_fix("{verify.get("target", "")}", "{verify.get("finding_id", "")}", '
            f'"{verify.get("target_type", "")}")')


def loop_to_markdown(resp: dict, *, generated_at: str | None = None) -> str:
    """Convert an ai_ready_loop response into a compact Markdown action plan."""
    target = resp.get("target", "")

    if resp.get("error"):
        return (
            "# Astova AI Readiness Action Plan\n\n"
            f"Target: {target}\n\n"
            f"Could not generate a plan: {resp['error']}\n"
        )

    ts = generated_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    out: list[str] = [
        "# Astova AI Readiness Action Plan",
        "",
        f"Target: {target}",
        f"Score: {resp.get('score')}/100",
        f"Generated: {ts}",
        "",
        "## Summary",
        "",
        f"* Total actionable findings: {resp.get('actionable_count', 0)}",
        f"* Deterministic fixes: {resp.get('deterministic_fix_count', 0)}",
        f"* AI-assisted fixes: {resp.get('ai_assisted_count', 0)}",
        f"* Manual review items: {resp.get('manual_count', 0)}",
        "",
        "## Top Actions",
        "",
    ]

    items = resp.get("items", [])
    if not items:
        out.append("Nothing to fix - this target looks AI Ready.")
        out.append("")

    for i, it in enumerate(items, 1):
        card = it.get("knowledge") or {}
        out += [
            f"### {i}. {it.get('title', '')}",
            "",
            f"Finding ID: {it.get('finding_id', '')}",
            f"Severity: {it.get('severity', '')}",
            f"Status: {it.get('status', '')}",
            f"Evidence: {it.get('evidence') or 'n/a'}",
            f"Why it matters: {card.get('why_it_matters') or 'n/a'}",
            f"Recommended fix: {it.get('recommendation') or card.get('how_to_fix') or 'n/a'}",
            f"Can Astova generate fix: {_can_generate(it)}",
            f"Agent next step: {it.get('agent_next_step', '')}",
            f"Verification: `{_verify_call(it.get('verify') or {})}`",
            "",
        ]

    out += [
        "Run after fixing:",
        "",
        f"`astova loop {target}`",
        "",
    ]
    return "\n".join(out)
