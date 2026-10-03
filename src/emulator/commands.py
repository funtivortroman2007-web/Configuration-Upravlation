from __future__ import annotations

import shlex
from dataclasses import dataclass, field

from .vfs import VFSLoadError, VirtualFileSystem

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
            items = state.vfs.list_directory(directory)
            if items is None:
                return False, f"ls: каталог не найден: {target}"
            return True, " ".join(items) if items else "(Пусто)"
        args = " ".join(arguments) if arguments else "(нет)"
        return True, f"ls: аргументы: {args}"

    if command == "cd":
        if state.vfs_error:
            return False, f"cd: {state.vfs_error}"
        if state.vfs:
            if len(arguments) > 1:
                return False, "cd: укажите не более одного пути"
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