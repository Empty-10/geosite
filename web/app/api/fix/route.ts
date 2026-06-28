// POST /api/fix — on-demand, AI-DRAFTED remediation for judgment-dependent findings.
//
// This is the ONLY place an LLM is called. It is metered (per-IP + global daily caps),
// cached by page-content hash (re-opening/re-scanning doesn't re-bill), and degrades
// cleanly: with no ANTHROPIC_API_KEY it returns 503 and the UI shows a disabled state.
// Deterministic fixes never come here — they ride along free on the scan path.
//
// Output is labeled source: "ai_drafted" so the UI shows "Drafted by Claude — review
// before publishing". It is NOT presented as a VERIFIED fact (accuracy principle).

import Anthropic from "@anthropic-ai/sdk";
import { normalizeUrl, ssrfReason } from "@/lib/scanUrl";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 30;

const MODEL = process.env.ASTOVA_FIX_MODEL || "claude-haiku-4-5";
const MAX_TOKENS = 800;
const PAGE_TIMEOUT_MS = 12_000;

// Findings that support AI drafting, mapped to a draft "kind". Everything else is 400.
const GENERATIVE: Record<string, "frontload" | "dehedge" | "expand"> = {
  "geo.aeo": "frontload",
  "geo.frontload": "frontload",
  "geo.definitive": "dehedge",
  "geo.thin_content": "expand",
};

// Best-effort, in-memory state. On serverless this is per-instance and resets on cold start;
// fine as a prototype guardrail. Real metering = plan/credits (the monetization hook).
const draftCache = new Map<string, { draft: string; rationale: string }>();
const ipHits = new Map<string, { n: number; reset: number }>();
let dayCount = 0;
let dayReset = Date.now() + 86_400_000;
const PER_IP_PER_MIN = 8;
const GLOBAL_PER_DAY = 200;

function json(body: unknown, status = 200): Response {
  return Response.json(body, { status });
}

function rateLimited(ip: string): string | null {
  const now = Date.now();
  if (now > dayReset) {
    dayCount = 0;
    dayReset = now + 86_400_000;
  }
  if (dayCount >= GLOBAL_PER_DAY) return "Daily AI-draft limit reached — try again tomorrow.";
  const h = ipHits.get(ip);
  if (!h || now > h.reset) ipHits.set(ip, { n: 1, reset: now + 60_000 });
  else if (h.n >= PER_IP_PER_MIN) return "Too many requests — wait a minute and try again.";
  else h.n += 1;
  return null;
}

function decode(s: string): string {
  return s
    .replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&nbsp;/g, " ");
}

function extractContext(html: string): { title: string; opening: string } {
  const tm = html.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
  const title = tm ? decode(tm[1]).trim().slice(0, 200) : "";
  const body = html
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<noscript[\s\S]*?<\/noscript>/gi, " ")
    .replace(/<[^>]+>/g, " ");
  const opening = decode(body).replace(/\s+/g, " ").trim().split(" ").slice(0, 220).join(" ");
  return { title, opening };
}

function buildPrompt(kind: string, ctx: { title: string; opening: string }): { system: string; user: string } {
  const jsonRule =
    ' Respond with ONLY a JSON object: {"draft": "<the rewritten text or outline>", ' +
    '"rationale": "<one sentence on what you changed and why>"} — no other text.';
  if (kind === "dehedge") {
    return {
      system:
        "You are an editor making web copy more confident and citable for AI answer engines. " +
        "Rewrite the passage to remove hedging ('might', 'usually', 'arguably'…) and state things " +
        "directly. Stay strictly faithful to the source — do not invent facts or overclaim beyond " +
        "what's given. Keep the meaning. 40–80 words." + jsonRule,
      user: `Page title: ${ctx.title}\nCurrent passage:\n${ctx.opening.slice(0, 900)}\n\nRewrite it in confident, direct language.`,
    };
  }
  if (kind === "expand") {
    return {
      system:
        "You are a GEO/SEO content strategist. Given a thin page, propose a concise bulleted " +
        "outline of sections and points that would make it a complete, citable answer — based ONLY " +
        "on the page's apparent topic. Do not write full prose; give an outline, 6–10 bullets max." +
        jsonRule,
      user: `Page title: ${ctx.title}\nCurrent content (excerpt):\n${ctx.opening}\n\nOutline what to add.`,
    };
  }
  return {
    system:
      "You are an editor improving a web page's opening so AI answer engines (ChatGPT, Claude, " +
      "Perplexity, Google AI Overviews) can extract a direct answer. Rewrite the opening to LEAD " +
      "with a complete, self-contained answer to the page's implied question, in confident, " +
      "non-hedged language. Stay strictly faithful to the source — do not invent facts, numbers, " +
      "names, or claims not present. 40–70 words." + jsonRule,
    user: `Page title: ${ctx.title}\nCurrent opening:\n${ctx.opening}\n\nRewrite the opening to front-load the answer.`,
  };
}

