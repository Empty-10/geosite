"""FastAPI wrapper around the scan engine.

Lets the web app reach the engine over HTTP instead of spawning a Python process — the
production path (web on Vercel, which has no Python runtime; engine on a container host).
The web route uses this when DAMASK_ENGINE_URL is set; otherwise it shells out locally.
See docs/PROJECT-STATUS.md → "Next tasks" #1.

Install:  pip install -e ".[service]"
Run:      uvicorn damask_engine.service:app --host 0.0.0.0 --port 8000

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

import threading
import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from . import store
from .cloudflare_logs import fetch_cloudflare_logs
from .crawl import crawl
from .crawler_logs import analyze_logs
from .scanner import scan

app = FastAPI(title="damask engine", version="1", description="GEO/SEO scan engine.")

# In-memory crawl jobs. Fine for the single Render instance; evicted oldest-first past a cap.
_MAX_JOBS = 200
_MAX_PAGES_CAP = 50
_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()


class ScanRequest(BaseModel):
    url: str


class CrawlRequest(BaseModel):
    url: str
    max_pages: int = 25


class LogsRequest(BaseModel):
    text: str
    source: str = "uploaded log"


class CloudflareLogsRequest(BaseModel):
    domain: str
    days: int = 7


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/scan")
def scan_endpoint(req: ScanRequest) -> dict:
    """Run a full scan and return the report dict. Failures surface in meta.error.

    When persistence is enabled (DAMASK_DB_PATH), the scan is saved and the response carries
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


@app.get("/history")
def history_endpoint(url: str, kind: str = "page", limit: int = 20) -> dict:
    """List recent saved scans for a URL (newest first). Empty when persistence is off."""
    return {"url": url, "kind": kind, "scans": store.history(url, kind=kind, limit=max(1, min(limit, 100)))}


@app.get("/scans/{scan_id}")
def get_scan_endpoint(scan_id: int) -> dict:
    """Fetch a stored report by id."""
    report = store.get(scan_id)
    if report is None:
        raise HTTPException(status_code=404, detail="scan not found")
    return report


@app.post("/logs")
def logs_endpoint(req: LogsRequest) -> dict:
    """Analyze access-log text for AI-crawler activity. Fast/synchronous; bounded internally."""
    return analyze_logs(req.text, source=req.source).to_dict()


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
