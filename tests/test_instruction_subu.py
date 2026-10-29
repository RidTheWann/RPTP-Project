# SPDX-License-Identifier: GPL-3.0-or-later
"""Synthetic SUBU tests for 32-bit modulo subtraction with sign extension."""
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


spike = load_module("rptp_gate0_spike_subu", "tools/rptp_gate0_spike.py")
ir = load_module("rptp_ir_subu", "tools/rptp_ir.py")
lower = load_module("rptp_lower_subu", "tools/rptp_lower.py")

BASE = spike.BASE
ZERO, V0 = spike.ZERO, spike.V0
A0, A1 = 4, 5
T0, T1, T2, T3, T4, T5 = 8, 9, 10, 11, 12, 13
S0, S1, S2 = 16, 17, 18
RA = spike.RA
SUBU = 0x23
SUB = 0x22
DSUBU = 0x2E
UINT64_MAX = 0xFFFFFFFFFFFFFFFF
SUBU_PC = BASE + 8


def nop_word() -> int:
    return spike.encode_r(ZERO, ZERO, ZERO, 0, 0)


def jr_ra_word() -> int:
    return spike.encode_r(RA, ZERO, ZERO, 0, 0x08)


def subu_fixture_rows() -> list[tuple[int, str, int]]:
    rows = [
        # LUI 0x8000 sign-extends the 32-bit word, so the modeled register holds
        # 0xFFFFFFFF80000000 while the SUBU operand word is 0x80000000.
        ("set_t0_negative_word", spike.encode_i(0x0F, ZERO, T0, 0x8000)),
        ("set_t1_one", spike.encode_i(0x09, ZERO, T1, 1)),
        ("upper_bits_of_rs_are_ignored", spike.encode_r(T0, T1, T2, 0, SUBU)),
        ("set_t3_positive_32_max_upper", spike.encode_i(0x0F, ZERO, T3, 0x7FFF)),
        ("set_t3_positive_32_max_lower", spike.encode_i(0x0D, T3, T3, 0xFFFF)),
        ("zero_minus_one_wraps", spike.encode_r(ZERO, T1, T4, 0, SUBU)),
        ("positive_difference_keeps_upper_clear", spike.encode_r(T3, T1, T5, 0, SUBU)),
        ("zero_minus_positive_sign_extends", spike.encode_r(ZERO, T3, S0, 0, SUBU)),
        ("equal_operands_yield_zero", spike.encode_r(T0, T0, S1, 0, SUBU)),
        ("difference_at_int32_min", spike.encode_r(ZERO, T0, S2, 0, SUBU)),
        ("set_a0_eight", spike.encode_i(0x09, ZERO, A0, 8)),
        ("set_a1_three", spike.encode_i(0x09, ZERO, A1, 3)),
        ("rs_destination_alias", spike.encode_r(A0, A1, A0, 0, SUBU)),
        ("rt_destination_alias", spike.encode_r(A0, A1, A1, 0, SUBU)),
        ("self_subtraction_is_zero", spike.encode_r(A0, A0, S1, 0, SUBU)),
        ("zero_destination_is_discarded", spike.encode_r(A0, A1, ZERO, 0, SUBU)),
        ("high_minus_high_ignores_upper", spike.encode_r(T0, T3, T0, 0, SUBU)),
        ("return_value", spike.encode_i(0x09, ZERO, V0, 42)),
        ("return_from_main", jr_ra_word()),
        ("return_delay_slot", nop_word()),
    ]
    return [(BASE + index * 4, name, word) for index, (name, word) in enumerate(rows)]


def subu_fixture():
    data = spike.build_elf_from_rows(subu_fixture_rows())
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


class SubuDecodeTests(unittest.TestCase):
    def test_decode_subu_uses_special_funct_0x23_with_zero_shamt(self):
        instruction = spike.decode_instruction(BASE, spike.encode_r(T0, T1, T2, 0, SUBU))
        self.assertEqual(instruction["op"], "subu")
        self.assertEqual((instruction["rs"], instruction["rt"], instruction["rd"]), (T0, T1, T2))
        self.assertNotIn("imm", instruction)

    def test_nonzero_shamt_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unsupported SPECIAL instruction"):
            spike.decode_instruction(BASE, spike.encode_r(T0, T1, T2, 1, SUBU))

    def test_trapping_sub_remains_unsupported(self):
        with self.assertRaisesRegex(ValueError, "Unsupported SPECIAL instruction"):
            spike.decode_instruction(BASE, spike.encode_r(T0, T1, T2, 0, SUB))

    def test_doubleword_dsubu_remains_unsupported(self):
        with self.assertRaisesRegex(ValueError, "Unsupported SPECIAL instruction"):
            spike.decode_instruction(BASE, spike.encode_r(T0, T1, T2, 0, DSUBU))


