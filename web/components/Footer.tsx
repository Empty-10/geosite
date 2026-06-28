import { Logo } from "./Logo";

const link: React.CSSProperties = { fontSize: 13, color: "var(--text-3)", textDecoration: "none", display: "block", marginBottom: 9 };
const colTitle: React.CSSProperties = { fontSize: 12, color: "var(--text-2)", marginBottom: 13, fontWeight: 500 };

export function Footer() {
  return (
    <footer style={{ borderTop: "1px solid var(--border)", padding: "48px 32px 36px" }}>
      <div style={{ maxWidth: 1100, margin: "0 auto", display: "flex", gap: 40, flexWrap: "wrap", justifyContent: "space-between" }}>
        <div style={{ maxWidth: 280 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
            <Logo size={18} />
            <span style={{ fontSize: 15, fontWeight: 500 }}>Astova</span>
          </div>
          <p style={{ fontSize: 13, color: "var(--text-3)", lineHeight: 1.55 }}>
            GEO/AEO readiness, measured honestly. See how AI engines read your site — and fix it.
          </p>
        </div>

        <div style={{ display: "flex", gap: 56, flexWrap: "wrap" }}>
          <div>
            <div style={colTitle}>Product</div>
            <a style={link} href="/report">Page report</a>
            <a style={link} href="/compare">Compare</a>
            <a style={link} href="/crawlers">Crawler logs</a>
            <a style={link} href="/visibility">AI visibility</a>
          </div>
          <div>
            <div style={colTitle}>Explore</div>
            <a style={link} href="/#product">Product</a>
            <a style={link} href="/#pricing">Pricing</a>
            <a style={link} href="/#faq">FAQ</a>
          </div>
        </div>
      </div>

      <div style={{ maxWidth: 1100, margin: "28px auto 0", paddingTop: 20, borderTop: "1px solid var(--border)", fontSize: 12.5, color: "var(--text-3)" }}>
        © 2026 Astova · GEO, measured honestly
      </div>
    </footer>
  );
}
