"use client";

// AI Ready Action Plan - a human entry point to the same ai_ready_loop workflow the MCP/CLI expose.
// Enter a URL -> POST /api/ai-ready -> show score, summary counts, top actions, and a copyable
// Markdown export. Deliberately simple/functional. No fixes applied, no LLM - just the plan.

import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { C, scoreColor } from "@/lib/tokens";

type Fix = { supported?: boolean; deterministic?: boolean; suggested_location?: string | null };
type Knowledge = { why_it_matters?: string; can_astova_generate?: string } | null;
type Verify = { target: string; finding_id: string; target_type: string };
type Item = {
  finding_id: string;
  title: string;
  status: string;
  severity: string;
  confidence: string;
  evidence: string | null;
  recommendation: string | null;
  knowledge: Knowledge;
  fix: Fix;
  verify: Verify;
  agent_next_step: string;
};
type Plan = {
  target: string;
  score: number | null;
  summary: string;
  actionable_count: number;
  deterministic_fix_count: number;
  ai_assisted_count: number;
  manual_count: number;
  items: Item[];
  markdown: string;
  error?: string;
};

const SEV_COLOR: Record<string, string> = {
  critical: C.fail, high: C.fail, medium: C.warn, low: C.text3, info: C.text3,
};

function bucketLabel(it: Item): { text: string; color: string } {
  if (it.fix?.supported) return { text: "Deterministic fix ready", color: C.accent };
  if (it.knowledge?.can_astova_generate === "ai_assisted") return { text: "AI-assisted", color: C.measured };
  return { text: "Manual review", color: C.text3 };
}

