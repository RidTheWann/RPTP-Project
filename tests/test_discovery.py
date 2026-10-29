# SPDX-License-Identifier: GPL-3.0-or-later
"""Executable specification for trusted-seed function discovery.

Every fixture is a synthetic ELF assembled in memory with
``tools.rptp.fixtures``; no game bytes, BIOS images or emulator sources are
involved.  The expected behaviour is taken from
``docs/research/function-discovery.md``:

* section 3.1 - trusted seeds only (entry, function symbols, JAL targets,
  resolved indirect targets, user seeds), never a blind scan;
* section 3.2 - recursive traversal, delay slots and block splitting;
* section 3.4 - indirect jumps and strict jump-table acceptance;
* section 3.5 - code-versus-data policy;
* section 4   - deterministic, sorted output.

Where the implementation deliberately uses a different diagnostic spelling,
the test asserts the concrete string produced by ``cfg.py``; the policy-level
behaviour (refuse/diagnose rather than guess) is what is being specified.
"""
from __future__ import annotations

import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.rptp.cfg import Program, discover_program
from tools.rptp.elf import ElfImage, parse_elf_bytes
from tools.rptp.fixtures import (
    A0,
    AT,
    DATA_BASE,
    RA,
    SP,
    T0,
    T1,
    T2,
    T3,
    T4,
    T5,
    ZERO,
    Assembler,
    build_elf,
    encode_i,
    encode_r,
)

ENTRY = 0x00100000


def _parse(words: list[int], data: bytes = b"", path: str = "<test_discovery>") -> ElfImage:
    return parse_elf_bytes(build_elf(words, data), path=path)


def _call_shape(program: Program) -> list[tuple[int, int, int | None, str]]:
    return [(edge.caller, edge.call_pc, edge.callee, edge.kind) for edge in program.call_edges]


def _function_shape(program: Program) -> list[tuple[int, str, str, list[int]]]:
    return [(function.entry, function.name, function.source, list(function.blocks))
            for function in program.functions]


def _entry_jal_with_gap_image() -> ElfImage:
    """Entry block, a local branch target, a JAL, and an unreferenced word.

    Layout (all addresses 4-byte aligned, code base 0x00100000):

      0x00100000  beq  $zero, $zero, local    (target+fall-through)
      0x00100004  nop                          (delay slot)
      0x00100008  jal  callee                 (proven call seed)
      0x0010000C  nop                          (delay slot)
      0x00100010  local: jr  $ra               (reachable via branch)
      0x00100014  nop                          (delay slot)
      0x00100018  addiu $sp, $sp, -0x20        (data gap, prologue lookalike)
      0x0010001C  callee: jr $ra               (only reachable through JAL)
      0x00100020  nop                          (delay slot)
    """
    asm = Assembler()
    asm.beq(ZERO, ZERO, "local")
    asm.nop()
    asm.jal("callee")
    asm.nop()
    asm.label("local")
    asm.jr(RA)
    asm.nop()
    asm.emit(encode_i(0x09, SP, SP, -0x20))  # 0x27BD... prologue-lookalike data
    asm.label("callee")
    asm.jr(RA)
    asm.nop()
    return _parse(asm.resolve(), path="<entry-jal-gap>")


def _branch_split_image() -> ElfImage:
    """A forward branch into the middle of a six-instruction straight run.

    Layout:
      0x00100000  addiu $t0, $zero, 1
      0x00100004  addiu $t1, $zero, 2
      0x00100008  beq  $t0, $t1, mid          (target then fall-through)
      0x0010000C  nop
      0x00100010  addiu $t2, $zero, 3         (head of the run)
      0x00100014  addiu $t3, $zero, 4
      0x00100018  addiu $t4, $zero, 5
      0x0010001C  mid: addiu $t5, $zero, 6
      0x00100020  jr   $ra
      0x00100024  nop
    """
    asm = Assembler()
    asm.addiu(T0, ZERO, 1)
    asm.addiu(T1, ZERO, 2)
    asm.beq(T0, T1, "mid")
    asm.nop()
    asm.addiu(T2, ZERO, 3)
    asm.addiu(T3, ZERO, 4)
    asm.addiu(T4, ZERO, 5)
    asm.label("mid")
    asm.addiu(T5, ZERO, 6)
    asm.jr(RA)
    asm.nop()
    return _parse(asm.resolve(), path="<branch-split>")


