// "How it works" — three numbered steps from URL to fix. Restrained, dark, green accents.

const STEPS = [
  {
    n: "01",
    title: "Scan any URL",
    body: "Paste a page — or your whole site. astova fetches it, renders JavaScript, and reads it the way an AI crawler does.",
  },
  {
    n: "02",
    title: "See what AI sees",
    body: "A deterministic AI Retrievability score, the 20-row scorecard, what GPTBot was actually served, and how you rank against competitors.",
  },
  {
    n: "03",
    title: "Apply the fixes",
    body: "Every issue ships with a paste-ready fix — schema, llms.txt, robots, front-loaded rewrites — or generate one with AI.",
  },
];

export function HowItWorks() {
  return (
    <section style={{ padding: "80px 32px", borderTop: "1px solid var(--border)", background: "var(--ink)" }}>
      <div style={{ maxWidth: 1100, margin: "0 auto" }}>
        <div style={{ maxWidth: 640, marginBottom: 44 }}>
          <span style={{ fontSize: 13, color: "var(--accent)" }}>How it works</span>
          <h2 style={{ fontSize: 30, fontWeight: 500, letterSpacing: "-0.02em", margin: "12px 0 14px", lineHeight: 1.12 }}>
            From URL to fix in three steps.
          </h2>
          <p style={{ fontSize: 16, color: "var(--text-2)", textWrap: "pretty" }}>
            No setup, no crawl budget to configure. Paste a link and read the result.
          </p>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gap: 16 }}>
          {STEPS.map((s) => (
            <div key={s.n} style={{ padding: 24, border: "1px solid var(--border)", borderRadius: 16, background: "var(--surface)" }}>
              <div style={{ fontSize: 28, fontWeight: 600, fontFamily: "var(--mono)", color: "var(--accent)", letterSpacing: "-0.02em", marginBottom: 16 }}>
                {s.n}
              </div>
              <h3 style={{ fontSize: 17, fontWeight: 500, marginBottom: 8 }}>{s.title}</h3>
              <p style={{ fontSize: 14, color: "var(--text-2)", textWrap: "pretty", lineHeight: 1.5 }}>{s.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