class SubuIrTests(unittest.TestCase):
    def test_ir_records_register_operands_and_rd_destination(self):
        result = ir.analyze_words(BASE, {BASE: spike.encode_r(T0, T1, T2, 0, SUBU)})
        instruction = result.instructions[0]
        self.assertEqual(instruction.op, "subu")
        self.assertEqual((instruction.rs, instruction.rt, instruction.rd), (T0, T1, T2))
        self.assertIsNone(instruction.immediate)
        self.assertIsNone(instruction.immediate_kind)
        self.assertEqual(instruction.destination_register, T2)
        self.assertEqual(instruction.control, ir.FALLTHROUGH)

    def test_zero_destination_is_recorded_as_none(self):
        result = ir.analyze_words(BASE, {BASE: spike.encode_r(T0, T1, ZERO, 0, SUBU)})
        self.assertIsNone(result.instructions[0].destination_register)

    def test_ir_rejects_unrelated_function_fail_closed(self):
        for funct in (SUB, DSUBU):
            with self.subTest(funct=funct):
                with self.assertRaises(ir.AnalysisError) as caught:
                    ir.analyze_words(BASE, {BASE: spike.encode_r(T0, T1, T2, 0, funct)})
                self.assertEqual(caught.exception.code, ir.IR_UNSUPPORTED_INSTRUCTION)


class SubuOracleTests(unittest.TestCase):
    def test_oracle_matches_literal_32_bit_sign_extended_results(self):
        data, _ = subu_fixture()
        entry, words, info = spike.parse_elf(data)
        state = spike.normalize_state(spike.execute_oracle(entry, words))
        regs = state["registers"]
        self.assertEqual(info["instruction_count"], 20)
        self.assertEqual(regs[ZERO], 0)
        # 0x80000000 - 0x7FFFFFFF = 1 in 32-bit modulo arithmetic; a 64-bit
        # subtraction of the same modeled registers would give 0xFFFFFFFF00000001.
        self.assertEqual(regs[T0], 1)
        self.assertEqual(regs[T1], 1)
        # 0x80000000 - 0x00000001 = 0x7FFFFFFF, sign-extended to a positive value;
        # a 64-bit subtraction would give 0xFFFFFFFF7FFFFFFF.
        self.assertEqual(regs[T2], 0x000000007FFFFFFF)
        self.assertEqual(regs[T3], 0x000000007FFFFFFF)
        self.assertEqual(regs[T4], UINT64_MAX)
        self.assertEqual(regs[T5], 0x000000007FFFFFFE)
        self.assertEqual(regs[S0], 0xFFFFFFFF80000001)
        self.assertEqual(regs[S1], 0)
        # 0 - 0x80000000 = 0x80000000, sign-extended; a 64-bit subtraction of the
        # modeled registers would give 0x0000000080000000.
        self.assertEqual(regs[S2], 0xFFFFFFFF80000000)
        self.assertEqual(regs[A0], 5)
        self.assertEqual(regs[A1], 2)
        self.assertEqual(regs[V0], 42)
        self.assertEqual(state["memory"], [])
        self.assertEqual(state["pc"], spike.RETURN_SENTINEL)
        self.assertEqual(state["trace"], [BASE + index * 4 for index in range(20)])


