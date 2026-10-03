from __future__ import annotations

import base64
import binascii
import csv
import posixpath
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath


class VFSLoadError(ValueError):
    pass


@dataclass
class VirtualFileSystem:
    directories: set[str] = field(default_factory=lambda: {"/"})
    files: dict[str, bytes] = field(default_factory=dict)

    @classmethod
    def from_csv(cls, csv_path: str) -> VirtualFileSystem:
        path = Path(csv_path)
        if not path.is_file():
            raise VFSLoadError(f"CSV-файл VFS не найден: {csv_path}")

        vfs = cls()
        try:
            with path.open("r", encoding="utf-8", newline="") as source:
                reader = csv.DictReader(source)
                if not {"path", "type", "content"}.issubset(reader.fieldnames or []):
                    raise VFSLoadError(
                        "CSV VFS должен содержать столбцы path,type,content"
                    )
                for line_number, row in enumerate(reader, start=2):
                    entry_path = cls._normalize_entry_path(row["path"] or "")
                    entry_type = (row["type"] or "").strip().lower()
                    if entry_type == "dir":
                        vfs._add_directory(entry_path)
                    elif entry_type == "file":
                        if entry_path in vfs.directories or entry_path in vfs.files:
                            raise VFSLoadError(f"Повторный путь: {entry_path}")
                        vfs._add_parent_directories(entry_path)
                        try:
                            vfs.files[entry_path] = base64.b64decode(
                                row["content"] or "", validate=True
                            )
                        except (binascii.Error, ValueError) as error:
                            raise VFSLoadError(
                                f"Некорректный Base64 в строке {line_number}"
                            ) from error
                    else:
                        raise VFSLoadError(
                            f"Неизвестный тип элемента в строке {line_number}: "
                            f"{entry_type}"
                        )
        except (OSError, UnicodeError, csv.Error) as error:
            raise VFSLoadError(f"Не удалось прочитать VFS: {error}") from error
        return vfs

    @staticmethod
    def _normalize_entry_path(entry_path: str) -> str:
        candidate = PurePosixPath(entry_path)
        if not entry_path or candidate.is_absolute() or ".." in candidate.parts:
            raise VFSLoadError(f"Недопустимый путь в CSV VFS: {entry_path}")
        normalized = posixpath.normpath(entry_path)
        if normalized in (".", ""):
            raise VFSLoadError("Путь элемента VFS не может быть пустым")
        return "/" + normalized.strip("/")

    def _add_parent_directories(self, entry_path: str) -> None:
        parent = posixpath.dirname(entry_path)
        while parent not in ("", "/"):
            if parent in self.files:
                raise VFSLoadError(f"Файл используется как каталог: {parent}")
            self.directories.add(parent)
            parent = posixpath.dirname(parent)

    def _add_directory(self, entry_path: str) -> None:
        if entry_path in self.files:
            raise VFSLoadError(f"Путь уже занят файлом: {entry_path}")
        self._add_parent_directories(entry_path)
        self.directories.add(entry_path)

    def resolve(self, cwd: str, target: str = ".") -> str:
        if target.startswith("/"):
            return posixpath.normpath(target)
        return posixpath.normpath(posixpath.join(cwd, target))

    def list_directory(self, directory: str) -> list[str] | None:
        if directory not in self.directories:
            return None
        prefix = "/" if directory == "/" else directory + "/"
        children = {
            path[len(prefix):].split("/", 1)[0]
            for path in self.directories | self.files.keys()
            if path.startswith(prefix) and path != directory
        }
        return sorted(children)

    def is_directory(self, path: str) -> bool:
        return path in self.directories

    def is_file(self, path: str) -> bool:
        return path in self.files

    def read_file(self, path: str) -> bytes | None:
        return self.files.get(path)