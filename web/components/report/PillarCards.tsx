import { scoreColor } from "@/lib/tokens";
import { PILLAR_CARDS } from "./types";

/** The pillar metric cards. Pillars absent from a scan render as "not run yet". */
export function PillarCards({ pillarScores }: { pillarScores: Record<string, number> }) {
  return (
    <div style={{ flex: 1, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
      {PILLAR_CARDS.map(({ label, key }) => {
        const value = pillarScores[key];
        const ran = typeof value === "number";
        return (
          <div
            key={label}
            style={{
              padding: "12px 14px",
              border: "1px solid var(--border)",
              borderRadius: 11,
              background: "var(--ink)",
              display: "flex",
              flexDirection: "column",
              gap: 8,
              opacity: ran ? 1 : 0.6,
            }}
          >
            <span style={{ fontSize: 12, color: "var(--text-2)" }}>{label}</span>
            {ran ? (
              <>
                <span style={{ fontSize: 22, fontWeight: 500, letterSpacing: "-0.01em" }}>{value}</span>
                <div style={{ height: 4, borderRadius: 99, background: "var(--border)", overflow: "hidden" }}>
                  <div style={{ height: "100%", width: `${value}%`, background: scoreColor(value), borderRadius: 99 }} />
                </div>
              </>
            ) : (
              <>
                <span style={{ fontSize: 13, fontWeight: 500, color: "var(--text-3)" }}>Not run yet</span>
                <span style={{ fontSize: 11, color: "var(--text-3)", fontFamily: "var(--mono)" }}>later phase</span>
              </>
            )}
          </div>
        );
      })}
    </div>
  );
}
