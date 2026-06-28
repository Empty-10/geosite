// A short, scannable summary high on the page — satisfies the GEO "summary bullets near the
// top" + "extractable structure" factors (AI Overviews and answer engines lift concise lists),
// and gives a human the one-glance version before the longer sections.

const POINTS = [
  "A deterministic AI-readiness score, read straight from your live HTML — verified, not guessed.",
  "Exactly what GPTBot, ClaudeBot and PerplexityBot were served when they crawled you.",
  "Every issue paired with a paste-ready fix — schema, llms.txt, front-loaded rewrites.",
  "An MCP connector so your AI agent applies the fixes and re-audits — not just flags them.",
];

export function SummaryPoints() {
  return (
    <section style={{ padding: "16px 32px 40px" }}>
      <div style={{ maxWidth: 720, margin: "0 auto" }}>
        <div style={{ fontSize: 12, color: "var(--text-3)", letterSpacing: "0.04em", textTransform: "uppercase", marginBottom: 14, textAlign: "center" }}>
          The short version
        </div>
        <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "grid", gap: 12 }}>
          {POINTS.map((p, i) => (
            <li
              key={i}
              style={{
                display: "flex",
                gap: 12,
                alignItems: "flex-start",
                fontSize: 15.5,
                color: "var(--text-2)",
                lineHeight: 1.5,
              }}
            >
              <span style={{ color: "var(--accent)", flexShrink: 0, marginTop: 1, fontSize: 14 }}>✓</span>
              <span style={{ textWrap: "pretty" }}>{p}</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
