from emulator.config import parse_args
from emulator.gui import ShellEmulator

import tkinter as tk


def main() -> None:
    args = parse_args()

    root = tk.Tk()
    ShellEmulator(root, args)
    root.mainloop()


if __name__ == "__main__":
    main()