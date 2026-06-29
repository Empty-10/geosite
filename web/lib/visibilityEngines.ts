// AI-engine providers for visibility sampling. Each returns the engine's answer text + the
// source URLs it cited/grounded on, so the same detection logic runs across all of them.
// Engines are gated by env keys — the feature runs on whatever is configured (Claude today;
// add PERPLEXITY_API_KEY / GEMINI_API_KEY to light up the others). No key in the plugin/client;
// keys live server-side here.

import Anthropic from "@anthropic-ai/sdk";

export type Sample = { text: string; sources: string[] };
export type Engine = { name: string; sample: (prompt: string) => Promise<Sample | null> };

const TIMEOUT = 40_000;

export function enabledEngines(): Engine[] {
  const engines: Engine[] = [];
  // "ChatGPT" = the real OpenAI API with web search, so the label matches the product users mean.
  const openai = process.env.OPENAI_API_KEY;
  if (openai) engines.push({ name: "ChatGPT", sample: (p) => sampleOpenAI(p, openai) });
  const anthropic = process.env.ANTHROPIC_API_KEY;
  if (anthropic) engines.push({ name: "Claude", sample: (p) => sampleClaude(p, anthropic) });
  const pplx = process.env.PERPLEXITY_API_KEY;
  if (pplx) engines.push({ name: "Perplexity", sample: (p) => samplePerplexity(p, pplx) });
  const gem = process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY;
  if (gem) engines.push({ name: "Gemini", sample: (p) => sampleGemini(p, gem) });
  return engines;
}

export type Sentiment = "positive" | "neutral" | "negative";

/** Classify how the brand is portrayed in each passage — one cheap Haiku call for the whole run. */
export async function classifySentiment(brand: string, passages: string[]): Promise<Sentiment[] | null> {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey || passages.length === 0) return null;
  try {
    const msg = await new Anthropic({ apiKey }).messages.create({
      model: process.env.ASTOVA_SENTIMENT_MODEL || "claude-haiku-4-5",
      max_tokens: 300,
      system:
        `For each numbered passage, classify how the brand "${brand}" is portrayed: positive, ` +
        `neutral, or negative. Return ONLY a JSON array of strings (one per passage), e.g. ["positive","neutral"].`,
      messages: [{ role: "user", content: passages.map((p, i) => `${i + 1}. ${p}`).join("\n\n") }],
    });
    const block = msg.content.find((b) => b.type === "text");
    const text = block && "text" in block ? block.text : "";
    const m = text.match(/\[[\s\S]*\]/);
    if (!m) return null;
    return (JSON.parse(m[0]) as string[]).map((s) => {
      const v = String(s).toLowerCase();
      return v.startsWith("pos") ? "positive" : v.startsWith("neg") ? "negative" : "neutral";
    });
  } catch {
    return null;
  }
}

async function sampleOpenAI(prompt: string, apiKey: string): Promise<Sample | null> {
  // OpenAI Responses API with the web_search tool — the closest API proxy to ChatGPT's
  // browsing answer. (If the API rejects the tool name on your account, switch the type to
  // "web_search_preview".) Pulls answer text + url_citation annotations as cited sources.
  const model = process.env.ASTOVA_OPENAI_MODEL || "gpt-4o";
  try {
    const r = await fetch("https://api.openai.com/v1/responses", {
      method: "POST",
      headers: { authorization: `Bearer ${apiKey}`, "content-type": "application/json" },
      body: JSON.stringify({ model, input: prompt, tools: [{ type: "web_search" }] }),
      signal: AbortSignal.timeout(TIMEOUT),
    });
    if (!r.ok) return null;
    const d = await r.json();
    let text = "";
    const sources = new Set<string>();
    for (const item of (d?.output ?? []) as { type?: string; content?: unknown[] }[]) {
      if (item?.type !== "message" || !Array.isArray(item.content)) continue;
      for (const c of item.content as { type?: string; text?: string; annotations?: { type?: string; url?: string }[] }[]) {
        if (c?.type !== "output_text") continue;
        text += (c.text ?? "") + " ";
        for (const a of c.annotations ?? []) if (a?.type === "url_citation" && a?.url) sources.add(a.url);
      }
    }
    if (!text && typeof d?.output_text === "string") text = d.output_text;
    return { text, sources: [...sources] };
  } catch {
    return null;
  }
}

async function sampleClaude(prompt: string, apiKey: string): Promise<Sample | null> {
  const model = process.env.ASTOVA_VISIBILITY_MODEL || "claude-sonnet-4-6";
  try {
    const msg = await new Anthropic({ apiKey }).messages.create({
      model,
      max_tokens: 1024,
      messages: [{ role: "user", content: prompt }],
      tools: [{ type: "web_search_20260209", name: "web_search", max_uses: 4 }],
    });
    if (msg.stop_reason === "refusal") return null;
    let text = "";
    const sources = new Set<string>();
    for (const raw of msg.content as unknown[]) {
      const b = raw as { type?: string; text?: string; citations?: { url?: string }[]; content?: unknown };
      if (b.type === "text") {
        text += (b.text ?? "") + " ";
        for (const c of b.citations ?? []) if (c?.url) sources.add(c.url);
      } else if (b.type === "web_search_tool_result" && Array.isArray(b.content)) {
        for (const r of b.content as { url?: string }[]) if (r?.url) sources.add(r.url);
      }
    }
    return { text, sources: [...sources] };
  } catch {
    return null;
  }
}

async function samplePerplexity(prompt: string, apiKey: string): Promise<Sample | null> {
  const model = process.env.ASTOVA_PERPLEXITY_MODEL || "sonar";
  try {
    const r = await fetch("https://api.perplexity.ai/chat/completions", {
      method: "POST",
      headers: { authorization: `Bearer ${apiKey}`, "content-type": "application/json" },
      body: JSON.stringify({ model, messages: [{ role: "user", content: prompt }] }),
      signal: AbortSignal.timeout(TIMEOUT),
    });
    if (!r.ok) return null;
    const d = await r.json();
    const text = d?.choices?.[0]?.message?.content ?? "";
    const sources: string[] = Array.isArray(d?.citations)
      ? d.citations
      : Array.isArray(d?.search_results)
        ? d.search_results.map((s: { url?: string }) => s?.url)
        : [];
    return { text, sources: sources.filter(Boolean) };
  } catch {
    return null;
  }
}

async function sampleGemini(prompt: string, apiKey: string): Promise<Sample | null> {
  const model = process.env.ASTOVA_GEMINI_MODEL || "gemini-2.0-flash";
  try {
    const r = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`,
      {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }], tools: [{ google_search: {} }] }),
        signal: AbortSignal.timeout(TIMEOUT),
      },
    );
    if (!r.ok) return null;
    const d = await r.json();
    const cand = d?.candidates?.[0];
    const text: string = (cand?.content?.parts ?? []).map((p: { text?: string }) => p?.text ?? "").join(" ");
    const chunks = cand?.groundingMetadata?.groundingChunks ?? [];
    const sources: string[] = chunks.map((c: { web?: { uri?: string } }) => c?.web?.uri).filter(Boolean);
    return { text, sources };
  } catch {
    return null;
  }
}
