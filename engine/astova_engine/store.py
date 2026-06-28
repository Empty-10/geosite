"""Scan history — a small persistence layer so re-scanning a URL can show what changed.

Backed by SQLite (stdlib, no new dependency). Enabled only when ASTOVA_DB_PATH is set; otherwise
every function is a graceful no-op (save -> None, history -> []), so the engine runs identically
with or without persistence.

Production note: SQLite on an ephemeral container disk (e.g. Render's default) resets on redeploy.
For durable history, point ASTOVA_DB_PATH at a persistent disk, or swap this module's storage for
Postgres later (the public functions are the seam).
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone


def db_path() -> str | None:
    return os.environ.get("ASTOVA_DB_PATH") or None


def is_enabled() -> bool:
    return db_path() is not None


@contextmanager
def _conn():
    path = db_path()
    if not path:
        raise RuntimeError("persistence not configured (set ASTOVA_DB_PATH)")
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        _ensure_schema(conn)
        yield conn
        conn.commit()
    finally:
        conn.close()


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL,
            url TEXT NOT NULL,
            created_at TEXT NOT NULL,
            score INTEGER,
            report TEXT NOT NULL
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_scans_url_kind ON scans(url, kind, id)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS monitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            cadence TEXT NOT NULL DEFAULT 'daily',
            email TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            consecutive_failures INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            last_run_at TEXT,
            next_run_at TEXT
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            monitor_id INTEGER NOT NULL,
            scan_id INTEGER,
            type TEXT NOT NULL,
            severity TEXT NOT NULL,
            summary TEXT NOT NULL,
            detail TEXT,
            created_at TEXT NOT NULL
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_monitor ON alerts(monitor_id, id)")


def save(report: dict) -> int | None:
    """Persist a report dict; return its new id (or None when persistence is disabled)."""
    if not is_enabled():
        return None
    kind = report.get("scan_type", "page")
    url = report.get("url") or report.get("source") or ""
    created_at = report.get("fetched_at") or datetime.now(timezone.utc).isoformat()
    score = report.get("overall_score")
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO scans (kind, url, created_at, score, report) VALUES (?, ?, ?, ?, ?)",
            (kind, url, created_at, score, json.dumps(report)),
        )
        return cur.lastrowid


def history(url: str, *, kind: str | None = None, limit: int = 20) -> list[dict]:
    """Recent scans for a URL (newest first), as lightweight rows (no full report)."""
    if not is_enabled():
        return []
    q = "SELECT id, kind, url, created_at, score FROM scans WHERE url = ?"
    args: list = [url]
    if kind:
        q += " AND kind = ?"
        args.append(kind)
    q += " ORDER BY id DESC LIMIT ?"
    args.append(limit)
    with _conn() as conn:
        return [dict(r) for r in conn.execute(q, args).fetchall()]


def get(scan_id: int) -> dict | None:
    """Full stored report for an id, or None."""
    if not is_enabled():
        return None
    with _conn() as conn:
        row = conn.execute("SELECT report FROM scans WHERE id = ?", (scan_id,)).fetchone()
        return json.loads(row["report"]) if row else None


def previous(url: str, *, kind: str, before_id: int) -> dict | None:
    """The most recent prior report for the same url+kind (id < before_id), or None."""
    if not is_enabled():
        return None
    with _conn() as conn:
        row = conn.execute(
            "SELECT report FROM scans WHERE url = ? AND kind = ? AND id < ? ORDER BY id DESC LIMIT 1",
            (url, kind, before_id),
        ).fetchone()
        return json.loads(row["report"]) if row else None


def diff_reports(old: dict, new: dict) -> dict:
    """Compare two page/site reports → score + pillar deltas and finding-level changes.

    A finding "regresses" when it goes from pass/info to fail/warn, "resolves" the other way
    (or disappears), and is "new" when it appears already failing/warning.
    """
    def is_issue(status: str) -> bool:
        return status in ("fail", "warn")

    def by_id(report: dict) -> dict[str, dict]:
        return {f["id"]: f for f in report.get("findings", [])}

    old_f, new_f = by_id(old), by_id(new)
    resolved, regressed, new_issues = [], [], []

    for fid, f in new_f.items():
        if fid in old_f:
            was, now = old_f[fid]["status"], f["status"]
            if is_issue(was) and not is_issue(now):
                resolved.append({"id": fid, "title": f["title"]})
            elif not is_issue(was) and is_issue(now):
                regressed.append({"id": fid, "title": f["title"], "status": now})
        elif is_issue(f["status"]):
            new_issues.append({"id": fid, "title": f["title"], "status": f["status"]})

    for fid, f in old_f.items():  # a finding that vanished but was an issue is now resolved
        if fid not in new_f and is_issue(f["status"]):
            resolved.append({"id": fid, "title": f["title"]})

    old_p, new_p = old.get("pillar_scores", {}), new.get("pillar_scores", {})
    pillar_deltas = {k: new_p.get(k, 0) - old_p.get(k, 0) for k in set(old_p) | set(new_p)}

    return {
        "since": old.get("fetched_at"),
        "score_delta": (new.get("overall_score") or 0) - (old.get("overall_score") or 0),
        "pillar_deltas": pillar_deltas,
        "resolved": resolved,
        "regressed": regressed,
        "new_issues": new_issues,
    }


# --------------------------------------------------------------------------- monitors + alerts

_CADENCE_DAYS = {"daily": 1, "weekly": 7}


def _next_run(now: datetime, cadence: str) -> str:
    return (now + timedelta(days=_CADENCE_DAYS.get(cadence, 1))).isoformat()


def add_monitor(url: str, *, cadence: str = "daily", email: str | None = None) -> int | None:
    """Register a URL to monitor (due immediately). Returns its id, or None when persistence off."""
    if not is_enabled():
        return None
    cadence = cadence if cadence in _CADENCE_DAYS else "daily"
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO monitors (url, cadence, email, active, consecutive_failures, created_at, "
            "next_run_at) VALUES (?, ?, ?, 1, 0, ?, ?)",
            (url, cadence, email, now, now),
        )
        return cur.lastrowid


def list_monitors(*, active_only: bool = False) -> list[dict]:
    if not is_enabled():
        return []
    q = "SELECT * FROM monitors" + (" WHERE active = 1" if active_only else "") + " ORDER BY id"
    with _conn() as conn:
        return [dict(r) for r in conn.execute(q).fetchall()]


def get_monitor(monitor_id: int) -> dict | None:
    if not is_enabled():
        return None
    with _conn() as conn:
        r = conn.execute("SELECT * FROM monitors WHERE id = ?", (monitor_id,)).fetchone()
        return dict(r) if r else None


def delete_monitor(monitor_id: int) -> bool:
    if not is_enabled():
        return False
    with _conn() as conn:
        cur = conn.execute("DELETE FROM monitors WHERE id = ?", (monitor_id,))
        conn.execute("DELETE FROM alerts WHERE monitor_id = ?", (monitor_id,))
        return cur.rowcount > 0


def due_monitors(now: datetime | None = None) -> list[dict]:
    """Active monitors whose next_run_at has passed (or is unset)."""
    if not is_enabled():
        return []
    ts = (now or datetime.now(timezone.utc)).isoformat()
    with _conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM monitors WHERE active = 1 AND (next_run_at IS NULL OR next_run_at <= ?) "
            "ORDER BY id", (ts,),
        ).fetchall()]


def mark_run(monitor_id: int, *, ok: bool, now: datetime | None = None) -> None:
    """Record a run: advance next_run_at by cadence; reset failures on success, else increment."""
    if not is_enabled():
        return
    now = now or datetime.now(timezone.utc)
    with _conn() as conn:
        r = conn.execute("SELECT cadence, consecutive_failures FROM monitors WHERE id = ?",
                         (monitor_id,)).fetchone()
        if not r:
            return
        failures = 0 if ok else (r["consecutive_failures"] + 1)
        conn.execute(
            "UPDATE monitors SET last_run_at = ?, next_run_at = ?, consecutive_failures = ? WHERE id = ?",
            (now.isoformat(), _next_run(now, r["cadence"]), failures, monitor_id),
        )


def record_alert(monitor_id: int, scan_id: int | None, alert: dict) -> int | None:
    if not is_enabled():
        return None
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO alerts (monitor_id, scan_id, type, severity, summary, detail, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (monitor_id, scan_id, alert["type"], alert["severity"], alert["summary"],
             json.dumps(alert.get("detail")), now),
        )
        return cur.lastrowid


def list_alerts(monitor_id: int | None = None, *, limit: int = 50) -> list[dict]:
    if not is_enabled():
        return []
    q, args = "SELECT * FROM alerts", []
    if monitor_id is not None:
        q += " WHERE monitor_id = ?"
        args.append(monitor_id)
    q += " ORDER BY id DESC LIMIT ?"
    args.append(max(1, min(limit, 200)))
    with _conn() as conn:
        rows = [dict(r) for r in conn.execute(q, args).fetchall()]
    for r in rows:
        if r.get("detail"):
            try:
                r["detail"] = json.loads(r["detail"])
            except (json.JSONDecodeError, TypeError):
                pass
    return rows
