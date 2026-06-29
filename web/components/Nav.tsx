import { Logo } from "./Logo";
import { ThemeToggle } from "./ThemeToggle";

const linkStyle: React.CSSProperties = {
  fontSize: 14,
  color: "var(--text-2)",
  cursor: "pointer",
  textDecoration: "none",
};

export function Nav() {
  return (
    <nav
      style={{
        position: "sticky",
        top: 0,
        zIndex: 50,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "16px 32px",
        borderBottom: "1px solid var(--border)",
        background: "var(--nav-bg)",
        backdropFilter: "blur(12px)",
        WebkitBackdropFilter: "blur(12px)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <Logo />
        <span style={{ fontSize: 17, fontWeight: 500, letterSpacing: "-0.01em" }}>Astova</span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 28 }}>
        <a style={linkStyle} href="/#product">Product</a>
        <a style={linkStyle} href="/agents">For agents</a>
        <a style={linkStyle} href="/mcp">MCP</a>
        <a style={linkStyle} href="/#pricing">Pricing</a>
        <a style={linkStyle} href="/#agencies">Agencies</a>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
        <ThemeToggle />
        <a style={linkStyle} href="/crawlers">Crawler logs</a>
        <a style={linkStyle} href="/login">Sign in</a>
        <a
          href="/report"
          style={{
            fontSize: 14,
            fontWeight: 500,
            color: "var(--on-accent)",
            background: "var(--accent)",
            border: "none",
            padding: "9px 16px",
            borderRadius: 8,
            cursor: "pointer",
            textDecoration: "none",
            display: "inline-block",
          }}
        >
          Start free scan
        </a>
      </div>
    </nav>
  );
}
