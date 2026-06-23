// POST /api/cloudflare-logs  { domain, days? }  → pull AI-crawler activity for a domain from
// Cloudflare analytics (no log upload). Thin proxy to the engine, which holds the CF token.
// Cloudflare-side errors come back as 200 with meta.error (the engine never raises); the client
// inspects that. Requires DAMASK_ENGINE_URL.

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 45;

const ENGINE_URL = process.env.DAMASK_ENGINE_URL;
const HTTP_TIMEOUT_MS = 40_000;

const NO_ENGINE =
  "Cloudflare connect isn't available on this deployment yet — it runs on the scan engine " +
  "service. Set DAMASK_ENGINE_URL to its URL (see web/README.md).";

function json(body: unknown, status = 200): Response {
  return Response.json(body, { status });
}

/** Reduce "https://www.acme.com/x" → "acme.com"; null if it isn't a plausible domain. */
function toDomain(raw: string): string | null {
  let v = raw.trim().toLowerCase();
  if (/^https?:\/\//.test(v)) {
    try {
      v = new URL(v).hostname;
    } catch {
      return null;
    }
  }
  v = v.replace(/^www\./, "").split("/")[0];
  return /^[a-z0-9-]+(\.[a-z0-9-]+)+$/.test(v) ? v : null;
}

export async function POST(req: Request): Promise<Response> {
  if (!ENGINE_URL) return json({ error: NO_ENGINE }, 503);

  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return json({ error: "Invalid JSON body." }, 400);
  }

  const raw = typeof (body as { domain?: unknown })?.domain === "string" ? (body as { domain: string }).domain : "";
  const domain = toDomain(raw);
  if (!domain) return json({ error: "Enter a domain on your Cloudflare account, e.g. acme.com." }, 400);

  const wanted = Number((body as { days?: unknown })?.days) || 7;
  const days = Math.min(Math.max(wanted, 1), 30);

  try {
    const res = await fetch(`${ENGINE_URL.replace(/\/$/, "")}/cloudflare-logs`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ domain, days }),
      signal: AbortSignal.timeout(HTTP_TIMEOUT_MS),
    });
    const data = await res.json();
    if (!res.ok) return json({ error: `Engine service error (${res.status}).` }, 502);
    return json(data); // LogReport (Cloudflare-side errors live in data.meta.error)
  } catch (e) {
    return json({ error: e instanceof Error ? e.message : "Engine service unreachable." }, 504);
  }
}
