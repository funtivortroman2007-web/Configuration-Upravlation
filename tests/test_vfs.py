import sys
import unittest
import re
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from emulator.commands import EmulatorState, execute_command
from emulator.script_runner import run_script


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class VirtualFileSystemTests(unittest.TestCase):
    def setUp(self):
        self.state = EmulatorState(
            vfs_path=str(REPOSITORY_ROOT / "src" / "vfs" / "nested.csv")
        )

    def run_command(self, command):
        return execute_command(command, self.state)

    def test_lists_nested_entries_without_reading_host_directories(self):
        self.assertEqual(self.run_command("ls"), (True, "home share"))
        self.assertEqual(self.run_command("ls /share/docs"), (True, "assets manual.txt"))
        self.assertEqual(self.run_command("ls /etc"), (False, "ls: каталог не найден: /etc"))

    def test_cd_resolves_relative_paths_inside_vfs(self):
        self.assertEqual(self.run_command("cd share/docs"), (True, "cd -> /share/docs"))
        self.assertEqual(self.run_command("cd assets"), (True, "cd -> /share/docs/assets"))
        self.assertEqual(self.run_command("pwd"), (True, "/share/docs/assets"))
        self.assertEqual(self.run_command("cd ../../../home"), (True, "cd -> /home"))

    def test_ls_lists_files_and_rejects_missing_paths(self):
        self.assertEqual(self.run_command("ls /home/welcome.txt"), (True, "welcome.txt"))
        self.assertFalse(self.run_command("ls /missing")[0])

    def test_tree_renders_nested_files_and_directory_totals(self):
        ok, output = self.run_command("tree /share")
        self.assertTrue(ok)
        self.assertEqual(
            output,
            "/share\n"
            "└── docs\n"
            "    ├── assets\n"
            "    │   └── data.bin\n"
            "    └── manual.txt\n"
            "\n"
            "2 directories, 2 files",
        )

    def test_tree_rejects_files_and_missing_directories(self):
        self.assertEqual(
            self.run_command("tree /home/welcome.txt"),
            (False, "tree: каталог не найден: /home/welcome.txt"),
        )
        self.assertFalse(self.run_command("tree /missing")[0])

    def test_uptime_uses_system_monotonic_time_and_rejects_arguments(self):
        with patch("emulator.commands.time.monotonic", return_value=90061):
            ok, output = self.run_command("uptime")
        self.assertTrue(ok)
        self.assertRegex(output, re.compile(r"^\d{2}:\d{2}:\d{2} up 1 day, 01:01:01$"))
        self.assertEqual(
            self.run_command("uptime extra"),
            (False, "uptime: команда не принимает аргументы"),
        )

    def test_cat_reads_base64_decoded_text_and_binary_data(self):
        self.assertEqual(self.run_command("cat /home/welcome.txt"), (True, "Hello from home.\n"))
        self.assertEqual(
            self.run_command("cat /share/docs/assets/data.bin"),
            (True, "0x000102ff"),
        )

    def test_missing_csv_is_reported_as_command_error(self):
        state = EmulatorState(vfs_path=str(REPOSITORY_ROOT / "missing.csv"))
        self.assertFalse(execute_command("ls", state)[0])
        self.assertIn("CSV-файл VFS не найден", state.vfs_error)

    def test_startup_script_exercises_vfs_commands_and_reports_errors(self):
        output = []
        script = REPOSITORY_ROOT / "src" / "scripts" / "start1.txt"
        run_script(str(script), self.state, output.append)
        self.assertIn("Hello from home.\n", output)
        self.assertIn("/share/docs/assets", output)
        self.assertTrue(any("Ошибка разбора команды" in line for line in output))
        self.assertTrue(any("завершен с ошибками" in line for line in output))

    def test_stage_four_script_covers_tree_uptime_and_command_errors(self):
        output = []
        script = REPOSITORY_ROOT / "src" / "scripts" / "start4.txt"
        run_script(str(script), self.state, output.append)
        self.assertTrue(any(line.startswith(".\n└── data.bin") for line in output))
        self.assertTrue(any("up " in line for line in output))
        self.assertTrue(any("tree: каталог не найден" in line for line in output))
        self.assertTrue(any("cd: каталог не найден" in line for line in output))
        self.assertTrue(any("Ошибка разбора команды" in line for line in output))
        self.assertTrue(any("завершен с ошибками" in line for line in output))

    def test_all_sample_csv_images_load(self):
        scenarios = (
            ("minimal.csv", "start_minimal.txt"),
            ("files.csv", "start_files.txt"),
            ("nested.csv", "start1.txt"),
        )
        for image, script_name in scenarios:
            with self.subTest(image=image):
                state = EmulatorState(vfs_path=str(REPOSITORY_ROOT / "src" / "vfs" / image))
                self.assertIsNone(state.vfs_error)
                self.assertIsNotNone(state.vfs)
                output = []
                script = REPOSITORY_ROOT / "src" / "scripts" / script_name
                run_script(str(script), state, output.append)
                if script_name in ("start1.txt", "start_minimal.txt"):
                    self.assertTrue(any("завершен с ошибками" in line for line in output))
                else:
                    self.assertIn("--- Скрипт выполнен успешно ---", output)


if __name__ == "__main__":
    unittest.main()