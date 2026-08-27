"""Small, top-most desktop chat window.  No game input or process hooks."""

from __future__ import annotations

from collections.abc import Callable


class ChatOverlay:
    def __init__(
        self,
        *,
        title: str,
        status: str,
        on_question: Callable[[str], str],
        parent=None,
    ):
        try:
            import tkinter as tk
            from tkinter import ttk
        except ImportError as exc:
            raise RuntimeError("This Python installation does not include tkinter") from exc

        self.tk = tk
        self.root = tk.Toplevel(parent) if parent is not None else tk.Tk()
        self.root.title(title)
        self.root.geometry("420x470+40+90")
        self.root.minsize(340, 300)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#171714")
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("Status.TLabel", background="#171714", foreground="#d6d3d1")
        style.configure("Send.TButton", background="#e7e5e4", foreground="#171714")

        header = tk.Frame(self.root, bg="#171714")
        header.pack(fill="x", padx=14, pady=(12, 6))
        tk.Label(
            header,
            text="Hearthstone Advisor",
            bg="#171714",
            fg="white",
            font=("Segoe UI", 13, "bold"),
        ).pack(side="left")
        self.status = ttk.Label(header, text=status, style="Status.TLabel")
        self.status.pack(side="right")

        self.transcript = tk.Text(
            self.root,
            wrap="word",
            state="disabled",
            bg="#211f1c",
            fg="#f5f5f4",
            insertbackground="white",
            relief="flat",
            padx=12,
            pady=12,
            font=("Segoe UI", 10),
        )
        self.transcript.pack(fill="both", expand=True, padx=12, pady=6)
        self.transcript.tag_configure("advisor", foreground="#fde68a", spacing1=8)
        self.transcript.tag_configure("you", foreground="#bfdbfe", spacing1=8)
        self.transcript.tag_configure("system", foreground="#a8a29e", spacing1=8)

        compose = tk.Frame(self.root, bg="#171714")
        compose.pack(fill="x", padx=12, pady=(6, 12))
        self.entry = tk.Entry(
            compose,
            bg="#292524",
            fg="white",
            insertbackground="white",
            relief="flat",
            font=("Segoe UI", 10),
        )
        self.entry.pack(side="left", fill="x", expand=True, ipady=8)

        def submit(_event=None) -> None:
            question = self.entry.get().strip()
            if not question:
                return
            self.entry.delete(0, "end")
            self.post("you", question)
            self.post("advisor", on_question(question))

        self.entry.bind("<Return>", submit)
        ttk.Button(compose, text="发送", command=submit, style="Send.TButton").pack(
            side="right", padx=(8, 0)
        )

    def post(self, role: str, message: str) -> None:
        def append() -> None:
            self.transcript.configure(state="normal")
            labels = {"advisor": "顾问", "you": "你", "system": "系统"}
            self.transcript.insert("end", f"{labels.get(role, role)}\n", role)
            self.transcript.insert("end", f"{message}\n")
            self.transcript.configure(state="disabled")
            self.transcript.see("end")

        self.root.after(0, append)

    def set_status(self, value: str) -> None:
        self.root.after(0, lambda: self.status.configure(text=value))

    def run(self) -> None:
        self.root.mainloop()
