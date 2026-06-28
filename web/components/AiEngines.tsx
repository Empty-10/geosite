// Slim trust strip under the hero: the AI answer engines astova checks you against. Text
// wordmarks (no fake customer logos) — honest, and it signals category fit instantly.

const ENGINES = ["ChatGPT", "Perplexity", "Gemini", "Google AI Overviews", "Copilot"];

export function AiEngines() {
  return (
    <section style={{ padding: "4px 32px 40px" }}>
      <div style={{ maxWidth: 1000, margin: "0 auto", textAlign: "center" }}>
        <div style={{ fontSize: 12, color: "var(--text-3)", marginBottom: 18, letterSpacing: "0.02em" }}>
          How your site shows up across the engines people actually ask
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "16px 36px", alignItems: "center" }}>
          {ENGINES.map((e) => (
            <span key={e} style={{ fontSize: 16, fontWeight: 500, color: "var(--text-2)", letterSpacing: "-0.01em", opacity: 0.85 }}>
              {e}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
