"use client";

// A small reusable "copy this" block: monospace content + a Copy button. Used on the /agents
// onboarding page for the prompt, CLI commands and MCP starter instruction. No logic beyond clipboard.

import { useState } from "react";
import { C } from "@/lib/tokens";

export function CopyBlock({ text, label }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div style={{ margin: "12px 0" }}>
      {label && (
        <div style={{ fontSize: 12, color: "var(--text-3)", marginBottom: 6, fontFamily: "var(--mono)" }}>
          {label}
        </div>
      )}
      <div
        style={{
          position: "relative",
          border: "1px solid var(--border)",
          borderRadius: 10,
          background: "var(--ink)",
          padding: "14px 80px 14px 16px",
        }}
      >
        <pre
          style={{
            margin: 0,
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
            fontFamily: "var(--mono)",
            fontSize: 13,
            lineHeight: 1.6,
            color: "var(--text)",
          }}
        >
          {text}
        </pre>
        <button
          onClick={copy}
          aria-label="Copy to clipboard"
          style={{
            position: "absolute",
            top: 10,
            right: 10,
            fontSize: 12,
            fontWeight: 600,
            padding: "6px 12px",
            borderRadius: 8,
            border: `1px solid ${C.border}`,
            background: copied ? C.accent : C.raised,
            color: copied ? C.ink : C.text,
            cursor: "pointer",
          }}
        >
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
    </div>
  );
}
