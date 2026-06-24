// The scorecard hero: headline AI Retrievability score + category breakdown + the 20-row table
// + the +8 overlay. The legible, deterministic presentation of the whole audit — and the same
// shape the MCP tool and WordPress plugin render. Renders nothing for pre-v6 reports.

import { C, scoreColor } from "@/lib/tokens";
import { rgba } from "./types";
import type { Scorecard, ScorecardRow } from "./scorecardTypes";

export function ScorecardPanel({ scorecard }: { scorecard?: Scorecard | null }) {
  if (!scorecard) return null;
  const { headline_score, technical_score, overlay, categories, rows } = scorecard;
  const hc = scoreColor(headline_score);

  return (
    <div
      style={{
        border: "1px solid var(--border)",
        borderRadius: 16,
        background: "var(--surface)",
        overflow: "hidden",
        marginBottom: 22,
      }}
    >
      {/* headline + categories */}
      <div style={{ display: "flex", gap: 20, padding: "20px 22px", flexWrap: "wrap", alignItems: "center" }}>
        <div style={{ minWidth: 150 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
            <span style={{ fontSize: 12, color: "var(--text-2)" }}>AI Retrievability</span>
            <span
              style={{
                fontSize: 10,
                color: C.accent,
                border: `1px solid ${rgba(C.accent, 0.4)}`,
                background: rgba(C.accent, 0.1),
                padding: "1px 7px",
                borderRadius: 999,
                fontFamily: "var(--mono)",
              }}
            >
              VERIFIED
            </span>
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
            <span style={{ fontSize: 46, fontWeight: 600, letterSpacing: "-0.02em", color: hc, lineHeight: 1 }}>
              {headline_score}
            </span>
            <span style={{ fontSize: 16, color: "var(--text-3)" }}>/100</span>
          </div>
          <div style={{ fontSize: 11.5, color: "var(--text-3)", fontFamily: "var(--mono)", marginTop: 6 }}>
            technical {technical_score} + overlay {overlay.total}
          </div>
        </div>

        <div style={{ flex: 1, minWidth: 240, display: "flex", flexDirection: "column", gap: 7 }}>
          {categories.map((cat) => (
            <div key={cat.label} style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ width: 150, fontSize: 12, color: "var(--text-2)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                {cat.label}
              </span>
              <div style={{ flex: 1, height: 6, borderRadius: 999, background: "var(--raised)", overflow: "hidden" }}>
                <div style={{ width: `${cat.score ?? 0}%`, height: "100%", background: cat.score == null ? "var(--border-strong)" : scoreColor(cat.score) }} />
              </div>
              <span style={{ width: 34, textAlign: "right", fontSize: 12, fontFamily: "var(--mono)", color: "var(--text-3)" }}>
                {cat.score ?? "—"}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* 20-row table */}
      <div style={{ borderTop: "1px solid var(--border)" }}>
        {rows.map((r) => (
          <Row key={r.n} row={r} />
        ))}
      </div>

      {/* overlay */}
      <div
        style={{
          borderTop: "1px solid var(--border)",
          padding: "10px 22px",
          display: "flex",
          gap: 14,
          flexWrap: "wrap",
          alignItems: "center",
          background: "var(--ink)",
        }}
      >
        <span style={{ fontSize: 11.5, color: "var(--text-3)", fontFamily: "var(--mono)" }}>
          overlay +{overlay.total}/{overlay.max}
        </span>
        {overlay.factors.map((f) => (
          <span
            key={f.name}
            style={{
              fontSize: 11,
              color: f.points > 0 ? C.accent : "var(--text-3)",
              fontFamily: "var(--mono)",
            }}
          >
            {f.points > 0 ? "✓" : "·"} {f.name} +{f.points}
          </span>
        ))}
      </div>
    </div>
  );
}

function Row({ row }: { row: ScorecardRow }) {
  const na = row.score == null;
  const color = na ? "var(--text-3)" : scoreColor(row.score!);
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: "8px 22px",
        borderTop: row.n === 1 ? "none" : "1px solid var(--border)",
      }}
    >
      <span style={{ width: 22, fontSize: 11.5, color: "var(--text-3)", fontFamily: "var(--mono)", textAlign: "right" }}>
        {row.n}
      </span>
      <span style={{ flex: 1, fontSize: 13, color: "var(--text)" }}>{row.label}</span>
      <div style={{ width: 90, height: 5, borderRadius: 999, background: "var(--raised)", overflow: "hidden" }}>
        {!na && <div style={{ width: `${row.score}%`, height: "100%", background: color }} />}
      </div>
      <span style={{ width: 38, textAlign: "right", fontSize: 12.5, fontFamily: "var(--mono)", color }}>
        {na ? "n/a" : row.score}
      </span>
    </div>
  );
}
