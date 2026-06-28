// GET /api/scans/:token  →  a saved scan report (for shareable /report?id=<token> links).
// Thin proxy to the engine's /scans/{token}. The path value is an unguessable capability token
// (not an enumerable row id). Requires ASTOVA_ENGINE_URL + the engine running with persistence.

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const ENGINE_URL = process.env.ASTOVA_ENGINE_URL;
const HTTP_TIMEOUT_MS = 20_000;

function json(body: unknown, status = 200): Response {
  return Response.json(body, { status });
}

export async function GET(_req: Request, ctx: { params: Promise<{ id: string }> }): Promise<Response> {
  if (!ENGINE_URL) return json({ error: "Saved reports aren't available on this deployment." }, 503);
  const { id } = await ctx.params;
  // Share tokens are URL-safe base64 (secrets.token_urlsafe): letters, digits, - and _.
  if (!/^[A-Za-z0-9_-]{16,64}$/.test(id)) return json({ error: "Invalid report link." }, 400);

  try {
    const res = await fetch(`${ENGINE_URL.replace(/\/$/, "")}/scans/${encodeURIComponent(id)}`, {
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
