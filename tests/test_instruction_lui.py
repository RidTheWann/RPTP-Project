# SPDX-License-Identifier: GPL-3.0-or-later
"""Focused synthetic tests for the LUI immediate."""
from __future__ import annotations

from dataclasses import replace
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module {relative_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


spike = load_module("rptp_gate0_spike_lui", "tools/rptp_gate0_spike.py")
ir = load_module("rptp_ir_lui", "tools/rptp_ir.py")
lower = load_module("rptp_lower_lui", "tools/rptp_lower.py")

BASE = spike.BASE
ZERO = spike.ZERO
V0 = spike.V0
T0 = spike.T0
T1 = spike.T1
T2 = spike.T2
T3 = spike.T3
T4 = spike.T4
RA = spike.RA

LUI = 0x0F
SHIFTED16 = "shifted16"
BOUNDARIES = (
    (T0, 0x0000, 0x0000000000000000),
    (T1, 0x0001, 0x0000000000010000),
    (T2, 0x7FFF, 0x000000007FFF0000),
    (T3, 0x8000, 0xFFFFFFFF80000000),
    (T4, 0xFFFF, 0xFFFFFFFFFFFF0000),
)


def nop_word() -> int:
    return spike.encode_r(ZERO, ZERO, ZERO, 0, 0x00)


def jr_ra_word() -> int:
    return spike.encode_r(RA, ZERO, ZERO, 0, 0x08)


def lui_fixture_rows() -> list[tuple[int, str, int]]:
    rows = [
        (f"lui_{immediate:04x}", spike.encode_i(LUI, ZERO, register, immediate))
        for register, immediate, _ in BOUNDARIES
    ]
    rows.extend(
        [
            ("zero_destination_lui", spike.encode_i(LUI, ZERO, ZERO, 0xFFFF)),
            ("return_value", spike.encode_i(0x09, ZERO, V0, 42)),
            ("return_from_main", jr_ra_word()),
            ("main_return_delay_slot", nop_word()),
        ]
    )
    return [(BASE + index * 4, name, word) for index, (name, word) in enumerate(rows)]


def lui_fixture():
    data = spike.build_elf_from_rows(lui_fixture_rows())
    return data, ir.analyze_elf(data)


def replace_instruction(result, pc: int, **fields):
    instructions = tuple(
        replace(instruction, **fields) if instruction.pc == pc else instruction
        for instruction in result.instructions
    )
    return replace(result, instructions=instructions)


def compiler_available() -> str | None:
    candidate = "cl" if os.name == "nt" and shutil.which("cl") else (os.environ.get("CXX") or "c++")
    return candidate if shutil.which(candidate) is not None else None


class LuiDecodeTests(unittest.TestCase):
    def test_decode_lui_records_shifted_immediate_and_zero_rs(self):
        instruction = spike.decode_instruction(BASE, spike.encode_i(LUI, ZERO, T1, 0x8000))

        self.assertEqual(instruction["op"], "lui")
        self.assertEqual(instruction["rs"], ZERO)
        self.assertEqual(instruction["rt"], T1)
        self.assertEqual(instruction["imm"], 0x8000)

    def test_decode_lui_rejects_nonzero_rs(self):
        with self.assertRaisesRegex(ValueError, "LUI requires rs=0"):
            spike.decode_instruction(BASE, spike.encode_i(LUI, T0, T1, 0x8000))


class LuiIrTests(unittest.TestCase):
    def test_ir_marks_lui_immediate_and_destination(self):
        words = {
            BASE: spike.encode_i(LUI, ZERO, T1, 0x8000),
            BASE + 4: spike.encode_i(LUI, ZERO, ZERO, 0xFFFF),
        }
        result = ir.analyze_words(BASE, words)
        by_pc = {instruction.pc: instruction for instruction in result.instructions}

        lui = by_pc[BASE]
        self.assertEqual(lui.op, "lui")
        self.assertEqual(lui.word, words[BASE])
        self.assertEqual((lui.rs, lui.rt), (ZERO, T1))
        self.assertEqual((lui.immediate, lui.immediate_kind), (0x8000, SHIFTED16))
        self.assertEqual(lui.destination_register, T1)
        self.assertEqual(lui.control, ir.FALLTHROUGH)

        zero_destination = by_pc[BASE + 4]
        self.assertEqual(zero_destination.op, "lui")
        self.assertEqual((zero_destination.rs, zero_destination.rt), (ZERO, ZERO))
        self.assertIsNone(zero_destination.destination_register)

    def test_ir_rejects_nonzero_rs_lui_fail_closed(self):
        with self.assertRaises(ir.AnalysisError) as caught:
            ir.analyze_words(BASE, {BASE: spike.encode_i(LUI, T0, T1, 0x8000)})

        self.assertEqual(caught.exception.code, ir.IR_UNSUPPORTED_INSTRUCTION)
        self.assertIn("LUI requires rs=0", str(caught.exception))


class LuiOracleTests(unittest.TestCase):
    def test_oracle_sign_extends_shifted_immediates_and_ignores_zero_register(self):
        data, _ = lui_fixture()
        entry, words, info = spike.parse_elf(data)
        state = spike.normalize_state(spike.execute_oracle(entry, words))
        registers = state["registers"]

        self.assertEqual(info["instruction_count"], 9)
        self.assertEqual(registers[ZERO], 0)
        for register, _, expected in BOUNDARIES:
            with self.subTest(register=register):
                self.assertEqual(registers[register], expected)
        self.assertEqual(registers[V0], 42)
        self.assertEqual(state["memory"], [])
        self.assertEqual(state["pc"], spike.RETURN_SENTINEL)
        self.assertTrue(state["halted"])
        self.assertEqual(state["trace"], [BASE + index * 4 for index in range(9)])


class LuiLoweringTests(unittest.TestCase):
    def test_lui_generated_native_state_matches_oracle(self):
        candidate = compiler_available()
        if candidate is None:
            self.skipTest("No C++ compiler available for the LUI native differential")

        data, result = lui_fixture()
        entry, words, _ = spike.parse_elf(data)
        oracle = spike.normalize_state(spike.execute_oracle(entry, words))
        source_text = lower.lower_to_cpp(result)

        with tempfile.TemporaryDirectory() as temp:
            out_dir = Path(temp)
            source = out_dir / "generated.cpp"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            exe = out_dir / ("rptp-lui.exe" if os.name == "nt" else "rptp-lui")
            command = spike.compile_generated(source, exe, "auto")
            proc = subprocess.run([str(exe)], cwd=out_dir, text=True, capture_output=True, check=False)

        self.assertEqual(proc.returncode, 0, msg=f"{command}\n{proc.stdout}\n{proc.stderr}")
        native = json.loads(proc.stdout)
        self.assertEqual(native, oracle)
        registers = native["registers"]
        self.assertEqual(registers[ZERO], 0)
        for register, _, expected in BOUNDARIES:
            with self.subTest(register=register):
                self.assertEqual(registers[register], expected)
        self.assertEqual(registers[V0], 42)

    def test_lui_lowering_is_deterministic_and_ignores_raw_word_only_changes(self):
        _, result = lui_fixture()
        first = lower.lower_to_cpp(result)
        changed_words = replace(
            result,
            instructions=tuple(replace(instruction, word=0) for instruction in result.instructions),
        )

        self.assertEqual(first, lower.lower_to_cpp(result))
        self.assertEqual(first, lower.lower_to_cpp(changed_words))
        self.assertNotIn("\r", first)
        self.assertTrue(first.endswith("\n"))

    def test_lui_lowering_rejects_metadata_that_disagrees_with_the_encoding(self):
        _, result = lui_fixture()

        cases = {
            "nonzero_rs": {"rs": T0},
            "missing_rs": {"rs": None},
            "wrong_immediate_kind": {"immediate_kind": "zero16"},
            "out_of_range_immediate": {"immediate": 0x10000},
            "wrong_destination": {"destination_register": None},
        }
        for name, fields in cases.items():
            with self.subTest(name=name):
                malformed = replace_instruction(result, BASE, **fields)
                with self.assertRaises(lower.LoweringError) as caught:
                    lower.lower_to_cpp(malformed)
                self.assertEqual(caught.exception.code, lower.LOWER_MALFORMED_INSTRUCTION)


if __name__ == "__main__":
    unittest.main(verbosity=2)
