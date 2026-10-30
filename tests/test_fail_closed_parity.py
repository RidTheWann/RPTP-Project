# SPDX-License-Identifier: GPL-3.0-or-later
"""E4 evidence: canonical, legacy and native paths reject the same delay-slot failures.

ADR-0005 gate E4 asks whether every in-scope path fails closed on the same
failure classes.  Identical messages are not required; equivalent rejection
is.  This module covers two classes:

* ``missing delay slot``: a control transfer whose delay slot lies outside
  the file-backed code; and
* ``control transfer in a delay slot``: a control transfer inside another
  transfer's delay slot.

The canonical path reports a typed CFG diagnostic, marks the block
``unsupported`` and the oracle refuses to execute it.  The frozen legacy IR
raises ``AnalysisError`` with its documented code before lowering can run.
The native harness, when ``RPTP_RUN_BINARY`` names a built executable, reports
its stable ``EXEC_*`` code with exit status 2.  A skipped harness leg is not a
pass.

The fixture words are RPTP test definitions built from the existing ``JR``
encoding helper.  This module records evidence only: it does not close E4,
declare the canonical path (ADR-0005 stays Proposed), change any Gate or claim
hardware behaviour.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from tests.test_path_contract import load_module
from tests.test_runtime_execution import BASE, build_program, encode_r
from tools.rptp import oracle
from tools.rptp.cfg import discover_program
from tools.rptp.elf import parse_elf_bytes
from tools.rptp.oracle import ExecutionError

legacy_ir = load_module("rptp_ir_e4", "tools/rptp_ir.py")

BINARY = os.environ.get("RPTP_RUN_BINARY", "")
JR_RA = encode_r(31, 0, 0, 0, 0x08)
NOP = encode_r(0, 0, 0, 0, 0)


@dataclass(frozen=True)
class DelaySlotCase:
    label: str
    words: tuple[int, ...]
    canonical_problem: str
    canonical_diagnostic: str
    canonical_message: str
    legacy_code: str
    legacy_pc: int
    runtime_code: str
    runtime_message: str


CASES = (
    DelaySlotCase(
        label="missing delay slot",
        words=(JR_RA,),
        canonical_problem="missing delay slot",
        canonical_diagnostic="block.missing_delay_slot",
        canonical_message="no file-backed delay slot",
        legacy_code=legacy_ir.IR_MISSING_DELAY_SLOT,
        legacy_pc=BASE,
        runtime_code="EXEC_DELAY_SLOT_MISSING",
        runtime_message="missing delay-slot instruction",
    ),
    DelaySlotCase(
        label="control transfer in a delay slot",
        words=(JR_RA, JR_RA, NOP),
        canonical_problem="control transfer in delay slot",
        canonical_diagnostic="block.control_in_delay_slot",
        canonical_message="unpredictable",
        legacy_code=legacy_ir.IR_CONTROL_IN_DELAY_SLOT,
        legacy_pc=BASE + 4,
        runtime_code="EXEC_DELAY_SLOT_CONTROL",
        runtime_message="control transfer in a delay slot",
    ),
)


class CanonicalAndLegacyDelaySlotTests(unittest.TestCase):
    def assert_canonical_rejects(self, case: DelaySlotCase) -> None:
        image = build_program(list(case.words))
        program = discover_program(parse_elf_bytes(image))
        block = program.blocks[BASE]
        self.assertEqual("unsupported", block.kind)
        self.assertEqual(case.canonical_problem, block.problem)
        self.assertFalse(block.supported)

        diagnostics = [d for d in program.diagnostics
                       if d.code == case.canonical_diagnostic]
        self.assertEqual(1, len(diagnostics))
        self.assertEqual("error", diagnostics[0].severity)
        self.assertIn(case.canonical_message, diagnostics[0].message)

        with self.assertRaisesRegex(ExecutionError, "unsupported block"):
            oracle.run_oracle(program)

    def assert_legacy_rejects(self, case: DelaySlotCase) -> None:
        image = build_program(list(case.words))
        with self.assertRaises(legacy_ir.AnalysisError) as caught:
            legacy_ir.analyze_elf(image)
        self.assertEqual(case.legacy_code, caught.exception.code)
        self.assertEqual(case.legacy_pc, caught.exception.pc)

    def test_missing_delay_slot_is_rejected_by_canonical_and_legacy_paths(self) -> None:
        case = CASES[0]
        self.assert_canonical_rejects(case)
        self.assert_legacy_rejects(case)

    def test_control_transfer_in_delay_slot_is_rejected_by_canonical_and_legacy_paths(self) -> None:
        case = CASES[1]
        self.assert_canonical_rejects(case)
        self.assert_legacy_rejects(case)


@unittest.skipUnless(BINARY and Path(BINARY).is_file(),
                     "RPTP_RUN_BINARY is not a built executable")
class NativeDelaySlotFailClosedTests(unittest.TestCase):
    def run_cli(self, image: bytes, *arguments: str) -> subprocess.CompletedProcess[str]:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "input.elf"
        path.write_bytes(image)
        return subprocess.run(
            [BINARY, *arguments, str(path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )

    def test_delay_slot_failures_report_stable_codes(self) -> None:
        for case in CASES:
            with self.subTest(case=case.label):
                image = build_program(list(case.words))
                first = self.run_cli(image, "--json")
                self.assertEqual(2, first.returncode, first.stderr)
                self.assertEqual("", first.stderr.strip())

                document = json.loads(first.stdout)
                self.assertEqual("error", document["status"])
                self.assertEqual(case.runtime_code, document["error"]["code"])
                self.assertIn(case.runtime_message, document["error"]["message"])
                self.assertIn("0x00100004", document["error"]["message"])
                self.assertNotIn("steps", document)

                second = self.run_cli(image, "--json")
                self.assertEqual(first.stdout, second.stdout)
                self.assertEqual(2, second.returncode)


if __name__ == "__main__":
    unittest.main()
