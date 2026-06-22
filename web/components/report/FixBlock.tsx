"use client";

import { useState } from "react";
import { C } from "@/lib/tokens";
import { rgba, type Fix } from "./types";

/** "Generate fix": reveals the deterministically-generated artifact with copy-to-clipboard. */
export function FixBlock({ fix }: { fix: Fix }) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  async function copy() {
    let ok = false;
    try {
      await navigator.clipboard.writeText(fix.content);
      ok = true;
    } catch {
      // Fallback for blocked/unavailable async clipboard (older or non-secure contexts).
      try {
        const ta = document.createElement("textarea");
        ta.value = fix.content;
        ta.style.position = "fixed";
        ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.select();
        ok = document.execCommand("copy");
        document.body.removeChild(ta);
      } catch {
        ok = false;
      }
    }
    if (ok) {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    }
  }

  return (
    <div>
      <button
        onClick={() => setOpen((o) => !o)}
        style={{
          fontSize: 12.5,
          fontWeight: 500,
          color: C.accent,
          border: `1px solid ${rgba(C.accent, 0.4)}`,
          background: rgba(C.accent, 0.12),
          padding: "7px 13px",
          borderRadius: 8,
          cursor: "pointer",
        }}
      >
        {open ? "Hide fix" : "Generate fix"}
      </button>

      {open && (
        <div style={{ marginTop: 12, animation: "dmFade 0.15s ease both" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
            <span style={{ fontSize: 11.5, color: "var(--text-3)" }}>
              {fix.title} · <span style={{ fontFamily: "var(--mono)" }}>{fix.kind}</span>
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
              fontSize: 12,
              color: "var(--text-2)",
              fontFamily: "var(--mono)",
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              padding: "10px 12px",
              whiteSpace: "pre-wrap",
              overflowX: "auto",
              maxHeight: 280,
              overflowY: "auto",
              margin: 0,
            }}
          >
            {fix.content}
          </pre>
          {fix.note && (
            <p style={{ fontSize: 11.5, color: "var(--text-3)", marginTop: 8 }}>{fix.note}</p>
          )}
        </div>
      )}
    </div>
  );
}
