"use client";

import { useRef, useState } from "react";
import { C } from "@/lib/tokens";
import { Logo } from "../Logo";
import { FindingsList } from "./FindingsList";
import { rgba } from "./types";
import { CATEGORY, type BotActivity, type LogReport } from "./logTypes";

const SAMPLE = `Paste access-log lines (Combined Log Format), e.g.
1.2.3.4 - - [10/Oct/2025:13:55:36 +0000] "GET /guide HTTP/1.1" 200 5234 "-" "Mozilla/5.0 (compatible; GPTBot/1.1; +https://openai.com/gptbot)"`;

type State =
  | { phase: "empty" }
  | { phase: "analyzing" }
  | { phase: "error"; message: string }
  | { phase: "done"; report: LogReport };

function cat(c: string) {
  return CATEGORY[c] ?? { label: c, color: C.text3 };
}

export function LogReportView() {
  const [text, setText] = useState("");
  const [state, setState] = useState<State>({ phase: "empty" });
  const fileRef = useRef<HTMLInputElement>(null);

  const analyze = async (logText: string, source: string) => {
    if (!logText.trim()) return;
    setState({ phase: "analyzing" });
    try {
      const res = await fetch("/api/logs", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ text: logText, source }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.error || `Analysis failed (${res.status}).`);
      setState({ phase: "done", report: data });
    } catch (e) {
      setState({ phase: "error", message: e instanceof Error ? e.message : "Something went wrong." });
    }
  };

  const onFile = (file: File) => {
    const reader = new FileReader();
    reader.onload = () => {
      const content = String(reader.result ?? "");
      setText(content.slice(0, 200_000)); // preview cap; full content is sent on analyze
      analyze(content, file.name);
    };
    reader.readAsText(file);
  };

  return (
    <div style={{ minHeight: "100vh", background: "var(--ink)" }}>
      <header
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          padding: "16px 24px",
          borderBottom: "1px solid var(--border)",
          background: "var(--surface)",
        }}
      >
        <a href="/" style={{ display: "inline-flex", alignItems: "center", gap: 10, color: "var(--text)" }}>
          <Logo size={20} />
          <span style={{ fontSize: 15, fontWeight: 500, letterSpacing: "-0.01em" }}>damask</span>
        </a>
        <span style={{ marginLeft: "auto", fontSize: 12, color: "var(--text-3)", fontFamily: "var(--mono)" }}>
          AI crawler logs
        </span>
      </header>

      <main style={{ maxWidth: 920, margin: "0 auto", padding: "24px 20px 80px" }}>
        <h1 style={{ fontSize: 22, fontWeight: 500, letterSpacing: "-0.02em", marginBottom: 6 }}>
          AI crawler-log analysis
        </h1>
        <p style={{ fontSize: 14, color: "var(--text-2)", marginBottom: 18, maxWidth: 640, lineHeight: 1.6 }}>
          Paste or upload your server access log to see which AI crawlers actually visited — GPTBot, ClaudeBot,
          PerplexityBot and more — what they read, and what errored. Every number is read straight from the log
          (<span style={{ color: C.accent }}>verified</span>).
        </p>

        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={SAMPLE}
          spellCheck={false}
          style={{
            width: "100%",
            minHeight: 160,
            resize: "vertical",
            padding: "12px 14px",
            borderRadius: 10,
            border: "1px solid var(--border)",
            background: "var(--surface)",
            color: "var(--text)",
            fontSize: 12.5,
            fontFamily: "var(--mono)",
            lineHeight: 1.5,
            outline: "none",
          }}
        />

        <div style={{ display: "flex", gap: 10, alignItems: "center", margin: "12px 0 24px" }}>
          <button
            onClick={() => analyze(text, "pasted log")}
            disabled={state.phase === "analyzing" || !text.trim()}
            style={{
              fontSize: 14,
              fontWeight: 500,
              border: "none",
              padding: "0 20px",
              height: 44,
              borderRadius: 10,
              cursor: state.phase === "analyzing" || !text.trim() ? "default" : "pointer",
              background: state.phase === "analyzing" || !text.trim() ? C.raised : C.accent,
              color: state.phase === "analyzing" || !text.trim() ? C.text3 : C.ink,
            }}
          >
            {state.phase === "analyzing" ? "Analyzing…" : "Analyze log"}
          </button>
          <button
            onClick={() => fileRef.current?.click()}
            style={{
              fontSize: 14,
              fontWeight: 500,
              border: "1px solid var(--border-strong)",
              padding: "0 18px",
              height: 44,
              borderRadius: 10,
              cursor: "pointer",
              background: "transparent",
              color: "var(--text-2)",
            }}
          >
            Upload file
          </button>
          <input
            ref={fileRef}
            type="file"
            accept=".log,.txt,text/plain"
            style={{ display: "none" }}
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) onFile(f);
              e.target.value = "";
            }}
          />
          <span style={{ fontSize: 12, color: "var(--text-3)" }}>Combined Log Format · nothing is stored</span>
        </div>

        {state.phase === "error" && (
          <div
            style={{
              padding: "18px",
              border: `1px solid ${rgba(C.fail, 0.4)}`,
              borderRadius: 12,
              background: rgba(C.fail, 0.06),
              color: "var(--text-2)",
              fontSize: 14,
            }}
          >
            <strong style={{ color: "var(--text)" }}>Couldn&apos;t analyze that log.</strong>
            <div style={{ marginTop: 6, color: "var(--text-3)" }}>{state.message}</div>
          </div>
        )}

        {state.phase === "done" && <LogBody report={state.report} />}
      </main>
    </div>
  );
}

