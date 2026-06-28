# web — astova landing app (Next.js)

The marketing/landing app, built from the approved Claude Design prototype
(`design/landing-prototype.html`) as real React components. Dark-mode-first, Geist type,
signal-green accent, and the verified-vs-measured confidence grammar.

## Run

```bash
cd web
npm install
npm run dev      # http://localhost:3000
```

The live-scan demo (`/api/scan`) shells out to the local Python engine, so set the engine
up once first (the route looks for `../engine/.venv/bin/python` by default):

```bash
cd ../engine
python -m venv .venv && ./.venv/bin/pip install -e .
```

Build for production:

```bash
npm run build && npm run start
```

## Structure

```
app/
  layout.tsx        root layout + metadata
  globals.css       design tokens (CSS variables) + fonts + keyframes
  page.tsx          landing page (assembles the sections)
components/
  Nav, Hero, HeroDemo, Confidence, Features, Pricing, AgencyCta, Footer, Logo
lib/
  tokens.ts         JS copies of the palette + scoreColor() for the live demo
```

`HeroDemo.tsx` is the interactive live-scan demo (a client component). It POSTs the URL to
`app/api/scan/route.ts`, which runs the **real** engine and returns its JSON `Report`; the
score ring, pillar cards, and priority-fix list are all driven by that response. Pillars
the engine doesn't run yet (Performance) render as "not run yet"; the citation-share block
is a clearly-labelled *sample* preview (MEASURED sampling is a later phase — never faked).

### `/api/scan`

`POST { "url": "example.com" }` → the engine's JSON report, or `{ "error": "..." }`.
It normalizes the URL, rejects loopback/private hosts (basic SSRF guard), and runs the
engine with a 25s timeout. Engine invocation is env-configurable:

| Env var | Default | Purpose |
|---|---|---|
| `ASTOVA_ENGINE_URL` | _(unset)_ | If set, POST the scan to this engine HTTP service (e.g. `http://localhost:8000`) instead of shelling out. The production path — see the FastAPI service in `engine/` (`uvicorn astova_engine.service:app`). Vercel has no Python runtime, so deployed builds must use this. |
| `ASTOVA_ENGINE_DIR` | `../engine` | Engine working directory. |
| `ASTOVA_PYTHON` | `<engine>/.venv/bin/python` | Python interpreter that has the engine installed. |

## Design source of truth

- `docs/claude-design-brief.md` — palette (exact hex, light + dark), type, motion, rules.
- `design/landing-prototype.html` — the original Claude Design prototype (reference only;
  it uses Claude Design's runtime and does not run standalone).
