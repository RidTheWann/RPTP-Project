# SPDX-License-Identifier: GPL-3.0-or-later
"""Cross-path equivalence: Python oracle versus generated C++ versus rptp-run.

One shared synthetic guest program is executed by three independent paths:

1. the Python oracle (direct interpreter over the CFG);
2. the generated C++20 state machine, compiled with MSVC; and
3. the native C++ execution harness through the ``rptp-run`` CLI.

The comparison covers final registers, final data bytes, stop PC, step count,
the executed-PC trace and the halt reason (with an explicit documented mapping).
The generated-native and runtime legs skip with a precise reason when their
toolchain or binary is unavailable; a missing leg is never reported as a pass.

The program deliberately avoids ``$ra`` control flow so that all three paths
start from the same observable state, uses only the instruction intersection of
the three models, and ends with a jump outside every loaded segment.  It covers
arithmetic, logic, shifts, LW/SW, a signed/unsigned 64-bit boundary loaded with
LD, taken/not-taken BEQ/BNE branches, and the six non-likely branch forms whose
delay slots always execute; BLTZAL/BGEZAL additionally exercise the
unconditional ``$ra = PC + 8`` link write, and the taken BGEZAL delay slot reads
``$ra`` so all three paths must write the link before the delay slot runs.
"""
from __future__ import annotations

import json
import os
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.test_runtime_loader import build_elf
from tools.rptp import cfg, elf, fixtures, native, oracle

BINARY = os.environ.get("RPTP_RUN_BINARY", "")
BASE = 0x00100000
DATA_BASE = 0x00002000
EXIT_PC = 0x00001000
MAX_STEPS = 100_000
MASK64 = 0xFFFFFFFFFFFFFFFF
DATA_OFFSET = 0x100
CODE_OFFSET = 0x200

# Expected halt reasons for the same event in each path.  The runtime harness
# calls a successful stop at an unmapped PC "unmapped-pc" and reports it in
# ``halt_reason``; the oracle and the generated state machine call the same
# stop "pc_outside_code" and report it in ``reason``.
HALT_REASON_MAP = {
    "oracle": "pc_outside_code",
    "generated": "pc_outside_code",
    "runtime": "unmapped-pc",
}


def initial_data() -> bytes:
    return struct.pack("<IIQ", 0xAABBCCDD, 0x11223344, 0x8000000000000000) + bytes(8)


def build_cross_path_image(words: list[int]) -> bytes:
    code = b"".join(struct.pack("<I", word & 0xFFFFFFFF) for word in words)
    data = initial_data()
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


