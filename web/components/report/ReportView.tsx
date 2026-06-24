"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { C } from "@/lib/tokens";
import { ToolNav } from "./ToolNav";
import { ConfidenceLegend } from "./ConfidenceLegend";
import { DiffBanner } from "./DiffBanner";
import { FindingsList } from "./FindingsList";
import { MeasuredCard } from "./MeasuredCard";
import { PillarCards, type PerfController } from "./PillarCards";
import { ScorecardPanel } from "./ScorecardPanel";
import { ScoreRing } from "./ScoreRing";
import { RenderTag } from "./RenderTag";
import { fixesByFinding, PILLAR_SECTIONS, priorityFixes, rgba, type Finding, type Report } from "./types";

// Honest descriptions of what PageSpeed is actually doing (it gives no real progress stream),
// advanced on our own elapsed timer.
const PERF_STAGES = [
  "Asking Google to run Lighthouse…",
  "Lighthouse is auditing the page…",
  "Measuring Core Web Vitals…",
  "Parsing results…",
];

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

type PerfState = {
  phase: "idle" | "loading" | "done" | "error";
  score: number | null;
  findings: Finding[];
  elapsed: number;
  error?: string;
};

function Body({ report, tab, setTab }: { report: Report; tab: number; setTab: (n: number) => void }) {
  const fixMap = fixesByFinding(report);
  const finalUrl = (report.meta?.final_url as string) || report.url;
  const when = new Date(report.fetched_at);

  // On-demand Performance. If the report already carries a performance score, start "done".
  const [perf, setPerf] = useState<PerfState>(() => {
    const pre = report.pillar_scores.performance;
    return typeof pre === "number"
      ? { phase: "done", score: pre, findings: report.findings.filter((f) => f.pillar === "performance"), elapsed: 0 }
      : { phase: "idle", score: null, findings: [], elapsed: 0 };
  });
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const stop = () => {
    if (timer.current) clearInterval(timer.current);
    timer.current = null;
  };
  useEffect(() => stop, []);

  const runPerformance = useCallback(async () => {
    setPerf((p) => ({ ...p, phase: "loading", elapsed: 0, error: undefined }));
    stop();
    timer.current = setInterval(() => setPerf((p) => (p.phase === "loading" ? { ...p, elapsed: p.elapsed + 1 } : p)), 1000);
    try {
      const res = await fetch("/api/performance", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ url: finalUrl }),
      });
      const data = await res.json();
      stop();
      if (!res.ok || data?.error || typeof data?.score !== "number") {
        setPerf((p) => ({ ...p, phase: "error", error: data?.error || `Performance check failed (${res.status}).` }));
        return;
      }
      setPerf({ phase: "done", score: data.score, findings: (data.findings as Finding[]) ?? [], elapsed: 0 });
    } catch (e) {
      stop();
      setPerf((p) => ({ ...p, phase: "error", error: e instanceof Error ? e.message : "Performance check failed." }));
    }
  }, [finalUrl]);

  const perfDone = perf.phase === "done" && typeof perf.score === "number";
  const pillarScores = perfDone ? { ...report.pillar_scores, performance: perf.score! } : report.pillar_scores;
  const allFindings = perf.findings.length ? [...report.findings, ...perf.findings] : report.findings;
  const fixes = priorityFixes(allFindings);

  // Add a Performance tab once it has findings to show.
  const sections = perf.findings.length ? [...PILLAR_SECTIONS, { label: "Performance", key: "performance" }] : PILLAR_SECTIONS;
  const activeTab = Math.min(tab, sections.length - 1);
  const section = sections[activeTab];
  const sectionFindings = allFindings.filter((f) => f.pillar === section.key);

  const perfController: PerfController | undefined =
    perf.phase === "done"
      ? undefined
      : {
          state: perf.phase === "loading" ? "loading" : perf.phase === "error" ? "error" : "idle",
          elapsed: perf.elapsed,
          label: PERF_STAGES[Math.min(Math.floor(perf.elapsed / 6), PERF_STAGES.length - 1)],
          onRun: runPerformance,
        };

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
