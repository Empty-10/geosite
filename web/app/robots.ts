import type { MetadataRoute } from "next";

import { SITE_URL } from "@/lib/site";

// We practice what we preach — AI answer engines are welcome. Only the private app surface
// (dashboard/auth) is disallowed. References the sitemap so crawlers discover the public pages.
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/dashboard", "/login", "/auth"],
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
    host: SITE_URL,
  };
}
