# SPDX-License-Identifier: GPL-3.0-or-later
"""Non-likely branch tests: the delay slot executes on both outcomes.

Every fixture is an original synthetic ELF assembled in memory.  ``BLEZ``,
``BGTZ``, ``BLTZ``, ``BGEZ``, ``BLTZAL`` and ``BGEZAL`` always execute their
delay slot; only the two link forms write ``GPR[31] = pc + 8``, and they do so
whether or not the branch is taken.  ``GPR[31]`` as ``rs`` is rejected
fail-closed because the approved reference marks it UNPREDICTABLE.
"""
from __future__ import annotations

import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.rptp import codegen, isa, ir, native, oracle
from tools.rptp.cfg import discover_program
from tools.rptp.elf import parse_elf_bytes
from tools.rptp.fixtures import (
    A0,
    A1,
    A2,
    A3,
    CODE_BASE,
    DATA_BASE,
    RA,
    S0,
    S1,
    S2,
    S3,
    S4,
    S5,
    S7,
    T0,
    T1,
    T2,
    T3,
    T4,
    T5,
    T6,
    V0,
    V1,
    ZERO,
    Assembler,
    build_elf,
)
from tools.rptp.oracle import RETURN_SENTINEL

MASK64 = 0xFFFFFFFFFFFFFFFF
MAX_STEPS = 100_000

PLAIN_FORMS = ("blez", "bgtz", "bltz", "bgez", "bltzal", "bgezal")
LINK_FORMS = {"bltzal", "bgezal"}
CONDITION_VALUES = {
    "blez": (0, 1),
    "bgtz": (1, 0),
    "bltz": (-1, 0),
    "bgez": (0, -1),
    "bltzal": (-1, 0),
    "bgezal": (0, -1),
}
HIGH_BIT_CASES = {
    # 0x00000000FFFFFFFF is positive as a signed 64-bit value.
    "low32_negative": {
        "value": 0x00000000FFFFFFFF,
        "taken": {"blez": False, "bgtz": True, "bltz": False, "bgez": True},
    },
    # 0xFFFFFFFF00000001 is negative as a signed 64-bit value.
    "high32_negative": {
        "value": 0xFFFFFFFF00000001,
        "taken": {"blez": True, "bgtz": False, "bltz": True, "bgez": False},
    },
}
HIGH_BIT_REGS = {
    "blez": (A0, A1, A2),
    "bgtz": (A3, V0, V1),
    "bltz": (S0, S1, S2),
    "bgez": (S3, S4, S5),
}


def pair(value: int) -> list[int]:
    value &= MASK64
    return [value, 0]


def build_program(asm: Assembler, data: bytes = b""):
    return discover_program(parse_elf_bytes(build_elf(asm.resolve(), data)))


def build_program_words(words: list[int]):
    return discover_program(parse_elf_bytes(build_elf(words)))


def execute(asm: Assembler, data: bytes = b""):
    return oracle.run_oracle(build_program(asm, data), max_steps=MAX_STEPS)


def _emit_form(asm: Assembler, form: str, taken: bool) -> tuple[int, int]:
    """Emit one non-likely branch with distinct delay/fall-through markers."""
    if form in LINK_FORMS:
        asm.addu(S7, RA, ZERO)
    taken_value, not_taken_value = CONDITION_VALUES[form]
    asm.addiu(T0, ZERO, taken_value if taken else not_taken_value)
    branch_pc = asm.pc
    getattr(asm, form)(T0, "target")
    delay_pc = asm.pc
    asm.addiu(A0, ZERO, 0x11)      # delay slot, executed on both outcomes
    asm.addiu(A1, ZERO, 0x22)      # fall-through, executed only when not taken
    asm.label("target")
    asm.addiu(A2, ZERO, 0x33)      # reached by both outcomes
    asm.jr(S7 if form in LINK_FORMS else RA)
    asm.nop()
    return branch_pc, delay_pc


