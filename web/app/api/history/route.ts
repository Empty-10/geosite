// GET /api/history?url=  → a site's saved scans (newest first), each with its share token
// so the UI can link back to that exact report. Thin proxy to the engine's /history.
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const ENGINE_URL = process.env.ASTOVA_ENGINE_URL;
const TIMEOUT_MS = 15_000;

export async function GET(req: Request): Promise<Response> {
  const url = new URL(req.url).searchParams.get("url");
  if (!url) return Response.json({ error: "Missing url." }, { status: 400 });

  const b = ENGINE_URL ? ENGINE_URL.replace(/\/$/, "") : null;
  if (!b) return Response.json({ scans: [], engineConfigured: false });

  try {
    const res = await fetch(
      `${b}/history?url=${encodeURIComponent(url)}&kind=page&limit=50`,
      { signal: AbortSignal.timeout(TIMEOUT_MS) },
    );
    const data = await res.json();
    if (!res.ok) return Response.json({ error: `Engine error (${res.status}).` }, { status: 502 });
    return Response.json({ ...data, engineConfigured: true });
  } catch (e) {
    return Response.json(
      { error: e instanceof Error ? e.message : "Engine unreachable." },
      { status: 504 },
    );
  }
}