def shared_program() -> tuple[list[int], dict[str, int]]:
    asm = fixtures.Assembler()
    asm.addu(fixtures.RA, fixtures.ZERO, fixtures.ZERO)      # normalize $ra across paths
    asm.addiu(fixtures.T0, fixtures.ZERO, DATA_BASE)          # data base

    asm.lw(fixtures.T1, 0, fixtures.T0)                       # 0xAABBCCDD, sign-extended
    asm.lw(fixtures.T2, 4, fixtures.T0)                       # 0x11223344
    asm.addu(fixtures.T3, fixtures.T1, fixtures.T2)           # 32-bit wrap and sign extension
    asm.sw(fixtures.T3, 0, fixtures.T0)                       # overwrite the first data word
    asm.lw(fixtures.T4, 0, fixtures.T0)                       # read the stored word back

    asm.addiu(fixtures.T5, fixtures.ZERO, 7)
    asm.addiu(fixtures.T6, fixtures.ZERO, 5)
    asm.addu(fixtures.T7, fixtures.T5, fixtures.T6)           # 12
    asm.emit(fixtures.encode_r(0x23, fixtures.S0, fixtures.T6, fixtures.T5))  # subu s0, t6, t5 -> -2
    asm.emit(fixtures.encode_i(0x19, fixtures.S1, fixtures.S0, 1))  # daddiu s1, s0, 1 -> -1
    asm.sll(fixtures.S2, fixtures.T7, 4)                      # 192
    asm.daddu(fixtures.S3, fixtures.S1, fixtures.T5)          # 6

    asm.lui(fixtures.S4, 0x1234)
    asm.ori(fixtures.S4, fixtures.S4, 0x5678)                 # 0x12345678
    asm.lui(fixtures.S5, 0xFEDC)
    asm.ori(fixtures.S5, fixtures.S5, 0xBA98)                 # 0xFFFFFFFFFEDCBA98
    asm.and_(fixtures.S6, fixtures.S4, fixtures.S5)
    asm.or_(fixtures.S7, fixtures.S4, fixtures.S5)
    asm.xor(fixtures.K0, fixtures.S4, fixtures.S5)
    asm.nor(fixtures.K1, fixtures.S4, fixtures.S5)
    asm.andi(fixtures.GP, fixtures.S5, 0x00FF)
    asm.xori(fixtures.SP, fixtures.S4, 0xFFFF)
    asm.sll(fixtures.FP, fixtures.S5, 1)                      # 32-bit shift, sign-extended

    asm.ld(fixtures.T8, 8, fixtures.T0)                       # 0x8000000000000000
    asm.slt(fixtures.T9, fixtures.T8, fixtures.ZERO)          # signed: 1
    asm.sltu(fixtures.V0, fixtures.ZERO, fixtures.T8)         # unsigned: 1
    asm.slti(fixtures.V1, fixtures.T8, -1)                    # signed: 1
    asm.sltiu(fixtures.A0, fixtures.T8, -1)                   # unsigned: 1
    asm.slt(fixtures.A1, fixtures.S0, fixtures.T7)            # -2 < 12: 1
    asm.sltu(fixtures.A2, fixtures.S0, fixtures.T7)           # huge < 12: 0

    asm.addiu(fixtures.A3, fixtures.ZERO, 3)
    asm.beq(fixtures.A3, fixtures.A3, "taken_branch")
    asm.addiu(fixtures.A3, fixtures.ZERO, 99)                 # delay slot changes the compared register
    asm.addiu(fixtures.T1, fixtures.ZERO, 123)                # skipped
    asm.label("taken_branch")
    asm.addiu(fixtures.T2, fixtures.A3, 0)                    # observes 99

    asm.bne(fixtures.T7, fixtures.T7, "not_taken_done")       # false: delay slot still executes
    asm.addiu(fixtures.T3, fixtures.ZERO, 44)                 # delay slot
    asm.addiu(fixtures.T4, fixtures.ZERO, 55)                 # fallthrough
    asm.label("not_taken_done")
    asm.addiu(fixtures.T3, fixtures.T3, 1)                    # 45

    asm.j("jump_target")
    asm.addiu(fixtures.T5, fixtures.ZERO, 77)                 # delay slot
    asm.addiu(fixtures.T6, fixtures.ZERO, 888)                # skipped
    asm.label("jump_target")
    asm.addiu(fixtures.T5, fixtures.T5, 1)                    # 78

    asm.sw(fixtures.T4, 16, fixtures.T0)                      # 55 at 0x2010
    asm.lw(fixtures.T6, 16, fixtures.T0)                      # read it back

    asm.addiu(fixtures.S0, fixtures.ZERO, 0)
    asm.blez(fixtures.S0, "plain_blez")                       # taken
    asm.addiu(fixtures.S1, fixtures.ZERO, 111)                # delay slot
    asm.addiu(fixtures.S2, fixtures.ZERO, 222)                # skipped
    asm.label("plain_blez")

    asm.addiu(fixtures.S3, fixtures.ZERO, 0)
    asm.bgtz(fixtures.S3, "plain_bgtz_end")                   # not taken
    asm.addiu(fixtures.S4, fixtures.ZERO, 333)                # delay slot still executes
    asm.addiu(fixtures.S5, fixtures.ZERO, 444)                # fall-through
    asm.label("plain_bgtz_end")

    asm.addiu(fixtures.S6, fixtures.ZERO, -1)
    asm.addiu(fixtures.K0, fixtures.ZERO, 0)
    asm.bltz(fixtures.S6, "plain_bltz")                       # taken
    asm.addiu(fixtures.S7, fixtures.ZERO, 555)                # delay slot
    asm.addiu(fixtures.K0, fixtures.ZERO, 666)                # skipped
    asm.label("plain_bltz")

    asm.addiu(fixtures.K1, fixtures.ZERO, 0)
    asm.addiu(fixtures.SP, fixtures.ZERO, 0)
    asm.bgez(fixtures.K1, "plain_bgez")                       # taken
    asm.addiu(fixtures.GP, fixtures.ZERO, 777)                # delay slot
    asm.addiu(fixtures.SP, fixtures.ZERO, 888)                # skipped
    asm.label("plain_bgez")

    asm.addiu(fixtures.FP, fixtures.ZERO, 0)
    asm.bltzal(fixtures.FP, "plain_bltzal_end")               # not taken, link written
    asm.addiu(fixtures.S0, fixtures.ZERO, 999)                # delay slot still executes
    asm.addiu(fixtures.S1, fixtures.ZERO, 1111)               # fall-through
    asm.label("plain_bltzal_end")

    asm.addiu(fixtures.S2, fixtures.ZERO, 0)
    asm.label("plain_bgezal_branch")
    asm.bgezal(fixtures.S2, "plain_bgezal")                   # taken, link written
    asm.addu(fixtures.S3, fixtures.RA, fixtures.ZERO)         # delay slot reads the new $ra
    asm.addiu(fixtures.S4, fixtures.ZERO, 3333)               # skipped
    asm.label("plain_bgezal")

    asm.emit(fixtures.encode_j(0x02, EXIT_PC))                # halt outside every segment
    asm.nop()                                                 # delay slot
    return asm.resolve(), dict(asm.labels)


