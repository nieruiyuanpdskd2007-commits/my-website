"use client";

import { useActionState } from "react";
import { updatePaperPassword, type UpdatePasswordState } from "./actions";

const initialState: UpdatePasswordState = { status: "idle", message: "" };

export default function PasswordForm() {
  const [state, action, pending] = useActionState(updatePaperPassword, initialState);

  return (
    <form action={action} className="mt-8 space-y-4">
      <label className="block text-sm font-medium text-slate-700">
        新密码
        <input
          name="password"
          type="password"
          autoComplete="new-password"
          minLength={10}
          required
          autoFocus
          className="mt-2 h-12 w-full rounded-xl border border-slate-300 px-4 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
        />
      </label>
      <label className="block text-sm font-medium text-slate-700">
        再次输入新密码
        <input
          name="confirmation"
          type="password"
          autoComplete="new-password"
          minLength={10}
          required
          className="mt-2 h-12 w-full rounded-xl border border-slate-300 px-4 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
        />
      </label>
      <p className="text-xs leading-5 text-slate-500">至少 10 个字符，建议同时包含字母、数字和符号。</p>
      <button
        type="submit"
        disabled={pending}
        className="h-12 w-full rounded-xl bg-slate-950 px-5 text-sm font-semibold text-white transition hover:bg-blue-600 disabled:cursor-wait disabled:bg-slate-400"
      >
        {pending ? "正在设置…" : "保存新密码"}
      </button>
      {state.message ? <p aria-live="polite" className="text-sm leading-6 text-rose-600">{state.message}</p> : null}
    </form>
  );
}
