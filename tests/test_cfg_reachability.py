# SPDX-License-Identifier: GPL-3.0-or-later
"""Synthetic-only tests for conservative known-edge CFG graph reachability.

The fixtures are assembled at test time from the existing encoder helpers.
They do not claim runtime reachability, dead-code status or function extents.
"""
from __future__ import annotations

from dataclasses import replace
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


spike = load_module("rptp_gate0_spike_reachability", "tools/rptp_gate0_spike.py")
ir = load_module("rptp_ir_reachability", "tools/rptp_ir.py")

BASE = spike.BASE
ZERO = spike.ZERO
T0 = spike.T0
T1 = spike.T1
RA = spike.RA


def nop_word() -> int:
    return spike.encode_r(ZERO, ZERO, ZERO, 0, 0x00)


def jr_register_word(register: int) -> int:
    return spike.encode_r(register, ZERO, ZERO, 0, 0x08)


def linear_words() -> dict[int, int]:
    return {
        BASE: spike.encode_i(0x09, ZERO, T0, 1),
        BASE + 4: spike.encode_i(0x09, ZERO, T1, 2),
        BASE + 8: nop_word(),
    }


def conditional_words() -> dict[int, int]:
    return {
        BASE: spike.encode_i(0x04, T0, ZERO, 2),
        BASE + 4: nop_word(),
        BASE + 8: nop_word(),
        BASE + 0x0C: nop_word(),
    }


def direct_transfer_words(opcode: int) -> dict[int, int]:
    return {
        BASE: spike.encode_j(opcode, BASE + 0x0C),
        BASE + 4: nop_word(),
        BASE + 8: nop_word(),
        BASE + 0x0C: nop_word(),
    }


class KnownEdgeGraphTests(unittest.TestCase):
    def test_linear_graph_reaches_every_block_and_reports_the_model(self):
        result = ir.analyze_words(BASE, linear_words())

        report = ir.analyze_known_edge_reachability(result, BASE)

        self.assertEqual(report.root_pc, BASE)
        self.assertEqual(report.reached_block_starts, (BASE,))
        self.assertEqual(report.not_reached_block_starts, ())
        self.assertEqual(report.unresolved_transfer_blocks, ())
        self.assertEqual(report.direct_call_blocks, ())
        self.assertEqual(report.to_dict()["model"], "known_edge_cfg_graph")
        self.assertTrue(any("not proof of semantic unreachability" in line for line in report.limitations))
        self.assertTrue(any("not runtime reachability" in line for line in report.limitations))
        self.assertTrue(any("function-extent" in line for line in report.limitations))

    def test_conditional_branch_reaches_both_recorded_successors(self):
        result = ir.analyze_words(BASE, conditional_words())

        report = ir.analyze_known_edge_reachability(result, BASE)

        self.assertEqual(
            report.reached_block_starts,
            (BASE, BASE + 8, BASE + 0x0C),
        )
        self.assertEqual(report.not_reached_block_starts, ())

    def test_explicit_root_can_differ_from_the_analysis_entry(self):
        result = ir.analyze_words(BASE, conditional_words())

        report = ir.analyze_known_edge_reachability(result, BASE + 8)

        self.assertEqual(report.root_pc, BASE + 8)
        self.assertEqual(report.reached_block_starts, (BASE + 8, BASE + 0x0C))
        self.assertEqual(report.not_reached_block_starts, (BASE,))

    def test_direct_jump_follows_only_its_stored_target(self):
        result = ir.analyze_words(BASE, direct_transfer_words(0x02))

        report = ir.analyze_known_edge_reachability(result, BASE)

        self.assertEqual(report.reached_block_starts, (BASE, BASE + 0x0C))
        self.assertEqual(report.not_reached_block_starts, (BASE + 8,))

    def test_direct_call_has_no_synthesized_return_edge(self):
        result = ir.analyze_words(BASE, direct_transfer_words(0x03))

        report = ir.analyze_known_edge_reachability(result, BASE)

        self.assertEqual(report.reached_block_starts, (BASE, BASE + 0x0C))
        self.assertEqual(report.not_reached_block_starts, (BASE + 8,))
        self.assertEqual(report.direct_call_blocks, (BASE,))
        self.assertTrue(any("no modeled return edge" in line for line in report.limitations))

    def test_unreferenced_block_is_only_not_graph_reached(self):
        result = ir.analyze_words(BASE, direct_transfer_words(0x02))

        report = ir.analyze_known_edge_reachability(result, BASE)

        self.assertEqual(report.not_reached_block_starts, (BASE + 8,))
        self.assertTrue(any("not proof of semantic unreachability" in line for line in report.limitations))
        self.assertTrue(any("dead code" in line for line in report.limitations))

    def test_multiple_not_reached_blocks_are_reported_in_stable_order(self):
        words = {
            BASE: spike.encode_j(0x02, BASE + 0x1C),
            BASE + 4: nop_word(),
            BASE + 8: spike.encode_j(0x02, BASE + 0x14),
            BASE + 0x0C: nop_word(),
            BASE + 0x10: nop_word(),
            BASE + 0x14: nop_word(),
            BASE + 0x18: nop_word(),
            BASE + 0x1C: nop_word(),
        }
        result = ir.analyze_words(BASE, words)

        report = ir.analyze_known_edge_reachability(result, BASE)

        self.assertEqual(report.reached_block_starts, (BASE, BASE + 0x1C))
        self.assertEqual(
            report.not_reached_block_starts,
            (BASE + 8, BASE + 0x10, BASE + 0x14),
        )

    def test_indirect_jump_reports_no_guessed_successor(self):
        words = {
            BASE: jr_register_word(T0),
            BASE + 4: nop_word(),
            BASE + 8: nop_word(),
        }
        result = ir.analyze_words(BASE, words)
        jump_block = next(block for block in result.blocks if block.start_pc == BASE)
        self.assertEqual(jump_block.successors, ())

        report = ir.analyze_known_edge_reachability(result, BASE)

        self.assertEqual(report.reached_block_starts, (BASE,))
        self.assertEqual(report.not_reached_block_starts, (BASE + 8,))
        self.assertEqual(report.unresolved_transfer_blocks, (BASE,))
        self.assertTrue(any("unresolved indirect jump" in line for line in report.limitations))

    def test_return_candidate_is_reported_as_an_unresolved_transfer(self):
        words = {
            BASE: jr_register_word(RA),
            BASE + 4: nop_word(),
            BASE + 8: nop_word(),
        }
        result = ir.analyze_words(BASE, words)

        report = ir.analyze_known_edge_reachability(result, BASE)

        self.assertEqual(report.reached_block_starts, (BASE,))
        self.assertEqual(report.not_reached_block_starts, (BASE + 8,))
        self.assertEqual(report.unresolved_transfer_blocks, (BASE,))


