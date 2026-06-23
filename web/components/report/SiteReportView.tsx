"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { C, scoreColor } from "@/lib/tokens";
import { ToolNav } from "./ToolNav";
import { FindingsList } from "./FindingsList";
import { ScoreRing } from "./ScoreRing";
import { rgba } from "./types";
import type { CrawlJob, PageSummary, SiteReport } from "./siteTypes";

const POLL_MS = 1600;
const MAX_POLL_MS = 4 * 60 * 1000; // give up after 4 minutes

type State =
  | { phase: "empty" }
  | { phase: "running"; url: string; done: number; total: number; current?: string }
  | { phase: "error"; url: string; message: string }
  | { phase: "done"; url: string; report: SiteReport };

function normalizeForSubmit(raw: string): string {
  const v = raw.trim();
  return /^https?:\/\//i.test(v) ? v : `https://${v}`;
}

export function SiteReportView() {
  const params = useSearchParams();
  const urlParam = params.get("url") ?? "";
  const [state, setState] = useState<State>({ phase: "empty" });
  const [input, setInput] = useState(urlParam);

  const pollTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const runId = useRef(0);

  const stop = useCallback(() => {
    if (pollTimer.current) clearTimeout(pollTimer.current);
    pollTimer.current = null;
  }, []);
  useEffect(() => stop, [stop]);

  const runCrawl = useCallback(
    async (url: string) => {
      stop();
      const myRun = ++runId.current;
      setState({ phase: "running", url, done: 0, total: 25 });

      let jobId: string;
      try {
        const res = await fetch("/api/crawl", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ url, maxPages: 25 }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data?.error || `Couldn't start the crawl (${res.status}).`);
        jobId = data.job_id;
      } catch (e) {
        if (runId.current === myRun)
          setState({ phase: "error", url, message: e instanceof Error ? e.message : "Couldn't start the crawl." });
        return;
      }

      const startedAt = Date.now();
      const poll = async () => {
        if (runId.current !== myRun) return; // superseded
        try {
          const res = await fetch(`/api/crawl?id=${encodeURIComponent(jobId)}`);
          const job: CrawlJob & { error?: string } = await res.json();
          if (!res.ok) throw new Error(job?.error || `Crawl failed (${res.status}).`);
          if (runId.current !== myRun) return;

          if (job.status === "done" && job.result) {
            setState({ phase: "done", url, report: job.result });
            return;
          }
          if (job.status === "error") {
            setState({ phase: "error", url, message: job.error || "The crawl failed." });
            return;
          }
          // still running
          setState({
            phase: "running",
            url,
            done: job.progress?.pages_crawled ?? 0,
            total: job.max_pages ?? 25,
            current: job.progress?.current,
          });
          if (Date.now() - startedAt > MAX_POLL_MS) {
            setState({ phase: "error", url, message: "The crawl took too long and was stopped." });
            return;
          }
          pollTimer.current = setTimeout(poll, POLL_MS);
        } catch (e) {
          if (runId.current === myRun)
            setState({ phase: "error", url, message: e instanceof Error ? e.message : "Lost contact with the crawl." });
        }
      };
      pollTimer.current = setTimeout(poll, POLL_MS);
    },
    [stop],
  );

  // Auto-start when arriving with ?url=
  useEffect(() => {
    if (urlParam) {
      setInput(urlParam);
      runCrawl(normalizeForSubmit(urlParam));
    } else {
      setState({ phase: "empty" });
    }
  }, [urlParam, runCrawl]);

  const submit = () => {
    if (input.trim()) runCrawl(normalizeForSubmit(input));
  };
  const busy = state.phase === "running";

  return (
    <div style={{ minHeight: "100vh", background: "var(--ink)" }}>
      <ToolNav active="site" />

      <main style={{ maxWidth: 920, margin: "0 auto", padding: "24px 20px 80px" }}>
        <div style={{ display: "flex", gap: 10, marginBottom: 22 }}>
          <div
            style={{
              flex: 1,
              display: "flex",
              alignItems: "center",
              gap: 10,
              padding: "0 14px",
              height: 46,
              border: "1px solid var(--border)",
              borderRadius: 10,
              background: "var(--surface)",
            }}
          >
            <span style={{ fontSize: 14, color: "var(--text-3)", fontFamily: "var(--mono)" }}>https://</span>
            <input
              value={input.replace(/^https?:\/\//i, "")}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
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
            onClick={submit}
            disabled={busy}
            style={{
              fontSize: 14,
              fontWeight: 500,
              border: "none",
              padding: "0 20px",
              height: 46,
              borderRadius: 10,
              cursor: busy ? "default" : "pointer",
              flexShrink: 0,
              background: busy ? C.raised : C.accent,
              color: busy ? C.text3 : C.ink,
            }}
          >
            {busy ? "Crawling…" : state.phase === "done" ? "Re-crawl" : "Crawl site"}
          </button>
        </div>

        {state.phase === "empty" && (
          <Placeholder>
            Enter a URL to crawl the whole site — every page scored, plus site-wide issues like broken links,
            duplicate titles, thin pages and sitemap gaps.
          </Placeholder>
        )}

        {state.phase === "running" && <Progress done={state.done} total={state.total} current={state.current} />}

        {state.phase === "error" && (
          <div
            style={{
              padding: "20px 18px",
              border: `1px solid ${rgba(C.fail, 0.4)}`,
              borderRadius: 12,
              background: rgba(C.fail, 0.06),
              color: "var(--text-2)",
              fontSize: 14,
            }}
          >
            <strong style={{ color: "var(--text)" }}>Couldn&apos;t crawl {state.url}.</strong>
            <div style={{ marginTop: 6, color: "var(--text-3)" }}>{state.message}</div>
          </div>
        )}

        {state.phase === "done" && <SiteBody report={state.report} />}
      </main>
    </div>
  );
}

function Placeholder({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        minHeight: 240,
        border: "1px dashed var(--border)",
        borderRadius: 12,
        color: "var(--text-3)",
        fontSize: 14,
        textAlign: "center",
        padding: 28,
        lineHeight: 1.6,
        maxWidth: 560,
        margin: "0 auto",
      }}
    >
      {children}
    </div>
  );
}

