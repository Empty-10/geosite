// GET /api/scans/:id  →  a saved scan report (for shareable /report?id= links).
// Thin proxy to the engine's /scans/{id}. Requires DAMASK_ENGINE_URL + the engine running with
// DAMASK_DB_PATH (persistence) set — otherwise nothing is saved and ids 404.

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const ENGINE_URL = process.env.DAMASK_ENGINE_URL;
const HTTP_TIMEOUT_MS = 20_000;

function json(body: unknown, status = 200): Response {
  return Response.json(body, { status });
}

export async function GET(_req: Request, ctx: { params: Promise<{ id: string }> }): Promise<Response> {
  if (!ENGINE_URL) return json({ error: "Saved reports aren't available on this deployment." }, 503);
  const { id } = await ctx.params;
  if (!/^\d+$/.test(id)) return json({ error: "Invalid report id." }, 400);

  try {
    const res = await fetch(`${ENGINE_URL.replace(/\/$/, "")}/scans/${id}`, {
      signal: AbortSignal.timeout(HTTP_TIMEOUT_MS),
    });
    if (res.status === 404) return json({ error: "That report no longer exists." }, 404);
    const data = await res.json();
    if (!res.ok) return json({ error: `Engine service error (${res.status}).` }, 502);
    return json(data);
  } catch (e) {
    return json({ error: e instanceof Error ? e.message : "Engine service unreachable." }, 504);
  }
}
