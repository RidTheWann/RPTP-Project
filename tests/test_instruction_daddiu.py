# SPDX-License-Identifier: GPL-3.0-or-later
"""Synthetic DADDIU tests for signed immediates and modulo-64-bit addition."""
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


spike = load_module("rptp_gate0_spike_daddiu", "tools/rptp_gate0_spike.py")
ir = load_module("rptp_ir_daddiu", "tools/rptp_ir.py")
lower = load_module("rptp_lower_daddiu", "tools/rptp_lower.py")

BASE = spike.BASE
ZERO, V0 = spike.ZERO, spike.V0
T0, T1, T2, T3, T4, T5, T6 = 8, 9, 10, 11, 12, 13, 14
S0 = spike.S0
S1, S2, S3, S4 = 17, 18, 19, 20
RA = spike.RA
DADDIU = 0x19
DADDI = 0x18
UINT64_MAX = 0xFFFFFFFFFFFFFFFF
INT64_MIN = 0x8000000000000000
INT64_MAX = 0x7FFFFFFFFFFFFFFF


def nop_word() -> int:
    return spike.encode_r(ZERO, ZERO, ZERO, 0, 0)


def jr_ra_word() -> int:
    return spike.encode_r(RA, ZERO, ZERO, 0, 0x08)


def daddiu_fixture_rows() -> list[tuple[int, str, int]]:
    rows = [
        ("set_zero", spike.encode_i(0x09, ZERO, T0, 0)),
        ("zero_plus_max_positive_imm", spike.encode_i(DADDIU, ZERO, T1, 32767)),
        ("set_all_ones", spike.encode_i(0x09, ZERO, T2, -1)),
        ("all_ones_plus_one_wraps", spike.encode_i(DADDIU, T2, T3, 1)),
        ("zero_minus_one", spike.encode_i(DADDIU, ZERO, T4, -1)),
        ("set_negative_ten", spike.encode_i(0x09, ZERO, T5, -10)),
        ("negative_ten_plus_five", spike.encode_i(DADDIU, T5, T6, 5)),
        ("negative_ten_plus_five_copy", spike.encode_i(DADDIU, T5, S0, 5)),
        ("destination_aliases_source", spike.encode_i(DADDIU, T6, T6, 5)),
        ("zero_destination_is_discarded", spike.encode_i(DADDIU, T2, ZERO, -1)),
        ("set_signed_32_max_upper", spike.encode_i(0x0F, ZERO, S1, 0x7FFF)),
        ("set_signed_32_max_lower", spike.encode_i(0x0D, S1, S1, 0xFFFF)),
        ("cross_positive_32_bit_boundary", spike.encode_i(DADDIU, S1, S2, 1)),
        ("set_signed_32_min", spike.encode_i(0x0F, ZERO, S3, 0x8000)),
        ("cross_negative_32_bit_boundary", spike.encode_i(DADDIU, S3, S4, -1)),
        ("return_value", spike.encode_i(0x09, ZERO, V0, 42)),
        ("return_from_main", jr_ra_word()),
        ("return_delay_slot", nop_word()),
    ]
    return [(BASE + index * 4, name, word) for index, (name, word) in enumerate(rows)]


def daddiu_fixture():
    data = spike.build_elf_from_rows(daddiu_fixture_rows())
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


class DaddiuDecodeTests(unittest.TestCase):
    def test_decode_daddiu_uses_opcode_0x19_and_sign_extends_immediate(self):
        instruction = spike.decode_instruction(BASE, spike.encode_i(DADDIU, T0, T1, -32768))
        self.assertEqual(instruction["op"], "daddiu")
        self.assertEqual((instruction["rs"], instruction["rt"]), (T0, T1))
        self.assertEqual(instruction["imm"], -32768)

    def test_trapping_daddi_remains_unsupported(self):
        with self.assertRaisesRegex(ValueError, "Unsupported opcode 0x18"):
            spike.decode_instruction(BASE, spike.encode_i(DADDI, T0, T1, 1))


