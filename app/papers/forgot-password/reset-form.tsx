"use client";

import Link from "next/link";
import { useActionState } from "react";
import { requestPasswordResetLink, type ResetRequestState } from "./actions";

const requestInitial: ResetRequestState = { status: "idle", message: "" };

export default function ResetForm() {
  const [requestState, requestAction, requesting] = useActionState(requestPasswordResetLink, requestInitial);

  return (
    <div className="mt-8">
      <form action={requestAction}>
        <button
          type="submit"
          disabled={requesting || requestState.status === "sent"}
          className="h-12 w-full rounded-xl border border-slate-300 bg-white px-5 text-sm font-semibold text-slate-800 transition hover:border-blue-400 hover:bg-blue-50 disabled:cursor-wait disabled:text-slate-400"
        >
          {requesting ? "正在发送…" : requestState.status === "sent" ? "找回邮件已发送" : "发送找回邮件"}
        </button>
        <p aria-live="polite" className={`mt-3 text-sm leading-6 ${requestState.status === "error" ? "text-rose-600" : "text-slate-500"}`}>
          {requestState.message || "邮件只会发送到已配置的所有者邮箱。"}
        </p>
      </form>

      <Link href="/papers/login" className="mt-6 inline-flex text-sm font-medium text-blue-600 hover:text-blue-700">
        返回密码登录
      </Link>
    </div>
  );
}
