"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { C } from "@/lib/tokens";
import { HeroScanDemo } from "./HeroScanDemo";

// Landing-page scan entry. Enter a URL → Scan → routes to the /report scan page, which shows the
// animated "scanning…" state then the score + full breakdown. (One scan, one place.)
export function HeroDemo() {
  const [url, setUrl] = useState("stripe.com");
  const router = useRouter();

  const scan = () => {
    const v = url.trim();
    if (!v) return;
    const withScheme = /^https?:\/\//i.test(v) ? v : `https://${v}`;
    router.push(`/report?url=${encodeURIComponent(withScheme)}`);
  };

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
        <span style={{ marginLeft: 8, fontSize: 12, color: "var(--text-3)", fontFamily: "var(--mono)" }}>live scan</span>
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
              border: `1px solid var(--border)`,
              borderRadius: 10,
              background: "var(--ink)",
            }}
          >
            <span style={{ fontSize: 14, color: "var(--text-3)", fontFamily: "var(--mono)" }}>https://</span>
            <input
              value={url.replace(/^https?:\/\//i, "")}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && scan()}
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
            onClick={scan}
            style={{
              fontSize: 14,
              fontWeight: 500,
              border: "none",
              padding: "0 20px",
              height: 46,
              borderRadius: 10,
              cursor: "pointer",
              flexShrink: 0,
              background: C.accent,
              color: C.ink,
            }}
          >
            Scan
          </button>
        </div>

        <HeroScanDemo />
        <div style={{ textAlign: "center", fontSize: 12, color: "var(--text-3)", marginTop: 12 }}>
          Live preview · run your own scan above — verified score, 20-row scorecard, and every fix.
        </div>
      </div>
    </div>
  );
}
