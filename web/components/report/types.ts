// Shared types + helpers for rendering a astova scan report. Used by both the landing
// HeroDemo and the full /report screen so the two never drift.

import { C } from "@/lib/tokens";
import type { Scorecard } from "./scorecardTypes";

// Rough remediation effort per check — lets the report frame fixes by ROI (impact vs effort).
// Quick = a templated/one-line change; Involved = server/infra work; everything else Moderate.
const EFFORT_QUICK = new Set([
  "title.length", "title.missing", "meta.description.length", "meta.description.missing",
  "canonical", "onpage.url", "robots.noindex", "robots.indexable", "tech.x_robots_tag",
  "opengraph", "onpage.snippet_directives", "onpage.hreflang", "onpage.lang", "onpage.form_labels",
  "images.alt", "onpage.images.dims", "schema.jsonld", "schema.missing", "schema.validation",
  "tech.llms_txt", "tech.security_headers", "tech.compression", "tech.resource_hints",
  "tech.viewport", "tech.robots.missing", "tech.robots.ai", "tech.sitemap.missing",
]);
const EFFORT_INVOLVED = new Set([
  "tech.https", "tech.tls", "tech.hsts", "tech.redirect", "tech.redirect.chain",
  "tech.mixed_content", "geo.js_rendered", "perf.score", "perf.lcp", "perf.cls", "perf.tbt",
  "perf.fcp", "perf.si", "perf.field",
]);

export function effortOf(id: string): { label: string; rank: number } {
  if (EFFORT_QUICK.has(id)) return { label: "Quick fix", rank: 0 };
  if (EFFORT_INVOLVED.has(id)) return { label: "Involved", rank: 2 };
  return { label: "Moderate", rank: 1 };
}

/** Map each finding id → the headline points its scorecard row would gain if fully fixed. */
export function impactByFinding(scorecard?: Scorecard | null): Record<string, number> {
  const out: Record<string, number> = {};
  for (const r of scorecard?.rows ?? []) {
    if (r.impact && r.impact > 0) {
      for (const id of r.findings) out[id] = Math.max(out[id] ?? 0, r.impact);
    }
  }
  return out;
}

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

export type Fix = {
  finding_id: string;
  title: string;
  kind: string;
  language: string;
  content: string;
  note: string | null;
  // "deterministic" (engine-generated, ready to apply) vs "ai_drafted" (Claude — review first).
  source?: "deterministic" | "ai_drafted";
};

// Findings whose remediation is judgment-dependent → eligible for on-demand AI drafting
// via POST /api/fix. Everything else has a deterministic fix (or none).
export const GENERATIVE_FINDINGS = new Set([
  "geo.aeo",
  "geo.frontload",
  "geo.definitive",
  "geo.thin_content",
]);

export type Report = {
  schema_version?: string;
  url: string;
  fetched_at: string;
  overall_score: number;
  pillar_scores: Record<string, number>;
  meta: Record<string, unknown>;
  findings: Finding[];
  fixes?: Fix[];
  scorecard?: Scorecard | null;
};

/** Index a report's fixes by the finding they remediate. */
export function fixesByFinding(report: Report): Record<string, Fix> {
  const out: Record<string, Fix> = {};
  for (const f of report.fixes ?? []) out[f.finding_id] = f;
  return out;
}

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

/**
 * Failing/warning findings, ranked for action. When scorecard impact is available we lead with
 * biggest score gain (ROI), falling back to severity; otherwise pure severity order.
 */
export function priorityFixes(findings: Finding[], impacts: Record<string, number> = {}): Finding[] {
  return findings
    .filter((f) => f.status === "fail" || f.status === "warn")
    .sort((a, b) => {
      const di = (impacts[b.id] ?? 0) - (impacts[a.id] ?? 0);
      return di !== 0 ? di : sev(a.severity).rank - sev(b.severity).rank;
    });
}
