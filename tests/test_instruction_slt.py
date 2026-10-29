# SPDX-License-Identifier: GPL-3.0-or-later
"""Focused synthetic tests for the SLT register comparison operation."""
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


spike = load_module("rptp_gate0_spike_slt", "tools/rptp_gate0_spike.py")
ir = load_module("rptp_ir_slt", "tools/rptp_ir.py")
lower = load_module("rptp_lower_slt", "tools/rptp_lower.py")

BASE = spike.BASE
ZERO = spike.ZERO
V0 = spike.V0
T0 = spike.T0
T1 = spike.T1
T2 = spike.T2
T3 = spike.T3
T4 = spike.T4
T5 = 13
S0 = spike.S0
S1 = spike.S1
S2 = spike.S2
S3 = spike.S3
S4 = spike.S4
S5 = 21
S6 = 22
S7 = spike.S7
RA = spike.RA

SLT = 0x2A
UNSUPPORTED_SPECIAL = 0x2C

INT64_MIN = 0x8000000000000000
INT64_MAX = 0x7FFFFFFFFFFFFFFF
UINT64_MASK = 0xFFFFFFFFFFFFFFFF


def nop_word() -> int:
    return spike.encode_r(ZERO, ZERO, ZERO, 0, 0x00)


def jr_ra_word() -> int:
    return spike.encode_r(RA, ZERO, ZERO, 0, 0x08)


def slt_fixture_rows() -> list[tuple[int, str, int]]:
    rows = [
        ("set_negative", spike.encode_i(0x09, ZERO, T0, -1)),
        ("set_zero_value", spike.encode_i(0x09, ZERO, T1, 0)),
        ("slt_negative_vs_zero", spike.encode_r(T0, T1, T2, 0, SLT)),
        ("set_positive", spike.encode_i(0x09, ZERO, T3, 1)),
        ("slt_positive_vs_negative", spike.encode_r(T3, T0, T4, 0, SLT)),
        ("set_equal_left", spike.encode_i(0x09, ZERO, S0, 5)),
        ("set_equal_right", spike.encode_i(0x09, ZERO, S1, 5)),
        ("slt_equal", spike.encode_r(S0, S1, S2, 0, SLT)),
        ("slt_destination_aliases_first_source", spike.encode_r(S0, T0, S0, 0, SLT)),
        ("set_second_alias_value", spike.encode_i(0x09, ZERO, T5, 10)),
        ("slt_destination_aliases_second_source", spike.encode_r(T0, T5, T5, 0, SLT)),
        ("slt_zero_destination", spike.encode_r(T0, T1, ZERO, 0, SLT)),
        ("slt_zero_source", spike.encode_r(ZERO, T3, S3, 0, SLT)),
        ("set_positive_high", spike.encode_i(0x0F, ZERO, S4, 0x7FFF)),
        ("set_negative_high", spike.encode_i(0x0F, ZERO, S5, 0x8000)),
        ("slt_negative_high_vs_positive_high", spike.encode_r(S5, S4, S6, 0, SLT)),
        ("slt_positive_high_vs_negative_high", spike.encode_r(S4, S5, S7, 0, SLT)),
        ("return_value", spike.encode_i(0x09, ZERO, V0, 42)),
        ("return_from_main", jr_ra_word()),
        ("main_return_delay_slot", nop_word()),
    ]
    return [(BASE + index * 4, name, word) for index, (name, word) in enumerate(rows)]


def slt_fixture():
    data = spike.build_elf_from_rows(slt_fixture_rows())
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


class SltDecodeTests(unittest.TestCase):
    def test_decode_slt_encoding(self):
        word = spike.encode_r(T0, T1, T2, 0, SLT)
        instruction = spike.decode_instruction(BASE, word)

        self.assertEqual(word >> 26, 0)
        self.assertEqual((word >> 6) & 0x1F, 0)
        self.assertEqual(word & 0x3F, SLT)
        self.assertEqual(instruction["op"], "slt")
        self.assertEqual((instruction["rs"], instruction["rt"], instruction["rd"]), (T0, T1, T2))

    def test_decode_rejects_nonzero_shamt(self):
        with self.assertRaisesRegex(ValueError, "Unsupported SPECIAL"):
            spike.decode_instruction(BASE, spike.encode_r(T0, T1, T2, 1, SLT))

    def test_decode_rejects_unsupported_special_function_and_opcode(self):
        with self.assertRaisesRegex(ValueError, "Unsupported SPECIAL"):
            spike.decode_instruction(BASE, spike.encode_r(T0, T1, T2, 0, UNSUPPORTED_SPECIAL))
        with self.assertRaisesRegex(ValueError, "Unsupported opcode 0x10"):
            spike.decode_instruction(BASE, spike.encode_i(0x10, T0, T1, 0))


