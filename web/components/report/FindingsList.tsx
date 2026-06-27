"use client";

import { useState } from "react";
import { C } from "@/lib/tokens";
import { AiDraftBlock } from "./AiDraftBlock";
import { FixBlock } from "./FixBlock";
import { conf, effortOf, GENERATIVE_FINDINGS, rgba, sev, type Finding, type Fix } from "./types";

const STATUS: Record<string, { label: string; color: string }> = {
  fail: { label: "Fail", color: C.fail },
  warn: { label: "Warn", color: C.warn },
  pass: { label: "Pass", color: C.accent },
  info: { label: "Info", color: C.text3 },
};

function statusOf(s: string) {
  return STATUS[s] ?? STATUS.info;
}

/**
 * Expandable findings list — click a row to reveal Evidence + Recommendation in place
 * (no modals, per the design brief). Used for the priority-fix list and per-pillar checks.
 * Parents that swap the `findings` set (e.g. pillar tabs) should pass a `key` to remount.
 */
export function FindingsList({ findings, fixes = {}, url, openFirst = true, impacts = {} }: {
  findings: Finding[];
  fixes?: Record<string, Fix>;
  url?: string; // when set, generative findings get an on-demand "Draft with AI" button
  openFirst?: boolean;
  impacts?: Record<string, number>; // finding id → headline points gained if fixed
}) {
  const [expanded, setExpanded] = useState<string | null>(openFirst ? findings[0]?.id ?? null : null);

  if (findings.length === 0) {
    return (
      <div
        style={{
          padding: "16px 14px",
          border: "1px solid var(--border)",
          borderRadius: 11,
          background: "var(--ink)",
          fontSize: 13,
          color: "var(--text-2)",
        }}
      >
        No failing or warning checks here — this section passes the deterministic audit.
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {findings.map((f) => {
        const open = expanded === f.id;
        const issue = f.status === "fail" || f.status === "warn";
        const st = statusOf(f.status);
        const s = sev(f.severity);
        const cf = conf(f.confidence);
        return (
          <div
            key={f.id}
            style={{ border: "1px solid var(--border)", borderRadius: 11, background: "var(--ink)", overflow: "hidden" }}
          >
            <div
              onClick={() => setExpanded(open ? null : f.id)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 12,
                padding: "12px 14px",
                cursor: "pointer",
                borderLeft: `3px solid ${st.color}`,
              }}
            >
              {issue ? (
                <span
                  style={{
                    fontSize: 11,
                    color: s.color,
                    border: `1px solid ${rgba(s.color, 0.35)}`,
                    background: rgba(s.color, 0.1),
                    padding: "2px 8px",
                    borderRadius: 6,
                    flexShrink: 0,
                  }}
                >
                  {s.label}
                </span>
              ) : (
                <span
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6,
                    fontSize: 11,
                    color: "var(--text-3)",
                    flexShrink: 0,
                    width: 56,
                  }}
                >
                  <span style={{ width: 6, height: 6, borderRadius: "50%", background: st.color }} />
                  {st.label}
                </span>
              )}
              <span style={{ flex: 1, fontSize: 13.5, color: "var(--text)" }}>{f.title}</span>
              {issue && impacts[f.id] > 0 && (
                <span
                  title="Estimated gain to your readiness score if fixed"
                  style={{ fontSize: 11.5, color: C.accent, fontFamily: "var(--mono)", flexShrink: 0 }}
                >
                  +{impacts[f.id]}
                </span>
              )}
              {issue && (
                <span
                  style={{
                    fontSize: 11,
                    color: "var(--text-3)",
                    border: "1px solid var(--border)",
                    borderRadius: 6,
                    padding: "2px 7px",
                    flexShrink: 0,
                  }}
                >
                  {effortOf(f.id).label}
                </span>
              )}
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                  fontSize: 11,
                  color: "var(--text-2)",
                  flexShrink: 0,
                }}
              >
                <span style={{ width: 6, height: 6, borderRadius: "50%", background: cf.color }} />
                {cf.label}
              </span>
              <span
                style={{
                  fontSize: 13,
                  color: "var(--text-3)",
                  transform: open ? "rotate(180deg)" : "rotate(0deg)",
                  transition: "transform 0.15s ease",
                }}
              >
                ⌄
              </span>
            </div>
            {open && (
              <div style={{ padding: "0 14px 14px 17px", animation: "dmFade 0.15s ease both" }}>
                {f.evidence && (
                  <>
                    <div style={{ fontSize: 11, color: "var(--text-3)", margin: "4px 0 6px" }}>Evidence</div>
                    <pre
                      style={{
                        fontSize: 12,
                        color: "var(--text-2)",
                        fontFamily: "var(--mono)",
                        background: "var(--surface)",
                        border: "1px solid var(--border)",
                        borderRadius: 8,
                        padding: "10px 12px",
                        whiteSpace: "pre-wrap",
                        marginBottom: 12,
                      }}
                    >
                      {f.evidence}
                    </pre>
                  </>
                )}
                {f.recommendation && (
                  <>
                    <div style={{ fontSize: 11, color: "var(--text-3)", marginBottom: 6 }}>Recommendation</div>
                    <p style={{ fontSize: 13, color: "var(--text-2)", marginBottom: 12 }}>{f.recommendation}</p>
                  </>
                )}
                {!f.evidence && !f.recommendation && (
                  <p style={{ fontSize: 13, color: "var(--text-3)", margin: "8px 0 12px" }}>
                    This check passed — nothing to fix.
                  </p>
                )}
                {issue && fixes[f.id] && <FixBlock fix={fixes[f.id]} />}
                {issue && !fixes[f.id] && url && GENERATIVE_FINDINGS.has(f.id) && (
                  <AiDraftBlock url={url} findingId={f.id} />
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