def _jump_table_image() -> tuple[ElfImage, tuple[int, ...]]:
    """Canonical SLTIU-bounded indexed-LW jump table with four valid entries.

    Code layout:
      0x00100000  sltiu $at, $a0, 4
      0x00100004  lui   $t1, hi(table)
      0x00100008  ori   $t1, $t1, lo(table)
      0x0010000C  sll   $t2, $a0, 2
      0x00100010  addu  $t2, $t1, $t2
      0x00100014  lw    $t0, 0($t2)
      0x00100018  jr    $t0
      0x0010001C  nop
      0x00100020  target 0: jr $ra / nop
      0x00100028  target 1: jr $ra / nop
      0x00100030  target 2: jr $ra / nop
      0x00100038  target 3: jr $ra / nop

    The four aligned table words at DATA_BASE point at the four target blocks;
    every entry satisfies the section 3.4 proof obligations.
    """
    targets = (0x00100020, 0x00100028, 0x00100030, 0x00100038)
    asm = Assembler()
    asm.emit(encode_i(0x0B, AT, A0, 4))          # sltiu $at, $a0, 4
    asm.lui(T1, DATA_BASE >> 16)
    asm.ori(T1, T1, DATA_BASE & 0xFFFF)
    asm.emit(encode_r(0x00, T2, 0, A0, 2))       # sll $t2, $a0, 2
    asm.addu(T2, T1, T2)
    asm.lw(T0, 0, T2)
    asm.jr(T0)
    asm.nop()
    for index, _target in enumerate(targets):
        asm.label(f"target{index}")
        asm.jr(RA)
        asm.nop()
    words = asm.resolve()
    table = b"".join(struct.pack("<I", target) for target in targets)
    return _parse(words, table, path="<jump-table>"), targets


