#!/usr/bin/env python3
"""Diagnose the local RPTP development environment; no dependencies required."""
from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable, Iterable

REQUIRED_PATHS = (
    "README.md",
    "LICENSE",
    ".gitignore",
    "CMakeLists.txt",
    "CMakePresets.json",
    ".github/workflows/ci.yml",
    "docs/ROADMAP.md",
    "docs/STATE.md",
    "docs/REFERENCES.md",
    "docs/DECISIONS/ADR-0001-foundation-and-clean-room.md",
    "tests/fixtures/MANIFEST",
    "tests/test_gate0_spike.py",
    "tests/test_iso_inspector.py",
    "tools/rptp_gate0_spike.py",
    "tools/rptp_inspect.py",
    "tools/check_forbidden_artifacts.py",
    "docs/ISO_INSPECTOR.md",
)


def _check(name: str, status: str, detail: str) -> dict[str, str]:
    return {"name": name, "status": status, "detail": detail}


def evaluate_environment(
    root: Path,
    system_name: str | None = None,
    python_version: tuple[int, ...] | None = None,
    which_func: Callable[[str], str | None] = shutil.which,
) -> dict[str, object]:
    """Return deterministic checks with injectable environment values for unit tests."""
    root = root.resolve()
    system = system_name or platform.system()
    version = python_version or sys.version_info[:3]
    checks: list[dict[str, str]] = []

    if version >= (3, 10):
        checks.append(_check("Python", "PASS", f"{version[0]}.{version[1]}.{version[2]}"))
    else:
        checks.append(_check("Python", "FAIL", f"Python 3.10+ required; found {version!r}"))

    missing = [item for item in REQUIRED_PATHS if not (root / item).is_file()]
    if missing:
        checks.append(_check("Project layout", "FAIL", "Missing required file(s): " + ", ".join(missing)))
    else:
        checks.append(_check("Project layout", "PASS", f"All {len(REQUIRED_PATHS)} required files are present."))

    if system.casefold() == "windows":
        compiler = which_func("cl")
        if compiler:
            checks.append(_check("C++ compiler", "PASS", f"MSVC found: {compiler}"))
        else:
            checks.append(_check("C++ compiler", "FAIL", "MSVC cl.exe not found on PATH. Open Visual Studio Developer PowerShell or an x64 Native Tools prompt."))
    else:
        candidates: Iterable[str] = ("g++", "clang++", "c++")
        found = [(name, which_func(name)) for name in candidates]
        found = [(name, path) for name, path in found if path]
        if found:
            name, path = found[0]
            checks.append(_check("C++ compiler", "PASS", f"{name} found: {path}"))
        else:
            checks.append(_check("C++ compiler", "FAIL", "No C++ compiler found; install GCC or Clang with C++20 support."))

    for tool in ("cmake", "ninja"):
        path = which_func(tool)
        if path:
            checks.append(_check(tool, "PASS", path))
        else:
            checks.append(_check(tool, "FAIL", f"{tool} not found on PATH; install it to use the project presets."))

    git_path = which_func("git")
    if git_path:
        checks.append(_check("git", "PASS", git_path))
    else:
        checks.append(_check("git", "WARN", "git not found; source tests can run, but version-control commands will not."))

    failed = any(row["status"] == "FAIL" for row in checks)
    return {
        "schema_version": 1,
        "status": "FAIL" if failed else "PASS",
        "root": str(root),
        "platform": system,
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1], help="RPTP repository root")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args()

    root = args.root.resolve()
    report = evaluate_environment(root)

    guard_path = root / "tools" / "check_forbidden_artifacts.py"
    if guard_path.is_file():
        proc = subprocess.run(
            [sys.executable, str(guard_path), "--root", str(root)],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        detail = (proc.stdout + proc.stderr).strip() or f"exit code {proc.returncode}"
        report["checks"].append(_check("Artifact guard", "PASS" if proc.returncode == 0 else "FAIL", detail))
    else:
        report["checks"].append(_check("Artifact guard", "FAIL", "Artifact guard tool is missing."))

    if any(row["status"] == "FAIL" for row in report["checks"]):
        report["status"] = "FAIL"

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"RPTP doctor — {report['root']}")
        for row in report["checks"]:
            print(f"[{row['status']}] {row['name']}: {row['detail']}")
        print(f"Overall status: {report['status']}")

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
