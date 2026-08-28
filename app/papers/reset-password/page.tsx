import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { getPaperOwner } from "@/lib/paper-auth";
import PasswordForm from "./password-form";

export const metadata: Metadata = {
  title: "设置论文库密码 | Ruiyuan",
  description: "设置 Ruiyuan 私人论文库的新密码。",
};

export default async function ResetPasswordPage() {
  const owner = await getPaperOwner();
  if (!owner) redirect("/papers/forgot-password?error=invalid-link");

  return (
    <main className="flex min-h-[calc(100vh-69px)] items-center justify-center bg-[#f5f7fb] px-5 py-12">
      <section className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-7 shadow-[0_24px_80px_rgba(15,23,42,0.10)] sm:p-10">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-blue-600">Password recovery</p>
        <h1 className="mt-4 text-3xl font-semibold tracking-tight text-slate-950">设置新密码</h1>
        <p className="mt-3 text-sm leading-6 text-slate-600">
          找回邮件已验证。设置完成后，请回到登录页使用新密码进入论文库。
        </p>
        <PasswordForm />
      </section>
    </main>
  );
}
