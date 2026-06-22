function Tile({
  name,
  price,
  per,
  note,
  cta,
  primary = false,
  featured = false,
}: {
  name: string;
  price: string;
  per?: string;
  note: string;
  cta: string;
  primary?: boolean;
  featured?: boolean;
}) {
  return (
    <div
      style={{
        padding: 26,
        border: featured ? "1px solid rgba(25,179,107,0.5)" : "1px solid var(--border)",
        borderRadius: 14,
        background: "var(--surface)",
        position: "relative",
      }}
    >
      {featured && (
        <span
          style={{
            position: "absolute",
            top: -10,
            left: 26,
            fontSize: 11,
            color: "var(--ink)",
            background: "var(--accent)",
            padding: "3px 9px",
            borderRadius: 6,
          }}
        >
          Most popular
        </span>
      )}
      <span style={{ fontSize: 14, color: "var(--text-2)" }}>{name}</span>
      <div style={{ display: "flex", alignItems: "baseline", gap: 4, margin: "10px 0 6px" }}>
        <span style={{ fontSize: 32, fontWeight: 500 }}>{price}</span>
        {per && <span style={{ fontSize: 13, color: "var(--text-3)" }}>{per}</span>}
      </div>
      <p style={{ fontSize: 13, color: "var(--text-3)", marginBottom: 20 }}>{note}</p>
      <button
        style={{
          width: "100%",
          fontSize: 14,
          fontWeight: primary ? 500 : 400,
          color: primary ? "var(--ink)" : "var(--text)",
          background: primary ? "var(--accent)" : "transparent",
          border: primary ? "none" : "1px solid var(--border-strong)",
          padding: 10,
          borderRadius: 9,
          cursor: "pointer",
        }}
      >
        {cta}
      </button>
    </div>
  );
}

export function Pricing() {
  return (
    <section style={{ padding: "80px 32px", borderTop: "1px solid var(--border)", background: "var(--ink)" }}>
      <div style={{ maxWidth: 1100, margin: "0 auto" }}>
        <div style={{ textAlign: "center", maxWidth: 560, margin: "0 auto 44px" }}>
          <span style={{ fontSize: 13, color: "var(--accent)" }}>Pricing</span>
          <h2 style={{ fontSize: 30, fontWeight: 500, letterSpacing: "-0.02em", margin: "12px 0 14px", lineHeight: 1.12 }}>
            Start with one free scan.
          </h2>
          <p style={{ fontSize: 16, color: "var(--text-2)" }}>
            No card required. Upgrade when you&apos;re monitoring more than one site.
          </p>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 16, maxWidth: 880, margin: "0 auto" }}>
          <Tile name="Free" price="$0" note="One full scan, one site." cta="Run a scan" />
          <Tile name="Pro" price="$49" per="/mo" note="10 sites, weekly monitoring, fixes." cta="Start free trial" primary featured />
          <Tile name="Agency" price="$199" per="/mo" note="Unlimited sites, white-label reports." cta="Talk to sales" />
        </div>
      </div>
    </section>
  );
}
