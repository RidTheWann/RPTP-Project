# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module {relative_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


spike = load_module("rptp_gate0_spike", "tools/rptp_gate0_spike.py")
guard = load_module("check_forbidden_artifacts", "tools/check_forbidden_artifacts.py")


class Gate0SpikeTests(unittest.TestCase):
    def test_synthetic_elf_is_valid_and_matches_manifest(self):
        data = spike.build_fixture_elf()
        fixture = ROOT / "tests/fixtures/gate0-r5900-subset.elf"
        manifest = json.loads((ROOT / "tests/fixtures/MANIFEST").read_text(encoding="utf-8"))
        record = next(row for row in manifest["fixtures"] if row["path"] == "tests/fixtures/gate0-r5900-subset.elf")
        self.assertEqual(hashlib.sha256(data).hexdigest(), record["sha256"])
        self.assertEqual(fixture.read_bytes(), data)
        entry, words, info = spike.parse_elf(data)
        self.assertEqual(entry, spike.BASE)
        self.assertEqual(info["instruction_count"], 28)
        self.assertEqual(len(words), 28)

    def test_truncated_elf_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "truncated"):
            spike.parse_elf(b"\x7fELF\x01\x01")

    def test_wrong_machine_is_rejected(self):
        data = bytearray(spike.build_fixture_elf())
        data[18:20] = (3).to_bytes(2, "little")
        with self.assertRaisesRegex(ValueError, "EM_MIPS"):
            spike.parse_elf(bytes(data))

    def test_unknown_opcode_fails_explicitly(self):
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            spike.decode_instruction(spike.BASE, 0x0000003F)

    def test_executable_segment_past_eof_is_rejected(self):
        data = bytearray(spike.build_fixture_elf())
        # First program header starts at 52; p_offset is its second 32-bit word.
        data[56:60] = (0xFFFFF000).to_bytes(4, "little")
        with self.assertRaisesRegex(ValueError, "extends beyond input"):
            spike.parse_elf(bytes(data))

    def test_control_transfer_without_delay_slot_is_rejected(self):
        jr_ra = spike.encode_r(spike.RA, 0, 0, 0, 0x08)
        with self.assertRaisesRegex(ValueError, "Missing delay-slot"):
            spike.decode_program({spike.BASE: jr_ra})

    def test_control_transfer_inside_delay_slot_is_rejected(self):
        jr_ra = spike.encode_r(spike.RA, 0, 0, 0, 0x08)
        with self.assertRaisesRegex(ValueError, "Control transfer in delay slot"):
            spike.decode_program({spike.BASE: jr_ra, spike.BASE + 4: jr_ra})

    def test_oracle_exercises_control_flow_memory_and_delay_slots(self):
        entry, words, _ = spike.parse_elf(spike.build_fixture_elf())
        state = spike.normalize_state(spike.execute_oracle(entry, words))
        regs = state["registers"]
        self.assertEqual(regs[spike.V0], 42)
        self.assertEqual(regs[spike.T2], 12)
        self.assertEqual(regs[spike.T4], 12)
        self.assertEqual(regs[spike.S4], 23)  # BNE not taken; its delay slot still executes.
        self.assertEqual(regs[spike.S0], 17)  # BEQ taken; its delay slot still executes.
        self.assertEqual(regs[spike.S1], 1)
        self.assertEqual(regs[spike.S2], 99)
        self.assertEqual(regs[spike.S3], 55)
        self.assertEqual(state["memory"], [[spike.MEMORY_ADDRESS, 12]])
        self.assertEqual(state["pc"], spike.RETURN_SENTINEL)
        self.assertTrue(state["halted"])

    def test_recompiler_output_is_deterministic(self):
        entry, words, _ = spike.parse_elf(spike.build_fixture_elf())
        decoded = spike.decode_program(words)
        first = spike.emit_cpp(decoded, entry)
        second = spike.emit_cpp(decoded, entry)
        self.assertEqual(first.encode("utf-8"), second.encode("utf-8"))

    def test_manifest_allows_only_registered_fixture_hash(self):
        self.assertEqual(guard.scan_repository(ROOT), [])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "tests/fixtures").mkdir(parents=True)
            good = b"synthetic fixture bytes"
            good_path = root / "tests/fixtures/good.elf"
            good_path.write_bytes(good)
            manifest = {
                "schema_version": 1,
                "fixtures": [{
                    "path": "tests/fixtures/good.elf",
                    "sha256": hashlib.sha256(good).hexdigest(),
                    "origin": "Synthetic test fixture created by this test.",
                    "license_status": "No third-party code; original synthetic test data.",
                }],
            }
            (root / "tests/fixtures/MANIFEST").write_text(json.dumps(manifest), encoding="utf-8")
            self.assertEqual(guard.scan_repository(root), [])
            (root / "unregistered.elf").write_bytes(b"not registered")
            self.assertTrue(any("Unregistered binary fixture" in error for error in guard.scan_repository(root)))

    def test_iso_is_rejected_even_if_someone_adds_it_to_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "tests/fixtures").mkdir(parents=True)
            (root / "tests/fixtures/MANIFEST").write_text(json.dumps({"schema_version": 1, "fixtures": []}), encoding="utf-8")
            (root / "sample.iso").write_bytes(b"not a game")
            self.assertTrue(any("Forbidden proprietary/game artifact" in error for error in guard.scan_repository(root)))

    def test_manifest_cannot_allowlist_outside_fixtures_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "tests/fixtures").mkdir(parents=True)
            data = b"synthetic"
            (root / "outside.elf").write_bytes(data)
            manifest = {
                "schema_version": 1,
                "fixtures": [{
                    "path": "outside.elf",
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "origin": "test",
                    "license_status": "test",
                }],
            }
            (root / "tests/fixtures/MANIFEST").write_text(json.dumps(manifest), encoding="utf-8")
            self.assertTrue(any("may only cover tests/fixtures" in error for error in guard.scan_repository(root)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
