"use client";

import { useEffect, useRef, useState } from "react";
import { C, scoreColor } from "@/lib/tokens";

// Visual scan steps. The engine runs three deterministic modules (technical, on-page, GEO
// readiness); the rest are surfaced here as roadmap so the full pillar set is visible.
// PERF_INDEX is shown as "not in this scan" — Performance is a later phase, never faked.
const MODULE_NAMES = [
  "Technical crawl",
  "On-page structure",
  "GEO readiness",
  "Performance",
  "Schema & metadata",
  "AI crawler access",
];
const PERF_INDEX = 3;

// Pillar cards map onto the engine's pillar_scores keys. Pillars absent from a scan
// (Performance isn't in the first slice) render as a "not run yet" state, not a number.
const PILLAR_CARDS: { label: string; key: string }[] = [
  { label: "Technical", key: "technical" },
  { label: "On-page", key: "onpage" },
  { label: "GEO readiness", key: "geo" },
  { label: "Performance", key: "performance" },
];

// severity → badge label + colour + sort rank (lower = more urgent).
const SEV: Record<string, { label: string; color: string; rank: number }> = {
  critical: { label: "Critical", color: C.fail, rank: 0 },
  high: { label: "High", color: C.fail, rank: 1 },
  medium: { label: "Medium", color: C.warn, rank: 2 },
  low: { label: "Low", color: C.measured, rank: 3 },
  info: { label: "Info", color: C.text3, rank: 4 },
};

// confidence → badge. The accuracy principle made visible: solid green = verified fact.
const CONF: Record<string, { label: string; color: string }> = {
  verified: { label: "Verified", color: C.accent },
  measured: { label: "Measured", color: C.measured },
  estimated: { label: "Estimated", color: C.warn },
};

const RING_R = 50;
const RING_CIRC = 2 * Math.PI * RING_R;
const MIN_SCAN_MS = 1900; // let the module ticks read even when the engine returns sooner

type Finding = {
  id: string;
  pillar: string;
  title: string;
  status: string;
  severity: string;
  confidence: string;
  value: unknown;
  evidence: string | null;
  recommendation: string | null;
};

type Report = {
  url: string;
  fetched_at: string;
  overall_score: number;
  pillar_scores: Record<string, number>;
  meta: Record<string, unknown>;
  findings: Finding[];
};

function rgba(hex: string, a: number): string {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
}

function sev(s: string) {
  return SEV[s] ?? SEV.info;
}
function conf(c: string) {
  return CONF[c] ?? CONF.verified;
}

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

type Phase = "idle" | "scanning" | "done" | "error";

