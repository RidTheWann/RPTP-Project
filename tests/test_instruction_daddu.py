# SPDX-License-Identifier: GPL-3.0-or-later
"""Synthetic DADDU tests for full 64-bit unsigned addition."""
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


spike = load_module("rptp_gate0_spike_daddu", "tools/rptp_gate0_spike.py")
ir = load_module("rptp_ir_daddu", "tools/rptp_ir.py")
lower = load_module("rptp_lower_daddu", "tools/rptp_lower.py")

BASE = spike.BASE
ZERO, V0 = spike.ZERO, spike.V0
T0, T1, T2, T3, T4, T5 = 8, 9, 10, 11, 12, 13
S0, S1, S2, S3, S4 = 16, 17, 18, 19, 20
RA = spike.RA
DADDU = 0x2D
UINT64_MAX = 0xFFFFFFFFFFFFFFFF
INT64_MIN = 0x8000000000000000
INT64_MAX = 0x7FFFFFFFFFFFFFFF
DADDU_PC = BASE + 12


def nop_word() -> int:
    return spike.encode_r(ZERO, ZERO, ZERO, 0, 0)


def jr_ra_word() -> int:
    return spike.encode_r(RA, ZERO, ZERO, 0, 0x08)


def daddu_fixture_rows() -> list[tuple[int, str, int]]:
    rows = [
        ("set_t0_upper", spike.encode_i(0x0F, ZERO, T0, 0xFFFF)),
        ("set_t0_all_ones", spike.encode_i(0x0D, T0, T0, 0xFFFF)),
        ("set_t1_one", spike.encode_i(0x09, ZERO, T1, 1)),
        ("all_ones_plus_one_wraps", spike.encode_r(T0, T1, T2, 0, DADDU)),
        ("set_t3_negative_ten", spike.encode_i(0x09, ZERO, T3, -10)),
        ("negative_ten_plus_one", spike.encode_r(T3, T1, T4, 0, DADDU)),
        ("negative_ten_plus_all_ones", spike.encode_r(T3, T0, T5, 0, DADDU)),
        ("source__destination_alias_doubles", spike.encode_r(T4, T4, T4, 0, DADDU)),
        ("zero_destination_is_discarded", spike.encode_r(T0, T1, ZERO, 0, DADDU)),
        ("set_positive_32_max_upper", spike.encode_i(0x0F, ZERO, S0, 0x7FFF)),
        ("set_positive_32_max_lower", spike.encode_i(0x0D, S0, S0, 0xFFFF)),
        ("cross_positive_32_bit_boundary", spike.encode_r(S0, T1, S1, 0, DADDU)),
        ("set_negative_32_min", spike.encode_i(0x0F, ZERO, S2, 0x8000)),
        ("cross_negative_32_bit_boundary", spike.encode_r(S2, T1, S3, 0, DADDU)),
        ("upper_bit_addition", spike.encode_r(T0, T0, S4, 0, DADDU)),
        ("destination_rt_alias_wraps", spike.encode_r(T0, T1, T1, 0, DADDU)),
        ("return_value", spike.encode_i(0x09, ZERO, V0, 42)),
        ("return_from_main", jr_ra_word()),
        ("return_delay_slot", nop_word()),
    ]
    return [(BASE + index * 4, name, word) for index, (name, word) in enumerate(rows)]


def daddu_fixture():
    data = spike.build_elf_from_rows(daddu_fixture_rows())
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


class DadduDecodeTests(unittest.TestCase):
    def test_decode_daddu_uses_special_funct_0x2d_with_zero_shamt(self):
        instruction = spike.decode_instruction(BASE, spike.encode_r(T0, T1, T2, 0, DADDU))
        self.assertEqual(instruction["op"], "daddu")
        self.assertEqual((instruction["rs"], instruction["rt"], instruction["rd"]), (T0, T1, T2))
        self.assertNotIn("imm", instruction)

    def test_nonzero_shamt_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unsupported SPECIAL instruction"):
            spike.decode_instruction(BASE, spike.encode_r(T0, T1, T2, 1, DADDU))

    def test_other_special_function_remains_unsupported(self):
        with self.assertRaisesRegex(ValueError, "Unsupported SPECIAL instruction"):
            spike.decode_instruction(BASE, spike.encode_r(T0, T1, T2, 0, 0x2E))


