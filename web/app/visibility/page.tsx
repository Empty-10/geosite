import type { Metadata } from "next";
import { VisibilityView } from "@/components/report/VisibilityView";

export const metadata: Metadata = {
  title: "AI visibility",
  robots: { index: false }, // working tool screen, not for search indexing
};

export default function VisibilityPage() {
  return <VisibilityView />;
}
