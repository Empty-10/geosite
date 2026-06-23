"""Scan history — a small persistence layer so re-scanning a URL can show what changed.

Backed by SQLite (stdlib, no new dependency). Enabled only when DAMASK_DB_PATH is set; otherwise
every function is a graceful no-op (save -> None, history -> []), so the engine runs identically
with or without persistence.

Production note: SQLite on an ephemeral container disk (e.g. Render's default) resets on redeploy.
For durable history, point DAMASK_DB_PATH at a persistent disk, or swap this module's storage for
Postgres later (the public functions are the seam).
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone


def db_path() -> str | None:
    return os.environ.get("DAMASK_DB_PATH") or None


def is_enabled() -> bool:
    return db_path() is not None


@contextmanager
def _conn():
    path = db_path()
    if not path:
        raise RuntimeError("persistence not configured (set DAMASK_DB_PATH)")
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
