# SPDX-License-Identifier: GPL-3.0-or-later
"""Synthetic SLL tests for 32-bit left shifts and the modeled 64-bit bridge."""
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


spike = load_module("rptp_gate0_spike_sll", "tools/rptp_gate0_spike.py")
ir = load_module("rptp_ir_sll", "tools/rptp_ir.py")
lower = load_module("rptp_lower_sll", "tools/rptp_lower.py")

BASE = spike.BASE
ZERO, V0 = spike.ZERO, spike.V0
T0, T1, T2, T3, T4, T5, T6 = 8, 9, 10, 11, 12, 13, 14
S0, S1, S2, S3, S4 = 16, 17, 18, 19, 20
RA = spike.RA
SLL = 0x00
UINT32_MAX = 0xFFFFFFFF
SIGNED_32_MIN_IN_64 = 0xFFFFFFFF80000000


def nop_word() -> int:
    return spike.encode_r(ZERO, ZERO, ZERO, 0, 0)


def jr_ra_word() -> int:
    return spike.encode_r(RA, ZERO, ZERO, 0, 0x08)


def sll_fixture_rows() -> list[tuple[int, str, int]]:
    rows = [
        ("set_one", spike.encode_i(0x09, ZERO, T0, 1)),
        ("shift_into_sign_bit", spike.encode_r(ZERO, T0, T1, 31, SLL)),
        ("thirty_two_bit_overflow_discards_upper_bit", spike.encode_r(ZERO, T1, T2, 1, SLL)),
        ("zero_shift_copies_source", spike.encode_r(ZERO, T0, T3, 0, SLL)),
        ("set_all_ones", spike.encode_i(0x09, ZERO, T4, -1)),
        ("shift_all_ones_by_four", spike.encode_r(ZERO, T4, T5, 4, SLL)),
        ("zero_destination_is_discarded", spike.encode_r(ZERO, T0, ZERO, 31, SLL)),
        ("shift_by_thirty", spike.encode_r(ZERO, T0, S0, 30, SLL)),
        ("source_aliases_destination", spike.encode_r(ZERO, T0, T0, 1, SLL)),
        ("set_0x00010001_upper", spike.encode_i(0x0F, ZERO, S1, 0x0001)),
        ("set_0x00010001_lower", spike.encode_i(0x0D, S1, S1, 0x0001)),
        ("shift_0x00010001_by_sixteen", spike.encode_r(ZERO, S1, S2, 16, SLL)),
        ("shift_positive_word_into_sign_bit", spike.encode_r(ZERO, S2, S3, 15, SLL)),
        ("sign_extended_input_uses_low_32_bits", spike.encode_r(ZERO, S3, S4, 1, SLL)),
        ("return_value", spike.encode_i(0x09, ZERO, V0, 42)),
        ("return_from_main", jr_ra_word()),
        ("return_delay_slot", nop_word()),
    ]
    return [(BASE + index * 4, name, word) for index, (name, word) in enumerate(rows)]


def sll_fixture():
    data = spike.build_elf_from_rows(sll_fixture_rows())
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


class SllDecodeTests(unittest.TestCase):
    def test_decode_sll_records_shift_amount_and_register_fields(self):
        instruction = spike.decode_instruction(BASE, spike.encode_r(ZERO, T1, T2, 17, SLL))
        self.assertEqual(instruction["op"], "sll")
        self.assertEqual((instruction["rs"], instruction["rt"], instruction["rd"]), (ZERO, T1, T2))
        self.assertEqual(instruction["shamt"], 17)

    def test_decode_sll_requires_zero_rs(self):
        with self.assertRaisesRegex(ValueError, "SLL requires rs=0"):
            spike.decode_instruction(BASE, spike.encode_r(T0, T1, T2, 4, SLL))

    def test_all_zero_word_remains_nop(self):
        instruction = spike.decode_instruction(BASE, spike.encode_r(ZERO, ZERO, ZERO, 0, SLL))
        self.assertEqual(instruction["op"], "nop")


