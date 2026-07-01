// Types for the 20-row scorecard (engine `report.scorecard`).

export type ScorecardRow = {
  n: number;
  label: string;
  score: number | null;
  status: string; // pass | warn | fail | n/a
  findings: string[];
  impact?: number; // headline points this row would add if brought to full marks
};

export type OverlayFactor = { name: string; points: number; max: number };

export type ScorecardOpportunity = { n: number; text: string; impact: number };

export type ScorecardSummary = {
  band: string; // strong | solid | needs work | at risk
  verdict: string;
  opportunities: ScorecardOpportunity[];
};

export type CitationReadiness = {
  band: string; // well positioned | partially positioned | poorly positioned | unknown
  score: number | null;
  reasons: { n: number; text: string }[];
};

// The standard Expert Review contract (engine: reviews.build_review). Every review renders from this.
export type ReviewConfidence = { level: "high" | "medium" | "low"; reasons: string[] };
export type ReviewSection = { name: string; status: "pass" | "attention" | "fail"; findings: string[] };
export type ReviewReport = {
  review: string;
  key: string;
  verdict: "strong" | "partial" | "weak";
  confidence: ReviewConfidence;
  summary: string[];
  likely_ai_quote: string | null;
  sections: ReviewSection[];
  counts: { issues: number; critical_high: number; deterministic_fixes: number; ai_assisted: number; manual: number };
  related_findings: string[];
};

// The consultant assessment (engine: assessment.build_assessment) - deterministic Implementation
// Programme + Review Comparison + Highest-ROI + programme-aware verdict.
export type ProgrammeFix = { finding_id: string; title: string; severity: string; impact: number };
export type ProgrammePhase = {
  key: string; name: string; objective: string; effort: string; effort_minutes: number;
  improvement: number; fixes_count: number; ai_agent_suitability: number; manual_review: string;
  fixes: ProgrammeFix[];
};
export type ReviewComparison = {
  key: string; name: string; verdict: "strong" | "partial" | "weak"; confidence: string;
  issues: number; critical_high: number; recoverable: number; maturity: number;
};
export type Assessment = {
  headline_score: number | null;
  band: string;
  band_label: string;
  confidence: ReviewConfidence;
  verdict: string[];
  programme: ProgrammePhase[];
  total_recoverable: number;
  total_effort: string;
  reviews: ReviewComparison[];
  highest_roi_review: string | null;
};

export type Scorecard = {
  confidence: "verified";
  headline_score: number;
  technical_score: number;
  overlay: { total: number; max: number; factors: OverlayFactor[] };
  rows: ScorecardRow[];
  categories: { label: string; score: number | null }[];
  summary?: ScorecardSummary;
  citation?: CitationReadiness;
  reviews?: Record<string, ReviewReport>;
  assessment?: Assessment;
};