def shared_words() -> list[int]:
    return shared_program()[0]


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


def normalize_generated(payload: dict) -> dict:
    return {
        "halted": payload["halted"],
        "pc": payload["pc"],
        "reason": payload["reason"],
        "steps": payload["steps"],
        "registers": [pair[0] & MASK64 for pair in payload["registers"]],
        "trace": list(payload["trace"]),
        "memory": {address: value for address, value in payload["memory"]},
    }


def normalize_runtime(payload: dict, trace: bool) -> dict:
    memory: dict[int, int] = {}
    for entry in payload["memory_writes"]:
        address = int(entry["address"], 16)
        value = int(entry["value"], 16)
        for offset in range(4):
            memory[address + offset] = (value >> (8 * offset)) & 0xFF
    return {
        "halted": payload["status"] == "ok",
        "pc": int(payload["final_pc"], 16),
        "reason": payload["halt_reason"],
        "steps": payload["steps"],
        "registers": [int(value, 16) & MASK64 for value in payload["registers"]],
        "trace": [int(value, 16) for value in payload["trace"]] if trace else [],
        "memory": memory,
    }


def final_data(normalized: dict) -> bytes:
    data = bytearray(initial_data())
    for address, value in normalized["memory"].items():
        if DATA_BASE <= address < DATA_BASE + len(data):
            data[address - DATA_BASE] = value
    return bytes(data)


class CrossPathEquivalenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.words, cls.labels = shared_program()
        cls.image = build_cross_path_image(cls.words)
        cls.parsed = elf.parse_elf_bytes(cls.image, path="cross_path_shared.elf")
        cls.program = cfg.discover_program(cls.parsed)
        cls.oracle_result = normalize_oracle(
            oracle.run_oracle(cls.program, max_steps=MAX_STEPS))
        cls.native_result: dict | None = None
        cls.runtime_result: dict | None = None

    def test_oracle_baseline_covers_boundary_and_delay_slots(self) -> None:
        state = self.oracle_result
        self.assertEqual([], self.program.unsupported_blocks())
        self.assertTrue(state["halted"])
        self.assertEqual("pc_outside_code", state["reason"])
        self.assertEqual(EXIT_PC, state["pc"])
        registers = state["registers"]
        self.assertEqual(self.labels["plain_bgezal_branch"] + 8, registers[fixtures.RA])
        self.assertEqual(0xFFFFFFFFAABBCCDD, registers[fixtures.T1])
        self.assertEqual(0x8000000000000000, registers[fixtures.T8])
        self.assertEqual(1, registers[fixtures.T9])
        self.assertEqual(1, registers[fixtures.V0])
        self.assertEqual(1, registers[fixtures.V1])
        self.assertEqual(1, registers[fixtures.A0])
        self.assertEqual(1, registers[fixtures.A1])
        self.assertEqual(0, registers[fixtures.A2])
        self.assertEqual(99, registers[fixtures.A3])
        self.assertEqual(99, registers[fixtures.T2])
        self.assertEqual(45, registers[fixtures.T3])
        self.assertEqual(55, registers[fixtures.T4])
        self.assertEqual(78, registers[fixtures.T5])
        self.assertEqual(55, registers[fixtures.T6])
        # Six non-likely branch forms: delay slots always execute, link writes happen
        # even when the branch is not taken.
        self.assertEqual(999, registers[fixtures.S0])
        self.assertEqual(1111, registers[fixtures.S1])
        self.assertEqual(0, registers[fixtures.S2])
        # The BGEZAL delay slot copied $ra after the link write, on all paths.
        self.assertEqual(self.labels["plain_bgezal_branch"] + 8,
                         registers[fixtures.S3])
        self.assertEqual(333, registers[fixtures.S4])
        self.assertEqual(444, registers[fixtures.S5])
        self.assertEqual(0xFFFFFFFFFFFFFFFF, registers[fixtures.S6])
        self.assertEqual(555, registers[fixtures.S7])
        self.assertEqual(0, registers[fixtures.K0])
        self.assertEqual(0, registers[fixtures.K1])
        self.assertEqual(777, registers[fixtures.GP])
        self.assertEqual(0, registers[fixtures.SP])
        self.assertEqual(0, registers[fixtures.FP])
        self.assertEqual(0, registers[0])
        data = final_data(state)
        self.assertEqual(
            (0xAABBCCDD + 0x11223344) & 0xFFFFFFFF,
            int.from_bytes(data[0:4], "little"))
        self.assertEqual(0x00000037, int.from_bytes(data[16:20], "little"))
        self.assertEqual(0x11223344, int.from_bytes(data[4:8], "little"))
        self.assertEqual(0x8000000000000000, int.from_bytes(data[8:16], "little"))

    def _native_or_skip(self) -> dict:
        try:
            native.find_msvc()
        except native.HarnessError as exc:
            self.skipTest(f"generated-native leg skipped: MSVC unavailable: {exc}")
        if type(self).native_result is None:
            try:
                type(self).native_result = normalize_generated(
                    native.run_differential(self.parsed, max_steps=MAX_STEPS))
            except native.HarnessError as exc:
                self.fail(f"generated-native leg failed: {exc}")
        return type(self).native_result

    def _runtime_or_skip(self) -> dict:
        if not (BINARY and Path(BINARY).is_file()):
            self.skipTest(
                "runtime-harness leg skipped: RPTP_RUN_BINARY is not a built executable")
        if type(self).runtime_result is None:
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "cross_path.elf"
                path.write_bytes(self.image)
                completed = subprocess.run(
                    [BINARY, "--json", "--trace", str(path)],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=False,
                )
            self.assertEqual(0, completed.returncode, completed.stderr)
            document = json.loads(completed.stdout)
            self.assertEqual("rptp.runtime.run.v1", document["schema"])
            self.assertEqual("ok", document["status"])
            type(self).runtime_result = normalize_runtime(document, trace=True)
        return type(self).runtime_result

    def assert_cross_path_equal(self, left: dict, right: dict, left_name: str,
                                right_name: str) -> None:
        self.assertEqual(HALT_REASON_MAP[left_name], left["reason"], left_name)
        self.assertEqual(HALT_REASON_MAP[right_name], right["reason"], right_name)
        self.assertEqual(left["halted"], right["halted"])
        self.assertEqual(left["pc"], right["pc"])
        self.assertEqual(left["steps"], right["steps"])
        self.assertEqual(left["trace"], right["trace"])
        self.assertEqual(left["registers"], right["registers"])
        self.assertEqual(final_data(left), final_data(right))

    def test_generated_native_matches_oracle(self) -> None:
        native_state = self._native_or_skip()
        self.assert_cross_path_equal(self.oracle_result, native_state, "oracle", "generated")

    def test_runtime_harness_matches_oracle(self) -> None:
        runtime_state = self._runtime_or_skip()
        self.assert_cross_path_equal(self.oracle_result, runtime_state, "oracle", "runtime")

    def test_all_three_paths_agree(self) -> None:
        native_state = self._native_or_skip()
        runtime_state = self._runtime_or_skip()
        self.assert_cross_path_equal(self.oracle_result, native_state, "oracle", "generated")
        self.assert_cross_path_equal(self.oracle_result, runtime_state, "oracle", "runtime")
        self.assertEqual(native_state["registers"], runtime_state["registers"])
        self.assertEqual(native_state["trace"], runtime_state["trace"])
        self.assertEqual(final_data(native_state), final_data(runtime_state))


if __name__ == "__main__":
    unittest.main(verbosity=2)
