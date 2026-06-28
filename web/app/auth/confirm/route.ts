// Handles the email-confirmation link Supabase sends on signup. The link carries a
// token_hash + type; we exchange it for a session (sets auth cookies) then redirect.
//
// NOTE: for this to fire, the Supabase "Confirm signup" email template must point at
// {{ .SiteURL }}/auth/confirm?token_hash={{ .TokenHash }}&type=email (see setup checklist).
import { type EmailOtpType } from "@supabase/supabase-js";
import { type NextRequest, NextResponse } from "next/server";

import { createClient } from "@/lib/supabase/server";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const tokenHash = searchParams.get("token_hash");
  const type = searchParams.get("type") as EmailOtpType | null;
  const next = searchParams.get("next") ?? "/dashboard";

  if (tokenHash && type) {
    const supabase = await createClient();
    const { error } = await supabase.auth.verifyOtp({ type, token_hash: tokenHash });
    if (!error) {
      return NextResponse.redirect(new URL(next, request.url));
    }
  }

  return NextResponse.redirect(new URL("/login?error=confirm", request.url));
}
