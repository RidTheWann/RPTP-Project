# SPDX-License-Identifier: GPL-3.0-or-later
"""Focused synthetic tests for the SUBU register operation.

Model under test (RPTP test definition, see docs/INSTRUCTION_CATALOG.md): subtract
the low 32 bits of ``rt`` from the low 32 bits of ``rs`` modulo 2**32, then
sign-extend the 32-bit difference into the 64-bit register array. No overflow
trap exists; a write to ``$zero`` is discarded. Expected values below are literal
constants worked out by hand, not recomputed with the implementation's logic.
"""
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
ZERO = spike.ZERO
V0 = spike.V0
A0 = spike.A0
T0 = spike.T0
T1 = spike.T1
T2 = spike.T2
T3 = spike.T3
T4 = spike.T4
T5 = 13
T6 = 14
T7 = 15
T8 = 24
S0 = spike.S0
S1 = spike.S1
S2 = spike.S2
S3 = spike.S3
S4 = spike.S4
S5 = 21
S6 = 22
RA = spike.RA

SUBU = 0x23
SUB = 0x22
UNSUPPORTED_SPECIAL = 0x2C

UINT64_MASK = 0xFFFFFFFFFFFFFFFF
FIRST_SUBU_PC = BASE + 4 * 4
INSTRUCTION_COUNT = 24


def nop_word() -> int:
    return spike.encode_r(ZERO, ZERO, ZERO, 0, 0x00)


def jr_ra_word() -> int:
    return spike.encode_r(RA, ZERO, ZERO, 0, 0x08)


