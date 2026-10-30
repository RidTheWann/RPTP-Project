# SPDX-License-Identifier: GPL-3.0-or-later
"""E3 evidence: four executions of one shared legacy-subset program.

ADR-0005 gate E3 asks whether the frozen legacy pipeline produces the same
observable result as the canonical path and the native harness.  This module
executes one synthetic program that contains every operation supported by
``tools/rptp_ir.py``/``tools/rptp_lower.py``:

1. the legacy generated C++20 state machine, compiled with MSVC ``/W4 /WX``;
2. the canonical Python oracle from ``tools/rptp`` (the reference result);
3. the canonical generated C++20 program (via
   :func:`tools.rptp.native.run_differential`); and
4. the native execution harness ``rptp-run`` over the same ELF image.

The memory models differ, so every result is normalized before comparison:

* the legacy generated program stores 32-bit words in a word-keyed map that
  starts empty and never contains the statically loaded data bytes;
* the canonical oracle and generated program track byte writes only
  (``GuestMemory.writes``);
* the native harness reports each 32-bit store as an ``address``/``value``
  word pair.

Each legacy/runtime word is expanded to four little-endian bytes and compared
against the canonical byte-write map.  No write is dropped, no region is
excluded and no tolerance is applied.  ``$ra`` starts at the ``0x7FFF0000``
return sentinel in the canonical generator and the legacy lowerer and at zero
in the native harness; the shared program's first instruction writes
``$ra = $zero`` on every path before any control transfer, so the compared
final state is defined by the program.

The halt reason is path vocabulary, not a behavioral difference: the legacy
state machine and the canonical models stop at an unmapped PC with
``pc_outside_code``, while the harness reports ``unmapped-pc``.  The mapping is
asserted explicitly in :data:`HALT_REASON_MAP`.

A missing compiler or runtime binary skips its leg with a precise reason; a
skipped leg is never reported as a pass.  This module does not declare the
canonical path (ADR-0005 stays Proposed), close R-031 or change any Gate.
"""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest

from tests.test_path_contract import (
    LEGACY_OPERATIONS,
    load_module,
    shared_legacy_program,
)
from tests.test_runtime_loader import build_elf
from tools.rptp import cfg, codegen, elf, fixtures, ir, isa, native, oracle

ROOT = Path(__file__).resolve().parents[1]
BASE = 0x00100000
DATA_BASE = 0x00002000
DATA_OFFSET = 0x100
CODE_OFFSET = 0x200
DATA_SIZE = 64
MASK64 = 0xFFFFFFFFFFFFFFFF
MAX_STEPS = 1_000
BINARY = os.environ.get("RPTP_RUN_BINARY", "")
LEGACY_OUTPUT_KEYS = frozenset({"halted", "pc", "registers", "memory", "trace"})

# The same stop event uses different vocabulary in each path.
HALT_REASON_MAP = {
    "oracle": "pc_outside_code",
    "legacy": "pc_outside_code",
    "generated": "pc_outside_code",
    "runtime": "unmapped-pc",
}

legacy_ir = load_module("rptp_ir_e3", "tools/rptp_ir.py")
legacy_lower = load_module("rptp_lower_e3", "tools/rptp_lower.py")


def build_e3_image(words: list[int]) -> bytes:
    code = b"".join(struct.pack("<I", word & 0xFFFFFFFF) for word in words)
    data = bytes(DATA_SIZE)
    payload = data + bytes(CODE_OFFSET - DATA_OFFSET - len(data)) + code
    return build_elf(
        BASE,
        [
            {"offset": DATA_OFFSET, "vaddr": DATA_BASE,
             "filesz": len(data), "memsz": len(data), "flags": 6},
            {"offset": CODE_OFFSET, "vaddr": BASE,
             "filesz": len(code), "memsz": len(code), "flags": 5},
        ],
        payload=payload,
        payload_offset=DATA_OFFSET,
    )


def legacy_generated_source(image: bytes) -> str:
    analysis = legacy_ir.analyze_elf(image)
    return legacy_lower.lower_to_cpp(analysis, max_steps=MAX_STEPS)


