# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


census = _load("rptp_census_under_test", ROOT / "tools" / "rptp_census.py")
inspector = census.inspector
spike = _load("rptp_census_spike_test", ROOT / "tools" / "rptp_gate0_spike.py")

BLOCK = 2048
VOLUME_BLOCKS = 32
BASE = 0x00100000
CONFIG = b"BOOT2 = cdrom0:\\SLUS_123.45;1\nVER = 1.00\nVMODE = NTSC\n"


def _both32(value: int) -> bytes:
    return value.to_bytes(4, "little") + value.to_bytes(4, "big")


def _both16(value: int) -> bytes:
    return value.to_bytes(2, "little") + value.to_bytes(2, "big")


def _record(extent: int, size: int, name: bytes, flags: int = 0) -> bytes:
    padding = 1 if len(name) % 2 == 0 else 0
    data = bytearray(33 + len(name) + padding)
    data[0] = len(data)
    data[2:10] = _both32(extent)
    data[10:18] = _both32(size)
    data[25] = flags
    data[28:32] = _both16(1)
    data[32] = len(name)
    data[33:33 + len(name)] = name
    return bytes(data)


def _iso(executable: bytes, boot_lba: int = 21) -> bytearray:
    image = bytearray(VOLUME_BLOCKS * BLOCK)
    pvd = bytearray(BLOCK)
    pvd[0], pvd[1:6], pvd[6] = 1, b"CD001", 1
    pvd[40:72] = b"RPTP CENSUS TEST".ljust(32, b" ")
    pvd[80:88] = _both32(VOLUME_BLOCKS)
    pvd[120:124] = _both16(1)
    pvd[124:128] = _both16(1)
    pvd[128:132] = _both16(BLOCK)
    pvd[881] = 1
    root = _record(19, BLOCK, b"\x00", 0x02)
    pvd[156:156 + len(root)] = root
    image[16 * BLOCK:17 * BLOCK] = pvd
    terminator = bytearray(BLOCK)
    terminator[0], terminator[1:6], terminator[6] = 255, b"CD001", 1
    image[17 * BLOCK:18 * BLOCK] = terminator
    directory = bytearray(BLOCK)
    records = [
        _record(19, BLOCK, b"\x00", 0x02),
        _record(19, BLOCK, b"\x01", 0x02),
        _record(20, len(CONFIG), b"SYSTEM.CNF;1"),
        _record(boot_lba, len(executable), b"SLUS_123.45;1"),
    ]
    offset = 0
    for record in records:
        directory[offset:offset + len(record)] = record
        offset += len(record)
    image[19 * BLOCK:20 * BLOCK] = directory
    image[20 * BLOCK:20 * BLOCK + len(CONFIG)] = CONFIG
    start = boot_lba * BLOCK
    image[start:start + len(executable)] = executable
    return image


def _rows() -> list[tuple[int, str, int]]:
    return [
        (BASE, "addiu", spike.encode_i(0x09, 0, 2, 1)),
        (BASE + 4, "daddiu", spike.encode_i(0x19, 0, 3, -1)),
        (BASE + 8, "syscall", 0x0000000C),
        (BASE + 12, "nop", 0),
    ]


def _elf() -> bytes:
    return spike.build_elf_from_rows(_rows())


