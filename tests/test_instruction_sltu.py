# SPDX-License-Identifier: GPL-3.0-or-later
"""Focused synthetic tests for the SLTU unsigned comparison operation."""
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


spike = load_module("rptp_gate0_spike_sltu", "tools/rptp_gate0_spike.py")
ir = load_module("rptp_ir_sltu", "tools/rptp_ir.py")
lower = load_module("rptp_lower_sltu", "tools/rptp_lower.py")

BASE = spike.BASE
ZERO = spike.ZERO
V0 = spike.V0
V1 = spike.V1
T0 = spike.T0
T1 = spike.T1
T2 = spike.T2
T3 = spike.T3
T4 = spike.T4
T5 = 13
T6 = 14
S0 = spike.S0
S1 = spike.S1
S2 = spike.S2
S3 = spike.S3
S4 = spike.S4
S5 = 21
S6 = 22
S7 = spike.S7
RA = spike.RA

SLTU = 0x2B
UNSUPPORTED_SPECIAL = 0x2C

INT64_MIN = 0x8000000000000000
INT64_MAX = 0x7FFFFFFFFFFFFFFF
UINT64_MAX = 0xFFFFFFFFFFFFFFFF
SIGN_EXTENDED_HIGH = 0xFFFFFFFF80000000


def nop_word() -> int:
    return spike.encode_r(ZERO, ZERO, ZERO, 0, 0x00)


def jr_ra_word() -> int:
    return spike.encode_r(RA, ZERO, ZERO, 0, 0x08)


def sltu_fixture_rows() -> list[tuple[int, str, int]]:
    rows = [
        ("set_zero", spike.encode_i(0x09, ZERO, T0, 0)),
        ("set_one", spike.encode_i(0x09, ZERO, T1, 1)),
        ("set_all_ones", spike.encode_i(0x09, ZERO, T2, -1)),
        ("set_high_bit_63", spike.encode_i(0x0F, ZERO, T3, 0x8000)),
        ("set_low_31_max_high", spike.encode_i(0x0F, ZERO, T4, 0x7FFF)),
        ("set_low_31_max", spike.encode_i(0x0D, T4, T4, 0xFFFF)),
        ("set_high_bit_63_copy", spike.encode_i(0x0F, ZERO, T5, 0x8000)),
        ("set_bit_31", spike.encode_i(0x0D, T5, T5, 0)),
        ("sltu_zero_less_one", spike.encode_r(T0, T1, S0, 0, SLTU)),
        ("sltu_one_less_zero", spike.encode_r(T1, T0, S1, 0, SLTU)),
        ("sltu_equal_zero", spike.encode_r(T0, T0, S2, 0, SLTU)),
        ("sltu_all_ones_less_zero", spike.encode_r(T2, T0, S3, 0, SLTU)),
        ("sltu_zero_less_all_ones", spike.encode_r(T0, T2, S4, 0, SLTU)),
        ("sltu_bit_31_less_low_31_max", spike.encode_r(T5, T4, S5, 0, SLTU)),
        ("sltu_low_31_max_less_bit_31", spike.encode_r(T4, T5, S6, 0, SLTU)),
        ("sltu_bit_63_less_low_31_max", spike.encode_r(T3, T4, S7, 0, SLTU)),
        ("sltu_low_31_max_less_bit_63", spike.encode_r(T4, T3, V1, 0, SLTU)),
        ("sltu_destination_aliases_first_source", spike.encode_r(T1, T0, T1, 0, SLTU)),
        ("sltu_destination_aliases_second_source", spike.encode_r(T0, T2, T2, 0, SLTU)),
        ("set_same_register_value", spike.encode_i(0x09, ZERO, T6, 5)),
        ("sltu_same_register_equal", spike.encode_r(T6, T6, T6, 0, SLTU)),
        ("sltu_zero_destination", spike.encode_r(T0, T2, ZERO, 0, SLTU)),
        ("sltu_zero_source", spike.encode_r(ZERO, T2, T6, 0, SLTU)),
        ("return_value", spike.encode_i(0x09, ZERO, V0, 42)),
        ("return_from_main", jr_ra_word()),
        ("main_return_delay_slot", nop_word()),
    ]
    return [(BASE + index * 4, name, word) for index, (name, word) in enumerate(rows)]


