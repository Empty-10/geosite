# Deploy the damask scan engine as an HTTP service (FastAPI) on any container host
# (Render, Railway, Fly.io, …). The Next.js web app on Vercel then points at it via
# DAMASK_ENGINE_URL and POSTs scans to /scan instead of shelling out to Python.
#
#   docker build -t damask-engine .
#   docker run -p 8000:8000 damask-engine      # → http://localhost:8000/health
#
# Note: Playwright rendering (--render) is intentionally NOT installed here to keep the
# image small; the web /api/scan path doesn't request rendering.

FROM python:3.12-slim

WORKDIR /app

# Install the engine + the FastAPI service extra + the MCP extra (so /mcp is served too).
COPY pyproject.toml ./
COPY damask_engine ./damask_engine
RUN pip install --no-cache-dir -e ".[service,mcp]"

# Hosts (Render/Railway/Fly) inject $PORT; default to 8000 locally.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn damask_engine.service:app --host 0.0.0.0 --port ${PORT:-8000}"]
