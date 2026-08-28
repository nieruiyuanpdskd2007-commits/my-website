"use server";

import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

export type LoginState = {
  status: "idle" | "error";
  message: string;
};

export async function loginWithPassword(
  previousState: LoginState,
  formData: FormData,
): Promise<LoginState> {
  void previousState;
  const email = process.env.PAPER_LIBRARY_OWNER_EMAIL?.trim().toLowerCase();
  const password = String(formData.get("password") ?? "");

  if (!email) return { status: "error", message: "登录账户尚未配置，请稍后再试。" };
  if (!password) return { status: "error", message: "请输入密码。" };

  const supabase = await createClient();
  const { error } = await supabase.auth.signInWithPassword({ email, password });
  if (error) {
    return { status: "error", message: "密码不正确。首次使用请点击“忘记密码”设置密码。" };
  }

  const { data } = await supabase.auth.getClaims();
  const signedInEmail = String(data?.claims?.email ?? "").trim().toLowerCase();
  if (signedInEmail !== email) {
    await supabase.auth.signOut();
    return { status: "error", message: "此账户没有论文库访问权限。" };
  }

  redirect("/papers");
}
