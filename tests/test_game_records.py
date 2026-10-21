# SPDX-License-Identifier: GPL-3.0-or-later

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
GAMES = ROOT / "docs" / "games"


class GameRecordTests(unittest.TestCase):
    def test_every_game_folder_has_indexed_status_record(self):
        index = (GAMES / "README.md").read_text(encoding="utf-8")
        directories = sorted(path for path in GAMES.iterdir() if path.is_dir())
        self.assertTrue(directories, "At least one game record is expected.")
        for directory in directories:
            with self.subTest(game=directory.name):
                status = directory / "STATUS.md"
                self.assertTrue(status.is_file(), f"Missing {status.relative_to(ROOT)}.")
                text = status.read_text(encoding="utf-8")
                self.assertIn("**Status:**", text)
                self.assertIn("**Last updated:**", text)
                self.assertIn(f"({directory.name}/STATUS.md)", index)


if __name__ == "__main__":
    unittest.main(verbosity=2)