class SubuLoweringTests(unittest.TestCase):
    def test_native_lowering_matches_oracle_and_literals(self):
        if compiler_available() is None:
            self.skipTest("No C++ compiler available for the SUBU native differential")
        data, result = subu_fixture()
        entry, words, _ = spike.parse_elf(data)
        oracle = spike.normalize_state(spike.execute_oracle(entry, words))
        source_text = lower.lower_to_cpp(result)
        with tempfile.TemporaryDirectory() as temp:
            out_dir = Path(temp)
            source = out_dir / "generated.cpp"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            exe = out_dir / ("rptp-subu.exe" if os.name == "nt" else "rptp-subu")
            command = spike.compile_generated(source, exe, "auto")
            proc = subprocess.run([str(exe)], cwd=out_dir, text=True, capture_output=True, check=False)
        self.assertEqual(proc.returncode, 0, msg=f"{command}\n{proc.stdout}\n{proc.stderr}")
        self.assertEqual(proc.stderr, "")
        native = json.loads(proc.stdout)
        self.assertEqual(native, oracle)
        self.assertEqual(native["registers"][T0], 1)
        self.assertEqual(native["registers"][T2], 0x000000007FFFFFFF)
        self.assertEqual(native["registers"][T4], UINT64_MAX)
        self.assertEqual(native["registers"][S2], 0xFFFFFFFF80000000)
        self.assertEqual(native["registers"][ZERO], 0)

    def test_native_helper_subtracts_low_words_and_sign_extends(self):
        if compiler_available() is None:
            self.skipTest("No C++ compiler available for the SUBU boundary differential")
        result = ir.analyze_words(BASE, {BASE: spike.encode_r(T0, T1, T2, 0, SUBU)})
        source_text = lower.lower_to_cpp(result)
        harness_text = f'''#define main rptp_generated_entry
#include "generated.cpp"
#undef main

int main() {{
    const auto sub = [](std::uint64_t lhs, std::uint64_t rhs) {{
        State state;
        state.pc = 0x{BASE:08X}u;
        state.registers[{T0}] = lhs;
        state.registers[{T1}] = rhs;
        run_generated(state);
        return state.registers[{T2}];
    }};
    std::cout << std::hex << sub(0ull, 1ull) << ' '
              << sub(0x0000000100000001ull, 1ull) << ' '
              << sub(0xFFFFFFFF80000000ull, 1ull) << ' '
              << sub(0x0123456789ABCDEFull, 0x0FEDCBA987654321ull) << '\\n';
    return 0;
}}
'''
        with tempfile.TemporaryDirectory() as temp:
            out_dir = Path(temp)
            source = out_dir / "generated.cpp"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            harness = out_dir / "harness.cpp"
            harness.write_text(harness_text, encoding="utf-8", newline="\n")
            exe = out_dir / ("rptp-subu-boundary.exe" if os.name == "nt" else "rptp-subu-boundary")
            command = spike.compile_generated(harness, exe, "auto")
            proc = subprocess.run([str(exe)], cwd=out_dir, text=True, capture_output=True, check=False)
        self.assertEqual(proc.returncode, 0, msg=f"{command}\n{proc.stdout}\n{proc.stderr}")
        self.assertEqual(proc.stderr, "")
        self.assertEqual(
            proc.stdout.split(),
            [
                "ffffffffffffffff",  # 0 - 1 wraps in 32-bit modulo arithmetic
                "0",                 # only the low words are subtracted
                "7fffffff",          # 0x80000000 - 1 stays positive
                "2468ace",           # 0x89ABCDEF - 0x87654321
            ],
        )

    def test_lowering_is_deterministic_and_ignores_raw_words(self):
        _, result = subu_fixture()
        source = lower.lower_to_cpp(result)
        mutated = replace(
            result,
            instructions=tuple(replace(item, word=0) for item in result.instructions),
        )
        self.assertEqual(source, lower.lower_to_cpp(mutated))
        self.assertIn("subu32(", source)
        self.assertNotIn("\r", source)
        self.assertTrue(source.endswith("\n"))

    def test_lowering_omits_helper_when_no_subu_is_present(self):
        result = ir.analyze_words(BASE, {BASE: spike.encode_r(T0, T1, T2, 0, 0x21)})
        self.assertNotIn("subu32(", lower.lower_to_cpp(result))

    def test_lowering_rejects_malformed_metadata(self):
        _, result = subu_fixture()
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
                malformed = replace_instruction(result, SUBU_PC, **fields)
                with self.assertRaises(lower.LoweringError) as caught:
                    lower.lower_to_cpp(malformed)
                self.assertEqual(caught.exception.code, code)


if __name__ == "__main__":
    unittest.main(verbosity=2)
