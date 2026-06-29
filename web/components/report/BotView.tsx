// "How each AI engine sees this page" — the signature accuracy view.
//
// Two axes the engine already measures, both VERIFIED:
//   - geo.js_rendered: raw HTML vs rendered DOM (does content need JavaScript?)
//   - geo.bot_access:  can the AI crawler fetch the page at all (WAF/CDN/cloaking)?
//
// Non-JS crawlers (ChatGPT/GPTBot, Claude/ClaudeBot, Perplexity) read the RAW HTML.
// JS-rendering crawlers (Google AI Overviews/Gemini, Copilot/Bing) render first. So a page
// whose content only appears after JavaScript is invisible to the first group — this panel
// makes that split explicit instead of leaving it as one buried finding.
import { C } from "@/lib/tokens";
import { rgba, type Report } from "./types";

const NO_JS_ENGINES = ["ChatGPT", "Claude", "Perplexity"];
const JS_ENGINES = ["Gemini", "AI Overviews", "Copilot"];

type JsValue = {
  raw_words?: number;
  rendered_words?: number;
  render_only_pct?: number;
  h1_js_only?: boolean;
  schema_js_only?: boolean;
};

type AccessValue = { bot_status?: number; normal_status?: number; blocked?: boolean };

export function BotView({ report }: { report: Report }) {
  const findings = report.findings ?? [];
  const js = findings.find((f) => f.id === "geo.js_rendered");
  const access = findings.find((f) => f.id === "geo.bot_access");

  const v = (js?.value ?? {}) as JsValue;
  const metaWords = Number((report.meta as Record<string, unknown>)?.word_count ?? 0);
  const rawWords = v.raw_words ?? metaWords;
  const renderedWords = v.rendered_words ?? rawWords;
  const pct = v.render_only_pct ?? 0;
  const gapWords = Math.max(0, renderedWords - rawWords);
  const hasGap = !!js && pct > 0 && gapWords > 0;

  const av = (access?.value ?? {}) as AccessValue;
  const hardBlocked = access?.status === "fail";
  const softBlocked = access?.status === "warn";

  return (
    <section style={{ marginBottom: 18 }}>
      <h2 style={{ fontSize: 16, fontWeight: 500, margin: "0 0 4px" }}>How each AI engine sees this page</h2>
      <p style={{ fontSize: 13, color: "var(--text-2)", margin: "0 0 14px" }}>
        AI crawlers split in two: most don&apos;t run JavaScript — they read your raw HTML.
      </p>

      {/* Access banner — a crawler that can't fetch the page never sees anything. */}
      {hardBlocked && (
        <Banner color={C.fail}>
          Blocked — fetched as GPTBot returned HTTP {av.bot_status ?? "error"} while a browser gets{" "}
          {av.normal_status ?? "200"}. Non-JS AI crawlers can&apos;t read this page at all. Fix crawler
          access (robots.txt + CDN/WAF) first.
        </Banner>
      )}
      {softBlocked && (
        <Banner color={C.warn}>
          GPTBot is served far less content than a browser — likely a consent wall, JS challenge or
          cloaking. The AI crawler sees a near-empty page.
        </Banner>
      )}

      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        <Column
          title="Read raw HTML — no JavaScript"
          engines={NO_JS_ENGINES}
          words={rawWords}
          accent={hasGap || hardBlocked ? C.warn : C.accent}
          notes={
            hardBlocked
              ? ["Can't fetch the page"]
              : [
                  v.h1_js_only ? "Your H1 is missing (loads via JS)" : null,
                  v.schema_js_only ? "Your structured data is missing (loads via JS)" : null,
                  hasGap ? `Misses ${gapWords} words (${pct}%) that load via JavaScript` : null,
                  !hasGap && !hardBlocked ? "Sees your full page" : null,
                ].filter(Boolean) as string[]
          }
          ok={!hasGap && !hardBlocked}
        />
        <Column
          title="Render JavaScript first"
          engines={JS_ENGINES}
          words={renderedWords}
          accent={C.measured}
          notes={[hasGap ? "Renders the page — sees the JS content too" : "Sees your full page"]}
          ok
        />
      </div>

      <p style={{ fontSize: 13, color: "var(--text-2)", margin: "12px 0 0", lineHeight: 1.5 }}>
        {hardBlocked ? (
          <>
            Until the crawler can fetch the page, <strong style={{ color: "var(--text)" }}>ChatGPT,
            Claude and Perplexity see nothing here</strong> — they don&apos;t render JavaScript to
            work around it either.
          </>
        ) : hasGap ? (
          <>
            <strong style={{ color: "var(--text)" }}>{pct}% of your content only exists after
            JavaScript runs.</strong>{" "}
            ChatGPT, Claude and Perplexity can&apos;t execute JS, so they never see it — only the
            JS-rendering engines do. Serve it in the initial HTML (SSR / static / prerender) to be
            readable by every engine.
          </>
        ) : (
          <>
            <strong style={{ color: C.accent }}>Your content is in the HTML</strong> — every AI
            engine sees the same page, whether it runs JavaScript or not.
          </>
        )}
      </p>
    </section>
  );
}

function Column({
  title,
  engines,
  words,
  accent,
  notes,
  ok,
}: {
  title: string;
  engines: string[];
  words: number;
  accent: string;
  notes: string[];
  ok: boolean;
}) {
  return (
    <div
      style={{
        flex: "1 1 240px",
        minWidth: 0,
        border: "1px solid var(--border)",
        borderRadius: 12,
        background: "var(--surface)",
        padding: "14px 16px",
      }}
    >
      <div style={{ fontSize: 12.5, color: "var(--text-3)", marginBottom: 8 }}>{title}</div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 12 }}>
        {engines.map((e) => (
          <span
            key={e}
            style={{
              fontSize: 12,
              color: "var(--text-2)",
              border: "1px solid var(--border)",
              borderRadius: 999,
              padding: "2px 9px",
            }}
          >
            {e}
          </span>
        ))}
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 6, marginBottom: 8 }}>
        <span style={{ fontSize: 24, fontWeight: 500, fontFamily: "var(--mono)", color: accent }}>
          {words.toLocaleString()}
        </span>
        <span style={{ fontSize: 12.5, color: "var(--text-3)" }}>words visible</span>
      </div>
      <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "grid", gap: 5 }}>
        {notes.map((n, i) => (
          <li key={i} style={{ display: "flex", gap: 7, fontSize: 12.5, color: "var(--text-2)" }}>
            <span style={{ color: ok ? C.accent : C.warn, flexShrink: 0 }}>{ok ? "✓" : "✗"}</span>
            <span>{n}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Banner({ color, children }: { color: string; children: React.ReactNode }) {
  return (
    <div
      style={{
        fontSize: 13,
        color: "var(--text)",
        background: rgba(color, 0.1),
        border: `1px solid ${rgba(color, 0.35)}`,
        borderRadius: 10,
        padding: "10px 12px",
        marginBottom: 12,
        lineHeight: 1.45,
      }}
    >
      {children}
    </div>
  );
}
