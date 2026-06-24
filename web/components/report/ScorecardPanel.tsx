"use client";

// The scorecard hero: headline AI Retrievability score + category breakdown + the 20-row table
// (each row expands to the checks behind it — passes = pros, warn/fail = cons) + the +8 overlay.
// The legible, deterministic presentation of the whole audit — the same shape the MCP tool and
// WordPress plugin render. Renders nothing for pre-v6 reports.

import { useState } from "react";
import { C, scoreColor } from "@/lib/tokens";
import { rgba, type Finding } from "./types";
import type { Scorecard, ScorecardRow } from "./scorecardTypes";

const STATUS: Record<string, { mark: string; color: string }> = {
  pass: { mark: "✓", color: C.accent },
  warn: { mark: "!", color: C.warn },
  fail: { mark: "✕", color: C.fail },
  info: { mark: "·", color: C.text3 },
};

export function ScorecardPanel({ scorecard, findings = [] }: { scorecard?: Scorecard | null; findings?: Finding[] }) {
  const byId = new Map(findings.map((f) => [f.id, f]));
  if (!scorecard) return null;
  const { headline_score, technical_score, overlay, categories, rows } = scorecard;
  const hc = scoreColor(headline_score);

  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: 16, background: "var(--surface)", overflow: "hidden", marginBottom: 22 }}>
      {/* headline + categories */}
      <div style={{ display: "flex", gap: 20, padding: "20px 22px", flexWrap: "wrap", alignItems: "center" }}>
        <div style={{ minWidth: 150 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
            <span style={{ fontSize: 12, color: "var(--text-2)" }}>AI Retrievability</span>
            <span style={{ fontSize: 10, color: C.accent, border: `1px solid ${rgba(C.accent, 0.4)}`, background: rgba(C.accent, 0.1), padding: "1px 7px", borderRadius: 999, fontFamily: "var(--mono)" }}>
              VERIFIED
            </span>
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
            <span style={{ fontSize: 46, fontWeight: 600, letterSpacing: "-0.02em", color: hc, lineHeight: 1 }}>{headline_score}</span>
            <span style={{ fontSize: 16, color: "var(--text-3)" }}>/100</span>
          </div>
          <div style={{ fontSize: 11.5, color: "var(--text-3)", fontFamily: "var(--mono)", marginTop: 6 }}>
            technical {technical_score} + overlay {overlay.total}
          </div>
        </div>

        <div style={{ flex: 1, minWidth: 240, display: "flex", flexDirection: "column", gap: 7 }}>
          {categories.map((cat) => (
            <div key={cat.label} style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ width: 150, fontSize: 12, color: "var(--text-2)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{cat.label}</span>
              <div style={{ flex: 1, height: 6, borderRadius: 999, background: "var(--raised)", overflow: "hidden" }}>
                <div style={{ width: `${cat.score ?? 0}%`, height: "100%", background: cat.score == null ? "var(--border-strong)" : scoreColor(cat.score) }} />
              </div>
              <span style={{ width: 34, textAlign: "right", fontSize: 12, fontFamily: "var(--mono)", color: "var(--text-3)" }}>{cat.score ?? "—"}</span>
            </div>
          ))}
        </div>
      </div>

      {/* 20-row table (expandable) */}
      <div style={{ borderTop: "1px solid var(--border)" }}>
        {rows.map((r) => (
          <Row key={r.n} row={r} byId={byId} />
        ))}
      </div>

      {/* overlay */}
      <div style={{ borderTop: "1px solid var(--border)", padding: "10px 22px", display: "flex", gap: 14, flexWrap: "wrap", alignItems: "center", background: "var(--ink)" }}>
        <span style={{ fontSize: 11.5, color: "var(--text-3)", fontFamily: "var(--mono)" }}>overlay +{overlay.total}/{overlay.max}</span>
        {overlay.factors.map((f) => (
          <span key={f.name} style={{ fontSize: 11, color: f.points > 0 ? C.accent : "var(--text-3)", fontFamily: "var(--mono)" }}>
            {f.points > 0 ? "✓" : "·"} {f.name} +{f.points}
          </span>
        ))}
      </div>
    </div>
  );
}

function Row({ row, byId }: { row: ScorecardRow; byId: Map<string, Finding> }) {
  const [open, setOpen] = useState(false);
  const na = row.score == null;
  const color = na ? "var(--text-3)" : scoreColor(row.score!);
  const checks = row.findings.map((id) => byId.get(id)).filter(Boolean) as Finding[];
  const canExpand = checks.length > 0;

  return (
    <div style={{ borderTop: row.n === 1 ? "none" : "1px solid var(--border)" }}>
      <div
        onClick={canExpand ? () => setOpen(!open) : undefined}
        role={canExpand ? "button" : undefined}
        style={{ display: "flex", alignItems: "center", gap: 12, padding: "8px 22px", cursor: canExpand ? "pointer" : "default" }}
      >
        <span style={{ width: 22, fontSize: 11.5, color: "var(--text-3)", fontFamily: "var(--mono)", textAlign: "right" }}>{row.n}</span>
        <span style={{ flex: 1, fontSize: 13, color: "var(--text)" }}>{row.label}</span>
        <div style={{ width: 90, height: 5, borderRadius: 999, background: "var(--raised)", overflow: "hidden" }}>
          {!na && <div style={{ width: `${row.score}%`, height: "100%", background: color }} />}
        </div>
        <span style={{ width: 38, textAlign: "right", fontSize: 12.5, fontFamily: "var(--mono)", color }}>{na ? "n/a" : row.score}</span>
        <span style={{ width: 12, fontSize: 11, color: "var(--text-3)", transform: open ? "rotate(180deg)" : "none", transition: "transform 0.15s ease", textAlign: "center" }}>
          {canExpand ? "⌄" : ""}
        </span>
      </div>

      {open && (
        <div style={{ padding: "2px 22px 12px 56px", background: "var(--ink)", animation: "dmFade 0.15s ease both" }}>
          {checks.map((f) => {
            const st = STATUS[f.status] ?? STATUS.info;
            const isIssue = f.status === "fail" || f.status === "warn";
            const detail = isIssue ? f.recommendation || f.evidence : f.evidence || f.recommendation;
            return (
              <div key={f.id} style={{ display: "flex", gap: 10, padding: "7px 0", borderTop: "1px solid var(--border)" }}>
                <span style={{ color: st.color, fontSize: 12, width: 14, textAlign: "center", flexShrink: 0, fontWeight: 600 }}>{st.mark}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 12.5, color: "var(--text)" }}>{f.title}</div>
                  {detail && <div style={{ fontSize: 11.5, color: "var(--text-3)", marginTop: 2, lineHeight: 1.5 }}>{detail}</div>}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
