"use client";

import { useState } from "react";
import { C } from "@/lib/tokens";
import { rgba, type Fix } from "./types";

type Phase = "idle" | "loading" | "done" | "error";

/**
 * On-demand "Draft with AI" for judgment-dependent findings. Calls POST /api/fix (the metered,
 * Claude-backed endpoint) and shows the draft fenced off as AI-drafted — never as a verified fact.
 */
export function AiDraftBlock({ url, findingId }: { url: string; findingId: string }) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [fix, setFix] = useState<Fix | null>(null);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  async function draft() {
    setPhase("loading");
    setError("");
    try {
      const res = await fetch("/api/fix", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ url, findingId }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.error || `Drafting failed (${res.status}).`);
      setFix(data);
      setPhase("done");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Drafting failed.");
      setPhase("error");
    }
  }

  async function copy() {
    if (!fix) return;
    try {
      await navigator.clipboard.writeText(fix.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable */
    }
  }

  if (phase === "done" && fix) {
    return (
      <div style={{ marginTop: 12, animation: "dmFade 0.15s ease both" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              fontSize: 11,
              color: C.warn,
              border: `1px solid ${rgba(C.warn, 0.35)}`,
              background: rgba(C.warn, 0.1),
              padding: "3px 9px",
              borderRadius: 999,
            }}
          >
            <span style={{ width: 5, height: 5, borderRadius: "50%", background: C.warn }} />
            Drafted by Claude — review before publishing
          </span>
          <button
            onClick={copy}
            style={{
              fontSize: 11,
              color: copied ? C.accent : "var(--text-2)",
              border: "1px solid var(--border-strong)",
              background: "transparent",
              padding: "3px 10px",
              borderRadius: 6,
              cursor: "pointer",
            }}
          >
            {copied ? "Copied ✓" : "Copy"}
          </button>
        </div>
        <pre
          style={{
            fontSize: 12.5,
            color: "var(--text)",
            fontFamily: fix.kind === "markdown" ? "inherit" : "var(--mono)",
            background: "var(--surface)",
            border: `1px solid ${rgba(C.warn, 0.25)}`,
            borderRadius: 8,
            padding: "12px 14px",
            whiteSpace: "pre-wrap",
            margin: 0,
          }}
        >
          {fix.content}
        </pre>
        {fix.note && (
          <p style={{ fontSize: 11.5, color: "var(--text-3)", marginTop: 8 }}>{fix.note}</p>
        )}
      </div>
    );
  }

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <button
        onClick={draft}
        disabled={phase === "loading"}
        style={{
          fontSize: 12.5,
          fontWeight: 500,
          color: C.warn,
          border: `1px solid ${rgba(C.warn, 0.4)}`,
          background: rgba(C.warn, 0.12),
          padding: "7px 13px",
          borderRadius: 8,
          cursor: phase === "loading" ? "default" : "pointer",
        }}
      >
        {phase === "loading" ? "Drafting…" : "Draft with AI"}
      </button>
      {phase === "error" && <span style={{ fontSize: 11.5, color: C.fail }}>{error}</span>}
    </div>
  );
}
