// POST /api/visibility/suggest — generate realistic sampling questions from a brand + topic.
// Cheap helper (one Haiku call, no web search) so users aren't staring at a blank prompt box.

import Anthropic from "@anthropic-ai/sdk";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 20;

const MODEL = process.env.DAMASK_SUGGEST_MODEL || "claude-haiku-4-5";

function json(body: unknown, status = 200): Response {
  return Response.json(body, { status });
}

export async function POST(req: Request): Promise<Response> {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) return json({ error: "Not configured on this deployment." }, 503);

  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return json({ error: "Invalid JSON body." }, 400);
  }
  const brand = typeof (body as { brand?: unknown })?.brand === "string" ? (body as { brand: string }).brand.trim() : "";
  const topic = typeof (body as { topic?: unknown })?.topic === "string" ? (body as { topic: string }).topic.trim() : "";
  if (!brand && !topic) return json({ error: "Provide a brand or topic." }, 400);

  try {
    const msg = await new Anthropic({ apiKey }).messages.create({
      model: MODEL,
      max_tokens: 400,
      system:
        "Generate realistic questions a potential customer would type into an AI assistant " +
        "(ChatGPT, Claude, Perplexity) where a company like the one described could be recommended " +
        "or cited. Questions should be category-level (not name the brand). Return ONLY a JSON array " +
        'of exactly 5 short question strings, e.g. ["...","..."].',
      messages: [{ role: "user", content: `Brand: ${brand || "(unspecified)"}\nCategory / topic: ${topic || "(infer from brand)"}` }],
    });
    const block = msg.content.find((x) => x.type === "text");
    const text = block && "text" in block ? block.text : "";
    const m = text.match(/\[[\s\S]*\]/);
    const prompts = m ? (JSON.parse(m[0]) as unknown[]).map((s) => String(s).trim()).filter(Boolean).slice(0, 5) : [];
    if (prompts.length === 0) return json({ error: "Couldn't generate questions — add your own." }, 502);
    return json({ prompts });
  } catch {
    return json({ error: "Suggestion failed — add your own questions." }, 502);
  }
}
