# SPDX-License-Identifier: GPL-3.0-or-later
"""Synthetic-only contract tests for the minimal IR and control-flow analysis.

The CFG fixture is assembled at test time from the existing encoder helpers in
``tools/rptp_gate0_spike.py``. No binary fixture is written or committed.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module {relative_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


spike = load_module("rptp_gate0_spike_ir", "tools/rptp_gate0_spike.py")
ir = load_module("rptp_ir_under_test", "tools/rptp_ir.py")

BASE = spike.BASE
ZERO = spike.ZERO
V0 = spike.V0
T0 = spike.T0
T1 = spike.T1
T2 = spike.T2
T3 = spike.T3
S0 = spike.S0
S1 = spike.S1
S2 = spike.S2
S3 = spike.S3
RA = spike.RA


def nop_word() -> int:
    return spike.encode_r(ZERO, ZERO, ZERO, 0, 0x00)


def jr_ra_word() -> int:
    return spike.encode_r(RA, ZERO, ZERO, 0, 0x08)


def ir_fixture_rows() -> list[tuple[int, str, int]]:
    rows = [
        ("set_t0", spike.encode_i(0x09, ZERO, T0, 1)),
        ("set_t1_ori", spike.encode_i(0x0D, ZERO, T1, 0x8001)),
        ("beq_to_branch_target", spike.encode_i(0x04, T0, ZERO, 3)),
        ("beq_delay", spike.encode_i(0x09, ZERO, S0, 7)),
        ("jump_to_return_block", spike.encode_j(0x02, BASE + 0x20)),
        ("jump_delay", spike.encode_i(0x09, ZERO, S1, 9)),
        ("jal_to_callee", spike.encode_j(0x03, BASE + 0x30)),
        ("jal_delay", spike.encode_i(0x09, ZERO, S2, 11)),
        ("return_candidate", jr_ra_word()),
        ("return_delay", spike.encode_i(0x09, ZERO, S3, 13)),
        ("unreachable_nop_1", nop_word()),
        ("unreachable_nop_2", nop_word()),
        ("callee", spike.encode_i(0x09, ZERO, V0, 42)),
        ("callee_return", jr_ra_word()),
        ("callee_delay", nop_word()),
    ]
    return [(BASE + index * 4, name, word) for index, (name, word) in enumerate(rows)]


def analyze_rows(rows: list[tuple[int, str, int]]):
    data = spike.build_elf_from_rows(rows)
    return data, ir.analyze_elf(data)


def flat_instruction_pcs(result) -> list[int]:
    return [instruction.pc for block in result.blocks for instruction in block.instructions]


class IrInstructionTests(unittest.TestCase):
    def test_non_control_instructions_preserve_operands_words_and_immediate_kinds(self):
        words = {
            BASE: spike.encode_r(T0, T1, T2, 0, 0x21),
            BASE + 4: spike.encode_i(0x09, ZERO, T0, -1),
            BASE + 8: spike.encode_i(0x0D, ZERO, T1, 0xFFFF),
            BASE + 12: spike.encode_i(0x23, T0, T3, 4),
            BASE + 16: spike.encode_i(0x2B, T0, T3, 8),
            BASE + 20: nop_word(),
        }
        result = ir.analyze_words(BASE, words)
        by_pc = {instruction.pc: instruction for instruction in result.instructions}

        addu = by_pc[BASE]
        self.assertEqual(addu.op, "addu")
        self.assertEqual(addu.word, words[BASE])
        self.assertEqual((addu.rs, addu.rt, addu.rd), (T0, T1, T2))
        self.assertEqual(addu.destination_register, T2)
        self.assertIsNone(addu.immediate)
        self.assertIsNone(addu.immediate_kind)
        self.assertEqual(addu.control, ir.FALLTHROUGH)

        addiu = by_pc[BASE + 4]
        self.assertEqual(addiu.op, "addiu")
        self.assertEqual(addiu.immediate, -1)
        self.assertEqual(addiu.immediate_kind, ir.SIGNED16)
        self.assertEqual(addiu.destination_register, T0)

        ori = by_pc[BASE + 8]
        self.assertEqual(ori.op, "ori")
        self.assertEqual(ori.immediate, 0xFFFF)
        self.assertEqual(ori.immediate_kind, ir.ZERO16)
        self.assertEqual(ori.destination_register, T1)

        lw = by_pc[BASE + 12]
        self.assertEqual(lw.op, "lw")
        self.assertEqual(lw.immediate, 4)
        self.assertEqual(lw.immediate_kind, ir.SIGNED16)
        self.assertEqual(lw.destination_register, T3)

        sw = by_pc[BASE + 16]
        self.assertEqual(sw.op, "sw")
        self.assertEqual(sw.immediate, 8)
        self.assertEqual(sw.immediate_kind, ir.SIGNED16)
        self.assertIsNone(sw.destination_register)

        nop = by_pc[BASE + 20]
        self.assertEqual(nop.op, "nop")
        self.assertIsNone(nop.destination_register)
        self.assertEqual(nop.control, ir.FALLTHROUGH)

    def test_zero_register_writes_are_not_modeled_as_destinations(self):
        words = {
            BASE: spike.encode_i(0x0D, ZERO, ZERO, 0xFFFF),
            BASE + 4: spike.encode_i(0x09, ZERO, ZERO, 1),
            BASE + 8: spike.encode_r(T0, T1, ZERO, 0, 0x21),
            BASE + 12: spike.encode_i(0x23, T0, ZERO, 0),
            BASE + 16: spike.encode_i(0x2B, T1, T0, 0),
            BASE + 20: nop_word(),
        }
        result = ir.analyze_words(BASE, words)
        by_pc = {instruction.pc: instruction for instruction in result.instructions}

        for pc in (BASE, BASE + 4, BASE + 8, BASE + 12):
            with self.subTest(pc=pc):
                self.assertIsNone(by_pc[pc].destination_register)
        self.assertEqual(by_pc[BASE].rs, ZERO)
        self.assertEqual(by_pc[BASE + 4].rs, ZERO)
        self.assertEqual(by_pc[BASE + 8].rd, ZERO)
        self.assertEqual(by_pc[BASE + 12].rt, ZERO)
        self.assertIsNone(by_pc[BASE + 16].destination_register)

    def test_jal_records_ra_as_its_modeled_destination(self):
        words = [
            spike.encode_j(0x03, BASE + 0x0C),
            nop_word(),
            nop_word(),
            jr_ra_word(),
            nop_word(),
        ]
        rows = [(BASE + index * 4, f"i{index}", word) for index, word in enumerate(words)]
        _, result = analyze_rows(rows)
        by_pc = {instruction.pc: instruction for instruction in result.instructions}

        self.assertEqual(by_pc[BASE].control, ir.DIRECT_CALL)
        self.assertEqual(by_pc[BASE].destination_register, RA)
        self.assertEqual(by_pc[BASE].target, BASE + 0x0C)


class ControlFlowTests(unittest.TestCase):
    def test_straight_line_sequence_forms_one_block(self):
        words = {
            BASE: spike.encode_i(0x09, ZERO, T0, 1),
            BASE + 4: spike.encode_i(0x09, ZERO, T1, 2),
            BASE + 8: spike.encode_i(0x0D, ZERO, T2, 3),
        }
        result = ir.analyze_words(BASE, words)

        self.assertEqual(len(result.blocks), 1)
        block = result.blocks[0]
        self.assertEqual((block.start_pc, block.end_pc), (BASE, BASE + 12))
        self.assertEqual([instruction.pc for instruction in block.instructions], [BASE, BASE + 4, BASE + 8])
        self.assertEqual(block.successors, ())
        self.assertIsNone(block.terminator)

    def test_bne_creates_target_and_fallthrough_successors(self):
        words = {
            BASE: spike.encode_i(0x05, T0, T1, 2),
            BASE + 4: nop_word(),
            BASE + 8: spike.encode_i(0x09, ZERO, S0, 1),
            BASE + 12: spike.encode_i(0x09, ZERO, S1, 2),
        }
        result = ir.analyze_words(BASE, words)
        blocks = {block.start_pc: block for block in result.blocks}

        self.assertEqual([block.start_pc for block in result.blocks], [BASE, BASE + 8, BASE + 12])
        branch_block = blocks[BASE]
        self.assertEqual(branch_block.terminator.op, "bne")
        self.assertEqual(branch_block.terminator.control, ir.CONDITIONAL_BRANCH)
        self.assertEqual(branch_block.terminator.target, BASE + 12)
        self.assertEqual(branch_block.successors, (BASE + 12, BASE + 8))
        self.assertEqual(blocks[BASE + 8].successors, (BASE + 12,))
        self.assertEqual(blocks[BASE + 12].successors, ())

    def test_direct_jump_and_call_targets_are_explicit(self):
        _, result = analyze_rows(ir_fixture_rows())
        blocks = {block.start_pc: block for block in result.blocks}
        by_pc = {instruction.pc: instruction for instruction in result.instructions}

        jump = by_pc[BASE + 0x10]
        self.assertEqual(jump.control, ir.DIRECT_JUMP)
        self.assertEqual(jump.target, BASE + 0x20)
        self.assertEqual(blocks[BASE + 0x10].successors, (BASE + 0x20,))

        call = by_pc[BASE + 0x18]
        self.assertEqual(call.control, ir.DIRECT_CALL)
        self.assertEqual(call.target, BASE + 0x30)
        self.assertEqual(blocks[BASE + 0x18].successors, (BASE + 0x30,))

    def test_delay_slots_are_owned_by_transfer_blocks_exactly_once(self):
        _, result = analyze_rows(ir_fixture_rows())
        transfers = [instruction for instruction in result.instructions if instruction.is_control_transfer]
        blocks_by_start = {block.start_pc: block for block in result.blocks}
        owner_by_slot = {}

        self.assertEqual(
            [instruction.pc for instruction in transfers],
            [BASE + 0x08, BASE + 0x10, BASE + 0x18, BASE + 0x20, BASE + 0x34],
        )
        for transfer in transfers:
            block = next(block for block in result.blocks if block.start_pc <= transfer.pc < block.end_pc)
            slot_pc = transfer.pc + 4
            slot = next(instruction for instruction in block.instructions if instruction.pc == slot_pc)
            self.assertEqual(slot.delay_slot_for, transfer.pc)
            self.assertEqual(block.end_pc, transfer.pc + 8)
            self.assertNotIn(slot_pc, blocks_by_start)
            owner_by_slot.setdefault(slot_pc, []).append(transfer.pc)

        self.assertEqual(set(owner_by_slot), {BASE + 0x0C, BASE + 0x14, BASE + 0x1C, BASE + 0x24, BASE + 0x38})
        self.assertTrue(all(len(owners) == 1 for owners in owner_by_slot.values()))
        self.assertEqual(len(flat_instruction_pcs(result)), len(result.instructions))
        self.assertEqual(sorted(flat_instruction_pcs(result)), [instruction.pc for instruction in result.instructions])

    def test_jr_ra_is_a_return_candidate_without_a_guessed_successor(self):
        _, result = analyze_rows(ir_fixture_rows())
        blocks = {block.start_pc: block for block in result.blocks}
        block = blocks[BASE + 0x20]

        self.assertEqual(block.terminator.op, "jr")
        self.assertEqual(block.terminator.control, ir.RETURN_CANDIDATE)
        self.assertIsNone(block.terminator.target)
        self.assertEqual(block.successors, ())
        self.assertEqual(block.instructions[-1].delay_slot_for, BASE + 0x20)

    def test_jr_to_another_register_stays_indirect(self):
        words = {
            BASE: spike.encode_r(T0, ZERO, ZERO, 0, 0x08),
            BASE + 4: nop_word(),
        }
        result = ir.analyze_words(BASE, words)

        self.assertEqual(len(result.blocks), 1)
        self.assertEqual(result.blocks[0].terminator.control, ir.INDIRECT_JUMP)
        self.assertEqual(result.blocks[0].successors, ())

    def test_block_partition_is_ordered_and_covers_every_instruction_once(self):
        _, result = analyze_rows(ir_fixture_rows())

        self.assertEqual(
            [block.start_pc for block in result.blocks],
            [BASE, BASE + 0x10, BASE + 0x18, BASE + 0x20, BASE + 0x28, BASE + 0x30],
        )
        self.assertEqual([block.end_pc for block in result.blocks], [BASE + 0x10, BASE + 0x18, BASE + 0x20, BASE + 0x28, BASE + 0x30, BASE + 0x3C])
        self.assertEqual(flat_instruction_pcs(result), [BASE + index * 4 for index in range(15)])


class IrCfgFailureTests(unittest.TestCase):
    def assert_analysis_error(self, code: str, entry: int, words: dict[int, int], **kwargs):
        with self.assertRaises(ir.AnalysisError) as caught:
            ir.analyze_words(entry, words, **kwargs)
        self.assertEqual(caught.exception.code, code)
        return caught.exception

    def test_target_outside_executable_range_is_rejected(self):
        words = {
            BASE: spike.encode_i(0x04, T0, ZERO, 4),
            BASE + 4: nop_word(),
            BASE + 8: nop_word(),
        }
        error = self.assert_analysis_error(ir.IR_TARGET_OUT_OF_RANGE, BASE, words)
        self.assertEqual(error.pc, BASE + 0x14)

    def test_unaligned_pc_and_entry_are_rejected(self):
        self.assert_analysis_error(ir.IR_UNALIGNED_PC, BASE, {BASE: nop_word(), BASE + 2: nop_word()})
        self.assert_analysis_error(ir.IR_UNALIGNED_ENTRY, BASE + 2, {BASE + 2: nop_word()})

    def test_truncated_stream_and_missing_delay_slot_are_rejected(self):
        self.assert_analysis_error(ir.IR_MISSING_DELAY_SLOT, BASE, {BASE: jr_ra_word()})

        words = {
            BASE: spike.encode_i(0x04, T0, ZERO, -1),
            BASE + 4: nop_word(),
        }
        self.assert_analysis_error(ir.IR_FALLTHROUGH_OUT_OF_RANGE, BASE, words)

        self.assert_analysis_error(ir.IR_NON_CONTIGUOUS_CODE, BASE, {BASE: nop_word(), BASE + 8: nop_word()})

    def test_jump_target_into_its_own_delay_slot_is_rejected(self):
        words = {
            BASE: spike.encode_j(0x02, BASE + 4),
            BASE + 4: nop_word(),
            BASE + 8: nop_word(),
        }
        self.assert_analysis_error(ir.IR_TARGET_IN_DELAY_SLOT, BASE, words)

    def test_unsupported_and_malformed_inputs_fail_closed(self):
        error = self.assert_analysis_error(ir.IR_UNSUPPORTED_INSTRUCTION, BASE, {BASE: 0xFC000000})
        self.assertEqual(error.pc, BASE)
        self.assert_analysis_error(ir.IR_EMPTY_CODE, BASE, {})
        self.assert_analysis_error(ir.IR_LIMIT_EXCEEDED, BASE, {BASE: nop_word(), BASE + 4: nop_word()}, max_instructions=1)
        self.assert_analysis_error(ir.IR_CONTROL_IN_DELAY_SLOT, BASE, {BASE: jr_ra_word(), BASE + 4: jr_ra_word(), BASE + 8: nop_word()})

        with self.assertRaises(ir.AnalysisError) as caught:
            ir.analyze_elf(b"\x7fELF\x01\x01")
        self.assertEqual(caught.exception.code, ir.IR_ELF_INVALID)

    def test_analysis_result_is_deterministic(self):
        data, result = analyze_rows(ir_fixture_rows())
        _, second = analyze_rows(ir_fixture_rows())

        self.assertEqual(data, spike.build_elf_from_rows(ir_fixture_rows()))
        self.assertEqual(result.to_dict(), second.to_dict())
        self.assertEqual(json.dumps(result.to_dict(), sort_keys=True), json.dumps(second.to_dict(), sort_keys=True))


class IrCfgRegressionTests(unittest.TestCase):
    def test_elf_analysis_reports_range_blocks_and_candidate_only_functions(self):
        data, result = analyze_rows(ir_fixture_rows())

        self.assertEqual(hashlib.sha256(data).hexdigest(), hashlib.sha256(spike.build_elf_from_rows(ir_fixture_rows())).hexdigest())
        self.assertEqual(result.entry, BASE)
        self.assertEqual((result.code_start, result.code_end), (BASE, BASE + 0x3C))
        self.assertEqual(len(result.instructions), 15)
        self.assertEqual(len(result.blocks), 6)

        candidates = {candidate.address: candidate for candidate in result.function_entries}
        self.assertEqual(list(candidates), [BASE, BASE + 0x30])
        self.assertEqual(candidates[BASE].origins, (ir.ORIGIN_ELF_ENTRY,))
        self.assertEqual(candidates[BASE].call_sites, ())
        self.assertEqual(candidates[BASE + 0x30].origins, (ir.ORIGIN_JAL_TARGET,))
        self.assertEqual(candidates[BASE + 0x30].call_sites, (BASE + 0x18,))
        for candidate in candidates.values():
            self.assertEqual(candidate.confidence, ir.CANDIDATE_CONFIDENCE)
            self.assertEqual(candidate.limitations, ir.CANDIDATE_LIMITATIONS)

    def test_gate0_and_ori_artifact_hashes_are_unchanged(self):
        gate0_entry, gate0_words, _ = spike.parse_elf(spike.build_fixture_elf())
        gate0_source = spike.emit_cpp(spike.decode_program(gate0_words), gate0_entry)
        self.assertEqual(
            hashlib.sha256(spike.build_fixture_elf()).hexdigest(),
            "b21f1f7793236d1ccba7308cc82f42d9f89915c87c0b037c46d8170f28349ca9",
        )
        self.assertEqual(
            hashlib.sha256(gate0_source.encode("utf-8")).hexdigest(),
            "5316e0f51ba8b1fa1252e409f38cb9ac7db7606fee17b28ef0dcf1be162ae795",
        )

        ori_entry, ori_words, _ = spike.parse_elf(spike.build_ori_fixture_elf())
        ori_source = spike.emit_cpp(spike.decode_program(ori_words), ori_entry)
        self.assertEqual(
            hashlib.sha256(spike.build_ori_fixture_elf()).hexdigest(),
            "6c04b37fb40b3e7eaa29f82e7f21795bf930f0668aade41d04b1e058b8ff6dbc",
        )
        self.assertEqual(
            hashlib.sha256(ori_source.encode("utf-8")).hexdigest(),
            "9d0d9fe3af4f1198cab447e802d364cf6b38dc00137f3583d0d6361ad2a50672",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
