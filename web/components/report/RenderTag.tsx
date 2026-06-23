// Small indicator shown when a scan executed the page's JavaScript (rendered the DOM)
// before analyzing — so the report reflects what a JS-running crawler sees, not just raw HTML.
// Hidden for ordinary raw-HTML scans (the common, server-rendered case).

export function RenderTag({ meta }: { meta?: Record<string, unknown> }) {
  const source = typeof meta?.render_source === "string" ? (meta.render_source as string) : null;
  if (!source) return null;
  const via = source === "cloudflare" ? "Cloudflare" : source === "playwright" ? "a headless browser" : source;
  return (
    <span
      title={`JavaScript was executed for this scan (rendered via ${via}), so the results reflect the page after JS runs.`}
      style={{
        fontSize: 10.5,
        color: "var(--text-3)",
        border: "1px solid var(--border)",
        borderRadius: 999,
        padding: "1px 8px",
        marginLeft: 8,
        fontFamily: "var(--mono)",
        cursor: "default",
        whiteSpace: "nowrap",
      }}
    >
      JS-rendered
    </span>
  );
}
