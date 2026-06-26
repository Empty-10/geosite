"use client";

import { useRef, useState } from "react";
import { C } from "@/lib/tokens";
import { ToolNav } from "./ToolNav";
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
  const [domain, setDomain] = useState("");
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

  const connectCloudflare = async (d: string) => {
    if (!d.trim()) return;
    setState({ phase: "analyzing" });
    try {
      const res = await fetch("/api/cloudflare-logs", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ domain: d }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.error || `Couldn't connect (${res.status}).`);
      // Cloudflare-side problems (bad scope, wrong zone) surface as 200 + meta.error.
      if (data?.meta?.error) throw new Error(data.meta.error);
      setState({ phase: "done", report: data });
    } catch (e) {
      setState({ phase: "error", message: e instanceof Error ? e.message : "Couldn't connect to Cloudflare." });
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
      <ToolNav active="crawlers" />

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
              background: state.phase === "analyzing" || !text.trim() ? "var(--raised)" : C.accent,
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

        {/* Cloudflare connector — no upload, pulls analytics for a domain you proxy via Cloudflare. */}
        <div
          style={{
            border: "1px solid var(--border)",
            borderRadius: 12,
            background: "var(--surface)",
            padding: "16px 16px 14px",
            marginBottom: 24,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
            <span style={{ fontSize: 13.5, color: "var(--text)", fontWeight: 500 }}>Or connect Cloudflare</span>
            <span style={{ fontSize: 11, color: "var(--text-3)" }}>— no upload, pulls the last 7 days</span>
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <div
              style={{
                flex: 1,
                minWidth: 220,
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "0 12px",
                height: 42,
                border: "1px solid var(--border)",
                borderRadius: 9,
                background: "var(--ink)",
              }}
            >
              <span style={{ fontSize: 13, color: "var(--text-3)", fontFamily: "var(--mono)" }}>domain</span>
              <input
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && connectCloudflare(domain)}
                placeholder="acme.com"
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
              onClick={() => connectCloudflare(domain)}
              disabled={state.phase === "analyzing" || !domain.trim()}
              style={{
                fontSize: 14,
                fontWeight: 500,
                border: "1px solid var(--border-strong)",
                padding: "0 18px",
                height: 42,
                borderRadius: 9,
                cursor: state.phase === "analyzing" || !domain.trim() ? "default" : "pointer",
                background: "transparent",
                color: "var(--text)",
              }}
            >
              Connect Cloudflare
            </button>
          </div>
          <div style={{ fontSize: 11.5, color: "var(--text-3)", marginTop: 10, lineHeight: 1.5 }}>
            Needs the domain on your Cloudflare account and the API token granted{" "}
            <span style={{ color: "var(--text-2)" }}>Zone → Read</span> +{" "}
            <span style={{ color: "var(--text-2)" }}>Analytics → Read</span>.
          </div>
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
