// Shared URL validation for server routes that fetch arbitrary user-supplied pages.
// Accept "acme.com" or a full URL; reject non-http(s), bare hosts, and SSRF targets.

/** Normalize to an http(s) href, or null if unusable. */
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

/**
 * Basic SSRF guard — refuse loopback / private / link-local targets. Not a defense against DNS
 * rebinding; adequate for a public scan demo. Returns a user-facing reason, or null if allowed.
 */
export function ssrfReason(target: string): string | null {
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