class TrustedSeedTests(unittest.TestCase):
    def test_entry_and_jal_seed_functions_not_reachable_by_fallthrough(self) -> None:
        """Entry is a Tier-A seed and JAL creates a function at its target.

        docs/research/function-discovery.md 3.1 (entry, JAL call targets) and
        3.2.  The callee sits after a JR/NOP and an unreferenced data word, so
        only call-target seeding - not linear scanning or fall-through - can
        discover it.
        """
        image = _entry_jal_with_gap_image()
        program = discover_program(image)

        self.assertEqual(ENTRY, program.entry)
        self.assertEqual(ENTRY, image.entry)
        self.assertEqual([0x00100000, 0x00100008, 0x00100010, 0x0010001C],
                         sorted(program.blocks))

        entry_block = program.blocks[ENTRY]
        self.assertEqual("branch", entry_block.kind)
        self.assertEqual([0x00100000, 0x00100004], entry_block.instruction_addresses)
        self.assertEqual((0x00100010, 0x00100008), entry_block.successors)

        call_block = program.blocks[0x00100008]
        self.assertEqual("call", call_block.kind)
        self.assertEqual(0x0010001C, call_block.call_target)
        # The callee is a successor.  (cfg.py also queues the JAL return site;
        # the documented contract only requires the call seed, so do not make
        # this assertion depend on that incidental extra edge.)
        self.assertIn(0x0010001C, call_block.successors)
        self.assertEqual("jal", call_block.instructions[0].mnemonic)

        self.assertEqual("return", program.blocks[0x00100010].kind)
        self.assertEqual("return", program.blocks[0x0010001C].kind)
        self.assertEqual([0x00100000, 0x0010001C],
                         [function.entry for function in program.functions])
        self.assertEqual(
            [(0x00100000, "entry"), (0x0010001C, "jal")],
            [(function.entry, function.source) for function in program.functions],
        )
        self.assertEqual([(0x00100000, 0x00100008, 0x0010001C, "jal")],
                         _call_shape(program))

        gap = 0x00100018
        self.assertIn(gap, program.code_words)  # bytes are in the executable segment...
        self.assertNotIn(gap, program.blocks)   # ...but are never decoded as code.
        self.assertIsNone(program.function_at(gap))
        self.assertFalse(any(gap in block.instruction_addresses
                             for block in program.blocks.values()))

    def test_branch_target_splits_straight_line_run(self) -> None:
        """A branch into a decoded run splits it at the target.

        docs/research/function-discovery.md 3.2: a newly discovered branch
        target inside an existing block starts a new block.  The head becomes
        a plain fall-through block and the tail keeps the original control
        kind (here ``return`` because the run ends in JR $ra).
        """
        program = discover_program(_branch_split_image())

        self.assertEqual([0x00100000, 0x00100010, 0x0010001C],
                         sorted(program.blocks))
        branch = program.blocks[0x00100000]
        self.assertEqual("branch", branch.kind)
        self.assertEqual((0x0010001C, 0x00100010), branch.successors)

        head = program.blocks[0x00100010]
        self.assertEqual("fallthrough", head.kind)
        self.assertEqual([0x00100010, 0x00100014, 0x00100018],
                         head.instruction_addresses)
        self.assertEqual((0x0010001C,), head.successors)
        self.assertEqual("", head.problem)

        tail = program.blocks[0x0010001C]
        self.assertEqual("return", tail.kind)
        self.assertEqual([0x0010001C, 0x00100020, 0x00100024],
                         tail.instruction_addresses)
        # delay_slot_pc is the trailing NOP; the block kind records JR $ra.
        self.assertEqual(["jr"], [insn.mnemonic for insn in tail.instructions
                                  if insn.is_control])
        self.assertEqual(0x00100024, tail.delay_slot_pc)

        split_events = [d for d in program.diagnostics if d.code == "block.split"]
        self.assertEqual(1, len(split_events))
        self.assertEqual(0x0010001C, split_events[0].address)
        self.assertEqual("info", split_events[0].severity)
        self.assertNotIn(0x00100010, [d.address for d in split_events])

    def test_seed_into_delay_slot_is_refused_with_diagnostic(self) -> None:
        """An explicit seed aimed at a delay slot must not split the block.

        docs/research/function-discovery.md 3.2/3.5: code addresses are
        instruction starts; splitting between a control transfer and its delay
        slot is unsafe.  ``cfg.py`` reports ``block.split_delay_slot`` and
        keeps the original block intact.
        """
        asm = Assembler()
        asm.addiu(T0, ZERO, 1)      # 0x00100000
        asm.jr(RA)                  # 0x00100004
        asm.nop()                   # 0x00100008 - delay slot
        asm.addiu(T1, ZERO, 2)      # 0x0010000C - unreachable after JR
        asm.jr(RA)                  # 0x00100010
        asm.nop()                   # 0x00100014
        program = discover_program(_parse(asm.resolve(), path="<delay-slot-seed>"),
                                   extra_seeds=(0x00100008,))

        self.assertEqual([0x00100000], sorted(program.blocks))
        block = program.blocks[0x00100000]
        self.assertEqual("return", block.kind)
        self.assertEqual([0x00100000, 0x00100004, 0x00100008],
                         block.instruction_addresses)
        self.assertEqual(0x00100008, block.delay_slot_pc)
        self.assertEqual("jr", block.instructions[1].mnemonic)

        refusals = [d for d in program.diagnostics if d.code == "block.split_delay_slot"]
        self.assertEqual(1, len(refusals))
        self.assertEqual("error", refusals[0].severity)
        self.assertEqual(0x00100008, refusals[0].address)
        self.assertIn("delay slot", refusals[0].message)

        self.assertNotIn(0x00100008, program.blocks)
        self.assertNotIn(0x0010000C, program.blocks)  # no scan after the return
        self.assertEqual([0x00100000], [function.entry for function in program.functions])

    def test_missing_delay_slot_at_segment_end_is_unsupported(self) -> None:
        """A control transfer whose delay slot is past EOF is not guessed.

        docs/research/function-discovery.md 3.2 and 5: this is
        DELAY_SLOT_OUTSIDE_IMAGE.  ``cfg.py`` marks the block ``unsupported``
        with a problem string instead of fabricating an instruction.
        """
        asm = Assembler()
        asm.addiu(T0, ZERO, 1)  # 0x00100000
        asm.jr(RA)              # 0x00100004; segment ends here
        program = discover_program(_parse(asm.resolve(), path="<missing-delay-slot>"))

        self.assertEqual([0x00100000], sorted(program.blocks))
        block = program.blocks[0x00100000]
        self.assertEqual("unsupported", block.kind)
        self.assertEqual([0x00100000, 0x00100004], block.instruction_addresses)
        self.assertEqual("missing delay slot", block.problem)
        self.assertIsNone(block.delay_slot_pc)
        self.assertFalse(block.supported)
        self.assertEqual("jr", block.instructions[-1].mnemonic)

        diagnostics = [d for d in program.diagnostics
                       if d.code == "block.missing_delay_slot"]
        self.assertEqual(1, len(diagnostics))
        self.assertEqual("error", diagnostics[0].severity)
        self.assertEqual(0x00100004, diagnostics[0].address)
        self.assertIn("no file-backed delay slot", diagnostics[0].message)
        self.assertEqual(1, program.stats["blocks"])
        self.assertEqual(0, len(program.blocks[0x00100000].successors))


