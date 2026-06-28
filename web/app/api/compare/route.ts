// POST /api/compare  →  scans 2–4 pages via the engine and returns a deterministic benchmark.
//
// The comparison is a server-side multi-scan, so it runs against the engine HTTP service
// (ASTOVA_ENGINE_URL). There's no local shell-out path: point at a running engine service
// (locally: `uvicorn astova_engine.service:app` + ASTOVA_ENGINE_URL=http://localhost:8000).

import { normalizeUrl, ssrfReason } from "@/lib/urlGuard";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 60;

const ENGINE_URL = process.env.ASTOVA_ENGINE_URL;
const ENGINE_HTTP_TIMEOUT_MS = 58_000; // N concurrent scans + a possible cold start
const MAX_URLS = 4;

function json(body: unknown, status = 200): Response {
  return Response.json(body, { status });
}

export async function POST(req: Request): Promise<Response> {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return json({ error: "Invalid JSON body." }, 400);
  }

  const rawList = (body as { urls?: unknown })?.urls;
  if (!Array.isArray(rawList)) return json({ error: "Provide a 'urls' array to compare." }, 400);

  // Normalize + de-dupe (by href) + SSRF-check each, preserving order (first = "you").
  const seen = new Set<string>();
  const urls: string[] = [];
  for (const raw of rawList) {
    if (typeof raw !== "string" || !raw.trim()) continue;
    const target = normalizeUrl(raw.trim());
    if (!target) return json({ error: `"${raw}" doesn't look like a valid website URL.` }, 400);
    const blocked = ssrfReason(target);
    if (blocked) return json({ error: blocked }, 400);
    if (!seen.has(target)) {
      seen.add(target);
      urls.push(target);
    }
  }

  if (urls.length < 2) return json({ error: "Provide at least 2 different URLs to compare." }, 400);
  if (urls.length > MAX_URLS) return json({ error: `Compare up to ${MAX_URLS} URLs at once.` }, 400);

  if (!ENGINE_URL) {
    return json(
      { error: "Comparison needs the engine service — set ASTOVA_ENGINE_URL to its URL." },
      503,
    );
  }

  try {
    const res = await fetch(`${ENGINE_URL.replace(/\/$/, "")}/compare`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ urls }),
      signal: AbortSignal.timeout(ENGINE_HTTP_TIMEOUT_MS),
    });
    if (!res.ok) return json({ error: `Engine service error (${res.status}).` }, 502);
    return Response.json(await res.json());
  } catch (e) {
    return json({ error: e instanceof Error ? e.message : "Engine service unreachable." }, 504);
  }
}
