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

export type Scorecard = {
  confidence: "verified";
  headline_score: number;
  technical_score: number;
  overlay: { total: number; max: number; factors: OverlayFactor[] };
  rows: ScorecardRow[];
  categories: { label: string; score: number | null }[];
  summary?: ScorecardSummary;
  citation?: CitationReadiness;
};
