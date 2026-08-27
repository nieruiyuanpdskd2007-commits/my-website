"""Installable desktop control center for the Hearthstone Agent."""

from __future__ import annotations

from pathlib import Path

from live.advisor import LiveAdvisor
from live.auth import LocalGuestAuth
from live.controller import LiveController
from live.overlay import ChatOverlay
from live.power_log import discover_power_log
from live.settings import AppSettings, default_settings_path
from live.types import GameMode, ModePolicy


class DesktopApp:
    def __init__(self) -> None:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk

        self.tk = tk
        self.filedialog = filedialog
        self.messagebox = messagebox
        self.settings = AppSettings.load()
        self.auth = LocalGuestAuth()
        self.advisor = LiveAdvisor()
        self.controller = LiveController(on_status=self._status_from_thread, on_event=self._event_from_thread)
        self.overlay: ChatOverlay | None = None
        self.last_recommendation_key = ""

        self.root = tk.Tk()
        self.root.title("Hearthstone Standard Agent")
        self.root.geometry("620x650")
        self.root.minsize(520, 560)
        self.root.configure(bg="#f7f4ed")
        self.root.protocol("WM_DELETE_WINDOW", self.exit)

        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("Primary.TButton", padding=10)
        style.configure("TButton", padding=8)

        top = tk.Frame(self.root, bg="#171714", padx=22, pady=18)
        top.pack(fill="x")
        tk.Label(
            top,
            text="Hearthstone Standard Agent",
            bg="#171714",
            fg="white",
            font=("Segoe UI", 17, "bold"),
        ).pack(anchor="w")
        self.status_var = tk.StringVar(value="已停止")
        tk.Label(
            top,
            textvariable=self.status_var,
            bg="#171714",
            fg="#fde68a",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(4, 0))

        body = tk.Frame(self.root, bg="#f7f4ed", padx=22, pady=18)
        body.pack(fill="both", expand=True)

        session = self.auth.current_session()
        account = tk.LabelFrame(
            body,
            text=" 账号 ",
            bg="#f7f4ed",
            fg="#44403c",
            padx=14,
            pady=12,
            font=("Segoe UI", 10, "bold"),
        )
        account.pack(fill="x")
        tk.Label(
            account,
            text=f"{session.display_name} · 数据保存在本机",
            bg="#f7f4ed",
            fg="#57534e",
        ).pack(side="left")
        ttk.Button(account, text="登录（预留）", command=self.auth_not_ready).pack(side="right")
        ttk.Button(account, text="注册（预留）", command=self.auth_not_ready).pack(
            side="right", padx=(0, 8)
        )

        controls = tk.LabelFrame(
            body,
            text=" 监听设置 ",
            bg="#f7f4ed",
            fg="#44403c",
            padx=14,
            pady=14,
            font=("Segoe UI", 10, "bold"),
        )
        controls.pack(fill="x", pady=(16, 0))

        tk.Label(controls, text="模式", bg="#f7f4ed").grid(row=0, column=0, sticky="w")
        self.mode_var = tk.StringVar(value=self.settings.mode)
        mode_box = ttk.Combobox(
            controls,
            textvariable=self.mode_var,
            state="readonly",
            values=[mode.value for mode in GameMode if mode != GameMode.UNKNOWN],
        )
        mode_box.grid(row=0, column=1, columnspan=2, sticky="ew", padx=(12, 0))
        mode_box.bind("<<ComboboxSelected>>", lambda _event: self.refresh_policy())

        tk.Label(controls, text="Power.log", bg="#f7f4ed").grid(
            row=1, column=0, sticky="w", pady=(12, 0)
        )
        discovered = discover_power_log()
        self.log_var = tk.StringVar(value=self.settings.log_path or str(discovered or ""))
        ttk.Entry(controls, textvariable=self.log_var).grid(
            row=1, column=1, sticky="ew", padx=(12, 8), pady=(12, 0)
        )
        ttk.Button(controls, text="浏览", command=self.browse_log).grid(
            row=1, column=2, pady=(12, 0)
        )
        controls.columnconfigure(1, weight=1)

        self.policy_var = tk.StringVar()
        tk.Label(
            controls,
            textvariable=self.policy_var,
            bg="#f7f4ed",
            fg="#92400e",
            justify="left",
            wraplength=510,
        ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(12, 0))
        self.refresh_policy()

        buttons = tk.Frame(body, bg="#f7f4ed")
        buttons.pack(fill="x", pady=16)
        self.start_button = ttk.Button(
            buttons, text="开始监听", command=self.start, style="Primary.TButton"
        )
        self.start_button.pack(side="left", fill="x", expand=True)
        self.stop_button = ttk.Button(buttons, text="停止", command=self.stop, state="disabled")
        self.stop_button.pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(buttons, text="打开顾问小窗", command=self.open_overlay).pack(
            side="left", fill="x", expand=True
        )

        activity_box = tk.LabelFrame(
            body,
            text=" 活动 ",
            bg="#f7f4ed",
            fg="#44403c",
            padx=10,
            pady=10,
            font=("Segoe UI", 10, "bold"),
        )
        activity_box.pack(fill="both", expand=True)
        self.activity = tk.Text(
            activity_box,
            state="disabled",
            wrap="word",
            bg="white",
            fg="#292524",
            relief="flat",
            padx=10,
            pady=10,
            font=("Segoe UI", 9),
        )
        self.activity.pack(fill="both", expand=True)
        self.log("软件已启动。选择模式与日志后点击“开始监听”。")
        self.log(self.controller.snapshot.knowledge_status)

        footer = tk.Frame(body, bg="#f7f4ed")
        footer.pack(fill="x", pady=(12, 0))
        tk.Label(
            footer,
            text="V0.2 · 全标准卡牌知识 · 不注入游戏、不控制输入、不读取隐藏信息",
            bg="#f7f4ed",
            fg="#78716c",
            font=("Segoe UI", 9),
        ).pack(side="left")
        ttk.Button(footer, text="退出软件", command=self.exit).pack(side="right")

    def refresh_policy(self) -> None:
        mode = GameMode(self.mode_var.get())
        policy = ModePolicy.for_mode(mode)
        self.policy_var.set(
            "练习/好友/复盘：允许公开信息建议。"
            if policy.live_recommendations
            else "天梯保护模式：对局中仅公开记牌和摘要，赛后复盘。"
        )
        if self.overlay:
            self.overlay.set_status("建议开启" if policy.live_recommendations else "天梯：仅记牌")

    def browse_log(self) -> None:
        value = self.filedialog.askopenfilename(
            title="选择 Hearthstone Power.log",
            filetypes=[("Hearthstone Power Log", "Power.log"), ("Log files", "*.log"), ("All", "*.*")],
        )
        if value:
            self.log_var.set(value)

    def start(self) -> None:
        path = Path(self.log_var.get().strip())
        if not path.is_file():
            self.messagebox.showerror("无法开始", "请选择存在的 Power.log 文件。")
            return
        mode = GameMode(self.mode_var.get())
        replay_path = default_settings_path().parent / "replays" / "live-public.jsonl"
        try:
            self.controller.start(
                path,
                mode=mode,
                local_player_id=self.settings.local_player_id,
                replay_path=replay_path,
            )
        except OSError as exc:
            self.messagebox.showerror("无法开始", str(exc))
            return
        self.settings.mode = mode.value
        self.settings.log_path = str(path)
        self.settings.save()
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.log(f"开始监听：{path}")
        self.open_overlay()

    def stop(self) -> None:
        self.controller.stop()
        self.status_var.set("已停止")
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.log("监听已停止。")

    def open_overlay(self) -> None:
        if self.overlay and self.overlay.root.winfo_exists():
            self.overlay.root.deiconify()
            self.overlay.root.lift()
            return
        policy = ModePolicy.for_mode(GameMode(self.mode_var.get()))
        self.overlay = ChatOverlay(
            title="Hearthstone Advisor",
            status="建议开启" if policy.live_recommendations else "天梯：仅记牌/复盘",
            on_question=lambda question: self.advisor.answer(question, self.controller.snapshot),
            parent=self.root,
        )
        self.overlay.post("system", self.policy_var.get())

    def auth_not_ready(self) -> None:
        self.messagebox.showinfo(
            "账号功能预留",
            "V0.2 使用本地访客模式，不收集或保存密码。正式后端、邮箱验证和隐私策略完成后再开放注册登录。",
        )

    def log(self, message: str) -> None:
        self.activity.configure(state="normal")
        self.activity.insert("end", message + "\n")
        self.activity.configure(state="disabled")
        self.activity.see("end")

    def _status_from_thread(self, message: str) -> None:
        if hasattr(self, "root"):
            self.root.after(0, lambda: self.status_var.set(message))

    def _event_from_thread(self, event, snapshot) -> None:
        if not hasattr(self, "root"):
            return

        def update() -> None:
            if event.kind in {"game_start", "game_end", "block"}:
                self.log(snapshot.history[-1] if snapshot.history else event.kind)
            if self.overlay and event.kind in {"game_start", "game_end"}:
                self.overlay.post("system", snapshot.history[-1])
            if event.kind == "options_end" and snapshot.is_my_turn:
                recommendation = self.advisor.recommend(snapshot)
                key = recommendation.render()
                if key != self.last_recommendation_key:
                    self.last_recommendation_key = key
                    self.log(
                        f"动作 {len(snapshot.legal_actions)} 个 · "
                        f"状态完整度 {snapshot.state_completeness:.0%}"
                    )
                    if self.overlay:
                        self.overlay.post("advisor", key)

        self.root.after(0, update)

    def exit(self) -> None:
        self.controller.stop()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    DesktopApp().run()


if __name__ == "__main__":
    main()
