"use client";

import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { C } from "@/lib/tokens";
import { ToolNav } from "./ToolNav";
import { ConfidenceLegend } from "./ConfidenceLegend";
import { DiffBanner } from "./DiffBanner";
import { FindingsList } from "./FindingsList";
import { MeasuredCard } from "./MeasuredCard";
import { PerformancePanel } from "./PerformancePanel";
import { PillarCards } from "./PillarCards";
import { ScorecardPanel } from "./ScorecardPanel";
import { ScoreRing } from "./ScoreRing";
import { RenderTag } from "./RenderTag";
import { usePerformance } from "./usePerformance";
import { fixesByFinding, PILLAR_SECTIONS, priorityFixes, rgba, type Report } from "./types";

type State =
  | { phase: "empty" }
  | { phase: "loading"; url: string }
  | { phase: "error"; url: string; message: string }
  | { phase: "done"; url: string; report: Report };

function normalizeForSubmit(raw: string): string {
  const v = raw.trim();
  return /^https?:\/\//i.test(v) ? v : `https://${v}`;
}

export function ReportView() {
  const params = useSearchParams();
  const urlParam = params.get("url") ?? "";
  const [state, setState] = useState<State>({ phase: "empty" });
  const [input, setInput] = useState(urlParam);
  const [tab, setTab] = useState(0);

  const runScan = useCallback(async (url: string) => {
    setState({ phase: "loading", url });
    setTab(0);
    try {
      const res = await fetch("/api/scan", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ url }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.error || `Scan failed (${res.status}).`);
      setState({ phase: "done", url, report: data });
    } catch (e) {
      setState({ phase: "error", url, message: e instanceof Error ? e.message : "Something went wrong." });
    }
  }, []);

  // Kick off a scan whenever the ?url= param changes (e.g. arriving from the hero demo).
  useEffect(() => {
    if (urlParam) {
      setInput(urlParam);
      runScan(normalizeForSubmit(urlParam));
    } else {
      setState({ phase: "empty" });
    }
  }, [urlParam, runScan]);

  const submit = () => {
    if (input.trim()) runScan(normalizeForSubmit(input));
  };

  return (
    <div style={{ minHeight: "100vh", background: "var(--ink)" }}>
      <ToolNav active="report" />

      <main style={{ maxWidth: 880, margin: "0 auto", padding: "24px 20px 80px" }}>
        {/* URL bar — always present, for entering or re-scanning */}
        <div style={{ display: "flex", gap: 10, marginBottom: 22 }}>
          <div
            style={{
              flex: 1,
              display: "flex",
              alignItems: "center",
              gap: 10,
              padding: "0 14px",
              height: 46,
              border: "1px solid var(--border)",
              borderRadius: 10,
              background: "var(--surface)",
            }}
          >
            <span style={{ fontSize: 14, color: "var(--text-3)", fontFamily: "var(--mono)" }}>https://</span>
            <input
              value={input.replace(/^https?:\/\//i, "")}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
              placeholder="your-site.com"
              style={{
                flex: 1,
                background: "transparent",
                border: "none",
                outline: "none",
                color: "var(--text)",
                fontSize: 14,
                fontFamily: "var(--mono)",
              }}
            />
          </div>
          <button
            onClick={submit}
            disabled={state.phase === "loading"}
            style={{
              fontSize: 14,
              fontWeight: 500,
              border: "none",
              padding: "0 20px",
              height: 46,
              borderRadius: 10,
              cursor: state.phase === "loading" ? "default" : "pointer",
              flexShrink: 0,
              background: state.phase === "loading" ? C.raised : C.accent,
              color: state.phase === "loading" ? C.text3 : C.ink,
            }}
          >
            {state.phase === "loading" ? "Scanning…" : state.phase === "done" ? "Re-scan" : "Scan"}
          </button>
          {state.phase === "done" && (
            <button
              onClick={() => window.print()}
              style={{
                fontSize: 14,
                fontWeight: 500,
                border: "1px solid var(--border-strong)",
                padding: "0 18px",
                height: 46,
                borderRadius: 10,
                cursor: "pointer",
                flexShrink: 0,
                background: "transparent",
                color: "var(--text-2)",
              }}
            >
              Export
            </button>
          )}
        </div>

        {state.phase === "empty" && (
          <Placeholder>Enter a URL above to run a deterministic GEO-readiness scan.</Placeholder>
        )}

        {state.phase === "loading" && <Placeholder>Scanning {state.url} …</Placeholder>}

        {state.phase === "error" && (
          <div
            style={{
              padding: "20px 18px",
              border: `1px solid ${rgba(C.fail, 0.4)}`,
              borderRadius: 12,
              background: rgba(C.fail, 0.06),
              color: "var(--text-2)",
              fontSize: 14,
            }}
          >
            <strong style={{ color: "var(--text)" }}>Couldn&apos;t scan {state.url}.</strong>
            <div style={{ marginTop: 6, color: "var(--text-3)" }}>{state.message}</div>
          </div>
        )}

        {state.phase === "done" && <Body report={state.report} tab={tab} setTab={setTab} />}
      </main>
    </div>
  );
}

function Placeholder({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        height: 280,
        border: "1px dashed var(--border)",
        borderRadius: 12,
        color: "var(--text-3)",
        fontSize: 14,
        textAlign: "center",
        padding: 24,
      }}
    >
      {children}
    </div>
  );
}

