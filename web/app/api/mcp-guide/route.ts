// GET /api/mcp-guide?client=...  ->  the engine's static MCP usage guide (mcp_usage_guide source of truth).
// Thin proxy to the engine's GET /mcp-guide. No guide content is duplicated in the web app.

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const ENGINE_URL = process.env.ASTOVA_ENGINE_URL;
const TIMEOUT_MS = 15_000;
const CLIENTS = new Set(["generic", "claude", "cursor", "chatgpt", "windsurf"]);

export async function GET(req: Request): Promise<Response> {
  const raw = new URL(req.url).searchParams.get("client") || "generic";
  const client = CLIENTS.has(raw) ? raw : "generic";

  const base = ENGINE_URL ? ENGINE_URL.replace(/\/$/, "") : null;
  if (!base) {
    return Response.json(
      {
        error:
          "The MCP guide service isn't configured on this deployment yet. Set ASTOVA_ENGINE_URL to a " +
          "running engine service (see web/README.md).",
      },
      { status: 503 },
    );
  }

  try {
    const res = await fetch(`${base}/mcp-guide?client=${encodeURIComponent(client)}`, {
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
    const data = await res.json();
    if (!res.ok) return Response.json({ error: `Engine service error (${res.status}).` }, { status: 502 });
    return Response.json(data);
  } catch (e) {
    return Response.json(
      { error: e instanceof Error ? e.message : "Engine service unreachable." },
      { status: 504 },
    );
  }
}
