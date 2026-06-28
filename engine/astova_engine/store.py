"""Scan history — a small persistence layer so re-scanning a URL can show what changed.

Two interchangeable backends sit behind the same public functions (the seam):

- **Postgres** when ``ASTOVA_DATABASE_URL`` is set (e.g. a Supabase connection string).
  Requires the ``postgres`` extra (``pip install -e ".[postgres]"`` → psycopg 3). Durable —
  survives container redeploys, shared across workers. This is the production path.
- **SQLite** when only ``ASTOVA_DB_PATH`` is set (stdlib, no dependency). Good for local dev.
  Note: SQLite on an ephemeral container disk resets on redeploy — use Postgres in production.
- **Disabled** when neither is set: every function is a graceful no-op (save -> None,
  history -> []), so the engine runs identically with or without persistence.

Postgres wins if both env vars are set. The two schemas differ only in the id column
(autoincrement vs identity); everything else (TEXT columns, JSON-as-text) is identical so the
diff/compare logic above the seam is backend-agnostic.
"""

from __future__ import annotations

import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone


def database_url() -> str | None:
    return os.environ.get("ASTOVA_DATABASE_URL") or None


def db_path() -> str | None:
    return os.environ.get("ASTOVA_DB_PATH") or None


def _backend() -> str | None:
    """Which storage backend is active: 'postgres', 'sqlite', or None (disabled)."""
    if database_url():
        return "postgres"
    if db_path():
        return "sqlite"
    return None


def is_enabled() -> bool:
    return _backend() is not None


def _ph(sql: str, dialect: str) -> str:
    """Translate the canonical '?' placeholder style to the backend's. SQL here never
    contains a literal '?' in a string value, so a blunt replace is safe."""
    return sql.replace("?", "%s") if dialect == "postgres" else sql


class _DB:
    """Thin dialect-aware wrapper so call sites write one SQL string for both backends."""

    def __init__(self, conn, dialect: str):
        self._conn = conn
        self.dialect = dialect

    def execute(self, sql: str, params: tuple | list = ()):  # returns a cursor
        return self._conn.execute(_ph(sql, self.dialect), params)

    def insert(self, sql: str, params: tuple | list = ()) -> int:
        """Run an INSERT and return the new row's id (handles RETURNING vs lastrowid)."""
        if self.dialect == "postgres":
            cur = self._conn.execute(_ph(sql, self.dialect) + " RETURNING id", params)
            return cur.fetchone()["id"]
        cur = self._conn.execute(sql, params)
        return cur.lastrowid


@contextmanager
def _conn():
    backend = _backend()
    if backend == "postgres":
        import psycopg
        from psycopg.rows import dict_row

        conn = psycopg.connect(database_url(), row_factory=dict_row)
    elif backend == "sqlite":
        conn = sqlite3.connect(db_path())
        conn.row_factory = sqlite3.Row
    else:
        raise RuntimeError("persistence not configured (set ASTOVA_DATABASE_URL or ASTOVA_DB_PATH)")
    db = _DB(conn, backend)
    try:
        _ensure_schema(db)
        yield db
        conn.commit()
    finally:
        conn.close()


