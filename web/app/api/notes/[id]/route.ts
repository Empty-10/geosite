// DELETE /api/notes/:id  → remove a note. Thin proxy to the engine.
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const ENGINE_URL = process.env.ASTOVA_ENGINE_URL;
const TIMEOUT_MS = 15_000;

export async function DELETE(
  _req: Request,
  ctx: { params: Promise<{ id: string }> },
): Promise<Response> {
  if (!ENGINE_URL) return Response.json({ error: "Notes aren’t available." }, { status: 503 });
  const { id } = await ctx.params;
  if (!/^\d+$/.test(id)) return Response.json({ error: "Invalid note id." }, { status: 400 });

  try {
    const res = await fetch(`${ENGINE_URL.replace(/\/$/, "")}/notes/${id}`, {
      method: "DELETE",
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
