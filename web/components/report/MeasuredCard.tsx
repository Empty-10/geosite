import { C } from "@/lib/tokens";
import { rgba } from "./types";

// Preview of the MEASURED citation module (a later phase). Static sample data, clearly
// labelled — NOT a measurement of the scanned site. It exists to show the verified-vs-
// measured visual grammar (a range band, not a solid bar). See CLAUDE.md accuracy principle.
export function MeasuredCard() {
  return (
    <div
      style={{
        padding: "14px 16px",
        border: "1px solid var(--border)",
        borderRadius: 12,
        background: "var(--ink)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
        <span style={{ fontSize: 12.5, color: "var(--text-2)" }}>AI answer-engine visibility</span>
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            fontSize: 11,
            color: C.measured,
            border: `1px solid ${rgba(C.measured, 0.35)}`,
            background: rgba(C.measured, 0.1),
            padding: "3px 9px",
            borderRadius: 999,
          }}
        >
          <span style={{ width: 5, height: 5, borderRadius: "50%", background: C.measured }} />
          Measured · sample
        </span>
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: 10 }}>
        <span style={{ fontSize: 26, fontWeight: 500 }}>23%</span>
        <span style={{ fontSize: 13, color: "var(--text-3)" }}>citation share</span>
      </div>
      <div style={{ position: "relative", height: 8, borderRadius: 99, background: "var(--border)", marginBottom: 8 }}>
        <div
          style={{
            position: "absolute",
            left: "17%",
            width: "12%",
            top: 0,
            bottom: 0,
            background: rgba(C.measured, 0.45),
            borderRadius: 99,
          }}
        />
        <div style={{ position: "absolute", left: "23%", top: -2, width: 2, height: 12, background: C.measured, borderRadius: 2 }} />
      </div>
      <span style={{ fontSize: 11.5, color: "var(--text-3)", fontFamily: "var(--mono)" }}>
        example output · citation sampling arrives in a later phase
      </span>
    </div>
  );
}
