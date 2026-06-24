"use client";

// Shared on-demand Performance (PageSpeed) state, used by both the report screen and the hero
// demo so the "Run check" card behaves identically and can't drift. PSI gives no real progress,
// so we surface only a real elapsed counter + honest stage labels (never a fake %).

import { useCallback, useEffect, useRef, useState } from "react";
import type { PerfController } from "./PillarCards";
import type { Finding } from "./types";

const PERF_STAGES = [
  "Asking Google to run Lighthouse…",
  "Lighthouse is auditing the page…",
  "Measuring Core Web Vitals…",
  "Parsing results…",
];

type PerfState = {
  phase: "idle" | "loading" | "done" | "error";
  score: number | null;
  findings: Finding[];
  elapsed: number;
  error?: string;
};

export function usePerformance(url: string, preScore?: number, preFindings: Finding[] = []) {
  const [perf, setPerf] = useState<PerfState>(() =>
    typeof preScore === "number"
      ? { phase: "done", score: preScore, findings: preFindings, elapsed: 0 }
      : { phase: "idle", score: null, findings: [], elapsed: 0 },
  );
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const stop = () => {
    if (timer.current) clearInterval(timer.current);
    timer.current = null;
  };
  useEffect(() => stop, []);

  // Reset when the target URL changes (e.g. the hero re-scans a different site).
  useEffect(() => {
    stop();
    setPerf(
      typeof preScore === "number"
        ? { phase: "done", score: preScore, findings: preFindings, elapsed: 0 }
        : { phase: "idle", score: null, findings: [], elapsed: 0 },
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url]);

  const run = useCallback(async () => {
    setPerf((p) => ({ ...p, phase: "loading", elapsed: 0, error: undefined }));
    stop();
    timer.current = setInterval(
      () => setPerf((p) => (p.phase === "loading" ? { ...p, elapsed: p.elapsed + 1 } : p)),
      1000,
    );
    try {
      const res = await fetch("/api/performance", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ url }),
      });
      const data = await res.json();
      stop();
      if (!res.ok || data?.error || typeof data?.score !== "number") {
        setPerf((p) => ({ ...p, phase: "error", error: data?.error || `Performance check failed (${res.status}).` }));
        return;
      }
      setPerf({ phase: "done", score: data.score, findings: (data.findings as Finding[]) ?? [], elapsed: 0 });
    } catch (e) {
      stop();
      setPerf((p) => ({ ...p, phase: "error", error: e instanceof Error ? e.message : "Performance check failed." }));
    }
  }, [url]);

  const done = perf.phase === "done" && typeof perf.score === "number";

  // For PillarCards: a controller while idle/loading/error; undefined once a score exists.
  const controller: PerfController | undefined = done
    ? undefined
    : {
        state: perf.phase === "loading" ? "loading" : perf.phase === "error" ? "error" : "idle",
        elapsed: perf.elapsed,
        label: PERF_STAGES[Math.min(Math.floor(perf.elapsed / 6), PERF_STAGES.length - 1)],
        onRun: run,
      };

  // Merge helpers so callers can fold the result into their pillar scores / findings.
  const pillarOverride: Record<string, number> = done ? { performance: perf.score! } : {};

  return { perf, controller, pillarOverride, findings: perf.findings, run };
}