def sltu_fixture():
    data = spike.build_elf_from_rows(sltu_fixture_rows())
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


class SltuDecodeTests(unittest.TestCase):
    def test_decode_sltu_encoding(self):
        word = spike.encode_r(T0, T1, T2, 0, SLTU)
        instruction = spike.decode_instruction(BASE, word)

        self.assertEqual(word >> 26, 0)
        self.assertEqual((word >> 6) & 0x1F, 0)
        self.assertEqual(word & 0x3F, SLTU)
        self.assertEqual(instruction["op"], "sltu")
        self.assertEqual((instruction["rs"], instruction["rt"], instruction["rd"]), (T0, T1, T2))

    def test_decode_rejects_nonzero_shamt(self):
        with self.assertRaisesRegex(ValueError, "Unsupported SPECIAL"):
            spike.decode_instruction(BASE, spike.encode_r(T0, T1, T2, 1, SLTU))

    def test_decode_rejects_unsupported_special_function_and_opcode(self):
        with self.assertRaisesRegex(ValueError, "Unsupported SPECIAL"):
            spike.decode_instruction(BASE, spike.encode_r(T0, T1, T2, 0, UNSUPPORTED_SPECIAL))
        with self.assertRaisesRegex(ValueError, "Unsupported opcode 0x10"):
            spike.decode_instruction(BASE, spike.encode_i(0x10, T0, T1, 0))


class SltuIrTests(unittest.TestCase):
    def test_ir_marks_sltu_operands_destinations_and_fallthrough(self):
        words = {
            BASE: spike.encode_r(T0, T1, T2, 0, SLTU),
            BASE + 4: spike.encode_r(S0, S1, ZERO, 0, SLTU),
        }
        result = ir.analyze_words(BASE, words)
        by_pc = {instruction.pc: instruction for instruction in result.instructions}

        instruction = by_pc[BASE]
        self.assertEqual(instruction.op, "sltu")
        self.assertEqual(instruction.word, words[BASE])
        self.assertEqual((instruction.rs, instruction.rt, instruction.rd), (T0, T1, T2))
        self.assertEqual(instruction.destination_register, T2)
        self.assertEqual(instruction.control, ir.FALLTHROUGH)
        self.assertIsNone(instruction.immediate)
        self.assertIsNone(instruction.immediate_kind)
        self.assertIsNone(instruction.target)

        zero_destination = by_pc[BASE + 4]
        self.assertEqual(zero_destination.op, "sltu")
        self.assertIsNone(zero_destination.destination_register)

    def test_ir_rejects_nonzero_shamt_fail_closed(self):
        with self.assertRaises(ir.AnalysisError) as caught:
            ir.analyze_words(BASE, {BASE: spike.encode_r(T0, T1, T2, 1, SLTU)})

        self.assertEqual(caught.exception.code, ir.IR_UNSUPPORTED_INSTRUCTION)
        self.assertIn("Unsupported SPECIAL", str(caught.exception))