def compile_and_run_legacy(source: str) -> dict:
    """Compile the legacy generated C++ with warnings-as-errors and run it once."""
    compiler = native.find_msvc()
    with native.temporary_workdir() as workdir:
        source_path = workdir / "legacy_generated.cpp"
        source_path.write_text(source, encoding="utf-8", newline="")
        exe = workdir / "legacy_generated.exe"
        batch = native._write_batch(workdir, "build_legacy.bat", [
            f'call "%{native._VCVARS_ENV}%" >nul',
            "if errorlevel 1 exit /b 1",
            f"cl {native.CL_FLAGS} /Fe:{exe.name} {source_path.name}",
        ])
        completed = native._run_batch(
            batch, workdir, native.COMPILE_TIMEOUT_SECONDS, compiler)
        compiler_output = native._combined_output(completed)
        if completed.returncode != 0 or not exe.is_file():
            raise native.HarnessError(
                f"legacy MSVC compilation failed (exit {completed.returncode}).\n"
                f"Toolchain: {compiler.description}\n"
                f"Artifacts kept at: {workdir}\n"
                f"--- compiler output ---\n{compiler_output or '<empty>'}")
        try:
            executed = subprocess.run(
                [str(exe)],
                cwd=str(workdir),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=native.RUN_TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise native.HarnessError(
                f"Unable to run {exe}: {exc}\nArtifacts kept at: {workdir}") from exc
        if executed.returncode != 0:
            raise native.HarnessError(
                f"legacy generated program exited with status {executed.returncode}: {exe}\n"
                f"Artifacts kept at: {workdir}\n"
                f"--- stdout ---\n{(executed.stdout or '').strip() or '<empty>'}\n"
                f"--- stderr ---\n{(executed.stderr or '').strip() or '<empty>'}")
        try:
            payload = json.loads(executed.stdout)
        except json.JSONDecodeError as exc:
            raise native.HarnessError(
                f"legacy generated program did not emit valid JSON: {exc}\n"
                f"Artifacts kept at: {workdir}\n"
                f"--- stdout ---\n{(executed.stdout or '').strip() or '<empty>'}") from exc
        if not isinstance(payload, dict) or set(payload) != LEGACY_OUTPUT_KEYS:
            keys = sorted(payload) if isinstance(payload, dict) else type(payload).__name__
            raise native.HarnessError(
                f"legacy generated program JSON keys changed: {keys}\n"
                f"Artifacts kept at: {workdir}")
        return payload


def expand_word_writes(pairs) -> dict[int, int]:
    """Expand 32-bit word stores into a little-endian byte-write map."""
    memory: dict[int, int] = {}
    for address, value in pairs:
        address = int(address)
        value = int(value) & 0xFFFFFFFF
        for offset in range(4):
            memory[address + offset] = (value >> (8 * offset)) & 0xFF
    return memory


def normalize_legacy(payload: dict) -> dict:
    trace = [int(pc) for pc in payload["trace"]]
    return {
        "halted": bool(payload["halted"]),
        "pc": int(payload["pc"]),
        # The legacy JSON has no reason field; an unknown PC is its only halt path.
        "reason": "pc_outside_code" if payload["halted"] else "not_halted",
        "steps": len(trace),
        "registers": [int(value) & MASK64 for value in payload["registers"]],
        "trace": trace,
        "memory": expand_word_writes(payload["memory"]),
    }


def normalize_oracle(state: dict) -> dict:
    return {
        "halted": state["halted"],
        "pc": state["pc"],
        "reason": state["reason"],
        "steps": state["steps"],
        "registers": [pair[0] & MASK64 for pair in state["registers"]],
        "trace": list(state["trace"]),
        "memory": {address: value for address, value in state["memory"]},
    }


def normalize_runtime(payload: dict) -> dict:
    return {
        "halted": payload["status"] == "ok",
        "pc": int(payload["final_pc"], 16),
        "reason": payload["halt_reason"],
        "steps": payload["steps"],
        "registers": [int(value, 16) & MASK64 for value in payload["registers"]],
        "trace": [int(value, 16) for value in payload["trace"]],
        "memory": expand_word_writes(
            (int(entry["address"], 16), int(entry["value"], 16))
            for entry in payload["memory_writes"]),
    }


def data_snapshot(memory: dict[int, int]) -> bytes:
    data = bytearray(DATA_SIZE)
    for address, value in memory.items():
        if DATA_BASE <= address < DATA_BASE + DATA_SIZE:
            data[address - DATA_BASE] = value
    return bytes(data)


class NativeLegacyEquivalenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.words, cls.labels = shared_legacy_program()
        cls.image = build_e3_image(cls.words)
        cls.parsed = elf.parse_elf_bytes(cls.image, path="native_legacy_equivalence.elf")
        cls.program = cfg.discover_program(cls.parsed)
        cls.oracle_result = normalize_oracle(
            oracle.run_oracle(cls.program, max_steps=MAX_STEPS))
        cls.legacy_result: dict | None = None
        cls.generated_result: dict | None = None
        cls.runtime_result: dict | None = None

    def _msvc_or_skip(self) -> None:
        try:
            native.find_msvc()
        except native.HarnessError as exc:
            self.skipTest(f"generated legs skipped: MSVC unavailable: {exc}")

    def _legacy_or_skip(self) -> dict:
        self._msvc_or_skip()
        if type(self).legacy_result is None:
            try:
                source = legacy_generated_source(self.image)
                type(self).legacy_result = normalize_legacy(compile_and_run_legacy(source))
            except native.HarnessError as exc:
                self.fail(f"legacy generated leg failed: {exc}")
        return type(self).legacy_result

    def _generated_or_skip(self) -> dict:
        self._msvc_or_skip()
        if type(self).generated_result is None:
            try:
                type(self).generated_result = normalize_oracle(
                    native.run_differential(self.parsed, max_steps=MAX_STEPS))
            except native.HarnessError as exc:
                self.fail(f"canonical generated leg failed: {exc}")
        return type(self).generated_result

    def _runtime_or_skip(self) -> dict:
        if not (BINARY and Path(BINARY).is_file()):
            self.skipTest(
                "native harness leg skipped: RPTP_RUN_BINARY is not a built executable")
        if type(self).runtime_result is None:
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "native_legacy_equivalence.elf"
                path.write_bytes(self.image)
                completed = subprocess.run(
                    [BINARY, "--json", "--trace", "--max-steps", str(MAX_STEPS), str(path)],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=native.RUN_TIMEOUT_SECONDS,
                    check=False,
                )
            self.assertEqual(0, completed.returncode, completed.stderr)
            document = json.loads(completed.stdout)
            self.assertEqual("rptp.runtime.run.v1", document["schema"])
            self.assertEqual("ok", document["status"])
            type(self).runtime_result = normalize_runtime(document)
        return type(self).runtime_result

    def assert_equivalent(self, left_name: str, left: dict,
                          right_name: str, right: dict) -> None:
        self.assertEqual(HALT_REASON_MAP[left_name], left["reason"],
                         f"{left_name} halt reason")
        self.assertEqual(HALT_REASON_MAP[right_name], right["reason"],
                         f"{right_name} halt reason")
        self.assertEqual(left["halted"], right["halted"],
                         f"{left_name} vs {right_name}: halted")
        self.assertEqual(left["pc"], right["pc"],
                         f"{left_name} vs {right_name}: final pc")
        self.assertEqual(left["steps"], right["steps"],
                         f"{left_name} vs {right_name}: step accounting")
        self.assertEqual(left["trace"], right["trace"],
                         f"{left_name} vs {right_name}: executed-PC trace")
        self.assertEqual(left["registers"], right["registers"],
                         f"{left_name} vs {right_name}: registers")
        self.assertEqual(left["memory"], right["memory"],
                         f"{left_name} vs {right_name}: memory writes")
        self.assertEqual(data_snapshot(left["memory"]), data_snapshot(right["memory"]),
                         f"{left_name} vs {right_name}: final data bytes")

    def test_canonical_baseline_covers_every_legacy_operation(self) -> None:
        mnemonics = {
            isa.decode_instruction(word, pc=BASE + index * 4).mnemonic
            for index, word in enumerate(self.words)
        }
        self.assertEqual(LEGACY_OPERATIONS, mnemonics)
        self.assertEqual([], self.program.unsupported_blocks())

        state = self.oracle_result
        self.assertTrue(state["halted"])
        self.assertEqual("pc_outside_code", state["reason"])
        self.assertEqual(0, state["pc"])
        self.assertEqual(49, state["steps"])
        self.assertEqual(49, len(state["trace"]))
        registers = state["registers"]
        self.assertEqual(0xFEDCBA9812345678, registers[fixtures.A0])
        self.assertEqual(0xFEDCBA9812345678, registers[fixtures.A1])
        self.assertEqual(30, registers[fixtures.V0])
        self.assertEqual(31, registers[fixtures.V1])          # JR delay slot
        self.assertEqual(1, registers[fixtures.A2])           # taken BEQ skipped 99
        self.assertEqual(3, registers[fixtures.A3])           # BNE fall-through
        self.assertEqual(8, registers[fixtures.T1])           # J delay slot
        self.assertEqual(9, registers[fixtures.T2])           # JAL delay slot
        self.assertEqual(55, registers[fixtures.T3])          # overwritten after the call
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
        self.assertEqual(12, registers[fixtures.FP])
        self.assertEqual(0, registers[fixtures.RA])
        self.assertEqual(0, registers[0])

        data = data_snapshot(state["memory"])
        self.assertEqual(12, int.from_bytes(data[0:4], "little"))
        self.assertEqual(0xFEDCBA98, int.from_bytes(data[4:8], "little"))
        self.assertEqual(0x12345678, int.from_bytes(data[8:12], "little"))
        self.assertEqual(0xFEDCBA98, int.from_bytes(data[12:16], "little"))
        self.assertEqual(0xFEDCBA9812345678, int.from_bytes(data[16:24], "little"))

    def test_generated_sources_are_deterministic(self) -> None:
        first = legacy_generated_source(self.image)
        second = legacy_generated_source(self.image)
        self.assertEqual(first, second)
        self.assertIn("Generated by tools/rptp_lower.py", first)
        self.assertNotIn(str(ROOT), first)
        self.assertNotIn("\r", first)

        lowering = ir.lower_program(self.program)
        canonical_first = codegen.generate(self.program, lowering)
        canonical_second = codegen.generate(self.program, lowering)
        self.assertEqual(canonical_first.source, canonical_second.source)
        self.assertEqual(canonical_first.memory_blob, canonical_second.memory_blob)
        self.assertNotIn(str(ROOT), canonical_first.source)

    def test_legacy_generated_matches_canonical_oracle(self) -> None:
        legacy = self._legacy_or_skip()
        self.assert_equivalent("oracle", self.oracle_result, "legacy", legacy)

    def test_canonical_generated_matches_oracle(self) -> None:
        generated = self._generated_or_skip()
        self.assert_equivalent("oracle", self.oracle_result, "generated", generated)

    def test_native_harness_matches_oracle(self) -> None:
        runtime = self._runtime_or_skip()
        self.assert_equivalent("oracle", self.oracle_result, "runtime", runtime)

    def test_all_four_executions_agree(self) -> None:
        legacy = self._legacy_or_skip()
        generated = self._generated_or_skip()
        runtime = self._runtime_or_skip()
        for name, state in (("legacy", legacy), ("generated", generated),
                            ("runtime", runtime)):
            with self.subTest(path=name):
                self.assert_equivalent("oracle", self.oracle_result, name, state)
        self.assertEqual(49, legacy["steps"])
        self.assertEqual(legacy["steps"], runtime["steps"])
        self.assertEqual(legacy["trace"], runtime["trace"])
        self.assertEqual(legacy["memory"], runtime["memory"])
        self.assertEqual(data_snapshot(legacy["memory"]),
                         data_snapshot(generated["memory"]))

    def _assert_divergences_rejected(self, base_name: str, base_state: dict) -> None:
        def flip_register(state: dict) -> None:
            state["registers"][fixtures.T7] ^= 1

        def flip_memory_byte(state: dict) -> None:
            state["memory"][DATA_BASE] ^= 1

        mutations = {
            "register": flip_register,
            "memory byte": flip_memory_byte,
            "trace entry": lambda state: state["trace"].pop(),
            "step count": lambda state: state.__setitem__("steps", state["steps"] + 1),
            "final pc": lambda state: state.__setitem__("pc", state["pc"] + 4),
            "halted flag": lambda state: state.__setitem__("halted", False),
            "halt reason": lambda state: state.__setitem__("reason", "divergent-reason"),
        }
        for label, mutate in mutations.items():
            with self.subTest(baseline=base_name, field=label):
                mutated = copy.deepcopy(base_state)
                mutate(mutated)
                with self.assertRaises(AssertionError):
                    self.assert_equivalent("oracle", self.oracle_result,
                                           base_name, mutated)

    def test_comparison_rejects_oracle_baseline_divergences(self) -> None:
        self._assert_divergences_rejected("oracle", copy.deepcopy(self.oracle_result))

    def test_comparison_rejects_legacy_baseline_divergences(self) -> None:
        # Skips without MSVC instead of silently testing only the oracle baseline.
        legacy = copy.deepcopy(self._legacy_or_skip())
        self._assert_divergences_rejected("legacy", legacy)


if __name__ == "__main__":
    unittest.main(verbosity=2)
