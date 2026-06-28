"use client";

// The hero centrepiece: a looping, canned demo of the product actually working — checks tick
// through, then the score counts up and a mini scorecard + verdict reveal. No network call (it's
// a deterministic loop, not a real scan), so it's instant and never flaky. Honours
// prefers-reduced-motion by showing the finished result statically.

import { useEffect, useRef, useState } from "react";
import { C, scoreColor } from "@/lib/tokens";

const CHECKS = [
  "Crawlability & indexing",
  "Schema & structured data",
  "Up-front answer block",
  "AI crawler access",
  "Front-loaded answer",
  "Citation readiness",
];

const ROWS = [
  { label: "Answer blocks (AEO)", score: 90 },
  { label: "Structured data", score: 80 },
  { label: "AI crawler access", score: 100 },
  { label: "Content depth", score: 64 },
];

const SCORE = 78;
const VERDICT = "Mostly ready for AI answer engines — biggest win: front-load the answer.";

export function HeroScanDemo() {
  const [phase, setPhase] = useState<"scan" | "result">("scan");
  const [ticked, setTicked] = useState(0);
  const [score, setScore] = useState(0);

  useEffect(() => {
    const reduced =
      typeof window !== "undefined" &&
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (reduced) {
      setPhase("result");
      setTicked(CHECKS.length);
      setScore(SCORE);
      return;
    }

    let cancelled = false;
    const timers: ReturnType<typeof setTimeout>[] = [];
    let raf = 0;

    const run = () => {
      setPhase("scan");
      setTicked(0);
      setScore(0);
      CHECKS.forEach((_, i) => {
        timers.push(setTimeout(() => setTicked(i + 1), 300 + i * 360));
      });
      const scanEnd = 300 + CHECKS.length * 360 + 450;
      timers.push(
        setTimeout(() => {
          setPhase("result");
          const start = performance.now();
          const dur = 900;
          const step = (t: number) => {
            if (cancelled) return;
            const p = Math.min(1, (t - start) / dur);
            setScore(Math.round(SCORE * (1 - (1 - p) * (1 - p)))); // easeOut
            if (p < 1) raf = requestAnimationFrame(step);
          };
          raf = requestAnimationFrame(step);
        }, scanEnd),
      );
      timers.push(setTimeout(run, scanEnd + 4400)); // hold the result, then loop
    };

    run();
    return () => {
      cancelled = true;
      timers.forEach(clearTimeout);
      cancelAnimationFrame(raf);
    };
  }, []);

  return (
    <div style={{ minHeight: 300, border: "1px solid var(--border)", borderRadius: 12, background: "var(--ink)", padding: 18 }}>
      {phase === "scan" ? <ScanPhase ticked={ticked} /> : <ResultPhase score={score} />}
    </div>
  );
}

function ScanPhase({ ticked }: { ticked: number }) {
  return (
    <div>
      <div style={{ fontSize: 12.5, color: "var(--text-3)", fontFamily: "var(--mono)", marginBottom: 14 }}>
        scanning stripe.com…
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 9 }}>
        {CHECKS.map((label, i) => {
          const done = i < ticked;
          const running = i === ticked;
          return (
            <div key={label} style={{ display: "flex", alignItems: "center", gap: 11, opacity: i <= ticked ? 1 : 0.4 }}>
              <span
                style={{
                  width: 18,
                  height: 18,
                  borderRadius: "50%",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 10,
                  flexShrink: 0,
                  background: done ? "var(--accent-wash)" : "transparent",
                  border: `1.5px solid ${done ? C.accent : running ? C.measured : "var(--border-strong)"}`,
                  color: C.accent,
                  animation: done ? "dmTick 0.3s ease both" : running ? "dmPulse 1s ease infinite" : undefined,
                }}
              >
                {done ? "✓" : ""}
              </span>
              <span style={{ fontSize: 13.5, color: done ? "var(--text-2)" : running ? "var(--text)" : C.text3 }}>{label}</span>
              <span style={{ marginLeft: "auto", fontSize: 11.5, color: "var(--text-3)", fontFamily: "var(--mono)" }}>
                {done ? "done" : running ? "…" : ""}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ResultPhase({ score }: { score: number }) {
  return (
    <div style={{ animation: "dmFade 0.3s ease both" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 16 }}>
        <Ring score={score} />
        <div>
          <div style={{ fontSize: 11.5, color: "var(--text-3)", marginBottom: 3 }}>AI Retrievability</div>
          <div style={{ fontSize: 14, fontWeight: 500, color: C.warn }}>Solid</div>
          <div style={{ fontSize: 11.5, color: "var(--text-3)", fontFamily: "var(--mono)", marginTop: 3 }}>stripe.com</div>
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 7, marginBottom: 14 }}>
        {ROWS.map((r, i) => (
          <div
            key={r.label}
            style={{ display: "flex", alignItems: "center", gap: 10, animation: "dmRise 0.4s ease both", animationDelay: `${0.1 + i * 0.08}s` }}
          >
            <span style={{ width: 150, fontSize: 12.5, color: "var(--text-2)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{r.label}</span>
            <div style={{ flex: 1, height: 6, borderRadius: 999, background: "var(--raised)", overflow: "hidden" }}>
              <div style={{ width: `${r.score}%`, height: "100%", background: scoreColor(r.score) }} />
            </div>
            <span style={{ width: 28, textAlign: "right", fontSize: 12, fontFamily: "var(--mono)", color: scoreColor(r.score) }}>{r.score}</span>
          </div>
        ))}
      </div>

      <div style={{ fontSize: 12.5, color: "var(--text-2)", lineHeight: 1.5, paddingTop: 12, borderTop: "1px solid var(--border)" }}>
        <span style={{ color: C.accent }}>Verdict · </span>
        {VERDICT}
      </div>
    </div>
  );
}

function Ring({ score }: { score: number }) {
  const r = 32;
  const circ = 2 * Math.PI * r;
  const off = circ * (1 - score / 100);
  const col = scoreColor(score);
  return (
    <svg width="80" height="80" viewBox="0 0 80 80" style={{ flexShrink: 0 }}>
      <circle cx="40" cy="40" r={r} fill="none" stroke="var(--raised)" strokeWidth="6.5" />
      <circle
        cx="40"
        cy="40"
        r={r}
        fill="none"
        stroke={col}
        strokeWidth="6.5"
        strokeLinecap="round"
        strokeDasharray={circ}
        strokeDashoffset={off}
        transform="rotate(-90 40 40)"
      />
      <text x="40" y="46" textAnchor="middle" fontSize="21" fontWeight="600" fill={col} fontFamily="var(--mono)">
        {score}
      </text>
    </svg>
  );
}
