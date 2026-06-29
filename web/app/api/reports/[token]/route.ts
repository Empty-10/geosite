// GET /api/reports/:token  ->  a shared AI Readiness report (report + derived bundle).
// Thin proxy to the engine's /reports/{token}. The token is an unguessable capability id (not an
// enumerable row id). Requires ASTOVA_ENGINE_URL + the engine running with persistence.

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const ENGINE_URL = process.env.ASTOVA_ENGINE_URL;
const HTTP_TIMEOUT_MS = 20_000;

function json(body: unknown, status = 200): Response {
  return Response.json(body, { status });
}

export async function GET(_req: Request, ctx: { params: Promise<{ token: string }> }): Promise<Response> {
  if (!ENGINE_URL) return json({ error: "Saved reports aren't available on this deployment." }, 503);
  const { token } = await ctx.params;
  // Share tokens are URL-safe base64 (secrets.token_urlsafe): letters, digits, - and _.
  if (!/^[A-Za-z0-9_-]{16,64}$/.test(token)) return json({ error: "Invalid report link." }, 400);

  try {
    const res = await fetch(`${ENGINE_URL.replace(/\/$/, "")}/reports/${encodeURIComponent(token)}`, {
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
