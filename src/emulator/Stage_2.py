#!/usr/bin/env python3
import argparse
import os
import socket
import getpass
import sys
import tkinter as tk
from tkinter import scrolledtext


# ---------- Конфигурация (Этап 2) ----------

def parse_args():
    """Разбор параметров командной строки."""
    parser = argparse.ArgumentParser(
        description="VFS Emulator - этап 2 (конфигурация)"
    )
    parser.add_argument(
        "--vfs", "-v",
        default=None,
        help="Путь к физическому расположению VFS"
    )
    parser.add_argument(
        "--script", "-s",
        default=None,
        help="Путь к стартовому скрипту"
    )
    return parser.parse_args()


def print_debug_banner(args):
    """Отладочный вывод всех заданных параметров при запуске."""
    print("=" * 50)
    print("=== Emulator started ===")
    print(f"VFS path:    {args.vfs if args.vfs else '<not specified>'}")
    print(f"Script path: {args.script if args.script else '<not specified>'}")
    print(f"Mode:        {'script' if args.script else 'interactive'}")
    print("=" * 50)


# ---------- Ядро эмулятора ----------

class Emulator:
    def __init__(self, vfs_path=None):
        self.vfs_path = vfs_path
        self.cwd = "/"  # текущая директория в виртуальной ФС

    def execute(self, line):
        """
        Выполняет одну строку команды.
        Возвращает (успех: bool, вывод: str).
        """
        line = line.strip()
        if not line:
            return True, ""

        parts = line.split()
        cmd, argv = parts[0], parts[1:]

        # --- команды-заглушки из этапа 1 ---
        if cmd == "ls":
            # Заглушка: показываем содержимое физической VFS, если она есть
            if self.vfs_path and os.path.isdir(self.vfs_path):
                try:
                    items = os.listdir(self.vfs_path)
                    return True, "  ".join(items) if items else "(empty)"
                except OSError as e:
                    return False, f"ls: {e}"
            return True, f"ls called with args: {argv}"

        elif cmd == "cd":
            if not argv:
                self.cwd = "/"
                return True, f"cd -> {self.cwd}"
            self.cwd = argv[0]
            return True, f"cd -> {self.cwd}"

        elif cmd == "pwd":
            return True, self.cwd

        elif cmd == "echo":
            return True, " ".join(argv)

        elif cmd == "exit":
            # Специальный сигнал — завершить скрипт/REPL
            return True, "__EXIT__"

        else:
            return False, f"unknown command: '{cmd}'"


# ---------- Запуск стартового скрипта ----------

def run_script(script_path, emulator, emit):
    """
    Выполняет стартовый скрипт построчно.
    emit(text) — функция вывода (в GUI и/или консоль).
    """
    if not os.path.isfile(script_path):
        emit(f"Error: script file not found: {script_path}")
        return

    emit(f"--- Running script: {script_path} ---")
    errors = []

    with open(script_path, "r", encoding="utf-8") as f:
        for lineno, raw in enumerate(f, start=1):
            line = raw.strip()

            # пустые строки и комментарии пропускаем
            if not line or line.startswith("#"):
                continue

            # 1) имитируем ввод пользователя
            emit(f"> {line}")

            # 2) выполняем
            try:
                ok, out = emulator.execute(line)
                if out == "__EXIT__":
                    emit("(script stopped by 'exit')")
                    break
                if out:
                    emit(out)
                if not ok:
                    errors.append(lineno)
            except Exception as e:
                emit(f"Error: {e}")
                errors.append(lineno)

    # 3) итоговое сообщение об ошибках
    if errors:
        emit(f"--- Script finished with errors on lines: {errors} ---")
    else:
        emit("--- Script finished successfully ---")


# ---------- GUI ----------

class EmulatorGUI:
    def __init__(self, root, args):
        self.root = root
        self.args = args

        # заголовок окна из этапа 1
        user = getpass.getuser()
        host = socket.gethostname()
        root.title(f"Эмулятор - [{user}@{host}]")

        # область вывода
        self.output = scrolledtext.ScrolledText(root, height=20, width=80)
        self.output.pack(padx=8, pady=8, fill=tk.BOTH, expand=True)
        self.output.configure(state="disabled")

        # поле ввода
        self.entry = tk.Entry(root)
        self.entry.pack(padx=8, pady=(0, 8), fill=tk.X)
        self.entry.bind("<Return>", self.on_enter)

        # эмулятор
        self.emulator = Emulator(vfs_path=args.vfs)

        # отладочный баннер в GUI
        self.emit("=" * 50)
        self.emit("=== Emulator started ===")
        self.emit(f"VFS path:    {args.vfs if args.vfs else '<not specified>'}")
        self.emit(f"Script path: {args.script if args.script else '<not specified>'}")
        self.emit(f"Mode:        {'script' if args.script else 'interactive'}")
        self.emit("=" * 50)

        # если задан скрипт — запускаем сразу после отрисовки окна
        if args.script:
            self.entry.configure(state="disabled")
            root.after(100, self.run_startup_script)
        else:
            self.entry.focus_set()

    def emit(self, text):
        """Пишем и в GUI, и в консоль (для shell-тестов)."""
        print(text)
        self.output.configure(state="normal")
        self.output.insert(tk.END, text + "\n")
        self.output.see(tk.END)
        self.output.configure(state="disabled")

    def run_startup_script(self):
        run_script(self.args.script, self.emulator, self.emit)
        # после скрипта — можно вернуть интерактив
        self.entry.configure(state="normal")
        self.entry.focus_set()

    def on_enter(self, event):
        line = self.entry.get().strip()
        self.entry.delete(0, tk.END)
        if not line:
            return

        self.emit(f"> {line}")
        ok, out = self.emulator.execute(line)
        if out == "__EXIT__":
            self.root.destroy()
            return
        if out:
            self.emit(out)
        if not ok:
            self.emit("(command failed)")


# ---------- main ----------

def main():
    args = parse_args()
    print_debug_banner(args)

    root = tk.Tk()
    app = EmulatorGUI(root, args)
    root.mainloop()


if __name__ == "__main__":
    main()