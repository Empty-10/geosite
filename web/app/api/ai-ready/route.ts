// POST /api/ai-ready  ->  the engine's ai_ready_loop "what to fix next" plan + Markdown export.
// Thin proxy to the engine's POST /ai-ready (which reuses ai_ready_loop + the Markdown formatter).
// No workflow logic lives here - the web app only validates the URL and forwards.

import { normalizeUrl, ssrfReason } from "@/lib/engineTarget";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 60;

const ENGINE_URL = process.env.ASTOVA_ENGINE_URL;
const TIMEOUT_MS = 55_000; // tolerate a cold-starting engine service

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

  const raw = typeof (body as { url?: unknown })?.url === "string" ? (body as { url: string }).url.trim() : "";
  if (!raw) return json({ error: "Provide a 'url' to assess." }, 400);

  const target = normalizeUrl(raw);
  if (!target) return json({ error: "That doesn't look like a valid website URL." }, 400);

  const blocked = ssrfReason(target);
  if (blocked) return json({ error: blocked }, 400);

  const base = ENGINE_URL ? ENGINE_URL.replace(/\/$/, "") : null;
  if (!base) {
    return json(
      {
        error:
          "The action-plan engine isn't configured on this deployment yet. Set ASTOVA_ENGINE_URL " +
          "to a running engine service (see web/README.md).",
      },
      503,
    );
  }

  const maxItems = Number((body as { maxItems?: unknown })?.maxItems) || 10;
  try {
    const res = await fetch(`${base}/ai-ready`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ target, target_type: "url", max_items: maxItems }),
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
    const data = await res.json();
    if (!res.ok) return json({ error: `Engine service error (${res.status}).` }, 502);
    return Response.json(data);
  } catch (e) {
    return json({ error: e instanceof Error ? e.message : "Engine service unreachable." }, 504);
  }
}
