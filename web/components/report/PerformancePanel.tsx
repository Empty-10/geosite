// "Google Lighthouse" results panel — shows the headline performance score *with* what it means,
// then each Core Web Vital as a list item: value, good/needs-work/poor, and a plain explanation.
// Renders when the on-demand Performance check has produced findings.

import { C, scoreColor } from "@/lib/tokens";
import { rgba, type Finding } from "./types";

// Plain-English meaning for each metric (the engine carries the value; we add the "why").
const META: Record<string, { explain: string }> = {
  "perf.lcp": { explain: "How quickly the main content appears. Good: under 2.5s." },
  "perf.cls": { explain: "How much the layout jumps around while loading. Good: under 0.1." },
  "perf.tbt": { explain: "How long scripts freeze the page before it's usable. Good: under 200ms." },
  "perf.fcp": { explain: "How quickly anything first shows on screen. Good: under 1.8s." },
  "perf.si": { explain: "How quickly the page visually fills in." },
  "perf.field": { explain: "Real Chrome-user experience (field data), not a lab test." },
};

const STATUS: Record<string, { label: string; color: string }> = {
  pass: { label: "Good", color: C.accent },
  warn: { label: "Needs work", color: C.warn },
  fail: { label: "Poor", color: C.fail },
  info: { label: "—", color: C.text3 },
};

export function PerformancePanel({ findings }: { findings: Finding[] }) {
  const score = findings.find((f) => f.id === "perf.score");
  if (!score) return null;
  const value = typeof score.value === "number" ? score.value : 0;
  const metrics = findings.filter((f) => f.id !== "perf.score");
  const sc = scoreColor(value);

  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: 14, background: "var(--surface)", overflow: "hidden", marginBottom: 24 }}>
      {/* header + headline score */}
      <div style={{ display: "flex", gap: 18, alignItems: "center", padding: "16px 18px", flexWrap: "wrap" }}>
        <div style={{ minWidth: 120 }}>
          <div style={{ fontSize: 12.5, color: "var(--text-2)", marginBottom: 4 }}>Google Lighthouse</div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
            <span style={{ fontSize: 40, fontWeight: 600, color: sc, lineHeight: 1 }}>{value}</span>
            <span style={{ fontSize: 14, color: "var(--text-3)" }}>/100</span>
          </div>
        </div>
        <div style={{ flex: 1, minWidth: 220, fontSize: 12.5, color: "var(--text-2)", lineHeight: 1.6 }}>
          Google&apos;s lab speed test (via PageSpeed Insights). The score blends the metrics below.
          <div style={{ marginTop: 6, fontFamily: "var(--mono)", fontSize: 11.5, color: "var(--text-3)" }}>
            <span style={{ color: C.fail }}>0–49 poor</span> · <span style={{ color: C.warn }}>50–89 needs work</span> ·{" "}
            <span style={{ color: C.accent }}>90–100 good</span>
          </div>
        </div>
      </div>

      {/* metric list */}
      <div style={{ borderTop: "1px solid var(--border)" }}>
        {metrics.map((m) => {
          const st = STATUS[m.status] ?? STATUS.info;
          const display = m.evidence || (m.value != null ? String(m.value) : "—");
          return (
            <div key={m.id} style={{ display: "flex", alignItems: "center", gap: 12, padding: "11px 18px", borderTop: "1px solid var(--border)" }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, color: "var(--text)" }}>{m.title}</div>
                <div style={{ fontSize: 11.5, color: "var(--text-3)", marginTop: 1 }}>{META[m.id]?.explain ?? ""}</div>
                {m.status !== "pass" && m.recommendation && (
                  <div style={{ fontSize: 11.5, color: "var(--text-2)", marginTop: 4, lineHeight: 1.45 }}>
                    <span style={{ color: C.accent }}>Fix:</span> {m.recommendation}
                  </div>
                )}
              </div>
              <span style={{ fontSize: 12.5, fontFamily: "var(--mono)", color: "var(--text-2)", whiteSpace: "nowrap" }}>
                {display}
              </span>
              <span
                style={{
                  fontSize: 11,
                  color: st.color,
                  border: `1px solid ${rgba(st.color, 0.35)}`,
                  background: rgba(st.color, 0.1),
                  padding: "1px 8px",
                  borderRadius: 6,
                  width: 78,
                  textAlign: "center",
                  flexShrink: 0,
                }}
              >
                {st.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
