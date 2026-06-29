import { HeroDemo } from "./HeroDemo";
import { RotatingWord } from "./RotatingWord";

const ENGINES = ["ChatGPT", "Claude", "Perplexity", "Gemini", "AI Overviews"];

export function Hero() {
  return (
    <section
      style={{
        padding: "72px 32px 80px",
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
            Verified AI-readiness · fixes, not findings
          </div>
          <h1
            style={{
              fontSize: 46,
              fontWeight: 500,
              letterSpacing: "-0.025em",
              lineHeight: 1.1,
              marginBottom: 20,
              textWrap: "balance",
            }}
          >
            Is your site ready for{" "}
            <RotatingWord words={ENGINES} suffix="?" />
          </h1>
          <p style={{ fontSize: 17, color: "var(--text-2)", maxWidth: 560, margin: "0 auto", textWrap: "pretty" }}>
            Astova reads your pages the way AI answer engines do, scores what&apos;s ready, and gives you the
            exact fixes - or lets your AI agent apply them. Verified from your live HTML, not guessed.
          </p>
        </div>

        <div style={{ width: "100%" }}>
          <HeroDemo />
        </div>
      </div>
    </section>
  );
}
