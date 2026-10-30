# SPDX-License-Identifier: GPL-3.0-or-later
"""E4 evidence: unaligned word access fails closed across every surviving path.

ADR-0005 gate E4 lists "unaligned LW/SW/LD/SD" as a rejection class that every
in-scope path must fail closed on.  The doubleword half was already checked by
the legacy Gate 0 oracle, the legacy lowering helpers, the canonical oracle and
code generation, and the native harness.  This module covers the word half:

* the canonical oracle raises ``ExecutionError`` naming the unaligned access;
* the frozen Gate 0 oracle raises ``ValueError`` before the access;
* the frozen lowering helpers throw ``unaligned word load``/``unaligned word
  store`` before touching guest memory; and
* the native harness, when ``RPTP_RUN_BINARY`` names a built executable,
  reports ``EXEC_MEMORY_FAULT`` with exit status 2.

Identical messages are not required; equivalent rejection is.  A skipped
compiler or harness leg is not a pass.  Each rejection is paired with an
aligned positive control so the check cannot simply reject every word access.

The fixture words are RPTP test definitions built from the existing encoders.
This module records evidence only: it does not close E4, declare the canonical
path (ADR-0005 stays Proposed), change any Gate or claim hardware behaviour.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from tests.test_runtime_execution import BASE, build_program, encode_i, encode_r
from tools.rptp import oracle
from tools.rptp.cfg import discover_program
from tools.rptp.elf import parse_elf_bytes
from tools.rptp.oracle import ExecutionError

ROOT = Path(__file__).resolve().parents[1]
BINARY = os.environ.get("RPTP_RUN_BINARY", "")
DATA = 0x2000
NOP = encode_r(0, 0, 0, 0, 0)
JR_RA = encode_r(31, 0, 0, 0, 0x08)


def load_module(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module {relative_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


spike = load_module("rptp_gate0_spike_alignment", "tools/rptp_gate0_spike.py")
legacy_ir = load_module("rptp_ir_alignment", "tools/rptp_ir.py")
legacy_lower = load_module("rptp_lower_alignment", "tools/rptp_lower.py")


@dataclass(frozen=True)
class AccessCase:
    label: str
    load: bool
    canonical_message: str
    legacy_message: str
    lowering_message: str
    runtime_message: str


CASES = (
    AccessCase(
        label="load",
        load=True,
        canonical_message="Unaligned LW",
        legacy_message="Oracle unaligned word load",
        lowering_message="unaligned word load",
        runtime_message="unaligned word load",
    ),
    AccessCase(
        label="store",
        load=False,
        canonical_message="Unaligned SW",
        legacy_message="Oracle unaligned word store",
        lowering_message="unaligned word store",
        runtime_message="unaligned word store",
    ),
)


def compiler_available() -> str | None:
    candidate = "cl" if os.name == "nt" and shutil.which("cl") else (os.environ.get("CXX") or "c++")
    return candidate if shutil.which(candidate) is not None else None


class CanonicalOracleAlignmentTests(unittest.TestCase):
    def test_unaligned_word_accesses_are_rejected(self) -> None:
        for case in CASES:
            for offset in (1, 2, 3):
                with self.subTest(case=case.label, offset=offset):
                    words = [encode_i(0x09, 0, 23, DATA)]
                    if case.load:
                        words.append(encode_i(0x23, 23, 8, offset))
                    else:
                        words.append(encode_i(0x09, 0, 8, 5))
                        words.append(encode_i(0x2B, 23, 8, offset))
                    words.extend((JR_RA, NOP))
                    program = discover_program(parse_elf_bytes(build_program(words)))
                    with self.assertRaisesRegex(ExecutionError, case.canonical_message):
                        oracle.run_oracle(program)


class LegacyOracleAlignmentTests(unittest.TestCase):
    def legacy_rows(self, case: AccessCase, offset: int) -> list[tuple[int, str, int]]:
        rows = [(0, "set_base", spike.encode_i(0x09, spike.ZERO, spike.T0, DATA))]
        if case.load:
            rows.append((4, "word_access", spike.encode_i(0x23, spike.T0, spike.T1, offset)))
        else:
            rows.append((4, "set_value", spike.encode_i(0x09, spike.ZERO, spike.T2, 5)))
            rows.append((8, "word_access", spike.encode_i(0x2B, spike.T0, spike.T2, offset)))
        index = 4 * len(rows)
        rows.extend((
            (index, "return", spike.encode_r(spike.RA, 0, 0, 0, 0x08)),
            (index + 4, "nop", spike.encode_r(0, 0, 0, 0, 0)),
        ))
        return rows

    def test_unaligned_word_accesses_are_rejected_before_the_access(self) -> None:
        for case in CASES:
            for offset in (1, 2, 3):
                with self.subTest(case=case.label, offset=offset):
                    image = spike.build_elf_from_rows(self.legacy_rows(case, offset))
                    entry, words, _ = spike.parse_elf(image)
                    expected = f"{case.legacy_message} at 0x{DATA + offset:08X}"
                    with self.assertRaisesRegex(ValueError, expected):
                        spike.execute_oracle(entry, words)

    def test_aligned_word_access_still_succeeds(self) -> None:
        image = spike.build_elf_from_rows([
            (0, "set_base", spike.encode_i(0x09, spike.ZERO, spike.T0, DATA)),
            (4, "set_value", spike.encode_i(0x09, spike.ZERO, spike.T2, 5)),
            (8, "aligned_store", spike.encode_i(0x2B, spike.T0, spike.T2, 0)),
            (12, "aligned_load", spike.encode_i(0x23, spike.T0, spike.T1, 0)),
            (16, "return", spike.encode_r(spike.RA, 0, 0, 0, 0x08)),
            (20, "nop", spike.encode_r(0, 0, 0, 0, 0)),
        ])
        entry, words, _ = spike.parse_elf(image)
        state = spike.execute_oracle(entry, words)
        self.assertEqual(5, state["registers"][spike.T1])
        self.assertEqual({str(DATA): 5}, state["memory"])


class LegacyLoweringAlignmentTests(unittest.TestCase):
    def test_generated_word_helpers_reject_unaligned_addresses(self) -> None:
        candidate = compiler_available()
        if candidate is None:
            self.skipTest("No C++ compiler available for legacy lowering alignment test")

        for case in CASES:
            with self.subTest(case=case.label):
                words = {BASE: spike.encode_i(0x09, spike.ZERO, spike.T0, DATA)}
                if case.load:
                    words[BASE + 4] = spike.encode_i(0x23, spike.T0, spike.T1, 1)
                else:
                    words[BASE + 4] = spike.encode_i(0x09, spike.ZERO, spike.T2, 5)
                    words[BASE + 8] = spike.encode_i(0x2B, spike.T0, spike.T2, 1)
                result = legacy_ir.analyze_words(BASE, words)
                source_text = legacy_lower.lower_to_cpp(result)

                with tempfile.TemporaryDirectory() as temp:
                    out_dir = Path(temp)
                    source = out_dir / "generated.cpp"
                    source.write_text(source_text, encoding="utf-8", newline="\n")
                    exe = out_dir / ("rptp-alignment.exe" if os.name == "nt" else "rptp-alignment")
                    command = spike.compile_generated(source, exe, "auto")
                    proc = subprocess.run(
                        [str(exe)], cwd=out_dir, text=True, capture_output=True, check=False,
                    )

                self.assertEqual(2, proc.returncode, msg=f"{command}\n{proc.stdout}\n{proc.stderr}")
                self.assertEqual("", proc.stdout)
                self.assertEqual(f"LOWER_RUNTIME_ERROR: {case.lowering_message}\n", proc.stderr)


@unittest.skipUnless(BINARY and Path(BINARY).is_file(),
                     "RPTP_RUN_BINARY is not a built executable")
class NativeAlignmentTests(unittest.TestCase):
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

    def test_unaligned_word_accesses_report_stable_codes(self) -> None:
        for case in CASES:
            with self.subTest(case=case.label):
                words = [encode_i(0x09, 0, 23, DATA)]
                if case.load:
                    words.append(encode_i(0x23, 23, 8, 1))
                else:
                    words.append(encode_i(0x09, 0, 8, 5))
                    words.append(encode_i(0x2B, 23, 8, 1))
                words.extend((JR_RA, NOP))
                image = build_program(words)

                first = self.run_cli(image, "--json")
                self.assertEqual(2, first.returncode, first.stderr)
                self.assertEqual("", first.stderr.strip())

                document = json.loads(first.stdout)
                self.assertEqual("error", document["status"])
                self.assertEqual("EXEC_MEMORY_FAULT", document["error"]["code"])
                self.assertIn(case.runtime_message, document["error"]["message"])
                self.assertNotIn("steps", document)

                second = self.run_cli(image, "--json")
                self.assertEqual(first.stdout, second.stdout)
                self.assertEqual(2, second.returncode)


if __name__ == "__main__":
    unittest.main()