class SltuOracleTests(unittest.TestCase):
    def test_oracle_compares_unsigned_register_values_deterministically(self):
        data, _ = sltu_fixture()
        entry, words, info = spike.parse_elf(data)
        first = spike.normalize_state(spike.execute_oracle(entry, words))
        second = spike.normalize_state(spike.execute_oracle(entry, words))
        registers = first["registers"]

        self.assertEqual(data, spike.build_elf_from_rows(sltu_fixture_rows()))
        self.assertEqual(info["instruction_count"], 26)
        self.assertEqual(first, second)
        self.assertEqual(registers[ZERO], 0)
        self.assertEqual(registers[T0], 0)
        self.assertEqual(registers[T1], 0)
        self.assertEqual(registers[T2], 1)
        self.assertEqual(registers[T3], SIGN_EXTENDED_HIGH)
        self.assertEqual(registers[T4], 0x000000007FFFFFFF)
        self.assertEqual(registers[T5], 0x0000000080000000)
        self.assertEqual(registers[T6], 1)
        self.assertEqual(registers[S0], 1)
        self.assertEqual(registers[S1], 0)
        self.assertEqual(registers[S2], 0)
        self.assertEqual(registers[S3], 0)
        self.assertEqual(registers[S4], 1)
        self.assertEqual(registers[S5], 0)
        self.assertEqual(registers[S6], 1)
        self.assertEqual(registers[S7], 0)
        self.assertEqual(registers[V1], 1)
        self.assertEqual(registers[V0], 42)
        self.assertEqual(first["memory"], [])
        self.assertEqual(first["pc"], spike.RETURN_SENTINEL)
        self.assertTrue(first["halted"])
        self.assertEqual(first["trace"], [BASE + index * 4 for index in range(26)])

    def test_sltu_helper_handles_unsigned_64_bit_boundaries(self):
        cases = (
            (0, 0, 0),
            (0, 1, 1),
            (1, 0, 0),
            (UINT64_MAX, 0, 0),
            (0, UINT64_MAX, 1),
            (INT64_MIN, INT64_MAX, 0),
            (INT64_MAX, INT64_MIN, 1),
            (INT64_MIN, INT64_MIN, 0),
            (0x0000000080000000, 0x000000007FFFFFFF, 0),
            (0x000000007FFFFFFF, 0x0000000080000000, 1),
            (UINT64_MAX, UINT64_MAX, 0),
            (1, UINT64_MAX, 1),
            (UINT64_MAX, 1, 0),
        )
        for lhs, rhs, expected in cases:
            with self.subTest(lhs=lhs, rhs=rhs):
                self.assertEqual(spike.sltu64(lhs, rhs), expected)