function Progress({ done, total, current }: { done: number; total: number; current?: string }) {
  const pct = total > 0 ? Math.min(100, Math.round((done / total) * 100)) : 0;
  return (
    <div
      style={{
        padding: "26px 22px",
        border: "1px solid var(--border)",
        borderRadius: 12,
        background: "var(--surface)",
      }}
    >
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 12 }}>
        <span style={{ fontSize: 14, color: "var(--text)" }}>Crawling the site…</span>
        <span style={{ fontSize: 13, color: "var(--text-3)", fontFamily: "var(--mono)" }}>
          {done} / {total} pages
        </span>
      </div>
      <div style={{ height: 6, borderRadius: 999, background: "var(--raised)", overflow: "hidden" }}>
        <div
          style={{
            width: `${Math.max(4, pct)}%`,
            height: "100%",
            background: C.accent,
            transition: "width 0.4s ease",
          }}
        />
      </div>
      <div
        style={{
          marginTop: 12,
          fontSize: 12,
          color: "var(--text-3)",
          fontFamily: "var(--mono)",
          whiteSpace: "nowrap",
          overflow: "hidden",
          textOverflow: "ellipsis",
        }}
      >
        {current ? `→ ${current}` : "discovering pages…"}
      </div>
    </div>
  );
}

function SiteBody({ report }: { report: SiteReport }) {
  const m = report.meta as { pages_crawled?: number; broken?: number; sitemap_urls?: number };
  const when = new Date(report.fetched_at);

  return (
    <div style={{ animation: "dmFade 0.3s ease both" }}>
      <div style={{ marginBottom: 16 }}>
        <h1 style={{ fontSize: 22, fontWeight: 500, letterSpacing: "-0.02em", marginBottom: 6, wordBreak: "break-all" }}>
          {report.url}
        </h1>
        <div style={{ fontSize: 12.5, color: "var(--text-3)", fontFamily: "var(--mono)" }}>
          crawled {when.toLocaleString()} · {m.pages_crawled ?? report.pages.length} pages · site-wide audit
        </div>
      </div>

      <div style={{ display: "flex", gap: 16, alignItems: "stretch", marginBottom: 22, flexWrap: "wrap" }}>
        <ScoreRing score={report.overall_score} />
        <div style={{ display: "flex", gap: 10, flex: 1, minWidth: 260 }}>
          <Stat label="Pages" value={m.pages_crawled ?? report.pages.length} />
          <Stat label="Broken links" value={m.broken ?? 0} bad={(m.broken ?? 0) > 0} />
          <Stat label="Sitemap URLs" value={m.sitemap_urls ?? 0} />
        </div>
      </div>

      <SectionTitle>Site-wide issues</SectionTitle>
      <div style={{ marginBottom: 28 }}>
        {report.site_findings.length > 0 ? (
          <FindingsList findings={report.site_findings} openFirst={false} />
        ) : (
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
            No site-wide issues found across the crawled pages — no broken links, duplicate titles, thin pages or
            sitemap gaps.
          </div>
        )}
      </div>

      <SectionTitle>Pages ({report.pages.length})</SectionTitle>
      <PagesTable pages={report.pages} />
    </div>
  );
}

