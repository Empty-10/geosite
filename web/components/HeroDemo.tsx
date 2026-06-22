"use client";

import { useEffect, useRef, useState } from "react";
import { C, scoreColor } from "@/lib/tokens";

const MODULE_NAMES = [
  "Technical crawl",
  "On-page structure",
  "GEO readiness",
  "Performance",
  "Schema & metadata",
  "AI crawler access",
];

const PILLARS: [string, number][] = [
  ["Technical", 92],
  ["On-page", 81],
  ["GEO readiness", 58],
  ["Performance", 74],
];

const FINDINGS = [
  {
    id: 0,
    sevLabel: "Critical",
    sevColor: C.fail,
    title: "No llms.txt or AI crawler policy found",
    evidence:
      "GET /llms.txt → 404\nGET /robots.txt → 200 (no AI directives)\nNo Google-Extended or GPTBot rules present.",
    recommendation:
      "Publish an llms.txt at the root declaring which paths AI engines may use, and add explicit allow/deny rules for GPTBot, ClaudeBot and Google-Extended in robots.txt.",
  },
  {
    id: 1,
    sevLabel: "High",
    sevColor: C.warn,
    title: "Thin content on 14 high-intent pages",
    evidence:
      "14 pages < 180 words of unique body copy.\n/pricing, /integrations, /compare/* most affected.\nAvg. extractable answer length: 42 words.",
    recommendation:
      "Expand each page with a direct, self-contained answer block near the top. AI engines cite passages that fully answer the prompt without needing surrounding context.",
  },
  {
    id: 2,
    sevLabel: "Medium",
    sevColor: C.measured,
    title: "Schema markup missing on product pages",
    evidence:
      "0 of 38 product URLs expose Product or FAQPage schema.\nNo Organization or sameAs entity graph detected.",
    recommendation:
      "Add Product and FAQPage JSON-LD to product templates and a single Organization entity sitewide so engines can resolve your brand entity confidently.",
  },
];

const SCORE_TARGET = 84;
const RING_R = 50;
const RING_CIRC = 2 * Math.PI * RING_R;

function rgba(hex: string, a: number): string {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
}

type Phase = "idle" | "scanning" | "done";

export function HeroDemo() {
  const [url, setUrl] = useState("acme.com");
  const [phase, setPhase] = useState<Phase>("idle");
  const [score, setScore] = useState(0);
  const [moduleStatus, setModuleStatus] = useState<number[]>([0, 0, 0, 0, 0, 0]);
  const [expanded, setExpanded] = useState(0);

  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);
  const raf = useRef<number | null>(null);

  function clearTimers() {
    timers.current.forEach((t) => clearTimeout(t));
    timers.current = [];
    if (raf.current) cancelAnimationFrame(raf.current);
  }
  useEffect(() => clearTimers, []);

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

  function onScan() {
    if (phase === "scanning") return;
    clearTimers();
    setPhase("scanning");
    setScore(0);
    setModuleStatus([0, 0, 0, 0, 0, 0]);
    setExpanded(0);

    const n = MODULE_NAMES.length;
    for (let i = 0; i < n; i++) {
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
    }
    const total = 120 + n * 300 + 320;
    timers.current.push(
      setTimeout(() => {
        setPhase("done");
        countUp(SCORE_TARGET, 650);
      }, total),
    );
  }

  const isIdle = phase === "idle";
  const isScanning = phase === "scanning";
  const isDone = phase === "done";
  const ringOffset = RING_CIRC * (1 - score / 100);

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
            {isScanning ? "Scanning…" : isDone ? "Re-scan" : "Scan"}
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
              6 modules · deterministic technical engine · ~2 seconds
            </span>
          </div>
        )}

        {isScanning && (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {MODULE_NAMES.map((name, i) => {
              const st = moduleStatus[i];
              const running = st === 1;
              const done = st === 2;
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
                    {done ? "✓" : ""}
                  </div>
                  <span style={{ flex: 1, fontSize: 14, color: done ? C.text2 : running ? C.text : C.text3 }}>
                    {name}
                  </span>
                  <span style={{ fontSize: 12, color: "var(--text-3)", fontFamily: "var(--mono)" }}>
                    {done ? "done" : running ? "scanning…" : "queued"}
                  </span>
                </div>
              );
            })}
          </div>
        )}

        {isDone && (
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
              <span style={{ color: "var(--accent)" }}>●</span> 6 modules complete · scanned in 2.3s
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
                {PILLARS.map(([label, value]) => (
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
                    }}
                  >
                    <span style={{ fontSize: 12, color: "var(--text-2)" }}>{label}</span>
                    <span style={{ fontSize: 22, fontWeight: 500, letterSpacing: "-0.01em" }}>{value}</span>
                    <div style={{ height: 4, borderRadius: 99, background: "var(--border)", overflow: "hidden" }}>
                      <div style={{ height: "100%", width: `${value}%`, background: scoreColor(value), borderRadius: 99 }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>

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
                  Measured
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
                ±6% · n=240 prompts · 2026-06-20
              </span>
            </div>

            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
              <span style={{ fontSize: 13, color: "var(--text)", fontWeight: 500 }}>Priority fixes</span>
              <span style={{ fontSize: 12, color: "var(--text-3)" }}>3 of 11 shown</span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {FINDINGS.map((f) => {
                const open = expanded === f.id;
                return (
                  <div
                    key={f.id}
                    style={{ border: "1px solid var(--border)", borderRadius: 11, background: "var(--ink)", overflow: "hidden" }}
                  >
                    <div
                      onClick={() => setExpanded(open ? -1 : f.id)}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 12,
                        padding: "12px 14px",
                        cursor: "pointer",
                        borderLeft: `3px solid ${f.sevColor}`,
                      }}
                    >
                      <span
                        style={{
                          fontSize: 11,
                          color: f.sevColor,
                          border: `1px solid ${rgba(f.sevColor, 0.35)}`,
                          background: rgba(f.sevColor, 0.1),
                          padding: "2px 8px",
                          borderRadius: 6,
                          flexShrink: 0,
                        }}
                      >
                        {f.sevLabel}
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
                        <span style={{ width: 6, height: 6, borderRadius: "50%", background: C.accent }} />
                        Verified
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
                        <div style={{ fontSize: 11, color: "var(--text-3)", marginBottom: 6 }}>Recommendation</div>
                        <p style={{ fontSize: 13, color: "var(--text-2)", marginBottom: 12 }}>{f.recommendation}</p>
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
          </div>
        )}
      </div>
    </div>
  );
}
