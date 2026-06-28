// Protected dashboard. Middleware already redirects unauthenticated users to /login; we
// re-check here (defense in depth) and pass the signed-in email to the client view.
import { redirect } from "next/navigation";

import { createClient } from "@/lib/supabase/server";
import { DashboardView } from "./DashboardView";

export const metadata = { title: "Dashboard" };

export default async function DashboardPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/login");

  return <DashboardView email={user.email ?? ""} />;
}
