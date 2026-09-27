from __future__ import annotations

import os
from typing import Callable

from .commands import EmulatorState, execute_command

def run_script(
        script_path: str,
        state: EmulatorState,
        emit: Callable[[str], None],
        on_exit: Callable[[], None] | None = None,
) -> None:
    if not os.path.isfile(script_path):
        emit(f'Ошибка: файл скрипта не найден: {script_path}')
        return
    emit(f'---Запуск скрипта: {script_path} ---')
    errors: list[int] = []

    with open(script_path, "r") as f:
        for lineno, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue

            emit(f"> {line}")

            try:
                ok, out = execute_command(line, state, on_exit=on_exit)

            except Exception as e:
                emit(f"Ошибка: {e}")
                errors.append(lineno)
                continue

            if out == "__EXIT__":
                emit("Скрипт остановлен командой exit")
                break
            if out:
                emit(out)
            if not ok:
                errors.append(lineno)

    if errors:
        emit(f"--- Скрипт завершен с ошибками в строках: {errors} ---")
    else:
        emit("--- Скрипт выполнен успешно ---")