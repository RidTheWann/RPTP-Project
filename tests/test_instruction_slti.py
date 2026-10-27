# SPDX-License-Identifier: GPL-3.0-or-later
"""Synthetic SLTI signed-immediate tests for decoder, IR, oracle and native lowering."""
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


spike = load_module("rptp_gate0_spike_slti", "tools/rptp_gate0_spike.py")
ir = load_module("rptp_ir_slti", "tools/rptp_ir.py")
lower = load_module("rptp_lower_slti", "tools/rptp_lower.py")

BASE = spike.BASE
ZERO = spike.ZERO
V0 = spike.V0
V1 = spike.V1
T0, T1, T2, T3, T4 = 8, 9, 10, 11, 12
T5, T6 = 13, 14
S0, S1, S2, S3, S4, S5, S6, S7 = 16, 17, 18, 19, 20, 21, 22, 23
RA = spike.RA
SLTI = 0x0A
INT64_MIN = 0x8000000000000000
INT64_MAX = 0x7FFFFFFFFFFFFFFF


def nop_word() -> int:
    return spike.encode_r(ZERO, ZERO, ZERO, 0, 0)


def jr_ra_word() -> int:
    return spike.encode_r(RA, ZERO, ZERO, 0, 0x08)


def slti_fixture_rows() -> list[tuple[int, str, int]]:
    rows = [
        ("set_zero", spike.encode_i(0x09, ZERO, T0, 0)),
        ("zero_less_one", spike.encode_i(SLTI, T0, S0, 1)),
        ("zero_less_zero", spike.encode_i(SLTI, T0, S1, 0)),
        ("set_one", spike.encode_i(0x09, ZERO, T0, 1)),
        ("equal_one", spike.encode_i(SLTI, T0, S2, 1)),
        ("one_less_two", spike.encode_i(SLTI, T0, S3, 2)),
        ("set_negative_one", spike.encode_i(0x09, ZERO, T0, -1)),
        ("negative_one_less_zero", spike.encode_i(SLTI, T0, S4, 0)),
        ("negative_one_less_negative_one", spike.encode_i(SLTI, T0, S5, -1)),
        ("negative_one_less_negative_two", spike.encode_i(SLTI, T0, S6, -2)),
        ("negative_one_less_positive_max", spike.encode_i(SLTI, T0, S7, 32767)),
        ("reset_one", spike.encode_i(0x09, ZERO, T0, 1)),
        ("one_less_negative_one", spike.encode_i(SLTI, T0, T5, -1)),
        ("one_less_positive_max", spike.encode_i(SLTI, T0, T6, 32767)),
        ("zero_source", spike.encode_i(SLTI, ZERO, V1, 1)),
        ("zero_destination", spike.encode_i(SLTI, T0, ZERO, -1)),
        ("source_destination_alias", spike.encode_i(SLTI, T0, T0, 2)),
        ("set_negative_high", spike.encode_i(0x0F, ZERO, T3, 0x8000)),
        ("negative_high_less_positive_max", spike.encode_i(SLTI, T3, T2, 32767)),
        ("set_positive_high", spike.encode_i(0x0F, ZERO, T3, 0x7FFF)),
        ("positive_high_less_positive_max", spike.encode_i(SLTI, T3, T4, 32767)),
        ("return_value", spike.encode_i(0x09, ZERO, V0, 42)),
        ("return_from_main", jr_ra_word()),
        ("return_delay_slot", nop_word()),
    ]
    return [(BASE + index * 4, name, word) for index, (name, word) in enumerate(rows)]


def slti_fixture():
    data = spike.build_elf_from_rows(slti_fixture_rows())
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


class SltiDecodeTests(unittest.TestCase):
    def test_decode_slti_and_sign_extends_immediate(self):
        instruction = spike.decode_instruction(BASE, spike.encode_i(SLTI, T0, T1, -32768))
        self.assertEqual(instruction["op"], "slti")
        self.assertEqual((instruction["rs"], instruction["rt"]), (T0, T1))
        self.assertEqual(instruction["imm"], -32768)

    def test_sltiu_remains_unsupported(self):
        with self.assertRaisesRegex(ValueError, "Unsupported opcode 0x0B"):
            spike.decode_instruction(BASE, spike.encode_i(0x0B, T0, T1, 1))


