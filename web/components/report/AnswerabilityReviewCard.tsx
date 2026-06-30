"use client";

// Answerability Review - renders the standard Expert Review contract from scorecard.reviews.answerability:
// Likely AI Quote (headline) + Verdict & Confidence + Consultant Summary + Section Breakdown + Counts.
// Read-only, no extra fetch, theme-safe (var(--*)). Mirrors the SchemaReviewCard pattern.

import { C } from "@/lib/tokens";
import type { ReviewReport, ReviewSection } from "./scorecardTypes";
import type { Report } from "./types";

const VERDICT = {
  strong: { label: "Strong", color: C.accent },
  partial: { label: "Partial", color: C.warn },
  weak: { label: "Weak", color: C.fail },
} as const;

const CONFIDENCE = {
  high: { label: "High", color: C.accent },
  medium: { label: "Medium", color: C.warn },
  low: { label: "Low", color: C.fail },
} as const;

const SECTION_COLOR: Record<string, string> = {
  pass: C.accent, attention: C.warn, fail: C.fail,
};

export function AnswerabilityReviewCard({ report }: { report: Report }) {
  const review = report.scorecard?.reviews?.answerability as ReviewReport | undefined;
  if (!review) return null;

  const v = VERDICT[review.verdict] ?? VERDICT.partial;
  const conf = CONFIDENCE[review.confidence.level] ?? CONFIDENCE.medium;
  const c = review.counts;

  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: 14, background: "var(--surface)", padding: 18, marginBottom: 24 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4, flexWrap: "wrap" }}>
        <h3 style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>Answerability Review</h3>
        <Pill label={v.label} color={v.color} />
        <span title={review.confidence.reasons.join("; ")} style={{ fontSize: 11.5, color: "var(--text-3)" }}>
          Confidence: <span style={{ color: conf.color, fontWeight: 600 }}>{conf.label}</span>
        </span>
      </div>
      <div style={{ fontSize: 12.5, color: "var(--text-3)", marginBottom: 14 }}>
        Could ChatGPT, Claude or Gemini confidently quote this page? {review.confidence.reasons[0] && `(${review.confidence.reasons[0]})`}
      </div>

      {/* Likely AI Quote - the headline */}
      <div style={{ border: `1px solid ${C.accent}`, borderRadius: 10, background: C.accentWash, padding: "12px 14px", marginBottom: 16 }}>
        <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: C.accent, marginBottom: 4 }}>
          Likely AI Quote
        </div>
        {review.likely_ai_quote ? (
          <div style={{ fontSize: 14, color: "var(--text)", lineHeight: 1.5, fontStyle: "italic" }}>
            “{review.likely_ai_quote}”
          </div>
        ) : (
          <div style={{ fontSize: 13, color: "var(--text-2)" }}>
            No extractable answer was found near the top - an AI engine has no clear sentence to quote.
          </div>
        )}
        <div style={{ fontSize: 11, color: "var(--text-3)", marginTop: 5 }}>
          The sentence an AI system is currently most likely to quote.
        </div>
      </div>

      {/* Consultant summary */}
      <ul style={{ listStyle: "none", padding: 0, margin: "0 0 16px", display: "grid", gap: 6 }}>
        {review.summary.map((line, i) => (
          <li key={i} style={{ fontSize: 13, color: "var(--text-2)", lineHeight: 1.5, display: "flex", gap: 8 }}>
            <span style={{ color: C.accent }}>›</span>
            <span>{line}</span>
          </li>
        ))}
      </ul>

      {/* Counts */}
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 14 }}>
        <Stat label="Issues" value={c.issues} color="var(--text)" />
        <Stat label="Critical / high" value={c.critical_high} color={c.critical_high ? C.fail : "var(--text-3)"} />
        <Stat label="AI-assisted" value={c.ai_assisted} color={c.ai_assisted ? C.measured : "var(--text-3)"} />
        <Stat label="Manual review" value={c.manual} color={c.manual ? C.warn : "var(--text-3)"} />
      </div>

      {/* Section breakdown */}
      <div style={{ display: "grid", gap: 6 }}>
        {review.sections.map((s) => <SectionRow key={s.name} s={s} />)}
      </div>
    </div>
  );
}

function Pill({ label, color }: { label: string; color: string }) {
  return (
    <span style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color, border: `1px solid ${color}`, borderRadius: 999, padding: "2px 8px" }}>
      {label}
    </span>
  );
}

function Stat({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: 10, background: "var(--ink)", padding: "8px 12px", minWidth: 96 }}>
      <div style={{ fontSize: 20, fontWeight: 700, color }}>{value}</div>
      <div style={{ fontSize: 11.5, color: "var(--text-2)" }}>{label}</div>
    </div>
  );
}

function SectionRow({ s }: { s: ReviewSection }) {
  const color = SECTION_COLOR[s.status] ?? "var(--text-3)";
  const label = s.status === "pass" ? "OK" : s.status === "attention" ? "Review" : "Fix";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13 }}>
      <span style={{ width: 8, height: 8, borderRadius: "50%", background: color, flexShrink: 0 }} />
      <span style={{ color: "var(--text)" }}>{s.name}</span>
      <span style={{ marginLeft: "auto", fontSize: 11, fontWeight: 600, color }}>{label}</span>
    </div>
  );
}
