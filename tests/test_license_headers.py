# SPDX-License-Identifier: GPL-3.0-or-later
"""Check that tracked project source files carry the SPDX license header."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_HEADER = "# SPDX-License-Identifier: GPL-3.0-or-later"
EXPECTED_CXX_HEADER = "// SPDX-License-Identifier: GPL-3.0-or-later"


def expected_header(path: Path) -> str:
    """C++ sources use a line comment; Python, CMake and workflow files use `#`."""
    return EXPECTED_CXX_HEADER if path.suffix in {".hpp", ".cpp"} else EXPECTED_HEADER


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
            # evidence/ holds captured build output, not authored project source.
            or (rel.suffix in {".hpp", ".cpp"} and rel.parts[:1] != ("evidence",))
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
            if len(lines) <= index or lines[index].strip() != expected_header(path):
                failures.append(f"{path.relative_to(ROOT).as_posix()}: header at line {index + 1}")

        self.assertEqual([], failures, "Missing SPDX header:\n" + "\n".join(failures))

    def test_expected_header_comment_style(self) -> None:
        self.assertEqual(EXPECTED_CXX_HEADER, expected_header(Path("runtime/src/guest_memory.cpp")))
        self.assertEqual(EXPECTED_CXX_HEADER, expected_header(Path("runtime/include/rptp/runtime/elf_loader.hpp")))
        self.assertEqual(EXPECTED_HEADER, expected_header(Path("tools/rptp_doctor.py")))
        self.assertEqual(EXPECTED_HEADER, expected_header(Path("CMakeLists.txt")))
        self.assertEqual(EXPECTED_HEADER, expected_header(Path(".github/workflows/ci.yml")))


if __name__ == "__main__":
    unittest.main()