export function HeroDemo() {
  const [url, setUrl] = useState("stripe.com");
  const [phase, setPhase] = useState<Phase>("idle");
  const [score, setScore] = useState(0);
  const [moduleStatus, setModuleStatus] = useState<number[]>(() =>
    MODULE_NAMES.map((_, i) => (i === PERF_INDEX ? 3 : 0)),
  );
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [expanded, setExpanded] = useState<string | null>(null);

  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);
  const raf = useRef<number | null>(null);
  const runId = useRef(0);
  const abortRef = useRef<AbortController | null>(null);

  function clearTimers() {
    timers.current.forEach((t) => clearTimeout(t));
    timers.current = [];
    if (raf.current) cancelAnimationFrame(raf.current);
  }
  useEffect(() => {
    return () => {
      clearTimers();
      abortRef.current?.abort();
    };
  }, []);

  function countUp(target: number, dur: number) {
    const start = performance.now();
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / dur);
      const eased = 1 - Math.pow(1 - t, 3);
      setScore(Math.round(target * eased));
      if (t < 1) raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
  }

  function startModuleAnimation() {
    setModuleStatus(MODULE_NAMES.map((_, i) => (i === PERF_INDEX ? 3 : 0)));
    MODULE_NAMES.forEach((_, i) => {
      if (i === PERF_INDEX) return; // stays "not run"
      timers.current.push(
        setTimeout(() => {
          setModuleStatus((ms) => {
            const next = [...ms];
            next[i] = 1;
            return next;
          });
        }, 120 + i * 300),
      );
      timers.current.push(
        setTimeout(() => {
          setModuleStatus((ms) => {
            const next = [...ms];
            next[i] = 2;
            return next;
          });
        }, 120 + i * 300 + 260),
      );
    });
  }

  async function onScan() {
    if (phase === "scanning") return;
    clearTimers();
    abortRef.current?.abort();
    const myRun = ++runId.current;
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    setPhase("scanning");
    setScore(0);
    setReport(null);
    setError(null);
    setExpanded(null);
    startModuleAnimation();

    const started = performance.now();
    try {
      const res = await fetch("/api/scan", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ url }),
        signal: ctrl.signal,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.error || `Scan failed (${res.status}).`);

      await delay(Math.max(0, MIN_SCAN_MS - (performance.now() - started)));
      if (runId.current !== myRun) return; // a newer scan superseded this one

      const fixes = priorityFixes(data.findings ?? []);
      setReport(data);
      setElapsedMs(performance.now() - started);
      setExpanded(fixes[0]?.id ?? null);
      setPhase("done");
      countUp(typeof data.overall_score === "number" ? data.overall_score : 0, 650);
    } catch (e) {
      if (runId.current !== myRun || ctrl.signal.aborted) return;
      setError(e instanceof Error ? e.message : "Something went wrong.");
      setPhase("error");
    }
  }

  const isIdle = phase === "idle";
  const isScanning = phase === "scanning";
  const isDone = phase === "done";
  const isError = phase === "error";
  const ringOffset = RING_CIRC * (1 - score / 100);

  const fixes = report ? priorityFixes(report.findings) : [];
  const modulesRun = MODULE_NAMES.length - 1; // Performance is not run in the first slice
  const buttonLabel = isScanning ? "Scanning…" : isDone ? "Re-scan" : isError ? "Retry" : "Scan";

  return (
    <div
      style={{
        border: "1px solid var(--border)",
        borderRadius: 16,
        background: "var(--surface)",
        overflow: "hidden",
        boxShadow: "0 24px 60px -20px rgba(0,0,0,0.6)",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "12px 16px",
          borderBottom: "1px solid var(--border)",
          background: "var(--raised)",
        }}
      >
        {[0, 1, 2].map((i) => (
          <div key={i} style={{ width: 10, height: 10, borderRadius: "50%", background: "var(--border-strong)" }} />
        ))}
        <span style={{ marginLeft: 8, fontSize: 12, color: "var(--text-3)", fontFamily: "var(--mono)" }}>
          live scan
        </span>
      </div>

      <div style={{ padding: 20 }}>
        <div style={{ display: "flex", gap: 10, marginBottom: 18 }}>
          <div
            style={{
              flex: 1,
              display: "flex",
              alignItems: "center",
              gap: 10,
              padding: "0 14px",
              height: 46,
              border: `1px solid ${isScanning ? C.borderStrong : C.border}`,
              borderRadius: 10,
              background: "var(--ink)",
            }}
          >
            <span style={{ fontSize: 14, color: "var(--text-3)", fontFamily: "var(--mono)" }}>https://</span>
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") onScan();
              }}
              placeholder="your-site.com"
              style={{
                flex: 1,
                background: "transparent",
                border: "none",
                outline: "none",
                color: "var(--text)",
                fontSize: 14,
                fontFamily: "var(--mono)",
              }}
            />
          </div>
          <button
            onClick={onScan}
            style={{
              fontSize: 14,
              fontWeight: 500,
              border: "none",
              padding: "0 20px",
              height: 46,
              borderRadius: 10,
              cursor: isScanning ? "default" : "pointer",
              flexShrink: 0,
              background: isScanning ? C.raised : C.accent,
              color: isScanning ? C.text3 : C.ink,
            }}
          >
            {buttonLabel}
          </button>
        </div>

        {isIdle && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: 10,
              height: 300,
              border: "1px dashed var(--border)",
              borderRadius: 12,
              textAlign: "center",
              padding: 24,
            }}
          >
            <div
              style={{
                width: 40,
                height: 40,
                border: "1.5px solid var(--border-strong)",
                borderRadius: "50%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <div
                style={{
                  width: 14,
                  height: 14,
                  border: "1.5px solid var(--text-3)",
                  borderRadius: "50%",
                  borderTopColor: "transparent",
                  transform: "rotate(45deg)",
                }}
              />
            </div>
            <span style={{ fontSize: 14, color: "var(--text-2)" }}>Enter a URL and run a scan</span>
            <span style={{ fontSize: 12.5, color: "var(--text-3)", maxWidth: 280 }}>
              Deterministic technical engine · live, verified results
            </span>
          </div>
        )}

        {isError && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: 10,
              height: 300,
              border: `1px solid ${rgba(C.fail, 0.4)}`,
              borderRadius: 12,
              textAlign: "center",
              padding: 24,
              background: rgba(C.fail, 0.06),
            }}
          >
            <div
              style={{
                width: 40,
                height: 40,
                border: `1.5px solid ${rgba(C.fail, 0.6)}`,
                borderRadius: "50%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: C.fail,
                fontSize: 20,
              }}
            >
              !
            </div>
            <span style={{ fontSize: 14, color: "var(--text)" }}>Couldn&apos;t complete the scan</span>
            <span style={{ fontSize: 12.5, color: "var(--text-3)", maxWidth: 320 }}>{error}</span>
          </div>
        )}

        {isScanning && (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {MODULE_NAMES.map((name, i) => {
              const st = moduleStatus[i];
              const running = st === 1;
              const done = st === 2;
              const notRun = st === 3;
              return (
                <div
                  key={name}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 12,
                    padding: "11px 14px",
                    border: "1px solid var(--border)",
                    borderRadius: 10,
                    background: "var(--raised)",
                    opacity: notRun ? 0.55 : 1,
                  }}
                >
                  <div
                    style={{
                      width: 20,
                      height: 20,
                      borderRadius: "50%",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 11,
                      flexShrink: 0,
                      background: done ? rgba(C.accent, 0.14) : C.raised,
                      border: `1.5px solid ${done ? C.accent : running ? C.measured : C.borderStrong}`,
                      color: done ? C.accent : C.text3,
                      animation: running
                        ? "dmPulse 1s ease infinite"
                        : done
                          ? "dmTick 0.3s ease both"
                          : undefined,
                    }}
                  >
                    {done ? "✓" : notRun ? "–" : ""}
                  </div>
                  <span style={{ flex: 1, fontSize: 14, color: done ? C.text2 : running ? C.text : C.text3 }}>
                    {name}
                  </span>
                  <span style={{ fontSize: 12, color: "var(--text-3)", fontFamily: "var(--mono)" }}>
                    {done ? "done" : running ? "scanning…" : notRun ? "not in this scan" : "queued"}
                  </span>
                </div>
              );
            })}
          </div>
        )}

        {isDone && report && (
          <div style={{ animation: "dmFade 0.4s ease both" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                fontSize: 12,
                color: "var(--text-3)",
                marginBottom: 16,
                fontFamily: "var(--mono)",
              }}
            >
              <span style={{ color: "var(--accent)" }}>●</span> {modulesRun} modules complete · scanned in{" "}
              {(elapsedMs / 1000).toFixed(1)}s
            </div>

            <div style={{ display: "flex", gap: 16, alignItems: "stretch", marginBottom: 14 }}>
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 6,
                  padding: "18px 22px",
                  border: "1px solid var(--border)",
                  borderRadius: 12,
                  background: "var(--ink)",
                }}
              >
                <div style={{ position: "relative", width: 116, height: 116 }}>
                  <svg width={116} height={116} viewBox="0 0 116 116" style={{ transform: "rotate(-90deg)" }}>
                    <circle cx={58} cy={58} r={RING_R} fill="none" stroke={C.border} strokeWidth={9} />
                    <circle
                      cx={58}
                      cy={58}
                      r={RING_R}
                      fill="none"
                      stroke={scoreColor(score)}
                      strokeWidth={9}
                      strokeLinecap="round"
                      strokeDasharray={RING_CIRC}
                      strokeDashoffset={ringOffset}
                    />
                  </svg>
                  <div
                    style={{
                      position: "absolute",
                      inset: 0,
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    <span style={{ fontSize: 34, fontWeight: 500, letterSpacing: "-0.02em", lineHeight: 1 }}>
                      {score}
                    </span>
                    <span style={{ fontSize: 11, color: "var(--text-3)" }}>/ 100</span>
                  </div>
                </div>
                <span style={{ fontSize: 12.5, color: "var(--text-2)" }}>Overall GEO score</span>
              </div>

              <div style={{ flex: 1, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                {PILLAR_CARDS.map(({ label, key }) => {
                  const value = report.pillar_scores[key];
                  const ran = typeof value === "number";
                  return (
                    <div
                      key={label}
                      style={{
                        padding: "12px 14px",
                        border: "1px solid var(--border)",
                        borderRadius: 11,
                        background: "var(--ink)",
                        display: "flex",
                        flexDirection: "column",
                        gap: 8,
                        opacity: ran ? 1 : 0.6,
                      }}
                    >
                      <span style={{ fontSize: 12, color: "var(--text-2)" }}>{label}</span>
                      {ran ? (
                        <>
                          <span style={{ fontSize: 22, fontWeight: 500, letterSpacing: "-0.01em" }}>{value}</span>
                          <div style={{ height: 4, borderRadius: 99, background: "var(--border)", overflow: "hidden" }}>
                            <div
                              style={{ height: "100%", width: `${value}%`, background: scoreColor(value), borderRadius: 99 }}
                            />
                          </div>
                        </>
                      ) : (
                        <>
                          <span style={{ fontSize: 13, fontWeight: 500, color: "var(--text-3)" }}>Not run yet</span>
                          <span style={{ fontSize: 11, color: "var(--text-3)", fontFamily: "var(--mono)" }}>
                            later phase
                          </span>
                        </>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Preview of the MEASURED citation module (later phase). Static sample data — not a
                measurement of the scanned site. Kept visually so the verified/measured grammar reads. */}
            <div
              style={{
                padding: "14px 16px",
                border: "1px solid var(--border)",
                borderRadius: 12,
                background: "var(--ink)",
                marginBottom: 16,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
                <span style={{ fontSize: 12.5, color: "var(--text-2)" }}>AI answer-engine visibility</span>
                <span
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6,
                    fontSize: 11,
                    color: C.measured,
                    border: `1px solid ${rgba(C.measured, 0.35)}`,
                    background: rgba(C.measured, 0.1),
                    padding: "3px 9px",
                    borderRadius: 999,
                  }}
                >
                  <span style={{ width: 5, height: 5, borderRadius: "50%", background: C.measured }} />
                  Measured · sample
                </span>
              </div>
              <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: 10 }}>
                <span style={{ fontSize: 26, fontWeight: 500 }}>23%</span>
                <span style={{ fontSize: 13, color: "var(--text-3)" }}>citation share</span>
              </div>
              <div style={{ position: "relative", height: 8, borderRadius: 99, background: "var(--border)", marginBottom: 8 }}>
                <div
                  style={{
                    position: "absolute",
                    left: "17%",
                    width: "12%",
                    top: 0,
                    bottom: 0,
                    background: rgba(C.measured, 0.45),
                    borderRadius: 99,
                  }}
                />
                <div
                  style={{ position: "absolute", left: "23%", top: -2, width: 2, height: 12, background: C.measured, borderRadius: 2 }}
                />
              </div>
              <span style={{ fontSize: 11.5, color: "var(--text-3)", fontFamily: "var(--mono)" }}>
                example output · citation sampling arrives in a later phase
              </span>
            </div>

            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
              <span style={{ fontSize: 13, color: "var(--text)", fontWeight: 500 }}>Priority fixes</span>
              <span style={{ fontSize: 12, color: "var(--text-3)" }}>
                {Math.min(3, fixes.length)} of {fixes.length} shown
              </span>
            </div>
            {fixes.length === 0 ? (
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
                No failing or warning checks — this page passes the deterministic GEO-readiness audit.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {fixes.slice(0, 3).map((f) => {
                  const open = expanded === f.id;
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
                          borderLeft: `3px solid ${s.color}`,
                        }}
                      >
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
                        <span style={{ flex: 1, fontSize: 13.5, color: "var(--text)" }}>{f.title}</span>
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
                          <button
                            style={{
                              fontSize: 12.5,
                              fontWeight: 500,
                              color: C.accent,
                              border: `1px solid ${rgba(C.accent, 0.4)}`,
                              background: rgba(C.accent, 0.12),
                              padding: "7px 13px",
                              borderRadius: 8,
                              cursor: "pointer",
                            }}
                          >
                            Generate fix
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/** Failing/warning findings, most urgent first — the actionable "priority fixes" list. */
function priorityFixes(findings: Finding[]): Finding[] {
  return findings
    .filter((f) => f.status === "fail" || f.status === "warn")
    .sort((a, b) => sev(a.severity).rank - sev(b.severity).rank);
}
