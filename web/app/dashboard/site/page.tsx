// Protected per-site detail: scan history (each linkable to its saved report), a re-scan
// button, and the site's running note log. Reached from a dashboard row.
import { redirect } from "next/navigation";

import { createClient } from "@/lib/supabase/server";
import { SiteDetailView } from "./SiteDetailView";

export const metadata = { title: "Site" };

export default async function SiteDetailPage({
  searchParams,
}: {
  searchParams: Promise<{ url?: string }>;
}) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  const { url } = await searchParams;
  if (!url) redirect("/dashboard");

  return <SiteDetailView url={url} />;
}
