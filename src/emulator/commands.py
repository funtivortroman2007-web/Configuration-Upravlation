from __future__ import annotations

import posixpath
import re
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


def _format_mode(mode: int, is_directory: bool) -> str:
    permissions = [
        "r" if mode & 0o400 else "-",
        "w" if mode & 0o200 else "-",
        "x" if mode & 0o100 else "-",
        "r" if mode & 0o040 else "-",
        "w" if mode & 0o020 else "-",
        "x" if mode & 0o010 else "-",
        "r" if mode & 0o004 else "-",
        "w" if mode & 0o002 else "-",
        "x" if mode & 0o001 else "-",
    ]
    for bit, index, lower, upper in (
        (0o4000, 2, "s", "S"),
        (0o2000, 5, "s", "S"),
        (0o1000, 8, "t", "T"),
    ):
        if mode & bit:
            permissions[index] = lower if permissions[index] == "x" else upper
    return ("d" if is_directory else "-") + "".join(permissions)


def _apply_mode_spec(mode_spec: str, current_mode: int) -> int | None:
    if re.fullmatch(r"[0-7]{3,4}", mode_spec):
        return int(mode_spec, 8)

    mode = current_mode
    for clause in mode_spec.split(","):
        match = re.fullmatch(r"([ugoa]*)([+=-])([rwx]*)", clause)
        if not match:
            return None
        classes, operator, permissions = match.groups()
        selected_classes = set("ugo" if not classes or "a" in classes else classes)
        class_bits = {"u": (6, 0o700), "g": (3, 0o070), "o": (0, 0o007)}
        selected_mask = 0
        permission_mask = 0
        for class_name in selected_classes:
            shift, mask = class_bits[class_name]
            selected_mask |= mask
            for permission, value in (("r", 4), ("w", 2), ("x", 1)):
                if permission in permissions:
                    permission_mask |= value << shift
        if operator == "+":
            mode |= permission_mask
        elif operator == "-":
            mode &= ~permission_mask
        else:
            mode = (mode & ~selected_mask) | permission_mask
    return mode

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
            if any(argument.startswith("-") and argument != "-l" for argument in arguments):
                return False, "ls: поддерживается только параметр -l"
            paths = [argument for argument in arguments if argument != "-l"]
            if len(paths) > 1:
                return False, "ls: укажите не более одного пути"
            long_listing = "-l" in arguments
            target = paths[0] if paths else "."
            directory = state.vfs.resolve(state.cwd, target)
            if state.vfs.is_file(directory):
                if not long_listing:
                    return True, posixpath.basename(directory)
                mode = state.vfs.get_mode(directory) or 0
                return True, f"{_format_mode(mode, False)} {posixpath.basename(directory)}"
            items = state.vfs.list_directory(directory)
            if items is None:
                return False, f"ls: каталог не найден: {target}"
            if long_listing:
                return True, "\n".join(
                    f"{_format_mode(state.vfs.get_mode(posixpath.join(directory, name)) or 0, state.vfs.is_directory(posixpath.join(directory, name)))} {name}"
                    for name in items
                ) if items else "(Пусто)"
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

    if command == "chmod":
        if state.vfs_error:
            return False, f"chmod: {state.vfs_error}"
        if not state.vfs:
            return False, "chmod: VFS не подключена"
        if len(arguments) != 2:
            return False, "Использование: chmod <режим> <путь>"
        mode_spec, target = arguments
        path = state.vfs.resolve(state.cwd, target)
        current_mode = state.vfs.get_mode(path)
        if current_mode is None:
            return False, f"chmod: файл или каталог не найден: {target}"
        new_mode = _apply_mode_spec(mode_spec, current_mode)
        if new_mode is None:
            return False, f"chmod: некорректный режим: {mode_spec}"
        state.vfs.set_mode(path, new_mode)
        return True, f"chmod: {mode_spec} {target}"

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