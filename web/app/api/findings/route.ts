// GET /api/findings  ->  the knowledge index: every finding Astova can explain.
// Thin proxy to the engine's /findings.
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const ENGINE_URL = process.env.ASTOVA_ENGINE_URL;
const TIMEOUT_MS = 15_000;

export async function GET(): Promise<Response> {
  const b = ENGINE_URL ? ENGINE_URL.replace(/\/$/, "") : null;
  if (!b) return Response.json({ findings: [], engineConfigured: false });
  try {
    const res = await fetch(`${b}/findings`, { signal: AbortSignal.timeout(TIMEOUT_MS) });
    const data = await res.json();
    if (!res.ok) return Response.json({ error: `Engine error (${res.status}).` }, { status: 502 });
    return Response.json(data);
  } catch (e) {
    return Response.json({ error: e instanceof Error ? e.message : "Engine unreachable." }, { status: 504 });
  }
}
