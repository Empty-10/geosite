"use client";

// Deterministic competitor benchmark: your page + up to 3 competitors, scorecards side by side,
// row-by-row leader, and where you lead / trail. Calls /api/compare (engine /compare). No LLM.

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { C, scoreColor } from "@/lib/tokens";
import { ToolNav } from "./ToolNav";
import { rgba } from "./types";
import type { CitationReadiness } from "./scorecardTypes";

type CompareSite = {
  url: string;
  final_url: string;
  error: string | null;
  headline: number | null;
  citation: CitationReadiness | null;
  categories: { label: string; score: number | null }[] | null;
  summary: { band: string; verdict: string } | null;
};
type CompareRow = { n: number; label: string; scores: (number | null)[]; best: number | null; leaders: number[] };
type Comparison = {
  you: number;
  sites: CompareSite[];
  headlines: (number | null)[];
  rows: CompareRow[];
  leads: { n: number; label: string; margin: number }[];
  trails: { n: number; label: string; gap: number }[];
};

type State =
  | { phase: "empty" }
  | { phase: "loading"; n: number }
  | { phase: "error"; message: string }
  | { phase: "done"; data: Comparison };

const MAX = 4;

function hostOf(u: string): string {
  try {
    return new URL(u).hostname.replace(/^www\./, "");
  } catch {
    return u.replace(/^https?:\/\//, "").replace(/^www\./, "").replace(/\/.*$/, "");
  }
}

export function CompareView() {
  const params = useSearchParams();
  const [urls, setUrls] = useState<string[]>(["", ""]);
  const [state, setState] = useState<State>({ phase: "empty" });

  // Prefill the primary slot from ?url= (e.g. arriving from a report's "compare" link).
  useEffect(() => {
    const seed = params.get("url");
    if (seed) setUrls((u) => [seed.replace(/^https?:\/\//i, ""), ...u.slice(1)]);
  }, [params]);

  const setAt = (i: number, v: string) => setUrls((u) => u.map((x, j) => (j === i ? v : x)));
  const addField = () => setUrls((u) => (u.length < MAX ? [...u, ""] : u));
  const removeField = (i: number) => setUrls((u) => (u.length > 2 ? u.filter((_, j) => j !== i) : u));

  const run = async () => {
    const clean = urls.map((u) => u.trim()).filter(Boolean);
    if (clean.length < 2) {
      setState({ phase: "error", message: "Enter at least two URLs — yours and a competitor." });
      return;
    }
    setState({ phase: "loading", n: clean.length });
    try {
      const res = await fetch("/api/compare", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ urls: clean }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.error || `Comparison failed (${res.status}).`);
      setState({ phase: "done", data: data.comparison });
    } catch (e) {
      setState({ phase: "error", message: e instanceof Error ? e.message : "Something went wrong." });
    }
  };

  return (
    <div style={{ minHeight: "100vh", background: "var(--ink)" }}>
      <ToolNav active="compare" />
      <main style={{ maxWidth: 980, margin: "0 auto", padding: "24px 20px 80px" }}>
        <h1 style={{ fontSize: 22, fontWeight: 500, letterSpacing: "-0.02em", marginBottom: 6 }}>
          Competitor benchmark
        </h1>
        <p style={{ fontSize: 13.5, color: "var(--text-3)", marginBottom: 20, maxWidth: 640, lineHeight: 1.55 }}>
          Score your page next to your competitors&apos;, row by row. The first URL is treated as
          yours. Deterministic — every number is read straight from the live pages.
        </p>

        {/* URL inputs */}
        <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 16 }}>
          {urls.map((u, i) => (
            <div key={i} style={{ display: "flex", gap: 10, alignItems: "center" }}>
              <span style={{ width: 78, fontSize: 12, color: i === 0 ? C.accent : "var(--text-3)", fontWeight: i === 0 ? 600 : 400 }}>
                {i === 0 ? "You" : `Competitor ${i}`}
              </span>
              <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 8, padding: "0 14px", height: 44, border: `1px solid ${i === 0 ? rgba(C.accent, 0.4) : "var(--border)"}`, borderRadius: 10, background: "var(--surface)" }}>
                <span style={{ fontSize: 13, color: "var(--text-3)", fontFamily: "var(--mono)" }}>https://</span>
                <input
                  value={u.replace(/^https?:\/\//i, "")}
                  onChange={(e) => setAt(i, e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && run()}
                  placeholder={i === 0 ? "your-site.com" : "competitor.com"}
                  style={{ flex: 1, background: "transparent", border: "none", outline: "none", color: "var(--text)", fontSize: 14, fontFamily: "var(--mono)" }}
                />
              </div>
              {urls.length > 2 && (
                <button onClick={() => removeField(i)} title="Remove" style={{ width: 32, height: 32, borderRadius: 8, border: "1px solid var(--border)", background: "transparent", color: "var(--text-3)", cursor: "pointer", flexShrink: 0 }}>
                  ✕
                </button>
              )}
            </div>
          ))}
        </div>

        <div style={{ display: "flex", gap: 10, marginBottom: 26, flexWrap: "wrap" }}>
          {urls.length < MAX && (
            <button onClick={addField} style={{ fontSize: 13, padding: "9px 16px", borderRadius: 9, border: "1px solid var(--border-strong)", background: "transparent", color: "var(--text-2)", cursor: "pointer" }}>
              + Add competitor
            </button>
          )}
          <button onClick={run} disabled={state.phase === "loading"} style={{ fontSize: 14, fontWeight: 500, border: "none", padding: "9px 22px", borderRadius: 9, cursor: state.phase === "loading" ? "default" : "pointer", background: state.phase === "loading" ? "var(--raised)" : C.accent, color: state.phase === "loading" ? C.text3 : C.ink }}>
            {state.phase === "loading" ? "Comparing…" : "Compare"}
          </button>
        </div>

        {state.phase === "loading" && (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12, padding: "40px 0" }}>
            <span style={{ width: 26, height: 26, borderRadius: "50%", border: "2.5px solid var(--border-strong)", borderTopColor: C.accent, animation: "dmSpin 0.75s linear infinite" }} />
            <div style={{ fontSize: 14, color: "var(--text)" }}>Scanning {state.n} sites and comparing…</div>
            <div style={{ fontSize: 12, color: "var(--text-3)" }}>This usually takes 20–30 seconds.</div>
          </div>
        )}

        {state.phase === "error" && (
          <div style={{ padding: "16px 18px", border: `1px solid ${rgba(C.fail, 0.4)}`, borderRadius: 12, background: rgba(C.fail, 0.06), color: "var(--text-2)", fontSize: 14 }}>
            {state.message}
          </div>
        )}

        {state.phase === "done" && <Results data={state.data} />}
      </main>
    </div>
  );
}

