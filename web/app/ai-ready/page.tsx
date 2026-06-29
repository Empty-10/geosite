import { Suspense } from "react";
import type { Metadata } from "next";
import { AiReadyView } from "@/components/AiReadyView";

export const metadata: Metadata = {
  title: "AI Ready Action Plan",
  description:
    "Scan a URL and get a prioritised, agent-friendly action plan to make it AI Ready - the same plan " +
    "Astova exposes to coding agents via MCP and the CLI.",
  robots: { index: false }, // working tool screen
};

export default function AiReadyPage() {
  // useSearchParams (inside AiReadyView, for the ?url= prefill) needs a Suspense boundary.
  return (
    <Suspense fallback={null}>
      <AiReadyView />
    </Suspense>
  );
}
