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
"""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from .scanner import scan

app = FastAPI(title="damask engine", version="1", description="GEO/SEO scan engine.")


class ScanRequest(BaseModel):
    url: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/scan")
def scan_endpoint(req: ScanRequest) -> dict:
    """Run a full scan and return the report dict. Failures surface in meta.error."""
    return scan(req.url, fixes=True).to_dict()
