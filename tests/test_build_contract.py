# SPDX-License-Identifier: GPL-3.0-or-later
"""Guard the documented build, CI and wrapper contracts against drift."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BuildContractTests(unittest.TestCase):
    def test_cmake_declares_supported_toolchain_and_tests(self) -> None:
        cmake = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")

        self.assertRegex(cmake, r"cmake_minimum_required\(VERSION 3\.25\)")
        self.assertRegex(cmake, r"project\(RPTP VERSION \d+\.\d+\.\d+ LANGUAGES CXX\)")
        self.assertIn("find_package(Python3 3.10 REQUIRED COMPONENTS Interpreter)", cmake)
        self.assertIn("include(CTest)", cmake)
        self.assertIn('COMMAND "${Python3_EXECUTABLE}" ${ARGN}', cmake)
        self.assertIn('WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"', cmake)

        for name in ("artifact_guard", "python_unit_tests", "gate0_differential_spike"):
            self.assertIn(f"\n        {name}\n", cmake)

        self.assertIn('"${PROJECT_SOURCE_DIR}/tools/check_forbidden_artifacts.py"', cmake)
        self.assertIn('-m unittest discover -s tests -v', cmake)
        self.assertIn('--out "${CMAKE_BINARY_DIR}/gate0" --compiler "${RPTP_GATE0_COMPILER}"', cmake)
        self.assertIn("DEPENDS rptp-doctor", cmake)
        self.assertIn('"${CMAKE_CTEST_COMMAND}" --output-on-failure', cmake)

    def test_runtime_targets_are_built_and_tested(self) -> None:
        cmake = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")

        self.assertIn("add_library(\n    rptp_runtime\n    STATIC", cmake)
        self.assertIn('target_include_directories(rptp_runtime PUBLIC "${PROJECT_SOURCE_DIR}/runtime/include")', cmake)
        self.assertIn("target_compile_features(rptp_runtime PUBLIC cxx_std_20)", cmake)
        self.assertIn("add_executable(rptp-load runtime/tools/rptp_load.cpp)", cmake)
        self.assertIn("add_executable(rptp-runtime-tests runtime/tests/runtime_tests.cpp)", cmake)
        self.assertIn("add_test(NAME runtime_loader_tests COMMAND rptp-runtime-tests)", cmake)
        self.assertIn('NAME runtime_loader_cli', cmake)
        self.assertIn('"RPTP_LOAD_BINARY=$<TARGET_FILE:rptp-load>"', cmake)
        self.assertIn("-m unittest tests.test_runtime_loader -v", cmake)
        self.assertIn("DEPENDS rptp-doctor rptp-load ${_rptp_runtime_test_target}", cmake)
        self.assertIn("/W4 /WX /permissive-", cmake)
        self.assertIn("-Wall -Wextra -Wpedantic -Werror", cmake)

    def test_presets_pair_configure_and_build_targets(self) -> None:
        presets = json.loads((ROOT / "CMakePresets.json").read_text(encoding="utf-8"))

        self.assertEqual(6, presets["version"])
        self.assertEqual({"major": 3, "minor": 25, "patch": 0}, presets["cmakeMinimumRequired"])

        configure = {preset["name"]: preset for preset in presets["configurePresets"]}
        self.assertEqual({"windows-msvc", "host"}, set(configure))
        for preset in configure.values():
            self.assertEqual("Ninja", preset["generator"])
            self.assertTrue(preset["binaryDir"].startswith("${sourceDir}/build/"))
            self.assertEqual("Debug", preset["cacheVariables"]["CMAKE_BUILD_TYPE"])
        self.assertEqual("cl", configure["windows-msvc"]["cacheVariables"]["RPTP_GATE0_COMPILER"])
        self.assertEqual("auto", configure["host"]["cacheVariables"]["RPTP_GATE0_COMPILER"])

        build = {preset["name"]: preset for preset in presets["buildPresets"]}
        self.assertEqual(set(configure), set(build))
        for name, preset in build.items():
            self.assertEqual(name, preset["configurePreset"])
            self.assertEqual(["rptp-ci"], preset["targets"])

    def test_workflow_uses_read_only_bounded_jobs(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

        self.assertIn("permissions:\n  contents: read", workflow)
        self.assertEqual(2, workflow.count("timeout-minutes: 15"))
        self.assertEqual(2, workflow.count("actions/checkout@v4"))
        self.assertEqual(2, workflow.count("actions/setup-python@v5"))
        self.assertEqual(2, workflow.count('python-version: "3.13"'))
        self.assertIn("runs-on: windows-latest", workflow)
        self.assertIn("runs-on: ubuntu-latest", workflow)
        self.assertIn('VsDevCmd.bat" -arch=x64 -host_arch=x64', workflow)
        self.assertIn("cmake --preset windows-msvc", workflow)
        self.assertIn("cmake --build --preset windows-msvc", workflow)
        self.assertIn("cmake --preset host", workflow)
        self.assertIn("cmake --build --preset host", workflow)
        self.assertNotIn("pull_request_target", workflow)
        self.assertNotIn("continue-on-error", workflow)
        self.assertNotRegex(workflow, r"\$\{\{\s*secrets\.")
        self.assertNotRegex(workflow, r"[A-Za-z]:\\")

    def test_wrapper_is_location_independent_and_explicit(self) -> None:
        wrapper = (ROOT / "scripts" / "run-msvc.ps1").read_text(encoding="utf-8")

        self.assertTrue(wrapper.startswith("# SPDX-License-Identifier: GPL-3.0-or-later\n"))
        self.assertIn("Split-Path -Parent $PSScriptRoot", wrapper)
        self.assertIn("Push-Location -LiteralPath $repoRoot", wrapper)
        self.assertIn("finally {", wrapper)
        self.assertIn("Pop-Location", wrapper)
        self.assertIn("python tools/check_forbidden_artifacts.py --root .", wrapper)
        self.assertIn("python tools/rptp_gate0_spike.py --out build/gate0-msvc --compiler cl", wrapper)
        self.assertIn("python -m unittest discover -s tests -v", wrapper)
        self.assertGreaterEqual(wrapper.count("exit $LASTEXITCODE"), 3)
        self.assertNotRegex(wrapper, r"[A-Za-z]:\\")

    def test_provenance_records_official_references_and_keeps_review_status(self) -> None:
        references = (ROOT / "docs" / "REFERENCES.md").read_text(encoding="utf-8")
        provenance = (ROOT / "docs" / "BUILD_PROVENANCE.md").read_text(encoding="utf-8")

        for reference in range(7, 13):
            self.assertIn(f"RPTP-REF-{reference:03d}", references)
            self.assertIn(f"RPTP-REF-{reference:03d}", provenance)

        for url in (
            "https://cmake.org/cmake/help/v3.25/manual/cmake-presets.7.html",
            "https://cmake.org/cmake/help/v3.25/command/add_test.html",
            "https://learn.microsoft.com/en-us/cpp/build/building-on-the-command-line?view=msvc-170",
            "https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax",
            "https://docs.python.org/3/library/unittest.html",
            "https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_scripts?view=powershell-5.1",
        ):
            self.assertIn(url, references)

        self.assertIn("agent-led re-derivation record", provenance)
        self.assertIn("`Review required` remains", provenance)
        self.assertIn("not an independent review", provenance)
        self.assertRegex(provenance, re.escape("No build behavior in this layer was derived from a sealed project"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
