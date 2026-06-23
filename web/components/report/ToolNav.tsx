// Shared header for the working-tool screens (page report / site crawl / crawler logs), so a
// user can move between them. The active tool is highlighted.

import { C } from "@/lib/tokens";
import { Logo } from "../Logo";
import { rgba } from "./types";

const TOOLS = [
  { key: "report", href: "/report", label: "Page report" },
  { key: "site", href: "/site", label: "Site crawl" },
  { key: "crawlers", href: "/crawlers", label: "Crawler logs" },
  { key: "visibility", href: "/visibility", label: "AI visibility" },
] as const;

export function ToolNav({ active }: { active: "report" | "site" | "crawlers" | "visibility" }) {
  return (
    <header
      style={{
        display: "flex",
        alignItems: "center",
        gap: 16,
        padding: "13px 20px",
        borderBottom: "1px solid var(--border)",
        background: "var(--surface)",
        flexWrap: "wrap",
      }}
    >
      <a href="/" style={{ display: "inline-flex", alignItems: "center", gap: 10, color: "var(--text)" }}>
        <Logo size={20} />
        <span style={{ fontSize: 15, fontWeight: 500, letterSpacing: "-0.01em" }}>damask</span>
      </a>
      <nav style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
        {TOOLS.map((t) => {
          const isActive = t.key === active;
          return (
            <a
              key={t.key}
              href={t.href}
              aria-current={isActive ? "page" : undefined}
              style={{
                fontSize: 13,
                padding: "6px 12px",
                borderRadius: 8,
                whiteSpace: "nowrap",
                color: isActive ? C.accent : "var(--text-2)",
                background: isActive ? rgba(C.accent, 0.12) : "transparent",
                border: `1px solid ${isActive ? rgba(C.accent, 0.4) : "transparent"}`,
              }}
            >
              {t.label}
            </a>
          );
        })}
      </nav>
    </header>
  );
}
