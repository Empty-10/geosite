import { scoreColor } from "@/lib/tokens";
import { PILLAR_CARDS } from "./types";

// Optional controller for the on-demand Performance card. When provided (report screen), the
// Performance pillar becomes runnable: idle → button, loading → spinner + elapsed + stage label,
// error → retry. Once a score lands in pillarScores it renders normally. Without it (hero demo),
// Performance stays an honest "not run yet".
export type PerfController = {
  state: "idle" | "loading" | "error";
  elapsed: number; // seconds, our own real timer
  label: string; // honest description of the current stage
  message?: string;
  onRun: () => void;
};

/** The pillar metric cards. Pillars absent from a scan render as "not run yet". */
export function PillarCards({ pillarScores, perf }: { pillarScores: Record<string, number>; perf?: PerfController }) {
  return (
    <div style={{ flex: 1, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
      {PILLAR_CARDS.map(({ label, key }, i) => {
        const value = pillarScores[key];
        const ran = typeof value === "number";
        const interactive = key === "performance" && !ran && !!perf;
        const clickable = interactive && perf!.state !== "loading";
        return (
          <div
            key={label}
            onClick={clickable ? perf!.onRun : undefined}
            role={clickable ? "button" : undefined}
            style={{
              padding: "12px 14px",
              border: `1px solid ${interactive ? "var(--border-strong)" : "var(--border)"}`,
              borderRadius: 11,
              background: "var(--ink)",
              display: "flex",
              flexDirection: "column",
              gap: 8,
              opacity: ran || interactive ? 1 : 0.6,
              cursor: clickable ? "pointer" : "default",
              animation: "dmRise 0.5s cubic-bezier(0.22, 1, 0.36, 1) both",
              animationDelay: `${i * 80}ms`,
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
            ) : interactive ? (
              <PerfCardBody perf={perf!} />
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

function PerfCardBody({ perf }: { perf: PerfController }) {
  if (perf.state === "loading") {
    return (
      <>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span
            style={{
              width: 13,
              height: 13,
              borderRadius: "50%",
              border: "1.5px solid var(--border-strong)",
              borderTopColor: "var(--accent)",
              animation: "dmSpin 0.7s linear infinite",
              flexShrink: 0,
            }}
          />
          <span style={{ fontSize: 15, fontWeight: 500, fontFamily: "var(--mono)" }}>{perf.elapsed}s</span>
        </div>
        <span
          style={{
            fontSize: 11,
            color: "var(--text-3)",
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          {perf.label}
        </span>
      </>
    );
  }
  if (perf.state === "error") {
    return (
      <>
        <span style={{ fontSize: 13, fontWeight: 500, color: "var(--fail)" }}>Couldn&apos;t run</span>
        <span style={{ fontSize: 11, color: "var(--accent)", fontFamily: "var(--mono)" }}>Retry →</span>
      </>
    );
  }
  return (
    <>
      <span style={{ fontSize: 13, fontWeight: 500, color: "var(--accent)" }}>Run check →</span>
      <span style={{ fontSize: 11, color: "var(--text-3)", fontFamily: "var(--mono)" }}>PageSpeed · ~10–30s</span>
    </>
  );
}