class SltiIrTests(unittest.TestCase):
    def test_ir_records_signed_immediate_and_rt_destination(self):
        result = ir.analyze_words(BASE, {BASE: spike.encode_i(SLTI, T0, T1, -1)})
        instruction = result.instructions[0]
        self.assertEqual(instruction.op, "slti")
        self.assertEqual((instruction.rs, instruction.rt), (T0, T1))
        self.assertEqual(instruction.immediate, -1)
        self.assertEqual(instruction.immediate_kind, ir.SIGNED16)
        self.assertEqual(instruction.destination_register, T1)
        self.assertEqual(instruction.control, ir.FALLTHROUGH)

    def test_ir_rejects_out_of_scope_instruction_fail_closed(self):
        with self.assertRaises(ir.AnalysisError) as caught:
            ir.analyze_words(BASE, {BASE: spike.encode_i(0x0B, T0, T1, 1)})
        self.assertEqual(caught.exception.code, ir.IR_UNSUPPORTED_INSTRUCTION)


class SltiOracleTests(unittest.TestCase):
    def test_oracle_matches_literal_signed_comparison_cases(self):
        data, _ = slti_fixture()
        entry, words, info = spike.parse_elf(data)
        state = spike.normalize_state(spike.execute_oracle(entry, words))
        registers = state["registers"]
        self.assertEqual(info["instruction_count"], 24)
        self.assertEqual(registers[ZERO], 0)
        self.assertEqual(registers[S0], 1)
        self.assertEqual(registers[S1], 0)
        self.assertEqual(registers[S2], 0)
        self.assertEqual(registers[S3], 1)
        self.assertEqual(registers[S4], 1)
        self.assertEqual(registers[S5], 0)
        self.assertEqual(registers[S6], 0)
        self.assertEqual(registers[S7], 1)
        self.assertEqual(registers[T5], 0)
        self.assertEqual(registers[T6], 1)
        self.assertEqual(registers[T2], 1)
        self.assertEqual(registers[T4], 0)
        self.assertEqual(registers[T0], 1)
        self.assertEqual(registers[V1], 1)
        self.assertEqual(registers[V0], 42)
        self.assertEqual(state["memory"], [])
        self.assertEqual(state["pc"], spike.RETURN_SENTINEL)
        self.assertEqual(state["trace"], [BASE + index * 4 for index in range(24)])

    def test_oracle_helper_signed_64_bit_boundaries(self):
        cases = (
            (INT64_MIN, -32768, 1),
            (INT64_MIN, 32767, 1),
            (INT64_MAX, -32768, 0),
            (0xFFFFFFFFFFFF7FFF, -32768, 1),
            (0xFFFFFFFFFFFF8000, -32768, 0),
            (0xFFFFFFFFFFFFFFFF, -1, 0),
        )
        for lhs, rhs, expected in cases:
            with self.subTest(lhs=f"0x{lhs:016X}", rhs=rhs):
                self.assertEqual(spike.slt64(lhs, rhs), expected)


