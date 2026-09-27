from emulator.config import parse_args, print_debug_banner
from emulator.gui import ShellEmulator

import tkinter as tk


def main() -> None:
    args = parse_args()
    print_debug_banner(args)

    root = tk.Tk()
    ShellEmulator(root, args)
    root.mainloop()


if __name__ == "__main__":
    main()