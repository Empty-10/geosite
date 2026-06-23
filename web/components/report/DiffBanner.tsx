// "Since last scan" change banner. Reads report.meta.diff (attached by the engine when scan
// history is enabled) — score delta + resolved / regressed / new findings. Renders nothing when
// there's no prior scan to compare against (persistence off, or first scan of a URL).

import { C } from "@/lib/tokens";
import { rgba } from "./types";

type Change = { id: string; title: string; status?: string };
type Diff = {
  since?: string | null;
  score_delta: number;
  pillar_deltas?: Record<string, number>;
  resolved: Change[];
  regressed: Change[];
  new_issues: Change[];
};

export function DiffBanner({ meta }: { meta?: Record<string, unknown> }) {
  const diff = meta?.diff as Diff | undefined;
  if (!diff) return null;

  const { score_delta, resolved, regressed, new_issues, since } = diff;
  const sinceLabel = since ? new Date(since).toLocaleDateString() : "last scan";
  const none = score_delta === 0 && !resolved.length && !regressed.length && !new_issues.length;
  const deltaColor = score_delta > 0 ? C.accent : score_delta < 0 ? C.fail : C.text3;
  const deltaText = score_delta > 0 ? `+${score_delta}` : `${score_delta}`;

  return (
    <div
      style={{
        border: "1px solid var(--border)",
        borderRadius: 12,
        background: "var(--surface)",
        padding: "12px 14px",
        marginBottom: 18,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: none ? 0 : 10 }}>
        <span style={{ fontSize: 12.5, color: "var(--text-2)" }}>Since {sinceLabel}</span>
        <span
          style={{
            fontSize: 12.5,
            fontFamily: "var(--mono)",
            color: deltaColor,
            border: `1px solid ${rgba(deltaColor, 0.35)}`,
            background: rgba(deltaColor, 0.1),
            padding: "1px 8px",
            borderRadius: 999,
          }}
        >
          {deltaText} pts
        </span>
        {none && <span style={{ fontSize: 12.5, color: "var(--text-3)" }}>· no changes</span>}
      </div>
      {!none && (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {resolved.length > 0 && <Group label="Resolved" color={C.accent} items={resolved} />}
          {regressed.length > 0 && <Group label="Regressed" color={C.fail} items={regressed} />}
          {new_issues.length > 0 && <Group label="New issues" color={C.warn} items={new_issues} />}
        </div>
      )}
    </div>
  );
}

function Group({ label, color, items }: { label: string; color: string; items: Change[] }) {
  return (
    <div style={{ display: "flex", gap: 8, alignItems: "baseline", fontSize: 12.5 }}>
      <span style={{ color, fontWeight: 500, whiteSpace: "nowrap" }}>
        {label} ({items.length})
      </span>
      <span style={{ color: "var(--text-3)", lineHeight: 1.5 }}>{items.map((i) => i.title).join(" · ")}</span>
    </div>
  );
}
