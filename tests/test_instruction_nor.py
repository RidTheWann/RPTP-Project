# SPDX-License-Identifier: GPL-3.0-or-later
"""Focused synthetic tests for the NOR register operation."""
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


spike = load_module("rptp_gate0_spike_nor", "tools/rptp_gate0_spike.py")
ir = load_module("rptp_ir_nor", "tools/rptp_ir.py")
lower = load_module("rptp_lower_nor", "tools/rptp_lower.py")

BASE = spike.BASE
ZERO = spike.ZERO
V0 = spike.V0
T0 = spike.T0
T1 = spike.T1
T2 = spike.T2
T3 = spike.T3
T5 = 13
T6 = 14
S0 = spike.S0
S1 = spike.S1
S2 = spike.S2
S3 = spike.S3
RA = spike.RA

NOR = 0x27
SLTU = 0x2B

UINT64_MASK = 0xFFFFFFFFFFFFFFFF


def nop_word() -> int:
    return spike.encode_r(ZERO, ZERO, ZERO, 0, 0x00)


def jr_ra_word() -> int:
    return spike.encode_r(RA, ZERO, ZERO, 0, 0x08)


def nor_fixture_rows() -> list[tuple[int, str, int]]:
    rows = [
        ("set_first_zero", spike.encode_i(0x0F, ZERO, T0, 0x0000)),
        ("set_second_zero", spike.encode_i(0x0F, ZERO, T1, 0x0000)),
        ("nor_zero_with_zero", spike.encode_r(T0, T1, T2, 0, NOR)),
        ("set_all_ones", spike.encode_i(0x09, ZERO, T6, -1)),
        ("nor_all_ones_with_zero", spike.encode_r(T6, T1, T3, 0, NOR)),
        ("set_high_left", spike.encode_i(0x0F, ZERO, S0, 0xF0F0)),
        ("set_high_right", spike.encode_i(0x0F, ZERO, S1, 0x0FF0)),
        ("nor_high_bits", spike.encode_r(S0, S1, S2, 0, NOR)),
        ("nor_identical_sources", spike.encode_r(S0, S0, S3, 0, NOR)),
        ("nor_all_ones_with_nonzero", spike.encode_r(T6, S1, T5, 0, NOR)),
        ("nor_destination_aliases_first_source", spike.encode_r(S0, S1, S0, 0, NOR)),
        ("nor_destination_aliases_second_source", spike.encode_r(S0, S1, S1, 0, NOR)),
        ("nor_zero_destination", spike.encode_r(S2, S3, ZERO, 0, NOR)),
        ("return_value", spike.encode_i(0x09, ZERO, V0, 42)),
        ("return_from_main", jr_ra_word()),
        ("main_return_delay_slot", nop_word()),
    ]
    return [(BASE + index * 4, name, word) for index, (name, word) in enumerate(rows)]


def nor_fixture():
    data = spike.build_elf_from_rows(nor_fixture_rows())
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


class NorDecodeTests(unittest.TestCase):
    def test_decode_nor_encoding(self):
        word = spike.encode_r(T0, T1, T2, 0, NOR)
        instruction = spike.decode_instruction(BASE, word)

        self.assertEqual(word >> 26, 0)
        self.assertEqual((word >> 6) & 0x1F, 0)
        self.assertEqual(word & 0x3F, NOR)
        self.assertEqual(instruction["op"], "nor")
        self.assertEqual((instruction["rs"], instruction["rt"], instruction["rd"]), (T0, T1, T2))

    def test_decode_rejects_nonzero_shamt(self):
        with self.assertRaisesRegex(ValueError, "Unsupported SPECIAL"):
            spike.decode_instruction(BASE, spike.encode_r(T0, T1, T2, 1, NOR))

    def test_decode_rejects_unsupported_special_function_and_opcode(self):
        with self.assertRaisesRegex(ValueError, "Unsupported SPECIAL"):
            spike.decode_instruction(BASE, spike.encode_r(T0, T1, T2, 0, SLTU))
        with self.assertRaisesRegex(ValueError, "Unsupported opcode 0x10"):
            spike.decode_instruction(BASE, spike.encode_i(0x10, T0, T1, 0))


