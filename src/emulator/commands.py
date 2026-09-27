from __future__ import annotations

import os
import shlex
from dataclasses import dataclass, field

@dataclass
class EmulatorState:
    vfs_path: str | None = None
    cwd: str = '/'

def parse_command(command_line: str) -> list[str]:
    return shlex.split(command_line)

def execute_command(
        command_line: str,
        state: EmulatorState,
        on_exit=None,
) -> tuple[bool, str]:
    try:
        parts = parse_command(command_line)
    except ValueError as e:
        return False, f"Ошибка разбора команды: {e}"

    if not parts:
        return True, ""

    command, *arguments = parts

    if command == "exit":
        if on_exit is not None:
            on_exit()
        return True, "__EXIT__"

    if command == "ls":
        if state.vfs_path and os.path.isdir(state.vfs_path):
            try:
                items = os.listdir(state.vfs_path)
                return True, " ".join(items) if items else "(Пусто)"
            except OSError as e:
                return False, f"ls: {e}"
        args = " ".join(arguments) if arguments else "(нет)"
        return True, f"ls: аргументы: {args}"

    if command == "cd":
        if not arguments:
            state.cwd = '/'
        else:
            state.cwd = arguments[0]
        return True, f"cd -> {state.cwd}"

    if command == "pwd":
        return True, state.cwd

    if command == "echo":
        return True , " ".join(arguments)

    return False, f"Ошибка: неизвестная команда{command}"