"use client";

// Shareable AI Readiness Report view (/report/[id]?share=<token>). Read-only: loads a stored report
// + its derived bundle (metadata, action summary, markdown, agent prompt) from /api/reports/<token>
// and renders it. Reuses existing report components; no scanning, no LLM. A valid token = access.

import { useEffect, useState } from "react";
import { C, scoreColor } from "@/lib/tokens";
import { ScoreRing } from "@/components/report/ScoreRing";
import { ExecutiveSummary } from "@/components/report/ExecutiveSummary";
import { ScorecardPanel } from "@/components/report/ScorecardPanel";
import { ConfidenceLegend } from "@/components/report/ConfidenceLegend";
import { ConsultantVerdict, ExpertReviewsPanel, ImplementationProgramme, VerificationPanel,
  AppendixSection } from "@/components/report/ConsultantReport";
import type { Report } from "@/components/report/types";

type Item = {
  finding_id: string; title: string; pillar: string; severity: string;
  status: string; evidence: string | null; recommendation: string | null;
};
type ActionSummary = {
  actionable_count: number; deterministic_fix_count: number; ai_assisted_count: number;
  manual_count: number; deterministic: Item[]; ai_assisted: Item[]; manual: Item[];
};
type Metadata = {
  report_id: number | null; created_at: string | null; scanned_target: string | null;
  engine_version: string | null; ruleset_version: string | null; report_version: string | null;
  share_token: string | null;
};
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type ReportDict = { overall_score: number; pillar_scores: Record<string, number>; scorecard: any; findings: any[] };
type Bundle = { metadata: Metadata; action_summary: ActionSummary; markdown: string; agent_prompt: string };

const PILLAR_LABEL: Record<string, string> = {
  technical: "Technical", onpage: "On-page", geo: "GEO readiness", performance: "Performance", local: "Local",
};

export function ReportDetailView({ reportId, share }: { reportId: string; share: string }) {
  const [data, setData] = useState<{ report: ReportDict; bundle: Bundle } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState("");

  useEffect(() => {
    if (!share) {
      setError("This report needs a share link. Open the full link you were given (it ends with ?share=...).");
      setLoading(false);
      return;
    }
    let cancelled = false;
    fetch(`/api/reports/${encodeURIComponent(share)}`)
      .then((r) => r.json().then((b) => ({ ok: r.ok, b })))
      .then(({ ok, b }) => {
        if (cancelled) return;
        if (!ok || b.error) setError(b.error || "Could not load this report.");
        else setData(b);
      })
      .catch((e) => !cancelled && setError(e instanceof Error ? e.message : "Could not load this report."))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [share]);

  async function copy(text: string, key: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(key);
      setTimeout(() => setCopied(""), 2000);
    } catch {
      setError("Could not copy to clipboard.");
    }
  }

  function downloadMarkdown(markdown: string) {
    const blob = new Blob([markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "astova-action-plan.md";
    a.click();
    URL.revokeObjectURL(url);
  }

  if (loading) return <Wrap><p style={{ color: C.text3 }}>Loading report...</p></Wrap>;
  if (error || !data)
    return (
      <Wrap>
        <div style={{ padding: 16, borderRadius: 10, border: `1px solid ${C.warn}`, background: "rgba(224,162,43,0.1)", color: C.text }}>
          {error || "Report unavailable."}
        </div>
      </Wrap>
    );

  const { report, bundle } = data;
  const m = bundle.metadata;
  const s = bundle.action_summary;
  const target = m.scanned_target || "this page";

  return (
    <Wrap>
      <div style={{ display: "flex", alignItems: "center", gap: 20, flexWrap: "wrap", marginBottom: 8 }}>
        <ScoreRing score={report.overall_score} label="AI Readiness" />
        <div style={{ flex: 1, minWidth: 240 }}>
          <h1 style={{ fontSize: 22, fontWeight: 600, margin: "0 0 4px", wordBreak: "break-all" }}>{target}</h1>
          <div style={{ fontSize: 18, fontWeight: 700, color: scoreColor(report.overall_score) }}>
            {report.overall_score}<span style={{ fontSize: 13, color: C.text3 }}>/100 AI Readiness</span>
          </div>
        </div>
      </div>

      <Meta m={m} />

      <ActionsBar
        copied={copied}
        onCopyMarkdown={() => copy(bundle.markdown, "md")}
        onCopyPrompt={() => copy(bundle.agent_prompt, "prompt")}
        onDownload={() => downloadMarkdown(bundle.markdown)}
        planHref={`/ai-ready?url=${encodeURIComponent(target)}`}
        printHref={`/report/${encodeURIComponent(reportId)}/print?share=${encodeURIComponent(share)}`}
      />

      {/* Consultant report hierarchy (same as the live report) */}
      <ConsultantVerdict report={report as unknown as Report} />
      <ExpertReviewsPanel report={report as unknown as Report} />
      <ImplementationProgramme report={report as unknown as Report} />
      <VerificationPanel report={report as unknown as Report} />

      <AppendixSection title="Detailed findings & evidence">
      <ExecutiveSummary scorecard={report.scorecard} />

      <H2>Readiness breakdown</H2>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 8 }}>
        {Object.entries(report.pillar_scores).map(([k, v]) => (
          <div key={k} style={{ border: `1px solid ${C.border}`, borderRadius: 10, background: C.surface, padding: "10px 14px", minWidth: 120 }}>
            <div style={{ fontSize: 20, fontWeight: 700, color: scoreColor(v) }}>{v}</div>
            <div style={{ fontSize: 12, color: C.text2 }}>{PILLAR_LABEL[k] || k}</div>
          </div>
        ))}
      </div>

      <ScorecardPanel scorecard={report.scorecard} findings={report.findings} />

      <H2>Action summary</H2>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 12 }}>
        <Count label="Actionable" value={s.actionable_count} color={C.text} />
        <Count label="Deterministic fixes" value={s.deterministic_fix_count} color={C.accent} />
        <Count label="AI-assisted" value={s.ai_assisted_count} color={C.measured} />
        <Count label="Manual review" value={s.manual_count} color={C.text3} />
      </div>

      <Bucket title="Deterministic fixes available" items={s.deterministic} color={C.accent}
        note="Astova can generate ready-to-apply content for these." />
      <Bucket title="AI-assisted fixes" items={s.ai_assisted} color={C.measured}
        note="Your AI agent drafts these from real page content." />
      <Bucket title="Manual review items" items={s.manual} color={C.text3}
        note="Need human judgement (facts, identity, local-business, legal)." />

      <div style={{ marginTop: 18 }}>
        <ConfidenceLegend />
      </div>
      </AppendixSection>
    </Wrap>
  );
}

