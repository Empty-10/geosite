"""FastAPI wrapper around the scan engine.

Lets the web app reach the engine over HTTP instead of spawning a Python process — the
production path (web on Vercel, which has no Python runtime; engine on a container host).
The web route uses this when ASTOVA_ENGINE_URL is set; otherwise it shells out locally.
See docs/PROJECT-STATUS.md → "Next tasks" #1.

Install:  pip install -e ".[service]"
Run:      uvicorn astova_engine.service:app --host 0.0.0.0 --port 8000

Contract (mirrors the CLI's --json output so the route handles both paths identically):
  POST /scan  {"url": "..."}  ->  200 + Report.to_dict()
The engine reports fetch/scan failures in the report's `meta.error` field rather than
raising, so a failed scan is still a 200 with an error inside — the caller inspects
meta.error. Only malformed requests yield non-200 (422 from validation).

Site crawl is asynchronous because it runs long (many pages): the job runs in a background
thread on this single-instance service and the caller polls.
  POST /crawl        {"url": "...", "max_pages": N}  ->  {"job_id", "status": "running"}
  GET  /crawl/{id}   ->  {"status": "running"|"done"|"error", "progress": {...}, "result"?, "error"?}
"""

from __future__ import annotations

import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from . import fixes, knowledge, monitoring, store
from .cloudflare_logs import fetch_cloudflare_logs
from .compare import compare_reports
from .config import get_pagespeed_key
from .crawl import crawl
from .crawler_logs import analyze_logs
from .fetch import fetch_pagespeed
from .models import Report
from .modules import performance as performance_mod
from .scanner import scan

# Optional remote MCP endpoint (Streamable HTTP). Mounted at /mcp when the [mcp] extra is
# installed, so claude.ai / Claude Desktop can call audit_url & scan_url over HTTP. Without the
# extra the REST API still works exactly the same — the mount is simply skipped.
try:
    from mcp.server.transport_security import TransportSecuritySettings

    from .mcp_server import mcp as _mcp

    _mcp.settings.stateless_http = True       # no per-session state — fine for our scan tools
    _mcp.settings.streamable_http_path = "/"  # so mounting at /mcp gives the endpoint /mcp
    # DNS-rebinding protection defaults to localhost-only, which 421s a public host (Render). This
    # is a public endpoint reached at an arbitrary host, so turn it off.
    _mcp.settings.transport_security = TransportSecuritySettings(enable_dns_rebinding_protection=False)
    _mcp_app = _mcp.streamable_http_app()

    @asynccontextmanager
    async def _lifespan(_app: "FastAPI"):
        async with _mcp.session_manager.run():
            yield

    _LIFESPAN = _lifespan
except Exception:  # noqa: BLE001 — [mcp] not installed; REST API runs without /mcp
    _mcp_app = None
    _LIFESPAN = None

app = FastAPI(title="astova engine", version="1", description="GEO/SEO scan engine.",
              lifespan=_LIFESPAN)

# In-memory crawl jobs. Fine for the single Render instance; evicted oldest-first past a cap.
_MAX_JOBS = 200
_MAX_PAGES_CAP = 50
_MAX_COMPARE = 4  # your page + up to 3 competitors
_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()


class ScanRequest(BaseModel):
    url: str


class CrawlRequest(BaseModel):
    url: str
    max_pages: int = 25


class CompareRequest(BaseModel):
    urls: list[str]


class MonitorCreate(BaseModel):
    url: str
    cadence: str = "daily"
    email: str | None = None


class NoteCreate(BaseModel):
    url: str
    body: str


class LogsRequest(BaseModel):
    text: str
    source: str = "uploaded log"


class CloudflareLogsRequest(BaseModel):
    domain: str
    days: int = 7


class PerformanceRequest(BaseModel):
    url: str
    strategy: str = "mobile"


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/scan")
def scan_endpoint(req: ScanRequest) -> dict:
    """Run a full scan and return the report dict. Failures surface in meta.error.

    When persistence is enabled (ASTOVA_DB_PATH), the scan is saved and the response carries
    meta.scan_id plus meta.diff (vs the previous scan of the same URL) for change tracking.
    """
    report = scan(req.url, fixes=True).to_dict()
    if not report.get("meta", {}).get("error") and store.is_enabled():
        scan_id = store.save(report)
        report.setdefault("meta", {})["scan_id"] = scan_id
        prev = store.previous(report.get("url", ""), kind="page", before_id=scan_id)
        if prev:
            report["meta"]["diff"] = store.diff_reports(prev, report)
    return report


def _safe_scan(url: str) -> Report:
    """Scan one URL for the comparison, never raising — a fetch failure becomes meta.error so one
    bad competitor URL doesn't sink the whole benchmark."""
    try:
        return scan(url, fixes=False)
    except Exception as exc:  # noqa: BLE001
        return Report(url=url, meta={"error": f"{type(exc).__name__}: {exc}"})


