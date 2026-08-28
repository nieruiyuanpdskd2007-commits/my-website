import type { EmailOtpType } from "@supabase/supabase-js";
import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

const otpTypes = new Set<EmailOtpType>([
  "email",
  "recovery",
  "invite",
  "email_change",
  "signup",
  "magiclink",
]);

export async function GET(request: Request) {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const tokenHash = url.searchParams.get("token_hash");
  const rawType = url.searchParams.get("type") as EmailOtpType | null;
  const supabase = await createClient();

  let authError = null;
  if (code) {
    ({ error: authError } = await supabase.auth.exchangeCodeForSession(code));
  } else if (tokenHash && rawType && otpTypes.has(rawType)) {
    ({ error: authError } = await supabase.auth.verifyOtp({
      token_hash: tokenHash,
      type: rawType,
    }));
  } else {
    authError = new Error("Missing authentication token");
  }

  if (authError) {
    return NextResponse.redirect(new URL("/papers/login?error=invalid-link", url.origin));
  }

  const { data } = await supabase.auth.getClaims();
  const signedInEmail = String(data?.claims?.email ?? "").trim().toLowerCase();
  const ownerEmail = process.env.PAPER_LIBRARY_OWNER_EMAIL?.trim().toLowerCase();

  if (!ownerEmail || signedInEmail !== ownerEmail) {
    await supabase.auth.signOut();
    return NextResponse.redirect(new URL("/papers/login?error=not-owner", url.origin));
  }

  return NextResponse.redirect(new URL("/papers", url.origin));
}
