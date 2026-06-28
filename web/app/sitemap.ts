import type { MetadataRoute } from "next";

import { SITE_URL } from "@/lib/site";

// Public, indexable routes. Auth-gated/private pages (/dashboard, /login, /auth) are excluded.
export default function sitemap(): MetadataRoute.Sitemap {
  const paths = ["", "/report", "/site", "/visibility", "/crawlers", "/compare"];
  return paths.map((path) => ({
    url: `${SITE_URL}${path || "/"}`,
    changeFrequency: "weekly",
    priority: path === "" ? 1 : 0.6,
  }));
}
