import { Suspense } from "react";
import type { Metadata } from "next";
import { CompareView } from "@/components/report/CompareView";

export const metadata: Metadata = {
  title: "Competitor benchmark",
  robots: { index: false }, // working tool screen, not for search indexing
};

export default function ComparePage() {
  // useSearchParams (inside CompareView) requires a Suspense boundary in the App Router.
  return (
    <Suspense fallback={null}>
      <CompareView />
    </Suspense>
  );
}