class NorIrTests(unittest.TestCase):
    def test_ir_marks_nor_operands_destinations_and_fallthrough(self):
        words = {
            BASE: spike.encode_r(T0, T1, T2, 0, NOR),
            BASE + 4: spike.encode_r(S0, S1, ZERO, 0, NOR),
        }
        result = ir.analyze_words(BASE, words)
        by_pc = {instruction.pc: instruction for instruction in result.instructions}

        instruction = by_pc[BASE]
        self.assertEqual(instruction.op, "nor")
        self.assertEqual(instruction.word, words[BASE])
        self.assertEqual((instruction.rs, instruction.rt, instruction.rd), (T0, T1, T2))
        self.assertEqual(instruction.destination_register, T2)
        self.assertEqual(instruction.control, ir.FALLTHROUGH)
        self.assertIsNone(instruction.immediate)
        self.assertIsNone(instruction.immediate_kind)

        zero_destination = by_pc[BASE + 4]
        self.assertEqual(zero_destination.op, "nor")
        self.assertIsNone(zero_destination.destination_register)

    def test_ir_rejects_nonzero_shamt_fail_closed(self):
        with self.assertRaises(ir.AnalysisError) as caught:
            ir.analyze_words(BASE, {BASE: spike.encode_r(T0, T1, T2, 1, NOR)})

        self.assertEqual(caught.exception.code, ir.IR_UNSUPPORTED_INSTRUCTION)
        self.assertIn("Unsupported SPECIAL", str(caught.exception))


class NorOracleTests(unittest.TestCase):
    def test_oracle_computes_full_64_bit_results_deterministically(self):
        data, _ = nor_fixture()
        entry, words, info = spike.parse_elf(data)
        first = spike.normalize_state(spike.execute_oracle(entry, words))
        second = spike.normalize_state(spike.execute_oracle(entry, words))
        registers = first["registers"]

        self.assertEqual(info["instruction_count"], 16)
        self.assertEqual(first, second)
        self.assertEqual(registers[ZERO], 0)
        self.assertEqual(registers[T0], 0)
        self.assertEqual(registers[T1], 0)
        self.assertEqual(registers[T2], UINT64_MASK)
        self.assertEqual(registers[T3], 0)
        self.assertEqual(registers[T5], 0)
        self.assertEqual(registers[T6], UINT64_MASK)
        self.assertEqual(registers[S0], 0x00000000000FFFFF)
        self.assertEqual(registers[S1], 0xFFFFFFFFF0000000)
        self.assertEqual(registers[S2], 0x00000000000FFFFF)
        self.assertEqual(registers[S3], 0x000000000F0FFFFF)
        self.assertEqual(registers[V0], 42)
        self.assertEqual(first["memory"], [])
        self.assertEqual(first["pc"], spike.RETURN_SENTINEL)
        self.assertTrue(first["halted"])
        self.assertEqual(first["trace"], [BASE + index * 4 for index in range(16)])


class NorLoweringTests(unittest.TestCase):
    def test_nor_native_state_matches_oracle(self):
        candidate = compiler_available()
        if candidate is None:
            self.skipTest("No C++ compiler available for the NOR native differential")

        data, result = nor_fixture()
        entry, words, _ = spike.parse_elf(data)
        oracle = spike.normalize_state(spike.execute_oracle(entry, words))
        source_text = lower.lower_to_cpp(result)

        with tempfile.TemporaryDirectory() as temp:
            out_dir = Path(temp)
            source = out_dir / "generated.cpp"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            exe = out_dir / ("rptp-nor.exe" if os.name == "nt" else "rptp-nor")
            command = spike.compile_generated(source, exe, "auto")
            proc = subprocess.run([str(exe)], cwd=out_dir, text=True, capture_output=True, check=False)

        self.assertEqual(proc.returncode, 0, msg=f"{command}\n{proc.stdout}\n{proc.stderr}")
        self.assertEqual(proc.stderr, "")
        native = json.loads(proc.stdout)
        self.assertEqual(native, oracle)
        self.assertEqual(native["registers"][T2], UINT64_MASK)
        self.assertEqual(native["registers"][S1], 0xFFFFFFFFF0000000)
        self.assertEqual(native["registers"][S3], 0x000000000F0FFFFF)
        self.assertEqual(native["memory"], [])
        self.assertEqual(native["pc"], spike.RETURN_SENTINEL)
        self.assertTrue(native["halted"])
        self.assertEqual(native["trace"], oracle["trace"])

    def test_nor_lowering_is_deterministic_and_ignores_raw_words(self):
        _, result = nor_fixture()
        source = lower.lower_to_cpp(result)
        changed_words = replace(
            result,
            instructions=tuple(replace(instruction, word=0) for instruction in result.instructions),
        )

        self.assertEqual(source, lower.lower_to_cpp(result))
        self.assertEqual(source, lower.lower_to_cpp(changed_words))
        self.assertNotIn("\r", source)
        self.assertTrue(source.endswith("\n"))

    def test_nor_lowering_rejects_malformed_metadata(self):
        _, result = nor_fixture()
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

    def test_nor_lowering_rejects_unsupported_operation(self):
        _, result = nor_fixture()
        malformed = replace_instruction(result, BASE + 8, op="sltu")

        with self.assertRaises(lower.LoweringError) as caught:
            lower.lower_to_cpp(malformed)
        self.assertEqual(caught.exception.code, lower.LOWER_UNSUPPORTED_OP)


if __name__ == "__main__":
    unittest.main(verbosity=2)
