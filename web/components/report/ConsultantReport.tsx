"use client";

// Consultant report components - pure renderers of the engine's deterministic scorecard.assessment
// (Implementation Programme, Review Comparison, Highest-ROI, programme-aware verdict) + the Expert
// Review contract. No logic, no recomputation, theme-safe (var(--*)). Reused by live/shared/print.

import { useState } from "react";
import { C, scoreColor } from "@/lib/tokens";
import type { Assessment, ProgrammePhase, ReviewComparison } from "./scorecardTypes";
import type { Report } from "./types";

const VERDICT = {
  strong: { label: "Strong", color: C.accent },
  partial: { label: "Partial", color: C.warn },
  weak: { label: "Weak", color: C.fail },
} as const;
const CONF = { high: C.accent, medium: C.warn, low: C.fail } as const;

function getAssessment(report: Report): Assessment | undefined {
  return report.scorecard?.assessment;
}
function stars(n: number) {
  return "★".repeat(Math.max(0, n)) + "☆".repeat(Math.max(0, 5 - n));
}

/* -------------------------------------------------- Executive Assessment (the hero) */

export function ExecutiveAssessment({ report }: { report: Report }) {
  const a = getAssessment(report);
  if (!a) return null;
  const confColor = CONF[a.confidence.level as keyof typeof CONF] ?? C.warn;
  return (
    <div style={{ border: `1px solid ${C.border}`, borderRadius: 16, background: "var(--surface)", padding: "20px 22px", marginBottom: 16 }}>
      <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.05em", textTransform: "uppercase", color: "var(--text-3)", marginBottom: 8 }}>
        How AI Ready is this website?
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 18, flexWrap: "wrap", marginBottom: 12 }}>
        <div style={{ fontSize: 48, fontWeight: 700, lineHeight: 1, color: scoreColor(report.overall_score) }}>
          {report.overall_score}<span style={{ fontSize: 18, color: "var(--text-3)" }}>/100</span>
        </div>
        <span style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase", color: scoreColor(report.overall_score), border: `1px solid ${scoreColor(report.overall_score)}`, borderRadius: 999, padding: "3px 10px" }}>
          {a.band_label}
        </span>
        <span title={a.confidence.reasons.join("; ")} style={{ fontSize: 12.5, color: "var(--text-2)" }}>
          Astova confidence: <span style={{ color: confColor, fontWeight: 600 }}>{a.confidence.level}</span>
        </span>
      </div>
      {a.verdict[0] && (
        <p style={{ fontSize: 15, lineHeight: 1.55, color: "var(--text)", margin: "0 0 14px" }}>{a.verdict[0]}</p>
      )}
      {a.programme.length > 0 && <PhaseStrip programme={a.programme} />}
    </div>
  );
}

function PhaseStrip({ programme }: { programme: ProgrammePhase[] }) {
  return (
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
      {programme.map((p, i) => (
        <div key={p.key} style={{ flex: "1 1 150px", border: `1px solid ${C.border}`, borderRadius: 10, background: "var(--ink)", padding: "10px 12px" }}>
          <div style={{ fontSize: 11, color: "var(--text-3)" }}>Phase {i + 1}</div>
          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text)" }}>{p.name}</div>
          <div style={{ fontSize: 12, color: C.accent, fontWeight: 600 }}>+{p.improvement} · {p.effort}</div>
          <div style={{ fontSize: 11, color: "var(--text-3)" }}>{stars(p.ai_agent_suitability)}</div>
        </div>
      ))}
    </div>
  );
}

/* -------------------------------------------------- Overall Consultant Verdict */

export function ConsultantVerdict({ report }: { report: Report }) {
  const a = getAssessment(report);
  if (!a || a.verdict.length <= 1) return null;
  return (
    <div style={{ borderLeft: `3px solid ${C.accent}`, paddingLeft: 14, margin: "0 0 22px" }}>
      <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.04em", textTransform: "uppercase", color: "var(--text-3)", marginBottom: 6 }}>
        Consultant verdict
      </div>
      {a.verdict.map((line, i) => (
        <p key={i} style={{ fontSize: 14, lineHeight: 1.55, color: "var(--text-2)", margin: "0 0 6px" }}>{line}</p>
      ))}
    </div>
  );
}

/* -------------------------------------------------- Expert Reviews comparison */

export function ExpertReviewsPanel({ report }: { report: Report }) {
  const a = getAssessment(report);
  if (!a || !a.reviews.length) return null;
  const top = a.highest_roi_review;
  const topRev = a.reviews.find((r) => r.key === top);
  return (
    <div style={{ marginBottom: 22 }}>
      <SectionTitle>Expert reviews</SectionTitle>
      {topRev && topRev.recoverable > 0 && (
        <div style={{ border: `1px solid ${C.accent}`, background: C.accentWash, borderRadius: 10, padding: "10px 14px", marginBottom: 12, fontSize: 13, color: "var(--text)" }}>
          <strong>Highest leverage:</strong> the {topRev.name} - +{topRev.recoverable} AI Readiness recoverable.
        </div>
      )}
      <div style={{ display: "grid", gap: 8 }}>
        {a.reviews.map((r) => <ReviewRow key={r.key} r={r} />)}
      </div>
    </div>
  );
}

