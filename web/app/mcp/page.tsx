import type { Metadata } from "next";

import { Nav } from "@/components/Nav";
import { Footer } from "@/components/Footer";
import { McpSetupView } from "@/components/McpSetupView";

export const metadata: Metadata = {
  title: "Use Astova with your AI coding agent (MCP setup)",
  description:
    "Set up the Astova MCP with Claude, Cursor, ChatGPT, Windsurf or a generic MCP client: install + config " +
    "steps, the recommended entrypoints, a copyable starter prompt, the safe workflow and every Astova tool.",
  alternates: { canonical: "/mcp" },
};

export default function McpPage() {
  return (
    <main style={{ minHeight: "100vh" }}>
      <Nav />
      <McpSetupView />
      <Footer />
    </main>
  );
}
