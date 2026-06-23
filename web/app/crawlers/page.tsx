import type { Metadata } from "next";
import { LogReportView } from "@/components/report/LogReportView";

export const metadata: Metadata = {
  title: "AI crawler logs",
  robots: { index: false }, // working tool screen, not for search indexing
};

export default function CrawlersPage() {
  return <LogReportView />;
}
