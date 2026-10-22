# SPDX-License-Identifier: GPL-3.0-or-later
"""Focused synthetic tests for the ANDI and XORI logical immediates."""
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


spike = load_module("rptp_gate0_spike_logical", "tools/rptp_gate0_spike.py")
ir = load_module("rptp_ir_logical", "tools/rptp_ir.py")
lower = load_module("rptp_lower_logical", "tools/rptp_lower.py")

BASE = spike.BASE
ZERO = spike.ZERO
V0 = spike.V0
A0 = spike.A0
A1 = spike.A1
T0 = spike.T0
T1 = spike.T1
T2 = spike.T2
T3 = spike.T3
T4 = spike.T4
T5 = 13
T6 = 14
S0 = 16
S1 = 17
RA = spike.RA

ANDI = 0x0C
XORI = 0x0E


def nop_word() -> int:
    return spike.encode_r(ZERO, ZERO, ZERO, 0, 0x00)


def jr_ra_word() -> int:
    return spike.encode_r(RA, ZERO, ZERO, 0, 0x08)


def logical_fixture_rows() -> list[tuple[int, str, int]]:
    rows = [
        ("zero_dest_andi", spike.encode_i(ANDI, ZERO, ZERO, 0xFFFF)),
        ("zero_dest_xori", spike.encode_i(XORI, ZERO, ZERO, 0xFFFF)),
        ("set_t0", spike.encode_i(0x09, ZERO, T0, 0x0F0F)),
        ("andi_mask", spike.encode_i(ANDI, T0, T1, 0x00FF)),
        ("xori_overlap", spike.encode_i(XORI, T0, T0, 0x0FF0)),
        ("set_all_ones", spike.encode_i(0x09, ZERO, T2, -1)),
        ("andi_all_ones", spike.encode_i(ANDI, T2, T3, 0xFFFF)),
        ("xori_zero_immediate", spike.encode_i(XORI, T2, T4, 0)),
        ("andi_zero_immediate", spike.encode_i(ANDI, T2, T5, 0)),
        ("xori_high_bit", spike.encode_i(XORI, ZERO, T6, 0x8001)),
        ("andi_high_bit", spike.encode_i(ANDI, T2, S0, 0x8001)),
        ("xori_all_ones", spike.encode_i(XORI, T2, S1, 0xFFFF)),
        ("compose_ori", spike.encode_i(0x0D, ZERO, A0, 0xF000)),
        ("compose_andi", spike.encode_i(ANDI, A0, A1, 0xF00F)),
        ("compose_xori", spike.encode_i(XORI, A1, A0, 0x0FF0)),
        ("return_value", spike.encode_i(0x09, ZERO, V0, 42)),
        ("return_from_main", jr_ra_word()),
        ("main_return_delay_slot", nop_word()),
    ]
    return [(BASE + index * 4, name, word) for index, (name, word) in enumerate(rows)]


def logical_fixture():
    data = spike.build_elf_from_rows(logical_fixture_rows())
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


class LogicalDecodeTests(unittest.TestCase):
    def test_decode_andi_xori_zero_extends_immediates(self):
        andi = spike.decode_instruction(BASE, spike.encode_i(ANDI, T0, T1, 0x8001))
        xori = spike.decode_instruction(BASE, spike.encode_i(XORI, T2, T3, 0xFFFF))

        self.assertEqual(andi["op"], "andi")
        self.assertEqual((andi["rs"], andi["rt"], andi["imm"]), (T0, T1, 0x8001))
        self.assertEqual(xori["op"], "xori")
        self.assertEqual((xori["rs"], xori["rt"], xori["imm"]), (T2, T3, 0xFFFF))

    def test_unknown_logical_opcode_is_still_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unsupported opcode 0x0F"):
            spike.decode_instruction(BASE, spike.encode_i(0x0F, T0, T1, 0))


class LogicalIrTests(unittest.TestCase):
    def test_ir_marks_logical_immediates_zero16_and_records_destinations(self):
        words = {
            BASE: spike.encode_i(ANDI, T0, T1, 0x8001),
            BASE + 4: spike.encode_i(XORI, T2, T3, 0xFFFF),
            BASE + 8: spike.encode_i(ANDI, ZERO, ZERO, 0xFFFF),
        }
        result = ir.analyze_words(BASE, words)
        by_pc = {instruction.pc: instruction for instruction in result.instructions}

        andi = by_pc[BASE]
        self.assertEqual(andi.op, "andi")
        self.assertEqual(andi.word, words[BASE])
        self.assertEqual((andi.rs, andi.rt), (T0, T1))
        self.assertEqual((andi.immediate, andi.immediate_kind), (0x8001, ir.ZERO16))
        self.assertEqual(andi.destination_register, T1)
        self.assertEqual(andi.control, ir.FALLTHROUGH)

        xori = by_pc[BASE + 4]
        self.assertEqual(xori.op, "xori")
        self.assertEqual((xori.immediate, xori.immediate_kind), (0xFFFF, ir.ZERO16))
        self.assertEqual(xori.destination_register, T3)

        zero_destination = by_pc[BASE + 8]
        self.assertEqual(zero_destination.op, "andi")
        self.assertIsNone(zero_destination.destination_register)


