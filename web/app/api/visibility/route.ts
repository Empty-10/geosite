// POST /api/visibility — MEASURED multi-engine AI-visibility sampling.
//
// For each prompt × each configured engine (Claude, Perplexity, Gemini — whichever keys are set),
// ask the engine the question with web search/grounding, then measure: did the brand get named,
// and did the domain get cited as a source? Aggregate into overall + per-engine rates (Wilson
// 95% CIs) and SHARE OF VOICE (you vs competitors). Bounded + metered — it costs real money.
//
// MEASURED, never VERIFIED: a sample on a date, shown with confidence bands.

import { analyzeSample, hostOf, wilson } from "@/lib/visibility";
import { classifySentiment, enabledEngines } from "@/lib/visibilityEngines";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 60;

const MAX_PROMPTS = 5;
const MAX_COMPETITORS = 6;

// In-memory metering (per-instance). A run = up to MAX_PROMPTS × engines calls.
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

function asList(v: unknown, cap: number): string[] {
  const arr = Array.isArray(v) ? v : typeof v === "string" ? v.split(/\r?\n|,/) : [];
  return arr.map((s) => String(s).trim()).filter(Boolean).slice(0, cap);
}

function rate(count: number, n: number): { count: number; n: number; rate: number; ci: [number, number] } {
  return { count, n, rate: n ? count / n : 0, ci: wilson(count, n) };
}

type Row = { engine: string; prompt: string; appeared: boolean; cited: boolean; competitors: string[]; excerpt: string; sources: string[] };

export async function POST(req: Request): Promise<Response> {
  const engines = enabledEngines();
  if (engines.length === 0) {
    return json({ error: "AI visibility isn't configured — set ANTHROPIC_API_KEY (and optionally PERPLEXITY_API_KEY / GEMINI_API_KEY)." }, 503);
  }

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

  // Fan out: every (engine, prompt) pair, in parallel.
  const tasks: Promise<Row | null>[] = [];
  for (const eng of engines) {
    for (const prompt of prompts) {
      tasks.push(
        eng.sample(prompt).then((s) => {
          if (!s) return null;
          const a = analyzeSample(s.text, s.sources, brand, domain, competitors);
          return { engine: eng.name, prompt, appeared: a.appeared, cited: a.cited, competitors: a.competitors, excerpt: a.excerpt, sources: s.sources };
        }).catch(() => null),
      );
    }
  }
  const rows = (await Promise.all(tasks)).filter(Boolean) as Row[];
  if (rows.length === 0) return json({ error: "Every sample failed — please try again." }, 502);

  const n = rows.length;
  const appeared = rows.filter((r) => r.appeared).length;
  const cited = rows.filter((r) => r.cited).length;

  const per_engine = engines
    .map((e) => {
      const er = rows.filter((r) => r.engine === e.name);
      if (er.length === 0) return null;
      return { engine: e.name, visibility: rate(er.filter((r) => r.appeared).length, er.length), citation: rate(er.filter((r) => r.cited).length, er.length) };
    })
    .filter(Boolean);

  // Share of voice: brand-named vs each competitor across all samples.
  const tally = new Map<string, number>([[brand, appeared]]);
  for (const c of competitors) tally.set(c, rows.filter((r) => r.competitors.includes(c)).length);
  const total = [...tally.values()].reduce((s, v) => s + v, 0) || 1;
  const share_of_voice = [...tally.entries()]
    .map(([name, mentions]) => ({ name, mentions, share: mentions / total, isTarget: name === brand }))
    .sort((x, y) => y.mentions - x.mentions);

  // Source intelligence: which domains the engines cite for these queries.
  const domainCounts = new Map<string, number>();
  for (const r of rows) {
    const seen = new Set<string>(); // count a domain once per answer
    for (const url of r.sources) {
      const h = hostOf(url);
      if (h && !seen.has(h)) {
        seen.add(h);
        domainCounts.set(h, (domainCounts.get(h) ?? 0) + 1);
      }
    }
  }
  const top_sources = [...domainCounts.entries()]
    .map(([d, citations]) => ({ domain: d, citations, isYou: d === domain.replace(/^www\./, "") }))
    .sort((a, b) => b.citations - a.citations)
    .slice(0, 8);

  // Sentiment: how the brand is portrayed where it appeared (one cheap Haiku call).
  let sentiment = null as { positive: number; neutral: number; negative: number; n: number } | null;
  const appearedExcerpts = rows.filter((r) => r.appeared && r.excerpt).map((r) => r.excerpt);
  const labels = await classifySentiment(brand, appearedExcerpts);
  if (labels && labels.length) {
    sentiment = {
      positive: labels.filter((l) => l === "positive").length,
      neutral: labels.filter((l) => l === "neutral").length,
      negative: labels.filter((l) => l === "negative").length,
      n: labels.length,
    };
  }

  // Per-prompt grid (cells per engine).
  const promptResults = prompts.map((prompt) => {
    const pr = rows.filter((r) => r.prompt === prompt);
    return {
      prompt,
      cells: pr.map((r) => ({ engine: r.engine, appeared: r.appeared, cited: r.cited })),
      competitors: [...new Set(pr.flatMap((r) => r.competitors))],
      excerpt: pr[0]?.excerpt ?? "",
    };
  });

  dayCount += 1;
  return json({
    scan_type: "visibility",
    confidence: "measured",
    brand,
    domain,
    engines: engines.map((e) => e.name),
    sampled_at: new Date().toISOString(),
    sample_size: n,
    requested: engines.length * prompts.length,
    visibility: rate(appeared, n),
    citation: rate(cited, n),
    per_engine,
    share_of_voice,
    top_sources,
    sentiment,
    prompts: promptResults,
  });
}
