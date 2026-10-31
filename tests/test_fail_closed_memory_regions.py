# SPDX-License-Identifier: GPL-3.0-or-later
"""E4 evidence: memory-region and link-register failures are explicit everywhere.

ADR-0005 gate E4 asks whether every in-scope path fails closed on the same
failure classes.  This module covers the two classes left after the reserved
``shamt``, delay-slot, unsupported-encoding and unaligned-access increments:

* an access outside the modelled memory of the executing path;
* a REGIMM link branch that uses GPR 31 as ``rs``, which the permitted manual
  leaves undefined (RPTP-REF-015).

The paths use different memory models, and that is a recorded design choice,
not a defect to "fix" here.  The canonical oracle and the generated C++ model a
flat, zero-filled 32 MiB main RAM and reject any word access whose last byte
reaches 0x02000000.  The native harness in ``runtime/`` maps only the ELF
``PT_LOAD`` segments and rejects any access that leaves a single mapped region,
which makes an access straddling two regions fail as well.  Each path must
therefore reject its own out-of-model access explicitly; equal rejection is
the requirement, identical bounds are not.

The canonical/legacy assertions run everywhere.  The generated-C++ leg runs
where MSVC is discoverable, and the harness leg runs when ``RPTP_RUN_BINARY``
names a built executable; a skip is reported as a skip and never as a pass.

The fixtures are synthetic RPTP test definitions assembled from the existing
helpers.  This module records evidence only: it does not close E4, declare the
canonical path (ADR-0005 stays Proposed), change any Gate or claim hardware
behaviour.
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
from tests.test_runtime_execution import BASE, DATA, build_program
from tools.rptp import codegen, ir, native, oracle
from tools.rptp.cfg import discover_program
from tools.rptp.elf import parse_elf_bytes
from tools.rptp.fixtures import RA, T0, T1, T2, ZERO, Assembler, build_elf
from tools.rptp.isa import decode_instruction
from tools.rptp.oracle import ExecutionError

legacy_ir = load_module("rptp_ir_e4_memory_regions", "tools/rptp_ir.py")

BINARY = os.environ.get("RPTP_RUN_BINARY", "")
RETURN_SENTINEL = 0x7FFF0000
LAST_RAM_WORD = 0x01FFFFFC
RAM_LIMIT = 0x02000000
NOP = 0
CANONICAL_RAM_MESSAGE = (
    "guest memory access 0x02000000+4 is outside the modelled 32 MiB main RAM")
GENERATED_RAM_MESSAGE = (
    "native model error: guest memory access outside modelled RAM")
CANONICAL_DIAGNOSTIC = "block.unsupported_control"
LINK_NOTE = "GPR 31 must not be used as rs; the manual defines the result as undefined."


@dataclass(frozen=True)
class LinkCase:
    label: str
    rt: int
    word: int
    mnemonic: str


LINK_CASES = (
    LinkCase("bltzal", 0x10, 0x07F00000, "bltzal"),
    LinkCase("bgezal", 0x11, 0x07F10000, "bgezal"),
    LinkCase("bltzall", 0x12, 0x07F20000, "bltzall"),
    LinkCase("bgezall", 0x13, 0x07F30000, "bgezall"),
)


def canonical_program(words: list[int]):
    return discover_program(parse_elf_bytes(build_elf(words)))


def boundary_words() -> list[int]:
    """Store and reload zero at the last word of the modelled 32 MiB RAM."""
    assembler = Assembler()
    assembler.lui(T0, LAST_RAM_WORD >> 16)
    assembler.ori(T0, T0, LAST_RAM_WORD & 0xFFFF)
    assembler.addiu(T1, ZERO, 0)
    assembler.sw(T1, 0, T0)
    assembler.lw(T2, 0, T0)
    assembler.jr(RA)
    assembler.nop()
    return assembler.resolve()


def out_of_ram_words(store: bool) -> list[int]:
    assembler = Assembler()
    assembler.lui(T0, RAM_LIMIT >> 16)
    if store:
        assembler.sw(T1, 0, T0)
    else:
        assembler.lw(T1, 0, T0)
    assembler.jr(RA)
    assembler.nop()
    return assembler.resolve()


class CanonicalOracleMemoryModelTests(unittest.TestCase):
    def test_last_ram_word_is_still_accessible(self) -> None:
        state = oracle.run_oracle(canonical_program(boundary_words()))

        self.assertEqual(0, state["registers"][T2][0])
        self.assertEqual(RETURN_SENTINEL, state["pc"])
        self.assertEqual("pc_outside_code", state["reason"])
        self.assertTrue(state["halted"])
        self.assertEqual(
            [[LAST_RAM_WORD + offset, 0] for offset in range(4)],
            state["memory"],
        )

    def test_word_access_ending_at_the_ram_limit_is_rejected(self) -> None:
        for store in (False, True):
            with self.subTest(store=store):
                with self.assertRaises(ExecutionError) as caught:
                    oracle.run_oracle(canonical_program(out_of_ram_words(store)))
                self.assertEqual(CANONICAL_RAM_MESSAGE, str(caught.exception))


@unittest.skipUnless(
    BINARY and Path(BINARY).is_file(), "RPTP_RUN_BINARY is not a built executable")
class NativeMemoryRegionTests(unittest.TestCase):
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

    def assert_memory_fault(self, image: bytes, message: str) -> None:
        first = self.run_cli(image, "--json")
        self.assertEqual(2, first.returncode, first.stderr)
        self.assertEqual("", first.stderr.strip())

        document = json.loads(first.stdout)
        self.assertEqual("error", document["status"])
        self.assertEqual("EXEC_MEMORY_FAULT", document["error"]["code"])
        self.assertIn(message, document["error"]["message"])
        self.assertNotIn("steps", document)

        second = self.run_cli(image, "--json")
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(2, second.returncode)

    def test_unmapped_word_load_and_store_fault(self) -> None:
        for store in (False, True):
            operator = "store" if store else "load"
            with self.subTest(store=store):
                assembler = Assembler(base=BASE)
                assembler.addiu(T0, ZERO, 0x3000)
                if store:
                    assembler.sw(T1, 0, T0)
                else:
                    assembler.lw(T1, 0, T0)
                assembler.jr(RA)
                assembler.nop()
                image = build_program(assembler.resolve())
                self.assert_memory_fault(
                    image, f"{operator} outside mapped memory at 0x00003000")

    def test_access_straddling_two_regions_faults(self) -> None:
        data = b"\x44\x33\x22\x11\x55\x66"

        control = Assembler(base=BASE)
        control.addiu(T0, ZERO, DATA)
        control.lw(T1, 0, T0)
        control.jr(RA)
        control.nop()
        result = self.run_cli(
            build_program(control.resolve(), data=data, data_memsz=len(data)), "--json")
        self.assertEqual(0, result.returncode, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual("ok", document["status"])
        self.assertEqual("unmapped-pc", document["halt_reason"])
        self.assertEqual(0x11223344, int(document["registers"][T1], 16))

        for store in (False, True):
            operator = "store" if store else "load"
            with self.subTest(store=store):
                assembler = Assembler(base=BASE)
                assembler.addiu(T0, ZERO, DATA)
                if store:
                    assembler.sw(T1, 4, T0)
                else:
                    assembler.lw(T1, 4, T0)
                assembler.jr(RA)
                assembler.nop()
                image = build_program(
                    assembler.resolve(), data=data, data_memsz=len(data))
                self.assert_memory_fault(
                    image, f"{operator} outside mapped memory at 0x00002004")


def _msvc_available(test: unittest.TestCase) -> None:
    try:
        native.find_msvc()
    except native.HarnessError as exc:
        test.skipTest(f"MSVC is not available: {exc}")


class GeneratedMemoryModelTests(unittest.TestCase):
    def build(self, words: list[int], workdir: Path) -> Path:
        program = canonical_program(words)
        lowered = ir.lower_program(program)
        self.assertEqual([], lowered.errors, "lowering produced errors")
        generated = codegen.generate(program, lowered)
        return native.build_native(generated, workdir)

    def test_last_ram_word_is_still_accessible(self) -> None:
        _msvc_available(self)
        with native.temporary_workdir() as workdir:
            exe = self.build(boundary_words(), workdir)
            state = native.run_native(
                exe, codegen.DEFAULT_MAX_STEPS, workdir / codegen.MEMORY_BLOB_NAME)

        self.assertEqual(RETURN_SENTINEL, state["pc"])
        self.assertEqual("pc_outside_code", state["reason"])
        self.assertTrue(state["halted"])
        self.assertEqual(0, state["registers"][T2][0])
        self.assertEqual(
            [[LAST_RAM_WORD + offset, 0] for offset in range(4)],
            state["memory"],
        )

    def test_word_access_ending_at_the_ram_limit_is_rejected(self) -> None:
        _msvc_available(self)
        for store in (False, True):
            with self.subTest(store=store):
                with native.temporary_workdir() as workdir:
                    exe = self.build(out_of_ram_words(store), workdir)
                    completed = subprocess.run(
                        [str(exe), str(codegen.DEFAULT_MAX_STEPS),
                         str(workdir / codegen.MEMORY_BLOB_NAME)],
                        cwd=str(workdir),
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        check=False,
                    )

                self.assertEqual(2, completed.returncode)
                self.assertEqual(GENERATED_RAM_MESSAGE, completed.stderr.strip())
                self.assertEqual("", completed.stdout.strip())


class LinkRegisterCanonicalTests(unittest.TestCase):
    def test_link_instruction_with_rs_31_is_rejected(self) -> None:
        for case in LINK_CASES:
            with self.subTest(case=case.label):
                instruction = decode_instruction(case.word, BASE)
                self.assertEqual(case.mnemonic, instruction.mnemonic)
                self.assertFalse(instruction.valid)
                self.assertFalse(instruction.supported)
                self.assertEqual(LINK_NOTE, instruction.note)

                program = canonical_program([case.word, NOP])
                block = program.blocks[BASE]
                self.assertEqual("unsupported", block.kind)
                self.assertEqual(LINK_NOTE, block.problem)
                self.assertFalse(block.supported)

                diagnostics = [d for d in program.diagnostics
                               if d.code == CANONICAL_DIAGNOSTIC]
                self.assertEqual(1, len(diagnostics))
                self.assertEqual("warning", diagnostics[0].severity)
                self.assertEqual(BASE, diagnostics[0].address)
                self.assertIn(f"{case.mnemonic} $ra, 0x00100004", diagnostics[0].message)
                self.assertIn(LINK_NOTE, diagnostics[0].message)

                with self.assertRaisesRegex(ExecutionError, "unsupported block"):
                    oracle.run_oracle(program)

                lowered = ir.lower_program(program)
                self.assertEqual(1, len(lowered.errors))
                self.assertIn(LINK_NOTE, lowered.errors[0])

                with self.assertRaises(codegen.CodegenError) as caught:
                    codegen.generate(program, lowered)
                self.assertIn("lowering failed", str(caught.exception))
                self.assertIn(LINK_NOTE, str(caught.exception))

    def test_legacy_ir_rejects_rs_31_before_lowering(self) -> None:
        for case in LINK_CASES:
            with self.subTest(case=case.label):
                image = build_elf([case.word, NOP])
                with self.assertRaises(legacy_ir.AnalysisError) as caught:
                    legacy_ir.analyze_elf(image)
                self.assertEqual(
                    legacy_ir.IR_UNSUPPORTED_INSTRUCTION, caught.exception.code)
                self.assertEqual(BASE, caught.exception.pc)
                expected = f"Unsupported opcode 0x01 (word 0x{case.word:08X}) at 0x00100000"
                self.assertIn(expected, str(caught.exception))


@unittest.skipUnless(
    BINARY and Path(BINARY).is_file(), "RPTP_RUN_BINARY is not a built executable")
class LinkRegisterRuntimeTests(unittest.TestCase):
    def run_cli(self, image: bytes) -> subprocess.CompletedProcess[str]:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "input.elf"
        path.write_bytes(image)
        return subprocess.run(
            [BINARY, "--json", str(path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )

    def test_link_instruction_with_rs_31_is_unsupported(self) -> None:
        for case in LINK_CASES:
            with self.subTest(case=case.label):
                image = build_program([case.word, NOP])
                first = self.run_cli(image)
                self.assertEqual(2, first.returncode, first.stderr)
                self.assertEqual("", first.stderr.strip())

                document = json.loads(first.stdout)
                self.assertEqual("error", document["status"])
                self.assertEqual(
                    "EXEC_UNSUPPORTED_INSTRUCTION", document["error"]["code"])
                self.assertIn(
                    f"unsupported instruction 0x{case.word:08x} at 0x00100000",
                    document["error"]["message"],
                )
                self.assertNotIn("steps", document)

                second = self.run_cli(image)
                self.assertEqual(first.stdout, second.stdout)
                self.assertEqual(2, second.returncode)


if __name__ == "__main__":
    unittest.main()
