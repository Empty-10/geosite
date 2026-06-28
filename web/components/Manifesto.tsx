// The thesis statement — a single large, centred line with italic green accent words (Velox-style).
// States the positioning/wedge, distinct from the Confidence section's verified/measured legend.

function I({ children }: { children: React.ReactNode }) {
  return <span style={{ color: "var(--accent)", fontStyle: "italic" }}>{children}</span>;
}

export function Manifesto() {
  return (
    <section style={{ padding: "76px 32px", borderTop: "1px solid var(--border)" }}>
      <div style={{ maxWidth: 780, margin: "0 auto", textAlign: "center" }}>
        <span style={{ fontSize: 13, color: "var(--accent)" }}>Why Astova</span>
        <p
          style={{
            fontSize: 26,
            fontWeight: 500,
            lineHeight: 1.42,
            letterSpacing: "-0.01em",
            marginTop: 16,
            textWrap: "balance",
          }}
        >
          Most AI-search tools just <I>track</I> what&apos;s happening. Astova is built on{" "}
          <I>determinism</I> — it reads your pages the way AI crawlers do, shows you exactly what&apos;s
          wrong, and hands you the <I>fix</I>. Verified, not estimated. <I>Reproducible</I>, not guessed.
        </p>
      </div>
    </section>
  );
}
