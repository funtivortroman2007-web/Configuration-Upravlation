from __future__ import annotations

import getpass
import socket
import tkinter as tk
from tkinter import ttk

from .commands import EmulatorState, execute_command
from .config import EmulatorConfig
from .script_runner import run_script


class ShellEmulator:
    def __init__(self, root: tk.Tk, config: EmulatorConfig) -> None:
        self.root = root
        self.config = config
        self.state = EmulatorState(vfs_path=config.vfs_path)

        username = getpass.getuser()
        hostname = socket.gethostname()
        self.root.title(f"Эмулятор - [{username}@{hostname}]")
        self.root.geometry("760x460")
        self.root.minsize(520, 320)

        self.output = tk.Text(
            root,
            wrap=tk.WORD,
            state=tk.DISABLED,
            background="#101418",
            foreground="#e8edf2",
            insertbackground="#e8edf2",
            padx=12,
            pady=12,
        )    
        self.output.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 6))

        command_frame = ttk.Frame(root)
        command_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Label(command_frame, text="> ").pack(side=tk.LEFT)
        self.command_entry = ttk.Entry(command_frame)
        self.command_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        self.command_entry.bind("<Return>", self._on_command)
        ttk.Button(
            command_frame, text="Выполнить", command=self._on_command
        ).pack(side=tk.RIGHT)
        self.command_entry.focus_set()

        if config.script_path:
            self.command_entry.configure(state=tk.DISABLED)
            self.root.after(50, self._run_startup_script)
        else:
            self._emit(
                "Эмулятор оболочки. Команды: ls, cd, tree, uptime, pwd, echo, cat, exit."
            )

    def _emit(self, text: str) -> None:
        print(text)
        self.output.configure(state=tk.NORMAL)
        self.output.insert(tk.END, f"{text}\n")
        self.output.see(tk.END)
        self.output.configure(state=tk.DISABLED)

    def _run_startup_script(self) -> None:
        run_script(
            self.config.script_path,
            self.state,
            emit=self._emit,
            on_exit=self._on_exit_from_script
        )
        self.command_entry.configure(state=tk.NORMAL)
        self.command_entry.focus_set()

    def _on_exit_from_script(self) -> None:
        # В скрипте exit не должен закрывать окно сразу - просто пометил
        pass

    def _on_command(self, _event: tk.Event | None = None) -> str:
        command_line = self.command_entry.get()
        self.command_entry.delete(0, tk.END)
        self._emit(f"> {command_line}")

        ok, out = execute_command(
            command_line,
            self.state,
            on_exit=lambda: self.root.after_idle(self.root.destroy),
        )
        if out == "__EXIT__":
            return "break"

        if out:
            self._emit(out)

        if not ok:
            self._emit("(команда завершилась с ошибкой)")
            return "break"