class ReachabilityRootFailureTests(unittest.TestCase):
    def assert_reachability_error(self, code: str, result, root_pc) -> None:
        with self.assertRaises(ir.AnalysisError) as caught:
            ir.analyze_known_edge_reachability(result, root_pc)
        self.assertEqual(caught.exception.code, code)

    def test_unaligned_root_is_rejected(self):
        result = ir.analyze_words(BASE, conditional_words())
        self.assert_reachability_error(ir.IR_REACHABILITY_UNALIGNED_ROOT, result, BASE + 2)

    def test_non_block_start_root_is_rejected(self):
        result = ir.analyze_words(BASE, linear_words())
        self.assert_reachability_error(ir.IR_REACHABILITY_ROOT_NOT_BLOCK_START, result, BASE + 4)

    def test_delay_slot_root_is_rejected(self):
        result = ir.analyze_words(BASE, conditional_words())
        self.assert_reachability_error(ir.IR_REACHABILITY_ROOT_IN_DELAY_SLOT, result, BASE + 4)

    def test_out_of_range_root_is_rejected(self):
        result = ir.analyze_words(BASE, linear_words())
        self.assert_reachability_error(ir.IR_REACHABILITY_ROOT_OUT_OF_RANGE, result, BASE + 0x100)

    def test_non_integer_root_is_rejected(self):
        result = ir.analyze_words(BASE, linear_words())
        self.assert_reachability_error(ir.IR_REACHABILITY_INVALID_ROOT, result, None)
        self.assert_reachability_error(ir.IR_REACHABILITY_INVALID_ROOT, result, True)


class ReachabilityValidationTests(unittest.TestCase):
    def assert_invalid_block(self, result, root_pc: int = BASE) -> None:
        with self.assertRaises(ir.AnalysisError) as caught:
            ir.analyze_known_edge_reachability(result, root_pc)
        self.assertEqual(caught.exception.code, ir.IR_REACHABILITY_INVALID_BLOCK)

    def test_missing_duplicate_and_overlapping_blocks_are_rejected(self):
        result = ir.analyze_words(BASE, conditional_words())
        blocks = result.blocks

        self.assert_invalid_block(replace(result, blocks=blocks[:-1]))
        self.assert_invalid_block(replace(result, blocks=blocks + (blocks[0],)))

        overlapping = (
            replace(blocks[0], end_pc=blocks[0].end_pc + 4),
            *blocks[1:],
        )
        self.assert_invalid_block(replace(result, blocks=overlapping))

    def test_malformed_successor_is_rejected(self):
        result = ir.analyze_words(BASE, conditional_words())
        blocks = tuple(
            replace(block, successors=(BASE + 0x100,))
            if block.start_pc == BASE
            else block
            for block in result.blocks
        )

        self.assert_invalid_block(replace(result, blocks=blocks))

    def test_invalid_result_objects_are_rejected(self):
        with self.assertRaises(ir.AnalysisError) as caught:
            ir.analyze_known_edge_reachability(None, BASE)
        self.assertEqual(caught.exception.code, ir.IR_REACHABILITY_INVALID_RESULT)

        result = ir.analyze_words(BASE, linear_words())
        with self.assertRaises(ir.AnalysisError) as caught:
            ir.analyze_known_edge_reachability(replace(result, blocks=()), BASE)
        self.assertEqual(caught.exception.code, ir.IR_REACHABILITY_INVALID_RESULT)


class ReachabilityStabilityTests(unittest.TestCase):
    def test_repeated_analysis_is_equal_and_does_not_mutate_the_result(self):
        result = ir.analyze_words(BASE, conditional_words())
        before = result.to_dict()

        first = ir.analyze_known_edge_reachability(result, BASE)
        second = ir.analyze_known_edge_reachability(result, BASE)

        self.assertEqual(first, second)
        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual(json.dumps(first.to_dict(), sort_keys=True), json.dumps(second.to_dict(), sort_keys=True))
        self.assertEqual(result.to_dict(), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
