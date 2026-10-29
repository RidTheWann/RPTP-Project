# SPDX-License-Identifier: GPL-3.0-or-later
"""Branch-likely delay-slot nullification tests.

Every fixture is an original synthetic ELF assembled in memory.  A likely
branch executes its delay slot only when the branch is taken; a not-taken
branch nullifies the delay slot and continues at ``pc + 8``.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.rptp import codegen, fixtures, isa, ir, native, oracle
from tools.rptp.cfg import BasicBlock, discover_program
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
    S7,
    T0,
    T1,
    T2,
    T3,
    T4,
    T5,
    T6,
    T7,
    T8,
    V0,
    V1,
    ZERO,
    Assembler,
    build_elf,
)
from tools.rptp.oracle import RETURN_SENTINEL

MASK64 = 0xFFFFFFFFFFFFFFFF
MAX_STEPS = 100_000

LIKELY_FORMS = (
    "beql",
    "bnel",
    "blezl",
    "bgtzl",
    "bltzl",
    "bgezl",
    "bltzall",
    "bgezall",
)
LINK_FORMS = {"bltzall", "bgezall"}


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
    """Emit one likely branch with distinct delay/fall-through markers."""
    if form in LINK_FORMS:
        asm.addu(S7, RA, ZERO)
    if form in {"beql", "bnel"}:
        equal = taken == (form == "beql")
        asm.addiu(T0, ZERO, 1)
        asm.addiu(T1, ZERO, 1 if equal else 2)
    elif form == "blezl":
        asm.addiu(T0, ZERO, 0 if taken else 1)
    elif form == "bgtzl":
        asm.addiu(T0, ZERO, 1 if taken else 0)
    elif form in {"bltzl", "bltzall"}:
        asm.addiu(T0, ZERO, -1 if taken else 0)
    else:  # bgezl, bgezall
        asm.addiu(T0, ZERO, 0 if taken else -1)

    branch_pc = asm.pc
    if form in {"beql", "bnel"}:
        getattr(asm, form)(T0, T1, "target")
    else:
        getattr(asm, form)(T0, "target")
    delay_pc = asm.pc
    asm.addiu(A0, ZERO, 0x11)      # delay slot
    asm.addiu(A1, ZERO, 0x22)      # fall-through
    asm.label("target")
    asm.addiu(A2, ZERO, 0x33)      # reached by both outcomes
    asm.jr(S7 if form in LINK_FORMS else RA)
    asm.nop()
    return branch_pc, delay_pc


def _combined_program() -> Assembler:
    """One program covering every likely form and both outcomes.

    Taken cases skip a fall-through marker, not-taken cases execute it.  The
    beql delay slot stores to memory; the bnel delay slot would store a second
    word only if it were incorrectly executed.
    """
    asm = Assembler()
    asm.addu(S7, RA, ZERO)
    asm.lui(T4, DATA_BASE >> 16)

    # beql taken: delay slot writes memory.
    asm.addiu(T0, ZERO, 1)
    asm.addiu(T1, ZERO, 1)
    asm.label("case0")
    asm.beql(T0, T1, "case0_target")
    asm.sw(T1, 0, T4)
    asm.addiu(V0, ZERO, 0x12)
    asm.label("case0_target")

    # bnel not taken: delay-slot memory write must be nullified.
    asm.addiu(T0, ZERO, 1)
    asm.addiu(T1, ZERO, 1)
    asm.label("case1")
    asm.bnel(T0, T1, "case1_target")
    asm.sw(T1, 4, T4)
    asm.addiu(V1, ZERO, 0x22)
    asm.label("case1_target")

    # blezl taken: delay-slot register write.
    asm.addiu(T0, ZERO, 0)
    asm.label("case2")
    asm.blezl(T0, "case2_target")
    asm.addiu(A0, ZERO, 0x11)
    asm.addiu(T2, ZERO, 0x12)
    asm.label("case2_target")

    # bgtzl not taken: delay-slot register write must be nullified.
    asm.addiu(T0, ZERO, 0)
    asm.label("case3")
    asm.bgtzl(T0, "case3_target")
    asm.addiu(A1, ZERO, 0x21)
    asm.addiu(T3, ZERO, 0x22)
    asm.label("case3_target")

    # bltzl not taken: delay-slot register write must be nullified.
    asm.addiu(T0, ZERO, 0)
    asm.label("case4")
    asm.bltzl(T0, "case4_target")
    asm.addiu(A2, ZERO, 0x31)
    asm.addiu(T5, ZERO, 0x32)
    asm.label("case4_target")

    # bgezl taken: delay slot targets $zero, which must stay zero.
    asm.addiu(T0, ZERO, 0)
    asm.label("case5")
    asm.bgezl(T0, "case5_target")
    asm.addiu(ZERO, ZERO, 7)
    asm.addiu(T6, ZERO, 0x62)
    asm.label("case5_target")

    # bltzall taken: link write plus delay slot.
    asm.addiu(T0, ZERO, -1)
    asm.label("case6")
    asm.bltzall(T0, "case6_target")
    asm.addiu(A3, ZERO, 0x41)
    asm.addiu(T7, ZERO, 0x42)
    asm.label("case6_target")

    # bgezall not taken: link is still written, delay slot is nullified.
    asm.addiu(T0, ZERO, -1)
    asm.label("case7")
    asm.bgezall(T0, "case7_target")
    asm.addiu(S0, ZERO, 0x51)
    asm.addiu(T8, ZERO, 0x52)
    asm.label("case7_target")

    asm.jr(S7)
    asm.nop()
    return asm


def _case_pcs(asm: Assembler) -> dict[str, int]:
    return {
        name: asm.labels[name]
        for name in (
            "case0", "case1", "case2", "case3",
            "case4", "case5", "case6", "case7",
        )
    }


class LikelyBranchSemanticsTests(unittest.TestCase):
    def test_taken_and_not_taken_for_every_likely_form(self):
        for form in LIKELY_FORMS:
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
                        state["registers"][A0], pair(0x11 if taken else 0),
                        f"{form}: wrong delay-slot register effect")
                    self.assertEqual(
                        state["registers"][A1], pair(0 if taken else 0x22),
                        f"{form}: wrong fall-through effect")
                    self.assertEqual(state["registers"][A2], pair(0x33), form)
                    if form in LINK_FORMS:
                        self.assertEqual(
                            state["registers"][RA], pair(branch_pc + 8),
                            f"{form}: link address must be pc + 8 even when nullified")
                    index = state["trace"].index(branch_pc)
                    if taken:
                        self.assertEqual(state["trace"][index + 1], delay_pc, form)
                        self.assertNotIn(fallthrough_pc, state["trace"], form)
                    else:
                        self.assertNotIn(delay_pc, state["trace"], form)
                        self.assertEqual(
                            state["trace"][index + 1], fallthrough_pc, form)

    def test_taken_likely_delay_slot_writes_memory(self):
        asm = Assembler()
        asm.lui(T4, DATA_BASE >> 16)
        asm.addiu(T0, ZERO, 1)
        asm.addiu(T1, ZERO, 1)
        asm.beql(T0, T1, "target")
        asm.sw(T1, 0, T4)
        asm.addiu(A0, ZERO, 0x22)
        asm.label("target")
        asm.addiu(A1, ZERO, 0x33)
        asm.jr(RA)
        asm.nop()
        state = execute(asm)
        self.assertEqual(state["registers"][A0], pair(0))
        self.assertEqual(state["registers"][A1], pair(0x33))
        self.assertEqual(
            state["memory"],
            [[DATA_BASE, 1], [DATA_BASE + 1, 0],
             [DATA_BASE + 2, 0], [DATA_BASE + 3, 0]],
        )

    def test_not_taken_likely_delay_slot_does_not_write_memory(self):
        asm = Assembler()
        asm.lui(T4, DATA_BASE >> 16)
        asm.addiu(T0, ZERO, 1)
        asm.addiu(T1, ZERO, 1)
        asm.bnel(T0, T1, "target")
        asm.sw(T1, 0, T4)
        asm.addiu(A0, ZERO, 0x22)
        asm.label("target")
        asm.addiu(A1, ZERO, 0x33)
        asm.jr(RA)
        asm.nop()
        state = execute(asm)
        self.assertEqual(state["registers"][A0], pair(0x22))
        self.assertEqual(state["registers"][A1], pair(0x33))
        self.assertEqual(state["memory"], [])

    def test_zero_stays_zero_when_a_taken_delay_slot_targets_it(self):
        asm = Assembler()
        asm.beql(ZERO, ZERO, "target")
        delay_pc = asm.pc
        asm.addiu(ZERO, ZERO, 7)
        asm.addiu(A0, ZERO, 0x22)
        asm.label("target")
        asm.addiu(A1, ZERO, 0x33)
        asm.jr(RA)
        asm.nop()
        state = execute(asm)
        self.assertEqual(state["registers"][ZERO], pair(0))
        self.assertEqual(state["registers"][A0], pair(0))
        self.assertEqual(state["registers"][A1], pair(0x33))
        self.assertIn(delay_pc, state["trace"])

    def test_zero_stays_zero_when_a_nullified_delay_slot_targets_it(self):
        asm = Assembler()
        asm.bnel(ZERO, ZERO, "target")
        delay_pc = asm.pc
        asm.addiu(ZERO, ZERO, 7)
        asm.addiu(A0, ZERO, 0x22)
        asm.label("target")
        asm.addiu(A1, ZERO, 0x33)
        asm.jr(RA)
        asm.nop()
        state = execute(asm)
        self.assertEqual(state["registers"][ZERO], pair(0))
        self.assertEqual(state["registers"][A0], pair(0x22))
        self.assertEqual(state["registers"][A1], pair(0x33))
        self.assertNotIn(delay_pc, state["trace"])


class LikelyBranchCombinedTests(unittest.TestCase):
    def test_combined_program_explicit_outcomes(self):
        asm = _combined_program()
        pcs = _case_pcs(asm)
        state = execute(asm)
        self.assertTrue(state["halted"])
        self.assertEqual(state["reason"], "pc_outside_code")
        self.assertEqual(state["pc"], RETURN_SENTINEL)
        self.assertEqual(state["registers"][ZERO], pair(0))
        self.assertEqual(state["registers"][A0], pair(0x11))
        self.assertEqual(state["registers"][A1], pair(0))
        self.assertEqual(state["registers"][A2], pair(0))
        self.assertEqual(state["registers"][A3], pair(0x41))
        self.assertEqual(state["registers"][V0], pair(0))
        self.assertEqual(state["registers"][V1], pair(0x22))
        self.assertEqual(state["registers"][T2], pair(0))
        self.assertEqual(state["registers"][T3], pair(0x22))
        self.assertEqual(state["registers"][T5], pair(0x32))
        self.assertEqual(state["registers"][T6], pair(0))
        self.assertEqual(state["registers"][T7], pair(0))
        self.assertEqual(state["registers"][T8], pair(0x52))
        self.assertEqual(state["registers"][S0], pair(0))
        self.assertEqual(state["registers"][T4], pair(DATA_BASE))
        self.assertEqual(state["registers"][RA], pair(pcs["case7"] + 8))
        self.assertEqual(
            state["memory"],
            [[DATA_BASE, 1], [DATA_BASE + 1, 0],
             [DATA_BASE + 2, 0], [DATA_BASE + 3, 0]],
        )
        trace = state["trace"]
        for name in ("case0", "case2", "case5", "case6"):
            self.assertIn(pcs[name] + 4, trace, f"{name} delay slot must execute")
        for name in ("case1", "case3", "case4", "case7"):
            self.assertNotIn(pcs[name] + 4, trace,
                             f"{name} delay slot must be nullified")

    def test_cfg_keeps_target_and_fallthrough_successors(self):
        asm = Assembler()
        asm.addiu(T0, ZERO, 1)
        asm.addiu(T1, ZERO, 1)
        branch_pc = asm.pc
        asm.beql(T0, T1, "target")
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
        self.assertEqual(control.mnemonic, "beql")
        self.assertTrue(control.likely)
        self.assertEqual(control.target, target_pc)
        self.assertEqual(control.fallthrough, fallthrough_pc)

    def test_generated_source_is_deterministic_and_guards_delay_slots(self):
        program = build_program(_combined_program())
        result = ir.lower_program(program)
        self.assertEqual(result.errors, [])
        first = codegen.generate(program, result)
        second = codegen.generate(program, result)
        self.assertEqual(first.source, second.source)
        self.assertEqual(first.source_sha256, second.source_sha256)
        self.assertEqual(first.memory_blob, second.memory_blob)
        self.assertEqual(first.blob_sha256, second.blob_sha256)
        self.assertIn("if (taken) {", first.source)
        self.assertNotIn("DelaySlot", first.source)

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

    def test_likely_branch_control_has_likely_metadata(self):
        word = (0x14 << 26) | (T0 << 21) | (T1 << 16) | 1
        ins = isa.decode_instruction(word, CODE_BASE)
        delay = isa.decode_instruction(0, CODE_BASE + 4)
        self.assertEqual(ins.mnemonic, "beql")
        self.assertTrue(ins.supported)
        self.assertTrue(ins.is_likely)
        block = BasicBlock(
            start=CODE_BASE,
            instructions=[ins, delay],
            kind="branch",
            successors=(CODE_BASE + 8, CODE_BASE + 8),
        )
        lowered = ir.lower_block(block)
        self.assertEqual(lowered.control.kind, "branch")
        self.assertTrue(lowered.control.likely)


class LikelyBranchFailClosedTests(unittest.TestCase):
    def test_link_likely_with_rs_31_is_rejected(self):
        word = (0x01 << 26) | (31 << 21) | (0x13 << 16) | 1
        ins = isa.decode_instruction(word, CODE_BASE)
        self.assertEqual(ins.mnemonic, "bgezall")
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

    def test_undefined_regimm_likely_neighbour_is_not_guessed(self):
        word = (0x01 << 26) | (0x04 << 16)
        ins = isa.decode_instruction(word, CODE_BASE)
        self.assertTrue(ins.mnemonic.startswith("unknown_"))
        self.assertFalse(ins.valid)
        self.assertFalse(ins.supported)
        self.assertIn("Unsupported REGIMM rt 0x04", ins.note)
        with self.assertRaises(ValueError):
            isa.decode_instruction(word, CODE_BASE, strict=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
