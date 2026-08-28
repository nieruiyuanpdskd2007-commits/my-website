import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { getPaperOwner } from "@/lib/paper-auth";
import LoginForm from "./login-form";

export const metadata: Metadata = {
  title: "登录论文库 | Ruiyuan",
  description: "登录 Ruiyuan 的私人论文库。",
};

export default async function PaperLoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string; reset?: string }>;
}) {
  const owner = await getPaperOwner();
  if (owner) redirect("/papers");

  const { error, reset } = await searchParams;

  return (
    <main className="flex min-h-[calc(100vh-69px)] items-center justify-center bg-[#f5f7fb] px-5 py-12">
      <section className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-7 shadow-[0_24px_80px_rgba(15,23,42,0.10)] sm:p-10">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-blue-600">Ruiyuan&apos;s private space</p>
        <h1 className="mt-4 text-3xl font-semibold tracking-tight text-slate-950">进入论文库</h1>
        <p className="mt-3 text-sm leading-6 text-slate-600">
          你的论文、分析笔记与推荐反馈只在登录后可见。输入密码即可进入。
        </p>
        {reset === "success" ? (
          <p className="mt-5 rounded-xl bg-emerald-50 px-4 py-3 text-sm leading-6 text-emerald-700">
            密码设置成功，请使用新密码登录。
          </p>
        ) : null}
        {error ? (
          <p className="mt-5 rounded-xl bg-rose-50 px-4 py-3 text-sm leading-6 text-rose-700">
            旧登录链接无效或已过期，请使用密码登录或找回密码。
          </p>
        ) : null}
        <LoginForm />
      </section>
    </main>
  );
}
