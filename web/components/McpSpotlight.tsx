import { C } from "@/lib/tokens";

// The unbeatable differentiator: astova runs as an MCP server, so your AI agent doesn't just
// audit a URL — it applies the fixes and re-audits to prove the score rose. "Fixes, not
// findings", live inside the tools you already work in. Two columns — pitch left, agent demo right.

export function McpSpotlight() {
  return (
    <section style={{ padding: "80px 32px", borderTop: "1px solid var(--border)" }}>
      <div
        style={{
          maxWidth: 1100,
          margin: "0 auto",
          display: "flex",
          gap: 40,
          alignItems: "center",
          flexWrap: "wrap",
        }}
      >
        <div style={{ flex: "1 1 360px", minWidth: 300 }}>
          <span style={{ fontSize: 13, color: "var(--accent)" }}>Fixes, not findings</span>
          <h2 style={{ fontSize: 30, fontWeight: 500, letterSpacing: "-0.02em", margin: "12px 0 14px", lineHeight: 1.12 }}>
            Let your AI agent fix it.
          </h2>
          <p style={{ fontSize: 16, color: "var(--text-2)", textWrap: "pretty", lineHeight: 1.55, marginBottom: 16 }}>
            Astova ships as an <span style={{ color: "var(--accent)", fontStyle: "italic" }}>MCP server</span>, so your
            assistant doesn&apos;t just <em>tell</em> you what&apos;s wrong — it audits the page against the real
            deterministic engine, then <span style={{ color: "var(--text)" }}>writes the schema, the{" "}
            <span style={{ fontFamily: "var(--mono)" }}>llms.txt</span>, the front-loaded intro</span> straight into your
            repo and re-audits to prove the score moved. Every other GEO tool stops at the finding.
          </p>
          <div style={{ fontSize: 13, color: "var(--text-3)", fontFamily: "var(--mono)" }}>
            Works in Claude Code · Cursor · Claude Desktop · claude.ai
          </div>
        </div>

        <div style={{ flex: "1 1 380px", minWidth: 300 }}>
          <ChatBlock />
        </div>
      </div>
    </section>
  );
}

function ChatBlock() {
  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: 14, background: "var(--surface)", overflow: "hidden", boxShadow: "0 24px 60px -28px rgba(0,0,0,0.5)" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 14px", borderBottom: "1px solid var(--border)", background: "var(--raised)" }}>
        {[0, 1, 2].map((i) => (
          <div key={i} style={{ width: 9, height: 9, borderRadius: "50%", background: "var(--border-strong)" }} />
        ))}
        <span style={{ marginLeft: 8, fontSize: 12, color: "var(--text-3)", fontFamily: "var(--mono)" }}>claude · Astova connector</span>
      </div>
      <div style={{ padding: 16, fontFamily: "var(--mono)", fontSize: 12.5, lineHeight: 1.7 }}>
        <div style={{ color: "var(--text-2)" }}>
          <span style={{ color: "var(--text-3)" }}>You ·</span> Audit my site and fix what&apos;s wrong.
        </div>
        <div style={{ color: "var(--text-3)", margin: "8px 0 6px" }}>
          Claude → <span style={{ color: "var(--measured)" }}>astova.fix_plan</span>(&quot;https://acme.com&quot;)
        </div>
        <div style={{ background: "var(--ink)", border: "1px solid var(--border)", borderRadius: 8, padding: "10px 12px", color: "var(--text-2)" }}>
          <div style={{ color: "var(--text-3)" }}>
            6 fixes ready <span style={{ color: "var(--text-3)" }}>· verified</span>
          </div>
          <div style={{ marginTop: 6, color: C.accent }}>+ JSON-LD Organization schema</div>
          <div style={{ color: C.accent }}>+ llms.txt</div>
          <div style={{ color: C.accent }}>+ front-load the answer (intro rewrite)</div>
        </div>
        <div style={{ color: "var(--text-2)", margin: "10px 0 6px" }}>
          <span style={{ color: "var(--text-3)" }}>Claude ·</span> Applied 6 fixes to your repo. Re-auditing…
        </div>
        <div style={{ color: "var(--text-3)" }}>
          astova → AI Retrievability{" "}
          <span style={{ color: "var(--text-3)" }}>71</span> →{" "}
          <span style={{ color: C.accent, fontWeight: 600 }}>89</span> ✓
        </div>
      </div>
    </div>
  );
}
