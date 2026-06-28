// Browser-side Supabase client (used in Client Components). Reads the public URL +
// anon key, which are safe to expose. Returns a fresh client per call; callers can
// memoize if needed. Auth state is kept in cookies so the server can read it too.
import { createBrowserClient } from "@supabase/ssr";

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  );
}