class SllIrTests(unittest.TestCase):
    def test_ir_records_shift5_immediate_and_rd_destination(self):
        result = ir.analyze_words(BASE, {BASE: spike.encode_r(ZERO, T1, T2, 31, SLL)})
        instruction = result.instructions[0]
        self.assertEqual(instruction.op, "sll")
        self.assertEqual(instruction.control, ir.FALLTHROUGH)
        self.assertEqual((instruction.rs, instruction.rt, instruction.rd), (ZERO, T1, T2))
        self.assertEqual((instruction.immediate, instruction.immediate_kind), (31, ir.SHIFT5))
        self.assertEqual(instruction.destination_register, T2)

    def test_ir_rejects_nonzero_rs_sll_fail_closed(self):
        with self.assertRaises(ir.AnalysisError) as caught:
            ir.analyze_words(BASE, {BASE: spike.encode_r(T0, T1, T2, 4, SLL)})

        self.assertEqual(caught.exception.code, ir.IR_UNSUPPORTED_INSTRUCTION)
        self.assertIn("SLL requires rs=0", str(caught.exception))

    def test_ir_records_zero_destination_for_zero_rd(self):
        result = ir.analyze_words(BASE, {BASE: spike.encode_r(ZERO, T1, ZERO, 3, SLL)})
        self.assertIsNone(result.instructions[0].destination_register)


class SllOracleTests(unittest.TestCase):
    def test_oracle_matches_literal_32_bit_shift_results(self):
        data, _ = sll_fixture()
        entry, words, info = spike.parse_elf(data)
        state = spike.normalize_state(spike.execute_oracle(entry, words))
        regs = state["registers"]
        self.assertEqual(info["instruction_count"], 17)
        self.assertEqual(regs[ZERO], 0)
        self.assertEqual(regs[T0], 2)
        self.assertEqual(regs[T1], SIGNED_32_MIN_IN_64)
        self.assertEqual(regs[T2], 0)
        self.assertEqual(regs[T3], 1)
        self.assertEqual(regs[T4], 0xFFFFFFFFFFFFFFFF)
        self.assertEqual(regs[T5], 0xFFFFFFFFFFFFFFF0)
        self.assertEqual(regs[S0], 0x40000000)
        self.assertEqual(regs[S1], 0x00010001)
        self.assertEqual(regs[S2], 0x00010000)
        self.assertEqual(regs[S3], SIGNED_32_MIN_IN_64)
        self.assertEqual(regs[S4], 0)
        self.assertEqual(regs[V0], 42)
        self.assertEqual(state["memory"], [])
        self.assertEqual(state["pc"], spike.RETURN_SENTINEL)
        self.assertEqual(state["trace"], [BASE + index * 4 for index in range(17)])


