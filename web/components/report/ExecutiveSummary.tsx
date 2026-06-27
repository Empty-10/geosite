"use client";

// The plain-English verdict at the very top of the report — the one thing a brand reads first.
// Pure presentation of the engine's deterministic `scorecard.summary`: a band, a one-paragraph
// verdict, and the top opportunities ranked by headline impact. Renders nothing pre-summary.

import { C } from "@/lib/tokens";
import { rgba } from "./types";
import type { Scorecard } from "./scorecardTypes";

const BAND: Record<string, { label: string; color: string }> = {
  strong: { label: "Strong", color: C.accent },
  solid: { label: "Solid", color: C.measured },
  "needs work": { label: "Needs work", color: C.warn },
  "at risk": { label: "At risk", color: C.fail },
};

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

export function ExecutiveSummary({ scorecard }: { scorecard?: Scorecard | null }) {
  const summary = scorecard?.summary;
  if (!summary) return null;
  const band = BAND[summary.band] ?? BAND.solid;

  return (
    <div
      style={{
        border: `1px solid ${rgba(band.color, 0.4)}`,
        borderRadius: 14,
        background: rgba(band.color, 0.05),
        padding: "18px 20px",
        marginBottom: 18,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
        <span
          style={{
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: "0.04em",
            textTransform: "uppercase",
            color: band.color,
            border: `1px solid ${rgba(band.color, 0.5)}`,
            background: rgba(band.color, 0.12),
            padding: "2px 9px",
            borderRadius: 999,
          }}
        >
          {band.label}
        </span>
        <span style={{ fontSize: 11.5, color: "var(--text-3)" }}>Verdict</span>
      </div>

      <p style={{ fontSize: 15, lineHeight: 1.55, color: "var(--text)", margin: 0 }}>{summary.verdict}</p>

      {summary.opportunities.length > 0 && (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 14 }}>
          {summary.opportunities.map((o) => (
            <span
              key={o.n}
              title="Estimated gain to your readiness score if fixed"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                fontSize: 12,
                color: "var(--text-2)",
                background: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                padding: "5px 10px",
              }}
            >
              {cap(o.text)}
              <span style={{ color: C.accent, fontFamily: "var(--mono)", fontSize: 11.5 }}>+{o.impact}</span>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
