# SPDX-License-Identifier: GPL-3.0-or-later
"""Differential tests: generated C++20 program versus the Python oracle.

The tests use the original synthetic fixture from ``tools/rptp/fixtures.py``;
no retail game data is involved.  Compiler artifacts stay under
``build/native-tests`` and are removed when a build succeeds.
"""
from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.rptp import cfg, codegen, elf, fixtures, ir, native, oracle

MAX_STEPS = 100_000
TOP_LEVEL_ORDER = (
    "halted", "pc", "reason", "steps", "registers",
    "hi", "lo", "hi1", "lo1", "fpr", "memory", "trace",
)


def _differential_program() -> tuple[elf.ElfImage, cfg.Program]:
    image = elf.parse_elf_bytes(fixtures.differential_fixture(), path="differential_fixture.elf")
    return image, cfg.discover_program(image)


def _program_for(data: bytes, path: str) -> tuple[elf.ElfImage, cfg.Program]:
    image = elf.parse_elf_bytes(data, path=path)
    return image, cfg.discover_program(image)


def _first_list_difference(expected: list[Any], actual: list[Any]) -> tuple[int, Any, Any]:
    for index in range(min(len(expected), len(actual))):
        if expected[index] != actual[index]:
            return index, expected[index], actual[index]
    index = min(len(expected), len(actual))
    expected_item = expected[index] if index < len(expected) else "<missing>"
    actual_item = actual[index] if index < len(actual) else "<missing>"
    return index, expected_item, actual_item


def _describe_mismatch(expected: dict[str, Any], actual: dict[str, Any]) -> str:
    """Return a compact report of the first differing top-level values."""
    lines = ["native output differs from the oracle:"]
    for key in TOP_LEVEL_ORDER:
        if key not in actual:
            lines.append(f"  {key}: missing from native output")
            continue
        if key not in expected:
            lines.append(f"  {key}: unexpected in native output")
            continue
        if actual[key] == expected[key]:
            continue
        if key == "registers":
            lines.append("  registers (native vs oracle):")
            shown = 0
            for index, (actual_pair, expected_pair) in enumerate(
                    zip(actual[key], expected[key])):
                if actual_pair != expected_pair:
                    lines.append(
                        f"    registers[{index}]: native={actual_pair!r} "
                        f"oracle={expected_pair!r}")
                    shown += 1
                    if shown >= 8:
                        lines.append("    ...")
                        break
            if len(actual[key]) != len(expected[key]):
                lines.append(
                    f"    length: native={len(actual[key])} oracle={len(expected[key])}")
        elif key in ("memory", "trace"):
            index, expected_item, actual_item = _first_list_difference(
                expected[key], actual[key])
            lines.append(
                f"  {key}: first difference at index {index}: "
                f"native={actual_item!r} oracle={expected_item!r} "
                f"(lengths native={len(actual[key])} oracle={len(expected[key])})")
        else:
            lines.append(
                f"  {key}: native={actual[key]!r} oracle={expected[key]!r}")
    return "\n".join(lines)


class NativeHarnessTests(unittest.TestCase):
    def _msvc_or_skip(self) -> native.MsvcToolchain:
        try:
            return native.find_msvc()
        except native.HarnessError as exc:
            self.skipTest(f"MSVC is genuinely unavailable: {exc}")

    def test_msvc_is_discoverable_and_cl_runs(self):
        compiler = self._msvc_or_skip()
        self.assertTrue(compiler.cl.is_file(), f"cl.exe not found at {compiler.cl}")
        self.assertTrue(compiler.vcvars.is_file(),
                        f"vcvars64.bat not found at {compiler.vcvars}")
        output = native.probe_compiler(compiler)
        self.assertIn("COMPILER OPTIONS", output.upper(),
                      f"cl.exe did not print its usage/version banner:\n{output}")

    def test_differential_fixture_matches_oracle(self):
        self._msvc_or_skip()
        image, program = _differential_program()
        result = ir.lower_program(program)
        self.assertEqual([], result.errors, "lowering produced errors")

        expected = oracle.run_oracle(program, max_steps=MAX_STEPS)
        actual = native.run_differential(image, max_steps=MAX_STEPS)
        if actual != expected:
            self.fail(_describe_mismatch(expected, actual))
        self.assertEqual(actual, expected)

    def test_broad_fixture_matches_oracle(self):
        self._msvc_or_skip()
        image, program = _program_for(fixtures.broad_fixture(), "broad_fixture.elf")
        result = ir.lower_program(program)
        self.assertEqual([], result.errors, "lowering produced errors")

        expected = oracle.run_oracle(program, max_steps=MAX_STEPS)
        actual = native.run_differential(image, max_steps=MAX_STEPS)
        if actual != expected:
            self.fail(_describe_mismatch(expected, actual))
        self.assertEqual(actual["reason"], "pc_outside_code")
        self.assertEqual(actual["pc"], 0x7FFF0000)

    def test_overflow_traps_match_oracle(self):
        self._msvc_or_skip()
        for mnemonic in ("add", "sub", "dadd", "dsub"):
            with self.subTest(mnemonic=mnemonic):
                image, program = _program_for(
                    fixtures.overflow_fixture(mnemonic), f"overflow_{mnemonic}.elf")
                result = ir.lower_program(program)
                self.assertEqual([], result.errors, "lowering produced errors")

                expected = oracle.run_oracle(program, max_steps=MAX_STEPS)
                actual = native.run_differential(image, max_steps=MAX_STEPS)
                if actual != expected:
                    self.fail(_describe_mismatch(expected, actual))
                # Both models must trap, not merely agree on untrapped values.
                self.assertEqual(actual["reason"], "trap:integer_overflow")
                self.assertTrue(actual["halted"])

    def test_generation_and_execution_are_deterministic(self):
        self._msvc_or_skip()
        _image, program = _differential_program()
        result = ir.lower_program(program)
        self.assertEqual([], result.errors, "lowering produced errors")

        first = codegen.generate(program, result)
        second = codegen.generate(program, result)
        self.assertEqual(
            hashlib.sha256(first.source.encode("utf-8")).hexdigest(),
            hashlib.sha256(second.source.encode("utf-8")).hexdigest(),
            "generated C++ source is not deterministic")
        self.assertEqual(first.source, second.source)
        self.assertEqual(
            hashlib.sha256(first.memory_blob).hexdigest(),
            hashlib.sha256(second.memory_blob).hexdigest(),
            "memory blob is not deterministic")
        self.assertEqual(first.memory_blob, second.memory_blob)

        with native.temporary_workdir() as workdir:
            exe = native.build_native(first, workdir)
            blob = workdir / codegen.MEMORY_BLOB_NAME
            first_run = native.run_native(exe, MAX_STEPS, blob)
            second_run = native.run_native(exe, MAX_STEPS, blob)
        self.assertEqual(first_run, second_run,
                         "two runs of the same native executable disagreed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