class CodeVersusDataTests(unittest.TestCase):
    def test_non_executable_data_words_never_become_blocks(self) -> None:
        """Non-executable PT_LOAD bytes are data even when they decode.

        docs/research/function-discovery.md 3.5.4 and 3.1: only executable
        segments can be code, and a user seed in data is rejected explicitly.
        The data segment below contains a prologue-lookalike and JR $ra.
        """
        asm = Assembler()
        asm.jr(RA)
        asm.nop()
        data = struct.pack(
            "<III",
            encode_i(0x09, SP, SP, -0x20),  # addiu $sp,$sp,-0x20 (prologue mask)
            0x03E00008,                     # jr $ra
            0x00000000,
        )
        image = _parse(asm.resolve(), data, path="<non-exec-data>")
        data_segment = image.segment_for(DATA_BASE)
        self.assertIsNotNone(data_segment)
        self.assertFalse(data_segment.executable)
        self.assertFalse(image.is_code_address(DATA_BASE))
        self.assertNotIn(DATA_BASE, image.code_words())

        program = discover_program(image, extra_seeds=(DATA_BASE,))

        self.assertEqual([0x00100000], sorted(program.blocks))
        self.assertEqual([0x00100000], [function.entry for function in program.functions])
        self.assertNotIn(DATA_BASE, program.blocks)
        self.assertIsNone(program.function_at(DATA_BASE))
        self.assertEqual([], [pc for pc in program.blocks
                              if pc >= DATA_BASE])

        rejected = [d for d in program.diagnostics if d.code == "seed.outside_code"]
        self.assertEqual(1, len(rejected))
        self.assertEqual(DATA_BASE, rejected[0].address)
        self.assertEqual("warning", rejected[0].severity)

    def test_interior_data_word_between_functions_is_not_a_function(self) -> None:
        """An unreferenced prologue-like word between functions stays data.

        docs/research/function-discovery.md 3.5.3 and 7 (``interleaved-data``):
        literal pools and inline data are DATA/INTERIOR_DATA, not seeds.
        """
        program = discover_program(_entry_jal_with_gap_image())

        gap = 0x00100018
        self.assertIn(gap, program.code_words)
        self.assertNotIn(gap, program.blocks)
        self.assertNotIn(gap, program.roots)
        self.assertIsNone(program.function_at(gap))
        self.assertFalse(any(gap in block.instruction_addresses
                             for block in program.blocks.values()))
        self.assertEqual([0x00100000, 0x0010001C],
                         [function.entry for function in program.functions])

    def test_unreferenced_code_after_return_is_not_linear_scanned(self) -> None:
        """Valid instructions after an unconditional JR/NOP are not discovered.

        docs/research/function-discovery.md 3.1/3.5: no blind scan.  The
        unreachable ``jal`` below must not create a call edge or a block at its
        target; only the entry block is reachable.
        """
        asm = Assembler()
        asm.jr(RA)                  # 0x00100000 - unconditional return
        asm.nop()                   # 0x00100004 - delay slot
        asm.jal("never_reached")    # 0x00100008 - valid JAL, unreachable
        asm.nop()                   # 0x0010000C
        asm.addiu(T0, ZERO, 7)      # 0x00100010
        asm.label("never_reached")  # 0x00100014
        asm.jr(RA)                  # 0x00100014
        asm.nop()                   # 0x00100018
        image = _parse(asm.resolve(), path="<no-scan>")
        program = discover_program(image)

        self.assertEqual([0x00100000], sorted(program.blocks))
        entry = program.blocks[0x00100000]
        self.assertEqual("return", entry.kind)
        self.assertEqual([0x00100000, 0x00100004], entry.instruction_addresses)
        self.assertEqual((), entry.successors)
        self.assertEqual([], _call_shape(program))
        self.assertNotIn(0x00100008, program.blocks)
        self.assertNotIn(0x00100014, program.blocks)
        self.assertIsNone(program.function_at(0x00100014))
        self.assertEqual([0x00100000], [function.entry for function in program.functions])
        # The words exist and decode, proving suppression is policy, not an
        # inability to decode them.
        self.assertIn(0x00100008, program.code_words)
        self.assertIn(0x00100014, program.code_words)
        self.assertEqual(2, program.stats["decoded_instructions"])