class SltiLoweringTests(unittest.TestCase):
    def test_slti_native_state_matches_oracle_and_literal_results(self):
        if compiler_available() is None:
            self.skipTest("No C++ compiler available for the SLTI native differential")
        data, result = slti_fixture()
        entry, words, _ = spike.parse_elf(data)
        oracle = spike.normalize_state(spike.execute_oracle(entry, words))
        source_text = lower.lower_to_cpp(result)
        with tempfile.TemporaryDirectory() as temp:
            out_dir = Path(temp)
            source = out_dir / "generated.cpp"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            exe = out_dir / ("rptp-slti.exe" if os.name == "nt" else "rptp-slti")
            command = spike.compile_generated(source, exe, "auto")
            proc = subprocess.run([str(exe)], cwd=out_dir, text=True, capture_output=True, check=False)
        self.assertEqual(proc.returncode, 0, msg=f"{command}\n{proc.stdout}\n{proc.stderr}")
        self.assertEqual(proc.stderr, "")
        native = json.loads(proc.stdout)
        self.assertEqual(native, oracle)
        self.assertEqual(native["registers"][S0], 1)
        self.assertEqual(native["registers"][S6], 0)
        self.assertEqual(native["registers"][T5], 0)
        self.assertEqual(native["registers"][T6], 1)
        self.assertEqual(native["registers"][T2], 1)
        self.assertEqual(native["registers"][T4], 0)
        self.assertEqual(native["registers"][V1], 1)
        self.assertEqual(native["registers"][ZERO], 0)

    def test_slti_native_helper_handles_64_bit_and_immediate_boundaries(self):
        if compiler_available() is None:
            self.skipTest("No C++ compiler available for the SLTI boundary differential")
        result = ir.analyze_words(BASE, {BASE: spike.encode_i(SLTI, T0, T1, -32768)})
        source_text = lower.lower_to_cpp(result)
        harness_text = f'''#define main rptp_generated_entry
#include "generated.cpp"
#undef main

int main() {{
    State min_vs_min;
    min_vs_min.pc = 0x{BASE:08X}u;
    min_vs_min.registers[{T0}] = 0x{INT64_MIN:016X}ull;
    run_generated(min_vs_min);

    State max_vs_min;
    max_vs_min.pc = 0x{BASE:08X}u;
    max_vs_min.registers[{T0}] = 0x{INT64_MAX:016X}ull;
    run_generated(max_vs_min);

    State min32_vs_min_immediate;
    min32_vs_min_immediate.pc = 0x{BASE:08X}u;
    min32_vs_min_immediate.registers[{T0}] = 0xFFFFFFFF80000000ull;
    run_generated(min32_vs_min_immediate);

    State below_min_immediate;
    below_min_immediate.pc = 0x{BASE:08X}u;
    below_min_immediate.registers[{T0}] = 0xFFFFFFFFFFFF7FFFull;
    run_generated(below_min_immediate);

    State equal_min_immediate;
    equal_min_immediate.pc = 0x{BASE:08X}u;
    equal_min_immediate.registers[{T0}] = 0xFFFFFFFFFFFF8000ull;
    run_generated(equal_min_immediate);

    std::cout << min_vs_min.registers[{T1}] << ' '
              << max_vs_min.registers[{T1}] << ' '
              << min32_vs_min_immediate.registers[{T1}] << ' '
              << below_min_immediate.registers[{T1}] << ' '
              << equal_min_immediate.registers[{T1}] << '\\n';
    return 0;
}}
'''
        with tempfile.TemporaryDirectory() as temp:
            out_dir = Path(temp)
            source = out_dir / "generated.cpp"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            harness = out_dir / "harness.cpp"
            harness.write_text(harness_text, encoding="utf-8", newline="\n")
            exe = out_dir / ("rptp-slti-boundary.exe" if os.name == "nt" else "rptp-slti-boundary")
            command = spike.compile_generated(harness, exe, "auto")
            proc = subprocess.run([str(exe)], cwd=out_dir, text=True, capture_output=True, check=False)
        self.assertEqual(proc.returncode, 0, msg=f"{command}\n{proc.stdout}\n{proc.stderr}")
        self.assertEqual(proc.stderr, "")
        self.assertEqual(proc.stdout.split(), ["1", "0", "1", "1", "0"])

    def test_slti_lowering_is_deterministic_and_ignores_raw_words(self):
        _, result = slti_fixture()
        source = lower.lower_to_cpp(result)
        changed_words = replace(
            result,
            instructions=tuple(replace(instruction, word=0) for instruction in result.instructions),
        )
        self.assertEqual(source, lower.lower_to_cpp(result))
        self.assertEqual(source, lower.lower_to_cpp(changed_words))
        self.assertIn("slt64(", source)
        boundary_source = lower.lower_to_cpp(
            ir.analyze_words(BASE, {BASE: spike.encode_i(SLTI, T0, T1, -32768)})
        )
        self.assertIn("static_cast<std::int64_t>(-32768)", boundary_source)
        self.assertNotIn("\r", source)
        self.assertTrue(source.endswith("\n"))

    def test_slti_lowering_rejects_malformed_metadata(self):
        _, result = slti_fixture()
        pc = BASE + 4
        cases = {
            "missing_rs": ({"rs": None}, lower.LOWER_MALFORMED_INSTRUCTION),
            "missing_rt": ({"rt": None}, lower.LOWER_MALFORMED_INSTRUCTION),
            "wrong_destination": ({"destination_register": None}, lower.LOWER_MALFORMED_INSTRUCTION),
            "wrong_immediate_kind": ({"immediate_kind": ir.ZERO16}, lower.LOWER_MALFORMED_INSTRUCTION),
            "out_of_range_immediate": ({"immediate": 32768}, lower.LOWER_MALFORMED_INSTRUCTION),
            "unexpected_rd": ({"rd": T2}, lower.LOWER_MALFORMED_INSTRUCTION),
        }
        for name, (fields, expected_code) in cases.items():
            with self.subTest(name=name):
                malformed = replace_instruction(result, pc, **fields)
                with self.assertRaises(lower.LoweringError) as caught:
                    lower.lower_to_cpp(malformed)
                self.assertEqual(caught.exception.code, expected_code)

    def test_slti_lowering_rejects_unsupported_operation(self):
        _, result = slti_fixture()
        malformed = replace_instruction(result, BASE + 4, op="sltiu")
        with self.assertRaises(lower.LoweringError) as caught:
            lower.lower_to_cpp(malformed)
        self.assertEqual(caught.exception.code, lower.LOWER_UNSUPPORTED_OP)


if __name__ == "__main__":
    unittest.main(verbosity=2)