class SllLoweringTests(unittest.TestCase):
    def test_native_lowering_matches_oracle_and_literals(self):
        if compiler_available() is None:
            self.skipTest("No C++ compiler available for the SLL native differential")
        data, result = sll_fixture()
        entry, words, _ = spike.parse_elf(data)
        oracle = spike.normalize_state(spike.execute_oracle(entry, words))
        source_text = lower.lower_to_cpp(result)
        with tempfile.TemporaryDirectory() as temp:
            out_dir = Path(temp)
            source = out_dir / "generated.cpp"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            exe = out_dir / ("rptp-sll.exe" if os.name == "nt" else "rptp-sll")
            command = spike.compile_generated(source, exe, "auto")
            proc = subprocess.run([str(exe)], cwd=out_dir, text=True, capture_output=True, check=False)
        self.assertEqual(proc.returncode, 0, msg=f"{command}\n{proc.stdout}\n{proc.stderr}")
        self.assertEqual(proc.stderr, "")
        native = json.loads(proc.stdout)
        self.assertEqual(native, oracle)
        self.assertEqual(native["registers"][T1], SIGNED_32_MIN_IN_64)
        self.assertEqual(native["registers"][T2], 0)
        self.assertEqual(native["registers"][T5], 0xFFFFFFFFFFFFFFF0)
        self.assertEqual(native["registers"][S4], 0)
        self.assertEqual(native["registers"][ZERO], 0)

    def test_native_helper_truncates_to_32_bits_then_sign_extends(self):
        if compiler_available() is None:
            self.skipTest("No C++ compiler available for the SLL boundary differential")
        result = ir.analyze_words(BASE, {BASE: spike.encode_r(ZERO, T1, T2, 0, SLL)})
        source_text = lower.lower_to_cpp(result)
        harness_text = f'''#define main rptp_generated_entry
#include "generated.cpp"
#undef main

int main() {{
    std::cout << std::hex << sll32(0x0000000000000001ull, 31u) << ' '
              << sll32(0x0000000000000001ull, 0u) << ' '
              << sll32(0x00000000FFFFFFFFull, 4u) << ' '
              << sll32(0xFFFFFFFF00000001ull, 1u) << ' '
              << sll32(0x0000000000000001ull, 16u) << ' '
              << sll32(0x00000000FFFFFFFFull, 30u) << '\\n';
    return 0;
}}
'''
        with tempfile.TemporaryDirectory() as temp:
            out_dir = Path(temp)
            source = out_dir / "generated.cpp"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            harness = out_dir / "harness.cpp"
            harness.write_text(harness_text, encoding="utf-8", newline="\n")
            exe = out_dir / ("rptp-sll-boundary.exe" if os.name == "nt" else "rptp-sll-boundary")
            command = spike.compile_generated(harness, exe, "auto")
            proc = subprocess.run([str(exe)], cwd=out_dir, text=True, capture_output=True, check=False)
        self.assertEqual(proc.returncode, 0, msg=f"{command}\n{proc.stdout}\n{proc.stderr}")
        self.assertEqual(proc.stderr, "")
        self.assertEqual(
            proc.stdout.split(),
            ["ffffffff80000000", "1", "fffffffffffffff0", "2", "10000", "ffffffffc0000000"],
        )

    def test_lowering_is_deterministic_and_ignores_raw_words(self):
        _, result = sll_fixture()
        source = lower.lower_to_cpp(result)
        mutated = replace(
            result,
            instructions=tuple(replace(item, word=0) for item in result.instructions),
        )
        self.assertEqual(source, lower.lower_to_cpp(mutated))
        self.assertIn("sll32(", source)
        self.assertNotIn("\r", source)
        self.assertTrue(source.endswith("\n"))

    def test_lowering_rejects_malformed_metadata(self):
        _, result = sll_fixture()
        cases = {
            "missing_rs": ({"rs": None}, lower.LOWER_MALFORMED_INSTRUCTION),
            "nonzero_rs": ({"rs": T0}, lower.LOWER_MALFORMED_INSTRUCTION),
            "missing_rt": ({"rt": None}, lower.LOWER_MALFORMED_INSTRUCTION),
            "missing_rd": ({"rd": None}, lower.LOWER_MALFORMED_INSTRUCTION),
            "wrong_destination": ({"destination_register": None}, lower.LOWER_MALFORMED_INSTRUCTION),
            "wrong_immediate_kind": ({"immediate_kind": ir.ZERO16}, lower.LOWER_MALFORMED_INSTRUCTION),
            "out_of_range_immediate": ({"immediate": 32}, lower.LOWER_MALFORMED_INSTRUCTION),
            "missing_immediate": ({"immediate": None, "immediate_kind": None}, lower.LOWER_MALFORMED_INSTRUCTION),
        }
        for name, (fields, code) in cases.items():
            with self.subTest(name=name):
                malformed = replace_instruction(result, BASE + 4, **fields)
                with self.assertRaises(lower.LoweringError) as caught:
                    lower.lower_to_cpp(malformed)
                self.assertEqual(caught.exception.code, code)


if __name__ == "__main__":
    unittest.main(verbosity=2)