class IndirectControlTests(unittest.TestCase):
    def test_jump_table_is_never_silently_followed(self) -> None:
        """A canonical table is either fully resolved or explicitly diagnosed.

        docs/research/function-discovery.md 3.4: an unproven transfer is never
        followed silently.  The current implementation only performs a
        backward register slice, so this test accepts either documented
        resolution or an explicit unresolved diagnostic; the strict
        all-entries-resolved contract is in
        ``test_jump_table_all_valid_entries_resolve`` below.
        """
        image, targets = _jump_table_image()
        program = discover_program(image)

        self.assertIn(0x00100000, program.blocks)
        block = program.blocks[0x00100000]
        self.assertIn(block.kind, {"indirect", "jump"})
        self.assertEqual(1, len(program.indirect_sites))
        site = program.indirect_sites[0]
        self.assertEqual(0x00100018, site.pc)
        self.assertEqual(T0, site.register)
        self.assertTrue(site.likely_jump_table)

        if site.resolved_target is None and not block.resolved_targets:
            # Safe fallback: explicit diagnostic, no guessed successors.
            self.assertTrue(program.function_at(0x00100000).has_unresolved_indirect)
            self.assertEqual([0x00100000], sorted(program.blocks))
            diagnostics = [d for d in program.diagnostics
                           if d.code == "indirect.unresolved"]
            self.assertEqual(1, len(diagnostics))
            self.assertEqual("warning", diagnostics[0].severity)
            self.assertEqual(0x00100018, diagnostics[0].address)
            self.assertEqual((), block.successors)
            self.assertEqual(1, program.stats["unresolved_indirect"])
        else:
            # Documented success path: all four valid entries are followed.
            self.assertEqual(targets, block.resolved_targets)
            for target in targets:
                self.assertIn(target, program.blocks)
            self.assertEqual(0, program.stats["unresolved_indirect"])
            self.assertFalse(any("unresolved" in diagnostic.code
                                 for diagnostic in program.diagnostics))

    @unittest.expectedFailure
    def test_jump_table_all_valid_entries_resolve(self) -> None:
        """SPEC, not current behaviour: a fully valid table resolves all entries.

        docs/research/function-discovery.md 3.4 requires that when the bounds
        guard dominates the indexed load and every one of the N aligned table
        entries canonicalises into executable code, the transfer yields all N
        targets and no unresolved entry.  Section 7's ``jump-table-4`` fixture
        expects "4 resolved targets, no unresolved entry".

        KNOWN GAP: cfg.py only performs a backward register slice.  For the
        canonical table it records an ``indirect.unresolved`` diagnostic
        ("load base of lw is not constant") and resolves zero targets; it does
        not read N table words.  This test intentionally keeps the documented
        contract and is marked expected failure until that gap is closed.
        """
        image, targets = _jump_table_image()
        program = discover_program(image)

        block = program.blocks[0x00100000]
        self.assertIn(block.kind, {"indirect", "jump"})
        self.assertTrue(program.indirect_sites[0].likely_jump_table)
        self.assertEqual(targets, block.resolved_targets)
        for target in targets:
            self.assertIn(target, program.blocks)
        self.assertEqual(0, program.stats["unresolved_indirect"])
        self.assertFalse(any("unresolved" in diagnostic.code
                             for diagnostic in program.diagnostics))

    def test_unknown_jr_register_marks_function_unresolved(self) -> None:
        """JR through a value loaded from an unknown pointer is diagnosed.

        docs/research/function-discovery.md 3.4/5: ``lw $t0,0($a0); jr $t0``
        with unknown ``$a0`` is UNRESOLVED_INDIRECT_JUMP, never a silent
        success.  ``cfg.py`` records ``has_unresolved_indirect`` on the owning
        function and an ``indirect.unresolved`` Program diagnostic.
        """
        asm = Assembler()
        asm.lw(T0, 0, A0)       # 0x00100000 - $a0 is an unknown argument
        asm.jr(T0)              # 0x00100004
        asm.nop()               # 0x00100008 - delay slot
        program = discover_program(_parse(asm.resolve(), path="<unresolved-jr>"))

        self.assertEqual([0x00100000], sorted(program.blocks))
        block = program.blocks[0x00100000]
        self.assertEqual("indirect", block.kind)
        self.assertEqual((), block.successors)
        self.assertEqual((), block.resolved_targets)
        # The trailing NOP is the delay slot; the control transfer is JR.
        self.assertEqual(["jr"], [insn.mnemonic for insn in block.instructions
                                  if insn.is_control])

        self.assertEqual(1, len(program.indirect_sites))
        site = program.indirect_sites[0]
        self.assertEqual(0x00100004, site.pc)
        self.assertEqual(T0, site.register)
        self.assertIsNone(site.resolved_target)
        self.assertFalse(site.likely_jump_table)

        function = program.function_at(0x00100000)
        self.assertIsNotNone(function)
        self.assertTrue(function.has_unresolved_indirect)
        self.assertEqual(1, program.stats["unresolved_indirect"])

        diagnostics = [d for d in program.diagnostics if d.code == "indirect.unresolved"]
        self.assertEqual(1, len(diagnostics))
        self.assertEqual("warning", diagnostics[0].severity)
        self.assertEqual(0x00100004, diagnostics[0].address)
        self.assertIn("Unresolved jr $t0", diagnostics[0].message)
        self.assertFalse(any(d.code == "indirect.resolved" for d in program.diagnostics))