def _ensure_schema(db: _DB) -> None:
    # The only cross-dialect difference is the auto-incrementing primary key.
    pk = (
        "id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY"
        if db.dialect == "postgres"
        else "id INTEGER PRIMARY KEY AUTOINCREMENT"
    )
    db.execute(f"""CREATE TABLE IF NOT EXISTS scans (
            {pk},
            kind TEXT NOT NULL,
            url TEXT NOT NULL,
            created_at TEXT NOT NULL,
            score INTEGER,
            report TEXT NOT NULL,
            token TEXT
        )""")
    db.execute("CREATE INDEX IF NOT EXISTS idx_scans_url_kind ON scans(url, kind, id)")
    # scans.token = unguessable capability id for shareable report links (not enumerable,
    # unlike the integer id). Present in the CREATE above for fresh installs; ALTER in for
    # tables created before this column existed. Idempotent on every startup.
    if db.dialect == "postgres":
        db.execute("ALTER TABLE scans ADD COLUMN IF NOT EXISTS token TEXT")
    else:
        try:
            db.execute("ALTER TABLE scans ADD COLUMN token TEXT")
        except sqlite3.OperationalError:
            pass  # column already exists
    db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_scans_token ON scans(token)")
    db.execute(f"""CREATE TABLE IF NOT EXISTS monitors (
            {pk},
            url TEXT NOT NULL,
            cadence TEXT NOT NULL DEFAULT 'daily',
            email TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            consecutive_failures INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            last_run_at TEXT,
            next_run_at TEXT
        )""")
    db.execute(f"""CREATE TABLE IF NOT EXISTS alerts (
            {pk},
            monitor_id INTEGER NOT NULL,
            scan_id INTEGER,
            type TEXT NOT NULL,
            severity TEXT NOT NULL,
            summary TEXT NOT NULL,
            detail TEXT,
            created_at TEXT NOT NULL
        )""")
    db.execute("CREATE INDEX IF NOT EXISTS idx_alerts_monitor ON alerts(monitor_id, id)")
    db.execute(f"""CREATE TABLE IF NOT EXISTS notes (
            {pk},
            url TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""")
    db.execute("CREATE INDEX IF NOT EXISTS idx_notes_url ON notes(url, id)")


def save(report: dict) -> int | None:
    """Persist a report dict; return its new id (or None when persistence is disabled)."""
    if not is_enabled():
        return None
    kind = report.get("scan_type", "page")
    url = report.get("url") or report.get("source") or ""
    created_at = report.get("fetched_at") or datetime.now(timezone.utc).isoformat()
    score = report.get("overall_score")
    # Capability token for shareable links — stamped into the report itself so a fetched copy
    # carries its own token (re-shareable), and links are unguessable rather than enumerable.
    token = secrets.token_urlsafe(16)
    report.setdefault("meta", {})["scan_token"] = token
    with _conn() as db:
        return db.insert(
            "INSERT INTO scans (kind, url, created_at, score, report, token) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (kind, url, created_at, score, json.dumps(report), token),
        )


def history(url: str, *, kind: str | None = None, limit: int = 20) -> list[dict]:
    """Recent scans for a URL (newest first), as lightweight rows (no full report)."""
    if not is_enabled():
        return []
    q = "SELECT id, kind, url, created_at, score, token FROM scans WHERE url = ?"
    args: list = [url]
    if kind:
        q += " AND kind = ?"
        args.append(kind)
    q += " ORDER BY id DESC LIMIT ?"
    args.append(limit)
    with _conn() as db:
        return [dict(r) for r in db.execute(q, args).fetchall()]


def get(scan_id: int) -> dict | None:
    """Full stored report for an integer id, or None. Internal use only — never exposed in a
    URL (it's enumerable). Public/shareable lookups go through get_by_token()."""
    if not is_enabled():
        return None
    with _conn() as db:
        row = db.execute("SELECT report FROM scans WHERE id = ?", (scan_id,)).fetchone()
        return json.loads(row["report"]) if row else None


def get_by_token(token: str) -> dict | None:
    """Full stored report for a share token, or None. Tokens are unguessable, so this is the
    only lookup path safe to expose in a public URL."""
    if not is_enabled() or not token:
        return None
    with _conn() as db:
        row = db.execute("SELECT report FROM scans WHERE token = ?", (token,)).fetchone()
        return json.loads(row["report"]) if row else None


