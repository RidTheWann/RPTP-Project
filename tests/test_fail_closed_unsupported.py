# SPDX-License-Identifier: GPL-3.0-or-later
"""E4 evidence: canonical, legacy and native paths reject unsupported encodings.

ADR-0005 gate E4 asks whether every in-scope path fails closed on the same
failure classes.  Identical messages are not required; equivalent rejection
is.  This module covers the ``unsupported encodings`` class with three words
the canonical decoder reports as unsupported: TEQ, COP1 and COP2.

The canonical path reports a typed CFG diagnostic, marks the block
``unsupported`` and the oracle refuses to execute it.  The frozen legacy IR
raises ``AnalysisError`` with its documented code before lowering can run.
The native harness, when ``RPTP_RUN_BINARY`` names a built executable, reports
its stable ``EXEC_*`` code with exit status 2.  A skipped harness leg is not a
pass.

The fixture words are RPTP test definitions built from the existing helpers.
This module records evidence only: it does not close E4, declare the canonical
path (ADR-0005 stays Proposed), change any Gate or claim hardware behaviour.
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
from tests.test_runtime_execution import BASE, build_program
from tools.rptp import oracle
from tools.rptp.cfg import discover_program
from tools.rptp.elf import parse_elf_bytes
from tools.rptp.isa import decode_instruction
from tools.rptp.oracle import ExecutionError

legacy_ir = load_module("rptp_ir_e4_unsupported", "tools/rptp_ir.py")

BINARY = os.environ.get("RPTP_RUN_BINARY", "")
CANONICAL_DIAGNOSTIC = "block.unsupported_instruction"
RUNTIME_CODE = "EXEC_UNSUPPORTED_INSTRUCTION"


@dataclass(frozen=True)
class UnsupportedCase:
    label: str
    word: int
    mnemonic: str
    canonical_problem: str
    canonical_message: str
    legacy_message: str
    runtime_message: str


CASES = (
    UnsupportedCase(
        label="teq",
        word=0x00000034,
        mnemonic="teq",
        canonical_problem="teq",
        canonical_message="is not supported: no lowering",
        legacy_message="Unsupported SPECIAL instruction 0x00000034 at 0x00100000",
        runtime_message="unsupported instruction 0x00000034 at 0x00100000",
    ),
    UnsupportedCase(
        label="cop1",
        word=0x46000000,
        mnemonic="cop1",
        canonical_problem="R5900 COP1 floating point is not implemented yet.",
        canonical_message="R5900 COP1 floating point is not implemented yet.",
        legacy_message="Unsupported opcode 0x11 (word 0x46000000) at 0x00100000",
        runtime_message="unsupported instruction 0x46000000 at 0x00100000",
    ),
    UnsupportedCase(
        label="cop2",
        word=0x4A000000,
        mnemonic="cop2",
        canonical_problem="VU0 macro-mode COP2 is not implemented yet.",
        canonical_message="VU0 macro-mode COP2 is not implemented yet.",
        legacy_message="Unsupported opcode 0x12 (word 0x4A000000) at 0x00100000",
        runtime_message="unsupported instruction 0x4a000000 at 0x00100000",
    ),
)


class CanonicalAndLegacyUnsupportedTests(unittest.TestCase):
    def assert_canonical_rejects(self, case: UnsupportedCase) -> None:
        instruction = decode_instruction(case.word, BASE)
        self.assertFalse(instruction.supported)
        self.assertEqual(case.mnemonic, instruction.mnemonic)

        image = build_program([case.word])
        program = discover_program(parse_elf_bytes(image))
        block = program.blocks[BASE]
        self.assertEqual("unsupported", block.kind)
        self.assertEqual(case.canonical_problem, block.problem)
        self.assertFalse(block.supported)

        diagnostics = [d for d in program.diagnostics
                       if d.code == CANONICAL_DIAGNOSTIC]
        self.assertEqual(1, len(diagnostics))
        self.assertEqual("warning", diagnostics[0].severity)
        self.assertEqual(BASE, diagnostics[0].address)
        self.assertIn(case.canonical_message, diagnostics[0].message)

        with self.assertRaisesRegex(ExecutionError, "unsupported block"):
            oracle.run_oracle(program)

    def assert_legacy_rejects(self, case: UnsupportedCase) -> None:
        image = build_program([case.word])
        with self.assertRaises(legacy_ir.AnalysisError) as caught:
            legacy_ir.analyze_elf(image)
        self.assertEqual(legacy_ir.IR_UNSUPPORTED_INSTRUCTION, caught.exception.code)
        self.assertEqual(BASE, caught.exception.pc)
        self.assertIn(case.legacy_message, str(caught.exception))

    def test_teq_is_rejected_by_canonical_and_legacy_paths(self) -> None:
        case = CASES[0]
        self.assert_canonical_rejects(case)
        self.assert_legacy_rejects(case)

    def test_cop1_is_rejected_by_canonical_and_legacy_paths(self) -> None:
        case = CASES[1]
        self.assert_canonical_rejects(case)
        self.assert_legacy_rejects(case)

    def test_cop2_is_rejected_by_canonical_and_legacy_paths(self) -> None:
        case = CASES[2]
        self.assert_canonical_rejects(case)
        self.assert_legacy_rejects(case)


@unittest.skipUnless(BINARY and Path(BINARY).is_file(),
                     "RPTP_RUN_BINARY is not a built executable")
class NativeUnsupportedFailClosedTests(unittest.TestCase):
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

    def test_unsupported_encodings_report_stable_codes(self) -> None:
        for case in CASES:
            with self.subTest(case=case.label):
                image = build_program([case.word])
                first = self.run_cli(image, "--json")
                self.assertEqual(2, first.returncode, first.stderr)
                self.assertEqual("", first.stderr.strip())

                document = json.loads(first.stdout)
                self.assertEqual("error", document["status"])
                self.assertEqual(RUNTIME_CODE, document["error"]["code"])
                self.assertIn(case.runtime_message, document["error"]["message"])
                self.assertNotIn("steps", document)

                second = self.run_cli(image, "--json")
                self.assertEqual(first.stdout, second.stdout)
                self.assertEqual(2, second.returncode)


if __name__ == "__main__":
    unittest.main()
