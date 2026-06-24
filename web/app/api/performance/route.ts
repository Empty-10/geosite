// POST /api/performance  { url }  → run the on-demand PageSpeed/Lighthouse check for a URL.
//
// Kept separate from /api/scan because it's slow (PSI is a single blocking lab run, ~10–30s)
// with no progress stream. Thin proxy to the engine, which holds the PageSpeed key. Requires
// DAMASK_ENGINE_URL. Engine reports "couldn't run" via { error } in a 200 body.

import { normalizeUrl, ssrfReason } from "@/lib/scanUrl";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 60;

const ENGINE_URL = process.env.DAMASK_ENGINE_URL;
const HTTP_TIMEOUT_MS = 55_000;

const NO_ENGINE =
  "Performance checks aren't available on this deployment yet — they run on the scan engine " +
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
  const raw = typeof (body as { url?: unknown })?.url === "string" ? (body as { url: string }).url.trim() : "";
  const target = normalizeUrl(raw);
  if (!target) return json({ error: "That doesn't look like a valid website URL." }, 400);
  const blocked = ssrfReason(target);
  if (blocked) return json({ error: blocked }, 400);

  try {
    const res = await fetch(`${ENGINE_URL.replace(/\/$/, "")}/performance`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ url: target }),
      signal: AbortSignal.timeout(HTTP_TIMEOUT_MS),
    });
    const data = await res.json();
    if (!res.ok) return json({ error: `Engine service error (${res.status}).` }, 502);
    return json(data); // { pillar, score, findings, error? }
  } catch (e) {
    return json({ error: e instanceof Error ? e.message : "Performance check unreachable." }, 504);
  }
}