class SltIrTests(unittest.TestCase):
    def test_ir_marks_slt_operands_destinations_and_fallthrough(self):
        words = {
            BASE: spike.encode_r(T0, T1, T2, 0, SLT),
            BASE + 4: spike.encode_r(S0, S1, ZERO, 0, SLT),
        }
        result = ir.analyze_words(BASE, words)
        by_pc = {instruction.pc: instruction for instruction in result.instructions}

        instruction = by_pc[BASE]
        self.assertEqual(instruction.op, "slt")
        self.assertEqual(instruction.word, words[BASE])
        self.assertEqual((instruction.rs, instruction.rt, instruction.rd), (T0, T1, T2))
        self.assertEqual(instruction.destination_register, T2)
        self.assertEqual(instruction.control, ir.FALLTHROUGH)
        self.assertIsNone(instruction.immediate)
        self.assertIsNone(instruction.immediate_kind)
        self.assertIsNone(instruction.target)

        zero_destination = by_pc[BASE + 4]
        self.assertEqual(zero_destination.op, "slt")
        self.assertIsNone(zero_destination.destination_register)

    def test_ir_rejects_nonzero_shamt_fail_closed(self):
        with self.assertRaises(ir.AnalysisError) as caught:
            ir.analyze_words(BASE, {BASE: spike.encode_r(T0, T1, T2, 1, SLT)})

        self.assertEqual(caught.exception.code, ir.IR_UNSUPPORTED_INSTRUCTION)
        self.assertIn("Unsupported SPECIAL", str(caught.exception))


class SltOracleTests(unittest.TestCase):
    def test_oracle_compares_signed_register_values_deterministically(self):
        data, _ = slt_fixture()
        entry, words, info = spike.parse_elf(data)
        first = spike.normalize_state(spike.execute_oracle(entry, words))
        second = spike.normalize_state(spike.execute_oracle(entry, words))
        registers = first["registers"]

        self.assertEqual(info["instruction_count"], 20)
        self.assertEqual(first, second)
        self.assertEqual(registers[ZERO], 0)
        self.assertEqual(registers[T0], UINT64_MASK)
        self.assertEqual(registers[T1], 0)
        self.assertEqual(registers[T2], 1)
        self.assertEqual(registers[T3], 1)
        self.assertEqual(registers[T4], 0)
        self.assertEqual(registers[S0], 0)
        self.assertEqual(registers[S1], 5)
        self.assertEqual(registers[S2], 0)
        self.assertEqual(registers[T5], 1)
        self.assertEqual(registers[S3], 1)
        self.assertEqual(registers[S4], 0x000000007FFF0000)
        self.assertEqual(registers[S5], 0xFFFFFFFF80000000)
        self.assertEqual(registers[S6], 1)
        self.assertEqual(registers[S7], 0)
        self.assertEqual(registers[V0], 42)
        self.assertEqual(first["memory"], [])
        self.assertEqual(first["pc"], spike.RETURN_SENTINEL)
        self.assertTrue(first["halted"])
        self.assertEqual(first["trace"], [BASE + index * 4 for index in range(20)])

    def test_slt_helper_handles_signed_64_bit_boundaries(self):
        cases = (
            (INT64_MIN, INT64_MAX, 1),
            (INT64_MAX, INT64_MIN, 0),
            (INT64_MIN, INT64_MIN, 0),
            (INT64_MAX, INT64_MAX, 0),
            (UINT64_MASK, 0, 1),
            (0, UINT64_MASK, 0),
        )
        for lhs, rhs, expected in cases:
            with self.subTest(lhs=lhs, rhs=rhs):
                self.assertEqual(spike.slt64(lhs, rhs), expected)


