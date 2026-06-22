const cardStyle: React.CSSProperties = {
  padding: 22,
  border: "1px solid var(--border)",
  borderRadius: 14,
  background: "var(--surface)",
};

const chipStyle: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 7,
  fontSize: 12,
  padding: "4px 10px",
  borderRadius: 999,
  marginBottom: 18,
};

const bodyStyle: React.CSSProperties = { fontSize: 14, color: "var(--text-2)", textWrap: "pretty" };

export function Confidence() {
  return (
    <section style={{ padding: "80px 32px", borderTop: "1px solid var(--border)", background: "var(--ink)" }}>
      <div style={{ maxWidth: 1100, margin: "0 auto" }}>
        <div style={{ maxWidth: 620, marginBottom: 44 }}>
          <span style={{ fontSize: 13, color: "var(--accent)" }}>The confidence system</span>
          <h2 style={{ fontSize: 30, fontWeight: 500, letterSpacing: "-0.02em", margin: "12px 0 14px", lineHeight: 1.12 }}>
            Verified fact and measured estimate never look the same.
          </h2>
          <p style={{ fontSize: 16, color: "var(--text-2)", textWrap: "pretty" }}>
            Every number carries its provenance. Solid means we verified it deterministically. A band means we sampled
            it. Gray means we inferred it. No other GEO tool draws this line.
          </p>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 16 }}>
          <div style={cardStyle}>
            <span style={{ ...chipStyle, color: "var(--accent)", border: "1px solid rgba(25,179,107,0.35)", background: "var(--accent-wash)" }}>
              <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--accent)" }} />
              Verified
            </span>
            <div style={{ height: 6, borderRadius: 99, background: "var(--border)", marginBottom: 16, overflow: "hidden" }}>
              <div style={{ height: "100%", width: "88%", background: "var(--accent)", borderRadius: 99 }} />
            </div>
            <p style={bodyStyle}>
              Read directly from your site or its response headers. Deterministic, reproducible, solid.
            </p>
          </div>

          <div style={cardStyle}>
            <span style={{ ...chipStyle, color: "var(--measured)", border: "1px solid rgba(77,141,246,0.35)", background: "rgba(77,141,246,0.1)" }}>
              <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--measured)" }} />
              Measured
            </span>
            <div style={{ position: "relative", height: 6, borderRadius: 99, background: "var(--border)", marginBottom: 16 }}>
              <div style={{ position: "absolute", left: "34%", width: "26%", top: 0, bottom: 0, background: "rgba(77,141,246,0.45)", borderRadius: 99 }} />
            </div>
            <p style={bodyStyle}>
              Sampled across real prompts. Shown as a range with its sample size and date — never as false precision.
            </p>
          </div>

          <div style={cardStyle}>
            <span style={{ ...chipStyle, color: "var(--text-2)", border: "1px solid var(--border-strong)", background: "var(--raised)" }}>
              <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--text-3)" }} />
              Estimated
            </span>
            <div style={{ height: 6, borderRadius: 99, background: "var(--border)", marginBottom: 16, overflow: "hidden" }}>
              <div style={{ height: "100%", width: "54%", background: "var(--text-3)", borderRadius: 99, opacity: 0.6 }} />
            </div>
            <p style={bodyStyle}>
              Inferred from related signals when direct measurement isn&apos;t possible. Always labeled as such.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
