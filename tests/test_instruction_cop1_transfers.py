# SPDX-License-Identifier: GPL-3.0-or-later
"""COP1 transfer semantics on the canonical RPTP path.

The four transfer forms move 32-bit values between general registers, the
floating-point register file and memory without performing any floating-point
arithmetic:

* ``MFC1`` moves ``FPR[fs]`` bits 31:0 into ``GPR[rt]``, sign-extended into the
  128-bit register model;
* ``MTC1`` moves ``GPR[rt]`` bits 31:0 into ``FPR[fs]``;
* ``LWC1`` loads a little-endian aligned word from memory into ``FPR[ft]``;
* ``SWC1`` stores the low word of ``FPR[ft]`` to an aligned memory address.

Encodings and field semantics come from the permitted MIPS64 reference,
RPTP-REF-015 pages 228 (LWC1), 250 (MFC1), 273 (MTC1) and 358 (SWC1).  COP1
arithmetic, CFC1/CTC1 and the branch forms remain unsupported; the model uses
a plain 32-bit FPR bank and does not model FPU exceptions, rounding or
nan/infinity behavior.  Reserved encoding bits 10:0 must be zero for MFC1 and
MTC1, and a non-zero value must fail closed.

Every fixture is an original synthetic ELF assembled in memory.
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
    RA,
    S0,
    S1,
    S3,
    S4,
    T0,
    T1,
    T2,
    T3,
    T4,
    T5,
    T6,
    T7,
    T8,
    ZERO,
    Assembler,
    build_elf,
    encode_i,
)
from tools.rptp.oracle import RETURN_SENTINEL

MASK32 = 0xFFFFFFFF
MASK64 = 0xFFFFFFFFFFFFFFFF
MAX_STEPS = 100_000

COP1 = 0x11 << 26
MFC1_FUNCTION = 0x00 << 21
MTC1_FUNCTION = 0x04 << 21
CFC1_FUNCTION = 0x02 << 21
CTC1_FUNCTION = 0x06 << 21

# Independent literal encodings for the four supported forms.
MFC1_WORD = COP1 | MFC1_FUNCTION | (T1 << 16) | (2 << 11)      # 0x44091000
MTC1_WORD = COP1 | MTC1_FUNCTION | (T1 << 16) | (3 << 11)      # 0x44891800
LWC1_WORD = (0x31 << 26) | (T0 << 21) | (2 << 16) | 0x0010     # 0xC5010010
SWC1_WORD = (0x39 << 26) | (29 << 21) | (3 << 16) | 0xFFFC     # 0xE7A3FFFC
CFC1_WORD = COP1 | CFC1_FUNCTION | (T0 << 16)                  # 0x44480000
CTC1_WORD = COP1 | CTC1_FUNCTION | (T0 << 16)                  # 0x44C80000

DATA_WORDS = (0x89ABCDEF, 0x7FFFFFFF, 0x80000000, 0x00000001)
DATA = struct.pack("<IIII", *DATA_WORDS)

EXPECTED_FPR = {
    0: 0x00001234,
    2: 0x89ABCDEF,
    3: 0x89ABCDEF,
    4: 0xFFFFFFFF,
    5: 0x7FFFFFFF,
    6: 0x80000000,
    7: 0xFFFFFFFF,
}

EXPECTED_REGISTERS = {
    T1: 0xFFFFFFFF89ABCDEF,
    T2: 0xFFFFFFFF89ABCDEF,
    T3: 0xFFFFFFFF89ABCDEF,
    T4: 0xFFFFFFFFFFFFFFFF,
    T5: 0xFFFFFFFFFFFFFFFF,
    T6: 0x000000007FFFFFFF,
    T7: 0xFFFFFFFF80000000,
    T8: 0x0000000000001234,
    S0: 0x000000007FFFFFFF,
    S1: 0xFFFFFFFF80000000,
    S3: 0x0000000000001234,
    S4: 0xFFFFFFFFFFFFFFFF,
}


def pair64(value: int) -> list[int]:
    value &= MASK64
    return [value, MASK64 if value & (1 << 63) else 0]


def build_assembler() -> Assembler:
    asm = Assembler()
    asm.lui(T0, DATA_BASE >> 16)
    asm.lwc1(2, 0, T0)
    asm.mfc1(T1, 2)
    asm.mtc1(T1, 3)
    asm.mfc1(T2, 3)
    asm.swc1(3, 4, T0)
    asm.lw(T3, 4, T0)
    asm.addiu(T4, ZERO, -1)
    asm.mtc1(T4, 4)
    asm.mfc1(T5, 4)
    asm.lui(T6, 0x7FFF)
    asm.ori(T6, T6, 0xFFFF)
    asm.mtc1(T6, 5)
    asm.mfc1(S0, 5)
    asm.lui(T7, 0x8000)
    asm.mtc1(T7, 6)
    asm.mfc1(S1, 6)
    asm.mfc1(ZERO, 4)
    asm.addiu(T8, ZERO, 0x1234)
    asm.mtc1(T8, 0)
    asm.mfc1(S3, 0)
    asm.swc1(4, 8, T0)
    asm.lwc1(7, 8, T0)
    asm.mfc1(S4, 7)
    asm.jr(RA)
    asm.nop()
    return asm


def build_program():
    return discover_program(parse_elf_bytes(build_elf(build_assembler().resolve(), DATA)))


def _small_program(asm: Assembler):
    return discover_program(parse_elf_bytes(build_elf(asm.resolve(), DATA)))


class Cop1TransferDecodeTests(unittest.TestCase):
    def test_mfc1_and_mtc1_decode_with_the_literal_fields(self) -> None:
        cases = (
            ("mfc1", MFC1_WORD, 0x00, 2),
            ("mtc1", MTC1_WORD, 0x04, 3),
        )
        for mnemonic, word, function, fs in cases:
            with self.subTest(mnemonic=mnemonic):
                instruction = isa.decode_instruction(word, CODE_BASE)
                self.assertEqual(mnemonic, instruction.mnemonic)
                self.assertTrue(instruction.supported)
                self.assertTrue(instruction.valid)
                self.assertEqual(isa.GENERIC, instruction.verification)
                self.assertEqual(function, instruction.rs)
                self.assertEqual(T1, instruction.rt)
                self.assertEqual(fs, instruction.rd)
                self.assertEqual(
                    f"{mnemonic} $t1, $f{fs}", instruction.text()
                )

    def test_lwc1_and_swc1_decode_as_supported_memory_forms(self) -> None:
        lwc1 = isa.decode_instruction(LWC1_WORD, CODE_BASE)
        self.assertEqual("lwc1", lwc1.mnemonic)
        self.assertTrue(lwc1.supported)
        self.assertTrue(lwc1.valid)
        self.assertEqual((T0, 2, 0x10), (lwc1.rs, lwc1.rt, lwc1.simm))
        self.assertEqual("lwc1 $f2, 16($t0)", lwc1.text())

        swc1 = isa.decode_instruction(SWC1_WORD, CODE_BASE)
        self.assertEqual("swc1", swc1.mnemonic)
        self.assertTrue(swc1.supported)
        self.assertTrue(swc1.valid)
        self.assertEqual((29, 3, -4), (swc1.rs, swc1.rt, swc1.simm))
        self.assertEqual("swc1 $f3, -4($sp)", swc1.text())

    def test_nonzero_reserved_bits_fail_closed(self) -> None:
        for mnemonic, base in (("mfc1", MFC1_WORD), ("mtc1", MTC1_WORD)):
            for reserved in (0x001, 0x400, 0x7FF):
                with self.subTest(mnemonic=mnemonic, reserved=reserved):
                    word = base | reserved
                    instruction = isa.decode_instruction(word, CODE_BASE)
                    self.assertEqual(mnemonic, instruction.mnemonic)
                    self.assertFalse(instruction.valid)
                    self.assertFalse(instruction.supported)
                    self.assertIn("Reserved encoding fields are non-zero.",
                                  instruction.note)

    def test_cfc1_and_ctc1_remain_unsupported_cop1(self) -> None:
        for mnemonic, word in (("cfc1", CFC1_WORD), ("ctc1", CTC1_WORD)):
            with self.subTest(mnemonic=mnemonic):
                instruction = isa.decode_instruction(word, CODE_BASE)
                self.assertEqual("cop1", instruction.mnemonic)
                self.assertEqual("cop1", instruction.cls)
                self.assertFalse(instruction.supported)
                with self.assertRaises(ir.LoweringError):
                    ir._lower_instruction(instruction)

    def test_catalog_marks_the_four_transfer_forms_supported(self) -> None:
        rows = {row["mnemonic"]: row for row in isa.catalog_rows()}
        for mnemonic in ("mfc1", "mtc1", "lwc1", "swc1"):
            with self.subTest(mnemonic=mnemonic):
                self.assertIn(mnemonic, rows)
                self.assertTrue(rows[mnemonic]["supported"])


class Cop1TransferIrTests(unittest.TestCase):
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

    def _ops(self, mnemonic: str) -> list:
        return [
            self.ops[instruction.pc]
            for instruction in self.instructions
            if instruction.mnemonic == mnemonic
        ]

    def test_transfer_forms_lower_to_dedicated_kinds(self) -> None:
        reads = self._ops("mfc1")
        writes = self._ops("mtc1")
        loads = self._ops("lwc1")
        stores = self._ops("swc1")
        self.assertTrue(reads and writes and loads and stores)
        self.assertTrue(all(op.kind == "fpr_read" for op in reads))
        self.assertTrue(all(op.kind == "fpr_write" for op in writes))
        self.assertTrue(all(op.kind == "cop1_load" for op in loads))
        self.assertTrue(all(op.kind == "cop1_store" for op in stores))

        first_read = reads[0]
        self.assertEqual((T1, 2), (first_read.dst, first_read.a))
        first_write = writes[0]
        self.assertEqual((3, T1), (first_write.dst, first_write.a))
        first_load = loads[0]
        self.assertEqual((2, T0, 0, 4), (first_load.dst, first_load.a,
                                        first_load.imm, first_load.size))
        first_store = stores[0]
        self.assertEqual((T0, 3, 4, 4), (first_store.a, first_store.b,
                                         first_store.imm, first_store.size))


class Cop1TransferOracleTests(unittest.TestCase):
    def test_oracle_produces_the_literal_results(self) -> None:
        state = oracle.run_oracle(build_program(), max_steps=MAX_STEPS)
        self.assertTrue(state["halted"])
        self.assertEqual("pc_outside_code", state["reason"])
        self.assertEqual(RETURN_SENTINEL, state["pc"])
        self.assertEqual(pair64(0), state["registers"][ZERO])
        for register, value in EXPECTED_REGISTERS.items():
            self.assertEqual(pair64(value), state["registers"][register],
                             f"register {register}")
        self.assertEqual(
            [EXPECTED_FPR[index] if index in EXPECTED_FPR else 0
             for index in range(32)],
            state["fpr"],
        )
        stored = (
            [[DATA_BASE + 4 + offset, byte]
             for offset, byte in enumerate(struct.pack("<I", 0x89ABCDEF))]
            + [[DATA_BASE + 8 + offset, byte]
               for offset, byte in enumerate(struct.pack("<I", 0xFFFFFFFF))]
        )
        self.assertEqual(stored, state["memory"])

    def test_unaligned_lwc1_fails_closed(self) -> None:
        asm = Assembler()
        asm.lui(T0, DATA_BASE >> 16)
        asm.emit(encode_i(0x31, 2, T0, 2))
        asm.jr(RA)
        asm.nop()
        with self.assertRaises(oracle.ExecutionError) as caught:
            oracle.run_oracle(_small_program(asm), max_steps=MAX_STEPS)
        self.assertEqual(f"Unaligned LWC1 at 0x{DATA_BASE + 2:08X}",
                         str(caught.exception))

    def test_unaligned_swc1_fails_closed(self) -> None:
        asm = Assembler()
        asm.lui(T0, DATA_BASE >> 16)
        asm.emit(encode_i(0x39, 2, T0, 6))
        asm.jr(RA)
        asm.nop()
        with self.assertRaises(oracle.ExecutionError) as caught:
            oracle.run_oracle(_small_program(asm), max_steps=MAX_STEPS)
        self.assertEqual(f"Unaligned SWC1 at 0x{DATA_BASE + 6:08X}",
                         str(caught.exception))

    def test_reserved_bits_program_fails_closed_before_lowering(self) -> None:
        asm = Assembler()
        asm.emit(MFC1_WORD | 0x001)
        asm.jr(RA)
        asm.nop()
        program = _small_program(asm)
        blocks = program.unsupported_blocks()
        self.assertEqual(1, len(blocks))
        self.assertIn("Reserved encoding fields are non-zero.", blocks[0].problem)
        result = ir.lower_program(program)
        self.assertEqual(1, len(result.errors))
        self.assertIn("unsupported", result.errors[0].lower())

    def test_rejected_transfer_is_refused_before_any_fpr_write(self) -> None:
        asm = Assembler()
        asm.emit(MTC1_WORD | 0x400)
        asm.jr(RA)
        asm.nop()
        with self.assertRaises(oracle.ExecutionError) as caught:
            oracle.run_oracle(_small_program(asm), max_steps=MAX_STEPS)
        self.assertIn("Reserved encoding fields are non-zero.",
                      str(caught.exception))


class Cop1TransferCodegenTests(unittest.TestCase):
    def test_generated_source_is_deterministic_and_carries_the_fpr_bank(self) -> None:
        program = build_program()
        result = ir.lower_program(program)
        self.assertEqual([], result.errors)
        first = codegen.generate(program, result)
        second = codegen.generate(program, result)
        self.assertEqual(first.source, second.source)
        self.assertEqual(first.source_sha256, second.source_sha256)
        self.assertEqual(first.memory_blob, second.memory_blob)
        self.assertIn("std::array<std::uint32_t, 32> fpr", first.source)
        self.assertIn('\\"fpr\\":[', first.source)
        self.assertIn("unaligned LWC1", first.source)
        self.assertIn("unaligned SWC1", first.source)
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
