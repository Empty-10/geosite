// Protected dashboard stub. The middleware already redirects unauthenticated users to
// /login; we re-check here (defense in depth, and to read the user for display).
import { redirect } from "next/navigation";

import { createClient } from "@/lib/supabase/server";

export const metadata = { title: "Dashboard" };

export default async function DashboardPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  return (
    <main
      style={{
        minHeight: "100dvh",
        padding: "3rem 1.5rem",
        maxWidth: 720,
        margin: "0 auto",
      }}
    >
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "2rem",
        }}
      >
        <span style={{ fontWeight: 600, fontSize: 18 }}>Astova</span>
        <form action="/auth/signout" method="post">
          <button
            type="submit"
            style={{
              background: "var(--raised)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              color: "var(--text)",
              padding: "0.45rem 0.8rem",
              fontSize: 14,
              cursor: "pointer",
            }}
          >
            Sign out
          </button>
        </form>
      </header>

      <h1 style={{ fontSize: 26, fontWeight: 600, margin: "0 0 0.5rem" }}>
        Dashboard
      </h1>
      <p style={{ color: "var(--text-2)", margin: "0 0 1.5rem" }}>
        Signed in as <strong style={{ color: "var(--text)" }}>{user.email}</strong>.
      </p>

      <div
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: 14,
          padding: "1.5rem",
          color: "var(--text-2)",
        }}
      >
        This is a placeholder. Your domains, scans, and monitors will live here.
      </div>
    </main>
  );
}
