"use server";

import { headers } from "next/headers";
import { createClient } from "@/lib/supabase/server";

export type ResetRequestState = {
  status: "idle" | "sent" | "error";
  message: string;
};

function ownerEmail() {
  return process.env.PAPER_LIBRARY_OWNER_EMAIL?.trim().toLowerCase();
}

export async function requestPasswordResetLink(
  previousState: ResetRequestState,
): Promise<ResetRequestState> {
  void previousState;
  const email = ownerEmail();
  if (!email) return { status: "error", message: "找回邮箱尚未配置。" };

  const requestHeaders = await headers();
  const origin = requestHeaders.get("origin") ?? process.env.NEXT_PUBLIC_SITE_URL;
  if (!origin) return { status: "error", message: "网站地址尚未配置，请稍后再试。" };

  const supabase = await createClient();
  const callback = new URL("/papers/auth/confirm", origin);
  callback.searchParams.set("next", "/papers/reset-password");
  const { error } = await supabase.auth.resetPasswordForEmail(email, {
    redirectTo: callback.toString(),
  });
  if (error) {
    const limited = error.status === 429 || error.code === "over_email_send_rate_limit";
    return {
      status: "error",
      message: limited
        ? "邮件服务已达到临时发送上限，请约一小时后再试。"
        : "找回邮件发送失败，请稍后重试。",
    };
  }

  return {
    status: "sent",
    message: "找回邮件已发送。请打开邮件并点击“Reset password”，然后设置新密码。",
  };
}