class TraversalRobustnessTests(unittest.TestCase):
    def test_unsupported_instruction_marks_block_unsupported(self) -> None:
        """A reachable COP1 word is decoded for diagnosis, never lowered.

        docs/research/function-discovery.md 2/5: unsupported encodings are
        explicit (UNKNOWN_INSTRUCTION / unsupported block), not silently
        skipped.  The trailing JR/NOP must not be reached because decoding
        stops at the unsupported word.
        """
        asm = Assembler()
        asm.addiu(T0, ZERO, 1)              # 0x00100000
        asm.emit(encode_i(0x11, 0, 0, 0))   # 0x00100004 - COP1, unsupported
        asm.jr(RA)                          # 0x00100008 - must stay undecoded
        asm.nop()                           # 0x0010000C
        program = discover_program(_parse(asm.resolve(), path="<unsupported-cop1>"))

        self.assertEqual([0x00100000], sorted(program.blocks))
        block = program.blocks[0x00100000]
        self.assertEqual("unsupported", block.kind)
        self.assertEqual([0x00100000, 0x00100004], block.instruction_addresses)
        self.assertEqual("cop1", block.instructions[-1].mnemonic)
        self.assertFalse(block.instructions[-1].supported)
        self.assertFalse(block.supported)
        self.assertIn("COP1", block.problem)
        self.assertEqual((), block.successors)

        diagnostics = [d for d in program.diagnostics
                       if d.code == "block.unsupported_instruction"]
        self.assertEqual(1, len(diagnostics))
        self.assertEqual(0x00100004, diagnostics[0].address)
        self.assertEqual("warning", diagnostics[0].severity)
        self.assertIn("not supported", diagnostics[0].message)
        self.assertEqual([block], program.unsupported_blocks())
        self.assertEqual(1, program.stats["unsupported_instructions"])
        self.assertNotIn(0x00100008, program.blocks)

    def test_discovery_is_deterministic(self) -> None:
        """Two runs on one image produce identical, sorted results.

        docs/research/function-discovery.md 4 and 7: report order is numeric
        and two runs are identical; no timestamps or set-order leakage.
        """
        image = _branch_split_image()
        first = discover_program(image)
        second = discover_program(image)

        self.assertEqual(first.entry, second.entry)
        self.assertEqual(sorted(first.blocks), sorted(second.blocks))
        self.assertEqual([0x00100000, 0x00100010, 0x0010001C],
                         sorted(first.blocks))
        self.assertEqual(_function_shape(first), _function_shape(second))
        self.assertEqual(
            [(0x00100000, "sub_00100000", "entry",
              [0x00100000, 0x00100010, 0x0010001C])],
            _function_shape(first),
        )
        self.assertEqual(first.blocks, second.blocks)
        self.assertEqual(first.functions, second.functions)
        self.assertEqual(first.call_edges, second.call_edges)
        self.assertEqual(first.indirect_sites, second.indirect_sites)
        self.assertEqual(first.diagnostics, second.diagnostics)
        self.assertEqual(first.roots, second.roots)
        self.assertEqual(first.stats, second.stats)
        self.assertTrue(first.diagnostics)  # the block.split event is compared too


if __name__ == "__main__":
    unittest.main(verbosity=2)