export function AiReadyView() {
  const params = useSearchParams();
  const prefilled = (params.get("url") || "").trim();
  const [url, setUrl] = useState(prefilled || "stripe.com");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [copied, setCopied] = useState(false);
  const autoRan = useRef(false);

  // Arriving from the homepage CTA with ?url=... prefills the input and runs once automatically.
  useEffect(() => {
    if (prefilled && !autoRan.current) {
      autoRan.current = true;
      generate(prefilled);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prefilled]);

  async function generate(target?: string) {
    const v = (target ?? url).trim();
    if (!v || loading) return;
    setLoading(true);
    setError(null);
    setPlan(null);
    setCopied(false);
    try {
      const res = await fetch("/api/ai-ready", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ url: v }),
      });
      const data = (await res.json()) as Plan & { error?: string };
      if (!res.ok || data.error) {
        setError(data.error || `Request failed (${res.status}).`);
      } else {
        setPlan(data);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  async function copyMarkdown() {
    if (!plan?.markdown) return;
    try {
      await navigator.clipboard.writeText(plan.markdown);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setError("Could not copy to clipboard.");
    }
  }

  return (
    <main style={{ maxWidth: 820, margin: "0 auto", padding: "48px 20px 80px", color: C.text }}>
      <h1 style={{ fontSize: 28, fontWeight: 700, margin: "0 0 8px" }}>AI Ready Action Plan</h1>
      <p style={{ color: C.text2, margin: "0 0 24px", lineHeight: 1.5 }}>
        Scan a URL and get the same prioritised, agent-friendly plan Astova gives coding agents via MCP and
        the CLI: what to fix, in what order, and how to verify each fix. Deterministic - no AI guesswork.
      </p>

      <div style={{ display: "flex", gap: 8, marginBottom: 24 }}>
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && generate()}
          placeholder="example.com"
          aria-label="URL to assess"
          style={{
            flex: 1, padding: "12px 14px", borderRadius: 10, border: `1px solid ${C.border}`,
            background: C.surface, color: C.text, fontSize: 15,
          }}
        />
        <button
          onClick={() => generate()}
          disabled={loading}
          style={{
            padding: "12px 18px", borderRadius: 10, border: "none", fontSize: 15, fontWeight: 600,
            background: C.accent, color: "#04130B", cursor: loading ? "default" : "pointer",
            opacity: loading ? 0.7 : 1, whiteSpace: "nowrap",
          }}
        >
          {loading ? "Generating..." : "Generate action plan"}
        </button>
      </div>

      {error && (
        <div style={{ padding: 14, borderRadius: 10, border: `1px solid ${C.fail}`, background: "rgba(229,72,77,0.1)", color: C.text, marginBottom: 24 }}>
          {error}
        </div>
      )}

      {plan && !plan.error && (
        <section>
          <div style={{ display: "flex", alignItems: "center", gap: 20, flexWrap: "wrap", marginBottom: 16 }}>
            <div style={{ fontSize: 40, fontWeight: 700, color: scoreColor(plan.score ?? 0) }}>
              {plan.score}<span style={{ fontSize: 18, color: C.text3 }}>/100</span>
            </div>
            <div style={{ color: C.text2, fontSize: 14, lineHeight: 1.5, flex: 1, minWidth: 220 }}>{plan.summary}</div>
          </div>

          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 24 }}>
            <Count label="Actionable" value={plan.actionable_count} color={C.text} />
            <Count label="Deterministic fixes" value={plan.deterministic_fix_count} color={C.accent} />
            <Count label="AI-assisted" value={plan.ai_assisted_count} color={C.measured} />
            <Count label="Manual review" value={plan.manual_count} color={C.text3} />
          </div>

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <h2 style={{ fontSize: 18, fontWeight: 600, margin: 0 }}>Top actions</h2>
            <button
              onClick={copyMarkdown}
              style={{
                padding: "8px 14px", borderRadius: 8, border: `1px solid ${C.border}`,
                background: C.raised, color: C.text, fontSize: 13, cursor: "pointer",
              }}
            >
              {copied ? "Copied" : "Copy Markdown"}
            </button>
          </div>

          {plan.items.length === 0 ? (
            <p style={{ color: C.text2 }}>Nothing to fix - this URL looks AI Ready.</p>
          ) : (
            <ol style={{ listStyle: "none", padding: 0, margin: 0, display: "grid", gap: 12 }}>
              {plan.items.map((it, i) => {
                const b = bucketLabel(it);
                return (
                  <li key={`${it.finding_id}-${i}`} style={{ border: `1px solid ${C.border}`, borderRadius: 12, background: C.surface, padding: 16 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 6 }}>
                      <span style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: SEV_COLOR[it.severity] || C.text3 }}>
                        {it.severity}
                      </span>
                      <span style={{ fontSize: 15, fontWeight: 600 }}>{it.title}</span>
                      <code style={{ fontSize: 12, color: C.text3 }}>{it.finding_id}</code>
                      <span style={{ marginLeft: "auto", fontSize: 11, fontWeight: 600, color: b.color, border: `1px solid ${b.color}`, borderRadius: 999, padding: "2px 8px" }}>
                        {b.text}
                      </span>
                    </div>
                    {it.evidence && <Row label="Evidence" value={it.evidence} mono />}
                    {it.knowledge?.why_it_matters && <Row label="Why it matters" value={it.knowledge.why_it_matters} />}
                    {it.recommendation && <Row label="Recommended fix" value={it.recommendation} />}
                    <Row label="Agent next step" value={it.agent_next_step} />
                    <Row
                      label="Verify"
                      value={`verify_fix("${it.verify.target}", "${it.verify.finding_id}", "${it.verify.target_type}")`}
                      mono
                    />
                  </li>
                );
              })}
            </ol>
          )}
        </section>
      )}
    </main>
  );
}

function Count({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div style={{ border: `1px solid ${C.border}`, borderRadius: 10, background: C.surface, padding: "10px 14px", minWidth: 110 }}>
      <div style={{ fontSize: 22, fontWeight: 700, color }}>{value}</div>
      <div style={{ fontSize: 12, color: C.text2 }}>{label}</div>
    </div>
  );
}

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div style={{ display: "flex", gap: 8, fontSize: 13, lineHeight: 1.5, marginTop: 4 }}>
      <span style={{ color: C.text3, minWidth: 104, flexShrink: 0 }}>{label}</span>
      <span style={{ color: C.text2, fontFamily: mono ? "ui-monospace, monospace" : undefined, wordBreak: "break-word" }}>{value}</span>
    </div>
  );
}
