"""Stage 1: a small graphical shell emulator (REPL)."""

from __future__ import annotations

import getpass
import shlex
import socket
import tkinter as tk
from tkinter import ttk
from typing import Callable


def parse_command(command_line: str) -> list[str]:
	"""Split a command line into a command and its arguments."""
	return shlex.split(command_line)


def execute_command(
	command_line: str,
	on_exit: Callable[[], None] | None = None,
) -> str:
	"""Execute one stage-1 command and return text for the terminal output."""
	try:
		parts = parse_command(command_line)
	except ValueError as error:
		return f"Ошибка разбора команды: {error}"

	if not parts:
		return ""

	command, *arguments = parts
	if command == "exit":
		if on_exit is not None:
			on_exit()
		return "Завершение работы эмулятора..."

	if command in {"ls", "cd"}:
		arguments_text = " ".join(arguments) if arguments else "(нет)"
		return f"{command}: аргументы: {arguments_text}"

	return f"Ошибка: неизвестная команда: {command}"


class ShellEmulator:
	"""Tkinter UI for the stage-1 shell emulator."""

	def __init__(self, root: tk.Tk) -> None:
		self.root = root
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
		ttk.Button(command_frame, text="Выполнить", command=self._on_command).pack(
			side=tk.RIGHT
		)
		self.command_entry.focus_set()

		self._write_output("Эмулятор оболочки. Доступные команды: ls, cd, exit.")

	def _write_output(self, text: str) -> None:
		self.output.configure(state=tk.NORMAL)
		self.output.insert(tk.END, f"{text}\n")
		self.output.see(tk.END)
		self.output.configure(state=tk.DISABLED)

	def _on_command(self, _event: tk.Event | None = None) -> str:
		command_line = self.command_entry.get()
		self.command_entry.delete(0, tk.END)
		self._write_output(f"> {command_line}")
		result = execute_command(
			command_line,
			lambda: self.root.after_idle(self.root.destroy),
		)
		if result:
			self._write_output(result)
		return "break"


def main() -> None:
	root = tk.Tk()
	ShellEmulator(root)
	root.mainloop()


if __name__ == "__main__":
	main()