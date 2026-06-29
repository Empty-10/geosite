// GET /api/reports/:token  ->  a shared AI Readiness report (report + derived bundle).
// Thin proxy to the engine's /reports/{token} via the shared fetchReportBundle helper. The token is
// an unguessable capability id (not an enumerable row id).

import { fetchReportBundle } from "@/lib/reportData";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(_req: Request, ctx: { params: Promise<{ token: string }> }): Promise<Response> {
  const { token } = await ctx.params;
  const result = await fetchReportBundle(token);
  if (!result.ok) return Response.json({ error: result.error }, { status: result.status });
  return Response.json(result.data);
}
