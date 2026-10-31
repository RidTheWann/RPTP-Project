# SPDX-License-Identifier: GPL-3.0-or-later
"""Executable specification for conservative direct-evidence discovery.

Every fixture is a synthetic ELF or ISO assembled in memory with
``tools.rptp.fixtures``; no game bytes, BIOS images or emulator sources are
involved.  The tests assert only the contract in
``docs/FUNCTION_DISCOVERY.md``: observed direct evidence, candidate-only
entries, explicit unsupported diagnostics, deterministic output, fail-closed
limits and read-only input handling.
"""
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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.rptp.fixtures import (
    CODE_BASE,
    RA,
    T0,
    T1,
    ZERO,
    Assembler,
    build_elf,
    encode_i,
    encode_j,
    encode_r,
)


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


discover = _load("rptp_discover_under_test", ROOT / "tools" / "rptp_discover.py")
inspector = discover.inspector

BASE = CODE_BASE
BLOCK = 2048
VOLUME_BLOCKS = 32
CONFIG = b"BOOT2 = cdrom0:\\SLUS_123.45;1\nVER = 1.00\nVMODE = NTSC\n"


def _call_chain() -> bytes:
    asm = Assembler()
    asm.jal("f1")
    asm.nop()
    asm.jr(RA)
    asm.nop()
    asm.label("f1")
    asm.jal("f2")
    asm.nop()
    asm.jr(RA)
    asm.nop()
    asm.label("f2")
    asm.jr(RA)
    asm.nop()
    return build_elf(asm.resolve())


def _assert_blocks_cover(report: dict[str, object]) -> None:
    code = report["code"]
    assert isinstance(code, dict)
    segments = {
        int(segment["program_header_index"]): segment
        for segment in code["segments"]
    }
    blocks = report["basic_blocks"]
    assert isinstance(blocks, list)
    total = 0
    previous_end = None
    previous_segment = None
    for block in blocks:
        assert isinstance(block, dict)
        segment = segments[int(block["segment_index"])]
        start = int(block["start"])
        end = int(block["end"])
        segment_index = int(block["segment_index"])
        if previous_segment == segment_index:
            assert previous_end is None or start == previous_end
        assert int(segment["virtual_address"]) <= start < end <= int(segment["virtual_word_end"])
        assert end - start == 4 * int(block["instruction_count"])
        total += int(block["instruction_count"])
        previous_end = end
        previous_segment = segment_index
    assert total == int(code["word_count"])


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
    pvd[40:72] = b"RPTP DISCOVERY TEST".ljust(32, b" ")
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


