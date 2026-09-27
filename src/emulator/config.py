from __future__ import annotations

import argparse
from dataclasses import dataclass

@dataclass
class EmulatorConfig:
    vfs_path: str | None
    script_path: str | None

    @property
    def mode(self) -> str:
        return "script" if self.script_path else "interactive"

def parse_args(argv: list[str] | None = None) -> EmulatorConfig:
    parser = argparse.ArgumentParser(
        prog="emulator"
    )
    parser.add_argument(
        "--vfs", "-v",
        default=None
    )
    parser.add_argument(
        "--script", "-s",
        default=None
    )
    ns = parser.parse_args(argv)
    return EmulatorConfig(vfs_path=ns.vfs, script_path=ns.script)