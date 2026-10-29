# SPDX-License-Identifier: GPL-3.0-or-later
"""Differential tests for the rptp-run synthetic execution harness.

The harness executes only the documented synthetic instruction subset on top of
the native loader. These tests build synthetic images independently and compare
the CLI result with the Python oracle. They are skipped unless CTest provides the
binary.
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
from tools.rptp_gate0_spike import execute_oracle

BINARY = os.environ.get("RPTP_RUN_BINARY", "")
SCHEMA = "rptp.runtime.run.v1"
BASE = 0x00100000
DATA = 0x00002000
CODE_OFFSET = 0x200
DATA_OFFSET = 0x100
ROOT = Path(__file__).resolve().parents[1]


def encode_i(op: int, rs: int, rt: int, imm: int) -> int:
    return ((op & 0x3F) << 26) | ((rs & 0x1F) << 21) | ((rt & 0x1F) << 16) | (imm & 0xFFFF)


def encode_r(rs: int, rt: int, rd: int, shamt: int, funct: int) -> int:
    return ((rs & 0x1F) << 21) | ((rt & 0x1F) << 16) | ((rd & 0x1F) << 11) | ((shamt & 0x1F) << 6) | (funct & 0x3F)


def encode_j(op: int, target: int) -> int:
    return ((op & 0x3F) << 26) | ((target >> 2) & 0x03FFFFFF)


def main_words() -> list[int]:
    return [
        encode_i(0x09, 0, 8, 7),  # 0x00 addiu t0, zero, 7
        encode_i(0x09, 0, 9, 5),  # 0x04 addiu t1, zero, 5
        encode_r(8, 9, 10, 0, 0x21),  # 0x08 addu t2, t0, t1
        encode_i(0x09, 0, 11, DATA),  # 0x0c addiu t3, zero, 0x2000
        encode_i(0x2B, 11, 10, 0),  # 0x10 sw t2, 0(t3)
        encode_i(0x23, 11, 12, 0),  # 0x14 lw t4, 0(t3)
        encode_i(0x05, 10, 12, 5),  # 0x18 bne t2, t4, 0x30 (not taken)
        encode_i(0x09, 0, 16, 3),  # 0x1c addiu s0, zero, 3 (delay slot)
        encode_i(0x04, 10, 9, 4),  # 0x20 beq t2, t1, 0x34 (not taken)
        encode_i(0x09, 0, 17, 4),  # 0x24 addiu s1, zero, 4 (delay slot)
        encode_j(0x03, BASE + 0x48),  # 0x28 jal 0x00100048
        encode_i(0x09, 0, 4, 9),  # 0x2c addiu a0, zero, 9 (delay slot)
        encode_i(0x09, 0, 18, 6),  # 0x30 addiu s2, zero, 6
        encode_j(0x02, BASE + 0x5C),  # 0x34 j 0x0010005c
        encode_r(0, 0, 0, 0, 0),  # 0x38 nop (delay slot)
        encode_r(0, 0, 0, 0, 0),  # 0x3c nop
        encode_r(0, 0, 0, 0, 0),  # 0x40 nop
        encode_r(0, 0, 0, 0, 0),  # 0x44 nop
        encode_r(4, 10, 2, 0, 0x21),  # 0x48 addu v0, a0, t2
        encode_r(31, 0, 0, 0, 0x08),  # 0x4c jr ra
        encode_i(0x09, 0, 19, 8),  # 0x50 addiu s3, zero, 8 (delay slot)
        encode_r(0, 0, 0, 0, 0),  # 0x54 nop
        encode_r(0, 0, 0, 0, 0),  # 0x58 nop
        encode_i(0x09, 0, 20, 10),  # 0x5c addiu s4, zero, 10
    ]


def extended_words() -> list[int]:
    return [
        encode_r(0, 0, 31, 0, 0x21),  # 0x00 addu ra, zero, zero (normalize the oracle's ra)
        encode_i(0x09, 0, 8, 1),  # 0x04 addiu t0, zero, 1
        encode_i(0x0F, 0, 9, 0x8000),  # 0x08 lui t1, 0x8000
        encode_i(0x0F, 0, 10, 0x1234),  # 0x0c lui t2, 0x1234
        encode_i(0x0D, 10, 10, 0x5678),  # 0x10 ori t2, t2, 0x5678
        encode_i(0x0C, 10, 11, 0x00FF),  # 0x14 andi t3, t2, 0x00ff
        encode_i(0x0E, 10, 12, 0xFFFF),  # 0x18 xori t4, t2, 0xffff
        encode_r(0, 10, 13, 4, 0x00),  # 0x1c sll t5, t2, 4
        encode_r(9, 8, 14, 0, 0x2A),  # 0x20 slt t6, t1, t0
        encode_r(8, 9, 15, 0, 0x2B),  # 0x24 sltu t7, t0, t1
        encode_i(0x0A, 9, 16, -1),  # 0x28 slti s0, t1, -1
        encode_i(0x0B, 8, 17, -1),  # 0x2c sltiu s1, t0, -1
        encode_i(0x19, 9, 18, -1),  # 0x30 daddiu s2, t1, -1
        encode_r(10, 12, 19, 0, 0x24),  # 0x34 and s3, t2, t4
        encode_r(11, 13, 20, 0, 0x25),  # 0x38 or s4, t3, t5
        encode_r(9, 8, 21, 0, 0x26),  # 0x3c xor s5, t1, t0
        encode_r(8, 8, 22, 0, 0x27),  # 0x40 nor s6, t0, t0
        encode_i(0x09, 0, 23, 0x2000),  # 0x44 addiu s7, zero, 0x2000
        encode_i(0x2B, 23, 10, 0),  # 0x48 sw t2, 0(s7)
        encode_i(0x23, 23, 24, 0),  # 0x4c lw t8, 0(s7)
        encode_i(0x0F, 0, 25, 0x4000),  # 0x50 lui t9, 0x4000
        encode_r(0, 25, 26, 1, 0x00),  # 0x54 sll k0, t9, 1
        encode_r(26, 25, 27, 0, 0x2D),  # 0x58 daddu k1, k0, t9
        encode_r(26, 26, 28, 0, 0x2D),  # 0x5c daddu gp, k0, k0
        encode_r(8, 9, 0, 0, 0x2D),  # 0x60 daddu zero, t0, t1
        encode_r(8, 9, 2, 0, 0x23),  # 0x64 subu v0, t0, t1
        encode_r(9, 8, 3, 0, 0x23),  # 0x68 subu v1, t1, t0
        encode_r(10, 12, 4, 0, 0x23),  # 0x6c subu a0, t2, t4
        encode_r(0, 8, 5, 0, 0x23),  # 0x70 subu a1, zero, t0
        encode_r(8, 9, 0, 0, 0x23),  # 0x74 subu zero, t0, t1
        encode_i(0x3F, 23, 28, 8),  # 0x78 sd gp, 8(s7)
        encode_i(0x37, 23, 29, 8),  # 0x7c ld sp, 8(s7)
        encode_i(0x3F, 0, 0, 0),  # 0x80 sd zero, 0(s7)
        encode_i(0x37, 23, 30, 0),  # 0x84 ld fp, 0(s7)
        encode_r(0, 0, 0, 0, 0),  # 0x88 nop
    ]


def build_program(words: list[int], entry: int = BASE, data_memsz: int = 16) -> bytes:
    code = b"".join(struct.pack("<I", word & 0xFFFFFFFF) for word in words)
    payload = b"\x00" * (CODE_OFFSET - DATA_OFFSET) + code
    return build_elf(
        entry,
        [
            {"offset": DATA_OFFSET, "vaddr": DATA, "filesz": 4, "memsz": data_memsz, "flags": 6},
            {"offset": CODE_OFFSET, "vaddr": BASE, "filesz": len(code), "memsz": len(code), "flags": 5},
        ],
        payload=payload,
        payload_offset=DATA_OFFSET,
    )


@unittest.skipUnless(BINARY and Path(BINARY).is_file(), "RPTP_RUN_BINARY is not a built executable")
class RuntimeExecutionCliTests(unittest.TestCase):
    def run_cli(self, image: bytes, *arguments: str) -> tuple[subprocess.CompletedProcess[str], Path]:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "input.elf"
        path.write_bytes(image)
        command = [BINARY, *arguments, str(path)]
        return subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False), path

    def test_result_matches_the_python_oracle(self) -> None:
        words = main_words()
        result, _ = self.run_cli(build_program(words), "--json", "--trace")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("", result.stderr.strip())
        document = json.loads(result.stdout)
        self.assertEqual(SCHEMA, document["schema"])
        self.assertEqual("ok", document["status"])
        self.assertEqual("0x00100000", document["entry_point"])
        self.assertEqual("unmapped-pc", document["halt_reason"])

        oracle = execute_oracle(BASE, {BASE + 4 * index: word for index, word in enumerate(words)})
        self.assertEqual(len(oracle["trace"]), document["steps"])
        self.assertEqual(oracle["trace"], [int(value, 16) for value in document["trace"]])
        self.assertEqual(oracle["pc"], int(document["final_pc"], 16))
        self.assertEqual(32, len(document["registers"]))
        for index, expected in enumerate(oracle["registers"]):
            self.assertEqual(expected, int(document["registers"][index], 16), f"register {index}")

        expected_memory = {int(address): value for address, value in oracle["memory"].items()}
        actual_memory = {
            int(entry["address"], 16): int(entry["value"], 16) for entry in document["memory_writes"]
        }
        self.assertEqual(expected_memory, actual_memory)

    def test_extended_subset_matches_the_python_oracle(self) -> None:
        words = extended_words()
        result, _ = self.run_cli(build_program(words), "--json", "--trace")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("", result.stderr.strip())
        document = json.loads(result.stdout)
        self.assertEqual(SCHEMA, document["schema"])
        self.assertEqual("ok", document["status"])
        self.assertEqual("0x00100000", document["entry_point"])
        self.assertEqual("unmapped-pc", document["halt_reason"])

        oracle = execute_oracle(BASE, {BASE + 4 * index: word for index, word in enumerate(words)})
        self.assertEqual(len(oracle["trace"]), document["steps"])
        self.assertEqual(oracle["trace"], [int(value, 16) for value in document["trace"]])
        self.assertEqual(oracle["pc"], int(document["final_pc"], 16))
        self.assertEqual(32, len(document["registers"]))
        for index, expected in enumerate(oracle["registers"]):
            self.assertEqual(expected, int(document["registers"][index], 16), f"register {index}")

        expected_memory = {int(address): value for address, value in oracle["memory"].items()}
        actual_memory = {
            int(entry["address"], 16): int(entry["value"], 16) for entry in document["memory_writes"]
        }
        self.assertEqual(expected_memory, actual_memory)
        self.assertEqual(0xFFFFFFFFC0000000, int(document["registers"][27], 16))
        self.assertEqual(0xFFFFFFFF00000000, int(document["registers"][28], 16))
        self.assertEqual(0, int(document["registers"][0], 16))
        self.assertEqual(0xFFFFFFFF80000001, int(document["registers"][2], 16))
        self.assertEqual(0x000000007FFFFFFF, int(document["registers"][3], 16))
        self.assertEqual(0xFFFFFFFFFFFFACF1, int(document["registers"][4], 16))
        self.assertEqual(0xFFFFFFFFFFFFFFFF, int(document["registers"][5], 16))
        self.assertEqual(0xFFFFFFFF00000000, int(document["registers"][29], 16))
        self.assertEqual(0, int(document["registers"][30], 16))
        self.assertEqual(0x00000000, actual_memory[0x00002000])
        self.assertEqual(0x00000000, actual_memory[0x00002004])
        self.assertEqual(0x00000000, actual_memory[0x00002008])
        self.assertEqual(0xFFFFFFFF, actual_memory[0x0000200C])

    def test_output_is_deterministic(self) -> None:
        image = build_program(main_words())
        first, _ = self.run_cli(image, "--json")
        second, _ = self.run_cli(image, "--json")
        self.assertEqual(0, first.returncode, first.stderr)
        self.assertEqual(first.stdout, second.stdout)

    def test_unsupported_instruction_fails_closed(self) -> None:
        result, _ = self.run_cli(build_program([0x0000003F]), "--json")
        self.assertEqual(2, result.returncode)
        self.assertEqual("", result.stderr.strip())
        document = json.loads(result.stdout)
        self.assertEqual("error", document["status"])
        self.assertEqual("EXEC_UNSUPPORTED_INSTRUCTION", document["error"]["code"])

    def test_step_limit_fails_closed(self) -> None:
        loop = [encode_j(0x02, BASE), encode_r(0, 0, 0, 0, 0)]
        result, _ = self.run_cli(build_program(loop), "--json", "--max-steps", "5")
        self.assertEqual(2, result.returncode)
        document = json.loads(result.stdout)
        self.assertEqual("EXEC_STEP_LIMIT", document["error"]["code"])

    def test_unmapped_store_fails_closed(self) -> None:
        words = [
            encode_i(0x09, 0, 8, 1),
            encode_i(0x09, 0, 11, 0x3000),
            encode_i(0x2B, 11, 8, 0),
        ]
        result, _ = self.run_cli(build_program(words), "--json")
        self.assertEqual(2, result.returncode)
        document = json.loads(result.stdout)
        self.assertEqual("EXEC_MEMORY_FAULT", document["error"]["code"])

    def test_unaligned_doubleword_load_fails_closed(self) -> None:
        words = [
            encode_i(0x09, 0, 8, 1),
            encode_i(0x09, 0, 23, DATA),
            encode_i(0x37, 23, 8, 2),
        ]
        result, _ = self.run_cli(build_program(words), "--json")
        self.assertEqual(2, result.returncode)
        document = json.loads(result.stdout)
        self.assertEqual("EXEC_MEMORY_FAULT", document["error"]["code"])

    def test_unaligned_doubleword_store_fails_closed(self) -> None:
        words = [
            encode_i(0x09, 0, 8, 1),
            encode_i(0x09, 0, 23, DATA),
            encode_i(0x3F, 23, 8, 4),
        ]
        result, _ = self.run_cli(build_program(words), "--json")
        self.assertEqual(2, result.returncode)
        document = json.loads(result.stdout)
        self.assertEqual("EXEC_MEMORY_FAULT", document["error"]["code"])

    def test_doubleword_load_past_the_segment_fails_closed(self) -> None:
        words = [
            encode_i(0x09, 0, 23, DATA),
            encode_i(0x37, 23, 8, 0),
        ]
        result, _ = self.run_cli(build_program(words, data_memsz=4), "--json")
        self.assertEqual(2, result.returncode)
        document = json.loads(result.stdout)
        self.assertEqual("EXEC_MEMORY_FAULT", document["error"]["code"])

    def test_doubleword_store_past_the_segment_fails_closed(self) -> None:
        words = [
            encode_i(0x09, 0, 8, 1),
            encode_i(0x09, 0, 23, DATA),
            encode_i(0x3F, 23, 8, 4),
        ]
        result, _ = self.run_cli(build_program(words, data_memsz=12), "--json")
        self.assertEqual(2, result.returncode)
        document = json.loads(result.stdout)
        self.assertEqual("EXEC_MEMORY_FAULT", document["error"]["code"])

    def test_doubleword_load_across_adjacent_segments_fails_closed(self) -> None:
        words = [
            encode_i(0x09, 0, 23, DATA),
            encode_i(0x37, 23, 8, 0),
        ]
        code = b"".join(struct.pack("<I", word) for word in words)
        payload = b"\x00" * (CODE_OFFSET - DATA_OFFSET) + code
        image = build_elf(
            BASE,
            [
                {"offset": DATA_OFFSET, "vaddr": DATA, "filesz": 4, "memsz": 8, "flags": 6},
                {"offset": DATA_OFFSET + 4, "vaddr": DATA + 8, "filesz": 4, "memsz": 8, "flags": 6},
                {"offset": CODE_OFFSET, "vaddr": BASE, "filesz": len(code), "memsz": len(code), "flags": 5},
            ],
            payload=payload,
            payload_offset=DATA_OFFSET,
        )
        result, _ = self.run_cli(image, "--json")
        self.assertEqual(2, result.returncode)
        document = json.loads(result.stdout)
        self.assertEqual("EXEC_MEMORY_FAULT", document["error"]["code"])

    def test_neighbouring_coprocessor_transfers_fail_closed(self) -> None:
        for word in (encode_i(0x36, 0, 8, 0), encode_i(0x3E, 0, 8, 0)):
            with self.subTest(word=f"0x{word:08x}"):
                result, _ = self.run_cli(build_program([word]), "--json")
                self.assertEqual(2, result.returncode)
                document = json.loads(result.stdout)
                self.assertEqual("EXEC_UNSUPPORTED_INSTRUCTION", document["error"]["code"])

    def test_control_transfer_in_delay_slot_fails_closed(self) -> None:
        words = [
            encode_i(0x04, 0, 0, 2),
            encode_j(0x02, BASE),
            encode_r(0, 0, 0, 0, 0),
        ]
        result, _ = self.run_cli(build_program(words), "--json")
        self.assertEqual(2, result.returncode)
        document = json.loads(result.stdout)
        self.assertEqual("EXEC_DELAY_SLOT_CONTROL", document["error"]["code"])

    def test_loader_error_is_reported_with_load_taxonomy(self) -> None:
        result, _ = self.run_cli(b"not an elf at all" + bytes(48), "--json")
        self.assertEqual(2, result.returncode)
        document = json.loads(result.stdout)
        self.assertEqual("LOAD_NOT_ELF", document["error"]["code"])

    def test_usage_and_read_errors_exit_one(self) -> None:
        result = subprocess.run([BINARY], capture_output=True, text=True, encoding="utf-8", check=False)
        self.assertEqual(1, result.returncode)
        image = build_program(main_words())
        zero_budget, _ = self.run_cli(image, "--json", "--max-steps", "0")
        self.assertEqual(1, zero_budget.returncode)
        missing = subprocess.run(
            [BINARY, str(Path(tempfile.gettempdir()) / "rptp-missing-image.elf")],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(1, missing.returncode)

    def test_gate0_fixture_store_is_outside_loaded_segments(self) -> None:
        fixture = ROOT / "tests" / "fixtures" / "gate0-r5900-subset.elf"
        if not fixture.is_file():
            self.skipTest("the registered Gate 0 fixture is unavailable")
        result = subprocess.run(
            [BINARY, "--json", str(fixture)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(2, result.returncode)
        document = json.loads(result.stdout)
        self.assertEqual("EXEC_MEMORY_FAULT", document["error"]["code"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
