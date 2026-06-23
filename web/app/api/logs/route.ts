// POST /api/logs  { text, source? }  → analyze access-log text for AI-crawler activity.
//
// Parsing is fast/synchronous (no job flow), but it runs in the engine — the deterministic
// analysis layer — so this is a thin proxy. Requires DAMASK_ENGINE_URL (locally, run the
// engine via uvicorn). No URL is fetched here, so there's no SSRF surface.

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 30;

const ENGINE_URL = process.env.DAMASK_ENGINE_URL;
const HTTP_TIMEOUT_MS = 25_000;
const MAX_BYTES = 5_000_000; // ~5 MB of log text per upload

const NO_ENGINE =
  "Crawler-log analysis isn't available on this deployment yet — it runs on the scan engine " +
  "service. Set DAMASK_ENGINE_URL to its URL (see web/README.md).";

function json(body: unknown, status = 200): Response {
  return Response.json(body, { status });
}

export async function POST(req: Request): Promise<Response> {
  if (!ENGINE_URL) return json({ error: NO_ENGINE }, 503);

  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return json({ error: "Invalid JSON body." }, 400);
  }

  const text = typeof (body as { text?: unknown })?.text === "string" ? (body as { text: string }).text : "";
  if (!text.trim()) return json({ error: "Paste or upload an access log to analyze." }, 400);
  if (text.length > MAX_BYTES) {
    return json({ error: "That log is too large — trim it to the most recent ~5 MB and try again." }, 413);
  }
  const source =
    typeof (body as { source?: unknown })?.source === "string"
      ? (body as { source: string }).source.slice(0, 120)
      : "uploaded log";

  try {
    const res = await fetch(`${ENGINE_URL.replace(/\/$/, "")}/logs`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ text, source }),
      signal: AbortSignal.timeout(HTTP_TIMEOUT_MS),
    });
    const data = await res.json();
    if (!res.ok) return json({ error: `Engine service error (${res.status}).` }, 502);
    return json(data);
  } catch (e) {
    return json({ error: e instanceof Error ? e.message : "Engine service unreachable." }, 504);
  }
}
