"use client";

import { useState } from "react";
import { C } from "@/lib/tokens";
import { pct } from "@/lib/visibility";
import { ToolNav } from "./ToolNav";
import { rgba } from "./types";
import type { CitedSource, EngineRate, Rate, Sentiment, ShareOfVoiceRow, VisibilityReport } from "./visibilityTypes";

type State =
  | { phase: "idle" }
  | { phase: "sampling" }
  | { phase: "error"; message: string }
  | { phase: "done"; report: VisibilityReport };

const M = C.measured; // the MEASURED colour — keeps the probabilistic layer visually distinct

export function VisibilityView() {
  const [brand, setBrand] = useState("");
  const [domain, setDomain] = useState("");
  const [topic, setTopic] = useState("");
  const [prompts, setPrompts] = useState("");
  const [competitors, setCompetitors] = useState("");
  const [suggesting, setSuggesting] = useState(false);
  const [state, setState] = useState<State>({ phase: "idle" });

  const suggest = async () => {
    setSuggesting(true);
    try {
      const res = await fetch("/api/visibility/suggest", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ brand, topic }),
      });
      const data = await res.json();
      if (res.ok && Array.isArray(data.prompts)) setPrompts((p) => (p.trim() ? p + "\n" : "") + data.prompts.join("\n"));
    } finally {
      setSuggesting(false);
    }
  };

  const run = async () => {
    const list = prompts.split("\n").map((s) => s.trim()).filter(Boolean);
    if (!brand.trim() || !domain.trim() || list.length === 0) return;
    setState({ phase: "sampling" });
    try {
      const res = await fetch("/api/visibility", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ brand, domain, prompts: list, competitors: competitors.split(",").map((s) => s.trim()).filter(Boolean) }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.error || `Sampling failed (${res.status}).`);
      setState({ phase: "done", report: data });
    } catch (e) {
      setState({ phase: "error", message: e instanceof Error ? e.message : "Something went wrong." });
    }
  };

  const busy = state.phase === "sampling";

  return (
    <div style={{ minHeight: "100vh", background: "var(--ink)" }}>
      <ToolNav active="visibility" />
      <main style={{ maxWidth: 920, margin: "0 auto", padding: "24px 20px 80px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
          <h1 style={{ fontSize: 22, fontWeight: 500, letterSpacing: "-0.02em" }}>AI visibility</h1>
          <Chip>MEASURED</Chip>
        </div>
        <p style={{ fontSize: 14, color: "var(--text-2)", marginBottom: 20, maxWidth: 680, lineHeight: 1.6 }}>
          Ask real AI engines (Claude, Perplexity, Gemini) questions and measure your{" "}
          <strong style={{ color: "var(--text)" }}>share of voice</strong> — how often you appear vs competitors —
          plus whether your domain gets <em>cited</em>. Sampled on a date, with 95% confidence intervals.
        </p>

        {/* inputs */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 10 }}>
          <Field label="Brand" value={brand} onChange={setBrand} placeholder="Acme Analytics" />
          <Field label="Domain" value={domain} onChange={setDomain} placeholder="acme.com" mono />
        </div>
        <div style={{ display: "flex", gap: 10, marginBottom: 10, alignItems: "flex-end" }}>
          <div style={{ flex: 1 }}>
            <Field label="Topic / category (for suggestions)" value={topic} onChange={setTopic} placeholder="product analytics tools" />
          </div>
          <button onClick={suggest} disabled={suggesting} style={ghostBtn(suggesting)}>
            {suggesting ? "Suggesting…" : "Suggest questions"}
          </button>
        </div>

        <label style={labelStyle}>Questions to sample (one per line, up to 5)</label>
        <textarea
          value={prompts}
          onChange={(e) => setPrompts(e.target.value)}
          placeholder={"What's the best product analytics tool for startups?\nWhich analytics platforms support self-hosting?"}
          spellCheck={false}
          style={{ width: "100%", minHeight: 110, resize: "vertical", padding: "12px 14px", borderRadius: 10, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text)", fontSize: 13.5, lineHeight: 1.5, outline: "none", marginBottom: 10 }}
        />
        <div style={{ marginBottom: 16 }}>
          <Field label="Competitors (comma-separated — for share of voice)" value={competitors} onChange={setCompetitors} placeholder="Mixpanel, Amplitude, PostHog" />
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 26 }}>
          <button onClick={run} disabled={busy} style={primaryBtn(busy)}>
            {busy ? "Sampling AI engines…" : "Measure visibility"}
          </button>
          <span style={{ fontSize: 12, color: "var(--text-3)" }}>Queries each engine live — bounded and rate-limited.</span>
        </div>

        {state.phase === "error" && (
          <div style={{ padding: "18px", border: `1px solid ${rgba(C.fail, 0.4)}`, borderRadius: 12, background: rgba(C.fail, 0.06), color: "var(--text-2)", fontSize: 14 }}>
            <strong style={{ color: "var(--text)" }}>Couldn&apos;t complete sampling.</strong>
            <div style={{ marginTop: 6, color: "var(--text-3)" }}>{state.message}</div>
          </div>
        )}

        {state.phase === "done" && <Results report={state.report} />}
      </main>
    </div>
  );
}