function Results({ data }: { data: Comparison }) {
  const { sites, rows, leads, trails, you } = data;
  const n = sites.length;

  return (
    <div style={{ animation: "dmFade 0.3s ease both" }}>
      {/* site header cards */}
      <div style={{ display: "grid", gridTemplateColumns: `repeat(${n}, minmax(0, 1fr))`, gap: 12, marginBottom: 22 }}>
        {sites.map((s, i) => {
          const isYou = i === you;
          return (
            <div key={i} style={{ border: `1px solid ${isYou ? rgba(C.accent, 0.45) : "var(--border)"}`, borderRadius: 12, background: isYou ? rgba(C.accent, 0.05) : "var(--surface)", padding: "14px 16px" }}>
              <div style={{ fontSize: 11, color: isYou ? C.accent : "var(--text-3)", fontWeight: 600, marginBottom: 4 }}>
                {isYou ? "You" : `Competitor ${i}`}
              </div>
              <div style={{ fontSize: 13, color: "var(--text)", fontFamily: "var(--mono)", marginBottom: 10, wordBreak: "break-all" }}>{hostOf(s.final_url)}</div>
              {s.error ? (
                <div style={{ fontSize: 12, color: C.fail }}>Couldn&apos;t scan this site.</div>
              ) : (
                <>
                  <div style={{ display: "flex", alignItems: "baseline", gap: 5 }}>
                    <span style={{ fontSize: 34, fontWeight: 600, letterSpacing: "-0.02em", color: scoreColor(s.headline ?? 0), lineHeight: 1 }}>{s.headline ?? "—"}</span>
                    <span style={{ fontSize: 13, color: "var(--text-3)" }}>/100</span>
                  </div>
                  {s.citation?.band && s.citation.band !== "unknown" && (
                    <div style={{ fontSize: 11.5, color: "var(--text-3)", marginTop: 6 }}>
                      {s.citation.band} to be cited
                    </div>
                  )}
                </>
              )}
            </div>
          );
        })}
      </div>

      {/* where you lead / trail */}
      {(leads.length > 0 || trails.length > 0) && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 12, marginBottom: 24 }}>
          <GapCard title="Where you lead" empty="No rows where you're ahead." color={C.accent} items={leads.map((l) => ({ label: l.label, delta: `+${l.margin}` }))} />
          <GapCard title="Where competitors beat you" empty="Nothing — you lead or tie everywhere." color={C.fail} items={trails.map((t) => ({ label: t.label, delta: `-${t.gap}` }))} />
        </div>
      )}

      {/* full row-by-row matrix */}
      <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 10 }}>Row-by-row breakdown</div>
      <div style={{ border: "1px solid var(--border)", borderRadius: 12, overflow: "hidden" }}>
        {/* header */}
        <div style={{ display: "grid", gridTemplateColumns: `minmax(0,1fr) repeat(${n}, 70px)`, alignItems: "center", padding: "9px 14px", background: "var(--surface)", borderBottom: "1px solid var(--border)" }}>
          <span style={{ fontSize: 11.5, color: "var(--text-3)" }}>Check</span>
          {sites.map((s, i) => (
            <span key={i} style={{ fontSize: 11, color: i === you ? C.accent : "var(--text-3)", textAlign: "center", fontWeight: i === you ? 600 : 400, fontFamily: "var(--mono)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {i === you ? "You" : hostOf(s.final_url).slice(0, 8)}
            </span>
          ))}
        </div>
        {rows.map((r) => (
          <div key={r.n} style={{ display: "grid", gridTemplateColumns: `minmax(0,1fr) repeat(${n}, 70px)`, alignItems: "center", padding: "8px 14px", borderTop: "1px solid var(--border)" }}>
            <span style={{ fontSize: 12.5, color: "var(--text)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", paddingRight: 8 }}>
              <span style={{ color: "var(--text-3)", fontFamily: "var(--mono)", marginRight: 7 }}>{r.n}</span>{r.label}
            </span>
            {r.scores.map((sc, i) => {
              const isLeader = r.leaders.includes(i) && r.leaders.length < n; // not a tie-for-all
              return (
                <span key={i} style={{ textAlign: "center" }}>
                  <span style={{ display: "inline-block", minWidth: 34, fontSize: 12.5, fontFamily: "var(--mono)", color: sc == null ? "var(--text-3)" : scoreColor(sc), padding: "2px 6px", borderRadius: 6, background: isLeader ? rgba(C.accent, 0.14) : "transparent", fontWeight: isLeader ? 600 : 400 }}>
                    {sc == null ? "—" : sc}
                  </span>
                </span>
              );
            })}
          </div>
        ))}
      </div>
      <div style={{ fontSize: 11.5, color: "var(--text-3)", marginTop: 10 }}>
        Highlighted cell = the leader for that check. Every score is VERIFIED — read straight from the live page.
      </div>
    </div>
  );
}

function GapCard({ title, items, empty, color }: { title: string; items: { label: string; delta: string }[]; empty: string; color: string }) {
  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: 12, background: "var(--surface)", padding: "14px 16px" }}>
      <div style={{ fontSize: 12.5, fontWeight: 500, color: "var(--text)", marginBottom: 10 }}>{title}</div>
      {items.length === 0 ? (
        <div style={{ fontSize: 12.5, color: "var(--text-3)" }}>{empty}</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
          {items.slice(0, 6).map((it) => (
            <div key={it.label} style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ flex: 1, fontSize: 12.5, color: "var(--text-2)" }}>{it.label}</span>
              <span style={{ fontSize: 11.5, fontFamily: "var(--mono)", color }}>{it.delta}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
