# SPDX-License-Identifier: GPL-3.0-or-later
"""Pin the documented capability split between the RPTP analysis paths.

This is a contract test, not a semantic differential.  It records which of the
42 Level B operations the legacy ``tools/rptp_ir.py`` / ``tools/rptp_lower.py``
pipeline implements and proves that the fourteen branch forms it does not
implement fail closed with the shared diagnostic instead of being silently
lowered.  The new ``tools/rptp`` decoder accepts the same words, so a change on
either side has to update the contracts, the semantics matrix and this test.

ADR-0005 (Proposed) uses this split as evidence for its canonical-path
recommendation; this module neither changes semantics nor settles the ADR.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

from tools.rptp import fixtures, isa

ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module {relative_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


legacy_ir = _load_module("rptp_path_contract_ir", "tools/rptp_ir.py")
legacy_lower = _load_module("rptp_path_contract_lower", "tools/rptp_lower.py")
spike = legacy_ir.spike

# The legacy pipeline's exact lowering set, copied from docs/IR_CFG.md and
# pinned here so an extension cannot be added to one path silently.
LEGACY_OPERATIONS = frozenset({
    "nop", "sll", "addu", "subu", "daddu", "and", "or", "xor", "nor",
    "slt", "sltu", "addiu", "daddiu", "slti", "sltiu", "andi", "ori",
    "xori", "lui", "lw", "sw", "ld", "sd", "beq", "bne", "j", "jal", "jr",
})

ORDINARY_BRANCH_FORMS = frozenset({
    "blez", "bgtz", "bltz", "bgez", "bltzal", "bgezal",
})

LIKELY_BRANCH_FORMS = frozenset({
    "beql", "bnel", "blezl", "bgtzl",
    "bltzl", "bgezl", "bltzall", "bgezall",
})

NEW_PATH_ONLY_OPERATIONS = ORDINARY_BRANCH_FORMS | LIKELY_BRANCH_FORMS
LEVEL_B_OPERATIONS = LEGACY_OPERATIONS | NEW_PATH_ONLY_OPERATIONS


def build_branch_program(form: str) -> tuple[list[int], int]:
    """Return words for ``addiu; <form>; nop; addiu; jr; nop`` and the branch PC."""
    assembler = fixtures.Assembler(base=spike.BASE)
    assembler.addiu(fixtures.T0, fixtures.ZERO, 0)
    if form in {"beql", "bnel"}:
        getattr(assembler, form)(fixtures.T0, fixtures.ZERO, "done")
    else:
        getattr(assembler, form)(fixtures.T0, "done")
    assembler.nop()
    assembler.addiu(fixtures.T1, fixtures.ZERO, 1)
    assembler.label("done")
    assembler.jr(fixtures.RA)
    assembler.nop()
    return assembler.resolve(), spike.BASE + 4


def build_shared_subset_program() -> bytes:
    """A program using only the legacy pipeline's 28-operation subset."""
    assembler = fixtures.Assembler(base=spike.BASE)
    assembler.addiu(fixtures.T0, fixtures.ZERO, 1)
    assembler.addiu(fixtures.T1, fixtures.ZERO, 2)
    assembler.addu(fixtures.T2, fixtures.T0, fixtures.T1)
    assembler.addiu(fixtures.T3, fixtures.ZERO, 0x2000)
    assembler.sw(fixtures.T2, 0, fixtures.T3)
    assembler.lw(fixtures.T4, 0, fixtures.T3)
    assembler.beq(fixtures.T2, fixtures.T4, "done")
    assembler.nop()
    assembler.addiu(fixtures.T5, fixtures.ZERO, 9)
    assembler.label("done")
    assembler.jr(fixtures.RA)
    assembler.nop()
    rows = [
        (spike.BASE + 4 * index, f"word_{index}", word)
        for index, word in enumerate(assembler.resolve())
    ]
    return spike.build_elf_from_rows(rows)


class PipelinePathContractTests(unittest.TestCase):
    def test_legacy_lowering_set_is_the_documented_shared_subset(self) -> None:
        self.assertEqual(set(legacy_lower._SUPPORTED_OPS), set(LEGACY_OPERATIONS))
        self.assertEqual(len(LEVEL_B_OPERATIONS), 42)
        self.assertTrue(LEGACY_OPERATIONS.isdisjoint(NEW_PATH_ONLY_OPERATIONS))
        self.assertTrue(LEVEL_B_OPERATIONS <= isa.SUPPORTED_MNEMONICS)

    def test_legacy_pipeline_rejects_the_fourteen_new_path_forms(self) -> None:
        for form in sorted(NEW_PATH_ONLY_OPERATIONS):
            with self.subTest(form=form):
                words, branch_pc = build_branch_program(form)
                rows = [
                    (spike.BASE + 4 * index, f"word_{index}", word)
                    for index, word in enumerate(words)
                ]
                with self.assertRaises(legacy_ir.AnalysisError) as caught:
                    legacy_ir.analyze_elf(spike.build_elf_from_rows(rows))
                self.assertEqual(caught.exception.code, legacy_ir.IR_UNSUPPORTED_INSTRUCTION)
                self.assertEqual(caught.exception.pc, branch_pc)

                decoded = isa.decode_instruction(words[1], branch_pc)
                self.assertEqual(decoded.mnemonic, form)
                self.assertTrue(decoded.supported)
                self.assertEqual(decoded.is_likely, form in LIKELY_BRANCH_FORMS)

    def test_legacy_pipeline_still_accepts_and_lowers_the_shared_subset(self) -> None:
        result = legacy_ir.analyze_elf(build_shared_subset_program())
        self.assertIn("beq", {instruction.op for instruction in result.instructions})

        source = legacy_lower.lower_to_cpp(result)
        self.assertTrue(source.endswith("\n"))
        self.assertEqual(source, legacy_lower.lower_to_cpp(result))
        self.assertNotIn(str(ROOT), source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