function Stat({ label, value, bad = false }: { label: string; value: number; bad?: boolean }) {
  return (
    <div
      style={{
        flex: 1,
        padding: "12px 14px",
        border: "1px solid var(--border)",
        borderRadius: 12,
        background: "var(--surface)",
      }}
    >
      <div style={{ fontSize: 22, fontWeight: 500, color: bad ? C.fail : "var(--text)", fontFamily: "var(--mono)" }}>
        {value}
      </div>
      <div style={{ fontSize: 11.5, color: "var(--text-3)", marginTop: 2 }}>{label}</div>
    </div>
  );
}

function PagesTable({ pages }: { pages: PageSummary[] }) {
  const rows = [...pages].sort((a, b) => a.overall_score - b.overall_score);
  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: 12, overflow: "hidden" }}>
      {rows.map((p, i) => {
        let path = p.url;
        try {
          const u = new URL(p.url);
          path = (u.pathname || "/") + (u.search || "");
        } catch {
          /* keep full url */
        }
        return (
          <a
            key={p.url}
            href={`/report?url=${encodeURIComponent(p.url)}`}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              padding: "11px 14px",
              borderTop: i === 0 ? "none" : "1px solid var(--border)",
              background: "var(--surface)",
              color: "var(--text)",
            }}
          >
            <span
              style={{
                fontSize: 12.5,
                fontWeight: 600,
                fontFamily: "var(--mono)",
                color: scoreColor(p.overall_score),
                width: 30,
                flexShrink: 0,
              }}
            >
              {p.overall_score}
            </span>
            <span
              style={{
                flex: 1,
                minWidth: 0,
                fontSize: 13,
                fontFamily: "var(--mono)",
                color: "var(--text-2)",
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              {path}
            </span>
            <span
              style={{
                flex: 1,
                minWidth: 0,
                fontSize: 13,
                color: "var(--text-3)",
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
              title={p.title}
            >
              {p.title || "—"}
            </span>
            <span style={{ fontSize: 12, color: "var(--text-3)", fontFamily: "var(--mono)", flexShrink: 0 }}>
              {p.word_count}w
            </span>
            <span
              style={{
                fontSize: 11.5,
                color: p.issues > 0 ? C.warn : "var(--text-3)",
                fontFamily: "var(--mono)",
                width: 64,
                textAlign: "right",
                flexShrink: 0,
              }}
            >
              {p.issues} {p.issues === 1 ? "issue" : "issues"}
            </span>
          </a>
        );
      })}
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <div style={{ fontSize: 13, color: "var(--text)", fontWeight: 500, marginBottom: 10 }}>{children}</div>;
}
