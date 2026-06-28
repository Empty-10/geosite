"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { C } from "@/lib/tokens";
import { ToolNav } from "./ToolNav";
import { CitationBridge } from "./CitationBridge";
import { ConfidenceLegend } from "./ConfidenceLegend";
import { DiffBanner } from "./DiffBanner";
import { ExecutiveSummary } from "./ExecutiveSummary";
import { FindingsList } from "./FindingsList";
import { PerformancePanel } from "./PerformancePanel";
import { ScanProgress } from "./ScanProgress";
import { PillarCards } from "./PillarCards";
import { ScorecardPanel } from "./ScorecardPanel";
import { ScoreRing } from "./ScoreRing";
import { RenderTag } from "./RenderTag";
import { usePerformance } from "./usePerformance";
import { buildFixesText, fixesByFinding, impactByFinding, PILLAR_SECTIONS, priorityFixes, rgba, type Finding, type Report } from "./types";

type State =
  | { phase: "empty" }
  | { phase: "loading"; url: string }
  | { phase: "loadingSaved" }
  | { phase: "error"; url: string; message: string }
  | { phase: "done"; url: string; report: Report };

function normalizeForSubmit(raw: string): string {
  const v = raw.trim();
  return /^https?:\/\//i.test(v) ? v : `https://${v}`;
}