function Results({ report }: { report: VisibilityReport }) {
  const when = new Date(report.sampled_at);
  return (
    <div style={{ animation: "dmFade 0.3s ease both" }}>
      <div style={{ fontSize: 12.5, color: M, fontFamily: "var(--mono)", marginBottom: 16, display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        <Chip>MEASURED</Chip>
        sampled {when.toLocaleString()} · n={report.sample_size} across {report.engines.length} engine
        {report.engines.length !== 1 ? "s" : ""}: {report.engines.join(", ")}
      </div>

      {/* SHARE OF VOICE — headline */}
      {report.share_of_voice.length > 0 && (
        <div style={{ border: `1px solid ${rgba(M, 0.3)}`, borderRadius: 14, background: rgba(M, 0.05), padding: "16px 18px", marginBottom: 16 }}>
          <div style={{ fontSize: 13, color: "var(--text)", fontWeight: 500, marginBottom: 12 }}>Share of voice</div>
          <ShareOfVoice rows={report.share_of_voice} />
        </div>
      )}

      <div style={{ display: "flex", gap: 12, marginBottom: 22, flexWrap: "wrap" }}>
        <RateCard title="Brand visibility" subtitle="answers that named your brand" rate={report.visibility} />
        <RateCard title="Citation rate" subtitle="answers that cited your domain" rate={report.citation} />
        {report.sentiment && report.sentiment.n > 0 && <SentimentCard s={report.sentiment} />}
      </div>

      {report.top_sources.length > 0 && (
        <>
          <SectionTitle>Who gets cited (for these questions)</SectionTitle>
          <div style={{ marginBottom: 22 }}>
            <Sources rows={report.top_sources} />
          </div>
        </>
      )}

      {report.per_engine.length > 1 && (
        <>
          <SectionTitle>By engine</SectionTitle>
          <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 22 }}>
            {report.per_engine.map((e) => (
              <EngineRow key={e.engine} e={e} />
            ))}
          </div>
        </>
      )}

      <SectionTitle>Per-question results</SectionTitle>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {report.prompts.map((p, i) => (
          <div key={i} style={{ border: "1px solid var(--border)", borderRadius: 11, background: "var(--surface)", padding: "12px 14px" }}>
            <div style={{ fontSize: 13.5, color: "var(--text)", marginBottom: 8 }}>{p.prompt}</div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {p.cells.map((c) => (
                <span key={c.engine} style={{ fontSize: 11, color: "var(--text-3)", border: "1px solid var(--border)", borderRadius: 6, padding: "2px 8px", display: "inline-flex", gap: 6, alignItems: "center" }}>
                  {c.engine}
                  <span style={{ color: c.appeared ? M : C.text3 }}>{c.appeared ? "named" : "—"}</span>
                  <span style={{ color: c.cited ? C.accent : C.text3 }}>{c.cited ? "cited" : "·"}</span>
                </span>
              ))}
            </div>
            {p.competitors.length > 0 && <div style={{ fontSize: 11, color: "var(--text-3)", marginTop: 6 }}>vs {p.competitors.join(", ")}</div>}
          </div>
        ))}
      </div>

      <p style={{ fontSize: 11.5, color: "var(--text-3)", marginTop: 18, lineHeight: 1.6 }}>
        Intervals are Wilson 95% bounds on a small sample — directional, not precise. Add more questions/engines for
        tighter bounds. The same engine on another day can differ; that variance is why this is MEASURED, not VERIFIED.
      </p>
    </div>
  );
}

