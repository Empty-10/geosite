// damask design tokens (dark-mode-first). See docs/claude-design-brief.md.
// JS-accessible copies for inline/dynamic styling (e.g. the live scan demo).

export const C = {
  ink: "#0D0F12",
  surface: "#16191E",
  raised: "#1C2026",
  border: "#242830",
  borderStrong: "#2E333C",
  text: "#E8EAED",
  text2: "#9BA1A8",
  text3: "#6B7178",
  accent: "#19B36B",
  accentHover: "#15A05F",
  accentWash: "rgba(25,179,107,0.12)",
  measured: "#4D8DF6",
  warn: "#E0A22B",
  fail: "#E5484D",
} as const;

// Status colour for a 0-100 score: green good, amber mid, red poor.
export function scoreColor(v: number): string {
  return v >= 80 ? C.accent : v >= 60 ? C.warn : C.fail;
}
