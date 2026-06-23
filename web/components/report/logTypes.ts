// Types for AI crawler-log analysis (engine LogReport).

import type { Finding } from "./types";

export type BotActivity = {
  name: string;
  operator: string;
  category: "training" | "search" | "user" | string;
  hits: number;
  paths: number;
  errors: number;
  bytes: number;
  last_seen: string | null;
  status_counts: Record<string, number>;
  top_paths: [string, number][];
};

export type LogReport = {
  schema_version?: string;
  scan_type: "logs";
  source: string;
  fetched_at: string;
  meta: {
    lines_total?: number;
    lines_parsed?: number;
    lines_truncated?: number;
    ai_requests?: number;
    date_range?: [string | null, string | null];
  };
  bots: BotActivity[];
  findings: Finding[];
};

// category → label + colour. search/user are the GEO-positive signals (actively fetching to
// answer/cite you); training is corpus-building.
export const CATEGORY: Record<string, { label: string; color: string }> = {
  search: { label: "Answer engine", color: "#19B36B" }, // accent
  user: { label: "User fetch", color: "#4D8DF6" }, // measured
  training: { label: "Training", color: "#6B7178" }, // text-3
};
