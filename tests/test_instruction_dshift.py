# SPDX-License-Identifier: GPL-3.0-or-later
"""Doubleword shift semantics on the canonical RPTP path.

The nine R5900 doubleword shift forms (DSLL, DSLL32, DSLLV, DSRA, DSRA32,
DSRAV, DSRL, DSRL32, DSRLV) operate on the 64-bit value in GPR[rt].  The
immediate forms shift by ``sa`` (DSLL/DSRA/DSRL) or ``sa + 32`` (the ``32``
variants); the variable forms take ``GPR[rs]`` bits 5..0 as the shift amount
and therefore mask it to 0..63.  Results are sign-extended to the 128-bit
register model, and arithmetic right shifts replicate the sign bit.

Every fixture is an original synthetic ELF assembled in memory.  Encodings and
semantics come from the permitted MIPS64 reference, RPTP-REF-015 pages 168-176
(DSLL 168, DSLL32 169, DSLLV 170, DSRA 171, DSRA32 172, DSRAV 173, DSRL 174,
DSRL32 175, DSRLV 176).
"""
from __future__ import annotations

import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.rptp import codegen, ir, isa, native, oracle
from tools.rptp.cfg import discover_program
from tools.rptp.elf import parse_elf_bytes
from tools.rptp.fixtures import (
    CODE_BASE,
    DATA_BASE,
    FP,
    K0,
    K1,
    RA,
    S0,
    S1,
    S2,
    S3,
    S4,
    S5,
    S6,
    T0,
    T1,
    T2,
    T3,
    T4,
    T5,
    T6,
    T7,
    ZERO,
    Assembler,
    build_elf,
    encode_r,
)
from tools.rptp.oracle import RETURN_SENTINEL

MASK64 = 0xFFFFFFFFFFFFFFFF
MAX_STEPS = 100_000

SOURCE_A = 0x8000000000000001
SOURCE_B = 0x0000000080000000
SOURCE_C = 0xFFFFFFFF80000000
DATA = struct.pack("<QQQ", SOURCE_A, SOURCE_B, SOURCE_C) + bytes(8)

# mnemonic, funct, destination, source register, shift amount, expected low 64 bits
IMMEDIATE_FORMS = (
    ("dsll", 0x38, T7, T1, 1, 0x0000000000000002),
    ("dsll32", 0x3C, S0, T1, 0, 0x0000000100000000),
    ("dsrl", 0x3A, S2, T1, 1, 0x4000000000000000),
    ("dsrl32", 0x3E, S3, T1, 0, 0x0000000080000000),
    ("dsra", 0x3B, S5, T1, 1, 0xC000000000000000),
    ("dsra32", 0x3F, S6, T3, 0, 0xFFFFFFFFFFFFFFFF),
)

VARIABLE_FORMS = (
    ("dsllv", 0x14, S1, T1, T5, 0x0000000200000000),
    ("dsrlv", 0x16, S4, T1, T6, 0x4000000000000000),
    ("dsrav", 0x17, K0, T3, T4, 0xFFFFFFFFC0000000),
)

EXPECTED = {
    T7: 0x0000000000000002,
    S0: 0x0000000100000000,
    S1: 0x0000000200000000,
    S2: 0x4000000000000000,
    S3: 0x0000000080000000,
    S4: 0x4000000000000000,
    S5: 0xC000000000000000,
    S6: 0xFFFFFFFFFFFFFFFF,
    K0: 0xFFFFFFFFC0000000,
    K1: 0x0000000100000000,
    FP: 0xC000000000000000,
}


def pair64(value: int) -> list[int]:
    value &= MASK64
    return [value, MASK64 if value & (1 << 63) else 0]


def build_assembler() -> Assembler:
    asm = Assembler()
    asm.lui(T0, DATA_BASE >> 16)
    asm.ld(T1, 0, T0)
    asm.ld(T2, 8, T0)
    asm.ld(T3, 16, T0)
    asm.addiu(T4, ZERO, 1)
    asm.addiu(T5, ZERO, 33)
    asm.addiu(T6, ZERO, 65)
    for mnemonic, _funct, dst, src, amount, _expected in IMMEDIATE_FORMS:
        getattr(asm, mnemonic)(dst, src, amount)
    for mnemonic, _funct, dst, src, amount_reg, _expected in VARIABLE_FORMS:
        getattr(asm, mnemonic)(dst, src, amount_reg)
    asm.dsllv(K1, T2, T4)
    asm.sd(S5, 24, T0)
    asm.ld(FP, 24, T0)
    asm.jr(RA)
    asm.nop()
    return asm


def build_program():
    return discover_program(parse_elf_bytes(build_elf(build_assembler().resolve(), DATA)))


