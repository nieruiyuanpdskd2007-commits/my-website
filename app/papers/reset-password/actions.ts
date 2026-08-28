"use server";

import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

export type UpdatePasswordState = {
  status: "idle" | "error";
  message: string;
};

export async function updatePaperPassword(
  previousState: UpdatePasswordState,
  formData: FormData,
): Promise<UpdatePasswordState> {
  void previousState;
  const password = String(formData.get("password") ?? "");
  const confirmation = String(formData.get("confirmation") ?? "");

  if (password.length < 10) return { status: "error", message: "新密码至少需要 10 个字符。" };
  if (password !== confirmation) return { status: "error", message: "两次输入的密码不一致。" };

  const ownerEmail = process.env.PAPER_LIBRARY_OWNER_EMAIL?.trim().toLowerCase();
  const supabase = await createClient();
  const { data } = await supabase.auth.getClaims();
  const signedInEmail = String(data?.claims?.email ?? "").trim().toLowerCase();
  if (!ownerEmail || signedInEmail !== ownerEmail) {
    await supabase.auth.signOut();
    return { status: "error", message: "找回会话已过期，请重新获取邮件。" };
  }

  const { error } = await supabase.auth.updateUser({ password });
  if (error) return { status: "error", message: "密码设置失败，请更换密码后重试。" };

  await supabase.auth.signOut();
  redirect("/papers/login?reset=success");
}
