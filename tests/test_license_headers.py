# SPDX-License-Identifier: GPL-3.0-or-later
"""Check that tracked project source files carry the SPDX license header."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_HEADER = "# SPDX-License-Identifier: GPL-3.0-or-later"


def tracked_project_files() -> list[Path]:
    """Return tracked files covered by the header policy; untracked files are skipped."""
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise unittest.SkipTest("git metadata is unavailable; cannot determine tracked files")

    paths: list[Path] = []
    for raw in result.stdout.decode("utf-8").split("\0"):
        if not raw:
            continue
        rel = PurePosixPath(raw)
        covered = (
            rel.name == "CMakeLists.txt"
            or rel.parts[:2] == (".github", "workflows") and rel.suffix == ".yml"
            or rel.suffix in {".py", ".ps1"}
        )
        if covered:
            paths.append(ROOT / Path(*rel.parts))
    return paths


class LicenseHeaderTests(unittest.TestCase):
    def test_tracked_project_sources_have_spdx_header(self) -> None:
        files = tracked_project_files()
        self.assertTrue(files, "No tracked project source files were found.")

        failures: list[str] = []
        for path in files:
            lines = path.read_text(encoding="utf-8").splitlines()
            index = 1 if lines and lines[0].startswith("#!") else 0
            if len(lines) <= index or lines[index].strip() != EXPECTED_HEADER:
                failures.append(f"{path.relative_to(ROOT).as_posix()}: header at line {index + 1}")

        self.assertEqual([], failures, "Missing SPDX header:\n" + "\n".join(failures))


if __name__ == "__main__":
    unittest.main()