class DaddiuIrTests(unittest.TestCase):
    def test_ir_records_signed_immediate_and_rt_destination(self):
        result = ir.analyze_words(BASE, {BASE: spike.encode_i(DADDIU, T0, T1, -1)})
        instruction = result.instructions[0]
        self.assertEqual(instruction.op, "daddiu")
        self.assertEqual((instruction.rs, instruction.rt), (T0, T1))
        self.assertEqual(instruction.immediate, -1)
        self.assertEqual(instruction.immediate_kind, ir.SIGNED16)
        self.assertEqual(instruction.destination_register, T1)
        self.assertEqual(instruction.control, ir.FALLTHROUGH)

    def test_ir_rejects_unrelated_opcode_fail_closed(self):
        with self.assertRaises(ir.AnalysisError) as caught:
            ir.analyze_words(BASE, {BASE: spike.encode_i(0x10, T0, T1, 1)})
        self.assertEqual(caught.exception.code, ir.IR_UNSUPPORTED_INSTRUCTION)


class DaddiuOracleTests(unittest.TestCase):
    def test_oracle_matches_literal_64_bit_modulo_results(self):
        data, _ = daddiu_fixture()
        entry, words, info = spike.parse_elf(data)
        state = spike.normalize_state(spike.execute_oracle(entry, words))
        regs = state["registers"]
        self.assertEqual(info["instruction_count"], 18)
        self.assertEqual(regs[ZERO], 0)
        self.assertEqual(regs[T0], 0)
        self.assertEqual(regs[T1], 32767)
        self.assertEqual(regs[T2], UINT64_MAX)
        self.assertEqual(regs[T3], 0)
        self.assertEqual(regs[T4], UINT64_MAX)
        self.assertEqual(regs[T5], UINT64_MAX - 9)
        self.assertEqual(regs[T6], 0)
        self.assertEqual(regs[S0], UINT64_MAX - 4)
        self.assertEqual(regs[S1], 0x000000007FFFFFFF)
        self.assertEqual(regs[S2], 0x0000000080000000)
        self.assertEqual(regs[S3], 0xFFFFFFFF80000000)
        self.assertEqual(regs[S4], 0xFFFFFFFF7FFFFFFF)
        self.assertEqual(regs[V0], 42)
        self.assertEqual(state["memory"], [])
        self.assertEqual(state["pc"], spike.RETURN_SENTINEL)
        self.assertEqual(state["trace"], [BASE + index * 4 for index in range(18)])