class BootCensusTests(unittest.TestCase):
    def test_census_counts_supported_and_raw_unsupported_encodings(self):
        report = census.census_elf_bytes(_elf(), name="synthetic.elf")
        self.assertEqual(report["status"], "CENSUSED")
        self.assertEqual(report["model"], "pt_load_word_census_v1")
        self.assertEqual(report["decoder"]["module"], "tools/rptp/isa.py")
        self.assertEqual(
            report["decoder"]["supported_mnemonic_count"],
            len(census.isa.SUPPORTED_MNEMONICS),
        )
        expected_digest = hashlib.sha256(
            "\n".join(sorted(census.isa.SUPPORTED_MNEMONICS)).encode("ascii")
        ).hexdigest()
        self.assertEqual(report["decoder"]["supported_mnemonic_set_sha256"], expected_digest)
        self.assertEqual(report["source"]["size_bytes"], len(_elf()))
        self.assertEqual(report["source"]["sha256"], hashlib.sha256(_elf()).hexdigest())
        self.assertEqual(report["elf"]["entry_point"], BASE)
        counts = report["census"]
        self.assertEqual(counts["word_count"], 4)
        self.assertEqual(counts["zero_word_count"], 1)
        self.assertEqual(counts["supported_word_count"], 3)
        self.assertEqual(counts["unsupported_word_count"], 1)
        self.assertEqual(counts["unique_word_count"], 4)
        self.assertEqual(counts["trailing_bytes"], 0)
        self.assertAlmostEqual(counts["supported_ratio"], 0.75)
        labels = {item["label"]: item for item in report["opcodes"]}
        self.assertTrue(labels["addiu"]["supported"])
        self.assertTrue(labels["daddiu"]["supported"])
        self.assertTrue(labels["nop"]["supported"])
        self.assertFalse(labels["special_0x0c"]["supported"])
        self.assertEqual(report["unsupported_encodings"], [labels["special_0x0c"]])
        self.assertEqual([item["label"] for item in report["opcodes"]], ["addiu", "daddiu", "nop", "special_0x0c"])
        self.assertIn("No code was executed", " ".join(report["limitations"]))

    def test_census_reports_trailing_bytes(self):
        elf = bytearray(_elf())
        struct.pack_into("<I", elf, 52 + 16, 14)
        struct.pack_into("<I", elf, 52 + 20, 16)
        report = census.census_elf_bytes(bytes(elf), name="trailing.elf")
        self.assertEqual(report["census"]["word_count"], 3)
        self.assertEqual(report["census"]["trailing_bytes"], 2)
        self.assertEqual(report["status"], "CENSUSED_WITH_WARNINGS")
        self.assertTrue(any("trailing byte" in warning for warning in report["warnings"]))

    def test_census_uses_current_decoder_including_branch_likely(self):
        rows = [
            (BASE, "beql", 0x50000000),
            (BASE + 4, "nop", 0),
            (BASE + 8, "subu", 0x00000023),
        ]
        report = census.census_elf_bytes(spike.build_elf_from_rows(rows), name="likely.elf")
        labels = {item["label"]: item for item in report["opcodes"]}
        self.assertTrue(labels["beql"]["supported"])
        self.assertTrue(labels["subu"]["supported"])
        self.assertEqual(report["census"]["supported_word_count"], 3)
        self.assertEqual(report["census"]["unsupported_word_count"], 0)

    def test_fails_closed_on_non_elf_and_size_limit(self):
        with self.assertRaises(inspector.InspectError) as raised:
            census.census_elf_bytes(bytes(64), name="not-elf.bin")
        self.assertEqual(raised.exception.code, "BOOT_EXECUTABLE_NOT_ELF")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "image.elf"
            path.write_bytes(_elf())
            with self.assertRaises(inspector.InspectError) as raised:
                census.census_elf_path(path, max_boot_bytes=16)
            self.assertEqual(raised.exception.code, "CENSUS_SIZE_LIMIT")

    def test_census_is_deterministic_and_does_not_mutate_input(self):
        data = _elf()
        first = census.census_elf_bytes(data, name="synthetic.elf")
        second = census.census_elf_bytes(data, name="synthetic.elf")
        self.assertEqual(first, second)
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))
        self.assertEqual(data, _elf())

    def test_iso_census_reads_boot_in_memory_without_writing(self):
        image = _iso(_elf())
        before = bytes(image)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "synthetic.iso"
            path.write_bytes(image)
            report = census.census_iso_path(path)
            self.assertEqual(bytes(path.read_bytes()), before)
        self.assertEqual(report["status"], "CENSUSED")
        self.assertEqual(report["source"]["kind"], "iso")
        self.assertEqual(report["source"]["boot_path"], "SLUS_123.45;1")
        self.assertEqual(report["source"]["boot_size_bytes"], len(_elf()))
        self.assertEqual(report["source"]["boot_sha256"], hashlib.sha256(_elf()).hexdigest())
        self.assertEqual(report["census"]["word_count"], 4)
        self.assertEqual(report["census"]["supported_word_count"], 3)

    def test_cli_emits_json_and_stable_errors(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "synthetic.elf"
            path.write_bytes(_elf())
            success = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "rptp_census.py"), str(path), "--elf", "--json"],
                capture_output=True,
                text=True,
                cwd=ROOT,
            )
            self.assertEqual(success.returncode, 0, success.stderr)
            report = json.loads(success.stdout)
            self.assertEqual(report["status"], "CENSUSED")
            self.assertEqual(report["census"]["word_count"], 4)
            bad = Path(temporary) / "bad.elf"
            bad.write_bytes(bytes(64))
            failure = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "rptp_census.py"), str(bad), "--elf", "--json"],
                capture_output=True,
                text=True,
                cwd=ROOT,
            )
            self.assertEqual(failure.returncode, 2)
            error = json.loads(failure.stdout)
            self.assertEqual(error["status"], "ERROR")
            self.assertEqual(error["error_code"], "BOOT_EXECUTABLE_NOT_ELF")


if __name__ == "__main__":
    unittest.main(verbosity=2)
