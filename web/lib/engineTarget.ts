// Shared URL helpers for engine-backed routes: normalize a user-typed target and refuse
// server-side requests to local/private addresses (basic SSRF guard). Pure, no I/O.

/** Build the AI Ready Action Plan link for a raw user-typed target, scheme-normalized + encoded.
 *  Returns null for empty input (caller decides what to do). Pure - safe to unit test. */
export function aiReadyHref(raw: string): string | null {
  const v = raw.trim();
  if (!v) return null;
  const withScheme = /^https?:\/\//i.test(v) ? v : `https://${v}`;
  return `/ai-ready?url=${encodeURIComponent(withScheme)}`;
}

/** Accept "acme.com" or a full URL; return a normalized http(s) href, or null if unusable. */
export function normalizeUrl(raw: string): string | null {
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

/** Refuse loopback / private / link-local targets. Adequate for a public tool surface. */
export function ssrfReason(target: string): string | null {
  const host = new URL(target).hostname.toLowerCase().replace(/^\[|\]$/g, "");
  if (host === "localhost" || host.endsWith(".localhost")) return "Local addresses aren't allowed.";
  if (host === "::1" || host.startsWith("fc") || host.startsWith("fd") || host.startsWith("fe80"))
    return "Local addresses aren't allowed.";
  const m = host.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);
  if (m) {
    const [a, b] = [Number(m[1]), Number(m[2])];
    if (
      a === 0 || a === 127 || a === 10 ||
      (a === 169 && b === 254) ||
      (a === 192 && b === 168) ||
      (a === 172 && b >= 16 && b <= 31)
    )
      return "Private addresses aren't allowed.";
  }
  return null;
}
