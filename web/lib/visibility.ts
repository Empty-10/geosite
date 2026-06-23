// Stats + parsing helpers for AI visibility (citation) sampling.
//
// This is the MEASURED layer (accuracy principle): a rate is an estimate from a sample, so it
// is always reported with a Wilson 95% confidence interval and the sample size — never a bare %.

/** Wilson score interval for a proportion k/n. Returns [low, high] in 0..1. */
export function wilson(k: number, n: number, z = 1.96): [number, number] {
  if (n <= 0) return [0, 0];
  const p = k / n;
  const denom = 1 + (z * z) / n;
  const center = (p + (z * z) / (2 * n)) / denom;
  const margin = (z * Math.sqrt((p * (1 - p)) / n + (z * z) / (4 * n * n))) / denom;
  return [Math.max(0, center - margin), Math.min(1, center + margin)];
}

/** True if `url`'s host is `domain` or a subdomain of it (www-insensitive). */
export function hostMatches(url: string, domain: string): boolean {
  try {
    const h = new URL(url).hostname.replace(/^www\./, "").toLowerCase();
    const d = domain.replace(/^www\./, "").toLowerCase().trim();
    return !!d && (h === d || h.endsWith("." + d));
  } catch {
    return false;
  }
}

export function pct(x: number): number {
  return Math.round(x * 100);
}
