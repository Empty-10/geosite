"use client";

// Expert Schema Review summary - turns the deeper schema.* findings into a focused review card
// (status + counts + the issue list) rather than leaving them as flat rows. Derived entirely from
// the report (findings + generated fixes); no extra fetch.

import { C } from "@/lib/tokens";
import { fixesByFinding, type Finding, type Report } from "./types";

const SEV_COLOR: Record<string, string> = {
  critical: C.fail, high: C.fail, medium: C.warn, low: "var(--text-3)", info: "var(--text-3)",
};

export function SchemaReviewCard({ report }: { report: Report }) {
  const schema = report.findings.filter((f) => f.id.startsWith("schema."));
  if (!schema.length) return null;

  const issues = schema.filter((f) => f.status === "fail" || f.status === "warn");
  const critHigh = issues.filter((f) => f.severity === "critical" || f.severity === "high");
  const fixes = fixesByFinding(report);
  const deterministic = issues.filter((f) => fixes[f.id]);
  const manual = issues.length - deterministic.length;

  const hasFail = issues.some((f) => f.status === "fail");
  const status = !issues.length ? "Clean" : hasFail ? "Issues found" : "Needs review";
  const statusColor = !issues.length ? C.accent : hasFail ? C.fail : C.warn;

  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: 14, background: "var(--surface)", padding: 18, marginBottom: 24 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4, flexWrap: "wrap" }}>
        <h3 style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>Expert Schema Review</h3>
        <span style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: statusColor, border: `1px solid ${statusColor}`, borderRadius: 999, padding: "2px 8px" }}>
          {status}
        </span>
      </div>
      <div style={{ fontSize: 12.5, color: "var(--text-3)", marginBottom: 12 }}>
        A deterministic review of the page&apos;s structured data: entity duplication, identity conflicts,
        graph wiring, sameAs, Article relationships and URL/type hygiene.
      </div>

      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: issues.length ? 14 : 0 }}>
        <Stat label="Schema issues" value={issues.length} color="var(--text)" />
        <Stat label="Critical / high" value={critHigh.length} color={critHigh.length ? C.fail : "var(--text-3)"} />
        <Stat label="Deterministic fixes" value={deterministic.length} color={deterministic.length ? C.accent : "var(--text-3)"} />
        <Stat label="Manual review" value={manual} color={manual ? C.warn : "var(--text-3)"} />
      </div>

      {issues.length > 0 && (
        <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "grid", gap: 6 }}>
          {issues.map((f) => (
            <Row key={f.id} f={f} deterministic={!!fixes[f.id]} />
          ))}
        </ul>
      )}
    </div>
  );
}

function Stat({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: 10, background: "var(--ink)", padding: "8px 12px", minWidth: 92 }}>
      <div style={{ fontSize: 20, fontWeight: 700, color }}>{value}</div>
      <div style={{ fontSize: 11.5, color: "var(--text-2)" }}>{label}</div>
    </div>
  );
}

function Row({ f, deterministic }: { f: Finding; deterministic: boolean }) {
  return (
    <li style={{ display: "flex", gap: 8, alignItems: "baseline", flexWrap: "wrap", fontSize: 13, lineHeight: 1.45 }}>
      <span style={{ fontSize: 10.5, fontWeight: 700, textTransform: "uppercase", color: SEV_COLOR[f.severity] ?? "var(--text-3)", minWidth: 52 }}>
        {f.severity}
      </span>
      <span style={{ color: "var(--text)", fontWeight: 500 }}>{f.title}</span>
      <code style={{ fontSize: 11, color: "var(--text-3)" }}>{f.id}</code>
      <span style={{ marginLeft: "auto", fontSize: 11, color: deterministic ? C.accent : "var(--text-3)" }}>
        {deterministic ? "fix ready" : "manual"}
      </span>
    </li>
  );
}