class LogicalOracleTests(unittest.TestCase):
    def test_oracle_masks_toggles_and_zero_extends(self):
        data = spike.build_elf_from_rows(logical_fixture_rows())
        entry, words, info = spike.parse_elf(data)
        state = spike.normalize_state(spike.execute_oracle(entry, words))
        registers = state["registers"]

        self.assertEqual(info["instruction_count"], 18)
        self.assertEqual(registers[ZERO], 0)
        self.assertEqual(registers[T0], 0x00FF)
        self.assertEqual(registers[T1], 0x000F)
        self.assertEqual(registers[T2], 0xFFFFFFFFFFFFFFFF)
        self.assertEqual(registers[T3], 0x000000000000FFFF)
        self.assertEqual(registers[T4], 0x00000000FFFFFFFF)
        self.assertEqual(registers[T5], 0)
        self.assertEqual(registers[T6], 0x0000000000008001)
        self.assertEqual(registers[S0], 0x0000000000008001)
        self.assertEqual(registers[S1], 0x00000000FFFF0000)
        self.assertEqual(registers[A0], 0x000000000000FFF0)
        self.assertEqual(registers[A1], 0x000000000000F000)
        self.assertEqual(registers[V0], 42)
        self.assertEqual(state["memory"], [])
        self.assertEqual(state["pc"], spike.RETURN_SENTINEL)
        self.assertTrue(state["halted"])
        self.assertEqual(state["trace"], [BASE + index * 4 for index in range(18)])


class LogicalLoweringTests(unittest.TestCase):
    def test_generated_native_state_matches_oracle(self):
        candidate = compiler_available()
        if candidate is None:
            self.skipTest("No C++ compiler available for the ANDI/XORI native differential")

        data, result = logical_fixture()
        entry, words, _ = spike.parse_elf(data)
        oracle = spike.normalize_state(spike.execute_oracle(entry, words))
        source_text = lower.lower_to_cpp(result)

        with tempfile.TemporaryDirectory() as temp:
            out_dir = Path(temp)
            source = out_dir / "generated.cpp"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            exe = out_dir / ("rptp-logical.exe" if os.name == "nt" else "rptp-logical")
            command = spike.compile_generated(source, exe, "auto")
            proc = subprocess.run([str(exe)], cwd=out_dir, text=True, capture_output=True, check=False)

        self.assertEqual(proc.returncode, 0, msg=f"{command}\n{proc.stdout}\n{proc.stderr}")
        native = json.loads(proc.stdout)
        self.assertEqual(native, oracle)
        registers = native["registers"]
        self.assertEqual(registers[ZERO], 0)
        self.assertEqual(registers[T0], 0x00FF)
        self.assertEqual(registers[T1], 0x000F)
        self.assertEqual(registers[T2], 0xFFFFFFFFFFFFFFFF)
        self.assertEqual(registers[T3], 0xFFFF)
        self.assertEqual(registers[T4], 0xFFFFFFFF)
        self.assertEqual(registers[T5], 0)
        self.assertEqual(registers[T6], 0x8001)
        self.assertEqual(registers[S0], 0x8001)
        self.assertEqual(registers[S1], 0xFFFF0000)
        self.assertEqual(registers[A0], 0xFFF0)
        self.assertEqual(registers[A1], 0xF000)
        self.assertEqual(native["memory"], [])
        self.assertEqual(native["pc"], spike.RETURN_SENTINEL)
        self.assertTrue(native["halted"])

    def test_lowering_is_deterministic_and_ignores_raw_words(self):
        _, result = logical_fixture()
        source = lower.lower_to_cpp(result)
        changed_words = replace(
            result,
            instructions=tuple(replace(instruction, word=0) for instruction in result.instructions),
        )

        self.assertEqual(source, lower.lower_to_cpp(result))
        self.assertEqual(source, lower.lower_to_cpp(changed_words))
        self.assertNotIn("\r", source)
        self.assertTrue(source.endswith("\n"))

    def test_malformed_logical_immediate_kind_is_rejected(self):
        _, result = logical_fixture()
        malformed = replace_instruction(result, BASE + 0x0C, immediate_kind=ir.SIGNED16)

        with self.assertRaises(lower.LoweringError) as caught:
            lower.lower_to_cpp(malformed)
        self.assertEqual(caught.exception.code, lower.LOWER_MALFORMED_INSTRUCTION)

    def test_missing_logical_operand_is_rejected(self):
        _, result = logical_fixture()
        malformed = replace_instruction(result, BASE + 0x0C, rs=None)

        with self.assertRaises(lower.LoweringError) as caught:
            lower.lower_to_cpp(malformed)
        self.assertEqual(caught.exception.code, lower.LOWER_MALFORMED_INSTRUCTION)


if __name__ == "__main__":
    unittest.main(verbosity=2)