def subu_fixture_rows() -> list[tuple[int, str, int]]:
    rows = [
        ("set_five", spike.encode_i(0x09, ZERO, T0, 5)),
        ("set_three", spike.encode_i(0x09, ZERO, T1, 3)),
        ("set_one", spike.encode_i(0x09, ZERO, T2, 1)),
        ("set_minus_one", spike.encode_i(0x09, ZERO, T3, -1)),
        ("subu_positive", spike.encode_r(T0, T1, S0, 0, SUBU)),
        ("subu_negative", spike.encode_r(T1, T0, S1, 0, SUBU)),
        ("subu_equal_sources", spike.encode_r(T0, T0, S2, 0, SUBU)),
        ("subu_zero_minus_one", spike.encode_r(ZERO, T2, S3, 0, SUBU)),
        ("subu_minus_one_minus_zero", spike.encode_r(T3, ZERO, T4, 0, SUBU)),
        ("set_min32", spike.encode_i(0x0F, ZERO, T5, 0x8000)),
        ("subu_min32_minus_one", spike.encode_r(T5, T2, T6, 0, SUBU)),
        ("set_max32_high", spike.encode_i(0x0F, ZERO, T7, 0x7FFF)),
        ("set_max32", spike.encode_i(0x0D, T7, T7, 0xFFFF)),
        ("subu_max32_minus_minus_one", spike.encode_r(T7, T3, S4, 0, SUBU)),
        ("subu_max32_minus_min32", spike.encode_r(T7, T5, A0, 0, SUBU)),
        ("set_zero_extended_min32", spike.encode_i(0x19, T7, T8, 1)),
        ("subu_ignores_upper_bits_a", spike.encode_r(T8, T5, S5, 0, SUBU)),
        ("subu_ignores_upper_bits_b", spike.encode_r(T5, T8, S6, 0, SUBU)),
        ("subu_destination_aliases_first_source", spike.encode_r(T0, T1, T0, 0, SUBU)),
        ("subu_destination_aliases_second_source", spike.encode_r(T0, T1, T1, 0, SUBU)),
        ("subu_zero_destination", spike.encode_r(T2, T3, ZERO, 0, SUBU)),
        ("return_value", spike.encode_i(0x09, ZERO, V0, 42)),
        ("return_from_main", jr_ra_word()),
        ("main_return_delay_slot", nop_word()),
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
    def test_decode_subu_encoding(self):
        word = spike.encode_r(T0, T1, T2, 0, SUBU)
        instruction = spike.decode_instruction(BASE, word)

        self.assertEqual(word >> 26, 0)
        self.assertEqual((word >> 6) & 0x1F, 0)
        self.assertEqual(word & 0x3F, 0x23)
        self.assertEqual(instruction["op"], "subu")
        self.assertEqual((instruction["rs"], instruction["rt"], instruction["rd"]), (T0, T1, T2))

    def test_decode_rejects_nonzero_shamt(self):
        with self.assertRaisesRegex(ValueError, "Unsupported SPECIAL"):
            spike.decode_instruction(BASE, spike.encode_r(T0, T1, T2, 1, SUBU))

    def test_decode_keeps_trapping_sub_unsupported(self):
        # SUB (funct 0x22) traps on signed overflow; that exception is not modeled,
        # so it must keep failing loudly instead of aliasing to SUBU.
        with self.assertRaisesRegex(ValueError, "Unsupported SPECIAL"):
            spike.decode_instruction(BASE, spike.encode_r(T0, T1, T2, 0, SUB))

    def test_decode_rejects_unsupported_special_function_and_opcode(self):
        with self.assertRaisesRegex(ValueError, "Unsupported SPECIAL"):
            spike.decode_instruction(BASE, spike.encode_r(T0, T1, T2, 0, UNSUPPORTED_SPECIAL))
        with self.assertRaisesRegex(ValueError, "Unsupported opcode 0x10"):
            spike.decode_instruction(BASE, spike.encode_i(0x10, T0, T1, 0))


class SubuIrTests(unittest.TestCase):
    def test_ir_marks_subu_operands_destinations_and_fallthrough(self):
        words = {
            BASE: spike.encode_r(T0, T1, T2, 0, SUBU),
            BASE + 4: spike.encode_r(S0, S1, ZERO, 0, SUBU),
        }
        result = ir.analyze_words(BASE, words)
        by_pc = {instruction.pc: instruction for instruction in result.instructions}

        instruction = by_pc[BASE]
        self.assertEqual(instruction.op, "subu")
        self.assertEqual(instruction.word, words[BASE])
        self.assertEqual((instruction.rs, instruction.rt, instruction.rd), (T0, T1, T2))
        self.assertEqual(instruction.destination_register, T2)
        self.assertEqual(instruction.control, ir.FALLTHROUGH)
        self.assertIsNone(instruction.immediate)
        self.assertIsNone(instruction.immediate_kind)

        zero_destination = by_pc[BASE + 4]
        self.assertEqual(zero_destination.op, "subu")
        self.assertIsNone(zero_destination.destination_register)

    def test_ir_rejects_nonzero_shamt_fail_closed(self):
        with self.assertRaises(ir.AnalysisError) as caught:
            ir.analyze_words(BASE, {BASE: spike.encode_r(T0, T1, T2, 1, SUBU)})

        self.assertEqual(caught.exception.code, ir.IR_UNSUPPORTED_INSTRUCTION)
        self.assertIn("Unsupported SPECIAL", str(caught.exception))

    def test_ir_rejects_trapping_sub_fail_closed(self):
        with self.assertRaises(ir.AnalysisError) as caught:
            ir.analyze_words(BASE, {BASE: spike.encode_r(T0, T1, T2, 0, SUB)})

        self.assertEqual(caught.exception.code, ir.IR_UNSUPPORTED_INSTRUCTION)


class SubuOracleTests(unittest.TestCase):
    def test_oracle_subtracts_low_32_bits_and_sign_extends_deterministically(self):
        data, _ = subu_fixture()
        entry, words, info = spike.parse_elf(data)
        first = spike.normalize_state(spike.execute_oracle(entry, words))
        second = spike.normalize_state(spike.execute_oracle(entry, words))
        registers = first["registers"]

        self.assertEqual(info["instruction_count"], INSTRUCTION_COUNT)
        self.assertEqual(first, second)
        self.assertEqual(registers[ZERO], 0)
        # Inputs that were only read.
        self.assertEqual(registers[T2], 1)
        self.assertEqual(registers[T3], UINT64_MASK)
        # 5 - 3, 3 - 5, x - x.
        self.assertEqual(registers[S0], 2)
        self.assertEqual(registers[S1], 0xFFFFFFFFFFFFFFFE)
        self.assertEqual(registers[S2], 0)
        # 0 - 1 and 0xFFFFFFFF - 0: the 32-bit result is sign-extended, never zero-extended.
        self.assertEqual(registers[S3], UINT64_MASK)
        self.assertEqual(registers[T4], UINT64_MASK)
        # 0x80000000 - 1 wraps to positive 0x7FFFFFFF.
        self.assertEqual(registers[T5], 0xFFFFFFFF80000000)
        self.assertEqual(registers[T6], 0x000000007FFFFFFF)
        # 0x7FFFFFFF - 0xFFFFFFFF wraps to 0x80000000, then sign-extends.
        self.assertEqual(registers[T7], 0x000000007FFFFFFF)
        self.assertEqual(registers[S4], 0xFFFFFFFF80000000)
        # 0x7FFFFFFF - 0x80000000 wraps to 0xFFFFFFFF, then sign-extends.
        self.assertEqual(registers[A0], UINT64_MASK)
        # Same low 32 bits, different upper 32 bits: a 64-bit subtract would be nonzero.
        self.assertEqual(registers[T8], 0x0000000080000000)
        self.assertEqual(registers[S5], 0)
        self.assertEqual(registers[S6], 0)
        # Destination aliasing: T0 = 5 - 3, then T1 = 2 - 3.
        self.assertEqual(registers[T0], 2)
        self.assertEqual(registers[T1], UINT64_MASK)
        self.assertEqual(registers[V0], 42)
        self.assertEqual(first["memory"], [])
        self.assertEqual(first["pc"], spike.RETURN_SENTINEL)
        self.assertTrue(first["halted"])
        self.assertEqual(first["trace"], [BASE + index * 4 for index in range(INSTRUCTION_COUNT)])


class SubuLoweringTests(unittest.TestCase):
    def test_subu_native_state_matches_oracle(self):
        candidate = compiler_available()
        if candidate is None:
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
        self.assertEqual(native["registers"][S1], 0xFFFFFFFFFFFFFFFE)
        self.assertEqual(native["registers"][T6], 0x000000007FFFFFFF)
        self.assertEqual(native["registers"][S4], 0xFFFFFFFF80000000)
        self.assertEqual(native["registers"][S5], 0)
        self.assertEqual(native["registers"][S6], 0)
        self.assertEqual(native["memory"], [])
        self.assertEqual(native["pc"], spike.RETURN_SENTINEL)
        self.assertTrue(native["halted"])
        self.assertEqual(native["trace"], oracle["trace"])

    def test_subu_native_helper_ignores_upper_32_bits(self):
        candidate = compiler_available()
        if candidate is None:
            self.skipTest("No C++ compiler available for the SUBU boundary differential")

        result = ir.analyze_words(BASE, {BASE: spike.encode_r(T0, T1, T2, 0, SUBU)})
        source_text = lower.lower_to_cpp(result)
        # (rs, rt, expected rd). The synthetic encoder cannot materialize arbitrary
        # 64-bit constants, so the harness seeds the generated state directly.
        cases = (
            (0x0000000080000000, 0xFFFFFFFF80000000, 0x0000000000000000),
            (0xFFFFFFFF80000000, 0x0000000080000000, 0x0000000000000000),
            (0x0000000100000000, 0x0000000000000001, 0xFFFFFFFFFFFFFFFF),
            (0x0000000000000000, 0x0000000080000000, 0xFFFFFFFF80000000),
            (0x123456789ABCDEF0, 0xFEDCBA9876543210, 0x000000002468ACE0),
            (0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF, 0x0000000000000000),
        )
        blocks = []
        for index, (lhs, rhs, _) in enumerate(cases):
            blocks.append(
                f"    State case{index};\n"
                f"    case{index}.pc = 0x{BASE:08X}u;\n"
                f"    case{index}.registers[{T0}] = 0x{lhs:016X}ull;\n"
                f"    case{index}.registers[{T1}] = 0x{rhs:016X}ull;\n"
                f"    run_generated(case{index});\n"
                f"    std::cout << case{index}.registers[{T2}] << ' ';\n"
            )
        harness_text = (
            '#define main rptp_generated_entry\n#include "generated.cpp"\n#undef main\n\n'
            "int main() {\n" + "".join(blocks) + "    std::cout << '\\n';\n    return 0;\n}\n"
        )

        with tempfile.TemporaryDirectory() as temp:
            out_dir = Path(temp)
            (out_dir / "generated.cpp").write_text(source_text, encoding="utf-8", newline="\n")
            harness = out_dir / "harness.cpp"
            harness.write_text(harness_text, encoding="utf-8", newline="\n")
            exe = out_dir / ("rptp-subu-boundary.exe" if os.name == "nt" else "rptp-subu-boundary")
            command = spike.compile_generated(harness, exe, "auto")
            proc = subprocess.run([str(exe)], cwd=out_dir, text=True, capture_output=True, check=False)

        self.assertEqual(proc.returncode, 0, msg=f"{command}\n{proc.stdout}\n{proc.stderr}")
        self.assertEqual(proc.stderr, "")
        self.assertEqual(proc.stdout.split(), [str(expected) for _, _, expected in cases])

    def test_subu_lowering_is_deterministic_and_ignores_raw_words(self):
        _, result = subu_fixture()
        source = lower.lower_to_cpp(result)
        changed_words = replace(
            result,
            instructions=tuple(replace(instruction, word=0) for instruction in result.instructions),
        )

        self.assertEqual(source, lower.lower_to_cpp(result))
        self.assertEqual(source, lower.lower_to_cpp(changed_words))
        self.assertNotIn("\r", source)
        self.assertTrue(source.endswith("\n"))

    def test_subu_lowering_rejects_malformed_metadata(self):
        _, result = subu_fixture()
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
                malformed = replace_instruction(result, FIRST_SUBU_PC, **fields)
                with self.assertRaises(lower.LoweringError) as caught:
                    lower.lower_to_cpp(malformed)
                self.assertEqual(caught.exception.code, expected_code)

    def test_subu_lowering_rejects_unsupported_operation(self):
        _, result = subu_fixture()
        malformed = replace_instruction(result, FIRST_SUBU_PC, op="sub")

        with self.assertRaises(lower.LoweringError) as caught:
            lower.lower_to_cpp(malformed)
        self.assertEqual(caught.exception.code, lower.LOWER_UNSUPPORTED_OP)


if __name__ == "__main__":
    unittest.main(verbosity=2)
