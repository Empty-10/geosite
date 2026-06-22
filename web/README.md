# web — damask landing app (Next.js)

The marketing/landing app, built from the approved Claude Design prototype
(`design/landing-prototype.html`) as real React components. Dark-mode-first, Geist type,
signal-green accent, and the verified-vs-measured confidence grammar.

## Run

```bash
cd web
npm install
npm run dev      # http://localhost:3000
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

`HeroDemo.tsx` is the interactive live-scan demo (a client component). The scan numbers
are currently mocked; wiring it to the real Python engine (or a `/api/scan` route that
calls it) is the next step. See the root `CLAUDE.md` roadmap.

## Design source of truth

- `docs/claude-design-brief.md` — palette (exact hex, light + dark), type, motion, rules.
- `design/landing-prototype.html` — the original Claude Design prototype (reference only;
  it uses Claude Design's runtime and does not run standalone).
