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
};
