"use client";

import { useState } from "react";

import { QA } from "@/lib/faq";

export function Faq() {
  const [open, setOpen] = useState<number | null>(0);
  return (
    <section id="faq" style={{ padding: "80px 32px", borderTop: "1px solid var(--border)", scrollMarginTop: 72 }}>
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