def _combined_program() -> Assembler:
    """One program covering every form and both outcomes."""
    asm = Assembler()
    asm.addu(S7, RA, ZERO)
    asm.lui(T4, DATA_BASE >> 16)

    # blez taken: the delay-slot store executes, the fall-through is skipped.
    asm.addiu(T0, ZERO, 0)
    asm.label("case0")
    asm.blez(T0, "case0_target")
    asm.sw(T0, 0, T4)
    asm.addiu(V0, ZERO, 0x12)
    asm.label("case0_target")

    # bgtz not taken: the delay-slot store still executes.
    asm.addiu(T0, ZERO, 0)
    asm.addiu(T1, ZERO, 1)
    asm.label("case1")
    asm.bgtz(T0, "case1_target")
    asm.sw(T1, 4, T4)
    asm.addiu(V1, ZERO, 0x22)
    asm.label("case1_target")

    # bltz taken: the delay-slot register write executes.
    asm.addiu(T0, ZERO, -1)
    asm.label("case2")
    asm.bltz(T0, "case2_target")
    asm.addiu(A0, ZERO, 0x11)
    asm.addiu(T2, ZERO, 0x12)
    asm.label("case2_target")

    # bgez not taken: the delay-slot register write still executes.
    asm.addiu(T0, ZERO, -1)
    asm.label("case3")
    asm.bgez(T0, "case3_target")
    asm.addiu(A1, ZERO, 0x21)
    asm.addiu(T3, ZERO, 0x22)
    asm.label("case3_target")

    # bltzal not taken: link written, delay slot executes, fall-through runs.
    asm.addiu(T0, ZERO, 0)
    asm.label("case4")
    asm.bltzal(T0, "case4_target")
    asm.addiu(A2, ZERO, 0x31)
    asm.addiu(T5, ZERO, 0x32)
    asm.label("case4_target")

    # bgezal taken: link written, delay slot targets $zero.
    asm.addiu(T0, ZERO, 0)
    asm.label("case5")
    asm.bgezal(T0, "case5_target")
    asm.addiu(ZERO, ZERO, 7)
    asm.addiu(T6, ZERO, 0x62)
    asm.label("case5_target")

    asm.jr(S7)
    asm.nop()
    return asm


def _case_pcs(asm: Assembler) -> dict[str, int]:
    return {
        name: asm.labels[name]
        for name in ("case0", "case1", "case2", "case3", "case4", "case5")
    }


def _high_bit_program(
    pattern: str,
) -> tuple[Assembler, dict[str, tuple[int, int]], bytes]:
    asm = Assembler()
    asm.lui(T1, DATA_BASE >> 16)
    asm.ld(T0, 0, T1)
    pcs: dict[str, tuple[int, int]] = {}
    for form, (delay, fallthrough, target) in HIGH_BIT_REGS.items():
        label = f"high_bit_{form}"
        branch_pc = asm.pc
        getattr(asm, form)(T0, label)
        pcs[form] = (branch_pc, asm.pc)
        asm.addiu(delay, ZERO, 0x11)
        asm.addiu(fallthrough, ZERO, 0x22)
        asm.label(label)
        asm.addiu(target, ZERO, 0x33)
    asm.jr(RA)
    asm.nop()
    return asm, pcs, struct.pack("<Q", HIGH_BIT_CASES[pattern]["value"])


