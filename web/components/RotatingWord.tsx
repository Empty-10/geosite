"use client";

// A single word that cycles through a list with a soft fade - used for the rotating AI-engine
// name in the hero headline. Static (first word) under prefers-reduced-motion.
//
// All words are stacked in one CSS grid cell, so the box auto-sizes to the WIDEST word and the
// line never reflows as words swap - while staying in normal flow (correct text baseline, unlike
// absolute positioning). The optional suffix (e.g. "?") sits right after the word so it hugs it.

import { useEffect, useState } from "react";

export function RotatingWord({
  words,
  color = "var(--accent)",
  intervalMs = 2400,
  suffix = "",
}: {
  words: string[];
  color?: string;
  intervalMs?: number;
  suffix?: string;
}) {
  const [i, setI] = useState(0);
  const [show, setShow] = useState(true);

  useEffect(() => {
    const reduced =
      typeof window !== "undefined" &&
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (reduced) return;
    const id = setInterval(() => {
      setShow(false);
      setTimeout(() => {
        setI((x) => (x + 1) % words.length);
        setShow(true);
      }, 220);
    }, intervalMs);
    return () => clearInterval(id);
  }, [words.length, intervalMs]);

  return (
    <span style={{ display: "inline-grid", justifyItems: "start", verticalAlign: "baseline" }}>
      {words.map((w, idx) => {
        const active = idx === i;
        return (
          <span
            key={w}
            aria-hidden={!active}
            style={{
              gridColumn: 1,
              gridRow: 1,
              whiteSpace: "nowrap",
              opacity: active && show ? 1 : 0,
              transform: active && show ? "translateY(0)" : "translateY(4px)",
              transition: "opacity 0.2s ease, transform 0.2s ease",
              pointerEvents: "none",
            }}
          >
            <span style={{ color }}>{w}</span>
            {suffix}
          </span>
        );
      })}
    </span>
  );
}
