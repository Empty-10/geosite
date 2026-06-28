# Astova

GEO-first website intelligence platform — high-accuracy GEO (Generative Engine
Optimization) reports backed by a deterministic technical/SEO engine.

> Codename `Astova` is a placeholder. See `CLAUDE.md` for the full vision, architecture,
> strategy, and build roadmap — read that first.

## What's here now

The **scan engine core** (`engine/`) — the foundation everything else sits on. Give it a
URL and it returns a scored report of on-page, technical, and GEO-readiness findings, each
tagged with a confidence label (`VERIFIED` / `MEASURED` / `ESTIMATED`).

## Quick start

```bash
cd engine
python -m venv .venv && source .venv/bin/activate
pip install -e .

python -m astova_engine https://example.com          # human-readable report
python -m astova_engine https://example.com --json    # JSON
pytest                                                # run offline tests
```

## Project layout

| Path | What |
|------|------|
| `engine/` | Python scan engine (start here) |
| `web/` | Next.js app — scaffold later (`web/README.md`) |
| `docs/` | Architecture doc + competitive notes |
| `CLAUDE.md` | Source-of-truth context for the whole project |

## Status

Phase 0 — engine skeleton. See the roadmap in `CLAUDE.md`.