function parseDraft(text: string): { draft: string; rationale: string } {
  const m = text.match(/\{[\s\S]*\}/);
  if (m) {
    try {
      const o = JSON.parse(m[0]);
      return { draft: String(o.draft ?? "").trim(), rationale: String(o.rationale ?? "").trim() };
    } catch {
      /* fall through to raw text */
    }
  }
  return { draft: text.trim(), rationale: "" };
}

const TITLES: Record<string, string> = {
  frontload: "Front-loaded opening",
  dehedge: "Confident rewrite",
  expand: "Content outline",
};

function payload(findingId: string, kind: string, draft: string, rationale: string) {
  return {
    finding_id: findingId,
    title: TITLES[kind] ?? "AI draft",
    kind: kind === "expand" ? "markdown" : "text",
    language: kind === "expand" ? "markdown" : "text",
    content: draft,
    note: rationale || null,
    source: "ai_drafted" as const,
  };
}

async function sha256(s: string): Promise<string> {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return Array.from(new Uint8Array(buf)).map((b) => b.toString(16).padStart(2, "0")).join("");
}

export async function POST(req: Request): Promise<Response> {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) return json({ error: "AI drafting isn't configured on this deployment." }, 503);

  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return json({ error: "Invalid JSON body." }, 400);
  }
  const rawUrl = (body as { url?: unknown })?.url;
  const findingId = (body as { findingId?: unknown })?.findingId;
  if (typeof rawUrl !== "string" || typeof findingId !== "string")
    return json({ error: "Provide 'url' and 'findingId'." }, 400);

  const kind = GENERATIVE[findingId];
  if (!kind) return json({ error: "This finding doesn't support AI drafting." }, 400);

  const target = normalizeUrl(rawUrl.trim());
  if (!target) return json({ error: "That doesn't look like a valid URL." }, 400);
  const blocked = ssrfReason(target);
  if (blocked) return json({ error: blocked }, 400);

  const ip = req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || "unknown";
  const limited = rateLimited(ip);
  if (limited) return json({ error: limited }, 429);

  // Fetch the page for context (also keys the cache on its content).
  let html: string;
  try {
    const res = await fetch(target, {
      headers: { "user-agent": "astovabot/0.1 (+fixes)" },
      signal: AbortSignal.timeout(PAGE_TIMEOUT_MS),
    });
    html = await res.text();
  } catch {
    return json({ error: "Couldn't fetch the page to draft from." }, 502);
  }
  const ctx = extractContext(html);
  if (!ctx.opening) return json({ error: "No readable content found on the page." }, 422);

  const cacheKey = await sha256(`${findingId}\n${ctx.opening}`);
  const cached = draftCache.get(cacheKey);
  if (cached) return json(payload(findingId, kind, cached.draft, cached.rationale));

  const { system, user } = buildPrompt(kind, ctx);
  let draft = "";
  let rationale = "";
  try {
    const msg = await new Anthropic({ apiKey }).messages.create({
      model: MODEL,
      max_tokens: MAX_TOKENS,
      system,
      messages: [{ role: "user", content: user }],
    });
    if (msg.stop_reason === "refusal") return json({ error: "The model declined to draft this." }, 422);
    const block = msg.content.find((b) => b.type === "text");
    const text = block && "text" in block ? block.text : "";
    ({ draft, rationale } = parseDraft(text));
  } catch {
    return json({ error: "AI drafting failed — please try again." }, 502);
  }
  if (!draft) return json({ error: "The model returned an empty draft." }, 502);

  draftCache.set(cacheKey, { draft, rationale });
  dayCount += 1;
  return json(payload(findingId, kind, draft, rationale));
}
