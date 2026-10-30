# SPDX-License-Identifier: GPL-3.0-or-later
"""Executable contract for the proposed canonical execution path (ADR-0005).

The Gate 0 spike, the legacy ``tools/rptp_ir.py``/``tools/rptp_lower.py``
pipeline, the ``tools/rptp`` package and the C++ runtime harness model
separate instruction subsets and memory models. ADR-0005 proposes
``tools/rptp`` as the canonical analysis front end and the native runtime as
the canonical execution target, freezes the legacy paths and requires
executable inventory and shared-subset equivalence evidence before any
retirement.

This module supplies the first two evidence gates:

* the legacy lowering set is exactly the documented 28 operations and is a
  strict subset of the canonical decoder's supported set; the fourteen branch
  forms added after Gate 0 are canonical-only;
* one synthetic program containing every legacy operation produces identical
  low-64 register state, halt PC and executed-PC trace in the legacy oracle
  and the canonical oracle, and both analysis/lowering paths accept it.

It does not declare the canonical path, compile generated C++, cover the
native harness, or change any Gate, provenance or compatibility status.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

from tests.test_runtime_loader import build_elf
from tools.rptp import cfg, elf, fixtures, isa, oracle

ROOT = Path(__file__).resolve().parents[1]
BASE = 0x00100000
DATA_BASE = 0x00002000
DATA_OFFSET = 0x100
CODE_OFFSET = 0x200
MASK64 = 0xFFFFFFFFFFFFFFFF
MAX_STEPS = 1_000


def load_module(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module {relative_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


spike = load_module("rptp_gate0_spike_path_contract", "tools/rptp_gate0_spike.py")
legacy_ir = load_module("rptp_ir_path_contract", "tools/rptp_ir.py")
legacy_lower = load_module("rptp_lower_path_contract", "tools/rptp_lower.py")

# The 28 operations accepted by tools/rptp_lower.py at this baseline.  The
# legacy paths are frozen by ADR-0005; changing this set requires updating the
# ADR, the evidence matrix and the shared differential program together.
LEGACY_OPERATIONS = frozenset({
    "nop", "sll", "addu", "subu", "daddu", "and", "or", "xor", "nor",
    "slt", "sltu", "addiu", "daddiu", "slti", "sltiu", "andi", "ori",
    "xori", "lui", "lw", "sw", "ld", "sd", "beq", "bne", "j", "jal", "jr",
})

# Branch forms added by later increments in the canonical path only.
ORDINARY_FORMS = frozenset({"blez", "bgtz", "bltz", "bgez", "bltzal", "bgezal"})
LIKELY_FORMS = frozenset({
    "beql", "bnel", "blezl", "bgtzl",
    "bltzl", "bgezl", "bltzall", "bgezall",
})


def shared_legacy_program() -> tuple[list[int], dict[str, int]]:
    """Build a program containing every legacy operation exactly at least once."""
    asm = fixtures.Assembler()
    asm.addu(fixtures.RA, fixtures.ZERO, fixtures.ZERO)
    asm.addiu(fixtures.T0, fixtures.ZERO, DATA_BASE)
    asm.addiu(fixtures.T1, fixtures.ZERO, 7)
    asm.addiu(fixtures.T2, fixtures.ZERO, 5)
    asm.addu(fixtures.T3, fixtures.T1, fixtures.T2)                       # 12
    asm.emit(fixtures.encode_r(0x23, fixtures.T4, fixtures.T2, fixtures.T1))  # subu
    asm.emit(fixtures.encode_i(0x19, fixtures.T5, fixtures.T4, 1))        # daddiu
    asm.daddu(fixtures.T6, fixtures.T5, fixtures.T1)                      # 6
    asm.sll(fixtures.T7, fixtures.T3, 4)                                  # 192
    asm.lui(fixtures.S0, 0x1234)
    asm.ori(fixtures.S0, fixtures.S0, 0x5678)
    asm.lui(fixtures.S1, 0xFEDC)
    asm.ori(fixtures.S1, fixtures.S1, 0xBA98)
    asm.and_(fixtures.S2, fixtures.S0, fixtures.S1)
    asm.or_(fixtures.S3, fixtures.S0, fixtures.S1)
    asm.xor(fixtures.S4, fixtures.S0, fixtures.S1)
    asm.nor(fixtures.S5, fixtures.S0, fixtures.S1)
    asm.andi(fixtures.S6, fixtures.S1, 0x00FF)
    asm.xori(fixtures.S7, fixtures.S0, 0xFFFF)
    asm.slt(fixtures.K0, fixtures.T4, fixtures.T3)
    asm.sltu(fixtures.K1, fixtures.T4, fixtures.T3)
    asm.slti(fixtures.GP, fixtures.T4, -1)
    asm.sltiu(fixtures.SP, fixtures.T4, -1)
    asm.sw(fixtures.T3, 0, fixtures.T0)
    asm.lw(fixtures.FP, 0, fixtures.T0)                                   # 12
    asm.sw(fixtures.S1, 4, fixtures.T0)
    asm.sw(fixtures.S0, 8, fixtures.T0)
    asm.sw(fixtures.S1, 12, fixtures.T0)
    asm.ld(fixtures.A0, 8, fixtures.T0)                                   # 0xFEDCBA9812345678
    asm.sd(fixtures.A0, 16, fixtures.T0)
    asm.ld(fixtures.A1, 16, fixtures.T0)
    asm.beq(fixtures.A0, fixtures.A1, "equal")
    asm.addiu(fixtures.A2, fixtures.ZERO, 1)
    asm.addiu(fixtures.A2, fixtures.ZERO, 99)                             # skipped
    asm.label("equal")
    asm.bne(fixtures.A0, fixtures.A1, "different")
    asm.addiu(fixtures.A3, fixtures.ZERO, 2)
    asm.addiu(fixtures.A3, fixtures.A3, 1)                                # 3
    asm.label("different")
    asm.j("after_call")
    asm.addiu(fixtures.T1, fixtures.ZERO, 8)                              # delay slot
    asm.addiu(fixtures.T2, fixtures.ZERO, 100)                            # skipped
    asm.label("after_call")
    asm.jal("subroutine")
    asm.addiu(fixtures.T2, fixtures.ZERO, 9)                              # delay slot
    asm.addiu(fixtures.T3, fixtures.ZERO, 55)
    asm.j("after_subroutine")
    asm.nop()
    asm.label("subroutine")
    asm.addiu(fixtures.V0, fixtures.ZERO, 30)
    asm.emit(fixtures.encode_r(0x08, fixtures.ZERO, fixtures.RA, fixtures.ZERO))  # jr ra
    asm.addiu(fixtures.V1, fixtures.ZERO, 31)                             # delay slot
    asm.label("after_subroutine")
    asm.addu(fixtures.RA, fixtures.ZERO, fixtures.ZERO)
    asm.emit(fixtures.encode_r(0x08, fixtures.ZERO, fixtures.RA, fixtures.ZERO))
    asm.nop()
    return asm.resolve(), dict(asm.labels)


def build_shared_image(words: list[int]) -> bytes:
    code = b"".join(int(word & 0xFFFFFFFF).to_bytes(4, "little") for word in words)
    data = bytes(16)
    payload = data + bytes(CODE_OFFSET - DATA_OFFSET - len(data)) + code
    return build_elf(
        BASE,
        [
            {"offset": DATA_OFFSET, "vaddr": DATA_BASE, "filesz": len(data), "memsz": len(data), "flags": 6},
            {"offset": CODE_OFFSET, "vaddr": BASE, "filesz": len(code), "memsz": len(code), "flags": 5},
        ],
        payload=payload,
        payload_offset=DATA_OFFSET,
    )


class PathInventoryTests(unittest.TestCase):
    def test_legacy_lowering_set_is_frozen_and_contained(self) -> None:
        self.assertEqual(LEGACY_OPERATIONS, frozenset(legacy_lower._SUPPORTED_OPS))
        self.assertLessEqual(LEGACY_OPERATIONS, isa.SUPPORTED_MNEMONICS)

    def test_post_gate0_branch_forms_are_canonical_only(self) -> None:
        self.assertEqual(LIKELY_FORMS, isa.LIKELY_MNEMONICS)
        for mnemonic in sorted(LIKELY_FORMS | ORDINARY_FORMS):
            with self.subTest(mnemonic=mnemonic):
                self.assertIn(mnemonic, isa.SUPPORTED_MNEMONICS)
                self.assertIn(mnemonic, isa.BRANCH_MNEMONICS)
                self.assertNotIn(mnemonic, LEGACY_OPERATIONS)


class SharedSubsetEquivalenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.words, cls.labels = shared_legacy_program()
        cls.image = build_shared_image(cls.words)
        cls.parsed = elf.parse_elf_bytes(cls.image, path="path_contract_shared.elf")
        cls.program = cfg.discover_program(cls.parsed)
        cls.canonical = oracle.run_oracle(cls.program, max_steps=MAX_STEPS)
        entry, legacy_words, _info = spike.parse_elf(cls.image)
        cls.legacy_entry = entry
        cls.legacy_words = legacy_words
        cls.legacy = spike.normalize_state(spike.execute_oracle(entry, legacy_words))
        cls.legacy_analysis = legacy_ir.analyze_elf(cls.image)
        cls.legacy_source = legacy_lower.lower_to_cpp(cls.legacy_analysis)
        cls.canonical_registers = [
            pair[0] & MASK64 for pair in cls.canonical["registers"]
        ]

    def test_the_program_contains_every_legacy_operation(self) -> None:
        mnemonics = {
            isa.decode_instruction(word, pc=BASE + index * 4).mnemonic
            for index, word in enumerate(self.words)
        }
        self.assertEqual(LEGACY_OPERATIONS, mnemonics)

    def test_both_analyzers_and_the_legacy_lowerer_accept_the_program(self) -> None:
        self.assertEqual([], self.program.unsupported_blocks())
        self.assertEqual(len(self.words), len(self.legacy_analysis.instructions))
        self.assertEqual(self.legacy_source, legacy_lower.lower_to_cpp(self.legacy_analysis))
        self.assertTrue(self.legacy_source.endswith("\n"))

    def test_legacy_and_canonical_oracles_agree(self) -> None:
        self.assertTrue(self.canonical["halted"])
        self.assertTrue(self.legacy["halted"])
        self.assertEqual("pc_outside_code", self.canonical["reason"])
        self.assertEqual(0, self.canonical["pc"])
        self.assertEqual(0, self.legacy["pc"])
        self.assertEqual(49, self.canonical["steps"])
        self.assertEqual(self.canonical["trace"], self.legacy["trace"])
        self.assertEqual(49, len(self.legacy["trace"]))
        self.assertEqual(self.canonical_registers, self.legacy["registers"])

    def test_the_shared_program_exercises_the_documented_values(self) -> None:
        registers = self.canonical_registers
        self.assertEqual(0xFEDCBA9812345678, registers[fixtures.A0])
        self.assertEqual(0xFEDCBA9812345678, registers[fixtures.A1])
        self.assertEqual(30, registers[fixtures.V0])
        self.assertEqual(31, registers[fixtures.V1])
        self.assertEqual(1, registers[fixtures.A2])
        self.assertEqual(3, registers[fixtures.A3])
        self.assertEqual(12, registers[fixtures.FP])
        self.assertEqual(0xFFFFFFFFFFFFFFFE, registers[fixtures.T4])
        self.assertEqual(0xFFFFFFFFFFFFFFFF, registers[fixtures.T5])
        self.assertEqual(6, registers[fixtures.T6])
        self.assertEqual(192, registers[fixtures.T7])
        self.assertEqual(0x12345678, registers[fixtures.S0])
        self.assertEqual(0xFFFFFFFFFEDCBA98, registers[fixtures.S1])
        self.assertEqual(0x12141218, registers[fixtures.S2])
        self.assertEqual(0xFFFFFFFFFEFCFEF8, registers[fixtures.S3])
        self.assertEqual(0xFFFFFFFFECE8ECE0, registers[fixtures.S4])
        self.assertEqual(0x1030107, registers[fixtures.S5])
        self.assertEqual(0x98, registers[fixtures.S6])
        self.assertEqual(0x1234A987, registers[fixtures.S7])
        self.assertEqual(1, registers[fixtures.K0])
        self.assertEqual(0, registers[fixtures.K1])
        self.assertEqual(1, registers[fixtures.GP])
        self.assertEqual(1, registers[fixtures.SP])
        self.assertEqual(0, registers[fixtures.RA])
        self.assertEqual(0, registers[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
