import { Suspense } from "react";
import type { Metadata } from "next";
import { ReportView } from "@/components/report/ReportView";

export const metadata: Metadata = {
  title: "Scan report",
  robots: { index: false }, // per-scan working screen, not for search indexing
};

export default function ReportPage() {
  // useSearchParams (inside ReportView) requires a Suspense boundary in the App Router.
  return (
    <Suspense fallback={null}>
      <ReportView />
    </Suspense>
  );
}
