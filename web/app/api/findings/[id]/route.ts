// GET /api/findings/:id  ->  structured fix knowledge for one finding (e.g. geo.aeo, schema.missing):
// why it matters for AI engines, how to fix it, and how an AI coding agent should approach it.
// Thin proxy to the engine's /findings/{id}.
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const ENGINE_URL = process.env.ASTOVA_ENGINE_URL;
const TIMEOUT_MS = 15_000;

export async function GET(
  _req: Request,
  ctx: { params: Promise<{ id: string }> },
): Promise<Response> {
  if (!ENGINE_URL) {
    return Response.json({ error: "Finding knowledge isn't available on this deployment." }, { status: 503 });
  }
  const { id } = await ctx.params;
  // finding ids are dotted lowercase tokens, e.g. geo.aeo, tech.robots.ai, onpage.heading_order
  if (!/^[a-z][a-z0-9_.]{1,60}$/.test(id)) {
    return Response.json({ error: "Invalid finding id." }, { status: 400 });
  }
  try {
    const res = await fetch(`${ENGINE_URL.replace(/\/$/, "")}/findings/${encodeURIComponent(id)}`, {
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
    if (res.status === 404) return Response.json({ error: `Unknown finding id '${id}'.` }, { status: 404 });
    const data = await res.json();
    if (!res.ok) return Response.json({ error: `Engine error (${res.status}).` }, { status: 502 });
    return Response.json(data);
  } catch (e) {
    return Response.json({ error: e instanceof Error ? e.message : "Engine unreachable." }, { status: 504 });
  }
}
