"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { Logo } from "@/components/Logo";
import { ThemeToggle } from "@/components/ThemeToggle";
import { C, scoreColor } from "@/lib/tokens";

type Scan = {
  id: number;
  score: number | null;
  created_at: string;
  token: string | null;
};

type Note = { id: number; body: string; created_at: string };

function rgba(hex: string, a: number): string {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
}

function prettyHost(raw: string): string {
  try {
    const u = new URL(raw);
    return u.hostname.replace(/^www\./, "") + u.pathname.replace(/\/$/, "");
  } catch {
    return raw;
  }
}

function fmtDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function SiteDetailView({ url }: { url: string }) {
  const [scans, setScans] = useState<Scan[] | null>(null);
  const [notes, setNotes] = useState<Note[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [rescanning, setRescanning] = useState(false);
  const [rescanError, setRescanError] = useState<string | null>(null);
  const [noteText, setNoteText] = useState("");
  const [savingNote, setSavingNote] = useState(false);

  const loadScans = useCallback(async () => {
    try {
      const res = await fetch(`/api/history?url=${encodeURIComponent(url)}`, { cache: "no-store" });
      const data = await res.json();
      if (!res.ok) setLoadError(data?.error ?? "Couldn’t load scan history.");
      else setScans(data.scans ?? []);
    } catch {
      setLoadError("Couldn’t reach the service.");
    }
  }, [url]);

  const loadNotes = useCallback(async () => {
    try {
      const res = await fetch(`/api/notes?url=${encodeURIComponent(url)}`, { cache: "no-store" });
      const data = await res.json();
      if (res.ok) setNotes(data.notes ?? []);
    } catch {
      /* notes are non-critical */
    }
  }, [url]);

  useEffect(() => {
    loadScans();
    loadNotes();
  }, [loadScans, loadNotes]);

  const rescan = useCallback(async () => {
    if (rescanning) return;
    setRescanning(true);
    setRescanError(null);
    try {
      const res = await fetch("/api/scan", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ url }),
      });
      const data = await res.json();
      if (!res.ok || data?.meta?.error) {
        setRescanError(data?.error ?? data?.meta?.error ?? "Scan failed.");
      } else {
        await loadScans();
      }
    } catch {
      setRescanError("Scan failed.");
    } finally {
      setRescanning(false);
    }
  }, [url, rescanning, loadScans]);

  const addNote = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      const body = noteText.trim();
      if (!body || savingNote) return;
      setSavingNote(true);
      try {
        const res = await fetch("/api/notes", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ url, body }),
        });
        if (res.ok) {
          setNoteText("");
          await loadNotes();
        }
      } finally {
        setSavingNote(false);
      }
    },
    [url, noteText, savingNote, loadNotes],
  );

  const deleteNote = useCallback(
    async (id: number) => {
      await fetch(`/api/notes/${id}`, { method: "DELETE" });
      await loadNotes();
    },
    [loadNotes],
  );

  const latest = scans?.find((s) => s.score != null) ?? null;
  const latestColor = latest?.score != null ? scoreColor(latest.score) : C.text3;

  // change for each scan vs the next-older scored scan
  const rows = useMemo(() => {
    const list = scans ?? [];
    return list.map((s, i) => {
      const prev = list.slice(i + 1).find((p) => p.score != null);
      const change = s.score != null && prev?.score != null ? s.score - prev.score : null;
      return { scan: s, change };
    });
  }, [scans]);

  return (
    <div style={{ minHeight: "100dvh", background: "var(--ink)" }}>
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
        <div style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 0 }}>
          <Logo />
          <a href="/dashboard" style={{ fontSize: 14, color: "var(--text-2)", textDecoration: "none" }}>
            ← Dashboard
          </a>
        </div>
        <ThemeToggle />
      </header>

      <main style={{ maxWidth: 980, margin: "0 auto", padding: "28px 20px 80px" }}>
        {/* Site header */}
        <div style={{ display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap", marginBottom: 24 }}>
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: 12,
              display: "grid",
              placeItems: "center",
              background: rgba(latestColor, 0.12),
              border: `1px solid ${rgba(latestColor, 0.3)}`,
              color: latestColor,
              fontFamily: "var(--mono)",
              fontSize: 22,
              fontWeight: 500,
              flexShrink: 0,
            }}
          >
            {latest?.score ?? "–"}
          </div>
          <div style={{ flex: "1 1 240px", minWidth: 0 }}>
            <h1 style={{ fontSize: 21, fontWeight: 500, letterSpacing: "-0.02em", margin: 0, wordBreak: "break-all" }}>
              {prettyHost(url)}
            </h1>
            <p style={{ color: "var(--text-2)", fontSize: 13, margin: "3px 0 0" }}>
              {scans == null ? "Loading…" : `${scans.length} scan${scans.length === 1 ? "" : "s"} on record`}
              {latest?.token && (
                <>
                  {" · "}
                  <a href={`/report?id=${latest.token}`} style={{ color: C.accent, textDecoration: "none" }}>
                    View latest report →
                  </a>
                </>
              )}
            </p>
          </div>
          <button onClick={rescan} disabled={rescanning} style={accentBtn(rescanning)}>
            {rescanning ? "Scanning…" : "Re-scan now"}
          </button>
        </div>
        {rescanError && <p style={{ color: "var(--fail)", fontSize: 13, margin: "-14px 0 14px" }}>{rescanError}</p>}

        <div style={{ display: "flex", flexWrap: "wrap", gap: 18, alignItems: "flex-start" }}>
          {/* Scan history */}
          <section style={{ flex: "1 1 440px", minWidth: 0 }}>
            <h2 style={sectionTitle}>Scan history</h2>
            <div style={panel}>
              {loadError ? (
                <Empty text={loadError} tone="error" />
              ) : scans == null ? (
                <Empty text="Loading…" />
              ) : scans.length === 0 ? (
                <Empty text="No scans yet. Run “Re-scan now” to capture the first one." />
              ) : (
                rows.map(({ scan, change }, i) => (
                  <div
                    key={scan.id}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 12,
                      padding: "11px 14px",
                      borderTop: i === 0 ? "none" : "1px solid var(--border)",
                    }}
                  >
                    <span
                      style={{
                        flexShrink: 0,
                        width: 34,
                        fontFamily: "var(--mono)",
                        fontSize: 15,
                        fontWeight: 500,
                        color: scan.score != null ? scoreColor(scan.score) : "var(--text-3)",
                      }}
                    >
                      {scan.score ?? "–"}
                    </span>
                    <span style={{ flex: 1, minWidth: 0, fontSize: 13, color: "var(--text-2)" }}>
                      {fmtDate(scan.created_at)}
                    </span>
                    <span style={{ flexShrink: 0, width: 48, textAlign: "right", fontFamily: "var(--mono)", fontSize: 12.5 }}>
                      {change == null ? (
                        <span style={{ color: "var(--text-3)" }}>—</span>
                      ) : change === 0 ? (
                        <span style={{ color: "var(--text-3)" }}>±0</span>
                      ) : (
                        <span style={{ color: change > 0 ? C.accent : C.fail }}>
                          {change > 0 ? "▲" : "▼"} {Math.abs(change)}
                        </span>
                      )}
                    </span>
                    {scan.token ? (
                      <a
                        href={`/report?id=${scan.token}`}
                        style={{ flexShrink: 0, fontSize: 12.5, color: C.accent, textDecoration: "none", whiteSpace: "nowrap" }}
                      >
                        View →
                      </a>
                    ) : (
                      <span style={{ flexShrink: 0, fontSize: 12, color: "var(--text-3)", whiteSpace: "nowrap" }}>
                        no link
                      </span>
                    )}
                  </div>
                ))
              )}
            </div>
          </section>

          {/* Notes */}
          <section style={{ flex: "1 1 300px", minWidth: 0 }}>
            <h2 style={sectionTitle}>Notes</h2>
            <form onSubmit={addNote} style={{ marginBottom: 12 }}>
              <textarea
                value={noteText}
                onChange={(e) => setNoteText(e.target.value)}
                placeholder="Add a note — e.g. “rewrote intros to front-load the answer”"
                rows={3}
                style={{ ...inputStyle, width: "100%", resize: "vertical", fontFamily: "inherit" }}
              />
              <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 8 }}>
                <button type="submit" disabled={savingNote || !noteText.trim()} style={accentBtn(savingNote || !noteText.trim())}>
                  {savingNote ? "Saving…" : "Add note"}
                </button>
              </div>
            </form>
            <div style={panel}>
              {notes == null ? (
                <Empty text="Loading…" />
              ) : notes.length === 0 ? (
                <Empty text="No notes yet." />
              ) : (
                notes.map((n, i) => (
                  <div
                    key={n.id}
                    style={{
                      display: "flex",
                      gap: 10,
                      padding: "11px 14px",
                      borderTop: i === 0 ? "none" : "1px solid var(--border)",
                    }}
                  >
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 14, color: "var(--text)", whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                        {n.body}
                      </div>
                      <div style={{ fontSize: 11.5, color: "var(--text-3)", marginTop: 4 }}>{fmtDate(n.created_at)}</div>
                    </div>
                    <button onClick={() => deleteNote(n.id)} title="Delete note" style={delBtn}>
                      ×
                    </button>
                  </div>
                ))
              )}
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}

function Empty({ text, tone }: { text: string; tone?: "error" }) {
  return (
    <div style={{ padding: "24px 16px", textAlign: "center", color: tone === "error" ? C.fail : "var(--text-3)", fontSize: 13 }}>
      {text}
    </div>
  );
}

const sectionTitle: React.CSSProperties = {
  fontSize: 13,
  fontWeight: 500,
  color: "var(--text-2)",
  margin: "0 0 10px",
  textTransform: "uppercase",
  letterSpacing: "0.04em",
};

const panel: React.CSSProperties = {
  border: "1px solid var(--border)",
  borderRadius: 14,
  background: "var(--surface)",
  overflow: "hidden",
};

const inputStyle: React.CSSProperties = {
  background: "var(--raised)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  padding: "0.55rem 0.7rem",
  color: "var(--text)",
  fontSize: 14,
  outline: "none",
};

const delBtn: React.CSSProperties = {
  flexShrink: 0,
  background: "transparent",
  border: "1px solid var(--border)",
  color: "var(--text-3)",
  borderRadius: 8,
  width: 26,
  height: 26,
  cursor: "pointer",
  fontSize: 13,
  lineHeight: 1,
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
