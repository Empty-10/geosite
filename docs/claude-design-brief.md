# damask — Claude Design brief

Paste this into Claude Design to start from a real spec. It defines the product, the
design principles, the exact palette (light + dark), typography, motion, components, and
the screens to design. Codename **damask** (placeholder).

---

## 1. What the product is

damask is a website-scanning platform that produces high-accuracy **GEO** (Generative
Engine Optimization) reports — how well a site is positioned to be cited by AI answer
engines (ChatGPT, Google AI Overviews, Perplexity, Gemini, Claude) — backed by a
deterministic technical/SEO engine.

Audience: SEO/marketing professionals and agencies. Reports are shown to clients, so the
UI must look credible and be clean enough to white-label.

**Positioning in one line:** the GEO tool that's honest — it separates *verified fact*
from *measured estimate*, and tells you what to fix, not just what's wrong.

## 2. Design principles (the soul of it)

- **Calm precision — an instrument, not a toy.** It should feel like a credible analytics
  tool (think Linear, Vercel, Stripe dashboard, Raycast). Clean surfaces, generous space,
  data legible at a glance.
- **Dark-mode-first**, with an equally clean light mode. Never beige/cream — cool neutrals.
- **Restraint reads as trust.** No gradients, glow, neon, or decorative effects. The
  product is positioned *against* hype tools that overclaim; the design must not look hype.
- **Motion only where it means something.** The one place motion earns its keep is a scan
  running (modules ticking complete, the score counting up once on arrival). Everywhere
  else: near-invisible (a 150ms expand when opening a finding). No parallax, no autoplay.
- **Progressive disclosure, never popups.** Do not fire scores/recommendations at the user
  in popups. A finding is one calm row; click to expand its evidence and fix in place.
- **The confidence system is the brand, made visible.** Verified facts look *solid*;
  measured estimates look *banded/ranged*. This visual grammar is consistent everywhere and
  is the single most important distinctive element. No competitor does it.

## 3. Colour palette — "Ink + signal green"

Rationale: the category is saturated with purple ("AI") and blue/orange ("SEO"). Green is
open territory and is semantically perfect here — it already means verified / healthy /
pass / go, which is what the scoring is about. Brand colour and "this is good" become the
same signal. Stepping out of the purple lane *is* the credibility play.

One neutral base + one signature accent (green). Semantic colours are reserved strictly for
meaning. To avoid an amber clash, **measured uses blue, not amber.**

### Dark mode (primary)

| Token | Hex | Use |
|---|---|---|
| Page background | `#0D0F12` | app canvas (ink) |
| Surface / card | `#16191E` | cards, panels |
| Surface raised | `#1C2026` | elevated rows, menus |
| Border | `#242830` | default 0.5–1px borders |
| Border strong | `#2E333C` | emphasis / hover |
| Text primary | `#E8EAED` | headings, key numbers |
| Text secondary | `#9BA1A8` | labels, body |
| Text tertiary | `#6B7178` | hints, timestamps |
| **Accent / brand / verified / pass** | `#19B36B` | primary actions, verified, good |
| Accent hover / active | `#15A05F` / `#128A52` | button states |
| Accent wash | `rgba(25,179,107,0.12)` | subtle fills behind accent |
| Measured (confidence) | `#4D8DF6` | sampled metrics, bands |
| Estimated (confidence) | `#6B7178` | inferred values |
| Warn (severity) | `#E0A22B` | medium/high warnings |
| Fail / critical (severity) | `#E5484D` | critical issues |

### Light mode

| Token | Hex | Use |
|---|---|---|
| Page background | `#FBFCFD` | cool near-white (never beige) |
| Surface / card | `#FFFFFF` | cards |
| Subtle surface | `#F2F4F6` | metric cards, wells |
| Border | `#E3E6EA` | default borders |
| Text primary | `#0D0F12` | headings, numbers |
| Text secondary | `#5A616B` | labels, body |
| Text tertiary | `#8A9099` | hints |
| Accent / brand / verified / pass | `#12925A` | (darker green for white-bg contrast) |
| Measured | `#2D6BE5` | sampled metrics |
| Warn | `#B5790F` text / `#E0A22B` fill | warnings |
| Fail / critical | `#D23B3F` | critical |