function EngineRow({ e }: { e: EngineRate }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, border: "1px solid var(--border)", borderRadius: 10, background: "var(--surface)", padding: "10px 14px" }}>
      <span style={{ width: 90, fontSize: 13, color: "var(--text)" }}>{e.engine}</span>
      <div style={{ flex: 1, display: "flex", gap: 16 }}>
        <MiniRate label="visible" r={e.visibility} color={M} />
        <MiniRate label="cited" r={e.citation} color={C.accent} />
      </div>
    </div>
  );
}

function MiniRate({ label, r, color }: { label: string; r: Rate; color: string }) {
  return (
    <span style={{ fontSize: 12, color: "var(--text-3)", fontFamily: "var(--mono)" }}>
      {label} <span style={{ color, fontWeight: 600 }}>{pct(r.rate)}%</span> ({r.count}/{r.n})
    </span>
  );
}

function RateCard({ title, subtitle, rate }: { title: string; subtitle: string; rate: Rate }) {
  return (
    <div style={{ flex: 1, minWidth: 240, border: `1px solid ${rgba(M, 0.3)}`, borderRadius: 14, background: rgba(M, 0.05), padding: "16px 18px" }}>
      <div style={{ fontSize: 13, color: "var(--text-2)" }}>{title}</div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 8, margin: "6px 0 2px" }}>
        <span style={{ fontSize: 34, fontWeight: 600, color: M, fontFamily: "var(--mono)" }}>{pct(rate.rate)}%</span>
        <span style={{ fontSize: 13, color: "var(--text-3)", fontFamily: "var(--mono)" }}>{rate.count}/{rate.n}</span>
      </div>
      <div style={{ fontSize: 12, color: "var(--text-3)", fontFamily: "var(--mono)" }}>95% CI {pct(rate.ci[0])}–{pct(rate.ci[1])}%</div>
      <div style={{ position: "relative", height: 5, borderRadius: 999, background: "var(--raised)", marginTop: 10 }}>
        <div style={{ position: "absolute", left: `${pct(rate.ci[0])}%`, width: `${Math.max(2, pct(rate.ci[1]) - pct(rate.ci[0]))}%`, height: "100%", borderRadius: 999, background: rgba(M, 0.55) }} />
        <div style={{ position: "absolute", left: `${pct(rate.rate)}%`, top: -2, width: 2, height: 9, background: M }} />
      </div>
      <div style={{ fontSize: 11, color: "var(--text-3)", marginTop: 8 }}>{subtitle}</div>
    </div>
  );
}

function SentimentCard({ s }: { s: Sentiment }) {
  const seg = [
    { label: "positive", n: s.positive, color: C.accent },
    { label: "neutral", n: s.neutral, color: C.text3 },
    { label: "negative", n: s.negative, color: C.fail },
  ];
  return (
    <div style={{ flex: 1, minWidth: 240, border: `1px solid ${rgba(M, 0.3)}`, borderRadius: 14, background: rgba(M, 0.05), padding: "16px 18px" }}>
      <div style={{ fontSize: 13, color: "var(--text-2)", marginBottom: 8 }}>Sentiment</div>
      <div style={{ display: "flex", height: 10, borderRadius: 999, overflow: "hidden", background: "var(--raised)", marginBottom: 10 }}>
        {seg.map((g) => g.n > 0 && <div key={g.label} style={{ width: `${pct(g.n / s.n)}%`, background: g.color }} />)}
      </div>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", fontSize: 11.5, fontFamily: "var(--mono)" }}>
        {seg.map((g) => (
          <span key={g.label} style={{ color: g.color }}>{g.label} {pct(g.n / s.n)}%</span>
        ))}
      </div>
      <div style={{ fontSize: 11, color: "var(--text-3)", marginTop: 8 }}>how you&apos;re described when named (n={s.n})</div>
    </div>
  );
}

