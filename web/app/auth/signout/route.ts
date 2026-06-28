// Sign the user out and send them back to /login. POST-only so it can't be triggered
// by a stray link prefetch.
import { NextResponse } from "next/server";

import { createClient } from "@/lib/supabase/server";

export async function POST(request: Request) {
  const supabase = await createClient();
  await supabase.auth.signOut();
  // 303 so the browser issues a GET to /login after the POST.
  return NextResponse.redirect(new URL("/login", request.url), { status: 303 });
}