class DaddiuLoweringTests(unittest.TestCase):
    def test_native_lowering_matches_oracle_and_literals(self):
        if compiler_available() is None:
            self.skipTest("No C++ compiler available for the DADDIU native differential")
        data, result = daddiu_fixture()
        entry, words, _ = spike.parse_elf(data)
        oracle = spike.normalize_state(spike.execute_oracle(entry, words))
        source_text = lower.lower_to_cpp(result)
        with tempfile.TemporaryDirectory() as temp:
            out_dir = Path(temp)
            source = out_dir / "generated.cpp"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            exe = out_dir / ("rptp-daddiu.exe" if os.name == "nt" else "rptp-daddiu")
            command = spike.compile_generated(source, exe, "auto")
            proc = subprocess.run([str(exe)], cwd=out_dir, text=True, capture_output=True, check=False)
        self.assertEqual(proc.returncode, 0, msg=f"{command}\n{proc.stdout}\n{proc.stderr}")
        self.assertEqual(proc.stderr, "")
        native = json.loads(proc.stdout)
        self.assertEqual(native, oracle)
        self.assertEqual(native["registers"][T3], 0)
        self.assertEqual(native["registers"][T4], UINT64_MAX)
        self.assertEqual(native["registers"][S0], UINT64_MAX - 4)
        self.assertEqual(native["registers"][S2], 0x0000000080000000)
        self.assertEqual(native["registers"][S4], 0xFFFFFFFF7FFFFFFF)
        self.assertEqual(native["registers"][ZERO], 0)

    def test_native_helper_wraps_full_64_bit_values(self):
        if compiler_available() is None:
            self.skipTest("No C++ compiler available for the DADDIU boundary differential")
        result = ir.analyze_words(BASE, {BASE: spike.encode_i(DADDIU, T0, T1, 1)})
        source_text = lower.lower_to_cpp(result)
        harness_text = f'''#define main rptp_generated_entry
#include "generated.cpp"
#undef main

int main() {{
    State all_ones;
    all_ones.pc = 0x{BASE:08X}u;
    all_ones.registers[{T0}] = 0x{UINT64_MAX:016X}ull;
    run_generated(all_ones);

    State signed_max;
    signed_max.pc = 0x{BASE:08X}u;
    signed_max.registers[{T0}] = 0x{INT64_MAX:016X}ull;
    run_generated(signed_max);

    State signed_min;
    signed_min.pc = 0x{BASE:08X}u;
    signed_min.registers[{T0}] = 0x{INT64_MIN:016X}ull;
    run_generated(signed_min);

    std::cout << std::hex << all_ones.registers[{T1}] << ' '
              << signed_max.registers[{T1}] << ' '
              << signed_min.registers[{T1}] << '\\n';
    return 0;
}}
'''
        with tempfile.TemporaryDirectory() as temp:
            out_dir = Path(temp)
            source = out_dir / "generated.cpp"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            harness = out_dir / "harness.cpp"
            harness.write_text(harness_text, encoding="utf-8", newline="\n")
            exe = out_dir / ("rptp-daddiu-boundary.exe" if os.name == "nt" else "rptp-daddiu-boundary")
            command = spike.compile_generated(harness, exe, "auto")
            proc = subprocess.run([str(exe)], cwd=out_dir, text=True, capture_output=True, check=False)
        self.assertEqual(proc.returncode, 0, msg=f"{command}\n{proc.stdout}\n{proc.stderr}")
        self.assertEqual(proc.stderr, "")
        self.assertEqual(proc.stdout.split(), ["0", "8000000000000000", "8000000000000001"])

    def test_lowering_is_deterministic_and_ignores_raw_words(self):
        _, result = daddiu_fixture()
        source = lower.lower_to_cpp(result)
        mutated = replace(
            result,
            instructions=tuple(replace(item, word=0) for item in result.instructions),
        )
        self.assertEqual(source, lower.lower_to_cpp(mutated))
        self.assertIn("daddiu64(", source)
        self.assertNotIn("\r", source)
        self.assertTrue(source.endswith("\n"))

    def test_lowering_rejects_malformed_metadata(self):
        _, result = daddiu_fixture()
        cases = {
            "missing_rs": ({"rs": None}, lower.LOWER_MALFORMED_INSTRUCTION),
            "missing_rt": ({"rt": None}, lower.LOWER_MALFORMED_INSTRUCTION),
            "wrong_destination": ({"destination_register": None}, lower.LOWER_MALFORMED_INSTRUCTION),
            "wrong_immediate_kind": ({"immediate_kind": ir.ZERO16}, lower.LOWER_MALFORMED_INSTRUCTION),
            "out_of_range_immediate": ({"immediate": 32768}, lower.LOWER_MALFORMED_INSTRUCTION),
            "unexpected_rd": ({"rd": T2}, lower.LOWER_MALFORMED_INSTRUCTION),
        }
        for name, (fields, code) in cases.items():
            with self.subTest(name=name):
                malformed = replace_instruction(result, BASE + 4, **fields)
                with self.assertRaises(lower.LoweringError) as caught:
                    lower.lower_to_cpp(malformed)
                self.assertEqual(caught.exception.code, code)


if __name__ == "__main__":
    unittest.main(verbosity=2)
