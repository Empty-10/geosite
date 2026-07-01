import type { Metadata } from "next";

import { fetchReportBundle, type ReportFinding } from "@/lib/reportData";
import { PrintTrigger } from "@/components/report/PrintTrigger";

export const metadata: Metadata = {
  title: "AI Readiness Report",
  robots: { index: false },
};

const PILLAR_LABEL: Record<string, string> = {
  technical: "Technical", onpage: "On-page", geo: "GEO readiness", performance: "Performance", local: "Local",
};
const SEV_RANK: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3, info: 4 };

// Print stylesheet: force white/black, sensible margins, and keep sections off page breaks.
const PRINT_CSS = `
  .astova-print { background: #ffffff; color: #111111; max-width: 760px; margin: 0 auto;
    padding: 32px 28px 56px; font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
    line-height: 1.5; }
  .astova-print h1, .astova-print h2 { color: #000; margin: 0; }
  .astova-print h2 { font-size: 15px; border-bottom: 1px solid #ddd; padding-bottom: 4px; margin: 0 0 8px; }
  .astova-print .sec { margin: 0 0 22px; page-break-inside: avoid; }
  .astova-print .muted { color: #555; }
  .astova-print ul { margin: 6px 0 0; padding-left: 18px; }
  .astova-print li { margin-bottom: 5px; }
  .astova-print table { width: 100%; border-collapse: collapse; }
  .astova-print td { padding: 4px 6px; border-bottom: 1px solid #eee; font-size: 13px; }
  @media print {
    @page { margin: 16mm; }
    html, body { background: #ffffff !important; }
    .astova-print { padding: 0; max-width: 100%; }
  }
`;

function fmtDate(iso: string | null): string {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleString("en-GB", { dateStyle: "long", timeStyle: "short" });
  } catch {
    return iso;
  }
}

function Findings({ items }: { items: ReportFinding[] }) {
  return (
    <ul>
      {items.map((f) => (
        <li key={f.finding_id}>
          <strong>{(f.status || "").toUpperCase()}</strong> {f.title}{" "}
          <span className="muted">({f.severity})</span>
          {f.recommendation ? <div className="muted" style={{ fontSize: 13 }}>{f.recommendation}</div> : null}
        </li>
      ))}
    </ul>
  );
}

