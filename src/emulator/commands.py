from __future__ import annotations

import posixpath
import shlex
from dataclasses import dataclass, field
from datetime import datetime
import time

from .vfs import VFSLoadError, VirtualFileSystem


def _format_uptime(seconds: float, current_time: str) -> str:
    total_seconds = max(0, int(seconds))
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    day_label = "day" if days == 1 else "days"
    return (
        f"{current_time} up {days} {day_label}, "
        f"{hours:02}:{minutes:02}:{seconds:02}"
    )


def _render_tree(vfs: VirtualFileSystem, root: str, label: str) -> str:
    lines = [label]
    totals = {"directories": 0, "files": 0}

    def visit(directory: str, prefix: str) -> None:
        children = vfs.list_directory(directory) or []
        for index, name in enumerate(children):
            is_last = index == len(children) - 1
            connector = "└── " if is_last else "├── "
            child_path = posixpath.join(directory, name)
            lines.append(f"{prefix}{connector}{name}")
            if vfs.is_directory(child_path):
                totals["directories"] += 1
                visit(child_path, prefix + ("    " if is_last else "│   "))
            else:
                totals["files"] += 1

    visit(root, "")
    directory_label = "directory" if totals["directories"] == 1 else "directories"
    file_label = "file" if totals["files"] == 1 else "files"
    lines.extend((
        "",
        f"{totals['directories']} {directory_label}, {totals['files']} {file_label}",
    ))
    return "\n".join(lines)

@dataclass
class EmulatorState:
    vfs_path: str | None = None
    cwd: str = '/'
    vfs: VirtualFileSystem | None = field(init=False, default=None)
    vfs_error: str | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        if self.vfs_path:
            try:
                self.vfs = VirtualFileSystem.from_csv(self.vfs_path)
            except VFSLoadError as error:
                self.vfs_error = str(error)

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
        if state.vfs_error:
            return False, f"ls: {state.vfs_error}"
        if state.vfs:
            if len(arguments) > 1:
                return False, "ls: укажите не более одного пути"
            target = arguments[0] if arguments else "."
            directory = state.vfs.resolve(state.cwd, target)
            if state.vfs.is_file(directory):
                return True, posixpath.basename(directory)
            items = state.vfs.list_directory(directory)
            if items is None:
                return False, f"ls: каталог не найден: {target}"
            return True, " ".join(items) if items else "(Пусто)"
        args = " ".join(arguments) if arguments else "(нет)"
        return True, f"ls: аргументы: {args}"

    if command == "cd":
        if state.vfs_error:
            return False, f"cd: {state.vfs_error}"
        if len(arguments) > 1:
            return False, "cd: укажите не более одного пути"
        if state.vfs:
            target = arguments[0] if arguments else "/"
            directory = state.vfs.resolve(state.cwd, target)
            if not state.vfs.is_directory(directory):
                return False, f"cd: каталог не найден: {target}"
            state.cwd = directory
            return True, f"cd -> {state.cwd}"
        if not arguments:
            state.cwd = '/'
        else:
            state.cwd = arguments[0]
        return True, f"cd -> {state.cwd}"

    if command == "tree":
        if state.vfs_error:
            return False, f"tree: {state.vfs_error}"
        if not state.vfs:
            return False, "tree: VFS не подключена"
        if len(arguments) > 1:
            return False, "tree: укажите не более одного пути"
        target = arguments[0] if arguments else "."
        root = state.vfs.resolve(state.cwd, target)
        if not state.vfs.is_directory(root):
            return False, f"tree: каталог не найден: {target}"
        return True, _render_tree(state.vfs, root, target)

    if command == "uptime":
        if arguments:
            return False, "uptime: команда не принимает аргументы"
        current_time = datetime.now().strftime("%H:%M:%S")
        return True, _format_uptime(time.monotonic(), current_time)

    if command == "pwd":
        return True, state.cwd

    if command == "echo":
        return True, " ".join(arguments)

    if command == "cat":
        if state.vfs_error:
            return False, f"cat: {state.vfs_error}"
        if not state.vfs:
            return False, "cat: VFS не подключена"
        if len(arguments) != 1:
            return False, "Использование: cat <файл>"
        file_path = state.vfs.resolve(state.cwd, arguments[0])
        content = state.vfs.read_file(file_path)
        if content is None:
            return False, f"cat: файл не найден: {arguments[0]}"
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            return True, f"0x{content.hex()}"
        if any(not char.isprintable() and char not in "\n\r\t" for char in text):
            return True, f"0x{content.hex()}"
        return True, text

    return False, f"Ошибка: неизвестная команда: {command}"