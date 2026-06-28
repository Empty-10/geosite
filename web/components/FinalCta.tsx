// Closing CTA — a restrained green-wash panel (not a saturated neon band), on-brand.

export function FinalCta() {
  return (
    <section style={{ padding: "44px 32px 96px", borderTop: "1px solid var(--border)" }}>
      <div style={{ maxWidth: 1100, margin: "0 auto" }}>
        <div
          style={{
            textAlign: "center",
            padding: "56px 32px",
            borderRadius: 20,
            border: "1px solid rgba(25,179,107,0.4)",
            background: "linear-gradient(180deg, var(--accent-wash), transparent)",
          }}
        >
          <h2 style={{ fontSize: 34, fontWeight: 500, letterSpacing: "-0.02em", lineHeight: 1.1, marginBottom: 14, textWrap: "balance" }}>
            Take control of AI search.
          </h2>
          <p style={{ fontSize: 16, color: "var(--text-2)", maxWidth: 540, margin: "0 auto 26px", textWrap: "pretty" }}>
            Run a free, deterministic scan and see exactly how AI engines read your site — and what to fix first.
          </p>
          <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
            <a href="/report" style={{ fontSize: 14, fontWeight: 500, color: "var(--on-accent)", background: "var(--accent)", padding: "12px 22px", borderRadius: 10, textDecoration: "none" }}>
              Start free scan
            </a>
            <a href="/report?url=https://stripe.com" style={{ fontSize: 14, color: "var(--text)", background: "transparent", border: "1px solid var(--border-strong)", padding: "12px 22px", borderRadius: 10, textDecoration: "none" }}>
              See a sample report
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
