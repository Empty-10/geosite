import { Logo } from "./Logo";

const linkStyle: React.CSSProperties = { fontSize: 13, color: "var(--text-3)", cursor: "pointer", textDecoration: "none" };

export function Footer() {
  return (
    <footer
      style={{
        padding: "36px 32px",
        borderTop: "1px solid var(--border)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        flexWrap: "wrap",
        gap: 16,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <Logo size={18} />
        <span style={{ fontSize: 14, color: "var(--text-2)" }}>damask</span>
        <span style={{ fontSize: 13, color: "var(--text-3)", marginLeft: 8 }}>© 2026 · GEO, measured honestly</span>
      </div>
      <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
        <a style={linkStyle} href="/report">Scan a page</a>
        <a style={linkStyle} href="/compare">Compare</a>
        <a style={linkStyle} href="/crawlers">Crawler logs</a>
        <a style={linkStyle} href="/visibility">AI visibility</a>
      </div>
    </footer>
  );
}
