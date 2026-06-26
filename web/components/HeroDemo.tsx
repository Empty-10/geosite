"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { C } from "@/lib/tokens";

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
          <span style={{ fontSize: 14, color: "var(--text-2)" }}>Enter a URL and run a deterministic GEO/SEO scan</span>
          <span style={{ fontSize: 12.5, color: "var(--text-3)", maxWidth: 300 }}>
            Verified results in seconds — score, 20-row scorecard, and every fix.
          </span>
        </div>
      </div>
    </div>
  );
}