class DadduIrTests(unittest.TestCase):
    def test_ir_records_register_operands_and_rd_destination(self):
        result = ir.analyze_words(BASE, {BASE: spike.encode_r(T0, T1, T2, 0, DADDU)})
        instruction = result.instructions[0]
        self.assertEqual(instruction.op, "daddu")
        self.assertEqual((instruction.rs, instruction.rt, instruction.rd), (T0, T1, T2))
        self.assertIsNone(instruction.immediate)
        self.assertIsNone(instruction.immediate_kind)
        self.assertEqual(instruction.destination_register, T2)
        self.assertEqual(instruction.control, ir.FALLTHROUGH)

    def test_zero_destination_is_recorded_as_none(self):
        result = ir.analyze_words(BASE, {BASE: spike.encode_r(T0, T1, ZERO, 0, DADDU)})
        self.assertIsNone(result.instructions[0].destination_register)

    def test_ir_rejects_unrelated_function_fail_closed(self):
        with self.assertRaises(ir.AnalysisError) as caught:
            ir.analyze_words(BASE, {BASE: spike.encode_r(T0, T1, T2, 0, 0x2E)})
        self.assertEqual(caught.exception.code, ir.IR_UNSUPPORTED_INSTRUCTION)


class DadduOracleTests(unittest.TestCase):
    def test_oracle_matches_literal_64_bit_modulo_results(self):
        data, _ = daddu_fixture()
        entry, words, info = spike.parse_elf(data)
        state = spike.normalize_state(spike.execute_oracle(entry, words))
        regs = state["registers"]
        self.assertEqual(info["instruction_count"], 19)
        self.assertEqual(regs[ZERO], 0)
        self.assertEqual(regs[T0], UINT64_MAX)
        self.assertEqual(regs[T1], 0)
        self.assertEqual(regs[T2], 0)
        self.assertEqual(regs[T3], UINT64_MAX - 9)
        self.assertEqual(regs[T4], UINT64_MAX - 17)
        self.assertEqual(regs[T5], UINT64_MAX - 10)
        self.assertEqual(regs[S0], 0x000000007FFFFFFF)
        self.assertEqual(regs[S1], 0x0000000080000000)
        self.assertEqual(regs[S2], 0xFFFFFFFF80000000)
        self.assertEqual(regs[S3], 0xFFFFFFFF80000001)
        self.assertEqual(regs[S4], UINT64_MAX - 1)
        self.assertEqual(regs[V0], 42)
        self.assertEqual(state["memory"], [])
        self.assertEqual(state["pc"], spike.RETURN_SENTINEL)
        self.assertEqual(state["trace"], [BASE + index * 4 for index in range(19)])


