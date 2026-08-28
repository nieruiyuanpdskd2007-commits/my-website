"use client";

import Link from "next/link";
import { useActionState } from "react";
import { loginWithPassword, type LoginState } from "./actions";

const initialState: LoginState = { status: "idle", message: "" };

export default function LoginForm() {
  const [state, action, pending] = useActionState(loginWithPassword, initialState);

  return (
    <form action={action} className="mt-8">
      <label htmlFor="paper-password" className="block text-sm font-medium text-slate-700">
        密码
      </label>
      <input
        id="paper-password"
        name="password"
        type="password"
        autoComplete="current-password"
        required
        autoFocus
        placeholder="输入论文库密码"
        className="mt-2 h-12 w-full rounded-xl border border-slate-300 bg-white px-4 text-base outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
      />
      <button
        type="submit"
        disabled={pending}
        className="mt-4 h-12 w-full rounded-xl bg-slate-950 px-5 text-sm font-semibold text-white transition hover:bg-blue-600 disabled:cursor-wait disabled:bg-slate-400"
      >
        {pending ? "正在登录…" : "进入论文库"}
      </button>
      <div className="mt-4 flex items-start justify-between gap-4">
        <p aria-live="polite" className={`min-h-6 text-sm leading-6 ${state.status === "error" ? "text-rose-600" : "text-slate-500"}`}>
          {state.message || "仅论文库所有者可以登录。"}
        </p>
        <Link href="/papers/forgot-password" className="shrink-0 text-sm font-medium text-blue-600 hover:text-blue-700">
          忘记密码
        </Link>
      </div>
    </form>
  );
}
