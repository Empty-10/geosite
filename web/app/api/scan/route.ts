// POST /api/scan  →  runs the real damask engine and returns its JSON Report.
//
// Engine invocation is isolated in runEngine() so it can be swapped without touching
// callers. Today it shells out to the local Python engine (Approach A in
// docs/PROJECT-STATUS.md → "Next tasks" #1). For production (web on Vercel, which has no
// Python runtime), set DAMASK_ENGINE_URL to a deployed engine service and the route will
// fetch that instead — a one-env-var swap, no rewrite.
//
//   DAMASK_ENGINE_URL  — if set, POST {url} to `${DAMASK_ENGINE_URL}/scan` instead of shelling out.
//   DAMASK_ENGINE_DIR  — engine working dir (default: ../engine relative to the web app).
//   DAMASK_PYTHON      — python interpreter (default: <engine>/.venv/bin/python).

import { spawn } from "node:child_process";
import path from "node:path";

// Needs child_process + filesystem paths — Node runtime, never edge. Never cache a scan.
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const SCAN_TIMEOUT_MS = 25_000;

const ENGINE_DIR =
  process.env.DAMASK_ENGINE_DIR || path.resolve(process.cwd(), "..", "engine");
const PYTHON =
  process.env.DAMASK_PYTHON || path.join(ENGINE_DIR, ".venv", "bin", "python");
const ENGINE_URL = process.env.DAMASK_ENGINE_URL;

type EngineResult =
  | { ok: true; data: unknown }
  | { ok: false; status: number; error: string };

function json(body: unknown, status = 200): Response {
  return Response.json(body, { status });
}

/** Accept "acme.com" or a full URL; return a normalized http(s) href, or null if unusable. */
function normalizeUrl(raw: string): string | null {
  const withScheme = /^https?:\/\//i.test(raw) ? raw : `https://${raw}`;
  try {
    const u = new URL(withScheme);
    if (u.protocol !== "http:" && u.protocol !== "https:") return null;
    if (!u.hostname.includes(".")) return null; // reject bare hosts like "localhost"
    return u.href;
  } catch {
    return null;
  }
}

/**
 * Basic SSRF guard: this endpoint fetches arbitrary URLs server-side from a public page,
 * so refuse loopback / private / link-local targets. Not a defense against DNS rebinding —
 * adequate for the landing demo; revisit if this becomes an authenticated product surface.
 */
function ssrfReason(target: string): string | null {
  const host = new URL(target).hostname.toLowerCase().replace(/^\[|\]$/g, "");
  if (host === "localhost" || host.endsWith(".localhost")) return "Local addresses aren't allowed.";
  if (host === "::1" || host.startsWith("fc") || host.startsWith("fd") || host.startsWith("fe80"))
    return "Local addresses aren't allowed.";
  const m = host.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);
  if (m) {
    const [a, b] = [Number(m[1]), Number(m[2])];
    if (
      a === 0 || a === 127 || a === 10 || // unspecified, loopback, private
      (a === 169 && b === 254) || // link-local (incl. cloud metadata 169.254.169.254)
      (a === 192 && b === 168) ||
      (a === 172 && b >= 16 && b <= 31)
    )
      return "Private addresses aren't allowed.";
  }
  return null;
}

/** Turn a raw engine/requests error string into a short, user-facing message. */
function friendlyFetchError(raw: string): string {
  const r = raw.toLowerCase();
  if (r.includes("resolve") || r.includes("nameresolution") || r.includes("getaddrinfo"))
    return "Couldn't find that site — check the domain is spelled correctly.";
  if (r.includes("timed out") || r.includes("timeout")) return "That site took too long to respond.";
  if (r.includes("connection") || r.includes("refused") || r.includes("ssl") || r.includes("certificate"))
    return "Couldn't reach that site — it may be down or blocking automated requests.";
  return "Couldn't fetch that page.";
}

/** Shell out to the local engine: `python -m damask_engine <url> --json`. */
function runEngineLocal(target: string): Promise<EngineResult> {
  return new Promise((resolve) => {
    let settled = false;
    const done = (r: EngineResult) => {
      if (!settled) {
        settled = true;
        resolve(r);
      }
    };

    const proc = spawn(PYTHON, ["-m", "damask_engine", target, "--json", "--fixes"], { cwd: ENGINE_DIR });
    let out = "";
    let err = "";

    const timer = setTimeout(() => {
      proc.kill("SIGKILL");
      done({ ok: false, status: 504, error: "Scan timed out." });
    }, SCAN_TIMEOUT_MS);

    proc.stdout.on("data", (d) => (out += d));
    proc.stderr.on("data", (d) => (err += d));

    proc.on("error", (e: NodeJS.ErrnoException) => {
      clearTimeout(timer);
      const hint =
        e.code === "ENOENT"
          ? ` (no interpreter at ${PYTHON} — run \`pip install -e .\` in engine/ or set DAMASK_PYTHON)`
          : "";
      done({ ok: false, status: 500, error: `Engine could not start${hint}.` });
    });

    proc.on("close", () => {
      clearTimeout(timer);
      let data: { meta?: { error?: string } };
      try {
        data = JSON.parse(out);
      } catch {
        return done({
          ok: false,
          status: 502,
          error: err.trim() || "Engine produced no parseable output.",
        });
      }
      // The engine reports fetch/scan failures in meta.error rather than crashing.
      if (data?.meta?.error) return done({ ok: false, status: 502, error: friendlyFetchError(String(data.meta.error)) });
      done({ ok: true, data });
    });
  });
}

/** Future path: hand the scan to a deployed engine HTTP service. */
async function runEngineHttp(base: string, target: string): Promise<EngineResult> {
  try {
    const res = await fetch(`${base.replace(/\/$/, "")}/scan`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ url: target }),
      signal: AbortSignal.timeout(SCAN_TIMEOUT_MS),
    });
    const data = (await res.json()) as { meta?: { error?: string } };
    if (!res.ok) return { ok: false, status: 502, error: `Engine service error (${res.status}).` };
    if (data?.meta?.error) return { ok: false, status: 502, error: friendlyFetchError(String(data.meta.error)) };
    return { ok: true, data };
  } catch (e) {
    return { ok: false, status: 504, error: e instanceof Error ? e.message : "Engine service unreachable." };
  }
}

export async function POST(req: Request): Promise<Response> {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return json({ error: "Invalid JSON body." }, 400);
  }

  const raw = typeof (body as { url?: unknown })?.url === "string" ? (body as { url: string }).url.trim() : "";
  if (!raw) return json({ error: "Provide a 'url' to scan." }, 400);

  const target = normalizeUrl(raw);
  if (!target) return json({ error: "That doesn't look like a valid website URL." }, 400);

  const blocked = ssrfReason(target);
  if (blocked) return json({ error: blocked }, 400);

  const result = ENGINE_URL ? await runEngineHttp(ENGINE_URL, target) : await runEngineLocal(target);
  if (!result.ok) return json({ error: result.error }, result.status);

  return Response.json(result.data);
}
