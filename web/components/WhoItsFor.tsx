// "Who it's for" — three audience cards with use-case tags (Fuse-style).

const AUDIENCES = [
  {
    icon: "◇",
    title: "SMBs & founders",
    body: "Get found in AI answers without hiring an SEO. One scan, plain-English fixes you can apply today.",
    tags: ["Free scan", "One-click fixes"],
  },
  {
    icon: "◈",
    title: "Agencies",
    body: "White-label audits your clients trust. The verified-vs-measured grammar does the credibility work for you.",
    tags: ["White-label", "Multi-site"],
  },
  {
    icon: "❑",
    title: "Content & SEO teams",
    body: "Make every page extractable and citable — and benchmark against the pages already winning AI answers.",
    tags: ["Benchmarks", "Crawler logs"],
  },
];

export function WhoItsFor() {
  return (
    <section id="agencies" style={{ padding: "80px 32px", borderTop: "1px solid var(--border)", background: "var(--ink)", scrollMarginTop: 72 }}>
      <div style={{ maxWidth: 1100, margin: "0 auto" }}>
        <div style={{ maxWidth: 640, marginBottom: 44 }}>
          <span style={{ fontSize: 13, color: "var(--accent)" }}>Who it&apos;s for</span>
          <h2 style={{ fontSize: 30, fontWeight: 500, letterSpacing: "-0.02em", margin: "12px 0 14px", lineHeight: 1.12 }}>
            Built for everyone fighting for AI visibility.
          </h2>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 16 }}>
          {AUDIENCES.map((a) => (
            <div key={a.title} style={{ padding: 24, border: "1px solid var(--border)", borderRadius: 16, background: "var(--surface)", display: "flex", flexDirection: "column" }}>
              <div style={{ width: 34, height: 34, border: "1px solid var(--border-strong)", borderRadius: 9, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--accent)", fontFamily: "var(--mono)", fontSize: 15, marginBottom: 16 }}>
                {a.icon}
              </div>
              <h3 style={{ fontSize: 17, fontWeight: 500, marginBottom: 8 }}>{a.title}</h3>
              <p style={{ fontSize: 14, color: "var(--text-2)", textWrap: "pretty", lineHeight: 1.5, marginBottom: 16, flex: 1 }}>{a.body}</p>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                {a.tags.map((t) => (
                  <span key={t} style={{ fontSize: 11.5, color: "var(--text-2)", border: "1px solid var(--border)", background: "var(--raised)", padding: "4px 10px", borderRadius: 999 }}>
                    {t}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
