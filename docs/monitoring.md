# Monitoring layer — build plan

> Status: **planned** (not built). This is the recurring-revenue layer: re-scan tracked URLs on a
> cadence, diff against the last scan, and alert on meaningful regressions. It's what makes the
> $29/mo subscription defensible (a one-shot audit is a one-time purchase; "watch my site and
> tell me when it breaks" is a subscription).

## Goal

Turn the existing deterministic snapshot scanner into a **watcher**:

1. Re-scan each tracked URL on a schedule (daily / weekly).
2. Diff the new scan against the previous one (we already have `store.diff_reports`).
3. Raise an **alert** when something that matters regresses — and deliver it (email first).
4. Show **history over time** (trend), which also closes the "tracking over time" gap vs Searchable.

Everything here is **deterministic / VERIFIED** and **near-zero cost** (scans make no paid API
calls; email is pennies). No LLM in the loop.

## What already exists (build on this, don't rebuild)

- `store.py` — SQLite, gated by `DAMASK_DB_PATH`. `save()`, `history()`, `get()`, `previous()`,
  and **`diff_reports(old, new)`** which already returns `score_delta`, `pillar_deltas`,
  `regressed`, `resolved`, `new_issues`. The `scans` table is the history table.
- `/scan` already auto-saves + attaches `meta.diff` when persistence is on.
- The engine is a single stateful Render instance — fine for SQLite + a monitors table.

**Prerequisite:** set `DAMASK_DB_PATH` on a Render **persistent disk** (currently unset, so nothing
persists in prod). Monitoring can't exist without durable storage.

## Architecture

```
 cron (external)  ──hits──▶  POST /monitors/run-due  (engine, shared-secret guarded)
                                      │
                                      ├─ for each monitor whose next_run_at <= now:
                                      │     scan(url) ─▶ store.save ─▶ store.diff_reports(prev,new)
                                      │     evaluate alert rules over the diff (+ debounce)
                                      │     record alerts ─▶ deliver (email)
                                      └─ advance next_run_at
```

The engine free tier **sleeps**, so an in-process scheduler won't fire — the trigger must be
**external**. Options (recommendation first):

| Option | Notes |
|---|---|
| **Vercel Cron → Next route → engine** *(recommended)* | Already on Vercel; a `vercel.json` cron hits a protected `/api/cron/run-due` that calls the engine. Free tier covers a daily tick. |
| Render Cron Job | Native, runs a command on a schedule; clean but a separate paid service. |
| GitHub Actions cron | Free, simple `curl` to the endpoint; coarse timing, fine for daily. |

All three just need to call `/monitors/run-due` with a shared secret. Pick one in M1.

## Data model (new in store.py)

```sql
CREATE TABLE monitors (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT NOT NULL,
  cadence TEXT NOT NULL DEFAULT 'daily',        -- daily | weekly
  email TEXT,                                    -- recipient (until accounts exist)
  active INTEGER NOT NULL DEFAULT 1,
  alert_config TEXT,                             -- JSON: thresholds + which rules are on
  consecutive_fetch_failures INTEGER NOT NULL DEFAULT 0,  -- for availability debounce
  created_at TEXT NOT NULL,
  last_run_at TEXT,
  next_run_at TEXT,
  account_id INTEGER                             -- NULL until M4 (accounts)
);
CREATE TABLE alerts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  monitor_id INTEGER NOT NULL,
  scan_id INTEGER,
  type TEXT NOT NULL,                            -- ai_crawler | score | check | availability | ssl
  severity TEXT NOT NULL,                        -- critical | warning
  summary TEXT NOT NULL,
  detail TEXT,                                   -- JSON (the relevant diff slice)
  created_at TEXT NOT NULL,
  delivered_at TEXT
);
```

History reuses the existing `scans` table (already keyed by url+kind+id).

## Alert rules (the flagship set)

Evaluated over `diff_reports` + the new report. Each rule is deterministic.

1. **AI-crawler access** 🔥 — `geo.bot_access` went PASS → WARN/FAIL (newly blocked/cloaked), or
   `tech.robots.ai` regressed. *Critical.* Uniquely GEO; nobody else alerts on this.
2. **Score regression** — `score_delta <= -threshold` (default −5). *Warning* (−5) / *critical* (−15).
3. **Check regression** — any entry in `diff.regressed`, with these escalated to **critical**:
   schema removed (`schema.jsonld`/`schema.missing`), `robots.noindex` appeared,
   `tech.index_conflict`, `tech.https`/`tech.status` regressed.
4. **Availability** — new scan has `meta.error` or a non-2xx status. **Debounced**: only alert
   after **2 consecutive** failures (`consecutive_fetch_failures`), and send a **recovery** notice
   when it comes back. Avoids paging on a transient blip or a cold-start timeout.
5. **SSL expiry** — cert expires within N days (default 14). We already fetch `tls_info`.

Later (opt-in, costs API, MEASURED): **visibility drift** — share-of-voice / citation-rate drop.

## Anti-noise (non-negotiable — it's the brand)

A monitor that cries wolf is worse than none. Guards:

- **Never treat a fetch failure as a score crash.** If the new scan errored, route it to the
  *availability* rule (debounced) — do **not** fire "score dropped to 0".
- **Render-flakiness guard.** The Cloudflare free-tier renderer intermittently returns an empty
  shell for SPAs, which would look like a content regression. If a regression is only on
  content-derived rows **and** `meta.render_source` differs from the previous scan, require a
  **second consecutive** confirming scan before alerting.
- **One digest per run**, not one email per finding — group a monitor's alerts into a single
  message led by the verdict diff.

## Surfaces (web)

- **`/monitors`** — add a URL (cadence + email), list monitors with last status + a **headline
  sparkline** (from `store.history`), and the recent alert log. Add/pause/remove.
- **Per-monitor trend** — headline + pillar scores over time (the "tracking over time" view).
- **Email template** — branded; leads with the verdict change ("AI Retrievability 82 → 71"),
  then the regressed checks with evidence, then a link to the full report.

## Delivery

- Email via a transactional provider (**Resend** recommended — simple, free tier ~3k/mo). API key
  in env (`RESEND_API_KEY`), never committed. Abstract behind a `notify(channel, payload)` seam so
  Slack/webhook drop in later.

## Phasing (build order)

| Phase | Scope | New deps | Ships value |
|---|---|---|---|
| **M0 — core** | `monitors`/`alerts` tables + CRUD; `POST /monitors/run-due` that scans due monitors, saves, diffs, evaluates rules, records alerts (delivery = logged stub). Offline-testable. Set `DAMASK_DB_PATH` on Render. | none | engine watches + records (no delivery yet) |
| **M1 — schedule** | External cron → `/monitors/run-due` with a shared secret. | Vercel Cron | runs automatically |
| **M2 — alerts** | The 5 rules + debounce/anti-noise + email delivery (Resend). | Resend | real notifications |
| **M3 — surfaces** | `/monitors` UI: add/list/pause, sparkline, alert log, per-monitor trend. | none | self-serve + "tracking over time" |
| **M4 — accounts/billing** | Tie monitors to accounts; gate as the paid feature. | auth + Stripe | **chargeable SaaS** |

**Honest dependency:** M0–M3 ship a working monitor **single-tenant / email-keyed** (no login) to
prove the value cheaply. **Charging** for it needs the accounts + billing layer (M4) — the larger
prerequisite called out in PROJECT-STATUS.

## Cost

- Scans: **$0** (deterministic, no paid API).
- Email: ~free (Resend free tier).
- Scheduler: free (Vercel/GitHub cron) or a small Render cron fee.
- Storage: SQLite on the existing Render disk.

So the monitoring layer is **cheap to operate** — the constraint is build effort + the accounts
prerequisite for monetisation, not running cost.

## Risks

- **Render free-tier sleep / cold starts** → run-due may hit a cold engine; give the cron call a
  generous timeout, and the availability rule its 2-failure debounce so a cold-start timeout never
  pages.
- **SQLite on one instance** — fine now; the `store.py` functions are the seam to swap to Postgres
  when multi-instance/accounts arrive (M4).
- **False positives** — mitigated by the anti-noise section; treat any new false-alert class as a
  bug, not noise to tolerate.
```