function Sources({ rows }: { rows: CitedSource[] }) {
  const max = Math.max(...rows.map((r) => r.citations), 1);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
      {rows.map((r) => (
        <div key={r.domain} style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ width: 180, fontSize: 12.5, color: r.isYou ? C.accent : "var(--text-2)", fontWeight: r.isYou ? 600 : 400, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
            {r.domain}{r.isYou ? " (you)" : ""}
          </span>
          <div style={{ flex: 1, height: 7, borderRadius: 999, background: "var(--raised)", overflow: "hidden" }}>
            <div style={{ width: `${pct(r.citations / max)}%`, height: "100%", background: r.isYou ? C.accent : "var(--border-strong)" }} />
          </div>
          <span style={{ width: 30, textAlign: "right", fontSize: 12, color: "var(--text-3)", fontFamily: "var(--mono)" }}>{r.citations}</span>
        </div>
      ))}
    </div>
  );
}

function ShareOfVoice({ rows }: { rows: ShareOfVoiceRow[] }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {rows.map((r) => (
        <div key={r.name} style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ width: 130, fontSize: 13, color: r.isTarget ? M : "var(--text-2)", fontWeight: r.isTarget ? 600 : 400, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{r.name}</span>
          <div style={{ flex: 1, height: 10, borderRadius: 999, background: "var(--raised)", overflow: "hidden" }}>
            <div style={{ width: `${pct(r.share)}%`, height: "100%", background: r.isTarget ? M : "var(--border-strong)" }} />
          </div>
          <span style={{ width: 70, textAlign: "right", fontSize: 12.5, color: "var(--text-3)", fontFamily: "var(--mono)" }}>{pct(r.share)}% ({r.mentions})</span>
        </div>
      ))}
    </div>
  );
}

function Chip({ children }: { children: React.ReactNode }) {
  return (
    <span style={{ fontSize: 10.5, letterSpacing: "0.04em", color: M, border: `1px solid ${rgba(M, 0.4)}`, background: rgba(M, 0.1), padding: "2px 8px", borderRadius: 999, fontFamily: "var(--mono)" }}>
      {children}
    </span>
  );
}

function Field({ label, value, onChange, placeholder, mono = false }: { label: string; value: string; onChange: (v: string) => void; placeholder?: string; mono?: boolean }) {
  return (
    <div>
      <label style={labelStyle}>{label}</label>
      <input value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} style={{ width: "100%", height: 42, padding: "0 12px", borderRadius: 9, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text)", fontSize: 14, outline: "none", fontFamily: mono ? "var(--mono)" : "inherit" }} />
    </div>
  );
}

const labelStyle: React.CSSProperties = { display: "block", fontSize: 12, color: "var(--text-3)", marginBottom: 6 };

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <div style={{ fontSize: 13, color: "var(--text)", fontWeight: 500, marginBottom: 10 }}>{children}</div>;
}

function primaryBtn(busy: boolean): React.CSSProperties {
  return { fontSize: 14, fontWeight: 500, border: "none", padding: "0 22px", height: 46, borderRadius: 10, cursor: busy ? "default" : "pointer", background: busy ? "var(--raised)" : M, color: busy ? C.text3 : "#fff" };
}

function ghostBtn(busy: boolean): React.CSSProperties {
  return { fontSize: 13.5, fontWeight: 500, border: "1px solid var(--border-strong)", padding: "0 14px", height: 42, borderRadius: 9, cursor: busy ? "default" : "pointer", background: "transparent", color: "var(--text-2)", whiteSpace: "nowrap", flexShrink: 0 };
}
