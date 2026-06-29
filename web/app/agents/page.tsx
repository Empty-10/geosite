import type { Metadata } from "next";

import { Nav } from "@/components/Nav";
import { Footer } from "@/components/Footer";
import { CopyBlock } from "@/components/CopyBlock";

export const metadata: Metadata = {
  title: "Use Astova with your AI coding agent",
  description:
    "A one-minute setup for Claude, Cursor, ChatGPT or Windsurf: run Astova to audit AI Readiness, let " +
    "your agent apply the fixes, then run Astova again to verify. Copy the prompt, CLI commands and MCP " +
    "starter instruction.",
  alternates: { canonical: "/agents" },
};

const AGENT_PROMPT =
  "Use Astova to make this project AI Ready. Run `astova loop .`, review the top actions, apply only the " +
  "safe deterministic or clearly instructed changes, then run `astova loop .` again to verify improvement. " +
  "Do not invent facts, business claims, author names, sameAs links, opening hours, addresses, legal claims " +
  "or data points. For any item marked manual or human review required, ask me before editing.";

const MCP_INSTRUCTION =
  "Use the Astova MCP. Start with `ai_ready_loop` for this project. For each issue, call `explain_finding`. " +
  "If a deterministic fix exists, call `generate_fix`. After you apply changes, call `verify_fix`.";

const sectionStyle: React.CSSProperties = { margin: "0 0 40px" };
const h2Style: React.CSSProperties = { fontSize: 20, fontWeight: 600, margin: "0 0 12px" };
const pStyle: React.CSSProperties = { color: "var(--text-2)", lineHeight: 1.6, margin: "0 0 8px" };

export default function AgentsPage() {
  return (
    <main style={{ minHeight: "100vh" }}>
      <Nav />

      <article style={{ maxWidth: 760, margin: "0 auto", padding: "56px 20px 80px", color: "var(--text)" }}>
        <header style={sectionStyle}>
          <h1 style={{ fontSize: 30, fontWeight: 700, margin: "0 0 12px" }}>
            Use Astova with your AI coding agent
          </h1>
          <p style={{ ...pStyle, fontSize: 17 }}>
            Astova audits your site or project for AI Readiness. Your AI coding agent applies the fixes.
            Astova then verifies the result - deterministically, with no guesswork. Copy one prompt or
            command below and you are set up with Claude, Cursor, ChatGPT, Windsurf or any agent.
          </p>
        </header>

        <section style={sectionStyle}>
          <h2 style={h2Style}>The loop</h2>
          <ol style={{ ...pStyle, paddingLeft: 20, margin: 0 }}>
            <li style={{ marginBottom: 6 }}>
              Run <code>astova loop .</code> to get a prioritised action plan for the project.
            </li>
            <li style={{ marginBottom: 6 }}>
              Give the Markdown action plan to your AI agent and let it apply the safe changes.
            </li>
            <li>
              Run <code>astova loop .</code> again after the changes to verify the score improved.
            </li>
          </ol>
        </section>

        <section style={sectionStyle}>
          <h2 style={h2Style}>Copy this prompt to your agent</h2>
          <p style={pStyle}>
            Paste this into Claude, Cursor, ChatGPT or Windsurf while it has your project open.
          </p>
          <CopyBlock text={AGENT_PROMPT} label="agent prompt" />
        </section>

        <section style={sectionStyle}>
          <h2 style={h2Style}>CLI commands</h2>
          <p style={pStyle}>Run these from your project root after installing the engine.</p>
          <CopyBlock text="astova check ." label="scan this project" />
          <CopyBlock text="astova loop ." label="prioritised action plan" />
          <CopyBlock
            text="astova export . --output astova-action-plan.md"
            label="write the plan to a file for your agent"
          />
        </section>

        <section style={sectionStyle}>
          <h2 style={h2Style}>Using the MCP</h2>
          <p style={pStyle}>
            With the Astova MCP connected to your agent, paste this to kick off the loop with the tools
            directly.
          </p>
          <CopyBlock text={MCP_INSTRUCTION} label="MCP starter instruction" />
        </section>

        <section
          style={{
            ...sectionStyle,
            border: "1px solid var(--border)",
            borderRadius: 12,
            background: "var(--surface)",
            padding: "18px 20px",
          }}
        >
          <h2 style={{ ...h2Style, marginBottom: 10 }}>Safety</h2>
          <ul style={{ ...pStyle, paddingLeft: 20, margin: 0 }}>
            <li style={{ marginBottom: 6 }}>Astova does not apply changes automatically.</li>
            <li style={{ marginBottom: 6 }}>Your AI agent edits the code; Astova only diagnoses and verifies.</li>
            <li style={{ marginBottom: 6 }}>
              Astova provides deterministic evidence, fixes where possible, and verification - never an
              LLM guess.
            </li>
            <li>
              Human review is required for factual, legal, business identity and local-business claims
              (names, addresses, hours, sameAs links, data points).
            </li>
          </ul>
        </section>
      </article>

      <Footer />
    </main>
  );
}
