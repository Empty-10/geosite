"use client";

import { useState } from "react";

const QA = [
  {
    q: "What is damask?",
    a: "A GEO/AEO tool that scans your site the way AI answer engines do — then tells you exactly what to fix to be retrieved and cited. The technical audit is deterministic; every finding is read straight from your live pages.",
  },
  {
    q: "How is it different from a normal SEO tool?",
    a: "Most SEO suites bolt shallow AI features onto a ranking tool. damask is GEO-first and deterministic: a reproducible audit of the on-page factors that decide whether AI engines can retrieve and cite you — and it ships the fix, not just the finding.",
  },
  {
    q: "Which AI engines does it cover?",
    a: "The readiness audit applies to every AI crawler. Multi-engine visibility sampling covers ChatGPT, Perplexity and Gemini (with AI Overviews and Copilot on the roadmap), always shown as a measured range, never as false precision.",
  },
  {
    q: "How accurate is it?",
    a: "The technical and on-page checks are VERIFIED — read directly from your live HTML and reproducible on re-run. Sampled signals (AI citations) are labelled MEASURED and shown with a confidence band. We never present an estimate as a fact.",
  },
  {
    q: "Do I need to install anything?",
    a: "No — paste a URL and scan. Optionally, connect the MCP server so you can audit from inside ChatGPT or Claude, or (soon) install the WordPress plugin to apply fixes in one click.",
  },
  {
    q: "How much does it cost?",
    a: "A free single-page scan, no card required. Pro ($49/mo) adds full-site crawls, competitor benchmarks and all fixes. Agency ($199/mo) adds unlimited sites and white-label reports.",
  },
];

export function Faq() {
  const [open, setOpen] = useState<number | null>(0);
  return (
    <section style={{ padding: "80px 32px", borderTop: "1px solid var(--border)" }}>
      <div style={{ maxWidth: 760, margin: "0 auto" }}>
        <div style={{ textAlign: "center", marginBottom: 36 }}>
          <span style={{ fontSize: 13, color: "var(--accent)" }}>FAQ</span>
          <h2 style={{ fontSize: 30, fontWeight: 500, letterSpacing: "-0.02em", margin: "12px 0 0", lineHeight: 1.12 }}>
            Frequently asked questions.
          </h2>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {QA.map((item, i) => {
            const isOpen = open === i;
            return (
              <div key={item.q} style={{ border: "1px solid var(--border)", borderRadius: 12, background: "var(--surface)", overflow: "hidden" }}>
                <button
                  onClick={() => setOpen(isOpen ? null : i)}
                  style={{
                    width: "100%",
                    display: "flex",
                    alignItems: "center",
                    gap: 12,
                    padding: "16px 18px",
                    background: "transparent",
                    border: "none",
                    cursor: "pointer",
                    textAlign: "left",
                    color: "var(--text)",
                    fontSize: 15,
                    fontWeight: 500,
                  }}
                >
                  <span style={{ flex: 1 }}>{item.q}</span>
                  <span style={{ fontSize: 18, color: "var(--text-3)", transform: isOpen ? "rotate(45deg)" : "none", transition: "transform 0.15s ease", lineHeight: 1 }}>
                    +
                  </span>
                </button>
                {isOpen && (
                  <div style={{ padding: "0 18px 18px", fontSize: 14, color: "var(--text-2)", lineHeight: 1.6, animation: "dmFade 0.15s ease both" }}>
                    {item.a}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