@app.post("/compare")
def compare_endpoint(req: CompareRequest) -> dict:
    """Scan 2–4 pages concurrently and return a deterministic side-by-side benchmark.

    The first URL is treated as the primary site ("you"); the rest are competitors. No external
    APIs, no LLM — just N scans and a row-by-row comparison of their scorecards.
    """
    urls = [u.strip() for u in req.urls if u and u.strip()][:_MAX_COMPARE]
    if len(urls) < 2:
        raise HTTPException(status_code=400, detail="Provide at least 2 URLs to compare.")
    with ThreadPoolExecutor(max_workers=len(urls)) as ex:
        reports = list(ex.map(_safe_scan, urls))  # map preserves input order
    return {"count": len(urls), "comparison": compare_reports(reports)}


def _require_persistence() -> None:
    if not store.is_enabled():
        raise HTTPException(status_code=503, detail="Persistence is off — set ASTOVA_DB_PATH.")


@app.post("/monitors")
def create_monitor(req: MonitorCreate) -> dict:
    """Register a URL to monitor on a cadence (daily|weekly)."""
    _require_persistence()
    mid = store.add_monitor(req.url, cadence=req.cadence, email=req.email)
    return {"id": mid, "url": req.url, "cadence": req.cadence}


@app.get("/monitors")
def list_monitors_endpoint() -> dict:
    return {"monitors": store.list_monitors()}


@app.delete("/monitors/{monitor_id}")
def delete_monitor_endpoint(monitor_id: int) -> dict:
    _require_persistence()
    if not store.delete_monitor(monitor_id):
        raise HTTPException(status_code=404, detail="monitor not found")
    return {"deleted": monitor_id}


@app.get("/monitors/{monitor_id}/alerts")
def monitor_alerts_endpoint(monitor_id: int, limit: int = 50) -> dict:
    return {"monitor_id": monitor_id, "alerts": store.list_alerts(monitor_id, limit=limit)}


@app.post("/monitors/run-due")
def run_due_endpoint(x_astova_cron: str | None = Header(default=None)) -> dict:
    """Scan every monitor whose next run is due, diff vs the previous scan, evaluate the alert
    rules (with anti-noise) and record any alerts. Triggered by an external cron.

    Guarded by a shared secret when ASTOVA_CRON_SECRET is set (the X-Astova-Cron header).
    """
    secret = os.environ.get("ASTOVA_CRON_SECRET")
    if secret and x_astova_cron != secret:
        raise HTTPException(status_code=401, detail="bad or missing cron secret")
    _require_persistence()

    results = []
    for m in store.due_monitors():
        report = scan(m["url"], fixes=False).to_dict()
        failed = bool(report.get("meta", {}).get("error"))
        scan_id = store.save(report) if not failed else None
        prev = store.previous(report.get("url", ""), kind="page", before_id=scan_id) if scan_id else None
        diff = store.diff_reports(prev, report) if prev else None

        res = monitoring.evaluate(m["url"], report, prev, diff, m["consecutive_failures"])
        for alert in res["alerts"]:
            store.record_alert(m["id"], scan_id, alert)
        store.mark_run(m["id"], ok=res["ok"])
        results.append({"monitor_id": m["id"], "url": m["url"], "ok": res["ok"],
                        "alerts": len(res["alerts"])})

    return {"ran": len(results), "results": results}


@app.get("/history")
def history_endpoint(url: str, kind: str = "page", limit: int = 20) -> dict:
    """List recent saved scans for a URL (newest first). Empty when persistence is off."""
    return {"url": url, "kind": kind, "scans": store.history(url, kind=kind, limit=max(1, min(limit, 100)))}


@app.get("/findings")
def list_findings_endpoint() -> dict:
    """The knowledge index: every finding Astova can explain, with its category and automation level."""
    return {"findings": knowledge.list_cards()}