function Body({ report, tab, setTab }: { report: Report; tab: number; setTab: (n: number) => void }) {
  const fixMap = fixesByFinding(report);
  const finalUrl = (report.meta?.final_url as string) || report.url;
  const when = new Date(report.fetched_at);

  // On-demand Performance — shared hook (same behaviour as the hero demo). Seed "done" if the
  // report already carries a performance score.
  const preScore = typeof report.pillar_scores.performance === "number" ? report.pillar_scores.performance : undefined;
  const { perf, controller: perfController, pillarOverride, findings: perfFindings } = usePerformance(
    finalUrl, preScore, report.findings.filter((f) => f.pillar === "performance"),
  );

  const pillarScores = { ...report.pillar_scores, ...pillarOverride };
  const allFindings = perfFindings.length ? [...report.findings, ...perfFindings] : report.findings;
  const fixes = priorityFixes(allFindings);

  // Performance detail gets its own "Google Lighthouse" panel (below), not a pillar tab.
  const sections = PILLAR_SECTIONS;
  const activeTab = Math.min(tab, sections.length - 1);
  const section = sections[activeTab];
  const sectionFindings = report.findings.filter((f) => f.pillar === section.key);

  return (
    <div style={{ animation: "dmFade 0.3s ease both" }}>
      {/* report header */}
      <div style={{ marginBottom: 18 }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 12, flexWrap: "wrap" }}>
          <h1 style={{ fontSize: 22, fontWeight: 500, letterSpacing: "-0.02em", marginBottom: 6, wordBreak: "break-all" }}>
            {finalUrl}
          </h1>
          <a
            href={`/site?url=${encodeURIComponent(finalUrl)}`}
            style={{ fontSize: 12.5, color: C.accent, whiteSpace: "nowrap", marginLeft: "auto" }}
          >
            Crawl whole site →
          </a>
        </div>
        <div style={{ fontSize: 12.5, color: "var(--text-3)", fontFamily: "var(--mono)" }}>
          scanned {when.toLocaleString()} · {report.findings.length} checks · schema v{report.schema_version ?? "?"}
          <RenderTag meta={report.meta} />
        </div>
      </div>

      <DiffBanner meta={report.meta} />

      <ScorecardPanel scorecard={report.scorecard} />

      <div style={{ marginBottom: 18 }}>
        <ConfidenceLegend />
      </div>

      <div style={{ display: "flex", gap: 16, alignItems: "stretch", marginBottom: 14 }}>
        <ScoreRing score={report.overall_score} />
        <PillarCards pillarScores={pillarScores} perf={perfController} />
      </div>

      {perf.phase === "error" && perf.error && (
        <div style={{ fontSize: 12, color: C.fail, marginBottom: 14 }}>{perf.error}</div>
      )}

      {perfFindings.length > 0 && <PerformancePanel findings={perfFindings} />}

      <div style={{ marginBottom: 24 }}>
        <MeasuredCard />
      </div>

      <SectionTitle>Priority fixes</SectionTitle>
      <div style={{ marginBottom: 28 }}>
        <FindingsList findings={fixes} fixes={fixMap} url={finalUrl} />
      </div>

      {/* per-pillar tabs */}
      <SectionTitle>All checks by pillar</SectionTitle>
      <div style={{ display: "flex", gap: 8, margin: "10px 0 14px", flexWrap: "wrap" }}>
        {sections.map((s, i) => {
          const active = i === activeTab;
          const score = pillarScores[s.key];
          return (
            <button
              key={s.key}
              onClick={() => setTab(i)}
              style={{
                fontSize: 13,
                padding: "7px 13px",
                borderRadius: 8,
                cursor: "pointer",
                border: `1px solid ${active ? rgba(C.accent, 0.5) : "var(--border)"}`,
                background: active ? rgba(C.accent, 0.12) : "transparent",
                color: active ? C.accent : "var(--text-2)",
              }}
            >
              {s.label}
              {typeof score === "number" && (
                <span style={{ marginLeft: 8, color: active ? C.accent : "var(--text-3)", fontFamily: "var(--mono)" }}>
                  {score}
                </span>
              )}
            </button>
          );
        })}
      </div>
      {/* key remounts the list per tab so its expanded-row state resets */}
      <FindingsList key={section.key} findings={sectionFindings} fixes={fixMap} url={finalUrl} openFirst={false} />
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <div style={{ fontSize: 13, color: "var(--text)", fontWeight: 500, marginBottom: 10 }}>{children}</div>;
}