function LogBody({ report }: { report: LogReport }) {
  const m = report.meta;
  const [from, to] = m.date_range ?? [null, null];
  const fmt = (s: string | null) => (s ? new Date(s).toLocaleString() : "?");

  return (
    <div style={{ animation: "dmFade 0.3s ease both" }}>
      <div style={{ fontSize: 12.5, color: "var(--text-3)", fontFamily: "var(--mono)", marginBottom: 18 }}>
        {m.ai_requests ?? 0} AI-crawler requests · {m.lines_parsed ?? 0} log lines · {from || to ? `${fmt(from)} → ${fmt(to)}` : "no timestamps"}
        {m.lines_truncated ? ` · truncated ${m.lines_truncated} lines` : ""}
      </div>

      <SectionTitle>Findings</SectionTitle>
      <div style={{ marginBottom: 26 }}>
        <FindingsList findings={report.findings} openFirst={false} />
      </div>

      <SectionTitle>AI crawlers seen ({report.bots.length})</SectionTitle>
      {report.bots.length > 0 ? (
        <BotsTable bots={report.bots} />
      ) : (
        <div
          style={{
            padding: "16px 14px",
            border: "1px solid var(--border)",
            borderRadius: 11,
            background: "var(--ink)",
            fontSize: 13,
            color: "var(--text-2)",
          }}
        >
          No known AI crawlers appear in this log window.
        </div>
      )}
    </div>
  );
}

function BotsTable({ bots }: { bots: BotActivity[] }) {
  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: 12, overflow: "hidden" }}>
      {bots.map((b, i) => {
        const c = cat(b.category);
        return (
          <div
            key={b.name}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              padding: "12px 14px",
              borderTop: i === 0 ? "none" : "1px solid var(--border)",
              background: "var(--surface)",
            }}
          >
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 13.5, color: "var(--text)", fontWeight: 500 }}>{b.name}</span>
                <span
                  style={{
                    fontSize: 10.5,
                    color: c.color,
                    border: `1px solid ${rgba(c.color, 0.4)}`,
                    background: rgba(c.color, 0.1),
                    padding: "1px 7px",
                    borderRadius: 999,
                  }}
                >
                  {c.label}
                </span>
              </div>
              <div style={{ fontSize: 11.5, color: "var(--text-3)", marginTop: 2 }}>{b.operator}</div>
            </div>
            <Metric value={b.hits} label="hits" />
            <Metric value={b.paths} label="paths" />
            <Metric value={b.errors} label="errors" bad={b.errors > 0} />
          </div>
        );
      })}
    </div>
  );
}

function Metric({ value, label, bad = false }: { value: number; label: string; bad?: boolean }) {
  return (
    <div style={{ width: 58, textAlign: "right", flexShrink: 0 }}>
      <div style={{ fontSize: 15, fontFamily: "var(--mono)", color: bad ? C.fail : "var(--text)" }}>{value}</div>
      <div style={{ fontSize: 10.5, color: "var(--text-3)" }}>{label}</div>
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <div style={{ fontSize: 13, color: "var(--text)", fontWeight: 500, marginBottom: 10 }}>{children}</div>;
}
