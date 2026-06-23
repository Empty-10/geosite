import { Suspense } from "react";
import type { Metadata } from "next";
import { SiteReportView } from "@/components/report/SiteReportView";

export const metadata: Metadata = {
  title: "Site crawl",
  robots: { index: false }, // per-scan working screen, not for search indexing
};

export default function SitePage() {
  // useSearchParams (inside SiteReportView) requires a Suspense boundary in the App Router.
  return (
    <Suspense fallback={null}>
      <SiteReportView />
    </Suspense>
  );
}