class PlainBranchSemanticsTests(unittest.TestCase):
    def test_taken_and_not_taken_for_every_form(self):
        for form in PLAIN_FORMS:
            for taken in (True, False):
                with self.subTest(form=form, taken=taken):
                    asm = Assembler()
                    branch_pc, delay_pc = _emit_form(asm, form, taken)
                    state = execute(asm)
                    fallthrough_pc = branch_pc + 8
                    self.assertTrue(state["halted"], form)
                    self.assertEqual(state["reason"], "pc_outside_code", form)
                    self.assertEqual(state["pc"], RETURN_SENTINEL, form)
                    self.assertEqual(
                        state["registers"][A0], pair(0x11),
                        f"{form}: the delay slot must execute on both outcomes")
                    self.assertEqual(
                        state["registers"][A1], pair(0 if taken else 0x22),
                        f"{form}: wrong fall-through effect")
                    self.assertEqual(state["registers"][A2], pair(0x33), form)
                    if form in LINK_FORMS:
                        self.assertEqual(
                            state["registers"][RA], pair(branch_pc + 8),
                            f"{form}: link address must be pc + 8 on both outcomes")
                    index = state["trace"].index(branch_pc)
                    self.assertEqual(state["trace"][index + 1], delay_pc, form)
                    if taken:
                        self.assertNotIn(fallthrough_pc, state["trace"], form)
                    else:
                        self.assertEqual(
                            state["trace"][index + 2], fallthrough_pc, form)

    def test_not_taken_delay_slot_writes_memory(self):
        asm = Assembler()
        asm.lui(T4, DATA_BASE >> 16)
        asm.addiu(T0, ZERO, 0)
        asm.addiu(T1, ZERO, 1)
        asm.bgtz(T0, "target")
        asm.sw(T1, 0, T4)
        asm.addiu(A0, ZERO, 0x22)
        asm.label("target")
        asm.addiu(A1, ZERO, 0x33)
        asm.jr(RA)
        asm.nop()
        state = execute(asm)
        self.assertEqual(state["registers"][A0], pair(0x22))
        self.assertEqual(state["registers"][A1], pair(0x33))
        self.assertEqual(
            state["memory"],
            [[DATA_BASE, 1], [DATA_BASE + 1, 0],
             [DATA_BASE + 2, 0], [DATA_BASE + 3, 0]],
        )

    def test_conditions_compare_the_signed_low_64_bits(self):
        for pattern, spec in HIGH_BIT_CASES.items():
            asm, pcs, data = _high_bit_program(pattern)
            state = execute(asm, data)
            self.assertEqual(
                state["registers"][T0][0] & MASK64, spec["value"])
            for form in HIGH_BIT_REGS:
                with self.subTest(pattern=pattern, form=form):
                    taken = spec["taken"][form]
                    delay, fallthrough, target = HIGH_BIT_REGS[form]
                    branch_pc, delay_pc = pcs[form]
                    self.assertEqual(state["registers"][delay], pair(0x11))
                    self.assertEqual(
                        state["registers"][fallthrough],
                        pair(0 if taken else 0x22))
                    self.assertEqual(state["registers"][target], pair(0x33))
                    self.assertIn(delay_pc, state["trace"])
                    if taken:
                        self.assertNotIn(branch_pc + 8, state["trace"])
                    else:
                        self.assertIn(branch_pc + 8, state["trace"])

    def test_signed_low_64_bits_match_the_generated_native_path(self):
        try:
            native.find_msvc()
        except native.HarnessError as exc:
            self.skipTest(f"MSVC is genuinely unavailable: {exc}")
        for pattern in HIGH_BIT_CASES:
            with self.subTest(pattern=pattern):
                asm, _pcs, data = _high_bit_program(pattern)
                image = parse_elf_bytes(build_elf(asm.resolve(), data))
                program = discover_program(image)
                expected = oracle.run_oracle(program, max_steps=MAX_STEPS)
                actual = native.run_differential(image, max_steps=MAX_STEPS)
                self.assertEqual(actual, expected)

    def test_zero_stays_zero_when_a_delay_slot_targets_it(self):
        asm = Assembler()
        asm.bgez(ZERO, "target")
        delay_pc = asm.pc
        asm.addiu(ZERO, ZERO, 7)
        asm.addiu(A0, ZERO, 0x33)
        asm.label("target")
        asm.addiu(A1, ZERO, 0x44)
        asm.jr(RA)
        asm.nop()
        state = execute(asm)
        self.assertEqual(state["registers"][ZERO], pair(0))
        self.assertEqual(state["registers"][A0], pair(0))
        self.assertEqual(state["registers"][A1], pair(0x44))
        self.assertIn(delay_pc, state["trace"])