class DoublewordShiftDecodeTests(unittest.TestCase):
    def test_immediate_forms_decode_with_zero_rs(self) -> None:
        for mnemonic, funct, destination, source, amount, _expected in IMMEDIATE_FORMS:
            with self.subTest(mnemonic=mnemonic):
                word = encode_r(funct, destination, ZERO, source, amount)
                instruction = isa.decode_instruction(word, CODE_BASE)
                self.assertEqual(mnemonic, instruction.mnemonic)
                self.assertTrue(instruction.supported)
                self.assertTrue(instruction.valid)
                self.assertEqual(isa.GENERIC, instruction.verification)
                self.assertEqual((0, source, destination, amount),
                                 (instruction.rs, instruction.rt,
                                  instruction.rd, instruction.shamt))

    def test_variable_forms_decode_with_zero_reserved_shamt(self) -> None:
        for mnemonic, funct, destination, source, amount_reg, _expected in VARIABLE_FORMS:
            with self.subTest(mnemonic=mnemonic):
                word = encode_r(funct, destination, amount_reg, source)
                instruction = isa.decode_instruction(word, CODE_BASE)
                self.assertEqual(mnemonic, instruction.mnemonic)
                self.assertTrue(instruction.supported)
                self.assertTrue(instruction.valid)
                self.assertEqual(isa.GENERIC, instruction.verification)
                self.assertEqual((amount_reg, source, destination, 0),
                                 (instruction.rs, instruction.rt,
                                  instruction.rd, instruction.shamt))

    def test_cfg_marks_the_family_supported(self) -> None:
        program = build_program()
        self.assertEqual([], program.unsupported_blocks())
        mnemonics = {
            instruction.mnemonic
            for instruction in program.blocks[CODE_BASE].instructions
        }
        expected = {form[0] for form in IMMEDIATE_FORMS} | {
            form[0] for form in VARIABLE_FORMS
        }
        self.assertTrue(expected <= mnemonics)


class DoublewordShiftIrTests(unittest.TestCase):
    def setUp(self) -> None:
        self.program = build_program()
        self.result = ir.lower_program(self.program)
        self.assertEqual([], self.result.errors)
        self.ops = {
            op.pc: op
            for block in self.result.blocks.values()
            for op in block.ops
        }
        self.instructions = list(self.program.blocks[CODE_BASE].instructions)

    def _instruction(self, mnemonic: str, destination: int):
        matches = [
            instruction for instruction in self.instructions
            if instruction.mnemonic == mnemonic and instruction.rd == destination
        ]
        self.assertEqual(1, len(matches), f"{mnemonic} to register {destination}")
        return matches[0]

    def test_immediate_forms_lower_to_64_bit_shifts(self) -> None:
        for mnemonic, _funct, destination, source, amount, _expected in IMMEDIATE_FORMS:
            with self.subTest(mnemonic=mnemonic):
                instruction = self._instruction(mnemonic, destination)
                op = self.ops[instruction.pc]
                self.assertEqual("shift", op.kind)
                self.assertEqual(destination, op.dst)
                self.assertEqual(source, op.a)
                self.assertEqual(64, op.width)
                expected_amount = amount + (32 if mnemonic.endswith("32") else 0)
                self.assertEqual(expected_amount, op.imm)

    def test_variable_forms_lower_to_register_controlled_shifts(self) -> None:
        for mnemonic, _funct, destination, source, amount_reg, _expected in VARIABLE_FORMS:
            with self.subTest(mnemonic=mnemonic):
                instruction = self._instruction(mnemonic, destination)
                op = self.ops[instruction.pc]
                self.assertEqual("shift_var", op.kind)
                self.assertEqual(destination, op.dst)
                self.assertEqual(source, op.a)
                self.assertEqual(amount_reg, op.b)
                self.assertEqual(64, op.width)


class DoublewordShiftOracleTests(unittest.TestCase):
    def test_oracle_produces_the_literal_64_bit_results(self) -> None:
        state = oracle.run_oracle(build_program(), max_steps=MAX_STEPS)
        self.assertTrue(state["halted"])
        self.assertEqual("pc_outside_code", state["reason"])
        self.assertEqual(RETURN_SENTINEL, state["pc"])
        self.assertEqual(pair64(SOURCE_A), state["registers"][T1])
        self.assertEqual(pair64(SOURCE_B), state["registers"][T2])
        self.assertEqual(pair64(SOURCE_C), state["registers"][T3])
        self.assertEqual(pair64(0), state["registers"][ZERO])
        for register, value in EXPECTED.items():
            self.assertEqual(pair64(value), state["registers"][register],
                             f"register {register}")
        stored = struct.pack("<Q", 0xC000000000000000)
        self.assertEqual(
            [[DATA_BASE + 24 + offset, byte] for offset, byte in enumerate(stored)],
            state["memory"],
        )


class DoublewordShiftCodegenTests(unittest.TestCase):
    def test_generated_source_is_deterministic_and_sign_extends(self) -> None:
        program = build_program()
        result = ir.lower_program(program)
        self.assertEqual([], result.errors)
        first = codegen.generate(program, result)
        second = codegen.generate(program, result)
        self.assertEqual(first.source, second.source)
        self.assertEqual(first.source_sha256, second.source_sha256)
        self.assertEqual(first.memory_blob, second.memory_blob)
        self.assertIn("rptp::sext64", first.source)
        self.assertNotIn("\r", first.source)
        self.assertTrue(first.source.endswith("\n"))

    def test_native_differential_matches_oracle(self) -> None:
        try:
            native.find_msvc()
        except native.HarnessError as exc:
            self.skipTest(f"MSVC is genuinely unavailable: {exc}")
        image = parse_elf_bytes(build_elf(build_assembler().resolve(), DATA))
        program = discover_program(image)
        expected = oracle.run_oracle(program, max_steps=MAX_STEPS)
        actual = native.run_differential(image, max_steps=MAX_STEPS)
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