class FunctionDiscoveryTests(unittest.TestCase):
    def test_direct_call_chain_reports_candidates_and_blocks(self) -> None:
        elf = _call_chain()
        report = discover.discover_elf_bytes(elf, name="call-chain.elf")

        self.assertEqual(report["status"], "DISCOVERED")
        self.assertEqual(report["model"], "conservative_direct_evidence_v1")
        self.assertEqual(report["entry_point"], BASE)
        self.assertEqual(report["source"]["input_name"], "call-chain.elf")
        self.assertEqual(report["source"]["sha256"], hashlib.sha256(elf).hexdigest())
        self.assertEqual(report["code"]["word_count"], 10)
        self.assertEqual(report["code"]["supported_word_count"], 10)
        self.assertEqual(report["code"]["unsupported_word_count"], 0)
        self.assertEqual(report["code"]["call_site_count"], 2)
        self.assertEqual(report["code"]["candidate_count"], 3)

        candidates = report["candidates"]
        self.assertEqual([item["address"] for item in candidates], [BASE, BASE + 0x10, BASE + 0x20])
        self.assertEqual(candidates[0]["origins"], ["elf_entry"])
        self.assertEqual(candidates[1]["origins"], ["jal_target"])
        self.assertEqual(candidates[1]["call_sites"], [BASE])
        self.assertEqual(candidates[2]["origins"], ["jal_target"])
        self.assertEqual(candidates[2]["call_sites"], [BASE + 0x10])
        for candidate in candidates:
            self.assertTrue(candidate["candidate_only"])
            self.assertNotIn("end", candidate)
            self.assertNotIn("size", candidate)
            self.assertNotIn("extent", candidate)
            self.assertNotIn("reachable", candidate)

        blocks = report["basic_blocks"]
        self.assertEqual([block["start"] for block in blocks], [BASE + offset for offset in (0, 8, 0x10, 0x18, 0x20)])
        self.assertEqual(blocks[0]["start_reasons"], ["entry", "segment_start", "transfer"])
        _assert_blocks_cover(report)

        self.assertEqual(
            [(site["kind"], site["mnemonic"]) for site in report["indirect_transfers"]],
            [("return_candidate", "jr"), ("return_candidate", "jr"), ("return_candidate", "jr")],
        )
        self.assertTrue(all(site["resolution"] == "unresolved" for site in report["indirect_transfers"]))

    def test_loop_branch_target_and_partition(self) -> None:
        asm = Assembler()
        asm.addiu(T0, ZERO, 0)
        asm.label("loop")
        asm.addiu(T0, T0, 1)
        asm.slti(T1, T0, 10)
        asm.bne(T0, T1, "loop")
        asm.nop()
        asm.jr(RA)
        asm.nop()
        report = discover.discover_elf_bytes(build_elf(asm.resolve()), name="loop.elf")

        self.assertEqual(report["code"]["branch_site_count"], 1)
        site = report["branch_sites"][0]
        self.assertEqual(site["site"], BASE + 0x0C)
        self.assertEqual(site["mnemonic"], "bne")
        self.assertEqual(site["target"], BASE + 4)
        self.assertEqual(site["target_status"], "in_code")
        self.assertFalse(site["likely"])
        self.assertEqual(
            report["direct_targets"]["branch"],
            [{"address": BASE + 4, "site_count": 1, "target_status": "in_code", "in_code": True}],
        )
        self.assertEqual(
            [block["start"] for block in report["basic_blocks"]],
            [BASE, BASE + 4, BASE + 0x0C, BASE + 0x14],
        )
        self.assertIn("branch_target", report["basic_blocks"][1]["start_reasons"])
        self.assertIn("transfer", report["basic_blocks"][2]["start_reasons"])
        _assert_blocks_cover(report)

    def test_indirect_transfers_are_unresolved_and_never_guessed(self) -> None:
        asm = Assembler()
        asm.jr(T0)
        asm.nop()
        asm.jalr(RA, T1)
        asm.nop()
        asm.jr(RA)
        asm.nop()
        report = discover.discover_elf_bytes(build_elf(asm.resolve()), name="indirect.elf")

        self.assertEqual(report["code"]["indirect_site_count"], 3)
        self.assertEqual(report["code"]["candidate_count"], 1)
        self.assertEqual([item["address"] for item in report["candidates"]], [BASE])
        sites = report["indirect_transfers"]
        self.assertEqual([item["mnemonic"] for item in sites], ["jr", "jalr", "jr"])
        self.assertEqual([item["kind"] for item in sites], ["indirect_jump", "indirect_call", "return_candidate"])
        self.assertEqual([item["rs"] for item in sites], [T0, T1, RA])
        self.assertEqual(sites[1]["rd"], RA)
        self.assertTrue(all(item["resolution"] == "unresolved" for item in sites))
        self.assertEqual(report["direct_targets"]["branch"], [])
        self.assertEqual(report["direct_targets"]["jump"], [])
        self.assertEqual(report["direct_targets"]["call"], [])
        _assert_blocks_cover(report)

    def test_unsupported_encodings_get_explicit_diagnostics(self) -> None:
        asm = Assembler()
        asm.addiu(T0, ZERO, 1)
        asm.emit(0x0000000C)       # syscall
        asm.emit(0x0000000D)       # break
        asm.emit(0x46000000)       # cop1 (BC1)
        asm.emit(0x35 << 26)       # unrecognised primary opcode
        asm.emit(0x00000028)       # mfsa, catalogued but unsupported
        asm.emit(0x10 << 26)       # opaque cop0
        asm.nop()
        report = discover.discover_elf_bytes(build_elf(asm.resolve()), name="unsupported.elf")

        self.assertEqual(report["code"]["unsupported_word_count"], 6)
        diagnostics = [item for item in report["diagnostics"] if item["code"] == "UNSUPPORTED_ENCODING"]
        self.assertEqual(len(diagnostics), 6)
        self.assertEqual(
            [item["address"] for item in diagnostics],
            [BASE + offset for offset in (4, 8, 12, 16, 20, 24)],
        )
        self.assertTrue(all(item["delay_slot"] is False for item in diagnostics))
        self.assertEqual(
            {item["encoding"] for item in diagnostics},
            {"special_0x0c", "special_0x0d", "opcode_0x11", "opcode_0x35", "special_0x28", "opcode_0x10"},
        )
        self.assertEqual(report["diagnostic_counts"], {"UNSUPPORTED_ENCODING": 6})
        self.assertEqual(len(report["unsupported_encodings"]), 6)
        self.assertTrue(all(item["count"] == 1 for item in report["unsupported_encodings"]))

        unsupported_control = report["unsupported_control"]
        self.assertEqual(
            [(item["site"], item["kind"]) for item in unsupported_control],
            [
                (BASE + 4, "unsupported_halt"),
                (BASE + 8, "unsupported_halt"),
                (BASE + 24, "opaque_cop0"),
            ],
        )
        block_starts = {block["start"] for block in report["basic_blocks"]}
        for diagnostic in diagnostics:
            self.assertIn(diagnostic["address"], block_starts)
            block = next(block for block in report["basic_blocks"] if block["start"] == diagnostic["address"])
            self.assertEqual(block["instruction_count"], 1)
        _assert_blocks_cover(report)

    def test_unsupported_encoding_in_delay_slot_is_diagnosed_not_followed(self) -> None:
        asm = Assembler()
        asm.jr(RA)
        asm.emit(0x0000000C)
        asm.jr(RA)
        asm.nop()
        report = discover.discover_elf_bytes(build_elf(asm.resolve()), name="delay-slot.elf")

        unsupported = [item for item in report["diagnostics"] if item["code"] == "UNSUPPORTED_ENCODING"]
        self.assertEqual(len(unsupported), 1)
        self.assertEqual(unsupported[0]["address"], BASE + 4)
        self.assertTrue(unsupported[0]["delay_slot"])
        self.assertEqual(
            [(item["code"], item["address"]) for item in report["diagnostics"] if item["code"] == "CONTROL_IN_DELAY_SLOT"],
            [("CONTROL_IN_DELAY_SLOT", BASE + 4)],
        )
        self.assertEqual(report["unsupported_control"], [])
        self.assertEqual([block["start"] for block in report["basic_blocks"]], [BASE, BASE + 8])
        self.assertEqual(report["basic_blocks"][0]["instruction_count"], 2)
        self.assertTrue(any("delay slot" in warning for warning in report["warnings"]))
        _assert_blocks_cover(report)

    def test_missing_delay_slot_is_reported(self) -> None:
        words = [0, encode_j(0x03, BASE)]
        report = discover.discover_elf_bytes(build_elf(words), name="missing-delay.elf")

        self.assertEqual(len(report["call_sites"]), 1)
        self.assertEqual(report["call_sites"][0]["target"], BASE)
        self.assertEqual(report["call_sites"][0]["target_status"], "in_code")
        self.assertIn(BASE, [item["address"] for item in report["candidates"]])
        self.assertEqual(
            [(item["code"], item["address"]) for item in report["diagnostics"] if item["code"] == "MISSING_DELAY_SLOT"],
            [("MISSING_DELAY_SLOT", BASE + 4)],
        )
        self.assertTrue(any("no delay slot" in warning for warning in report["warnings"]))
        _assert_blocks_cover(report)

    def test_out_of_code_call_target_is_reported_not_followed(self) -> None:
        words = [encode_j(0x03, 0x00300000), 0, encode_r(0x08, 0, RA, 0), 0]
        report = discover.discover_elf_bytes(build_elf(words), name="outside.elf")

        self.assertEqual(report["status"], "DISCOVERED_WITH_WARNINGS")
        self.assertEqual(len(report["call_sites"]), 1)
        self.assertEqual(report["call_sites"][0]["target"], 0x00300000)
        self.assertEqual(report["call_sites"][0]["target_status"], "outside_loaded_segments")
        self.assertEqual(
            report["direct_targets"]["call"],
            [{
                "address": 0x00300000,
                "site_count": 1,
                "target_status": "outside_loaded_segments",
                "in_code": False,
            }],
        )
        self.assertEqual([item["address"] for item in report["candidates"]], [BASE])
        self.assertTrue(any("not followed" in warning for warning in report["warnings"]))
        _assert_blocks_cover(report)

    def test_target_in_delay_slot_is_not_a_block_boundary(self) -> None:
        asm = Assembler()
        asm.beq(ZERO, ZERO, "l1")
        asm.nop()
        asm.emit(encode_i(0x04, 0, 0, 0))  # branch to its own delay slot at pc+8
        asm.nop()
        asm.label("l1")
        asm.jr(RA)
        asm.nop()
        report = discover.discover_elf_bytes(build_elf(asm.resolve()), name="target-delay-slot.elf")

        site = report["branch_sites"][1]
        self.assertEqual(site["site"], BASE + 8)
        self.assertEqual(site["target"], BASE + 0x0C)
        self.assertEqual(site["target_status"], "delay_slot")
        self.assertNotIn(BASE + 0x0C, [block["start"] for block in report["basic_blocks"]])
        self.assertEqual(
            [item["code"] for item in report["diagnostics"]],
            ["TARGET_IN_DELAY_SLOT"],
        )
        self.assertTrue(any("delay_slot=1" in warning for warning in report["warnings"]))
        _assert_blocks_cover(report)

    def test_trailing_bytes_are_reported_and_not_decoded(self) -> None:
        elf = bytearray(build_elf([0, 0, 0, 0]))
        struct.pack_into("<I", elf, 52 + 16, 15)  # p_filesz
        struct.pack_into("<I", elf, 52 + 20, 16)  # p_memsz
        report = discover.discover_elf_bytes(bytes(elf), name="trailing.elf")

        self.assertEqual(report["code"]["word_count"], 3)
        self.assertEqual(report["code"]["segments"][0]["trailing_bytes"], 3)
        self.assertIn("3 trailing", " ".join(report["warnings"]))
        self.assertEqual(report["status"], "DISCOVERED_WITH_WARNINGS")
        _assert_blocks_cover(report)

    def test_malformed_inputs_fail_closed_with_stable_codes(self) -> None:
        base = _call_chain()
        cases: list[tuple[str, bytes, dict[str, object], str]] = []
        cases.append(("not-elf", bytes(64), {}, "BOOT_EXECUTABLE_NOT_ELF"))

        mutated = bytearray(base)
        struct.pack_into("<H", mutated, 18, 3)
        cases.append(("machine", bytes(mutated), {}, "DISCOVER_UNSUPPORTED_MACHINE"))

        mutated = bytearray(base)
        struct.pack_into("<H", mutated, 16, 3)
        cases.append(("type", bytes(mutated), {}, "DISCOVER_UNSUPPORTED_TYPE"))

        mutated = bytearray(base)
        struct.pack_into("<I", mutated, 24, 0x00300000)
        cases.append(("entry-outside", bytes(mutated), {}, "DISCOVER_ENTRY_NOT_IN_CODE"))

        mutated = bytearray(base)
        struct.pack_into("<I", mutated, 24, BASE + 2)
        cases.append(("entry-unaligned", bytes(mutated), {}, "DISCOVER_ENTRY_UNALIGNED"))

        mutated = bytearray(base)
        struct.pack_into("<I", mutated, 52 + 24, 6)
        cases.append(("no-exec", bytes(mutated), {}, "DISCOVER_NO_EXECUTABLE_CODE"))

        mutated = bytearray(base)
        struct.pack_into("<H", mutated, 44, 0)
        cases.append(("no-load", bytes(mutated), {}, "DISCOVER_NO_LOAD_SEGMENTS"))

        mutated = bytearray(base)
        struct.pack_into("<I", mutated, 52 + 8, BASE + 2)
        struct.pack_into("<I", mutated, 52 + 28, 0)
        cases.append(("segment-unaligned", bytes(mutated), {}, "DISCOVER_SEGMENT_UNALIGNED"))

        with tempfile.TemporaryDirectory() as temporary:
            missing = Path(temporary) / "missing.elf"
            with self.assertRaises(inspector.InspectError) as raised:
                discover.discover_elf_path(missing)
            self.assertEqual(raised.exception.code, "DISCOVER_INPUT_NOT_FOUND")

        for name, data, options, code in cases:
            with self.subTest(case=name):
                with self.assertRaises(inspector.InspectError) as raised:
                    discover.discover_elf_bytes(data, name=f"{name}.elf", **options)
                self.assertEqual(raised.exception.code, code)

        with self.assertRaises(inspector.InspectError) as raised:
            discover.discover_elf_bytes(base, max_instructions=1)
        self.assertEqual(raised.exception.code, "DISCOVER_INSTRUCTION_LIMIT")

        with self.assertRaises(inspector.InspectError) as raised:
            discover.discover_elf_bytes(build_elf([0x0000000C, 0x0000000D]), max_diagnostics=1)
        self.assertEqual(raised.exception.code, "DISCOVER_DIAGNOSTIC_LIMIT")

        with self.assertRaises(inspector.InspectError) as raised:
            discover.discover_elf_bytes(base, max_input_bytes=len(base) - 1)
        self.assertEqual(raised.exception.code, "DISCOVER_SIZE_LIMIT")

        with self.assertRaises(inspector.InspectError) as raised:
            discover.discover_elf_bytes(base, max_instructions=0)
        self.assertEqual(raised.exception.code, "DISCOVER_INVALID_LIMIT")

        asm = Assembler()
        asm.jr(RA)
        asm.nop()
        with self.assertRaises(inspector.InspectError) as raised:
            discover.discover_elf_bytes(build_elf(asm.resolve(), entry=BASE + 4))
        self.assertEqual(raised.exception.code, "DISCOVER_ENTRY_IN_DELAY_SLOT")

    def test_executable_segment_overlap_fails_closed(self) -> None:
        asm = Assembler()
        asm.jr(RA)
        asm.nop()
        elf = bytearray(build_elf(asm.resolve(), data=b"\0\0\0\0"))
        second = 52 + 32
        struct.pack_into("<I", elf, second + 8, BASE + 4)   # p_vaddr overlaps code
        struct.pack_into("<I", elf, second + 24, 5)         # PF_X | PF_R
        struct.pack_into("<I", elf, second + 28, 0)         # no alignment constraint
        with self.assertRaises(inspector.InspectError) as raised:
            discover.discover_elf_bytes(bytes(elf), name="overlap.elf")
        self.assertEqual(raised.exception.code, "DISCOVER_CODE_OVERLAP")

    def test_output_is_deterministic_and_input_is_not_mutated(self) -> None:
        elf = _call_chain()
        before = bytes(elf)
        first = discover.discover_elf_bytes(elf, name="same.elf")
        second = discover.discover_elf_bytes(elf, name="same.elf")
        self.assertEqual(first, second)
        self.assertEqual(
            json.dumps(first, sort_keys=True),
            json.dumps(second, sort_keys=True),
        )
        self.assertEqual(elf, before)
        self.assertEqual(first["source"]["input_name"], "same.elf")
        self.assertNotIn(str(ROOT), json.dumps(first, sort_keys=True))

    def test_cli_json_is_deterministic_and_writes_no_artifacts(self) -> None:
        elf = _call_chain()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "synthetic.elf"
            path.write_bytes(elf)
            command = [
                sys.executable,
                str(ROOT / "tools" / "rptp_discover.py"),
                "--elf",
                str(path),
                "--json",
            ]
            first = subprocess.run(command, capture_output=True, text=True, cwd=ROOT)
            second = subprocess.run(command, capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(first.stdout, second.stdout)
            report = json.loads(first.stdout)
            self.assertEqual(report["status"], "DISCOVERED")
            self.assertEqual(report["entry_point"], BASE)
            self.assertNotIn(str(path.parent), first.stdout)
            self.assertEqual({item.name for item in Path(temporary).iterdir()}, {"synthetic.elf"})

            human = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "rptp_discover.py"), "--elf", str(path)],
                capture_output=True,
                text=True,
                cwd=ROOT,
            )
            self.assertEqual(human.returncode, 0, human.stderr)
            self.assertIn("candidate-only", human.stdout)
            self.assertIn("Static direct-evidence only", human.stdout)

            bad = Path(temporary) / "bad.elf"
            bad.write_bytes(bytes(64))
            failure = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "rptp_discover.py"), "--elf", str(bad), "--json"],
                capture_output=True,
                text=True,
                cwd=ROOT,
            )
            self.assertEqual(failure.returncode, 2)
            error = json.loads(failure.stdout)
            self.assertEqual(error["status"], "ERROR")
            self.assertEqual(error["error_code"], "BOOT_EXECUTABLE_NOT_ELF")

            limited = subprocess.run(
                command + ["--max-instructions", "1"],
                capture_output=True,
                text=True,
                cwd=ROOT,
            )
            self.assertEqual(limited.returncode, 2)
            self.assertEqual(json.loads(limited.stdout)["error_code"], "DISCOVER_INSTRUCTION_LIMIT")

    def test_iso_boot_is_read_in_memory_without_modification(self) -> None:
        elf = _call_chain()
        image = _iso(elf)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "synthetic.iso"
            path.write_bytes(image)
            before = path.read_bytes()
            before_mtime = path.stat().st_mtime_ns
            report = discover.discover_iso_path(path)
            after = path.read_bytes()
            after_mtime = path.stat().st_mtime_ns
        self.assertEqual(before, after)
        self.assertEqual(before_mtime, after_mtime)
        self.assertEqual(report["source"]["kind"], "iso")
        self.assertEqual(report["source"]["input_name"], "synthetic.iso")
        self.assertEqual(report["source"]["image_size_bytes"], len(image))
        self.assertEqual(report["source"]["boot_path"], "SLUS_123.45;1")
        self.assertEqual(report["source"]["boot_size_bytes"], len(elf))
        self.assertEqual(report["source"]["boot_sha256"], hashlib.sha256(elf).hexdigest())
        self.assertEqual(report["entry_point"], BASE)
        self.assertEqual([item["address"] for item in report["candidates"]], [BASE, BASE + 0x10, BASE + 0x20])
        _assert_blocks_cover(report)

    def test_limitations_and_candidates_do_not_claim_extents(self) -> None:
        report = discover.discover_elf_bytes(_call_chain(), name="claims.elf")
        text = " ".join(report["limitations"])
        self.assertIn("not a function boundary", text)
        self.assertIn("candidate-only", text)
        self.assertIn("never guessed", text)
        self.assertIn("No code is executed", text)
        for candidate in report["candidates"]:
            self.assertTrue(candidate["candidate_only"])
            self.assertEqual(
                set(candidate),
                {"address", "origins", "call_sites", "candidate_only", "note"},
            )
        self.assertEqual(report["candidates"][0]["note"], "Candidate entry only; no function extent, reachability or completeness claim.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
