export function AgencyCta() {
  return (
    <section id="agencies" style={{ padding: "48px 32px 90px", borderTop: "1px solid var(--border)", scrollMarginTop: 72 }}>
      <div style={{ maxWidth: 1100, margin: "0 auto" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 40,
            padding: 40,
            border: "1px solid var(--border)",
            borderRadius: 18,
            background: "var(--surface)",
            flexWrap: "wrap",
          }}
        >
          <div style={{ maxWidth: 540 }}>
            <span style={{ fontSize: 13, color: "var(--accent)" }}>For agencies</span>
            <h2 style={{ fontSize: 26, fontWeight: 500, letterSpacing: "-0.02em", margin: "12px 0 12px", lineHeight: 1.14 }}>
              Reports your clients will trust — with your logo on them.
            </h2>
            <p style={{ fontSize: 15, color: "var(--text-2)", textWrap: "pretty" }}>
              White-label every report with your brand and accent colour. The honest verified-vs-measured grammar does
              the credibility work for you.
            </p>
          </div>
          <div style={{ display: "flex", gap: 12 }}>
            <a
              href="/#pricing"
              style={{ fontSize: 14, fontWeight: 500, color: "var(--on-accent)", background: "var(--accent)", border: "none", padding: "11px 18px", borderRadius: 9, cursor: "pointer", textDecoration: "none", display: "inline-block" }}
            >
              See plans
            </a>
            <a
              href="/report?url=https://stripe.com"
              style={{ fontSize: 14, color: "var(--text)", background: "transparent", border: "1px solid var(--border-strong)", padding: "11px 18px", borderRadius: 9, cursor: "pointer", textDecoration: "none", display: "inline-block" }}
            >
              See a sample report
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
