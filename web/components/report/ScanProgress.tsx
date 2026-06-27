"use client";

// The "currently scanning" state — module-by-module ticks while the real scan runs. Self-
// contained animation; the parent swaps it for the report once the result arrives. Used by the
// /report scan page (and previously the hero). Performance is shown as "on demand", never faked.

import { useEffect, useState } from "react";
import { C } from "@/lib/tokens";

const MODULES = ["Technical crawl", "On-page structure", "GEO readiness", "Performance", "Schema & metadata", "AI crawler access"];
const PERF_INDEX = 3;

// status: 0 queued · 1 scanning · 2 done · 3 on-demand (Performance)
export function ScanProgress({ url }: { url?: string }) {
  const [status, setStatus] = useState<number[]>(() => MODULES.map((_, i) => (i === PERF_INDEX ? 3 : 0)));

  useEffect(() => {
    const timers: ReturnType<typeof setTimeout>[] = [];
    MODULES.forEach((_, i) => {
      if (i === PERF_INDEX) return;
      timers.push(setTimeout(() => setStatus((s) => set(s, i, 1)), 150 + i * 340));
      timers.push(setTimeout(() => setStatus((s) => set(s, i, 2)), 150 + i * 340 + 300));
    });
    return () => timers.forEach(clearTimeout);
  }, []);

  // Every module (except the on-demand Performance one) has ticked done.
  const allDone = status.every((s, i) => i === PERF_INDEX || s === 2);

  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: 14, background: "var(--surface)", padding: 18 }}>
      <div style={{ fontSize: 13.5, color: "var(--text)", marginBottom: 14, fontFamily: "var(--mono)" }}>
        Scanning {url ? prettyUrl(url) : "…"}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {MODULES.map((name, i) => {
          const st = status[i];
          const running = st === 1;
          const done = st === 2;
          const notRun = st === 3;
          return (
            <div
              key={name}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 12,
                padding: "11px 14px",
                border: "1px solid var(--border)",
                borderRadius: 10,
                background: "var(--raised)",
                opacity: notRun ? 0.55 : 1,
              }}
            >
              <div
                style={{
                  width: 20,
                  height: 20,
                  borderRadius: "50%",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 11,
                  flexShrink: 0,
                  background: done ? rgba(C.accent, 0.14) : "var(--raised)",
                  border: `1.5px solid ${done ? C.accent : running ? C.measured : "var(--border-strong)"}`,
                  color: done ? C.accent : C.text3,
                  animation: running ? "dmPulse 1s ease infinite" : done ? "dmTick 0.3s ease both" : undefined,
                }}
              >
                {done ? "✓" : notRun ? "–" : ""}
              </div>
              <span style={{ flex: 1, fontSize: 14, color: done ? "var(--text-2)" : running ? "var(--text)" : C.text3 }}>{name}</span>
              <span style={{ fontSize: 12, color: "var(--text-3)", fontFamily: "var(--mono)" }}>
                {done ? "done" : running ? "scanning…" : notRun ? "on demand" : "queued"}
              </span>
            </div>
          );
        })}
      </div>
      {allDone && (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12, marginTop: 28, marginBottom: 8, textAlign: "center", animation: "dmFade 0.3s ease both" }}>
          <span style={{ width: 26, height: 26, borderRadius: "50%", border: "2.5px solid var(--border-strong)", borderTopColor: C.accent, animation: "dmSpin 0.75s linear infinite" }} />
          <div style={{ fontSize: 15, color: "var(--text)", fontWeight: 500 }}>Compiling your findings…</div>
          <div style={{ fontSize: 12.5, color: "var(--text-3)", maxWidth: 320 }}>
            This usually takes 20–30 seconds (longer on the first scan after a quiet period).
          </div>
        </div>
      )}
    </div>
  );
}

function set(arr: number[], i: number, v: number): number[] {
  const n = [...arr];
  n[i] = v;
  return n;
}

function rgba(hex: string, a: number): string {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
}

function prettyUrl(u: string): string {
  return u.replace(/^https?:\/\//i, "").replace(/\/$/, "");
}
