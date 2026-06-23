// POST /api/visibility — MEASURED AI-visibility sampling.
//
// For each prompt, ask Claude the question WITH web search on, then measure: did the brand get
// named in the answer, and did the domain get cited as a source? Aggregate across prompts into
// rates with Wilson 95% confidence intervals + sample size. This is the only multi-call LLM
// surface; it costs real money (web search + tokens), so it is bounded and metered.
//
// MEASURED, never VERIFIED: results are a sample on a date, reported with a confidence band.
// Single engine for now (Claude); Perplexity/Gemini/OpenAI arrive when their keys are added.

import Anthropic from "@anthropic-ai/sdk";
import { hostMatches, wilson } from "@/lib/visibility";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 60;

const MODEL = process.env.DAMASK_VISIBILITY_MODEL || "claude-sonnet-4-6";
const MAX_PROMPTS = 5;
const MAX_COMPETITORS = 6;
const MAX_TOKENS = 1024;
const WEB_SEARCH_USES = 4;

// In-memory metering (per-instance; resets on cold start). A run = up to MAX_PROMPTS engine
// calls, so we meter runs, conservatively, to cap spend.
const ipHits = new Map<string, { n: number; reset: number }>();
let dayCount = 0;
let dayReset = Date.now() + 86_400_000;
const PER_IP_PER_DAY = 5;
const GLOBAL_PER_DAY = 40;

function json(body: unknown, status = 200): Response {
  return Response.json(body, { status });
}

function rateLimited(ip: string): string | null {
  const now = Date.now();
  if (now > dayReset) {
    dayCount = 0;
    dayReset = now + 86_400_000;
  }
  if (dayCount >= GLOBAL_PER_DAY) return "Daily visibility-sampling limit reached — try again tomorrow.";
  const h = ipHits.get(ip);
  if (!h || now > h.reset) ipHits.set(ip, { n: 1, reset: now + 86_400_000 });
  else if (h.n >= PER_IP_PER_DAY) return "You've used today's visibility runs — try again tomorrow.";
  else h.n += 1;
  return null;
}

type Analysis = {
  appeared: boolean;
  domainCited: boolean;
  domainSearched: boolean;
  competitors: string[];
  excerpt: string;
};

/** Pull answer text + cited/searched source URLs out of a web-search response. */
function analyze(content: unknown[], brand: string, domain: string, competitors: string[]): Analysis {
  let answer = "";
  const cited = new Set<string>();
  const searched = new Set<string>();
  for (const raw of content) {
    const block = raw as { type?: string; text?: string; citations?: { url?: string }[]; content?: unknown };
    if (block.type === "text") {
      answer += (block.text ?? "") + " ";
      for (const c of block.citations ?? []) if (c?.url) cited.add(c.url);
    } else if (block.type === "web_search_tool_result") {
      const results = block.content;
      if (Array.isArray(results)) for (const r of results) if (r?.url) searched.add(r.url);
    }
  }
  const low = answer.toLowerCase();
  return {
    appeared: !!brand && low.includes(brand.toLowerCase()),
    domainCited: [...cited].some((u) => hostMatches(u, domain)),
    domainSearched: [...searched].some((u) => hostMatches(u, domain)),
    competitors: competitors.filter((c) => low.includes(c.toLowerCase())),
    excerpt: answer.replace(/\s+/g, " ").trim().slice(0, 320),
  };
}

function asList(v: unknown, cap: number): string[] {
  const arr = Array.isArray(v)
    ? v
    : typeof v === "string"
      ? v.split(/\r?\n|,/)
      : [];
  return arr.map((s) => String(s).trim()).filter(Boolean).slice(0, cap);
}

export async function POST(req: Request): Promise<Response> {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) return json({ error: "AI visibility sampling isn't configured on this deployment." }, 503);

  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return json({ error: "Invalid JSON body." }, 400);
  }
  const b = body as { brand?: unknown; domain?: unknown; prompts?: unknown; competitors?: unknown };
  const brand = typeof b.brand === "string" ? b.brand.trim() : "";
  const domain = (typeof b.domain === "string" ? b.domain.trim() : "").replace(/^https?:\/\//, "").replace(/\/.*$/, "");
  const prompts = asList(b.prompts, MAX_PROMPTS);
  const competitors = asList(b.competitors, MAX_COMPETITORS);

  if (!brand) return json({ error: "Provide your brand name (what to look for in answers)." }, 400);
  if (!domain) return json({ error: "Provide your domain (to detect citations)." }, 400);
  if (prompts.length === 0) return json({ error: "Add at least one question to sample." }, 400);

  const ip = req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || "unknown";
  const limited = rateLimited(ip);
  if (limited) return json({ error: limited }, 429);

  const client = new Anthropic({ apiKey });

  const sampleOne = async (prompt: string) => {
    try {
      const msg = await client.messages.create({
        model: MODEL,
        max_tokens: MAX_TOKENS,
        messages: [{ role: "user", content: prompt }],
        tools: [{ type: "web_search_20260209", name: "web_search", max_uses: WEB_SEARCH_USES }],
      });
      if (msg.stop_reason === "refusal") return { prompt, error: "declined" };
      const a = analyze(msg.content as unknown[], brand, domain, competitors);
      return {
        prompt,
        appeared: a.appeared,
        cited: a.domainCited,
        found_not_cited: a.domainSearched && !a.domainCited,
        competitors: a.competitors,
        excerpt: a.excerpt,
      };
    } catch {
      return { prompt, error: "sampling failed" };
    }
  };

  const settled = await Promise.all(prompts.map(sampleOne));
  const ok = settled.filter((r) => !("error" in r && r.error)) as {
    prompt: string; appeared: boolean; cited: boolean; found_not_cited: boolean; competitors: string[]; excerpt: string;
  }[];
  if (ok.length === 0) return json({ error: "Every sample failed — please try again." }, 502);

  const n = ok.length;
  const appeared = ok.filter((r) => r.appeared).length;
  const cited = ok.filter((r) => r.cited).length;
  const mkRate = (count: number) => ({ count, n, rate: count / n, ci: wilson(count, n) });

  // Share of voice: how often the brand is named vs each competitor, across the sample.
  const tally = new Map<string, number>([[brand, appeared]]);
  for (const c of competitors) tally.set(c, ok.filter((r) => r.competitors.includes(c)).length);
  const total = [...tally.values()].reduce((s, v) => s + v, 0) || 1;
  const share_of_voice = [...tally.entries()]
    .map(([name, mentions]) => ({ name, mentions, share: mentions / total, isTarget: name === brand }))
    .sort((x, y) => y.mentions - x.mentions);

  const report = {
    scan_type: "visibility" as const,
    confidence: "measured" as const,
    brand,
    domain,
    engine: "Claude (web search)",
    model: MODEL,
    sampled_at: new Date().toISOString(),
    sample_size: n,
    requested: prompts.length,
    visibility: mkRate(appeared),
    citation: mkRate(cited),
    share_of_voice,
    prompts: ok,
  };

  dayCount += 1;
  return json(report);
}