def previous(url: str, *, kind: str, before_id: int) -> dict | None:
    """The most recent prior report for the same url+kind (id < before_id), or None."""
    if not is_enabled():
        return None
    with _conn() as db:
        row = db.execute(
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
    with _conn() as db:
        return db.insert(
            "INSERT INTO monitors (url, cadence, email, active, consecutive_failures, created_at, "
            "next_run_at) VALUES (?, ?, ?, 1, 0, ?, ?)",
            (url, cadence, email, now, now),
        )


def list_monitors(*, active_only: bool = False) -> list[dict]:
    if not is_enabled():
        return []
    q = "SELECT * FROM monitors" + (" WHERE active = 1" if active_only else "") + " ORDER BY id"
    with _conn() as db:
        return [dict(r) for r in db.execute(q).fetchall()]


def get_monitor(monitor_id: int) -> dict | None:
    if not is_enabled():
        return None
    with _conn() as db:
        r = db.execute("SELECT * FROM monitors WHERE id = ?", (monitor_id,)).fetchone()
        return dict(r) if r else None


def delete_monitor(monitor_id: int) -> bool:
    if not is_enabled():
        return False
    with _conn() as db:
        cur = db.execute("DELETE FROM monitors WHERE id = ?", (monitor_id,))
        db.execute("DELETE FROM alerts WHERE monitor_id = ?", (monitor_id,))
        return cur.rowcount > 0


def due_monitors(now: datetime | None = None) -> list[dict]:
    """Active monitors whose next_run_at has passed (or is unset)."""
    if not is_enabled():
        return []
    ts = (now or datetime.now(timezone.utc)).isoformat()
    with _conn() as db:
        return [
            dict(r)
            for r in db.execute(
                "SELECT * FROM monitors WHERE active = 1 AND (next_run_at IS NULL OR next_run_at <= ?) "
                "ORDER BY id",
                (ts,),
            ).fetchall()
        ]


def mark_run(monitor_id: int, *, ok: bool, now: datetime | None = None) -> None:
    """Record a run: advance next_run_at by cadence; reset failures on success, else increment."""
    if not is_enabled():
        return
    now = now or datetime.now(timezone.utc)
    with _conn() as db:
        r = db.execute(
            "SELECT cadence, consecutive_failures FROM monitors WHERE id = ?", (monitor_id,)
        ).fetchone()
        if not r:
            return
        failures = 0 if ok else (r["consecutive_failures"] + 1)
        db.execute(
            "UPDATE monitors SET last_run_at = ?, next_run_at = ?, consecutive_failures = ? WHERE id = ?",
            (now.isoformat(), _next_run(now, r["cadence"]), failures, monitor_id),
        )


def record_alert(monitor_id: int, scan_id: int | None, alert: dict) -> int | None:
    if not is_enabled():
        return None
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as db:
        return db.insert(
            "INSERT INTO alerts (monitor_id, scan_id, type, severity, summary, detail, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                monitor_id,
                scan_id,
                alert["type"],
                alert["severity"],
                alert["summary"],
                json.dumps(alert.get("detail")),
                now,
            ),
        )


def list_alerts(monitor_id: int | None = None, *, limit: int = 50) -> list[dict]:
    if not is_enabled():
        return []
    q, args = "SELECT * FROM alerts", []
    if monitor_id is not None:
        q += " WHERE monitor_id = ?"
        args.append(monitor_id)
    q += " ORDER BY id DESC LIMIT ?"
    args.append(max(1, min(limit, 200)))
    with _conn() as db:
        rows = [dict(r) for r in db.execute(q, args).fetchall()]
    for r in rows:
        if r.get("detail"):
            try:
                r["detail"] = json.loads(r["detail"])
            except (json.JSONDecodeError, TypeError):
                pass
    return rows


# --- notes -------------------------------------------------------------------------------
# A per-site running log the user keeps alongside a URL's scan history ("rewrote intros 28 Jun").


def add_note(url: str, body: str) -> int | None:
    """Add a note to a site's log; return its id (or None when disabled / body empty)."""
    if not is_enabled():
        return None
    body = (body or "").strip()
    if not body:
        return None
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as db:
        return db.insert(
            "INSERT INTO notes (url, body, created_at) VALUES (?, ?, ?)", (url, body, now)
        )


def list_notes(url: str, *, limit: int = 200) -> list[dict]:
    """Notes for a URL, newest first."""
    if not is_enabled():
        return []
    with _conn() as db:
        return [
            dict(r)
            for r in db.execute(
                "SELECT id, url, body, created_at FROM notes WHERE url = ? ORDER BY id DESC LIMIT ?",
                (url, max(1, min(limit, 500))),
            ).fetchall()
        ]


def delete_note(note_id: int) -> bool:
    """Delete a note; True if a row was removed."""
    if not is_enabled():
        return False
    with _conn() as db:
        return db.execute("DELETE FROM notes WHERE id = ?", (note_id,)).rowcount > 0
