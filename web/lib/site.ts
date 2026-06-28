// Canonical site origin, used for metadataBase, canonical tags, JSON-LD, sitemap and robots.
// Centralised so locking the real domain later is a one-line change (set NEXT_PUBLIC_SITE_URL).
export const SITE_URL = (
  process.env.NEXT_PUBLIC_SITE_URL || "https://geosite-gamma.vercel.app"
).replace(/\/$/, "");
