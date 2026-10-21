from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("rptp_doctor", ROOT / "tools/rptp_doctor.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Cannot load tools/rptp_doctor.py")
doctor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(doctor)


class RptpDoctorTests(unittest.TestCase):
    def make_project_layout(self, root: Path) -> None:
        for relative in doctor.REQUIRED_PATHS:
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("fixture", encoding="utf-8")

    @staticmethod
    def fake_which(available: set[str]):
        def which(name: str):
            return f"/test-bin/{name}" if name in available else None
        return which

    def test_supported_python_and_linux_toolchain_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_project_layout(root)
            result = doctor.evaluate_environment(root, "Linux", (3, 13, 0), self.fake_which({"g++", "cmake", "ninja", "git"}))
            self.assertEqual(result["status"], "PASS")
            self.assertFalse(any(row["status"] == "FAIL" for row in result["checks"]))

    def test_old_python_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_project_layout(root)
            result = doctor.evaluate_environment(root, "Linux", (3, 9, 18), self.fake_which({"g++", "cmake", "ninja", "git"}))
            self.assertEqual(result["status"], "FAIL")
            self.assertTrue(any(row["name"] == "Python" and row["status"] == "FAIL" for row in result["checks"]))

    def test_windows_requires_msvc_on_path(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_project_layout(root)
            result = doctor.evaluate_environment(root, "Windows", (3, 13, 0), self.fake_which({"cmake", "ninja", "git"}))
            compiler = next(row for row in result["checks"] if row["name"] == "C++ compiler")
            self.assertEqual(compiler["status"], "FAIL")
            self.assertIn("Developer PowerShell", compiler["detail"])

    def test_linux_accepts_clang_when_gcc_is_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_project_layout(root)
            result = doctor.evaluate_environment(root, "Linux", (3, 13, 0), self.fake_which({"clang++", "cmake", "ninja", "git"}))
            compiler = next(row for row in result["checks"] if row["name"] == "C++ compiler")
            self.assertEqual(compiler["status"], "PASS")
            self.assertIn("clang++", compiler["detail"])

    def test_missing_project_files_are_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            result = doctor.evaluate_environment(Path(temp), "Linux", (3, 13, 0), self.fake_which({"g++", "cmake", "ninja", "git"}))
            layout = next(row for row in result["checks"] if row["name"] == "Project layout")
            self.assertEqual(layout["status"], "FAIL")
            self.assertIn("CMakeLists.txt", layout["detail"])

    def test_missing_cmake_or_ninja_fails_with_actionable_message(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_project_layout(root)
            result = doctor.evaluate_environment(root, "Linux", (3, 13, 0), self.fake_which({"g++", "git"}))
            self.assertEqual(result["status"], "FAIL")
            missing = {row["name"] for row in result["checks"] if row["status"] == "FAIL"}
            self.assertTrue({"cmake", "ninja"}.issubset(missing))


if __name__ == "__main__":
    unittest.main(verbosity=2)