class SltLoweringTests(unittest.TestCase):
    def test_slt_native_state_matches_oracle(self):
        candidate = compiler_available()
        if candidate is None:
            self.skipTest("No C++ compiler available for the SLT native differential")

        data, result = slt_fixture()
        entry, words, _ = spike.parse_elf(data)
        oracle = spike.normalize_state(spike.execute_oracle(entry, words))
        source_text = lower.lower_to_cpp(result)

        with tempfile.TemporaryDirectory() as temp:
            out_dir = Path(temp)
            source = out_dir / "generated.cpp"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            exe = out_dir / ("rptp-slt.exe" if os.name == "nt" else "rptp-slt")
            command = spike.compile_generated(source, exe, "auto")
            proc = subprocess.run([str(exe)], cwd=out_dir, text=True, capture_output=True, check=False)

        self.assertEqual(proc.returncode, 0, msg=f"{command}\n{proc.stdout}\n{proc.stderr}")
        self.assertEqual(proc.stderr, "")
        native = json.loads(proc.stdout)
        self.assertEqual(native, oracle)
        self.assertEqual(native["registers"][T2], 1)
        self.assertEqual(native["registers"][T4], 0)
        self.assertEqual(native["registers"][S6], 1)
        self.assertEqual(native["registers"][S7], 0)
        self.assertEqual(native["memory"], [])
        self.assertEqual(native["pc"], spike.RETURN_SENTINEL)
        self.assertTrue(native["halted"])
        self.assertEqual(native["trace"], oracle["trace"])

    def test_slt_native_helper_handles_signed_64_bit_boundaries(self):
        candidate = compiler_available()
        if candidate is None:
            self.skipTest("No C++ compiler available for the SLT boundary differential")

        result = ir.analyze_words(BASE, {BASE: spike.encode_r(T0, T1, T2, 0, SLT)})
        source_text = lower.lower_to_cpp(result)
        harness_text = f'''#define main rptp_generated_entry
#include "generated.cpp"
#undef main

int main() {{
    State min_vs_max;
    min_vs_max.pc = 0x{BASE:08X}u;
    min_vs_max.registers[{T0}] = 0x{INT64_MIN:016X}ull;
    min_vs_max.registers[{T1}] = 0x{INT64_MAX:016X}ull;
    run_generated(min_vs_max);

    State max_vs_min;
    max_vs_min.pc = 0x{BASE:08X}u;
    max_vs_min.registers[{T0}] = 0x{INT64_MAX:016X}ull;
    max_vs_min.registers[{T1}] = 0x{INT64_MIN:016X}ull;
    run_generated(max_vs_min);

    State min_vs_min;
    min_vs_min.pc = 0x{BASE:08X}u;
    min_vs_min.registers[{T0}] = 0x{INT64_MIN:016X}ull;
    min_vs_min.registers[{T1}] = 0x{INT64_MIN:016X}ull;
    run_generated(min_vs_min);

    std::cout << min_vs_max.registers[{T2}] << ' '
              << max_vs_min.registers[{T2}] << ' '
              << min_vs_min.registers[{T2}] << ' '
              << max_vs_min.registers[0] << ' '
              << (max_vs_min.halted ? 1 : 0) << ' '
              << (max_vs_min.pc - 0x{BASE:08X}u) << ' '
              << max_vs_min.trace.size() << '\\n';
    return 0;
}}
'''

        with tempfile.TemporaryDirectory() as temp:
            out_dir = Path(temp)
            source = out_dir / "generated.cpp"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            harness = out_dir / "harness.cpp"
            harness.write_text(harness_text, encoding="utf-8", newline="\n")
            exe = out_dir / ("rptp-slt-boundary.exe" if os.name == "nt" else "rptp-slt-boundary")
            command = spike.compile_generated(harness, exe, "auto")
            proc = subprocess.run([str(exe)], cwd=out_dir, text=True, capture_output=True, check=False)

        self.assertEqual(proc.returncode, 0, msg=f"{command}\n{proc.stdout}\n{proc.stderr}")
        self.assertEqual(proc.stderr, "")
        self.assertEqual(proc.stdout.split(), ["1", "0", "0", "0", "1", "4", "1"])

    def test_slt_lowering_is_deterministic_and_ignores_raw_words(self):
        _, result = slt_fixture()
        source = lower.lower_to_cpp(result)
        changed_words = replace(
            result,
            instructions=tuple(replace(instruction, word=0) for instruction in result.instructions),
        )

        self.assertEqual(source, lower.lower_to_cpp(result))
        self.assertEqual(source, lower.lower_to_cpp(changed_words))
        self.assertNotIn("\r", source)
        self.assertTrue(source.endswith("\n"))

    def test_slt_lowering_rejects_malformed_metadata(self):
        _, result = slt_fixture()
        cases = {
            "missing_rs": ({"rs": None}, lower.LOWER_MALFORMED_INSTRUCTION),
            "missing_rt": ({"rt": None}, lower.LOWER_MALFORMED_INSTRUCTION),
            "missing_rd": ({"rd": None}, lower.LOWER_MALFORMED_INSTRUCTION),
            "wrong_destination": ({"destination_register": None}, lower.LOWER_MALFORMED_INSTRUCTION),
            "unexpected_immediate": (
                {"immediate": 0, "immediate_kind": ir.ZERO16},
                lower.LOWER_MALFORMED_INSTRUCTION,
            ),
            "wrong_control": ({"control": ir.DIRECT_JUMP}, lower.LOWER_INVALID_CONTROL),
        }
        for name, (fields, expected_code) in cases.items():
            with self.subTest(name=name):
                malformed = replace_instruction(result, BASE + 8, **fields)
                with self.assertRaises(lower.LoweringError) as caught:
                    lower.lower_to_cpp(malformed)
                self.assertEqual(caught.exception.code, expected_code)

    def test_slt_lowering_rejects_unsupported_operation(self):
        _, result = slt_fixture()
        malformed = replace_instruction(result, BASE + 8, op="dadd")

        with self.assertRaises(lower.LoweringError) as caught:
            lower.lower_to_cpp(malformed)
        self.assertEqual(caught.exception.code, lower.LOWER_UNSUPPORTED_OP)


if __name__ == "__main__":
    unittest.main(verbosity=2)
