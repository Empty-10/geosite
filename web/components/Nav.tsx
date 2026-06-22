import { Logo } from "./Logo";

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
        background: "rgba(13,15,18,0.72)",
        backdropFilter: "blur(12px)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <Logo />
        <span style={{ fontSize: 17, fontWeight: 500, letterSpacing: "-0.01em" }}>damask</span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 28 }}>
        <a style={linkStyle}>Product</a>
        <a style={linkStyle}>Pricing</a>
        <a style={linkStyle}>Agencies</a>
        <a style={linkStyle}>Docs</a>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
        <a style={linkStyle}>Sign in</a>
        <button
          style={{
            fontSize: 14,
            fontWeight: 500,
            color: "var(--ink)",
            background: "var(--accent)",
            border: "none",
            padding: "9px 16px",
            borderRadius: 8,
            cursor: "pointer",
          }}
        >
          Start free scan
        </button>
      </div>
    </nav>
  );
}
