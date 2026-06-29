// Server-side fetch of a shared report bundle from the engine. Shared by the /api/reports proxy and
// the print page so the engine call + token validation live in one place (no duplication).

const ENGINE_URL = process.env.ASTOVA_ENGINE_URL;
const TIMEOUT_MS = 20_000;
const TOKEN_RE = /^[A-Za-z0-9_-]{16,64}$/;

export type ReportFinding = {
  finding_id: string; title: string; pillar: string; severity: string;
  status: string; evidence: string | null; recommendation: string | null;
};
export type ReportActionSummary = {
  actionable_count: number; deterministic_fix_count: number; ai_assisted_count: number;
  manual_count: number; deterministic: ReportFinding[]; ai_assisted: ReportFinding[]; manual: ReportFinding[];
};
export type ReportMeta = {
  report_id: number | null; created_at: string | null; scanned_target: string | null;
  engine_version: string | null; ruleset_version: string | null; report_version: string | null;
  share_token: string | null;
};
export type ReportBundle = {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  report: { overall_score: number; pillar_scores: Record<string, number>; scorecard: any; findings: any[] };
  bundle: { metadata: ReportMeta; action_summary: ReportActionSummary; markdown: string; agent_prompt: string };
};

export type FetchResult =
  | { ok: true; data: ReportBundle }
  | { ok: false; status: number; error: string };

export async function fetchReportBundle(token: string): Promise<FetchResult> {
  if (!ENGINE_URL) return { ok: false, status: 503, error: "Saved reports aren't available on this deployment." };
  if (!TOKEN_RE.test(token)) return { ok: false, status: 400, error: "Invalid report link." };
  try {
    const res = await fetch(`${ENGINE_URL.replace(/\/$/, "")}/reports/${encodeURIComponent(token)}`, {
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
    if (res.status === 404) return { ok: false, status: 404, error: "That report no longer exists." };
    const data = (await res.json()) as ReportBundle;
    if (!res.ok) return { ok: false, status: 502, error: `Engine service error (${res.status}).` };
    return { ok: true, data };
  } catch (e) {
    return { ok: false, status: 504, error: e instanceof Error ? e.message : "Engine service unreachable." };
  }
}
