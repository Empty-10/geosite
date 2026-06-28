import { C } from "@/lib/tokens";

// The unbeatable differentiator: damask runs as an MCP server, so you can audit a URL from
// inside ChatGPT / Claude. Two columns — pitch left, a chat/terminal block right.

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
          <span style={{ fontSize: 13, color: "var(--accent)" }}>Built different</span>
          <h2 style={{ fontSize: 30, fontWeight: 500, letterSpacing: "-0.02em", margin: "12px 0 14px", lineHeight: 1.12 }}>
            Audit from inside ChatGPT &amp; Claude.
          </h2>
          <p style={{ fontSize: 16, color: "var(--text-2)", textWrap: "pretty", lineHeight: 1.55, marginBottom: 16 }}>
            damask ships as an <span style={{ color: "var(--accent)", fontStyle: "italic" }}>MCP server</span>. Connect
            it once and ask your assistant to audit any URL — it calls the real deterministic engine and reasons over the
            scorecard. No pasted HTML, no LLM guesswork. No other GEO tool lives where you already work.
          </p>
          <div style={{ fontSize: 13, color: "var(--text-3)", fontFamily: "var(--mono)" }}>
            Works in claude.ai · Claude Desktop · ChatGPT
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
        <span style={{ marginLeft: 8, fontSize: 12, color: "var(--text-3)", fontFamily: "var(--mono)" }}>claude · damask connector</span>
      </div>
      <div style={{ padding: 16, fontFamily: "var(--mono)", fontSize: 12.5, lineHeight: 1.7 }}>
        <div style={{ color: "var(--text-2)" }}>
          <span style={{ color: "var(--text-3)" }}>You ·</span> Audit stripe.com for AI visibility.
        </div>
        <div style={{ color: "var(--text-3)", margin: "8px 0" }}>
          Claude → <span style={{ color: "var(--measured)" }}>damask.audit_url</span>(&quot;https://stripe.com&quot;)
        </div>
        <div style={{ background: "var(--ink)", border: "1px solid var(--border)", borderRadius: 8, padding: "10px 12px", color: "var(--text-2)" }}>
          <div>
            AI Retrievability: <span style={{ color: C.accent, fontWeight: 600 }}>78/100</span> <span style={{ color: "var(--text-3)" }}>· verified</span>
          </div>
          <div style={{ marginTop: 6, color: C.warn }}>✗ Front-loaded answer — buried at ~280 words</div>
          <div style={{ color: C.warn }}>✗ FAQ schema — missing</div>
          <div style={{ color: C.accent }}>✓ AI crawler access — GPTBot served 200</div>
        </div>
      </div>
    </div>
  );
}