export function ReportView() {
  const params = useSearchParams();
  const urlParam = params.get("url") ?? "";
  const idParam = params.get("id") ?? "";
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

  // Load a previously-saved report (shareable ?id= link) instead of re-scanning.
  const loadSaved = useCallback(async (id: string) => {
    setState({ phase: "loadingSaved" });
    setTab(0);
    try {
      const res = await fetch(`/api/scans/${encodeURIComponent(id)}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data?.error || `Couldn't load report (${res.status}).`);
      const url = (data.meta?.final_url as string) || data.url || "";
      setInput(url);
      setState({ phase: "done", url, report: data });
    } catch (e) {
      setState({ phase: "error", url: "", message: e instanceof Error ? e.message : "Couldn't load the saved report." });
    }
  }, []);

  // ?id= loads a saved report; ?url= runs a fresh scan.
  useEffect(() => {
    if (idParam) {
      loadSaved(idParam);
    } else if (urlParam) {
      setInput(urlParam);
      runScan(normalizeForSubmit(urlParam));
    } else {
      setState({ phase: "empty" });
    }
  }, [idParam, urlParam, runScan, loadSaved]);

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
              background: state.phase === "loading" ? "var(--raised)" : C.accent,
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

        {state.phase === "loading" && <ScanProgress url={state.url} />}

        {state.phase === "loadingSaved" && <Placeholder>Loading saved report…</Placeholder>}

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
  const impacts = impactByFinding(report.scorecard);
  const fixes = priorityFixes(allFindings, impacts);

  // Performance detail gets its own "Google Lighthouse" panel (below), not a pillar tab.
  const sections = PILLAR_SECTIONS;
  const activeTab = Math.min(tab, sections.length - 1);
  const section = sections[activeTab];
  const sectionFindings = report.findings.filter((f) => f.pillar === section.key);

  // Two-audience layering: the exec view (verdict → score → priority fixes) is always visible;
  // the dev detail (every check, by pillar) opens on demand.
  const [showAllChecks, setShowAllChecks] = useState(false);

  // Clicking a scored pillar card jumps to its checks (or to the Lighthouse panel).
  const checksRef = useRef<HTMLDivElement>(null);
  const perfRef = useRef<HTMLDivElement>(null);
  const jumpToPillar = (key: string) => {
    if (key === "performance") {
      perfRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }
    const idx = PILLAR_SECTIONS.findIndex((s) => s.key === key);
    if (idx >= 0) setTab(idx);
    setShowAllChecks(true);
    checksRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <div style={{ animation: "dmFade 0.3s ease both" }}>
      {/* report header */}
      <div style={{ marginBottom: 18 }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 12, flexWrap: "wrap" }}>
          <h1 style={{ fontSize: 22, fontWeight: 500, letterSpacing: "-0.02em", marginBottom: 6, wordBreak: "break-all" }}>
            {finalUrl}
          </h1>
          <div style={{ marginLeft: "auto", display: "flex", gap: 14, alignItems: "baseline", flexWrap: "wrap" }}>
            {report.meta?.scan_token != null && <ShareButton token={report.meta.scan_token as string} />}
            <FixesExport report={report} url={finalUrl} findings={allFindings} impacts={impacts} />
            <a href={`/compare?url=${encodeURIComponent(finalUrl)}`} style={{ fontSize: 12.5, color: C.accent, whiteSpace: "nowrap" }}>
              Compare vs competitors →
            </a>
            <a href={`/site?url=${encodeURIComponent(finalUrl)}`} style={{ fontSize: 12.5, color: C.accent, whiteSpace: "nowrap" }}>
              Crawl whole site →
            </a>
          </div>
        </div>
        <div style={{ fontSize: 12.5, color: "var(--text-3)", fontFamily: "var(--mono)" }}>
          scanned {when.toLocaleString()} · {report.findings.length} checks · schema v{report.schema_version ?? "?"}
          <RenderTag meta={report.meta} />
        </div>
      </div>

      <DiffBanner meta={report.meta} />

      <ExecutiveSummary scorecard={report.scorecard} />

      <ScorecardPanel scorecard={report.scorecard} findings={allFindings} />

      <div style={{ marginBottom: 18 }}>
        <ConfidenceLegend />
      </div>

      <div style={{ display: "flex", gap: 16, alignItems: "stretch", marginBottom: 14 }}>
        <ScoreRing score={report.overall_score} />
        <PillarCards pillarScores={pillarScores} perf={perfController} onSelect={jumpToPillar} />
      </div>

      {perf.phase === "error" && perf.error && (
        <div style={{ fontSize: 12, color: C.fail, marginBottom: 14 }}>{perf.error}</div>
      )}

      <div ref={perfRef}>{perfFindings.length > 0 && <PerformancePanel findings={perfFindings} />}</div>

      <div style={{ marginBottom: 24 }}>
        <CitationBridge citation={report.scorecard?.citation} url={finalUrl} />
      </div>

      <SectionTitle>Priority fixes — highest score gain first</SectionTitle>
      <div style={{ marginBottom: 28 }}>
        <FindingsList findings={fixes} fixes={fixMap} url={finalUrl} impacts={impacts} />
      </div>

      {/* per-pillar tabs — dev detail, collapsed by default */}
      <div ref={checksRef} style={{ scrollMarginTop: 16 }}>
        <button
          onClick={() => setShowAllChecks((v) => !v)}
          style={{
            width: "100%",
            display: "flex",
            alignItems: "center",
            gap: 10,
            padding: "12px 14px",
            border: "1px solid var(--border)",
            borderRadius: 10,
            background: "var(--surface)",
            cursor: "pointer",
            color: "var(--text)",
            fontSize: 13,
            fontWeight: 500,
            marginBottom: showAllChecks ? 14 : 0,
          }}
        >
          <span style={{ flex: 1, textAlign: "left" }}>All checks by pillar — what passed and what to fix</span>
          <span style={{ fontSize: 12, color: "var(--text-3)", fontFamily: "var(--mono)" }}>{allFindings.length} checks</span>
          <span style={{ fontSize: 12, color: "var(--text-3)", transform: showAllChecks ? "rotate(180deg)" : "none", transition: "transform 0.15s ease" }}>⌄</span>
        </button>
        {showAllChecks && (
          <>
        <div style={{ display: "flex", gap: 8, margin: "0 0 14px", flexWrap: "wrap" }}>
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
        <FindingsList key={section.key} findings={sectionFindings} fixes={fixMap} url={finalUrl} openFirst={false} impacts={impacts} />
          </>
        )}
      </div>
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <div style={{ fontSize: 13, color: "var(--text)", fontWeight: 500, marginBottom: 10 }}>{children}</div>;
}

function ShareButton({ token }: { token: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    // Unguessable capability link — the token (not the enumerable row id) grants access.
    const url = `${window.location.origin}/report?id=${token}`;
    try {
      await navigator.clipboard.writeText(url);
    } catch {
      /* clipboard blocked — the URL is still shareable from the address bar */
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1600);
  };
  return (
    <button
      onClick={copy}
      title="Copy a shareable link to this saved report"
      style={{ fontSize: 12.5, color: copied ? C.accent : "var(--text-2)", background: "transparent", border: "none", cursor: "pointer", padding: 0, whiteSpace: "nowrap" }}
    >
      {copied ? "✓ Link copied" : "🔗 Share"}
    </button>
  );
}

// Deterministic "everything to fix" export — copy or download a plain checklist of every issue
// + recommendation + ready-made fix. No AI; just compiles what the scan already found.
function FixesExport({
  report,
  url,
  findings,
  impacts,
}: {
  report: Report;
  url: string;
  findings: Finding[];
  impacts: Record<string, number>;
}) {
  const [copied, setCopied] = useState(false);
  const text = () => buildFixesText(report, url, findings, impacts);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text());
    } catch {
      /* clipboard blocked */
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1600);
  };

  const download = () => {
    const host = (() => {
      try {
        return new URL(url).hostname.replace(/^www\./, "");
      } catch {
        return "site";
      }
    })();
    const blob = new Blob([text()], { type: "text/markdown;charset=utf-8" });
    const href = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = href;
    a.download = `astova-fixes-${host}.md`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(href);
  };

  const linkStyle: React.CSSProperties = {
    fontSize: 12.5,
    color: C.accent,
    background: "transparent",
    border: "none",
    cursor: "pointer",
    padding: 0,
    whiteSpace: "nowrap",
  };

  return (
    <>
      <button onClick={copy} title="Copy every fix as a checklist" style={{ ...linkStyle, color: copied ? C.accent : "var(--text-2)" }}>
        {copied ? "✓ Copied" : "Copy fixes"}
      </button>
      <button onClick={download} title="Download every fix as a Markdown file" style={linkStyle}>
        Export fixes ↓
      </button>
    </>
  );
}
