import { C, scoreColor } from "@/lib/tokens";

const tile: React.CSSProperties = {
  padding: 22,
  border: "1px solid var(--border)",
  borderRadius: 16,
  background: "var(--surface)",
  display: "flex",
  flexDirection: "column",
  gap: 12,
};

const iconChip: React.CSSProperties = {
  width: 34,
  height: 34,
  border: "1px solid var(--border-strong)",
  borderRadius: 9,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  color: "var(--accent)",
  fontFamily: "var(--mono)",
  fontSize: 15,
  flexShrink: 0,
};

function Head({ icon, title, body }: { icon: string; title: string; body: string }) {
  return (
    <>
      <div style={iconChip}>{icon}</div>
      <h3 style={{ fontSize: 16.5, fontWeight: 500 }}>{title}</h3>
      <p style={{ fontSize: 13.5, color: "var(--text-2)", textWrap: "pretty", lineHeight: 1.5 }}>{body}</p>
    </>
  );
}

// Mini scorecard preview for the big tile.
function MiniScorecard() {
  const rows = [
    { label: "Answer blocks (AEO)", score: 90 },
    { label: "Structured data", score: 80 },
    { label: "Content depth", score: 64 },
  ];
  return (
    <div style={{ marginTop: "auto", border: "1px solid var(--border)", borderRadius: 10, background: "var(--ink)", padding: 12 }}>
      <div style={{ display: "flex", alignItems: "baseline", gap: 6, marginBottom: 10 }}>
        <span style={{ fontSize: 22, fontWeight: 600, color: scoreColor(78), fontFamily: "var(--mono)" }}>78</span>
        <span style={{ fontSize: 11.5, color: "var(--text-3)" }}>AI Retrievability</span>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
        {rows.map((r) => (
          <div key={r.label} style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ flex: 1, fontSize: 11.5, color: "var(--text-3)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{r.label}</span>
            <div style={{ width: 70, height: 5, borderRadius: 999, background: "var(--raised)", overflow: "hidden" }}>
              <div style={{ width: `${r.score}%`, height: "100%", background: scoreColor(r.score) }} />
            </div>
            <span style={{ width: 22, textAlign: "right", fontSize: 11, fontFamily: "var(--mono)", color: scoreColor(r.score) }}>{r.score}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// "What the AI bot saw" status preview.
function MiniBotView() {
  const Line = ({ ok, text }: { ok: boolean; text: string }) => (
    <div style={{ display: "flex", alignItems: "center", gap: 9, fontSize: 12, color: "var(--text-2)" }}>
      <span style={{ width: 16, height: 16, borderRadius: "50%", flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 9, color: ok ? C.accent : C.warn, background: ok ? "var(--accent-wash)" : "rgba(224,162,43,0.12)", border: `1px solid ${ok ? C.accent : C.warn}` }}>
        {ok ? "✓" : "!"}
      </span>
      {text}
    </div>
  );
  return (
    <div style={{ marginTop: "auto", border: "1px solid var(--border)", borderRadius: 10, background: "var(--ink)", padding: 12, display: "flex", flexDirection: "column", gap: 9 }}>
      <Line ok text="Fetched as GPTBot — HTTP 200, readable" />
      <Line ok text="JS-only content — 0% (bot sees everything)" />
      <Line ok={false} text="Front-loaded answer — buried at ~280 words" />
    </div>
  );
}

// Competitor mini-bars.
function MiniCompare() {
  const rows = [
    { label: "you", score: 78 },
    { label: "rival-a", score: 64 },
    { label: "rival-b", score: 71 },
  ];
  return (
    <div style={{ marginTop: "auto", display: "flex", flexDirection: "column", gap: 7 }}>
      {rows.map((r) => (
        <div key={r.label} style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ width: 48, fontSize: 11, fontFamily: "var(--mono)", color: r.label === "you" ? C.accent : "var(--text-3)" }}>{r.label}</span>
          <div style={{ flex: 1, height: 5, borderRadius: 999, background: "var(--raised)", overflow: "hidden" }}>
            <div style={{ width: `${r.score}%`, height: "100%", background: scoreColor(r.score) }} />
          </div>
          <span style={{ width: 20, textAlign: "right", fontSize: 11, fontFamily: "var(--mono)", color: scoreColor(r.score) }}>{r.score}</span>
        </div>
      ))}
    </div>
  );
}

export function Features() {
  return (
    <section id="product" style={{ padding: "80px 32px", borderTop: "1px solid var(--border)", scrollMarginTop: 72 }}>
      <div style={{ maxWidth: 1100, margin: "0 auto" }}>
        <div style={{ maxWidth: 640, marginBottom: 44 }}>
          <span style={{ fontSize: 13, color: "var(--accent)" }}>What it does</span>
          <h2 style={{ fontSize: 30, fontWeight: 500, letterSpacing: "-0.02em", margin: "12px 0 14px", lineHeight: 1.12 }}>
            See it, prove it, fix it — across every AI engine.
          </h2>
          <p style={{ fontSize: 16, color: "var(--text-2)", textWrap: "pretty" }}>
            One deterministic engine, six ways to know exactly where you stand — and what to change.
          </p>
        </div>

        <div className="bento">
          <div className={"b3"} style={tile}>
            <Head icon="◆" title="AI Retrievability scorecard" body="A 20-row deterministic audit with a single headline score — every check read straight from your live HTML, reproducible on re-run." />
            <MiniScorecard />
          </div>

          <div className={"b3"} style={tile}>
            <Head icon="◉" title="What the AI bot saw" body="We fetch your page as GPTBot and compare — catching WAF/CDN blocks, cloaking and JS-only content that hide you from AI crawlers." />
            <MiniBotView />
          </div>

          <div className={"b2"} style={tile}>
            <Head icon="⊟" title="Crawler-log analytics" body="Verified server-log evidence of GPTBot, ClaudeBot, PerplexityBot and Google-Extended actually hitting your pages — and what errored." />
          </div>

          <div className={"b2"} style={tile}>
            <Head icon="⇄" title="Competitor benchmark" body="Score your page next to rivals, row by row — see exactly where you lead and where they beat you." />
            <MiniCompare />
          </div>

          <div className={"b2"} style={tile}>
            <Head icon="⌘" title="Fixes, not findings" body="Every issue ships with a ready-to-apply fix — schema, llms.txt, robots, front-loaded rewrites — deterministic or AI-drafted." />
          </div>
        </div>
      </div>
    </section>
  );
}
