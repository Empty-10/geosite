import { CONF } from "./types";

/** The verified-vs-measured legend shown atop a report — makes the grammar explicit. */
export function ConfidenceLegend() {
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 16, alignItems: "center" }}>
      {Object.values(CONF).map((c) => (
        <span
          key={c.label}
          style={{ display: "inline-flex", alignItems: "center", gap: 7, fontSize: 12, color: "var(--text-2)" }}
        >
          <span style={{ width: 7, height: 7, borderRadius: "50%", background: c.color }} />
          {c.label}
        </span>
      ))}
      <span style={{ fontSize: 11.5, color: "var(--text-3)" }}>
        Solid = read straight from the page. Measured = sampled, shown with a band.
      </span>
    </div>
  );
}
