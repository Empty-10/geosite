"use client";

// A single word that cycles through a list with a soft fade — used for the rotating AI-engine
// name in the hero headline. Static (first word) under prefers-reduced-motion.

import { useEffect, useState } from "react";

export function RotatingWord({
  words,
  color = "var(--accent)",
  intervalMs = 2400,
}: {
  words: string[];
  color?: string;
  intervalMs?: number;
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
    <span
      style={{
        color,
        fontStyle: "italic",
        display: "inline-block",
        whiteSpace: "nowrap",
        opacity: show ? 1 : 0,
        transform: show ? "translateY(0)" : "translateY(5px)",
        transition: "opacity 0.2s ease, transform 0.2s ease",
      }}
    >
      {words[i]}
    </span>
  );
}
