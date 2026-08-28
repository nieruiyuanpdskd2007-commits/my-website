"use client";

import { useActionState } from "react";
import { requestMagicLink, type LoginState } from "./actions";

const initialState: LoginState = { status: "idle", message: "" };

export default function LoginForm() {
  const [state, action, pending] = useActionState(requestMagicLink, initialState);

  return (
    <form action={action} className="mt-8">
      <button
        type="submit"
        disabled={pending || state.status === "sent"}
        className="h-12 w-full rounded-xl bg-slate-950 px-5 text-sm font-semibold text-white transition hover:bg-blue-600 disabled:cursor-wait disabled:bg-slate-400"
      >
        {pending ? "正在发送…" : state.status === "sent" ? "邮件已发送" : "发送登录链接"}
      </button>
      <p
        aria-live="polite"
        className={`mt-4 min-h-10 text-sm leading-6 ${state.status === "error" ? "text-rose-600" : "text-slate-500"}`}
      >
        {state.message || "无需密码。登录链接只会发送给论文库所有者。"}
      </p>
    </form>
  );
}