class SltuLoweringTests(unittest.TestCase):
    def test_sltu_native_state_matches_oracle(self):
        candidate = compiler_available()
        if candidate is None:
            self.skipTest("No C++ compiler available for the SLTU native differential")

        data, result = sltu_fixture()
        entry, words, _ = spike.parse_elf(data)
        oracle = spike.normalize_state(spike.execute_oracle(entry, words))
        source_text = lower.lower_to_cpp(result)

        with tempfile.TemporaryDirectory() as temp:
            out_dir = Path(temp)
            source = out_dir / "generated.cpp"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            exe = out_dir / ("rptp-sltu.exe" if os.name == "nt" else "rptp-sltu")
            command = spike.compile_generated(source, exe, "auto")
            proc = subprocess.run([str(exe)], cwd=out_dir, text=True, capture_output=True, check=False)

        self.assertEqual(proc.returncode, 0, msg=f"{command}\n{proc.stdout}\n{proc.stderr}")
        self.assertEqual(proc.stderr, "")
        native = json.loads(proc.stdout)
        self.assertEqual(native, oracle)
        self.assertEqual(native["registers"][S0], 1)
        self.assertEqual(native["registers"][S1], 0)
        self.assertEqual(native["registers"][S5], 0)
        self.assertEqual(native["registers"][S6], 1)
        self.assertEqual(native["registers"][S7], 0)
        self.assertEqual(native["registers"][V1], 1)
        self.assertEqual(native["memory"], [])
        self.assertEqual(native["pc"], spike.RETURN_SENTINEL)
        self.assertTrue(native["halted"])
        self.assertEqual(native["trace"], oracle["trace"])

    def test_sltu_native_helper_handles_unsigned_64_bit_boundaries(self):
        candidate = compiler_available()
        if candidate is None:
            self.skipTest("No C++ compiler available for the SLTU boundary differential")

        result = ir.analyze_words(BASE, {BASE: spike.encode_r(T0, T1, T2, 0, SLTU)})
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

    State equal_high;
    equal_high.pc = 0x{BASE:08X}u;
    equal_high.registers[{T0}] = 0x{INT64_MIN:016X}ull;
    equal_high.registers[{T1}] = 0x{INT64_MIN:016X}ull;
    run_generated(equal_high);

    State bit_31_vs_low_31_max;
    bit_31_vs_low_31_max.pc = 0x{BASE:08X}u;
    bit_31_vs_low_31_max.registers[{T0}] = 0x0000000080000000ull;
    bit_31_vs_low_31_max.registers[{T1}] = 0x000000007FFFFFFFull;
    run_generated(bit_31_vs_low_31_max);

    State low_31_max_vs_bit_31;
    low_31_max_vs_bit_31.pc = 0x{BASE:08X}u;
    low_31_max_vs_bit_31.registers[{T0}] = 0x000000007FFFFFFFull;
    low_31_max_vs_bit_31.registers[{T1}] = 0x0000000080000000ull;
    run_generated(low_31_max_vs_bit_31);

    std::cout << min_vs_max.registers[{T2}] << ' '
              << max_vs_min.registers[{T2}] << ' '
              << equal_high.registers[{T2}] << ' '
              << bit_31_vs_low_31_max.registers[{T2}] << ' '
              << low_31_max_vs_bit_31.registers[{T2}] << ' '
              << low_31_max_vs_bit_31.registers[0] << ' '
              << (low_31_max_vs_bit_31.halted ? 1 : 0) << ' '
              << (low_31_max_vs_bit_31.pc - 0x{BASE:08X}u) << ' '
              << low_31_max_vs_bit_31.trace.size() << '\\n';
    return 0;
}}
'''

        with tempfile.TemporaryDirectory() as temp:
            out_dir = Path(temp)
            source = out_dir / "generated.cpp"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            harness = out_dir / "harness.cpp"
            harness.write_text(harness_text, encoding="utf-8", newline="\n")
            exe = out_dir / ("rptp-sltu-boundary.exe" if os.name == "nt" else "rptp-sltu-boundary")
            command = spike.compile_generated(harness, exe, "auto")
            proc = subprocess.run([str(exe)], cwd=out_dir, text=True, capture_output=True, check=False)

        self.assertEqual(proc.returncode, 0, msg=f"{command}\n{proc.stdout}\n{proc.stderr}")
        self.assertEqual(proc.stderr, "")
        self.assertEqual(proc.stdout.split(), ["0", "1", "0", "0", "1", "0", "1", "4", "1"])

    def test_sltu_lowering_is_deterministic_and_ignores_raw_words(self):
        _, result = sltu_fixture()
        source = lower.lower_to_cpp(result)
        changed_words = replace(
            result,
            instructions=tuple(replace(instruction, word=0) for instruction in result.instructions),
        )

        self.assertEqual(source, lower.lower_to_cpp(result))
        self.assertEqual(source, lower.lower_to_cpp(changed_words))
        self.assertNotIn("\r", source)
        self.assertTrue(source.endswith("\n"))
        self.assertIn("sltu64(", source)

    def test_sltu_lowering_rejects_malformed_metadata(self):
        _, result = sltu_fixture()
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
                malformed = replace_instruction(result, BASE + 0x20, **fields)
                with self.assertRaises(lower.LoweringError) as caught:
                    lower.lower_to_cpp(malformed)
                self.assertEqual(caught.exception.code, expected_code)

    def test_sltu_lowering_rejects_unsupported_operation(self):
        _, result = sltu_fixture()
        malformed = replace_instruction(result, BASE + 0x20, op="dadd")

        with self.assertRaises(lower.LoweringError) as caught:
            lower.lower_to_cpp(malformed)
        self.assertEqual(caught.exception.code, lower.LOWER_UNSUPPORTED_OP)


if __name__ == "__main__":
    unittest.main(verbosity=2)
