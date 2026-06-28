// Session refresh + route protection, run from the root middleware on every request.
//
// Two jobs:
//   1. Refresh the Supabase auth token (cookies) so server-rendered pages see a live
//      session. This MUST run for auth to work across navigations.
//   2. Gate protected routes: an unauthenticated hit to /dashboard is redirected to /login.
//
// Graceful degradation: if the Supabase env vars aren't configured yet, we skip auth
// entirely and pass the request through, so the existing marketing site keeps working
// until NEXT_PUBLIC_SUPABASE_URL / _ANON_KEY are set.
import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

const PROTECTED_PREFIXES = ["/dashboard"];

export async function updateSession(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request });

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !anonKey) {
    return supabaseResponse; // auth not configured — don't break the rest of the site
  }

  const supabase = createServerClient(url, anonKey, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
        supabaseResponse = NextResponse.next({ request });
        cookiesToSet.forEach(({ name, value, options }) =>
          supabaseResponse.cookies.set(name, value, options),
        );
      },
    },
  });

  // IMPORTANT: do not run code between createServerClient and getUser() — it refreshes
  // the token and getUser() validates it against the Supabase Auth server.
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const path = request.nextUrl.pathname;
  const isProtected = PROTECTED_PREFIXES.some(
    (p) => path === p || path.startsWith(p + "/"),
  );

  if (!user && isProtected) {
    const redirectUrl = request.nextUrl.clone();
    redirectUrl.pathname = "/login";
    redirectUrl.searchParams.set("redirectedFrom", path);
    return NextResponse.redirect(redirectUrl);
  }

  return supabaseResponse;
}