@app.get("/findings/{finding_id}")
def explain_finding_endpoint(finding_id: str) -> dict:
    """Structured fix knowledge for a single finding id (e.g. geo.aeo, schema.missing): why it
    matters for AI engines, how to fix it, and how an AI coding agent should approach it safely."""
    result = knowledge.explain(finding_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Unknown finding id '{finding_id}'")
    return result


class FixContext(BaseModel):
    url: str = ""
    html: str | None = None


@app.post("/findings/{finding_id}/fix")
def generate_fix_endpoint(finding_id: str, ctx: FixContext) -> dict:
    """Deterministically generate a ready-to-apply fix for a supported finding (no LLM, not applied).
    Body is the context: {"url": "...", "html"?: "..."}. Returns the consistent fix response object.
    Supported today: schema.missing, geo.faq, tech.robots.missing, tech.robots.ai, tech.llms_txt,
    canonical, tech.viewport."""
    return fixes.generate_fix(finding_id, {"url": ctx.url, "html": ctx.html})


@app.get("/notes")
def list_notes_endpoint(url: str) -> dict:
    """A site's running note log, newest first. Empty when persistence is off."""
    return {"url": url, "notes": store.list_notes(url)}


@app.post("/notes")
def create_note_endpoint(req: NoteCreate) -> dict:
    """Add a note to a site's log."""
    _require_persistence()
    note_id = store.add_note(req.url, req.body)
    if note_id is None:
        raise HTTPException(status_code=400, detail="note body is empty")
    return {"id": note_id, "url": req.url}


@app.delete("/notes/{note_id}")
def delete_note_endpoint(note_id: int) -> dict:
    """Delete a note."""
    _require_persistence()
    return {"deleted": note_id if store.delete_note(note_id) else None}


@app.get("/scans/{token}")
def get_scan_endpoint(token: str) -> dict:
    """Fetch a stored report by its share token. Tokens are unguessable capability ids; the
    integer row id is deliberately NOT a lookup path here, so saved reports can't be enumerated."""
    report = store.get_by_token(token)
    if report is None:
        raise HTTPException(status_code=404, detail="scan not found")
    return report


@app.post("/logs")
def logs_endpoint(req: LogsRequest) -> dict:
    """Analyze access-log text for AI-crawler activity. Fast/synchronous; bounded internally."""
    return analyze_logs(req.text, source=req.source).to_dict()


@app.post("/performance")
def performance_endpoint(req: PerformanceRequest) -> dict:
    """Run only the PageSpeed/Lighthouse performance check for a URL (on-demand; slow).

    Returns the Performance pillar score + findings so the report can merge them in. PSI is a
    single blocking lab run (~10–30s) with no progress stream — failures surface in `error`.
    """
    strategy = req.strategy if req.strategy in ("mobile", "desktop") else "mobile"
    psi = fetch_pagespeed(req.url, get_pagespeed_key(), strategy=strategy)
    if psi is None:
        return {"pillar": "performance", "score": None, "findings": [],
                "error": "PageSpeed Insights was unavailable for this URL."}
    return {
        "pillar": "performance",
        "strategy": strategy,
        "score": performance_mod.pillar_score(psi),
        "findings": [f.to_dict() for f in performance_mod.analyze(psi)],
    }


@app.post("/cloudflare-logs")
def cloudflare_logs_endpoint(req: CloudflareLogsRequest) -> dict:
    """Pull AI-crawler activity for a domain from Cloudflare analytics. Errors surface in meta.error."""
    days = max(1, min(req.days, 30))
    return fetch_cloudflare_logs(req.domain, days=days).to_dict()


def _run_crawl(job_id: str, url: str, max_pages: int) -> None:
    def on_progress(done: int, current: str) -> None:
        with _jobs_lock:
            if job_id in _jobs:
                _jobs[job_id]["progress"] = {"pages_crawled": done, "current": current}

    try:
        site = crawl(url, max_pages=max_pages, on_progress=on_progress)
        err = site.meta.get("error")
        with _jobs_lock:
            if job_id in _jobs:
                _jobs[job_id].update(status="error" if err else "done",
                                     result=site.to_dict(), error=err)
    except Exception as exc:  # never let a worker thread die silently
        with _jobs_lock:
            if job_id in _jobs:
                _jobs[job_id].update(status="error", error=f"{type(exc).__name__}: {exc}")


@app.post("/crawl")
def start_crawl(req: CrawlRequest) -> dict:
    """Start a site crawl in the background and return a job id to poll."""
    job_id = uuid.uuid4().hex[:12]
    max_pages = max(1, min(req.max_pages, _MAX_PAGES_CAP))
    with _jobs_lock:
        if len(_jobs) >= _MAX_JOBS:
            del _jobs[next(iter(_jobs))]  # evict oldest (dicts keep insertion order)
        _jobs[job_id] = {"status": "running", "url": req.url,
                         "progress": {"pages_crawled": 0}, "max_pages": max_pages}
    threading.Thread(target=_run_crawl, args=(job_id, req.url, max_pages), daemon=True).start()
    return {"job_id": job_id, "status": "running"}


@app.get("/crawl/{job_id}")
def crawl_status(job_id: str) -> dict:
    """Poll a crawl job. 404 once it's evicted or never existed."""
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="unknown or expired job")
        return {"job_id": job_id, **job}


# Remote MCP endpoint at /mcp (Streamable HTTP). Last, so it doesn't shadow the REST routes.
if _mcp_app is not None:
    app.mount("/mcp", _mcp_app)
