"use client";

// /mcp - human view of the Astova MCP usage guide. The content is fetched from /api/mcp-guide
// (which proxies the engine's mcp_usage_guide source of truth) - nothing is duplicated here.

import { useEffect, useState } from "react";
import { C } from "@/lib/tokens";
import { CopyBlock } from "@/components/CopyBlock";

type Entrypoint = { tool: string; when_to_use: string };
type Tool = { tool: string; description: string };
type Guide = {
  client: string;
  purpose: string;
  recommended_entrypoints: Entrypoint[];
  setup: string[];
  starter_prompt: string;
  workflow: string[];
  safety_rules: string[];
  available_tools: Tool[];
  error?: string;
};

const CLIENTS: { id: string; label: string }[] = [
  { id: "generic", label: "Generic" },
  { id: "claude", label: "Claude" },
  { id: "cursor", label: "Cursor" },
  { id: "chatgpt", label: "ChatGPT" },
  { id: "windsurf", label: "Windsurf" },
];

// Pull the MCP server config JSON out of a setup step so it gets its own Copy button - derived from
// the guide, never hardcoded.
function extractConfig(setup: string[]): string | null {
  for (const step of setup) {
    const i = step.indexOf('{"mcpServers"');
    if (i >= 0) {
      const j = step.lastIndexOf("}");
      if (j > i) return step.slice(i, j + 1);
    }
  }
  return null;
}

const h2: React.CSSProperties = { fontSize: 18, fontWeight: 600, margin: "32px 0 10px" };
const li: React.CSSProperties = { color: "var(--text-2)", lineHeight: 1.6, marginBottom: 6 };

export function McpSetupView() {
  const [client, setClient] = useState("generic");
  const [guide, setGuide] = useState<Guide | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetch(`/api/mcp-guide?client=${encodeURIComponent(client)}`)
      .then((r) => r.json())
      .then((data: Guide) => {
        if (cancelled) return;
        if (data.error) setError(data.error);
        else setGuide(data);
      })
      .catch((e) => !cancelled && setError(e instanceof Error ? e.message : "Could not load the guide."))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [client]);

  const config = guide ? extractConfig(guide.setup) : null;

  return (
    <article style={{ maxWidth: 780, margin: "0 auto", padding: "56px 20px 80px", color: "var(--text)" }}>
      <h1 style={{ fontSize: 30, fontWeight: 700, margin: "0 0 12px" }}>
        Use Astova with your AI coding agent
      </h1>
      <p style={{ color: "var(--text-2)", lineHeight: 1.6, margin: "0 0 8px", fontSize: 17 }}>
        Astova provides the AI Readiness expertise. Your AI agent applies the changes. Astova verifies the
        result - deterministically, with no LLM guesswork.
      </p>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", margin: "24px 0 4px" }}>
        {CLIENTS.map((c) => {
          const active = c.id === client;
          return (
            <button
              key={c.id}
              onClick={() => setClient(c.id)}
              style={{
                padding: "8px 16px", borderRadius: 999, fontSize: 14, fontWeight: 600, cursor: "pointer",
                border: `1px solid ${active ? C.accent : "var(--border)"}`,
                background: active ? C.accent : "var(--surface)",
                color: active ? "var(--ink)" : "var(--text)",
              }}
            >
              {c.label}
            </button>
          );
        })}
      </div>

      {loading && <p style={{ color: "var(--text-3)", marginTop: 24 }}>Loading guide...</p>}

      {error && (
        <div style={{ padding: 14, borderRadius: 10, border: `1px solid ${C.warn}`, background: "rgba(224,162,43,0.1)", color: "var(--text)", marginTop: 24 }}>
          {error}
        </div>
      )}

      {guide && !error && (
        <section>
          <h2 style={h2}>Purpose</h2>
          <p style={{ color: "var(--text-2)", lineHeight: 1.6 }}>{guide.purpose}</p>

          <h2 style={h2}>Recommended entrypoints</h2>
          <ul style={{ paddingLeft: 18, margin: 0 }}>
            {guide.recommended_entrypoints.map((e) => (
              <li key={e.tool} style={li}>
                <code>{e.tool}</code> - {e.when_to_use}
              </li>
            ))}
          </ul>

          <h2 style={h2}>Setup</h2>
          <ol style={{ paddingLeft: 18, margin: 0 }}>
            {guide.setup.map((step, i) => (
              <li key={i} style={li}>{step}</li>
            ))}
          </ol>
          {config && <CopyBlock text={config} label="MCP server config" />}

          <h2 style={h2}>Starter prompt</h2>
          <p style={{ color: "var(--text-3)", fontSize: 13, margin: "0 0 4px" }}>
            Paste this into {CLIENTS.find((c) => c.id === client)?.label} once Astova is connected.
          </p>
          <CopyBlock text={guide.starter_prompt} label="starter prompt" />

          <h2 style={h2}>Workflow</h2>
          <ol style={{ paddingLeft: 18, margin: 0 }}>
            {guide.workflow.map((w, i) => (
              <li key={i} style={li}>{w}</li>
            ))}
          </ol>

          <h2 style={h2}>Safety rules</h2>
          <ul style={{ paddingLeft: 18, margin: 0 }}>
            {guide.safety_rules.map((r, i) => (
              <li key={i} style={li}>{r}</li>
            ))}
          </ul>

          <h2 style={h2}>Available tools</h2>
          <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "grid", gap: 8 }}>
            {guide.available_tools.map((t) => (
              <li key={t.tool} style={{ border: `1px solid var(--border)`, borderRadius: 10, background: "var(--surface)", padding: "10px 14px" }}>
                <code style={{ color: C.accent, fontSize: 13 }}>{t.tool}</code>
                <div style={{ color: "var(--text-2)", fontSize: 13, lineHeight: 1.5, marginTop: 2 }}>{t.description}</div>
              </li>
            ))}
          </ul>
        </section>
      )}
    </article>
  );
}
