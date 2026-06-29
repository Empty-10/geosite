import type { Metadata } from "next";

import { Nav } from "@/components/Nav";
import { Footer } from "@/components/Footer";
import { ReportDetailView } from "@/components/report/ReportDetailView";

export const metadata: Metadata = {
  title: "AI Readiness Report",
  description: "A shareable, deterministic AI Readiness report from Astova.",
  robots: { index: false }, // per-report capability link, not for indexing
};

export default async function ReportDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ share?: string }>;
}) {
  const { id } = await params;
  const sp = await searchParams;
  const share = typeof sp.share === "string" ? sp.share : "";
  return (
    <main style={{ minHeight: "100vh" }}>
      <Nav />
      <ReportDetailView reportId={id} share={share} />
      <Footer />
    </main>
  );
}
