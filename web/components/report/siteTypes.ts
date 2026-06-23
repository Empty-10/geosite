// Types for a multi-page site crawl (engine SiteReport + the crawl job envelope it arrives in).

import type { Finding } from "./types";

export type PageSummary = {
  url: string;
  status_code: number;
  overall_score: number;
  pillar_scores: Record<string, number>;
  title: string;
  meta_description: string;
  word_count: number;
  issues: number;
};

export type SiteReport = {
  schema_version?: string;
  scan_type: "site";
  url: string;
  fetched_at: string;
  overall_score: number;
  meta: Record<string, unknown>;
  pages: PageSummary[];
  site_findings: Finding[];
};

// Envelope returned by GET /api/crawl?id= while a crawl runs and once it finishes.
export type CrawlJob = {
  job_id: string;
  status: "running" | "done" | "error";
  url?: string;
  max_pages?: number;
  progress?: { pages_crawled: number; current?: string };
  result?: SiteReport;
  error?: string;
};