export default async function PrintReportPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ share?: string }>;
}) {
  await params; // id is cosmetic; the share token authorises the read
  const sp = await searchParams;
  const share = typeof sp.share === "string" ? sp.share : "";
  const result = share
    ? await fetchReportBundle(share)
    : ({ ok: false, status: 400, error: "This report needs a share link (it ends with ?share=...)." } as const);

  if (!result.ok) {
    return (
      <div className="astova-print">
        <style>{PRINT_CSS}</style>
        <p>{result.error}</p>
      </div>
    );
  }

  const { report, bundle } = result.data;
  const m = bundle.metadata;
  const s = bundle.action_summary;
  const scorecard = report.scorecard || {};
  const summary = scorecard.summary || {};
  const top = [...s.deterministic, ...s.ai_assisted, ...s.manual]
    .sort((a, b) => (SEV_RANK[a.severity] ?? 9) - (SEV_RANK[b.severity] ?? 9))
    .slice(0, 8);

  return (
    <div className="astova-print">
      <style>{PRINT_CSS}</style>
      <PrintTrigger />

      <div className="sec">
        <div style={{ fontSize: 13, letterSpacing: "0.04em", textTransform: "uppercase", color: "#555" }}>Astova</div>
        <h1 style={{ fontSize: 24, margin: "2px 0 4px" }}>AI Readiness Report</h1>
        <div className="muted" style={{ fontSize: 13, wordBreak: "break-all" }}>{m.scanned_target}</div>
        <div className="muted" style={{ fontSize: 12 }}>{fmtDate(m.created_at)} · Report #{m.report_id ?? "?"}</div>
      </div>

      <div className="sec" style={{ display: "flex", alignItems: "baseline", gap: 12 }}>
        <div style={{ fontSize: 44, fontWeight: 700 }}>{report.overall_score}</div>
        <div style={{ fontSize: 16 }}>/ 100 AI Readiness</div>
      </div>

      <div className="sec muted" style={{ fontSize: 12 }}>
        All scored checks are <strong>VERIFIED</strong> - read deterministically from the live page and
        reproducible on re-run. AI citation sampling (MEASURED) is reported separately.
      </div>

      {scorecard.assessment && (
        <>
          <div className="sec">
            <h2>Executive assessment</h2>
            <div className="muted" style={{ fontSize: 12, marginBottom: 4 }}>
              {scorecard.assessment.band_label} · Astova confidence: {scorecard.assessment.confidence?.level}
            </div>
            {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
            {(scorecard.assessment.verdict || []).map((line: string, i: number) => (
              <p key={i} style={{ margin: "4px 0", fontSize: 13 }}>{line}</p>
            ))}
          </div>

          {scorecard.assessment.programme?.length > 0 && (
            <div className="sec">
              <h2>Implementation programme - one-week plan</h2>
              {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
              {scorecard.assessment.programme.map((p: any, i: number) => (
                <div key={p.key} style={{ marginBottom: 8, pageBreakInside: "avoid" }}>
                  <div style={{ fontWeight: 700, fontSize: 13 }}>
                    Phase {i + 1}: {p.name} - {p.effort}, +{p.improvement} AI Readiness, {p.fixes_count} fix(es)
                  </div>
                  <div className="muted" style={{ fontSize: 12 }}>{p.objective}</div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {"★".repeat(p.ai_agent_suitability)} AI-agent · Manual review: {p.manual_review}
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {(summary.verdict || (summary.opportunities && summary.opportunities.length)) && (
        <div className="sec">
          <h2>Executive summary</h2>
          {summary.verdict ? <p style={{ margin: "6px 0" }}>{summary.verdict}</p> : null}
          {summary.opportunities && summary.opportunities.length ? (
            <ul>
              {summary.opportunities.slice(0, 5).map((o: { label?: string } | string, i: number) => (
                <li key={i}>{typeof o === "string" ? o : o.label}</li>
              ))}
            </ul>
          ) : null}
        </div>
      )}

      <div className="sec">
        <h2>Readiness breakdown</h2>
        <table>
          <tbody>
            {Object.entries(report.pillar_scores).map(([k, v]) => (
              <tr key={k}>
                <td>{PILLAR_LABEL[k] || k}</td>
                <td style={{ textAlign: "right", fontWeight: 600 }}>{v}/100</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="sec">
        <h2>Action summary</h2>
        <table>
          <tbody>
            <tr><td>Actionable findings</td><td style={{ textAlign: "right" }}>{s.actionable_count}</td></tr>
            <tr><td>Deterministic fixes available</td><td style={{ textAlign: "right" }}>{s.deterministic_fix_count}</td></tr>
            <tr><td>AI-assisted fixes</td><td style={{ textAlign: "right" }}>{s.ai_assisted_count}</td></tr>
            <tr><td>Manual review items</td><td style={{ textAlign: "right" }}>{s.manual_count}</td></tr>
          </tbody>
        </table>
      </div>

      {top.length > 0 && (
        <div className="sec">
          <h2>Top findings</h2>
          <Findings items={top} />
        </div>
      )}

      {s.deterministic.length > 0 && (
        <div className="sec">
          <h2>Deterministic fixes available</h2>
          <Findings items={s.deterministic} />
        </div>
      )}
      {s.ai_assisted.length > 0 && (
        <div className="sec">
          <h2>AI-assisted items</h2>
          <Findings items={s.ai_assisted} />
        </div>
      )}
      {s.manual.length > 0 && (
        <div className="sec">
          <h2>Manual review items</h2>
          <Findings items={s.manual} />
        </div>
      )}

      <div className="sec">
        <h2>Verification guidance</h2>
        <p style={{ margin: "6px 0" }}>
          Apply the fixes, then re-scan the target (or use Astova&apos;s verify step per finding) to confirm
          the score improved. Re-running reproduces every VERIFIED finding exactly.
        </p>
      </div>

      <div className="sec muted" style={{ fontSize: 11, borderTop: "1px solid #ddd", paddingTop: 10 }}>
        <strong>Confidence labels.</strong> VERIFIED - read straight from the page or an authoritative API;
        re-running reproduces it exactly. MEASURED - sampled from AI engines on a date, shown with a
        confidence band and sample size. ESTIMATED - modelled/inferred, flagged as directional. This report
        is VERIFIED throughout. Engine {m.engine_version} · Ruleset {m.ruleset_version} · Report format{" "}
        {m.report_version} · Generated by Astova.
      </div>
    </div>
  );
}