class PlainBranchCombinedTests(unittest.TestCase):
    def test_combined_program_explicit_outcomes(self):
        asm = _combined_program()
        pcs = _case_pcs(asm)
        state = execute(asm)
        self.assertTrue(state["halted"])
        self.assertEqual(state["reason"], "pc_outside_code")
        self.assertEqual(state["pc"], RETURN_SENTINEL)
        self.assertEqual(state["registers"][ZERO], pair(0))
        self.assertEqual(state["registers"][A0], pair(0x11))
        self.assertEqual(state["registers"][A1], pair(0x21))
        self.assertEqual(state["registers"][A2], pair(0x31))
        self.assertEqual(state["registers"][V0], pair(0))
        self.assertEqual(state["registers"][V1], pair(0x22))
        self.assertEqual(state["registers"][T2], pair(0))
        self.assertEqual(state["registers"][T3], pair(0x22))
        self.assertEqual(state["registers"][T5], pair(0x32))
        self.assertEqual(state["registers"][T6], pair(0))
        self.assertEqual(state["registers"][T4], pair(DATA_BASE))
        self.assertEqual(state["registers"][RA], pair(pcs["case5"] + 8))
        self.assertEqual(
            state["memory"],
            [[DATA_BASE, 0], [DATA_BASE + 1, 0],
             [DATA_BASE + 2, 0], [DATA_BASE + 3, 0],
             [DATA_BASE + 4, 1], [DATA_BASE + 5, 0],
             [DATA_BASE + 6, 0], [DATA_BASE + 7, 0]],
        )
        trace = state["trace"]
        for name in pcs:
            self.assertIn(pcs[name] + 4, trace, f"{name} delay slot must execute")
        for name in ("case0", "case2", "case5"):
            self.assertNotIn(pcs[name] + 8, trace,
                             f"{name} fall-through must be skipped")
        for name in ("case1", "case3", "case4"):
            self.assertIn(pcs[name] + 8, trace,
                          f"{name} fall-through must execute")

    def test_cfg_keeps_target_and_fallthrough_successors(self):
        asm = Assembler()
        asm.addiu(T0, ZERO, 1)
        branch_pc = asm.pc
        asm.blez(T0, "target")
        asm.addiu(A0, ZERO, 0x11)
        fallthrough_pc = asm.pc
        asm.addiu(A1, ZERO, 0x22)
        asm.label("target")
        target_pc = asm.pc
        asm.addiu(A2, ZERO, 0x33)
        asm.jr(RA)
        asm.nop()
        program = build_program(asm)
        block = program.blocks[CODE_BASE]
        self.assertTrue(block.supported)
        self.assertEqual(block.successors, (target_pc, fallthrough_pc))
        result = ir.lower_program(program)
        self.assertEqual(result.errors, [])
        control = result.blocks[CODE_BASE].control
        self.assertEqual(control.pc, branch_pc)
        self.assertEqual(control.kind, "branch")
        self.assertEqual(control.mnemonic, "blez")
        self.assertFalse(control.likely)
        self.assertIsNone(control.link_reg)
        self.assertEqual(control.target, target_pc)
        self.assertEqual(control.fallthrough, fallthrough_pc)

    def test_branch_target_zero_is_not_replaced_by_the_fallthrough(self):
        # beq $0, $0 at 0x1000 with immediate 0xFBFF targets address 0:
        # 0x1000 + 4 + (-1025 * 4) == 0.  The IR must keep the literal target.
        words = [0x1000FBFF, 0x00000000, 0x00000000]
        program = discover_program(parse_elf_bytes(build_elf(words, base=0x1000)))
        self.assertEqual(program.blocks[0x1000].instructions[0].target, 0)
        result = ir.lower_program(program, block_starts=[0x1000])
        self.assertEqual(result.errors, [])
        control = result.blocks[0x1000].control
        self.assertEqual(control.kind, "branch")
        self.assertEqual(control.target, 0)
        self.assertEqual(control.fallthrough, 0x1008)
        generated = codegen.generate(program, result)
        self.assertIn("taken ? 0x00000000u : 0x00001008u", generated.source)

    def test_link_control_records_gpr_31(self):
        asm = Assembler()
        asm.addiu(T0, ZERO, -1)
        asm.bltzal(T0, "target")
        asm.nop()
        asm.label("target")
        asm.jr(RA)
        asm.nop()
        result = ir.lower_program(build_program(asm))
        self.assertEqual(result.errors, [])
        control = result.blocks[CODE_BASE].control
        self.assertEqual(control.mnemonic, "bltzal")
        self.assertFalse(control.likely)
        self.assertEqual(control.link_reg, 31)

    def test_generated_source_is_deterministic_and_executes_the_delay_slot(self):
        program = build_program(_combined_program())
        result = ir.lower_program(program)
        self.assertEqual(result.errors, [])
        first = codegen.generate(program, result)
        second = codegen.generate(program, result)
        self.assertEqual(first.source, second.source)
        self.assertEqual(first.source_sha256, second.source_sha256)
        self.assertEqual(first.memory_blob, second.memory_blob)
        self.assertEqual(first.blob_sha256, second.blob_sha256)
        self.assertNotIn("if (taken) {", first.source)

    def test_native_differential_matches_oracle(self):
        try:
            native.find_msvc()
        except native.HarnessError as exc:
            self.skipTest(f"MSVC is genuinely unavailable: {exc}")
        image = parse_elf_bytes(build_elf(_combined_program().resolve()))
        program = discover_program(image)
        result = ir.lower_program(program)
        self.assertEqual(result.errors, [])
        expected = oracle.run_oracle(program, max_steps=MAX_STEPS)
        actual = native.run_differential(image, max_steps=MAX_STEPS)
        self.assertEqual(actual, expected)


