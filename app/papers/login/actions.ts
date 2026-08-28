"use server";

import { headers } from "next/headers";
import { createClient } from "@/lib/supabase/server";

export type LoginState = {
  status: "idle" | "sent" | "error";
  message: string;
};

export async function requestMagicLink(previousState: LoginState): Promise<LoginState> {
  void previousState;
  const email = process.env.PAPER_LIBRARY_OWNER_EMAIL?.trim().toLowerCase();
  if (!email) {
    return { status: "error", message: "登录邮箱尚未配置，请稍后再试。" };
  }

  const requestHeaders = await headers();
  const origin = requestHeaders.get("origin") ?? process.env.NEXT_PUBLIC_SITE_URL;
  if (!origin) {
    return { status: "error", message: "网站地址尚未配置，请稍后再试。" };
  }

  const supabase = await createClient();
  const { error } = await supabase.auth.signInWithOtp({
    email,
    options: {
      emailRedirectTo: `${origin.replace(/\/$/, "")}/papers/auth/confirm`,
      shouldCreateUser: true,
    },
  });

  if (error) {
    return { status: "error", message: "登录邮件发送失败，请稍后重试。" };
  }

  return {
    status: "sent",
    message: "登录链接已发送到你的邮箱。打开邮件中的链接即可进入论文库。",
  };
}
