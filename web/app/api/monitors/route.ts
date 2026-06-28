// GET  /api/monitors  → the user's monitored sites, each enriched with latest score,
//                       change since last scan, and a short score trend (for sparklines).
// POST /api/monitors  → add a site to monitor ({ url, cadence? }).
//
// Thin aggregating proxy to the engine (ASTOVA_ENGINE_URL). The engine must be running with
// persistence (ASTOVA_DATABASE_URL / ASTOVA_DB_PATH) for monitors to exist. When the engine
// isn't configured we return an empty, clearly-flagged payload so the dashboard renders a
// helpful empty state instead of erroring.
import { normalizeUrl, ssrfReason } from "@/lib/scanUrl";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const ENGINE_URL = process.env.ASTOVA_ENGINE_URL;
const TIMEOUT_MS = 20_000;

function base(): string | null {
  return ENGINE_URL ? ENGINE_URL.replace(/\/$/, "") : null;
}

type Scan = { id: number; score: number | null; created_at: string };

export async function GET(): Promise<Response> {
  const b = base();
  if (!b) return Response.json({ monitors: [], engineConfigured: false });

  try {
    const res = await fetch(`${b}/monitors`, { signal: AbortSignal.timeout(TIMEOUT_MS) });
    if (!res.ok) {
      return Response.json(
        { error: `Engine error (${res.status}).`, monitors: [], engineConfigured: true },
        { status: 502 },
      );
    }
    const data = await res.json();
    const monitors: Array<Record<string, unknown>> = data.monitors ?? [];

    const enriched = await Promise.all(
      monitors.map(async (m) => {
        const url = String(m.url ?? "");
        let scans: Scan[] = [];
        try {
          const h = await fetch(
            `${b}/history?url=${encodeURIComponent(url)}&kind=page&limit=14`,
            { signal: AbortSignal.timeout(TIMEOUT_MS) },
          );
          if (h.ok) scans = (await h.json()).scans ?? [];
        } catch {
          /* history is best-effort; a monitor with no scans yet is fine */
        }
        const scored = scans.filter((s) => typeof s.score === "number") as Required<Scan>[];
        const latestScore = scored[0]?.score ?? null;
        const prevScore = scored[1]?.score ?? null;
        const change =
          latestScore != null && prevScore != null ? latestScore - prevScore : null;
        // history is newest-first; reverse so the sparkline reads oldest → newest.
        const trend = scored.map((s) => s.score).reverse();
        const lastScanAt = scored[0]?.created_at ?? m.last_run_at ?? null;
        return { ...m, latestScore, change, trend, lastScanAt, scanCount: scored.length };
      }),
    );

    return Response.json({ monitors: enriched, engineConfigured: true });
  } catch (e) {
    return Response.json(
      {
        error: e instanceof Error ? e.message : "Engine unreachable.",
        monitors: [],
        engineConfigured: true,
      },
      { status: 504 },
    );
  }
}

export async function POST(req: Request): Promise<Response> {
  const b = base();
  if (!b) {
    return Response.json({ error: "Monitoring isn't available on this deployment." }, { status: 503 });
  }

  let body: { url?: string; cadence?: string; email?: string };
  try {
    body = await req.json();
  } catch {
    return Response.json({ error: "Invalid request." }, { status: 400 });
  }

  const normalized = normalizeUrl((body.url ?? "").trim());
  if (!normalized) return Response.json({ error: "Enter a valid URL." }, { status: 400 });
  const ssrf = ssrfReason(normalized);
  if (ssrf) return Response.json({ error: ssrf }, { status: 400 });

  try {
    const res = await fetch(`${b}/monitors`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        url: normalized,
        cadence: body.cadence || "daily",
        email: body.email || null,
      }),
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      return Response.json(
        { error: data?.detail || `Engine error (${res.status}).` },
        { status: 502 },
      );
    }
    return Response.json(data);
  } catch (e) {
    return Response.json(
      { error: e instanceof Error ? e.message : "Engine unreachable." },
      { status: 504 },
    );
  }
}
