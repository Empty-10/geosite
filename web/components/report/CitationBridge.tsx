// The readiness → visibility bridge: connects the deterministic on-page score to the question a
// brand actually asks — "will AI engines cite me?" — and routes to the tool that *measures* it.
// Honest by construction: the band is VERIFIED readiness (on-page signals), the CTA leads to the
// MEASURED citation sampling. Replaces the old static "23% citation share" placeholder card.

import { C } from "@/lib/tokens";
import { rgba } from "./types";
import type { CitationReadiness } from "./scorecardTypes";

const BAND: Record<string, { color: string; lead: string }> = {
  "well positioned": { color: C.accent, lead: "well positioned" },
  "partially positioned": { color: C.warn, lead: "partially positioned" },
  "poorly positioned": { color: C.fail, lead: "poorly positioned" },
};

export function CitationBridge({ citation, url }: { citation?: CitationReadiness; url: string }) {
  if (!citation || citation.band === "unknown" || citation.score == null) return null;
  const band = BAND[citation.band] ?? BAND["partially positioned"];
  const visHref = `/visibility?url=${encodeURIComponent(url)}`;

  return (
    <div style={{ border: `1px solid ${rgba(band.color, 0.4)}`, borderRadius: 12, background: rgba(band.color, 0.05), padding: "16px 18px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: 10, flexWrap: "wrap" }}>
        <span style={{ fontSize: 13, fontWeight: 500, color: "var(--text)" }}>Will AI engines cite this page?</span>
        <span style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 11, color: C.accent, border: `1px solid ${rgba(C.accent, 0.35)}`, background: rgba(C.accent, 0.1), padding: "2px 8px", borderRadius: 999, fontFamily: "var(--mono)" }}>
          VERIFIED · readiness
        </span>
      </div>

      <p style={{ fontSize: 13.5, lineHeight: 1.55, color: "var(--text-2)", margin: "0 0 10px" }}>
        Based on the on-page signals answer engines use to pick sources, this page is{" "}
        <strong style={{ color: band.color }}>{band.lead}</strong> to be cited
        <span style={{ color: "var(--text-3)" }}> ({citation.score}/100 retrieval readiness)</span>.
        {citation.reasons.length > 0 && (
          <> The main thing holding it back: {citation.reasons.map((r) => r.text).join(", ")}.</>
        )}
      </p>

      <div style={{ borderTop: "1px solid var(--border)", paddingTop: 10, marginTop: 4 }}>
        <a href={visHref} style={{ fontSize: 12.5, color: C.measured, fontWeight: 500 }}>
          Readiness predicts citability — now measure whether engines actually cite you →
        </a>
        <div style={{ fontSize: 11, color: "var(--text-3)", marginTop: 4 }}>
          Live citation sampling is <span style={{ color: C.measured }}>MEASURED</span> (shown with a confidence band), separate from this deterministic readiness read.
        </div>
      </div>
    </div>
  );
}
