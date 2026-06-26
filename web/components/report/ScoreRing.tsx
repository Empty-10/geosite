"use client";

import { useEffect, useRef, useState } from "react";
import { C, scoreColor } from "@/lib/tokens";

const R = 50;
const CIRC = 2 * Math.PI * R;

/** Circular score gauge. Counts up to `score` once on mount (design brief §6). */
export function ScoreRing({ score, animate = true, label = "Overall GEO score" }: {
  score: number;
  animate?: boolean;
  label?: string;
}) {
  const [shown, setShown] = useState(animate ? 0 : score);
  const raf = useRef<number | null>(null);

  useEffect(() => {
    if (!animate) {
      setShown(score);
      return;
    }
    const start = performance.now();
    const from = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / 650);
      const eased = 1 - Math.pow(1 - t, 3);
      setShown(Math.round(from + (score - from) * eased));
      if (t < 1) raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => {
      if (raf.current) cancelAnimationFrame(raf.current);
    };
  }, [score, animate]);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 6,
        padding: "18px 22px",
        border: "1px solid var(--border)",
        borderRadius: 12,
        background: "var(--ink)",
      }}
    >
      <div style={{ position: "relative", width: 116, height: 116 }}>
        <svg width={116} height={116} viewBox="0 0 116 116" style={{ transform: "rotate(-90deg)" }}>
          <circle cx={58} cy={58} r={R} fill="none" stroke="var(--border)" strokeWidth={9} />
          <circle
            cx={58}
            cy={58}
            r={R}
            fill="none"
            stroke={scoreColor(shown)}
            strokeWidth={9}
            strokeLinecap="round"
            strokeDasharray={CIRC}
            strokeDashoffset={CIRC * (1 - shown / 100)}
          />
        </svg>
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <span style={{ fontSize: 34, fontWeight: 500, letterSpacing: "-0.02em", lineHeight: 1 }}>
            {shown}
          </span>
          <span style={{ fontSize: 11, color: "var(--text-3)" }}>/ 100</span>
        </div>
      </div>
      <span style={{ fontSize: 12.5, color: "var(--text-2)" }}>{label}</span>
    </div>
  );
}