class PlainBranchDelaySlotOrderingTests(unittest.TestCase):
    """R-032: delay-slot effects survive a taken branch, and the link write is
    visible to the delay slot before it executes."""

    def test_taken_branch_delay_slot_store_keeps_a_nonzero_value(self):
        asm = Assembler()
        asm.lui(T4, DATA_BASE >> 16)
        asm.addiu(T0, ZERO, 0)
        asm.addiu(T1, ZERO, 0x2A)
        asm.blez(T0, "target")
        asm.sw(T1, 0, T4)          # delay slot of a taken branch
        asm.addiu(A0, ZERO, 0x22)  # skipped fall-through
        asm.label("target")
        asm.addiu(A1, ZERO, 0x33)
        asm.jr(RA)
        asm.nop()
        state = execute(asm)
        self.assertEqual(state["registers"][A0], pair(0))
        self.assertEqual(state["registers"][A1], pair(0x33))
        self.assertEqual(
            state["memory"],
            [[DATA_BASE, 0x2A], [DATA_BASE + 1, 0],
             [DATA_BASE + 2, 0], [DATA_BASE + 3, 0]],
        )

    def test_delay_slot_reads_the_link_written_by_the_branch(self):
        for form, taken in (("bgezal", True), ("bltzal", False)):
            with self.subTest(form=form, taken=taken):
                asm = Assembler()
                asm.addu(S7, RA, ZERO)          # keep the initial $ra (RETURN_SENTINEL) as the return
                asm.addiu(RA, ZERO, 0x7FFF)     # stale $ra the link must overwrite
                asm.addiu(T0, ZERO, 0)          # bgezal taken / bltzal not taken
                branch_pc = asm.pc
                getattr(asm, form)(T0, "target")
                delay_pc = asm.pc
                asm.addiu(A0, RA, 0)            # delay slot observes the new $ra
                asm.addiu(A1, ZERO, 0x22)       # fall-through
                asm.label("target")
                asm.addiu(A2, RA, 0)            # target block also sees the new $ra
                asm.jr(S7)
                asm.nop()
                state = execute(asm)
                self.assertTrue(state["halted"])
                self.assertEqual(
                    state["trace"][state["trace"].index(branch_pc) + 1], delay_pc)
                self.assertEqual(state["registers"][A0], pair(branch_pc + 8))
                self.assertEqual(state["registers"][RA], pair(branch_pc + 8))
                self.assertEqual(state["registers"][A1], pair(0 if taken else 0x22))
                self.assertEqual(state["registers"][A2], pair(branch_pc + 8))


class PlainBranchFailClosedTests(unittest.TestCase):
    def test_decoding_marks_the_six_forms_manual(self):
        encodings = {
            "blez": (0x06, 0x00),
            "bgtz": (0x07, 0x00),
            "bltz": (0x01, 0x00),
            "bgez": (0x01, 0x01),
            "bltzal": (0x01, 0x10),
            "bgezal": (0x01, 0x11),
        }
        for mnemonic, (opcode, rt_field) in encodings.items():
            with self.subTest(mnemonic=mnemonic):
                word = (opcode << 26) | (T0 << 21) | (rt_field << 16) | 1
                ins = isa.decode_instruction(word, CODE_BASE)
                self.assertEqual(ins.mnemonic, mnemonic)
                self.assertTrue(ins.supported)
                self.assertTrue(ins.valid)
                self.assertEqual(ins.verification, isa.MANUAL)
                self.assertFalse(ins.is_likely)

    def test_link_plain_with_rs_31_is_rejected(self):
        for mnemonic, rt_field in (("bltzal", 0x10), ("bgezal", 0x11)):
            with self.subTest(mnemonic=mnemonic):
                word = (0x01 << 26) | (31 << 21) | (rt_field << 16) | 1
                ins = isa.decode_instruction(word, CODE_BASE)
                self.assertEqual(ins.mnemonic, mnemonic)
                self.assertFalse(ins.valid)
                self.assertFalse(ins.supported)
                self.assertIn("GPR 31", ins.note)
                program = build_program_words([word, 0])
                block = program.blocks[CODE_BASE]
                self.assertFalse(block.supported)
                problems = [d for d in program.diagnostics
                            if d.code == "block.unsupported_control"]
                self.assertTrue(problems)
                self.assertIn("GPR 31", problems[0].message)


if __name__ == "__main__":
    unittest.main(verbosity=2)
