# SPDX-License-Identifier: GPL-3.0-or-later
"""Exact-value edge tests for the RPTP reference oracle.

Every fixture here is an original synthetic ELF assembled in memory; no game
data, BIOS image or emulator source is involved.  The tests pin the documented
R5900 subset semantics and act as the specification the native emitter is
compared against.  Assertions use the complete normalised register pairs so
that a wrong high lane cannot hide behind a matching low 64 bits.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.rptp.cfg import discover_program
from tools.rptp.elf import parse_elf_bytes
from tools.rptp.fixtures import (
    A0,
    A1,
    A2,
    CODE_BASE,
    DATA_BASE,
    RA,
    S0,
    S1,
    S2,
    S3,
    T0,
    T1,
    T2,
    T3,
    T4,
    T5,
    T6,
    T7,
    V0,
    V1,
    ZERO,
    Assembler,
    build_elf,
    encode_i,
    encode_mmi,
    encode_r,
)
from tools.rptp.oracle import ExecutionError, RETURN_SENTINEL, run_oracle

MASK64 = 0xFFFFFFFFFFFFFFFF
MASK128 = (1 << 128) - 1

LOW64_MESSAGE = (
    "KNOWN ORACLE BUG (low-64 compare): R5900 GPRs are 128-bit, but BEQ/BNE "
    "and MOVZ/MOVN conditions must inspect only bits 63..0.  A difference "
    "that exists only in the high lane must not affect the result."
)

HILO_MESSAGE = (
    "ORACLE SEMANTIC MISMATCH: MULT/MULTU/DIV/DIVU must place SEXT64 of each "
    "32-bit half into HI/LO (docs/research/r5900-isa.json and codegen "
    "exec_div/exec_mult do this); the oracle currently zero-extends.  "
    "MFHI/MFLO consequently lose the sign extension too."
)

LOAD_DATA = bytes([
    0x80, 0x01, 0x82, 0x03, 0x84, 0x05, 0x86, 0x07,
    0xF0, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77,
    0x88, 0x99, 0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF,
])


def pair(value: int) -> list[int]:
    """Return the normalised [lo64, hi64] register pair for an integer."""
    value &= MASK128
    return [value & MASK64, (value >> 64) & MASK64]


def sext_width(value: int, bits: int) -> list[int]:
    value &= (1 << bits) - 1
    if value & (1 << (bits - 1)):
        value -= 1 << bits
    return pair(value)


def sext32(value: int) -> list[int]:
    return sext_width(value, 32)


def sext16(value: int) -> list[int]:
    return sext_width(value, 16)


def sext8(value: int) -> list[int]:
    return sext_width(value, 8)


def sext64(value: int) -> list[int]:
    value &= MASK64
    if value & (1 << 63):
        value -= 1 << 64
    return pair(value)


def build_program(asm: Assembler, data: bytes = b""):
    return discover_program(parse_elf_bytes(build_elf(asm.resolve(), data)))


def execute(asm: Assembler, data: bytes = b"", **kwargs):
    return run_oracle(build_program(asm, data), **kwargs)


def load_data_base(asm: Assembler, register: int = T4) -> None:
    asm.lui(register, DATA_BASE >> 16)


def pcs(*indices: int) -> list[int]:
    return [CODE_BASE + 4 * index for index in indices]


class OracleEdgeTestCase(unittest.TestCase):
    def assert_returned(self, state, steps: int | None = None) -> None:
        self.assertTrue(state["halted"], "oracle did not halt")
        self.assertEqual(state["reason"], "pc_outside_code")
        self.assertEqual(state["pc"], RETURN_SENTINEL)
        if steps is not None:
            self.assertEqual(state["steps"], steps)
            self.assertEqual(len(state["trace"]), steps)


class Alu64BitBoundaryTests(OracleEdgeTestCase):
    def test_daddu_carries_across_bit_63(self):
        asm = Assembler()
        asm.daddu(T2, T0, T1)       # 0xFFFF_FFFF_FFFF_FFFF + 1 wraps to 0
        asm.daddu(T3, S0, S1)       # 0x7FFF_FFFF_FFFF_FFFF + 1 sets bit 63
        asm.jr(RA)
        asm.nop()
        state = execute(asm, initial_registers={
            T0: 0xFFFFFFFFFFFFFFFF,
            T1: 1,
            S0: 0x7FFFFFFFFFFFFFFF,
            S1: 1,
        })
        self.assertEqual(state["registers"][T2], pair(0))
        self.assertEqual(state["registers"][T3], sext64(1 << 63))
        self.assert_returned(state)

    def test_dsubu_borrows_across_bit_63(self):
        asm = Assembler()
        asm.dsubu(T2, T0, T1)       # 0 - 1 wraps to 0xFFFF_FFFF_FFFF_FFFF
        asm.dsubu(T3, S0, S1)       # 0x8000_0000_0000_0000 - 1 = 0x7FFF...
        asm.jr(RA)
        asm.nop()
        state = execute(asm, initial_registers={
            T0: 0,
            T1: 1,
            S0: 1 << 63,
            S1: 1,
        })
        self.assertEqual(state["registers"][T2], sext64(0xFFFFFFFFFFFFFFFF))
        self.assertEqual(state["registers"][T3], pair(0x7FFFFFFFFFFFFFFF))
        self.assert_returned(state)

    def test_dsll32_shift_amounts_zero_and_31(self):
        asm = Assembler()
        asm.addiu(T0, ZERO, 1)
        asm.dsll32(T1, T0, 0)       # 1 << 32
        asm.dsll32(T2, T0, 31)      # 1 << 63
        asm.jr(RA)
        asm.nop()
        state = execute(asm)
        self.assertEqual(state["registers"][T1], pair(1 << 32))
        self.assertEqual(state["registers"][T2], sext64(1 << 63))
        self.assert_returned(state)

    def test_addiu_truncates_to_32_then_sign_extends(self):
        asm = Assembler()
        asm.addiu(T0, ZERO, -1)     # 0xFFFF_FFFF_FFFF_FFFF
        asm.addiu(T1, T0, 1)        # low 32 bits wrap to zero
        asm.addiu(T2, ZERO, -32768) # 0xFFFF_FFFF_FFFF_8000
        asm.jr(RA)
        asm.nop()
        state = execute(asm)
        self.assertEqual(state["registers"][T0], pair(-1))
        self.assertEqual(state["registers"][T1], pair(0))
        self.assertEqual(state["registers"][T2], sext32(0xFFFF8000))
        self.assert_returned(state)

    def test_andi_ori_xori_zero_extend_the_16_bit_immediate(self):
        asm = Assembler()
        asm.lui(T0, 0x1234)
        asm.ori(T1, T0, 0x8000)              # positive result, no sign fill
        asm.andi(T2, T0, 0x8000)             # bit 15 is clear in LUI result
        asm.emit(encode_i(0x0E, T3, T0, 0x8000))  # xori
        asm.addiu(T4, ZERO, -1)              # 64-bit all ones source
        asm.andi(T5, T4, 0x8000)
        asm.ori(T6, ZERO, 0x8000)
        asm.emit(encode_i(0x0E, T7, ZERO, 0x8000))  # xori of zero
        asm.jr(RA)
        asm.nop()
        state = execute(asm)
        self.assertEqual(state["registers"][T1], pair(0x12348000))
        self.assertEqual(state["registers"][T2], pair(0))
        self.assertEqual(state["registers"][T3], pair(0x12348000))
        self.assertEqual(state["registers"][T5], pair(0x8000))
        self.assertEqual(state["registers"][T6], pair(0x8000))
        self.assertEqual(state["registers"][T7], pair(0x8000))
        self.assert_returned(state)


class LoadStoreTests(OracleEdgeTestCase):
    def test_lb_and_lbu(self):
        asm = Assembler()
        load_data_base(asm)
        asm.emit(encode_i(0x20, T0, T4, 0))  # lb  0x80
        asm.emit(encode_i(0x24, T1, T4, 0))  # lbu 0x80
        asm.emit(encode_i(0x20, T2, T4, 2))  # lb  0x82
        asm.emit(encode_i(0x24, T3, T4, 2))  # lbu 0x82
        asm.jr(RA)
        asm.nop()
        state = execute(asm, LOAD_DATA)
        self.assertEqual(state["registers"][T0], sext8(0x80))
        self.assertEqual(state["registers"][T1], pair(0x80))
        self.assertEqual(state["registers"][T2], sext8(0x82))
        self.assertEqual(state["registers"][T3], pair(0x82))
        self.assert_returned(state)

    def test_lh_and_lhu(self):
        asm = Assembler()
        load_data_base(asm)
        asm.emit(encode_i(0x21, T0, T4, 18))  # lh  0xBBAA
        asm.emit(encode_i(0x25, T1, T4, 18))  # lhu 0xBBAA
        asm.emit(encode_i(0x21, T2, T4, 0))   # lh  0x0180
        asm.emit(encode_i(0x25, T3, T4, 0))   # lhu 0x0180
        asm.jr(RA)
        asm.nop()
        state = execute(asm, LOAD_DATA)
        self.assertEqual(state["registers"][T0], sext16(0xBBAA))
        self.assertEqual(state["registers"][T1], pair(0xBBAA))
        self.assertEqual(state["registers"][T2], pair(0x0180))
        self.assertEqual(state["registers"][T3], pair(0x0180))
        self.assert_returned(state)

    def test_lw_and_lwu(self):
        asm = Assembler()
        load_data_base(asm)
        asm.emit(encode_i(0x23, T0, T4, 16))  # lw  0xBBAA9988
        asm.emit(encode_i(0x27, T1, T4, 16))  # lwu 0xBBAA9988
        asm.emit(encode_i(0x23, T2, T4, 0))   # lw  0x03820180
        asm.emit(encode_i(0x27, T3, T4, 0))   # lwu 0x03820180
        asm.jr(RA)
        asm.nop()
        state = execute(asm, LOAD_DATA)
        self.assertEqual(state["registers"][T0], sext32(0xBBAA9988))
        self.assertEqual(state["registers"][T1], pair(0xBBAA9988))
        self.assertEqual(state["registers"][T2], pair(0x03820180))
        self.assertEqual(state["registers"][T3], pair(0x03820180))
        self.assert_returned(state)

    def test_ld_sign_extends_64_bit_value(self):
        asm = Assembler()
        load_data_base(asm)
        asm.emit(encode_i(0x37, T0, T4, 8))   # ld 0x77665544332211F0
        asm.emit(encode_i(0x37, T1, T4, 16))  # ld 0xFFEEDDCCBBAA9988
        asm.jr(RA)
        asm.nop()
        state = execute(asm, LOAD_DATA)
        self.assertEqual(state["registers"][T0], sext64(0x77665544332211F0))
        self.assertEqual(state["registers"][T1], sext64(0xFFEEDDCCBBAA9988))
        self.assert_returned(state)

    def test_sb_sh_sw_sd_sq_write_little_endian_bytes(self):
        asm = Assembler()
        asm.lui(T0, 0x1234)
        asm.ori(T0, T0, 0x5678)
        load_data_base(asm)
        asm.emit(encode_i(0x28, T0, T4, 0))   # sb
        asm.emit(encode_i(0x29, T0, T4, 2))   # sh
        asm.emit(encode_i(0x2B, T0, T4, 4))   # sw
        asm.emit(encode_i(0x3F, T0, T4, 8))   # sd
        asm.emit(encode_i(0x1F, T0, T4, 16))  # sq
        asm.jr(RA)
        asm.nop()
        state = execute(asm)
        value = 0x12345678
        expected: list[list[int]] = []
        for offset, size in ((0, 1), (2, 2), (4, 4), (8, 8), (16, 16)):
            for byte_index in range(size):
                expected.append([
                    DATA_BASE + offset + byte_index,
                    (value >> (8 * byte_index)) & 0xFF,
                ])
        expected.sort()
        self.assertEqual(state["memory"], expected)
        self.assert_returned(state)

    def test_lq_and_sq_mask_low_four_address_bits(self):
        asm = Assembler()
        load_data_base(asm, T0)
        asm.addiu(T0, T0, 3)        # unaligned base: 0x0020_0003
        asm.lq(T1, 5, T0)           # 0x0020_0008 -> 0x0020_0000
        asm.sq(T1, 0x13, T0)        # 0x0020_0016 -> 0x0020_0010
        asm.jr(RA)
        asm.nop()
        state = execute(asm, bytes(range(0x10, 0x30)))
        self.assertEqual(
            state["registers"][T1],
            [0x1716151413121110, 0x1F1E1D1C1B1A1918],
        )
        self.assertEqual(
            state["memory"],
            [[DATA_BASE + 0x10 + index, 0x10 + index] for index in range(16)],
        )
        self.assert_returned(state)

    def test_unaligned_half_and_word_accesses_raise(self):
        cases = (
            ("lh", 0x21, 1, r"Unaligned LH"),
            ("lw", 0x23, 2, r"Unaligned LW"),
            ("sh", 0x29, 1, r"Unaligned SH"),
            ("sw", 0x2B, 2, r"Unaligned SW"),
        )
        for name, opcode, offset, pattern in cases:
            with self.subTest(access=name):
                asm = Assembler()
                load_data_base(asm)
                asm.addiu(T4, T4, offset)
                asm.emit(encode_i(opcode, T0, T4, 0))
                asm.jr(RA)
                asm.nop()
                with self.assertRaisesRegex(ExecutionError, pattern):
                    execute(asm)

    def test_out_of_ram_access_raises(self):
        for name, opcode in (("lw", 0x23), ("sw", 0x2B)):
            with self.subTest(access=name):
                asm = Assembler()
                asm.lui(T0, 0x0200)  # 0x0200_0000 == RAM_SIZE
                asm.emit(encode_i(opcode, T1, T0, 0))
                asm.jr(RA)
                asm.nop()
                with self.assertRaisesRegex(
                        ExecutionError, r"outside the modelled 32 MiB main RAM"):
                    execute(asm)


class MultiplyDivideTests(OracleEdgeTestCase):
    def test_mult_and_multu_use_only_low_32_bit_operands(self):
        asm = Assembler()
        asm.mult(T0, T1)
        asm.mflo(T2)
        asm.mfhi(T3)
        asm.multu(T4, T5)
        asm.mflo(T6)
        asm.mfhi(T7)
        asm.jr(RA)
        asm.nop()
        state = execute(asm, initial_registers={
            T0: 0xDEADBEEF00000004,
            T1: 0xCAFEBABE00000005,
            T4: 0x11111111FFFFFFFF,
            T5: 0x22222222FFFFFFFF,
        })
        # MULT: 4 * 5 == 20.
        self.assertEqual(state["registers"][T2], pair(20))
        self.assertEqual(state["registers"][T3], pair(0))
        # MULTU: (2^32 - 1)^2 == 0xFFFF_FFFE_0000_0001.
        self.assertEqual(state["registers"][T6], pair(1))
        # HI holds SEXT64(0xFFFF_FFFE), so MFHI also sign-extends from bit 31.
        self.assertEqual(state["registers"][T7], sext32(0xFFFFFFFE), HILO_MESSAGE)
        self.assertEqual(state["lo"], 1, HILO_MESSAGE)
        self.assertEqual(state["hi"], 0xFFFFFFFFFFFFFFFE, HILO_MESSAGE)
        self.assert_returned(state)

    def test_mult_int32_min_times_minus_one(self):
        asm = Assembler()
        asm.mult(T0, T1)
        asm.mflo(T2)
        asm.mfhi(T3)
        asm.jr(RA)
        asm.nop()
        state = execute(asm, initial_registers={
            T0: 0x1234567880000000,
            T1: 0x0BADF00DFFFFFFFF,
        })
        self.assertEqual(state["lo"], 0xFFFFFFFF80000000, HILO_MESSAGE)
        self.assertEqual(state["hi"], 0, HILO_MESSAGE)
        self.assertEqual(state["registers"][T2], pair(-0x80000000), HILO_MESSAGE)
        self.assertEqual(state["registers"][T3], pair(0), HILO_MESSAGE)
        self.assert_returned(state)

    def test_div_7_by_minus_3(self):
        asm = Assembler()
        asm.addiu(T0, ZERO, 7)
        asm.addiu(T1, ZERO, -3)
        asm.div(T0, T1)
        asm.mflo(T2)
        asm.mfhi(T3)
        asm.jr(RA)
        asm.nop()
        state = execute(asm)
        self.assertEqual(state["lo"], 0xFFFFFFFFFFFFFFFE, HILO_MESSAGE)
        self.assertEqual(state["hi"], 1, HILO_MESSAGE)
        self.assertEqual(state["registers"][T2], pair(-2), HILO_MESSAGE)
        self.assertEqual(state["registers"][T3], pair(1), HILO_MESSAGE)
        self.assert_returned(state)

    def test_div_int32_min_by_minus_one(self):
        asm = Assembler()
        asm.lui(T0, 0x8000)          # 0xFFFF_FFFF_8000_0000
        asm.addiu(T1, ZERO, -1)
        asm.div(T0, T1)
        asm.mflo(T2)
        asm.mfhi(T3)
        asm.jr(RA)
        asm.nop()
        state = execute(asm)
        self.assertEqual(state["lo"], 0xFFFFFFFF80000000, HILO_MESSAGE)
        self.assertEqual(state["hi"], 0, HILO_MESSAGE)
        self.assertEqual(state["registers"][T2], pair(-0x80000000), HILO_MESSAGE)
        self.assertEqual(state["registers"][T3], pair(0), HILO_MESSAGE)
        self.assert_returned(state)

    def test_divu_by_zero_is_model_defined_zero_quotient(self):
        asm = Assembler()
        asm.addiu(T0, ZERO, -1)      # low 32 bits are 0xFFFF_FFFF
        asm.addiu(T1, ZERO, 0)
        asm.divu(T0, T1)
        asm.mflo(T2)
        asm.mfhi(T3)
        asm.jr(RA)
        asm.nop()
        state = execute(asm)
        self.assertEqual(state["lo"], 0, HILO_MESSAGE)
        self.assertEqual(state["hi"], 0xFFFFFFFFFFFFFFFF, HILO_MESSAGE)
        self.assertEqual(state["registers"][T2], pair(0), HILO_MESSAGE)
        self.assertEqual(state["registers"][T3], pair(-1), HILO_MESSAGE)
        self.assert_returned(state)

    def test_mthi_mtlo_roundtrip_sign_extends_into_128_bits(self):
        asm = Assembler()
        asm.mthi(T0)
        asm.mtlo(T0)
        asm.mfhi(T1)
        asm.mflo(T2)
        asm.addiu(T3, ZERO, -1)
        asm.mthi(T3)
        asm.mfhi(T4)
        asm.jr(RA)
        asm.nop()
        state = execute(asm, initial_registers={T0: 0xDEAD8000000000000001})
        self.assertEqual(state["hi"], 0xFFFFFFFFFFFFFFFF)
        self.assertEqual(state["lo"], 0x8000000000000001)
        self.assertEqual(state["registers"][T1], sext64(0x8000000000000001))
        self.assertEqual(state["registers"][T2], sext64(0x8000000000000001))
        self.assertEqual(state["registers"][T4], pair(-1))
        self.assert_returned(state)

    def test_secondary_hi_lo_1_variants_are_encodable(self):
        # fixtures.encode_mmi() exposes the raw MMI encoding, so the *1 forms
        # can be exercised even though Assembler.mmi() has no named entry.
        asm = Assembler()
        asm.emit(encode_mmi(0x018, 0, T0, T1))   # mult1
        asm.emit(encode_mmi(0x010, T2, 0, 0))    # mfhi1
        asm.emit(encode_mmi(0x012, T3, 0, 0))    # mflo1
        asm.emit(encode_mmi(0x01A, 0, T4, T5))   # div1
        asm.emit(encode_mmi(0x010, T6, 0, 0))    # mfhi1
        asm.emit(encode_mmi(0x012, T7, 0, 0))    # mflo1
        asm.jr(RA)
        asm.nop()
        state = execute(asm, initial_registers={
            T0: 0xAAAAAAAAFFFFFFFF,
            T1: 0xBBBBBBBB00000003,
            T4: 7,
            # DIV1 truncates its operands to 32 bits: low half is -3.
            T5: 0xFFFFFFFFFFFFFFFD,
        })
        # mult1: -1 * 3 == -3 -> HI1 = -1, LO1 = -3.
        self.assertEqual(state["registers"][T2], pair(-1), HILO_MESSAGE)
        self.assertEqual(state["registers"][T3], pair(-3), HILO_MESSAGE)
        # div1: 7 / -3 == -2 remainder 1.
        self.assertEqual(state["registers"][T6], pair(1), HILO_MESSAGE)
        self.assertEqual(state["registers"][T7], pair(-2), HILO_MESSAGE)
        self.assertEqual(state["hi"], 0)
        self.assertEqual(state["lo"], 0)
        self.assertEqual(state["hi1"], 1, HILO_MESSAGE)
        self.assertEqual(state["lo1"], 0xFFFFFFFFFFFFFFFE, HILO_MESSAGE)
        self.assert_returned(state)


class ControlFlowTests(OracleEdgeTestCase):
    def test_taken_branch_samples_condition_before_delay_slot_overwrite(self):
        asm = Assembler()
        asm.addiu(T0, ZERO, 1)
        asm.addiu(T1, ZERO, 1)
        asm.beq(T0, T1, "taken")
        asm.addiu(T0, ZERO, 99)   # delay slot overwrites the compared register
        asm.addiu(A0, ZERO, 7)    # skipped when the branch is taken
        asm.label("taken")
        asm.addiu(A1, ZERO, 5)
        asm.jr(RA)
        asm.nop()
        state = execute(asm)
        self.assertEqual(state["registers"][T0], pair(99))
        self.assertEqual(state["registers"][A0], pair(0))
        self.assertEqual(state["registers"][A1], pair(5))
        self.assertEqual(state["trace"], pcs(0, 1, 2, 3, 5, 6, 7))
        self.assert_returned(state, steps=7)

    def test_not_taken_branch_executes_delay_slot_and_fallthrough(self):
        asm = Assembler()
        asm.addiu(T0, ZERO, 1)
        asm.addiu(T1, ZERO, 2)
        asm.beq(T0, T1, "taken")
        asm.addiu(A0, ZERO, 7)    # delay slot always executes
        asm.addiu(A1, ZERO, 9)    # fall-through executes
        asm.label("taken")
        asm.addiu(A2, ZERO, 5)
        asm.jr(RA)
        asm.nop()
        state = execute(asm)
        self.assertEqual(state["registers"][A0], pair(7))
        self.assertEqual(state["registers"][A1], pair(9))
        self.assertEqual(state["registers"][A2], pair(5))
        self.assertEqual(state["trace"], pcs(0, 1, 2, 3, 4, 5, 6, 7))
        self.assert_returned(state, steps=8)

    def test_jal_writes_link_value_pc_plus_8(self):
        asm = Assembler()
        asm.jal("sub")            # index 0: link = 0x0010_0008
        asm.addiu(T0, ZERO, 3)    # index 1: call delay slot
        asm.lui(RA, 0x7FFF)       # index 2: return target, then halt
        asm.jr(RA)
        asm.nop()
        asm.label("sub")
        asm.addiu(S0, RA, 0)      # observe the link value
        asm.addiu(V0, ZERO, 11)
        asm.jr(RA)
        asm.nop()
        state = execute(asm)
        self.assertEqual(state["registers"][S0], pair(CODE_BASE + 8))
        self.assertEqual(state["registers"][V0], pair(11))
        self.assertEqual(state["registers"][T0], pair(3))
        self.assertEqual(state["trace"], pcs(0, 1, 5, 6, 7, 8, 2, 3, 4))
        self.assert_returned(state, steps=9)

    def test_jr_ra_reaches_return_sentinel_as_pc_outside_code(self):
        asm = Assembler()
        asm.addiu(T0, ZERO, 1)
        asm.jr(RA)
        asm.nop()
        state = execute(asm)
        self.assertEqual(state["registers"][T0], pair(1))
        self.assertEqual(state["trace"], pcs(0, 1, 2))
        self.assert_returned(state, steps=3)

    def test_step_limit_zero_halts_before_first_instruction(self):
        asm = Assembler()
        asm.addiu(T0, ZERO, 1)
        asm.jr(RA)
        asm.nop()
        state = execute(asm, max_steps=0)
        self.assertTrue(state["halted"])
        self.assertEqual(state["reason"], "step_limit")
        self.assertEqual(state["steps"], 0)
        self.assertEqual(state["trace"], [])
        self.assertEqual(state["pc"], CODE_BASE)

    def test_step_limit_stops_self_jump_loop(self):
        asm = Assembler()
        asm.label("loop")
        asm.j("loop")
        asm.nop()
        state = execute(asm, max_steps=2)
        self.assertTrue(state["halted"])
        self.assertEqual(state["reason"], "step_limit")
        self.assertEqual(state["steps"], 2)
        self.assertEqual(state["trace"], pcs(0, 1))
        self.assertEqual(state["pc"], CODE_BASE)

    def test_delay_slot_and_skipped_pc_trace_order(self):
        asm = Assembler()
        asm.addiu(T0, ZERO, 1)
        asm.bne(T0, ZERO, "target")
        asm.addiu(T1, ZERO, 2)    # delay slot, executed after the bne
        asm.addiu(T2, ZERO, 3)    # skipped by the taken branch
        asm.label("target")
        asm.addiu(T3, ZERO, 4)
        asm.jr(RA)
        asm.nop()
        state = execute(asm)
        self.assertEqual(state["trace"], pcs(0, 1, 2, 4, 5, 6))
        self.assertEqual(state["registers"][T1], pair(2))
        self.assertEqual(state["registers"][T2], pair(0))
        self.assertEqual(state["registers"][T3], pair(4))
        self.assert_returned(state, steps=6)


class Low64RegisterCompareTests(OracleEdgeTestCase):
    """Specification tests for the low-64-bit compare fix in the oracle."""

    def test_beq_and_bne_compare_only_the_low_64_bits(self):
        asm = Assembler()
        asm.beq(T0, T1, "beq_ok")
        asm.addiu(V0, ZERO, 1)      # delay slot, always executes
        asm.addiu(S0, ZERO, 111)    # skipped: low lanes are equal
        asm.label("beq_ok")
        asm.addiu(S1, ZERO, 5)
        asm.bne(T0, T1, "bne_ok")
        asm.addiu(V1, ZERO, 2)      # delay slot, always executes
        asm.addiu(S2, ZERO, 222)    # executes: low lanes are equal
        asm.label("bne_ok")
        asm.addiu(S3, ZERO, 7)
        asm.jr(RA)
        asm.nop()
        state = execute(asm, initial_registers={
            T0: 0x1234,
            T1: (1 << 64) | 0x1234,
        })
        self.assertEqual(state["registers"][S0], pair(0), LOW64_MESSAGE)
        self.assertEqual(state["registers"][S2], pair(222), LOW64_MESSAGE)
        self.assertEqual(state["registers"][S1], pair(5))
        self.assertEqual(state["registers"][S3], pair(7))
        self.assertEqual(state["trace"], pcs(0, 1, 3, 4, 5, 6, 7, 8, 9),
                         LOW64_MESSAGE)
        self.assert_returned(state, steps=9)

    def test_movz_and_movn_compare_only_the_low_64_bits(self):
        asm = Assembler()
        asm.emit(encode_r(0x0A, T2, T0, T1))  # movz t2, t0, t1
        asm.emit(encode_r(0x0B, T4, T3, T1))  # movn t4, t3, t1
        asm.jr(RA)
        asm.nop()
        state = execute(asm, initial_registers={
            T0: 0xAA,
            T1: 1 << 64,  # low 64 bits are zero, high lane is not
            T3: 0xCC,
            T4: 0x55,
        })
        self.assertEqual(state["registers"][T2], pair(0xAA), LOW64_MESSAGE)
        self.assertEqual(state["registers"][T4], pair(0x55), LOW64_MESSAGE)
        self.assert_returned(state)


if __name__ == "__main__":
    unittest.main(verbosity=2)
