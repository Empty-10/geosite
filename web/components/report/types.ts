// Shared types + helpers for rendering a damask scan report. Used by both the landing
// HeroDemo and the full /report screen so the two never drift.

import { C } from "@/lib/tokens";

export type Finding = {
  id: string;
  pillar: string;
  title: string;
  status: string;
  severity: string;
  confidence: string;
  value: unknown;
  evidence: string | null;
  recommendation: string | null;
};

export type Report = {
  schema_version?: string;
  url: string;
  fetched_at: string;
  overall_score: number;
  pillar_scores: Record<string, number>;
  meta: Record<string, unknown>;
  findings: Finding[];
};

// severity → badge label + colour + sort rank (lower = more urgent).
export const SEV: Record<string, { label: string; color: string; rank: number }> = {
  critical: { label: "Critical", color: C.fail, rank: 0 },
  high: { label: "High", color: C.fail, rank: 1 },
  medium: { label: "Medium", color: C.warn, rank: 2 },
  low: { label: "Low", color: C.measured, rank: 3 },
  info: { label: "Info", color: C.text3, rank: 4 },
};

// confidence → chip. The accuracy principle made visible: solid green = verified fact.
export const CONF: Record<string, { label: string; color: string }> = {
  verified: { label: "Verified", color: C.accent },
  measured: { label: "Measured", color: C.measured },
  estimated: { label: "Estimated", color: C.warn },
};

// Pillar cards shown on every report. Keys map onto engine pillar_scores; pillars the
// engine doesn't run yet (Performance) render as "not run yet" rather than a faked number.
export const PILLAR_CARDS: { label: string; key: string }[] = [
  { label: "Technical", key: "technical" },
  { label: "On-page", key: "onpage" },
  { label: "GEO readiness", key: "geo" },
  { label: "Performance", key: "performance" },
];

// Pillars that have findings to browse, in tab order (the deterministic first slice).
export const PILLAR_SECTIONS: { label: string; key: string }[] = [
  { label: "Technical", key: "technical" },
  { label: "On-page", key: "onpage" },
  { label: "GEO readiness", key: "geo" },
];

export function rgba(hex: string, a: number): string {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
}

export function sev(s: string) {
  return SEV[s] ?? SEV.info;
}

export function conf(c: string) {
  return CONF[c] ?? CONF.verified;
}

/** Failing/warning findings, most urgent first — the actionable "priority fixes" list. */
export function priorityFixes(findings: Finding[]): Finding[] {
  return findings
    .filter((f) => f.status === "fail" || f.status === "warn")
    .sort((a, b) => sev(a.severity).rank - sev(b.severity).rank);
}