**Colour rules:** green/amber/red appear *only* to convey status — never decoratively.
The confidence pair is consistent everywhere: accent green = verified (solid), blue =
measured (shown as a range band), gray = estimated.

## 4. Typography

- **Sans (UI + headings):** a clean geometric grotesque — Inter, Geist, or similar.
- **Mono (evidence / code snippets / URLs):** Geist Mono, JetBrains Mono, or similar.
- **Weights: 400 and 500 only.** Never heavier.
- Scale: hero score number 34px/500 · h1 22 · h2 18 · body 15–16 · small label 12–13.
- Sentence case everywhere. No ALL CAPS, no Title Case.

## 5. Motion

- **Scan running:** module rows tick to complete; the overall score counts up once
  (~600ms ease-out); skeleton placeholders while data loads. This is the hero moment.
- **Finding expand:** 150ms ease.
- **Nothing else moves.** No hover bounce, parallax, autoplay, or animated gradients.

## 6. Core components

- **Score ring** — circular gauge, big number centred, accent-green arc on a neutral
  track. Counts up once on load.
- **Pillar cards** — metric card (13px muted label, 24px/500 number) with a thin solid
  progress bar coloured by score (green good → amber mid → red poor). Verified = solid bar.
- **AI-visibility card (measured)** — deliberately *different*: a "Measured" chip, a value,
  and a **range band** (not a solid bar) plus "±band · n=sample · date". This is the
  verified-vs-measured grammar in action.
- **Findings list** — each finding is a row with a coloured left bar (severity), a severity
  tag (Critical/High/Medium), the title, and a small confidence chip (green dot = Verified).
  Click to expand in place → Evidence (mono block) + Recommendation + a `Generate fix`
  button (the "fixes, not findings" differentiator). No modals.
- **Confidence chips** — tiny pill: coloured dot + label (Verified / Measured / Estimated).
- **Buttons** — outline/ghost by default; primary action filled accent green.

## 7. Screens to design

1. **Landing page.** Hero = a *live demo*: a URL input; on submit, an animated scan runs
   (modules ticking, score resolving) and reveals a sample report inline. This is the most
   persuasive moment — the one place expressive motion belongs. Below: the verified-vs-
   measured value prop, the closed-loop features (attribution, crawler logs, fixes), a
   pricing teaser, and an agency/white-label callout. Can be a touch more expressive than
   the app, but still restrained.
2. **Dashboard.** List of monitored sites; each row shows the site, its overall score, a
   small trend sparkline, the change since last scan (▲/▼), and any alert badges. Top:
   "Add site", search/filter. Calm and scannable.
3. **Scan report** (the core working screen). Header (site URL, scan time, re-scan,
   export). Confidence legend. Score ring + pillar cards + the measured AI-visibility card.
   Then "Priority fixes" — the expandable findings list. Sections/tabs per pillar
   (Technical, On-page, GEO readiness; Performance/Local/AI-visibility as they come online).
4. **Site detail / monitoring.** Score over time (line chart), a change log, and the alert
   feed (what moved, when). Verified metrics solid; measured metrics with bands.
5. **Settings / white-label.** Workspace, team/seats, branding (logo + accent for client
   reports), export defaults. Agencies live here.

## 8. Do / don't

- Do: cool neutral base, one green accent, semantic colour only for meaning, solid-vs-band
  for verified-vs-measured, progressive disclosure, motion only on scan.
- Don't: beige/cream, purple-AI glow, gradients, decorative animation, popups, more than
  one brand accent, heavy font weights, Title Case.

---

*Tip: paste section 2 + 3 first to set the vibe and palette, then ask Claude Design to
design one screen at a time starting with the scan report (section 7.3).*