function Wrap({ children }: { children: React.ReactNode }) {
  return <article style={{ maxWidth: 860, margin: "0 auto", padding: "40px 20px 80px", color: C.text }}>{children}</article>;
}

function H2({ children }: { children: React.ReactNode }) {
  return <h2 style={{ fontSize: 16, fontWeight: 600, margin: "28px 0 10px" }}>{children}</h2>;
}

function Meta({ m }: { m: Metadata }) {
  const when = m.created_at ? new Date(m.created_at).toLocaleString() : "?";
  const bits = [
    `Report #${m.report_id ?? "?"}`,
    `Generated ${when}`,
    `Engine ${m.engine_version ?? "?"}`,
    `Ruleset ${m.ruleset_version ?? "?"}`,
    `Format ${m.report_version ?? "?"}`,
  ];
  return (
    <div style={{ fontSize: 12, color: C.text3, fontFamily: "var(--mono)", marginBottom: 16 }}>
      {bits.join("  ·  ")}
    </div>
  );
}

function ActionsBar({
  copied, onCopyMarkdown, onCopyPrompt, onDownload, planHref, printHref,
}: {
  copied: string; onCopyMarkdown: () => void; onCopyPrompt: () => void; onDownload: () => void;
  planHref: string; printHref: string;
}) {
  const btn = (primary: boolean): React.CSSProperties => ({
    padding: "9px 14px", borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: "pointer",
    border: primary ? "none" : `1px solid ${C.border}`,
    background: primary ? C.accent : C.raised, color: primary ? C.ink : C.text,
    textDecoration: "none", display: "inline-block",
  });
  return (
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 20 }}>
      <button onClick={onCopyPrompt} style={btn(true)}>{copied === "prompt" ? "Copied" : "Copy agent prompt"}</button>
      <button onClick={onCopyMarkdown} style={btn(false)}>{copied === "md" ? "Copied" : "Copy Markdown"}</button>
      <button onClick={onDownload} style={btn(false)}>Download Markdown</button>
      <a href={printHref} style={btn(false)}>Print / Save PDF</a>
      <a href={planHref} style={btn(false)}>Open AI Ready Action Plan</a>
    </div>
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

function Bucket({ title, items, color, note }: { title: string; items: Item[]; color: string; note: string }) {
  if (!items.length) return null;
  return (
    <div style={{ marginBottom: 16 }}>
      <H2>{title} <span style={{ fontSize: 13, color: C.text3, fontWeight: 400 }}>({items.length})</span></H2>
      <p style={{ color: C.text3, fontSize: 12.5, margin: "0 0 8px" }}>{note}</p>
      <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "grid", gap: 8 }}>
        {items.map((it) => (
          <li key={it.finding_id} style={{ border: `1px solid ${C.border}`, borderLeft: `3px solid ${color}`, borderRadius: 8, background: C.surface, padding: "10px 14px" }}>
            <div style={{ display: "flex", gap: 8, alignItems: "baseline", flexWrap: "wrap" }}>
              <span style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: C.text3 }}>{it.severity}</span>
              <span style={{ fontSize: 14, fontWeight: 600 }}>{it.title}</span>
              <code style={{ fontSize: 11, color: C.text3 }}>{it.finding_id}</code>
            </div>
            {it.recommendation && <div style={{ fontSize: 13, color: C.text2, lineHeight: 1.5, marginTop: 3 }}>{it.recommendation}</div>}
          </li>
        ))}
      </ul>
    </div>
  );
}
