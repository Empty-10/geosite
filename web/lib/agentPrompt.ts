// Build a ready-to-paste prompt that tells an AI coding agent how to act on an Astova action plan
// SAFELY. Pure - reuses the Markdown plan already returned by /api/ai-ready (which carries the target,
// score, summary and top findings), and wraps it with explicit guardrails. No LLM, no network.

export type PromptPlan = {
  target: string;
  score: number | null;
  actionable_count: number;
  deterministic_fix_count: number;
  ai_assisted_count: number;
  manual_count: number;
  markdown: string;
};

export function buildAgentPrompt(plan: PromptPlan): string {
  return [
    `Use this Astova AI Readiness action plan to make ${plan.target} more AI Ready.`,
    "",
    `Score now: ${plan.score}/100. Actionable findings: ${plan.actionable_count} ` +
      `(${plan.deterministic_fix_count} deterministic fix(es), ${plan.ai_assisted_count} AI-assisted, ` +
      `${plan.manual_count} manual review).`,
    "",
    "How to work through it:",
    "- Apply deterministic fixes exactly as given - they are ready to paste.",
    "- For AI-assisted items, draft only from real, existing page content.",
    "- Do not invent facts, author names, sameAs links, opening hours, addresses, legal claims, " +
      "local-business details or data points.",
    "- For any item marked manual or human review, ask me before editing.",
    "- After you finish, run Astova again (astova loop, or re-run this scan) to verify the score improved.",
    "",
    plan.markdown,
  ].join("\n");
}