class DadduLoweringTests(unittest.TestCase):
    def test_native_lowering_matches_oracle_and_literals(self):
        if compiler_available() is None:
            self.skipTest("No C++ compiler available for the DADDU native differential")
        data, result = daddu_fixture()
        entry, words, _ = spike.parse_elf(data)
        oracle = spike.normalize_state(spike.execute_oracle(entry, words))
        source_text = lower.lower_to_cpp(result)
        with tempfile.TemporaryDirectory() as temp:
            out_dir = Path(temp)
            source = out_dir / "generated.cpp"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            exe = out_dir / ("rptp-daddu.exe" if os.name == "nt" else "rptp-daddu")
            command = spike.compile_generated(source, exe, "auto")
            proc = subprocess.run([str(exe)], cwd=out_dir, text=True, capture_output=True, check=False)
        self.assertEqual(proc.returncode, 0, msg=f"{command}\n{proc.stdout}\n{proc.stderr}")
        self.assertEqual(proc.stderr, "")
        native = json.loads(proc.stdout)
        self.assertEqual(native, oracle)
        self.assertEqual(native["registers"][T2], 0)
        self.assertEqual(native["registers"][T4], UINT64_MAX - 17)
        self.assertEqual(native["registers"][T5], UINT64_MAX - 10)
        self.assertEqual(native["registers"][S1], 0x0000000080000000)
        self.assertEqual(native["registers"][S4], UINT64_MAX - 1)
        self.assertEqual(native["registers"][ZERO], 0)

    def test_native_helper_wraps_full_64_bit_values(self):
        if compiler_available() is None:
            self.skipTest("No C++ compiler available for the DADDU boundary differential")
        result = ir.analyze_words(BASE, {BASE: spike.encode_r(T0, T1, T2, 0, DADDU)})
        source_text = lower.lower_to_cpp(result)
        harness_text = f'''#define main rptp_generated_entry
#include "generated.cpp"
#undef main

int main() {{
    const auto add = [](std::uint64_t lhs, std::uint64_t rhs) {{
        State state;
        state.pc = 0x{BASE:08X}u;
        state.registers[{T0}] = lhs;
        state.registers[{T1}] = rhs;
        run_generated(state);
        return state.registers[{T2}];
    }};
    std::cout << std::hex << add(0x{UINT64_MAX:016X}ull, 1ull) << ' '
              << add(0x{INT64_MAX:016X}ull, 1ull) << ' '
              << add(0x{INT64_MIN:016X}ull, 0x{INT64_MIN:016X}ull) << ' '
              << add(0x0123456789ABCDEFull, 0x0FEDCBA987654321ull) << '\\n';
    return 0;
}}
'''
        with tempfile.TemporaryDirectory() as temp:
            out_dir = Path(temp)
            source = out_dir / "generated.cpp"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            harness = out_dir / "harness.cpp"
            harness.write_text(harness_text, encoding="utf-8", newline="\n")
            exe = out_dir / ("rptp-daddu-boundary.exe" if os.name == "nt" else "rptp-daddu-boundary")
            command = spike.compile_generated(harness, exe, "auto")
            proc = subprocess.run([str(exe)], cwd=out_dir, text=True, capture_output=True, check=False)
        self.assertEqual(proc.returncode, 0, msg=f"{command}\n{proc.stdout}\n{proc.stderr}")
        self.assertEqual(proc.stderr, "")
        self.assertEqual(proc.stdout.split(), ["0", "8000000000000000", "0", "1111111111111110"])

    def test_lowering_is_deterministic_and_ignores_raw_words(self):
        _, result = daddu_fixture()
        source = lower.lower_to_cpp(result)
        mutated = replace(
            result,
            instructions=tuple(replace(item, word=0) for item in result.instructions),
        )
        self.assertEqual(source, lower.lower_to_cpp(mutated))
        self.assertIn("daddu64(", source)
        self.assertNotIn("\r", source)
        self.assertTrue(source.endswith("\n"))

    def test_lowering_rejects_malformed_metadata(self):
        _, result = daddu_fixture()
        cases = {
            "missing_rs": ({"rs": None}, lower.LOWER_MALFORMED_INSTRUCTION),
            "missing_rt": ({"rt": None}, lower.LOWER_MALFORMED_INSTRUCTION),
            "missing_rd": ({"rd": None}, lower.LOWER_MALFORMED_INSTRUCTION),
            "wrong_destination": ({"destination_register": None}, lower.LOWER_MALFORMED_INSTRUCTION),
            "unexpected_immediate": ({"immediate": 0}, lower.LOWER_MALFORMED_INSTRUCTION),
            "unexpected_immediate_kind": ({"immediate_kind": ir.ZERO16}, lower.LOWER_MALFORMED_INSTRUCTION),
            "wrong_control": ({"control": lower.DIRECT_JUMP}, lower.LOWER_INVALID_CONTROL),
            "unexpected_target": ({"target": BASE}, lower.LOWER_MALFORMED_INSTRUCTION),
        }
        for name, (fields, code) in cases.items():
            with self.subTest(name=name):
                malformed = replace_instruction(result, DADDU_PC, **fields)
                with self.assertRaises(lower.LoweringError) as caught:
                    lower.lower_to_cpp(malformed)
                self.assertEqual(caught.exception.code, code)


if __name__ == "__main__":
    unittest.main(verbosity=2)
