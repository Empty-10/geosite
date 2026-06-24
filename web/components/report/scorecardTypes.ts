// Types for the 20-row scorecard (engine `report.scorecard`).

export type ScorecardRow = {
  n: number;
  label: string;
  score: number | null;
  status: string; // pass | warn | fail | n/a
  findings: string[];
};

export type OverlayFactor = { name: string; points: number; max: number };

export type Scorecard = {
  confidence: "verified";
  headline_score: number;
  technical_score: number;
  overlay: { total: number; max: number; factors: OverlayFactor[] };
  rows: ScorecardRow[];
  categories: { label: string; score: number | null }[];
};
