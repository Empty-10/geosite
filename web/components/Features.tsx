const features = [
  {
    icon: "↗",
    title: "Citation attribution",
    body: "See which pages get cited by ChatGPT, Perplexity, AI Overviews and Gemini — and which competitors take your slot.",
  },
  {
    icon: "⊟",
    title: "Crawler logs",
    body: "Verified server-log evidence of GPTBot, ClaudeBot, PerplexityBot and Google-Extended hitting your pages.",
  },
  {
    icon: "⌘",
    title: "Generate fixes",
    body: "Every finding ships with a ready-to-apply fix — schema, llms.txt, content edits — not just a red flag.",
  },
];

export function Features() {
  return (
    <section id="product" style={{ padding: "80px 32px", borderTop: "1px solid var(--border)", scrollMarginTop: 72 }}>
      <div style={{ maxWidth: 1100, margin: "0 auto" }}>
        <div style={{ maxWidth: 620, marginBottom: 44 }}>
          <span style={{ fontSize: 13, color: "var(--accent)" }}>The closed loop</span>
          <h2 style={{ fontSize: 30, fontWeight: 500, letterSpacing: "-0.02em", margin: "12px 0 14px", lineHeight: 1.12 }}>
            See it, prove it, fix it.
          </h2>
          <p style={{ fontSize: 16, color: "var(--text-2)", textWrap: "pretty" }}>
            Most tools stop at a list of problems. damask closes the loop from measurement to remediation.
          </p>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 16 }}>
          {features.map((f) => (
            <div key={f.title} style={{ padding: 24, border: "1px solid var(--border)", borderRadius: 14, background: "var(--surface)" }}>
              <div
                style={{
                  width: 34,
                  height: 34,
                  border: "1px solid var(--border-strong)",
                  borderRadius: 9,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  marginBottom: 18,
                  color: "var(--accent)",
                  fontFamily: "var(--mono)",
                  fontSize: 15,
                }}
              >
                {f.icon}
              </div>
              <h3 style={{ fontSize: 17, fontWeight: 500, marginBottom: 8 }}>{f.title}</h3>
              <p style={{ fontSize: 14, color: "var(--text-2)", textWrap: "pretty" }}>{f.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
