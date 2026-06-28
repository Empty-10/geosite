"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Logo } from "@/components/Logo";
import { ThemeToggle } from "@/components/ThemeToggle";
import { C, scoreColor } from "@/lib/tokens";

type Monitor = {
  id: number;
  url: string;
  cadence: string;
  active: number | boolean;
  consecutive_failures: number;
  created_at: string;
  last_run_at: string | null;
  next_run_at: string | null;
  latestScore: number | null;
  change: number | null;
  trend: number[];
  lastScanAt: string | null;
  scanCount: number;
};

type Payload = {
  monitors: Monitor[];
  engineConfigured: boolean;
  error?: string;
};

function rgba(hex: string, a: number): string {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
}

function prettyHost(raw: string): string {
  try {
    const u = new URL(raw);
    const path = u.pathname.replace(/\/$/, "");
    return u.hostname.replace(/^www\./, "") + path;
  } catch {
    return raw;
  }
}

function timeAgo(iso: string | null): string {
  if (!iso) return "never scanned";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "—";
  const s = Math.max(0, (Date.now() - then) / 1000);
  if (s < 60) return "just now";
  const m = s / 60;
  if (m < 60) return `${Math.floor(m)}m ago`;
  const h = m / 60;
  if (h < 24) return `${Math.floor(h)}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

/** An alert signal derived from data already on the monitor (no extra requests). */
function alertFor(m: Monitor): { label: string; color: string } | null {
  if (m.consecutive_failures > 0) {
    return { label: `Scan failing ×${m.consecutive_failures}`, color: C.fail };
  }
  if (m.change != null && m.change <= -5) {
    return { label: `Dropped ${m.change}`, color: C.warn };
  }
  return null;
}

function Sparkline({ data, color }: { data: number[]; color: string }) {
  const w = 88;
  const h = 28;
  if (!data || data.length < 2) {
    return <span style={{ color: "var(--text-3)", fontSize: 12, width: w, textAlign: "center" }}>—</span>;
  }
  const min = Math.min(...data);
  const max = Math.max(...data);
  const span = max - min || 1;
  const pad = 3;
  const pts = data.map((v, i) => {
    const x = pad + (i / (data.length - 1)) * (w - pad * 2);
    const y = pad + (1 - (v - min) / span) * (h - pad * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const last = pts[pts.length - 1].split(",");
  return (
    <svg width={w} height={h} style={{ display: "block", flexShrink: 0 }} aria-hidden>
      <polyline
        points={pts.join(" ")}
        fill="none"
        stroke={color}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx={last[0]} cy={last[1]} r={2.2} fill={color} />
    </svg>
  );
}

export function DashboardView({ email }: { email: string }) {
  const [state, setState] = useState<Payload | null>(null);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [newUrl, setNewUrl] = useState("");
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);
  const addInputRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    try {
      const res = await fetch("/api/monitors", { cache: "no-store" });
      const data: Payload = await res.json();
      setState(data);
    } catch {
      setState({ monitors: [], engineConfigured: true, error: "Couldn’t reach the dashboard service." });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const addSite = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      const url = newUrl.trim();
      if (!url || adding) return;
      setAdding(true);
      setAddError(null);
      try {
        const res = await fetch("/api/monitors", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ url }),
        });
        const data = await res.json();
        if (!res.ok) {
          setAddError(data?.error ?? "Couldn’t add that site.");
        } else {
          setNewUrl("");
          await load();
        }
      } catch {
        setAddError("Couldn’t add that site.");
      } finally {
        setAdding(false);
      }
    },
    [newUrl, adding, load],
  );

  const removeSite = useCallback(
    async (id: number, label: string) => {
      if (!confirm(`Stop monitoring ${label}?`)) return;
      await fetch(`/api/monitors/${id}`, { method: "DELETE" });
      await load();
    },
    [load],
  );

  const monitors = state?.monitors ?? [];
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return q ? monitors.filter((m) => m.url.toLowerCase().includes(q)) : monitors;
  }, [monitors, query]);

  const stats = useMemo(() => {
    const scored = monitors.filter((m) => m.latestScore != null);
    const avg = scored.length
      ? Math.round(scored.reduce((s, m) => s + (m.latestScore ?? 0), 0) / scored.length)
      : null;
    const alerts = monitors.filter((m) => alertFor(m)).length;
    return { count: monitors.length, avg, alerts };
  }, [monitors]);

  return (
    <div style={{ minHeight: "100dvh", background: "var(--ink)" }}>
      {/* Header */}
      <header
        style={{
          position: "sticky",
          top: 0,
          zIndex: 50,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
          padding: "13px 20px",
          borderBottom: "1px solid var(--border)",
          background: "var(--nav-bg)",
          backdropFilter: "blur(12px)",
          WebkitBackdropFilter: "blur(12px)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Logo />
          <span style={{ fontSize: 16, fontWeight: 500, letterSpacing: "-0.01em" }}>Astova</span>
          <span style={{ color: "var(--text-3)" }}>/</span>
          <span style={{ fontSize: 15, color: "var(--text-2)" }}>Dashboard</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <ThemeToggle />
          <span
            style={{ fontSize: 13, color: "var(--text-3)", maxWidth: 180, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
            title={email}
          >
            {email}
          </span>
          <form action="/auth/signout" method="post">
            <button type="submit" style={ghostBtn}>Sign out</button>
          </form>
        </div>
      </header>

      <main style={{ maxWidth: 980, margin: "0 auto", padding: "28px 20px 80px" }}>
        <h1 style={{ fontSize: 22, fontWeight: 500, letterSpacing: "-0.02em", margin: "0 0 4px" }}>
          Your sites
        </h1>
        <p style={{ color: "var(--text-2)", fontSize: 14, margin: "0 0 22px" }}>
          Monitored pages, their AI-readiness score, and what changed since the last scan.
        </p>

        {/* Stats */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginBottom: 18 }}>
          <StatTile label="Sites tracked" value={stats.count} />
          <StatTile
            label="Average score"
            value={stats.avg ?? "—"}
            color={stats.avg != null ? scoreColor(stats.avg) : undefined}
          />
          <StatTile label="Active alerts" value={stats.alerts} color={stats.alerts ? C.warn : undefined} />
        </div>

        {/* Controls: add + search */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginBottom: 16 }}>
          <form onSubmit={addSite} style={{ display: "flex", gap: 8, flex: "1 1 320px", minWidth: 0 }}>
            <input
              ref={addInputRef}
              value={newUrl}
              onChange={(e) => {
                setNewUrl(e.target.value);
                setAddError(null);
              }}
              placeholder="Add a site to monitor — e.g. stripe.com/pricing"
              style={{ ...inputStyle, flex: 1, minWidth: 0 }}
            />
            <button type="submit" disabled={adding || !newUrl.trim()} style={accentBtn(adding || !newUrl.trim())}>
              {adding ? "Adding…" : "Add site"}
            </button>
          </form>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search…"
            style={{ ...inputStyle, flex: "0 1 200px" }}
          />
        </div>
        {addError && <p style={{ color: "var(--fail)", fontSize: 13, margin: "-6px 0 14px" }}>{addError}</p>}

        {/* Body */}
        {loading ? (
          <Centered>
            <Spinner />
          </Centered>
        ) : state && !state.engineConfigured ? (
          <EmptyState
            title="Monitoring isn’t connected yet"
            body="Set ASTOVA_ENGINE_URL (and the engine’s persistence) to start tracking sites here."
          />
        ) : state?.error ? (
          <EmptyState title="Couldn’t load your sites" body={state.error} tone="error" />
        ) : monitors.length === 0 ? (
          <EmptyState
            title="No sites yet"
            body="Add your first site above to start monitoring its AI-readiness over time."
            action={() => addInputRef.current?.focus()}
          />
        ) : filtered.length === 0 ? (
          <EmptyState title="No matches" body={`Nothing matches “${query}”.`} />
        ) : (
          <div
            style={{
              border: "1px solid var(--border)",
              borderRadius: 14,
              background: "var(--surface)",
              overflow: "hidden",
            }}
          >
            {filtered.map((m, i) => (
              <SiteRow
                key={m.id}
                m={m}
                first={i === 0}
                onRemove={() => removeSite(m.id, prettyHost(m.url))}
              />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

function SiteRow({ m, first, onRemove }: { m: Monitor; first: boolean; onRemove: () => void }) {
  const score = m.latestScore;
  const color = score != null ? scoreColor(score) : C.text3;
  const alert = alertFor(m);
  const change = m.change;

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        flexWrap: "wrap",
        gap: 14,
        padding: "13px 16px",
        borderTop: first ? "none" : "1px solid var(--border)",
      }}
    >
      {/* Score chip */}
      <div
        style={{
          flexShrink: 0,
          width: 44,
          height: 44,
          borderRadius: 10,
          display: "grid",
          placeItems: "center",
          background: rgba(color, 0.12),
          border: `1px solid ${rgba(color, 0.3)}`,
          color,
          fontFamily: "var(--mono)",
          fontSize: 16,
          fontWeight: 500,
        }}
      >
        {score ?? "–"}
      </div>

      {/* Site + meta */}
      <a
        href={`/report?url=${encodeURIComponent(m.url)}`}
        style={{ flex: "1 1 200px", minWidth: 0, textDecoration: "none", color: "var(--text)" }}
      >
        <div
          style={{
            fontSize: 15,
            fontWeight: 500,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {prettyHost(m.url)}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "var(--text-3)", marginTop: 2 }}>
          <span>{timeAgo(m.lastScanAt)}</span>
          <span>·</span>
          <span style={{ textTransform: "capitalize" }}>{m.cadence}</span>
          {alert && (
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 5,
                color: alert.color,
                border: `1px solid ${rgba(alert.color, 0.35)}`,
                background: rgba(alert.color, 0.1),
                padding: "1px 7px",
                borderRadius: 999,
                fontSize: 11,
              }}
            >
              {alert.label}
            </span>
          )}
        </div>
      </a>

      {/* Trend */}
      <Sparkline data={m.trend} color={color} />

      {/* Change */}
      <div style={{ flexShrink: 0, width: 56, textAlign: "right", fontSize: 13, fontFamily: "var(--mono)" }}>
        {change == null ? (
          <span style={{ color: "var(--text-3)" }}>—</span>
        ) : change === 0 ? (
          <span style={{ color: "var(--text-3)" }}>±0</span>
        ) : (
          <span style={{ color: change > 0 ? C.accent : C.fail }}>
            {change > 0 ? "▲" : "▼"} {Math.abs(change)}
          </span>
        )}
      </div>

      {/* Remove */}
      <button
        onClick={onRemove}
        title="Stop monitoring"
        style={{
          flexShrink: 0,
          background: "transparent",
          border: "1px solid var(--border)",
          color: "var(--text-3)",
          borderRadius: 8,
          width: 30,
          height: 30,
          cursor: "pointer",
          fontSize: 14,
          lineHeight: 1,
        }}
      >
        ×
      </button>
    </div>
  );
}

function StatTile({ label, value, color }: { label: string; value: React.ReactNode; color?: string }) {
  return (
    <div
      style={{
        flex: "1 1 150px",
        padding: "12px 14px",
        border: "1px solid var(--border)",
        borderRadius: 12,
        background: "var(--surface)",
      }}
    >
      <div style={{ fontSize: 22, fontWeight: 500, fontFamily: "var(--mono)", color: color ?? "var(--text)" }}>
        {value}
      </div>
      <div style={{ fontSize: 11.5, color: "var(--text-3)", marginTop: 2 }}>{label}</div>
    </div>
  );
}

function EmptyState({
  title,
  body,
  action,
  tone,
}: {
  title: string;
  body: string;
  action?: () => void;
  tone?: "error";
}) {
  return (
    <div
      style={{
        border: "1px dashed var(--border-strong)",
        borderRadius: 14,
        background: "var(--surface)",
        padding: "44px 24px",
        textAlign: "center",
      }}
    >
      <div style={{ fontSize: 16, fontWeight: 500, color: tone === "error" ? C.fail : "var(--text)" }}>
        {title}
      </div>
      <p style={{ color: "var(--text-2)", fontSize: 14, margin: "8px auto 0", maxWidth: 420 }}>{body}</p>
      {action && (
        <button onClick={action} style={{ ...accentBtn(false), marginTop: 16 }}>
          Add a site
        </button>
      )}
    </div>
  );
}

function Centered({ children }: { children: React.ReactNode }) {
  return <div style={{ display: "grid", placeItems: "center", padding: "60px 0" }}>{children}</div>;
}

function Spinner() {
  return (
    <span
      style={{
        width: 22,
        height: 22,
        borderRadius: "50%",
        border: "2.5px solid var(--border-strong)",
        borderTopColor: "var(--accent)",
        display: "inline-block",
        animation: "dmSpin 0.7s linear infinite",
      }}
    />
  );
}

const inputStyle: React.CSSProperties = {
  background: "var(--raised)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  padding: "0.55rem 0.7rem",
  color: "var(--text)",
  fontSize: 14,
  outline: "none",
};

const ghostBtn: React.CSSProperties = {
  background: "var(--raised)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  color: "var(--text)",
  padding: "0.4rem 0.75rem",
  fontSize: 13,
  cursor: "pointer",
};

function accentBtn(disabled: boolean): React.CSSProperties {
  return {
    background: "var(--accent)",
    color: "var(--on-accent)",
    border: "none",
    borderRadius: 8,
    padding: "0.55rem 0.95rem",
    fontSize: 14,
    fontWeight: 500,
    cursor: disabled ? "default" : "pointer",
    opacity: disabled ? 0.55 : 1,
    whiteSpace: "nowrap",
  };
}
