// GET  /api/notes?url=  → a site's running note log (newest first).
// POST /api/notes        → add a note ({ url, body }).
// Thin proxy to the engine's /notes.
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const ENGINE_URL = process.env.ASTOVA_ENGINE_URL;
const TIMEOUT_MS = 15_000;

function base(): string | null {
  return ENGINE_URL ? ENGINE_URL.replace(/\/$/, "") : null;
}

export async function GET(req: Request): Promise<Response> {
  const url = new URL(req.url).searchParams.get("url");
  if (!url) return Response.json({ error: "Missing url." }, { status: 400 });
  const b = base();
  if (!b) return Response.json({ notes: [], engineConfigured: false });

  try {
    const res = await fetch(`${b}/notes?url=${encodeURIComponent(url)}`, {
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
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

export async function POST(req: Request): Promise<Response> {
  const b = base();
  if (!b) return Response.json({ error: "Notes aren’t available on this deployment." }, { status: 503 });

  let body: { url?: string; body?: string };
  try {
    body = await req.json();
  } catch {
    return Response.json({ error: "Invalid request." }, { status: 400 });
  }
  const url = (body.url ?? "").trim();
  const text = (body.body ?? "").trim();
  if (!url) return Response.json({ error: "Missing url." }, { status: 400 });
  if (!text) return Response.json({ error: "Note is empty." }, { status: 400 });
  if (text.length > 5000) return Response.json({ error: "Note is too long." }, { status: 400 });

  try {
    const res = await fetch(`${b}/notes`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ url, body: text }),
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) return Response.json({ error: `Engine error (${res.status}).` }, { status: 502 });
    return Response.json(data);
  } catch (e) {
    return Response.json(
      { error: e instanceof Error ? e.message : "Engine unreachable." },
      { status: 504 },
    );
  }
}
