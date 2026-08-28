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
  searchParams: Promise<{ error?: string }>;
}) {
  const owner = await getPaperOwner();
  if (owner) redirect("/papers");

  const { error } = await searchParams;

  return (
    <main className="flex min-h-[calc(100vh-69px)] items-center justify-center bg-[#f5f7fb] px-5 py-12">
      <section className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-7 shadow-[0_24px_80px_rgba(15,23,42,0.10)] sm:p-10">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-blue-600">Ruiyuan&apos;s private space</p>
        <h1 className="mt-4 text-3xl font-semibold tracking-tight text-slate-950">进入论文库</h1>
        <p className="mt-3 text-sm leading-6 text-slate-600">
          你的论文、分析笔记与推荐反馈只在登录后可见。点击下方按钮获取一次性登录链接。
        </p>
        {error ? (
          <p className="mt-5 rounded-xl bg-rose-50 px-4 py-3 text-sm leading-6 text-rose-700">
            登录链接无效或已过期，请重新发送。
          </p>
        ) : null}
        <LoginForm />
      </section>
    </main>
  );
}
