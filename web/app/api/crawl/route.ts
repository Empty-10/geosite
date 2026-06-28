// Site crawl proxy.
//   POST /api/crawl       { url, maxPages? }  → start a crawl on the engine, return { job_id }.
//   GET  /api/crawl?id=…                      → poll the job → { status, progress, result?, error? }.
//
// Unlike /api/scan, a crawl runs long (many pages), so the engine runs it as a background job
// and the client polls. There's no serverless shell-out path for a long crawl, so this requires
// the engine HTTP service: set ASTOVA_ENGINE_URL (locally, run the engine via uvicorn).

import { normalizeUrl, ssrfReason } from "@/lib/scanUrl";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 60;

const ENGINE_URL = process.env.ASTOVA_ENGINE_URL;
const HTTP_TIMEOUT_MS = 55_000;

const NO_ENGINE =
  "Site crawl isn't available on this deployment yet — it runs on the scan engine service. " +
  "Set ASTOVA_ENGINE_URL to its URL (see web/README.md).";

function json(body: unknown, status = 200): Response {
  return Response.json(body, { status });
}

function engineBase(): string {
  return (ENGINE_URL as string).replace(/\/$/, "");
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
  if (!raw) return json({ error: "Provide a 'url' to crawl." }, 400);

  const target = normalizeUrl(raw);
  if (!target) return json({ error: "That doesn't look like a valid website URL." }, 400);

  const blocked = ssrfReason(target);
  if (blocked) return json({ error: blocked }, 400);

  const wanted = Number((body as { maxPages?: unknown })?.maxPages) || 25;
  const maxPages = Math.min(Math.max(wanted, 1), 50);

  try {
    const res = await fetch(`${engineBase()}/crawl`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ url: target, max_pages: maxPages }),
      signal: AbortSignal.timeout(HTTP_TIMEOUT_MS),
    });
    const data = await res.json();
    if (!res.ok) return json({ error: `Engine service error (${res.status}).` }, 502);
    return json(data); // { job_id, status }
  } catch (e) {
    return json({ error: e instanceof Error ? e.message : "Engine service unreachable." }, 504);
  }
}

export async function GET(req: Request): Promise<Response> {
  if (!ENGINE_URL) return json({ error: NO_ENGINE }, 503);

  const id = new URL(req.url).searchParams.get("id");
  if (!id) return json({ error: "Provide a job id." }, 400);
  if (!/^[a-f0-9]{6,32}$/i.test(id)) return json({ error: "Invalid job id." }, 400);

  try {
    const res = await fetch(`${engineBase()}/crawl/${id}`, {
      signal: AbortSignal.timeout(HTTP_TIMEOUT_MS),
    });
    if (res.status === 404) return json({ error: "That crawl job expired — start a new scan." }, 404);
    const data = await res.json();
    if (!res.ok) return json({ error: `Engine service error (${res.status}).` }, 502);
    return json(data);
  } catch (e) {
    return json({ error: e instanceof Error ? e.message : "Engine service unreachable." }, 504);
  }
}