function ReviewRow({ r }: { r: ReviewComparison }) {
  const v = VERDICT[r.verdict] ?? VERDICT.partial;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", border: `1px solid ${C.border}`, borderRadius: 10, background: "var(--surface)", padding: "10px 14px" }}>
      <span style={{ fontSize: 14, fontWeight: 600, minWidth: 150 }}>{r.name}</span>
      <span style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: v.color, border: `1px solid ${v.color}`, borderRadius: 999, padding: "2px 8px" }}>{v.label}</span>
      <span style={{ fontSize: 12, color: "var(--text-3)" }}>Maturity {r.maturity}%</span>
      <span style={{ fontSize: 12, color: "var(--text-3)" }}>{r.issues} issue(s){r.critical_high ? ` · ${r.critical_high} critical/high` : ""}</span>
      <span style={{ marginLeft: "auto", fontSize: 12.5, fontWeight: 600, color: r.recoverable ? C.accent : "var(--text-3)" }}>+{r.recoverable} recoverable</span>
    </div>
  );
}

/* -------------------------------------------------- Implementation Programme */

export function ImplementationProgramme({ report }: { report: Report }) {
  const a = getAssessment(report);
  if (!a || !a.programme.length) return null;
  return (
    <div style={{ marginBottom: 22 }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 10, flexWrap: "wrap", marginBottom: 4 }}>
        <SectionTitle>Implementation programme - your one-week plan</SectionTitle>
        <span style={{ fontSize: 12.5, color: "var(--text-2)" }}>
          Recover <strong style={{ color: C.accent }}>+{a.total_recoverable}</strong> over ~{a.total_effort}
        </span>
      </div>
      <div style={{ display: "grid", gap: 10 }}>
        {a.programme.map((p, i) => <PhaseCard key={p.key} p={p} n={i + 1} />)}
      </div>
    </div>
  );
}

function PhaseCard({ p, n }: { p: ProgrammePhase; n: number }) {
  return (
    <div style={{ border: `1px solid ${C.border}`, borderRadius: 12, background: "var(--surface)", padding: 16 }}>
      <div style={{ display: "flex", alignItems: "baseline", gap: 10, flexWrap: "wrap", marginBottom: 4 }}>
        <span style={{ fontSize: 12, color: "var(--text-3)" }}>Phase {n}</span>
        <span style={{ fontSize: 15, fontWeight: 600 }}>{p.name}</span>
        <span style={{ marginLeft: "auto", fontSize: 13, fontWeight: 600, color: C.accent }}>+{p.improvement} AI Readiness</span>
      </div>
      <div style={{ fontSize: 12.5, color: "var(--text-2)", lineHeight: 1.5, marginBottom: 8 }}>{p.objective}</div>
      <div style={{ display: "flex", gap: 14, flexWrap: "wrap", fontSize: 12, color: "var(--text-3)", marginBottom: 8 }}>
        <span>Effort: <strong style={{ color: "var(--text-2)" }}>{p.effort}</strong></span>
        <span>{p.fixes_count} fix(es)</span>
        <span>AI-agent: <span style={{ color: C.accent }}>{stars(p.ai_agent_suitability)}</span></span>
        <span>Manual review: <strong style={{ color: "var(--text-2)" }}>{p.manual_review}</strong></span>
      </div>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        {p.fixes.map((f) => (
          <span key={f.finding_id} title={f.title} style={{ fontSize: 11, fontFamily: "var(--mono)", color: "var(--text-2)", border: `1px solid ${C.border}`, borderRadius: 6, padding: "2px 7px" }}>
            {f.finding_id}{f.impact ? ` +${f.impact}` : ""}
          </span>
        ))}
      </div>
    </div>
  );
}

/* -------------------------------------------------- Verification */

export function VerificationPanel({ report }: { report: Report }) {
  if (!getAssessment(report)) return null;
  return (
    <div style={{ border: `1px solid ${C.border}`, borderRadius: 12, background: "var(--surface)", padding: 16, marginBottom: 22 }}>
      <SectionTitle>Verification</SectionTitle>
      <p style={{ fontSize: 13, color: "var(--text-2)", lineHeight: 1.55, margin: 0 }}>
        After your AI agent applies each phase, re-scan the page (or call <code>verify_fix</code> per finding)
        to confirm the score improved. Every finding here is <strong>VERIFIED</strong> - read from the live
        page and reproducible on re-run. Hand your agent the copied action plan to work the programme in order.
      </p>
    </div>
  );
}

/* -------------------------------------------------- Appendix (progressive disclosure) */

export function AppendixSection({ title, children, defaultOpen = false }: { title: string; children: React.ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div style={{ marginBottom: 16 }}>
      <button
        onClick={() => setOpen((v) => !v)}
        style={{ width: "100%", display: "flex", alignItems: "center", gap: 10, padding: "12px 14px", border: `1px solid ${C.border}`, borderRadius: 10, background: "var(--surface)", cursor: "pointer", color: "var(--text)", fontSize: 13, fontWeight: 500, marginBottom: open ? 14 : 0 }}
      >
        <span style={{ flex: 1, textAlign: "left" }}>{title}</span>
        <span style={{ fontSize: 12, color: "var(--text-3)", transform: open ? "rotate(180deg)" : "none", transition: "transform 0.15s ease" }}>⌄</span>
      </button>
      {open && <div>{children}</div>}
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <div style={{ fontSize: 13, color: "var(--text)", fontWeight: 600, marginBottom: 10 }}>{children}</div>;
}
