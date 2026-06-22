import { HeroDemo } from "./HeroDemo";

export function Hero() {
  return (
    <section
      style={{
        padding: "72px 32px 40px",
        display: "flex",
        justifyContent: "center",
        position: "relative",
        overflow: "hidden",
      }}
    >
      <div className="hero-bg" />
      <div
        style={{
          width: "100%",
          maxWidth: 760,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 40,
          textAlign: "center",
          position: "relative",
          zIndex: 1,
        }}
      >
        <div style={{ maxWidth: 640 }}>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              padding: "5px 12px",
              border: "1px solid var(--border)",
              borderRadius: 999,
              background: "var(--surface)",
              fontSize: 12.5,
              color: "var(--text-2)",
              marginBottom: 24,
            }}
          >
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--accent)" }} />
            GEO reports, backed by a deterministic engine
          </div>
          <h1
            style={{
              fontSize: 46,
              fontWeight: 500,
              letterSpacing: "-0.025em",
              lineHeight: 1.08,
              marginBottom: 20,
              textWrap: "balance",
            }}
          >
            Know exactly how AI engines see your site.
          </h1>
          <p style={{ fontSize: 17, color: "var(--text-2)", maxWidth: 520, margin: "0 auto", textWrap: "pretty" }}>
            damask scans your site and separates verified fact from measured estimate — then tells you what to fix, not
            just what&apos;s wrong.
          </p>
        </div>

        <div style={{ width: "100%" }}>
          <HeroDemo />
        </div>
      </div>
    </section>
  );
}
