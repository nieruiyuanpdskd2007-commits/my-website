import type { Metadata } from "next";
import ResetForm from "./reset-form";

export const metadata: Metadata = {
  title: "设置或找回论文库密码 | Ruiyuan",
  description: "通过所有者邮箱首次设置或找回私人论文库密码。",
};

export default async function ForgotPasswordPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const { error } = await searchParams;

  return (
    <main className="flex min-h-[calc(100vh-69px)] items-center justify-center bg-[#f5f7fb] px-5 py-12">
      <section className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-7 shadow-[0_24px_80px_rgba(15,23,42,0.10)] sm:p-10">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-blue-600">Password recovery</p>
        <h1 className="mt-4 text-3xl font-semibold tracking-tight text-slate-950">首次设置或找回密码</h1>
        <p className="mt-3 text-sm leading-6 text-slate-600">
          第一次使用或忘记密码时，获取一封验证邮件；点击邮件中的重置按钮即可设置新密码。邮箱地址不会显示在页面上。
        </p>
        {error ? (
          <p className="mt-5 rounded-xl bg-rose-50 px-4 py-3 text-sm leading-6 text-rose-700">
            找回链接无效或已过期，请重新发送。
          </p>
        ) : null}
        <ResetForm />
      </section>
    </main>
  );
}
