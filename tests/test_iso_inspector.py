# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import hashlib
import importlib.util
from io import BytesIO
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("rptp_inspect", ROOT / "tools/rptp_inspect.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Cannot load tools/rptp_inspect.py")
inspector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inspector)

BLOCK = 2048
VOLUME_BLOCKS = 32
DEFAULT_CONFIG = b"BOOT2 = cdrom0:\\SLUS_123.45;1\nVER = 1.00\nVMODE = NTSC\n"


def _both32(value: int) -> bytes:
    return value.to_bytes(4, "little") + value.to_bytes(4, "big")


def _both16(value: int) -> bytes:
    return value.to_bytes(2, "little") + value.to_bytes(2, "big")


def _record(
    extent: int,
    size: int,
    name: bytes,
    flags: int = 0,
    file_unit_size: int = 0,
    interleave_gap: int = 0,
) -> bytes:
    padding = 1 if len(name) % 2 == 0 else 0
    data = bytearray(33 + len(name) + padding)
    data[0] = len(data)
    data[2:10] = _both32(extent)
    data[10:18] = _both32(size)
    data[25] = flags
    data[26] = file_unit_size
    data[27] = interleave_gap
    data[28:32] = _both16(1)
    data[32] = len(name)
    data[33:33 + len(name)] = name
    return bytes(data)


def _elf(machine: int = 8, phnum: int = 1, elf_type: int = 2, entry_point: int = 0x00100000,
         load_offset: int = 84, load_filesz: int = 44, load_memsz: int | None = None,
         load_align: int = 4, load_vaddr: int | None = None, data_size: int = 128) -> bytes:
    if load_memsz is None:
        load_memsz = load_filesz
    if load_vaddr is None:
        load_vaddr = entry_point
    data = bytearray(data_size)
    data[:7] = b"\x7fELF" + bytes((1, 1, 1))
    data[16:18] = elf_type.to_bytes(2, "little")
    data[18:20] = machine.to_bytes(2, "little")
    data[20:24] = (1).to_bytes(4, "little")
    data[24:28] = entry_point.to_bytes(4, "little")
    data[28:32] = (52).to_bytes(4, "little")
    data[40:42] = (52).to_bytes(2, "little")
    data[42:44] = (32).to_bytes(2, "little")
    data[44:46] = phnum.to_bytes(2, "little")
    if phnum and 52 + 32 <= data_size:
        data[52:56] = (1).to_bytes(4, "little")
        data[56:60] = load_offset.to_bytes(4, "little")
        data[60:64] = load_vaddr.to_bytes(4, "little")
        data[64:68] = load_vaddr.to_bytes(4, "little")
        data[68:72] = load_filesz.to_bytes(4, "little")
        data[72:76] = load_memsz.to_bytes(4, "little")
        data[76:80] = (5).to_bytes(4, "little")
        data[80:84] = load_align.to_bytes(4, "little")
    return bytes(data)


def _iso(config: bytes | None = DEFAULT_CONFIG,
         executable: bytes | None = None, boot_lba: int = 21, block_size: int = BLOCK,
         system_flags: int = 0, boot_flags: int = 0, subdir_flags: int | None = None,
         system_interleave: tuple[int, int] = (0, 0),
         boot_interleave: tuple[int, int] = (0, 0),
         subdir_interleave: tuple[int, int] = (0, 0), tree: bool = False) -> bytearray:
    image = bytearray(VOLUME_BLOCKS * BLOCK)
    pvd = bytearray(BLOCK)
    pvd[0], pvd[1:6], pvd[6] = 1, b"CD001", 1
    pvd[40:72] = b"RPTP SYNTHETIC".ljust(32, b" ")
    pvd[80:88] = _both32(VOLUME_BLOCKS)
    pvd[120:124] = _both16(1)
    pvd[124:128] = _both16(1)
    pvd[128:132] = _both16(block_size)
    pvd[881] = 1
    root_record = _record(19, BLOCK, b"\x00", 0x02)
    pvd[156:156 + len(root_record)] = root_record
    image[16 * BLOCK:17 * BLOCK] = pvd
    terminator = bytearray(BLOCK)
    terminator[0], terminator[1:6], terminator[6] = 255, b"CD001", 1
    image[17 * BLOCK:18 * BLOCK] = terminator

    records = [_record(19, BLOCK, b"\x00", 0x02), _record(19, BLOCK, b"\x01", 0x02)]
    if subdir_flags is not None:
        records.append(_record(19, BLOCK, b"SUBDIR;1", subdir_flags | 0x02, *subdir_interleave))
    if tree:
        records.append(_record(22, BLOCK, b"SUBDIR;1", 0x02))
    if config is not None:
        records.append(_record(20, len(config), b"SYSTEM.CNF;1", system_flags, *system_interleave))
    exe = executable if executable is not None else _elf()
    records.append(_record(boot_lba, len(exe), b"SLUS_123.45;1", boot_flags, *boot_interleave))
    directory = bytearray(BLOCK)
    offset = 0
    for record in records:
        directory[offset:offset + len(record)] = record
        offset += len(record)
    image[19 * BLOCK:20 * BLOCK] = directory
    if config is not None:
        image[20 * BLOCK:20 * BLOCK + len(config)] = config
    if boot_lba < VOLUME_BLOCKS:
        end = min(len(image), boot_lba * BLOCK + len(exe))
        image[boot_lba * BLOCK:end] = exe[:end - boot_lba * BLOCK]
    if tree:
        subdir = bytearray(BLOCK)
        offset = 0
        for record in (
            _record(22, BLOCK, b"\x00", 0x02),
            _record(19, BLOCK, b"\x01", 0x02),
            _record(24, BLOCK, b"NESTED;1", 0x02),
        ):
            subdir[offset:offset + len(record)] = record
            offset += len(record)
        image[22 * BLOCK:23 * BLOCK] = subdir
        nested = bytearray(BLOCK)
        offset = 0
        for record in (
            _record(24, BLOCK, b"\x00", 0x02),
            _record(22, BLOCK, b"\x01", 0x02),
            _record(25, 32, b"DEEP.BIN;1"),
        ):
            nested[offset:offset + len(record)] = record
            offset += len(record)
        image[24 * BLOCK:25 * BLOCK] = nested
        deep = b"SYNTHETIC DEEP FILE".ljust(32, b"\x00")
        image[25 * BLOCK:25 * BLOCK + len(deep)] = deep
    return image


class RecordingStream(BytesIO):
    def __init__(self, data: bytes):
        super().__init__(data)
        self.read_sizes: list[int] = []
        self.read_offsets: list[int] = []

    def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(size)
        self.read_offsets.append(self.tell())
        return super().read(size)


class ShortReadStream:
    def __init__(self, data: bytes):
        self._data = data
        self._position = 0

    def seek(self, offset: int) -> int:
        self._position = offset
        return offset

    def read(self, size: int) -> bytes:
        start = self._position
        end = min(len(self._data), start + max(0, size - 1))
        self._position = end
        return self._data[start:end]


def _padded_config(size: int = 1000) -> bytes:
    base = b"BOOT2 = cdrom0:\\SLUS_123.45;1\n"
    return base + b"#" * (size - len(base))


def _mutate(base: bytes, rng: random.Random) -> bytes:
    data = bytearray(base)
    mode = rng.randrange(3)
    if mode == 0:
        for _ in range(rng.randint(1, 4)):
            data[rng.randrange(len(data))] = rng.randrange(256)
    elif mode == 1:
        data = data[:rng.randrange(len(data) + 1)]
    else:
        start = rng.randrange(len(data))
        chunk = data[start:start + rng.randint(1, 64)]
        data[start:start + len(chunk)] = b"\x00" * len(chunk)
    return bytes(data)


class IsoInspectorTests(unittest.TestCase):
    def test_inspects_synthetic_iso_and_elf(self):
        report = inspector.inspect_bytes(bytes(_iso()), "memory.iso")
        self.assertEqual(report["status"], "INSPECTED")
        self.assertEqual(report["iso9660"]["volume_id"], "RPTP SYNTHETIC")
        self.assertEqual(report["iso9660"]["logical_block_size"], BLOCK)
        self.assertEqual(report["system_cnf"]["boot_key"], "BOOT2")
        self.assertEqual(report["boot_executable"]["path"], "SLUS_123.45;1")
        self.assertEqual(report["boot_executable"]["sha256"], hashlib.sha256(_elf()).hexdigest())
        self.assertEqual(report["boot_executable"]["elf"]["machine_id"], 8)
        self.assertEqual(report["boot_executable"]["elf"]["entry_point"], 0x00100000)
        self.assertEqual(report["boot_executable"]["elf"]["load_segment_count"], 1)
        self.assertEqual(report["boot_executable"]["resolved_path"], ["SLUS_123.45;1"])
        self.assertEqual(report["boot_executable"]["device"], "cdrom0")
        self.assertEqual(report["boot_executable"]["extent"]["extent_lba"], 21)
        self.assertEqual(report["boot_executable"]["extent"]["extent_bytes"], len(_elf()))
        self.assertEqual(report["system_cnf"]["size_bytes"], len(DEFAULT_CONFIG))
        self.assertEqual(report["system_cnf"]["sha256"], hashlib.sha256(DEFAULT_CONFIG).hexdigest())
        self.assertEqual(report["system_cnf"]["device"], "cdrom0")
        self.assertEqual(report["iso9660"]["volume_set_size"], 1)
        self.assertEqual(report["iso9660"]["volume_sequence_number"], 1)
        self.assertEqual(report["iso9660"]["root_directory"]["extent_lba"], 19)

    def test_supports_legacy_boot_key(self):
        report = inspector.inspect_bytes(bytes(_iso(config=b"BOOT = cdrom0:\\SLUS_123.45;1\n")))
        self.assertEqual(report["system_cnf"]["boot_key"], "BOOT")

    def test_rejects_small_image(self):
        with self.assertRaises(inspector.InspectError) as ctx:
            inspector.inspect_bytes(bytes(10 * BLOCK))
        self.assertEqual(ctx.exception.code, "IMAGE_TOO_SMALL")

    def test_rejects_unaligned_image(self):
        with self.assertRaises(inspector.InspectError) as ctx:
            inspector.inspect_bytes(bytes(VOLUME_BLOCKS * BLOCK + 1))
        self.assertEqual(ctx.exception.code, "IMAGE_ALIGNMENT_INVALID")

    def test_rejects_invalid_descriptor_signature(self):
        image = _iso()
        image[16 * BLOCK + 1:16 * BLOCK + 6] = b"XXXXX"
        with self.assertRaises(inspector.InspectError) as ctx:
            inspector.inspect_bytes(bytes(image))
        self.assertEqual(ctx.exception.code, "VOLUME_DESCRIPTOR_SIGNATURE")

    def test_rejects_both_endian_mismatch(self):
        image = _iso()
        image[16 * BLOCK + 84:16 * BLOCK + 88] = (99).to_bytes(4, "big")
        with self.assertRaises(inspector.InspectError) as ctx:
            inspector.inspect_bytes(bytes(image))
        self.assertEqual(ctx.exception.code, "BOTH_ENDIAN_MISMATCH")

    def test_rejects_unsupported_block_size(self):
        with self.assertRaises(inspector.InspectError) as ctx:
            inspector.inspect_bytes(bytes(_iso(block_size=1024)))
        self.assertEqual(ctx.exception.code, "UNSUPPORTED_LOGICAL_BLOCK_SIZE")

    def test_rejects_missing_system_cnf(self):
        with self.assertRaises(inspector.InspectError) as ctx:
            inspector.inspect_bytes(bytes(_iso(config=None)))
        self.assertEqual(ctx.exception.code, "SYSTEM_CNF_NOT_FOUND")

    def test_rejects_config_without_boot_key(self):
        with self.assertRaises(inspector.InspectError) as ctx:
            inspector.inspect_bytes(bytes(_iso(config=b"VER = 1.00\nVMODE = NTSC\n")))
        self.assertEqual(ctx.exception.code, "BOOT_CONFIG_MISSING")

    def test_rejects_parent_path_component(self):
        config = b"BOOT2 = cdrom0:\\..\\SLUS_123.45;1\n"
        with self.assertRaises(inspector.InspectError) as ctx:
            inspector.inspect_bytes(bytes(_iso(config=config)))
        self.assertEqual(ctx.exception.code, "UNSAFE_BOOT_PATH")

    def test_rejects_extent_outside_volume(self):
        with self.assertRaises(inspector.InspectError) as ctx:
            inspector.inspect_bytes(bytes(_iso(boot_lba=1000)))
        self.assertEqual(ctx.exception.code, "EXTENT_OUT_OF_BOUNDS")

    def test_rejects_huge_extent_without_overflow(self):
        data = bytes(_iso())
        reader = inspector.IsoReader(BytesIO(data), len(data), "huge.iso")
        reader.volume_blocks = VOLUME_BLOCKS
        with self.assertRaises(inspector.InspectError) as ctx:
            reader.extent({"lba": 0xFFFFFFFF, "xa_len": 0, "size": 0xFFFFFFFF, "name": "huge"})
        self.assertEqual(ctx.exception.code, "EXTENT_OUT_OF_BOUNDS")

    def test_rejects_truncated_volume_space(self):
        image = _iso()
        image[16 * BLOCK + 80:16 * BLOCK + 88] = _both32(VOLUME_BLOCKS + 1)
        with self.assertRaises(inspector.InspectError) as ctx:
            inspector.inspect_bytes(bytes(image))
        self.assertEqual(ctx.exception.code, "IMAGE_TRUNCATED")

    def test_accepts_image_larger_than_pvd_volume(self):
        image = _iso()
        image.extend(b"\x00" * BLOCK)
        data = bytes(image)

        report = inspector.inspect_bytes(data, "larger.iso")
        self.assertEqual(report["status"], "INSPECTED")
        self.assertEqual(report["image_size_bytes"], (VOLUME_BLOCKS + 1) * BLOCK)

        survey = inspector.IsoReader(BytesIO(data), len(data), "larger.iso").survey()
        self.assertEqual(survey["status"], "SURVEYED")
        self.assertEqual(survey["sector_count"], VOLUME_BLOCKS + 1)
        self.assertEqual(survey["volume_space_blocks"], VOLUME_BLOCKS)
        self.assertEqual(survey["volume_space_relation"], "smaller")
        self.assertEqual(survey["volume_space_delta_bytes"], -BLOCK)

    def test_rejects_short_stream_read(self):
        data = bytes(_iso())
        with self.assertRaises(inspector.InspectError) as ctx:
            inspector.inspect_stream(ShortReadStream(data), len(data), "short.iso")
        self.assertEqual(ctx.exception.code, "IMAGE_TRUNCATED")

    def test_max_read_bytes_is_configurable(self):
        with self.assertRaises(inspector.InspectError) as ctx:
            inspector.inspect_bytes(bytes(_iso()), max_read_bytes=8)
        self.assertEqual(ctx.exception.code, "FILE_SIZE_LIMIT")

    def test_file_reads_use_configured_chunks(self):
        config = _padded_config(1000)
        data = bytes(_iso(config=config))
        stream = RecordingStream(data)
        report = inspector.inspect_stream(stream, len(data), "chunked.iso", chunk_size=128)
        self.assertEqual(report["status"], "INSPECTED")
        self.assertNotIn(len(config), stream.read_sizes)
        self.assertIn(128, stream.read_sizes)

    def test_rejects_invalid_directory_record_length(self):
        image = _iso()
        image[19 * BLOCK] = 1
        with self.assertRaises(inspector.InspectError) as ctx:
            inspector.inspect_bytes(bytes(image))
        self.assertEqual(ctx.exception.code, "DIRECTORY_RECORD_LENGTH_INVALID")

    def test_rejects_non_elf_boot_file(self):
        with self.assertRaises(inspector.InspectError) as ctx:
            inspector.inspect_bytes(bytes(_iso(executable=bytes(84))))
        self.assertEqual(ctx.exception.code, "BOOT_EXECUTABLE_NOT_ELF")

    def test_rejects_program_header_table_out_of_bounds(self):
        with self.assertRaises(inspector.InspectError) as ctx:
            inspector.inspect_bytes(bytes(_iso(executable=_elf(phnum=3))))
        self.assertEqual(ctx.exception.code, "ELF_PROGRAM_HEADERS_OUT_OF_BOUNDS")

    def test_non_mips_machine_is_reported_as_warning(self):
        report = inspector.inspect_bytes(bytes(_iso(executable=_elf(machine=3))))
        self.assertEqual(report["status"], "INSPECTED_WITH_WARNINGS")
        self.assertTrue(any("EM_MIPS" in warning for warning in report["warnings"]))

    def test_boot_path_depth_is_bounded(self):
        path = b"BOOT2 = cdrom0:" + b"\\A" * 33 + b"\\SLUS_123.45;1\n"
        with self.assertRaises(inspector.InspectError) as ctx:
            inspector.inspect_bytes(bytes(_iso(config=path)))
        self.assertEqual(ctx.exception.code, "BOOT_PATH_DEPTH_LIMIT")

    def test_survey_counts_directories_files_and_depth(self):
        data = bytes(_iso(tree=True))
        report = inspector.IsoReader(BytesIO(data), len(data), "tree.iso").survey()
        self.assertEqual(report["status"], "SURVEYED")
        self.assertEqual(report["directory_count"], 3)
        self.assertEqual(report["directory_record_count"], 2)
        self.assertEqual(report["file_count"], 3)
        self.assertEqual(report["record_count"], 5)
        self.assertEqual(report["max_depth"], 2)
        self.assertEqual(report["multi_extent_records"], 0)
        self.assertEqual(report["interleaved_records"], 0)
        self.assertEqual(report["skipped_unsupported_directories"], 0)
        self.assertEqual(report["highest_file_extent_end_bytes"], 25 * BLOCK + 32)
        self.assertEqual(report["largest_file_size_bytes"], len(_elf()))

    def test_survey_counts_interleaved_records_without_rejecting(self):
        data = bytes(_iso(tree=True, system_interleave=(1, 1)))
        report = inspector.IsoReader(BytesIO(data), len(data), "tree.iso").survey()
        self.assertEqual(report["status"], "SURVEYED")
        self.assertEqual(report["interleaved_records"], 1)

    def test_survey_skips_multi_extent_directory(self):
        data = bytes(_iso(subdir_flags=0x80))
        report = inspector.IsoReader(BytesIO(data), len(data), "multi.iso").survey()
        self.assertEqual(report["status"], "SURVEYED")
        self.assertEqual(report["directory_count"], 1)
        self.assertEqual(report["multi_extent_records"], 1)
        self.assertEqual(report["skipped_unsupported_directories"], 1)

    def test_survey_rejects_multi_extent_root(self):
        image = _iso()
        image[16 * BLOCK + 156 + 25] = 0x82
        with self.assertRaises(inspector.InspectError) as ctx:
            inspector.IsoReader(BytesIO(bytes(image)), len(image), "root.iso").survey()
        self.assertEqual(ctx.exception.code, "MULTI_EXTENT_UNSUPPORTED")

    def test_survey_rejects_malformed_directory_records(self):
        cases: list[tuple[str, bytes, str]] = []

        invalid_length = _iso(tree=True)
        invalid_length[19 * BLOCK + 68] = 33
        cases.append(("invalid record length", bytes(invalid_length), "DIRECTORY_RECORD_LENGTH_INVALID"))

        truncated_identifier = _iso(tree=True)
        truncated_identifier[19 * BLOCK + 68 + 32] = 255
        cases.append(("truncated identifier", bytes(truncated_identifier), "DIRECTORY_IDENTIFIER_TRUNCATED"))

        unsafe_extent = _iso(tree=True)
        unsafe_extent[19 * BLOCK + 68 + 2:19 * BLOCK + 68 + 10] = _both32(VOLUME_BLOCKS + 1)
        cases.append(("unsafe extent", bytes(unsafe_extent), "EXTENT_OUT_OF_BOUNDS"))

        crossing = _iso()
        directory = bytearray(BLOCK)
        for index in range(60):
            record = _record(20, 1, bytes((65 + index,)))
            directory[index * 34:index * 34 + len(record)] = record
        directory[2040] = 34
        crossing[19 * BLOCK:20 * BLOCK] = directory
        cases.append(("record crosses block", bytes(crossing), "DIRECTORY_RECORD_CROSSES_BLOCK"))

        for label, data, code in cases:
            with self.subTest(case=label):
                errors: list[tuple[str, str]] = []
                for _ in range(2):
                    with self.assertRaises(inspector.InspectError) as ctx:
                        inspector.IsoReader(BytesIO(data), len(data), "malformed.iso").survey()
                    errors.append((ctx.exception.code, str(ctx.exception)))
                self.assertEqual(errors[0][0], code)
                self.assertEqual(errors[0], errors[1])

    def test_survey_enforces_limits_at_boundaries(self):
        data = bytes(_iso(tree=True))
        cases = (
            ("depth", "MAX_SURVEY_DEPTH", 2, 1, "SURVEY_DEPTH_LIMIT"),
            ("directories", "MAX_SURVEY_DIRECTORIES", 3, 2, "SURVEY_DIRECTORY_LIMIT"),
            ("records", "MAX_SURVEY_RECORDS", 11, 10, "SURVEY_RECORD_LIMIT"),
        )
        for label, constant, exact, over, code in cases:
            with self.subTest(limit=label):
                with mock.patch.object(inspector, constant, exact):
                    report = inspector.IsoReader(BytesIO(data), len(data), "limits.iso").survey()
                    self.assertEqual(report["status"], "SURVEYED")
                with mock.patch.object(inspector, constant, over):
                    with self.assertRaises(inspector.InspectError) as ctx:
                        inspector.IsoReader(BytesIO(data), len(data), "limits.iso").survey()
                    self.assertEqual(ctx.exception.code, code)

    def test_survey_counts_unsupported_file_and_directory_records(self):
        data = bytes(_iso(subdir_flags=0, subdir_interleave=(0, 1), boot_flags=0x80))
        report = inspector.IsoReader(BytesIO(data), len(data), "unsupported.iso").survey()
        self.assertEqual(report["status"], "SURVEYED")
        self.assertEqual(report["record_count"], 3)
        self.assertEqual(report["directory_record_count"], 1)
        self.assertEqual(report["file_count"], 2)
        self.assertEqual(report["multi_extent_records"], 1)
        self.assertEqual(report["interleaved_records"], 1)
        self.assertEqual(report["skipped_unsupported_directories"], 1)

    def test_survey_mutations_raise_only_inspect_errors(self):
        base = bytes(_iso(tree=True))
        rng = random.Random(20261023)
        for _ in range(250):
            data = _mutate(base, rng)
            try:
                report = inspector.IsoReader(BytesIO(data), len(data), "mutated.iso").survey()
            except inspector.InspectError:
                continue
            self.assertEqual(report["status"], "SURVEYED")

    def test_survey_file_mutations_preserve_input_bytes(self):
        base = bytes(_iso(tree=True))
        rng = random.Random(20261024)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "survey-mutated.iso"
            for _ in range(50):
                data = _mutate(base, rng)
                path.write_bytes(data)
                before = hashlib.sha256(data).hexdigest()
                try:
                    report = inspector.survey_path(path)
                except inspector.InspectError:
                    pass
                else:
                    self.assertEqual(report["status"], "SURVEYED")
                self.assertEqual(before, hashlib.sha256(path.read_bytes()).hexdigest())

    def test_cli_survey_json_preserves_input_for_success_and_error(self):
        invalid = _iso()
        invalid[19 * BLOCK + 68] = 33
        cases = (
            ("valid", bytes(_iso(tree=True)), 0, "SURVEYED", None),
            ("invalid", bytes(invalid), 2, "ERROR", "DIRECTORY_RECORD_LENGTH_INVALID"),
        )
        with tempfile.TemporaryDirectory() as directory:
            for label, data, returncode, status, error_code in cases:
                with self.subTest(case=label):
                    path = Path(directory) / f"{label}.iso"
                    path.write_bytes(data)
                    before = hashlib.sha256(data).hexdigest()
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tools/rptp_inspect.py"), str(path), "--survey", "--json"],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertEqual(result.returncode, returncode, result.stderr)
                    payload = json.loads(result.stdout)
                    self.assertEqual(payload["status"], status)
                    if error_code is not None:
                        self.assertEqual(payload["error_code"], error_code)
                    self.assertEqual(before, hashlib.sha256(path.read_bytes()).hexdigest())

    def test_cli_survey_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tree.iso"
            path.write_bytes(bytes(_iso(tree=True)))
            result = subprocess.run(
                [sys.executable, str(ROOT / "tools/rptp_inspect.py"), str(path), "--survey", "--json"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "SURVEYED")
            self.assertEqual(payload["directory_count"], 3)
            self.assertNotIn("input_name", payload)

    def test_cli_survey_text_reports_unsigned_volume_delta(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tree.iso"
            path.write_bytes(bytes(_iso(tree=True)) + bytes(BLOCK * 4))
            result = subprocess.run(
                [sys.executable, str(ROOT / "tools/rptp_inspect.py"), str(path), "--survey"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("smaller than the file by 8192 bytes", result.stdout)
            self.assertNotIn("-8192", result.stdout)

    def test_error_is_deterministic(self):
        data = bytes(_iso(boot_lba=1000))
        errors: list[tuple[str, str]] = []
        for _ in range(2):
            with self.assertRaises(inspector.InspectError) as ctx:
                inspector.inspect_bytes(data, "error.iso")
            errors.append((ctx.exception.code, str(ctx.exception)))
        self.assertEqual(errors[0], errors[1])

    def test_report_is_deterministic(self):
        data = bytes(_iso())
        first = json.dumps(inspector.inspect_bytes(data), sort_keys=True)
        second = json.dumps(inspector.inspect_bytes(data), sort_keys=True)
        self.assertEqual(first, second)

    def test_rejects_system_cnf_directory(self):
        with self.assertRaises(inspector.InspectError) as ctx:
            inspector.inspect_bytes(bytes(_iso(system_flags=0x02)))
        self.assertEqual(ctx.exception.code, "SYSTEM_CNF_IS_DIRECTORY")

    def test_rejects_multi_extent_system_cnf(self):
        with self.assertRaises(inspector.InspectError) as ctx:
            inspector.inspect_bytes(bytes(_iso(system_flags=0x80)))
        self.assertEqual(ctx.exception.code, "MULTI_EXTENT_UNSUPPORTED")

    def test_rejects_multi_extent_boot_executable(self):
        with self.assertRaises(inspector.InspectError) as ctx:
            inspector.inspect_bytes(bytes(_iso(boot_flags=0x80)))
        self.assertEqual(ctx.exception.code, "MULTI_EXTENT_UNSUPPORTED")

    def test_rejects_multi_extent_subdirectory(self):
        with self.assertRaises(inspector.InspectError) as ctx:
            inspector.inspect_bytes(bytes(_iso(subdir_flags=0x80)))
        self.assertEqual(ctx.exception.code, "MULTI_EXTENT_UNSUPPORTED")

    def test_rejects_interleaved_system_cnf(self):
        with self.assertRaises(inspector.InspectError) as ctx:
            inspector.inspect_bytes(bytes(_iso(system_interleave=(1, 1))))
        self.assertEqual(ctx.exception.code, "INTERLEAVED_UNSUPPORTED")

    def test_rejects_interleaved_boot_executable(self):
        with self.assertRaises(inspector.InspectError) as ctx:
            inspector.inspect_bytes(bytes(_iso(boot_interleave=(1, 1))))
        self.assertEqual(ctx.exception.code, "INTERLEAVED_UNSUPPORTED")

    def test_rejects_interleaved_directory(self):
        with self.assertRaises(inspector.InspectError) as ctx:
            inspector.inspect_bytes(bytes(_iso(subdir_flags=0, subdir_interleave=(1, 1))))
        self.assertEqual(ctx.exception.code, "INTERLEAVED_UNSUPPORTED")

    def test_ecma119_bp27_bp28_rejected_independently(self):
        cases = (
            ("SYSTEM.CNF file-unit", {"system_interleave": (1, 0)}),
            ("SYSTEM.CNF interleave-gap", {"system_interleave": (0, 1)}),
            ("boot executable file-unit", {"boot_interleave": (1, 0)}),
            ("boot executable interleave-gap", {"boot_interleave": (0, 1)}),
            ("subdirectory file-unit", {"subdir_flags": 0, "subdir_interleave": (1, 0)}),
            ("subdirectory interleave-gap", {"subdir_flags": 0, "subdir_interleave": (0, 1)}),
        )
        for label, kwargs in cases:
            with self.subTest(case=label):
                with self.assertRaises(inspector.InspectError) as ctx:
                    inspector.inspect_bytes(bytes(_iso(**kwargs)))
                self.assertEqual(ctx.exception.code, "INTERLEAVED_UNSUPPORTED")

    def test_interleaved_field_rejection_preserves_input_bytes(self):
        cases = (
            ("SYSTEM.CNF file-unit", {"system_interleave": (1, 0)}),
            ("SYSTEM.CNF interleave-gap", {"system_interleave": (0, 1)}),
            ("boot executable file-unit", {"boot_interleave": (1, 0)}),
            ("boot executable interleave-gap", {"boot_interleave": (0, 1)}),
            ("subdirectory file-unit", {"subdir_flags": 0, "subdir_interleave": (1, 0)}),
            ("subdirectory interleave-gap", {"subdir_flags": 0, "subdir_interleave": (0, 1)}),
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "interleaved.iso"
            for label, kwargs in cases:
                with self.subTest(case=label):
                    data = bytes(_iso(**kwargs))
                    path.write_bytes(data)
                    before = hashlib.sha256(data).hexdigest()
                    with self.assertRaises(inspector.InspectError) as ctx:
                        inspector.inspect_path(path)
                    self.assertEqual(ctx.exception.code, "INTERLEAVED_UNSUPPORTED")
                    self.assertEqual(before, hashlib.sha256(path.read_bytes()).hexdigest())

    def test_rejects_multi_volume_set(self):
        image = _iso()
        image[16 * BLOCK + 120:16 * BLOCK + 124] = _both16(2)
        with self.assertRaises(inspector.InspectError) as ctx:
            inspector.inspect_bytes(bytes(image))
        self.assertEqual(ctx.exception.code, "UNSUPPORTED_VOLUME_SET")

    def test_rejects_multi_volume_sequence(self):
        image = _iso()
        image[16 * BLOCK + 124:16 * BLOCK + 128] = _both16(2)
        with self.assertRaises(inspector.InspectError) as ctx:
            inspector.inspect_bytes(bytes(image))
        self.assertEqual(ctx.exception.code, "UNSUPPORTED_VOLUME_SET")

    def test_rejects_directory_record_volume_sequence(self):
        image = _iso()
        image[19 * BLOCK + 28:19 * BLOCK + 32] = _both16(2)
        with self.assertRaises(inspector.InspectError) as ctx:
            inspector.inspect_bytes(bytes(image))
        self.assertEqual(ctx.exception.code, "UNSUPPORTED_VOLUME_SEQUENCE")

    def test_rejects_empty_directory_identifier(self):
        image = _iso()
        image[16 * BLOCK + 156 + 32] = 0
        with self.assertRaises(inspector.InspectError) as ctx:
            inspector.inspect_bytes(bytes(image))
        self.assertEqual(ctx.exception.code, "DIRECTORY_IDENTIFIER_EMPTY")

    def test_rejects_out_of_bounds_load_segment(self):
        with self.assertRaises(inspector.InspectError) as ctx:
            inspector.inspect_bytes(bytes(_iso(executable=_elf(load_filesz=1000))))
        self.assertEqual(ctx.exception.code, "ELF_LOAD_SEGMENT_OUT_OF_BOUNDS")

    def test_rejects_load_segment_size_inversion(self):
        with self.assertRaises(inspector.InspectError) as ctx:
            inspector.inspect_bytes(bytes(_iso(executable=_elf(load_filesz=44, load_memsz=10))))
        self.assertEqual(ctx.exception.code, "ELF_LOAD_SEGMENT_SIZE_INVALID")

    def test_rejects_load_segment_bad_alignment(self):
        with self.assertRaises(inspector.InspectError) as ctx:
            inspector.inspect_bytes(bytes(_iso(executable=_elf(load_align=3))))
        self.assertEqual(ctx.exception.code, "ELF_LOAD_SEGMENT_ALIGNMENT_INVALID")

    def test_warns_when_elf_has_no_load_segments(self):
        report = inspector.inspect_bytes(bytes(_iso(executable=_elf(phnum=0))))
        self.assertEqual(report["status"], "INSPECTED_WITH_WARNINGS")
        self.assertTrue(any("PT_LOAD" in warning for warning in report["warnings"]))

    def test_warns_when_entry_point_is_outside_load_segments(self):
        executable = _elf(entry_point=0x00200000, load_vaddr=0x00100000)
        report = inspector.inspect_bytes(bytes(_iso(executable=executable)))
        self.assertEqual(report["status"], "INSPECTED_WITH_WARNINGS")
        self.assertTrue(any("entry point" in warning for warning in report["warnings"]))

    def test_warns_for_non_executable_elf(self):
        report = inspector.inspect_bytes(bytes(_iso(executable=_elf(elf_type=3))))
        self.assertEqual(report["status"], "INSPECTED_WITH_WARNINGS")
        self.assertTrue(any("ET_EXEC" in warning for warning in report["warnings"]))

    def test_warns_when_boot_path_has_no_device(self):
        report = inspector.inspect_bytes(bytes(_iso(config=b"BOOT2 = \\SLUS_123.45;1\n")))
        self.assertEqual(report["status"], "INSPECTED_WITH_WARNINGS")
        self.assertTrue(any("device prefix" in warning for warning in report["warnings"]))

    def test_cli_json_success_and_error(self):
        with tempfile.TemporaryDirectory() as directory:
            good = Path(directory) / "good.iso"
            good.write_bytes(bytes(_iso()))
            result = subprocess.run(
                [sys.executable, str(ROOT / "tools/rptp_inspect.py"), str(good), "--json"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "INSPECTED")
            self.assertEqual(payload["system_cnf"]["boot_key"], "BOOT2")

            bad = Path(directory) / "bad.iso"
            bad.write_bytes(b"not an iso")
            result = subprocess.run(
                [sys.executable, str(ROOT / "tools/rptp_inspect.py"), str(bad), "--json"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "ERROR")
            self.assertEqual(payload["error_code"], "IMAGE_TOO_SMALL")

    def test_malformed_mutations_raise_only_inspect_errors(self):
        base = bytes(_iso())
        rng = random.Random(20261021)
        for _ in range(250):
            data = _mutate(base, rng)
            try:
                report = inspector.inspect_bytes(data, "mutated.iso")
            except inspector.InspectError:
                continue
            self.assertIn(report["status"], ("INSPECTED", "INSPECTED_WITH_WARNINGS"))

    def test_file_mutations_preserve_input_bytes(self):
        base = bytes(_iso())
        rng = random.Random(20261022)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mutated.iso"
            for _ in range(50):
                data = _mutate(base, rng)
                path.write_bytes(data)
                before = hashlib.sha256(data).hexdigest()
                try:
                    report = inspector.inspect_path(path)
                except inspector.InspectError:
                    pass
                else:
                    self.assertIn(report["status"], ("INSPECTED", "INSPECTED_WITH_WARNINGS"))
                self.assertEqual(before, hashlib.sha256(path.read_bytes()).hexdigest())


class IsoInputBoundaryTests(unittest.TestCase):
    def test_duplicate_config_keys_are_rejected_independently_of_order(self):
        values = (b"cdrom0:\\SLUS_123.45;1", b"cdrom0:\\MISSING.ELF;1")
        for first, second in ((values[0], values[1]), (values[1], values[0]), (values[0], values[0])):
            with self.subTest(first=first, second=second):
                config = b"BOOT2 = " + first + b"\nboot2 = " + second + b"\n"
                with self.assertRaises(inspector.InspectError) as ctx:
                    inspector.inspect_bytes(bytes(_iso(config=config)))
                self.assertEqual(ctx.exception.code, "SYSTEM_CNF_DUPLICATE_KEY")

    def test_embedded_nuls_and_non_ascii_config_are_not_silently_repaired(self):
        for config, code in (
            (b"BO\x00OT2 = cdrom0:\\SLUS_123.45;1\n", "SYSTEM_CNF_ENCODING_INVALID"),
            (b"BOOT2 = cdrom0:\\SLUS_123.\x0045;1\n", "SYSTEM_CNF_ENCODING_INVALID"),
            (b"BOOT2 = cdrom0:\\SLUS_123.45;1\nVER = \xff\n", "SYSTEM_CNF_ENCODING_INVALID"),
        ):
            with self.subTest(config=config):
                with self.assertRaises(inspector.InspectError) as ctx:
                    inspector.inspect_bytes(bytes(_iso(config=config)))
                self.assertEqual(ctx.exception.code, code)

    def test_supports_terminal_nul_padding_and_balanced_boot_quotes(self):
        for quote in (b"", b"'", b'"'):
            config = b"BOOT2 = " + quote + b"cdrom0:\\SLUS_123.45;1" + quote + b"\n\x00\x00"
            with self.subTest(quote=quote):
                report = inspector.inspect_bytes(bytes(_iso(config=config)))
                self.assertEqual(report["status"], "INSPECTED")
                self.assertEqual(report["boot_executable"]["path"], "SLUS_123.45;1")

    def test_rejects_unbalanced_or_embedded_boot_quotes(self):
        for value in (b'"cdrom0:\\SLUS_123.45;1', b"cdrom0:\\SLUS_123.45;1'",
                      b"'cdrom0:\\SLUS_123.45;1\"", b'cdrom0:\\SLUS_123."45;1'):
            with self.subTest(value=value):
                with self.assertRaises(inspector.InspectError) as ctx:
                    inspector.inspect_bytes(bytes(_iso(config=b"BOOT2 = " + value + b"\n")))
                self.assertEqual(ctx.exception.code, "BOOT_PATH_INVALID")

    def test_boot2_still_takes_precedence_over_distinct_legacy_boot(self):
        config = DEFAULT_CONFIG + b"BOOT = cdrom0:\\MISSING.ELF;1\n"
        report = inspector.inspect_bytes(bytes(_iso(config=config)))
        self.assertEqual(report["system_cnf"]["boot_key"], "BOOT2")

    def test_special_directory_records_count_toward_safety_limits(self):
        data = bytes(_iso())
        for method, constant, code in (("list_dir", "MAX_DIRECTORY_ENTRIES", "DIRECTORY_ENTRY_LIMIT"),
                                       ("survey", "MAX_SURVEY_RECORDS", "SURVEY_RECORD_LIMIT")):
            with self.subTest(method=method):
                stream = RecordingStream(data)
                reader = inspector.IsoReader(stream, len(data), "special.iso")
                reader.parse_pvd(reader.scan_pvd())
                stream.read_sizes.clear()
                stream.read_offsets.clear()
                with mock.patch.object(inspector, constant, 1):
                    with self.assertRaises(inspector.InspectError) as ctx:
                        if method == "list_dir":
                            reader.list_dir(reader.root)
                        else:
                            reader.survey()
                self.assertEqual(ctx.exception.code, code)
                directory_reads = [offset for offset in stream.read_offsets if offset >= 19 * BLOCK]
                self.assertLessEqual(len(directory_reads), 4)

    def test_directory_byte_limits_include_zero_padding(self):
        data = bytes(_iso(tree=True))
        reader = inspector.IsoReader(BytesIO(data), len(data), "padding.iso")
        reader.parse_pvd(reader.scan_pvd())
        with mock.patch.object(inspector, "MAX_DIRECTORY_BYTES", BLOCK):
            self.assertEqual(len(reader.list_dir(reader.root)), 3)
        with mock.patch.object(inspector, "MAX_DIRECTORY_BYTES", BLOCK - 1):
            with self.assertRaises(inspector.InspectError) as ctx:
                reader.list_dir(reader.root)
            self.assertEqual(ctx.exception.code, "DIRECTORY_SIZE_LIMIT")
        with mock.patch.object(inspector, "MAX_SURVEY_BYTES", 3 * BLOCK):
            self.assertEqual(reader.survey()["directory_count"], 3)
        with mock.patch.object(inspector, "MAX_SURVEY_BYTES", 3 * BLOCK - 1):
            with self.assertRaises(inspector.InspectError) as ctx:
                reader.survey()
            self.assertEqual(ctx.exception.code, "SURVEY_BYTE_LIMIT")

    def test_read_range_validates_negative_and_empty_bounds(self):
        reader = inspector.IsoReader(BytesIO(b"abc"), 3, "bounds.iso")
        for start, size in ((0, -1), (-1, 0), (4, 0)):
            with self.subTest(start=start, size=size):
                with self.assertRaises(inspector.InspectError) as ctx:
                    reader.read_range(start, size)
                self.assertEqual(ctx.exception.code, "IMAGE_BOUNDS")
        self.assertEqual(reader.read_range(3, 0), b"")

    def test_large_boot_executable_is_streamed_without_materialization(self):
        executable = _elf(data_size=inspector.MAX_READ_BYTES + BLOCK)
        image = _iso(executable=executable)
        end = 21 * BLOCK + len(executable)
        volume_size = ((end + BLOCK - 1) // BLOCK) * BLOCK
        image.extend(bytes(volume_size - len(image)))
        image[21 * BLOCK:end] = executable
        image[16 * BLOCK + 80:16 * BLOCK + 88] = _both32(volume_size // BLOCK)
        stream = RecordingStream(bytes(image))
        report = inspector.inspect_stream(stream, len(image), chunk_size=64 * 1024)
        self.assertEqual(report["status"], "INSPECTED")
        self.assertEqual(report["boot_executable"]["sha256"], hashlib.sha256(executable).hexdigest())
        self.assertLessEqual(max(stream.read_sizes), 64 * 1024)
        reader = inspector.IsoReader(stream, len(image), "large.iso")
        with self.assertRaises(inspector.InspectError) as ctx:
            reader.read_range(21 * BLOCK, len(executable))
        self.assertEqual(ctx.exception.code, "FILE_SIZE_LIMIT")


class IsoFormatContractTests(unittest.TestCase):
    @staticmethod
    def descriptor(kind: int, version: int = 1) -> bytes:
        data = bytearray(BLOCK)
        data[0], data[1:6], data[6] = kind, b"CD001", version
        return bytes(data)

    @staticmethod
    def descriptor_image(*descriptors: bytes) -> bytes:
        image = _iso()
        for index, descriptor in enumerate(descriptors):
            image[(16 + index) * BLOCK:(17 + index) * BLOCK] = descriptor
        return bytes(image)

    def test_reports_actual_primary_descriptor_lba_after_boot_record(self):
        pvd = bytes(_iso()[16 * BLOCK:17 * BLOCK])
        data = self.descriptor_image(self.descriptor(0), pvd, self.descriptor(255))
        report = inspector.inspect_bytes(data)
        self.assertEqual(report["iso9660"]["primary_volume_descriptor_lba"], 17)
        self.assertEqual(report["iso9660"]["volume_descriptors"], [
            {"lba": 16, "type": 0, "version": 1},
            {"lba": 17, "type": 1, "version": 1},
            {"lba": 18, "type": 255, "version": 1},
        ])
        self.assertEqual(report["status"], "INSPECTED_WITH_WARNINGS")
        self.assertTrue(any("type 0 at block 16" in warning for warning in report["warnings"]))
        self.assertEqual(report["boot_executable"]["sha256"], hashlib.sha256(_elf()).hexdigest())

    def test_auxiliary_namespaces_are_reported_but_never_followed(self):
        pvd = bytes(_iso()[16 * BLOCK:17 * BLOCK])
        for kind, version in ((2, 1), (2, 2), (3, 1)):
            with self.subTest(kind=kind, version=version):
                auxiliary = bytearray(self.descriptor(kind, version))
                auxiliary[156:190] = _record(0xFFFFFFFF, BLOCK, b"\x00", 0x02)
                data = self.descriptor_image(pvd, bytes(auxiliary), self.descriptor(255))
                report = inspector.inspect_bytes(data)
                self.assertEqual(report["status"], "INSPECTED_WITH_WARNINGS")
                self.assertEqual(report["iso9660"]["volume_descriptors"][1],
                                 {"lba": 17, "type": kind, "version": version})
                self.assertEqual(report["boot_executable"]["sha256"], hashlib.sha256(_elf()).hexdigest())
                survey = inspector.IsoReader(BytesIO(data), len(data), "auxiliary.iso").survey()
                self.assertEqual(survey["status"], "SURVEYED_WITH_WARNINGS")
                self.assertEqual(survey["volume_descriptors"], report["iso9660"]["volume_descriptors"])
                self.assertEqual(survey["warnings"], report["warnings"])
                self.assertEqual(survey["directory_count"], 1)

    def test_rejects_reserved_descriptor_types(self):
        pvd = bytes(_iso()[16 * BLOCK:17 * BLOCK])
        for kind in (4, 254):
            data = self.descriptor_image(pvd, self.descriptor(kind), self.descriptor(255))
            for method in ("inspect", "survey"):
                with self.subTest(kind=kind, method=method):
                    reader = inspector.IsoReader(BytesIO(data), len(data), "reserved.iso")
                    with self.assertRaises(inspector.InspectError) as ctx:
                        getattr(reader, method)()
                    self.assertEqual(ctx.exception.code, "UNSUPPORTED_VOLUME_DESCRIPTOR_TYPE")

    def test_rejects_invalid_versions_for_each_descriptor_type(self):
        pvd = bytes(_iso()[16 * BLOCK:17 * BLOCK])
        for kind, version in ((0, 2), (1, 2), (2, 0), (2, 3), (3, 2), (255, 2)):
            with self.subTest(kind=kind, version=version):
                data = self.descriptor_image(pvd, self.descriptor(kind, version), self.descriptor(255))
                with self.assertRaises(inspector.InspectError) as ctx:
                    inspector.inspect_bytes(data)
                self.assertEqual(ctx.exception.code, "VOLUME_DESCRIPTOR_VERSION")

    def test_accepts_identical_repeated_primary_descriptors(self):
        pvd = bytes(_iso()[16 * BLOCK:17 * BLOCK])
        data = self.descriptor_image(pvd, pvd, self.descriptor(255))
        report = inspector.inspect_bytes(data)
        self.assertEqual(report["status"], "INSPECTED")
        self.assertEqual(report["iso9660"]["primary_volume_descriptor_lba"], 16)
        self.assertEqual(len(report["iso9660"]["volume_descriptors"]), 3)

    def test_rejects_conflicting_primary_descriptor_copies(self):
        pvd = bytes(_iso()[16 * BLOCK:17 * BLOCK])
        conflicting = bytearray(pvd)
        conflicting[40] = ord("X")
        data = self.descriptor_image(pvd, bytes(conflicting), self.descriptor(255))
        with self.assertRaises(inspector.InspectError) as ctx:
            inspector.inspect_bytes(data)
        self.assertEqual(ctx.exception.code, "PRIMARY_VOLUME_DESCRIPTOR_CONFLICT")

    def test_rejects_unsupported_primary_file_structure_version(self):
        for version in (0, 2, 255):
            with self.subTest(version=version):
                image = _iso()
                image[16 * BLOCK + 881] = version
                with self.assertRaises(inspector.InspectError) as ctx:
                    inspector.inspect_bytes(bytes(image))
                self.assertEqual(ctx.exception.code, "UNSUPPORTED_FILE_STRUCTURE_VERSION")

    def test_descriptor_reads_stop_at_declared_volume_boundary(self):
        image = _iso()
        image[16 * BLOCK + 80:16 * BLOCK + 88] = _both32(17)
        stream = RecordingStream(bytes(image))
        with self.assertRaises(inspector.InspectError) as ctx:
            inspector.inspect_stream(stream, len(image))
        self.assertEqual(ctx.exception.code, "VOLUME_DESCRIPTOR_OUT_OF_BOUNDS")
        self.assertEqual(stream.read_offsets, [16 * BLOCK])
        self.assertEqual(stream.read_sizes, [BLOCK])

    def test_rejects_primary_descriptor_outside_its_declared_volume(self):
        pvd = bytearray(_iso()[16 * BLOCK:17 * BLOCK])
        pvd[80:88] = _both32(17)
        data = self.descriptor_image(self.descriptor(0), bytes(pvd), self.descriptor(255))
        with self.assertRaises(inspector.InspectError) as ctx:
            inspector.inspect_bytes(data)
        self.assertEqual(ctx.exception.code, "VOLUME_DESCRIPTOR_OUT_OF_BOUNDS")

    def test_descriptor_scan_limit_includes_terminator_at_exact_boundary(self):
        pvd = bytes(_iso()[16 * BLOCK:17 * BLOCK])
        data = self.descriptor_image(pvd, self.descriptor(0), self.descriptor(255))
        with mock.patch.object(inspector, "MAX_DESCRIPTORS", 3):
            self.assertEqual(inspector.inspect_bytes(data)["status"], "INSPECTED_WITH_WARNINGS")
        stream = RecordingStream(data)
        with mock.patch.object(inspector, "MAX_DESCRIPTORS", 2):
            with self.assertRaises(inspector.InspectError) as ctx:
                inspector.inspect_stream(stream, len(data))
        self.assertEqual(ctx.exception.code, "VOLUME_DESCRIPTOR_TERMINATOR_MISSING")
        self.assertEqual(stream.read_offsets, [16 * BLOCK, 17 * BLOCK])

    def test_multi_extent_chains_are_rejected_before_ambiguous_lookup(self):
        for target in ("SYSTEM.CNF", "SLUS_123.45", "ASSET.BIN"):
            with self.subTest(target=target):
                config = DEFAULT_CONFIG
                records = [
                    _record(19, BLOCK, b"\x00", 0x02),
                    _record(19, BLOCK, b"\x01", 0x02),
                    _record(20, len(config), b"SYSTEM.CNF;1", 0x80 if target == "SYSTEM.CNF" else 0),
                    _record(21, len(_elf()), b"SLUS_123.45;1", 0x80 if target == "SLUS_123.45" else 0),
                ]
                if target == "ASSET.BIN":
                    records.append(_record(23, BLOCK, b"ASSET.BIN;1", 0x80))
                records.append(_record(24, 1, target.encode("ascii") + b";1"))
                image = _iso()
                directory = b"".join(records)
                image[19 * BLOCK:20 * BLOCK] = directory.ljust(BLOCK, b"\x00")
                data = bytes(image)
                with self.assertRaises(inspector.InspectError) as ctx:
                    inspector.inspect_bytes(data)
                self.assertEqual(ctx.exception.code, "MULTI_EXTENT_UNSUPPORTED")
                survey = inspector.IsoReader(BytesIO(data), len(data), "sections.iso").survey()
                self.assertEqual(survey["multi_extent_records"], 1)
                self.assertEqual(survey["file_count"], len(records) - 2)

    def test_rejects_nonzero_identifier_padding(self):
        record = bytearray(_record(20, len(DEFAULT_CONFIG), b"SYSTEM.CNF;1"))
        self.assertEqual(len(b"SYSTEM.CNF;1") % 2, 0)
        record[-1] = 1
        image = _iso()
        offset = 19 * BLOCK + 68
        image[offset:offset + len(record)] = record
        with self.assertRaises(inspector.InspectError) as ctx:
            inspector.inspect_bytes(bytes(image))
        self.assertEqual(ctx.exception.code, "DIRECTORY_PADDING_INVALID")

    def test_rejects_nonstandard_root_record_length(self):
        image = _iso()
        image[16 * BLOCK + 156] = 36
        with self.assertRaises(inspector.InspectError) as ctx:
            inspector.inspect_bytes(bytes(image))
        self.assertEqual(ctx.exception.code, "ROOT_RECORD_INVALID")

    def test_rejects_reserved_directory_flags_in_inspection_and_survey(self):
        for flag in (0x20, 0x40):
            data = bytes(_iso(boot_flags=flag))
            for method in ("inspect", "survey"):
                with self.subTest(flag=flag, method=method):
                    reader = inspector.IsoReader(BytesIO(data), len(data), "flags.iso")
                    with self.assertRaises(inspector.InspectError) as ctx:
                        getattr(reader, method)()
                    self.assertEqual(ctx.exception.code, "DIRECTORY_FLAGS_INVALID")

    def test_rejects_associated_and_record_formatted_files(self):
        for flag, code in ((0x04, "ASSOCIATED_FILE_UNSUPPORTED"), (0x08, "RECORD_FORMAT_UNSUPPORTED")):
            for target in ("system_flags", "boot_flags"):
                with self.subTest(flag=flag, target=target):
                    data = bytes(_iso(**{target: flag}))
                    with self.assertRaises(inspector.InspectError) as ctx:
                        inspector.inspect_bytes(data)
                    self.assertEqual(ctx.exception.code, code)
                    survey = inspector.IsoReader(BytesIO(data), len(data), "opaque.iso").survey()
                    self.assertEqual(survey["file_count"], 2)

    def test_opaque_system_use_bytes_do_not_replace_primary_names(self):
        image = _iso()
        record = bytearray(_record(21, len(_elf()), b"SLUS_123.45;1"))
        record.extend(b"OPAQUE SYSTEM USE")
        record[0] = len(record)
        offset = 19 * BLOCK + 68 + len(_record(20, len(DEFAULT_CONFIG), b"SYSTEM.CNF;1"))
        image[offset:offset + len(record)] = record
        data = bytes(image)
        report = inspector.inspect_bytes(data)
        self.assertEqual(report["boot_executable"]["path"], "SLUS_123.45;1")
        self.assertEqual(report["boot_executable"]["sha256"], hashlib.sha256(_elf()).hexdigest())
        self.assertIn("system-use", " ".join(report["limitations"]))

    def test_format_contract_cli_is_deterministic_and_read_only(self):
        pvd = bytes(_iso()[16 * BLOCK:17 * BLOCK])
        invalid_padding = _iso()
        invalid_padding[19 * BLOCK + 512] = 1
        invalid_identifier = _iso()
        invalid_identifier[19 * BLOCK + 68 + 33] = 0xFF
        cases = (
            (self.descriptor_image(pvd, self.descriptor(2, 2), self.descriptor(255)),
             0, "INSPECTED_WITH_WARNINGS", "SURVEYED_WITH_WARNINGS", None),
            (bytes(_iso(boot_flags=0x80)), 2, "ERROR", "SURVEYED", "MULTI_EXTENT_UNSUPPORTED"),
            (self.descriptor_image(pvd, self.descriptor(254), self.descriptor(255)),
             2, "ERROR", "ERROR", "UNSUPPORTED_VOLUME_DESCRIPTOR_TYPE"),
            (bytes(invalid_padding), 2, "ERROR", "ERROR", "DIRECTORY_PADDING_INVALID"),
            (bytes(invalid_identifier), 2, "ERROR", "ERROR", "DIRECTORY_IDENTIFIER_INVALID"),
            (bytes(_iso(config=b"BOOT2 = cdrom0:\\SLUS_123.45;2\n")),
             2, "ERROR", "SURVEYED", "BOOT_EXECUTABLE_NOT_FOUND"),
            (bytes(_iso(executable=_elf(load_align=0x1000))),
             2, "ERROR", "SURVEYED", "ELF_LOAD_SEGMENT_ALIGNMENT_INVALID"),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contract.iso"
            for data, code, inspect_status, survey_status, error_code in cases:
                path.write_bytes(data)
                for survey in (False, True):
                    with self.subTest(code=code, survey=survey):
                        expected_status = survey_status if survey else inspect_status
                        expected_code = 0 if expected_status != "ERROR" else code
                        command = [sys.executable, str(ROOT / "tools/rptp_inspect.py"), str(path), "--json"]
                        if survey:
                            command.append("--survey")
                        outputs = []
                        for _ in range(2):
                            result = subprocess.run(command, capture_output=True, text=True, check=False)
                            self.assertEqual(result.returncode, expected_code, result.stderr)
                            self.assertEqual(result.stderr, "")
                            payload = json.loads(result.stdout)
                            self.assertEqual(payload["status"], expected_status)
                            if expected_status == "ERROR":
                                self.assertEqual(payload["error_code"], error_code)
                            outputs.append(result.stdout)
                            self.assertEqual(path.read_bytes(), data)
                            self.assertEqual(list(Path(directory).iterdir()), [path])
                        self.assertEqual(outputs[0], outputs[1])


class IsoReviewRegressionTests(unittest.TestCase):
    def test_rejects_nonzero_directory_sector_tail_in_both_modes(self):
        for payload in (b"\x01", _record(23, 1, b"HIDDEN.BIN;1", 0x80)):
            image = _iso()
            image[19 * BLOCK + 512:19 * BLOCK + 512 + len(payload)] = payload
            data = bytes(image)
            for method in ("inspect", "survey"):
                with self.subTest(payload=payload, method=method):
                    reader = inspector.IsoReader(BytesIO(data), len(data), "tail.iso")
                    with self.assertRaises(inspector.InspectError) as ctx:
                        getattr(reader, method)()
                    self.assertEqual(ctx.exception.code, "DIRECTORY_PADDING_INVALID")

    def test_accepts_zero_padding_before_next_directory_sector(self):
        image = _iso()
        root = _record(26, 2 * BLOCK, b"\x00", 0x02)
        image[16 * BLOCK + 156:16 * BLOCK + 190] = root
        first = root + _record(26, 2 * BLOCK, b"\x01", 0x02)
        second = (_record(20, len(DEFAULT_CONFIG), b"SYSTEM.CNF;1")
                  + _record(21, len(_elf()), b"SLUS_123.45;1"))
        image[26 * BLOCK:27 * BLOCK] = first.ljust(BLOCK, b"\x00")
        image[27 * BLOCK:28 * BLOCK] = second.ljust(BLOCK, b"\x00")
        data = bytes(image)
        self.assertEqual(inspector.inspect_bytes(data)["status"], "INSPECTED")
        self.assertEqual(inspector.IsoReader(BytesIO(data), len(data), "padding.iso").survey()["file_count"], 2)

    def test_rejects_non_printable_primary_identifiers_in_both_modes(self):
        for name in (b"SYSTEM.CNF;1\x00", b"SYSTEM.CNF;1\xff", b"SYSTEM.CNF;1\t"):
            image = _iso(config=None)
            records = (_record(19, BLOCK, b"\x00", 0x02) + _record(19, BLOCK, b"\x01", 0x02)
                       + _record(20, len(DEFAULT_CONFIG), name) + _record(21, len(_elf()), b"SLUS_123.45;1"))
            image[19 * BLOCK:20 * BLOCK] = records.ljust(BLOCK, b"\x00")
            image[20 * BLOCK:20 * BLOCK + len(DEFAULT_CONFIG)] = DEFAULT_CONFIG
            data = bytes(image)
            for method in ("inspect", "survey"):
                with self.subTest(name=name, method=method):
                    reader = inspector.IsoReader(BytesIO(data), len(data), "identifier.iso")
                    with self.assertRaises(inspector.InspectError) as ctx:
                        getattr(reader, method)()
                    self.assertEqual(ctx.exception.code, "DIRECTORY_IDENTIFIER_INVALID")

    def test_special_identifiers_require_directory_flag(self):
        for name in (b"\x00", b"\x01"):
            image = _iso()
            record = _record(19, BLOCK, name)
            image[19 * BLOCK:19 * BLOCK + len(record)] = record
            data = bytes(image)
            for method in ("inspect", "survey"):
                with self.subTest(name=name, method=method):
                    reader = inspector.IsoReader(BytesIO(data), len(data), "special.iso")
                    with self.assertRaises(inspector.InspectError) as ctx:
                        getattr(reader, method)()
                    self.assertEqual(ctx.exception.code, "DIRECTORY_IDENTIFIER_INVALID")

    def test_explicit_boot_version_does_not_select_another_version(self):
        for version in (b"2", b"1extra", b"1;2"):
            with self.subTest(version=version):
                config = b"BOOT2 = cdrom0:\\SLUS_123.45;" + version + b"\n"
                with self.assertRaises(inspector.InspectError) as ctx:
                    inspector.inspect_bytes(bytes(_iso(config=config)))
                self.assertEqual(ctx.exception.code, "BOOT_EXECUTABLE_NOT_FOUND")

    def test_coexisting_boot_versions_are_resolved_exactly(self):
        first, second = _elf(), _elf(machine=3)
        for version, expected in ((b"1", first), (b"2", second)):
            with self.subTest(version=version):
                config = b"BOOT2 = cdrom0:\\slus_123.45;" + version + b"\n"
                image = _iso(config=config, executable=first)
                records = (_record(19, BLOCK, b"\x00", 0x02) + _record(19, BLOCK, b"\x01", 0x02)
                           + _record(20, len(config), b"SYSTEM.CNF;1")
                           + _record(21, len(first), b"SLUS_123.45;1")
                           + _record(23, len(second), b"SLUS_123.45;2"))
                image[19 * BLOCK:20 * BLOCK] = records.ljust(BLOCK, b"\x00")
                image[23 * BLOCK:23 * BLOCK + len(second)] = second
                report = inspector.inspect_bytes(bytes(image))
                self.assertEqual(report["boot_executable"]["path"], "SLUS_123.45;" + version.decode("ascii"))
                self.assertEqual(report["boot_executable"]["sha256"], hashlib.sha256(expected).hexdigest())
                unversioned = b"BOOT2 = cdrom0:\\SLUS_123.45\n"
                image[20 * BLOCK:20 * BLOCK + len(config)] = unversioned.ljust(len(config), b"\x00")
                with self.assertRaises(inspector.InspectError) as ctx:
                    inspector.inspect_bytes(bytes(image))
                self.assertEqual(ctx.exception.code, "AMBIGUOUS_PATH")
        report = inspector.inspect_bytes(bytes(_iso(config=b"BOOT2 = cdrom0:\\SLUS_123.45\n")))
        self.assertEqual(report["boot_executable"]["path"], "SLUS_123.45;1")

    def test_survey_directory_budget_is_enforced_while_scheduling(self):
        image = _iso()
        records = [_record(19, BLOCK, b"\x00", 0x02), _record(19, BLOCK, b"\x01", 0x02)]
        records.extend(_record(lba, BLOCK, f"D{lba}".encode("ascii"), 0x02) for lba in (22, 23, 24, 25))
        image[19 * BLOCK:20 * BLOCK] = b"".join(records).ljust(BLOCK, b"\x00")
        stream = RecordingStream(bytes(image))
        with mock.patch.object(inspector, "MAX_SURVEY_DIRECTORIES", 3):
            with self.assertRaises(inspector.InspectError) as ctx:
                inspector.IsoReader(stream, len(image), "wide.iso").survey()
        self.assertEqual(ctx.exception.code, "SURVEY_DIRECTORY_LIMIT")
        self.assertLess(max(stream.read_offsets), 19 * BLOCK + sum(map(len, records[:5])))

    def test_survey_deduplicates_aliases_and_cycles(self):
        image = _iso()
        records = [_record(19, BLOCK, b"\x00", 0x02), _record(19, BLOCK, b"\x01", 0x02)]
        records.extend(_record(22, BLOCK, f"ALIAS{index}".encode("ascii"), 0x02) for index in range(30))
        image[19 * BLOCK:20 * BLOCK] = b"".join(records).ljust(BLOCK, b"\x00")
        child = (_record(22, BLOCK, b"\x00", 0x02) + _record(19, BLOCK, b"\x01", 0x02)
                 + _record(19, BLOCK, b"ROOT", 0x02))
        image[22 * BLOCK:23 * BLOCK] = child.ljust(BLOCK, b"\x00")
        with mock.patch.object(inspector, "MAX_SURVEY_DIRECTORIES", 2):
            report = inspector.IsoReader(BytesIO(bytes(image)), len(image), "aliases.iso").survey()
        self.assertEqual(report["directory_count"], 2)
        self.assertEqual(report["directory_record_count"], 31)
        self.assertEqual(report["max_depth"], 1)

    def test_rejects_incongruent_elf_load_alignment(self):
        executable = _elf(load_align=0x1000, load_offset=84, load_vaddr=0x00100000)
        with self.assertRaises(inspector.InspectError) as ctx:
            inspector.inspect_bytes(bytes(_iso(executable=executable)))
        self.assertEqual(ctx.exception.code, "ELF_LOAD_SEGMENT_ALIGNMENT_INVALID")

    def test_accepts_elf_load_alignment_boundaries(self):
        for alignment, address in ((0, 0x00100000), (1, 0x00100000), (4, 0x00100000), (0x1000, 0x00100054)):
            with self.subTest(alignment=alignment):
                executable = _elf(load_align=alignment, load_vaddr=address, entry_point=address)
                report = inspector.inspect_bytes(bytes(_iso(executable=executable)))
                self.assertEqual(report["status"], "INSPECTED")
                self.assertEqual(report["boot_executable"]["elf"]["load_segments"][0]["alignment"], alignment)


class ElfLoadMapTests(unittest.TestCase):
    @staticmethod
    def executable(headers: list[tuple[int, int, int, int, int, int]], entry: int = 0x1000) -> bytes:
        data = bytearray(_elf(phnum=len(headers), entry_point=entry, data_size=256))
        for index, (kind, offset, address, file_size, memory_size, flags) in enumerate(headers):
            values = (kind, offset, address, address, file_size, memory_size, flags, 1)
            start = 52 + index * 32
            data[start:start + 32] = b"".join(value.to_bytes(4, "little") for value in values)
        return bytes(data)

    def test_rejects_virtual_range_overflow_for_any_load_segment(self):
        for flags in (0, 5, 6):
            for memory_size in (0x11, 0x100):
                with self.subTest(flags=flags, memory_size=memory_size):
                    executable = self.executable([(1, 192, 0xFFFFFFF0, 8, memory_size, flags)], 0xFFFFFFF0)
                    with self.assertRaises(inspector.InspectError) as ctx:
                        inspector.inspect_bytes(bytes(_iso(executable=executable)))
                    self.assertEqual(ctx.exception.code, "ELF_LOAD_SEGMENT_ADDRESS_INVALID")

    def test_accepts_exact_elf32_end_and_empty_ranges(self):
        for address, file_size, memory_size, entry in (
            (0xFFFFFFF0, 8, 0x10, 0xFFFFFFF0),
            (0xFFFFFFFF, 1, 1, 0xFFFFFFFF),
            (0xFFFFFFFF, 0, 0, 0xFFFFFFFF),
            (0, 0, 0, 0),
        ):
            with self.subTest(address=address, memory_size=memory_size):
                executable = self.executable([(1, 192, address, file_size, memory_size, 5)], entry)
                report = inspector.inspect_bytes(bytes(_iso(executable=executable)))
                segment = report["boot_executable"]["elf"]["load_segments"][0]
                self.assertEqual(segment["virtual_memory_end"], address + memory_size)
                self.assertEqual(segment["virtual_file_end"], address + file_size)
                self.assertEqual(segment["zero_fill_size"], memory_size - file_size)
                self.assertEqual(len(report["boot_executable"]["elf"]["entry_point_mappings"]), bool(memory_size))

    def test_rejects_decreasing_load_addresses_without_sorting_input(self):
        executable = self.executable([
            (1, 192, 0x2000, 8, 16, 5),
            (4, 0, 0, 0, 0, 0),
            (1, 200, 0x1000, 8, 16, 6),
        ], 0x2000)
        with self.assertRaises(inspector.InspectError) as ctx:
            inspector.inspect_bytes(bytes(_iso(executable=executable)))
        self.assertEqual(ctx.exception.code, "ELF_LOAD_SEGMENT_ORDER_INVALID")

    def test_reports_original_header_indexes_and_distinct_memory_ranges(self):
        executable = self.executable([
            (4, 0, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0),
            (1, 192, 0x1000, 8, 16, 5),
            (1, 200, 0x2000, 4, 32, 6),
        ], 0x1004)
        report = inspector.inspect_bytes(bytes(_iso(executable=executable)))
        elf = report["boot_executable"]["elf"]
        self.assertEqual(report["status"], "INSPECTED")
        self.assertEqual([segment["program_header_index"] for segment in elf["load_segments"]], [1, 2])
        self.assertEqual([segment["virtual_file_end"] for segment in elf["load_segments"]], [0x1008, 0x2004])
        self.assertEqual([segment["virtual_memory_end"] for segment in elf["load_segments"]], [0x1010, 0x2020])
        self.assertEqual([segment["zero_fill_size"] for segment in elf["load_segments"]], [8, 28])
        self.assertEqual(elf["entry_point_mappings"], [
            {"program_header_index": 1, "file_offset": 196, "executable": True, "file_backed": True},
        ])
        self.assertFalse(elf["load_segments_overlap"])

    def test_entry_mapping_uses_half_open_file_and_memory_ranges(self):
        for entry, file_backed, expected_offset in ((0x1000, True, 192), (0x1007, True, 199),
                                                    (0x1008, False, None), (0x100F, False, None)):
            with self.subTest(entry=entry):
                executable = self.executable([(1, 192, 0x1000, 8, 16, 5)], entry)
                report = inspector.inspect_bytes(bytes(_iso(executable=executable)))
                elf = report["boot_executable"]["elf"]
                self.assertEqual(elf["entry_point_mappings"], [
                    {"program_header_index": 0, "file_offset": expected_offset,
                     "executable": True, "file_backed": file_backed},
                ])
                self.assertEqual(report["status"], "INSPECTED" if file_backed else "INSPECTED_WITH_WARNINGS")
                self.assertEqual(any("not in file-backed executable" in warning for warning in report["warnings"]),
                                 not file_backed)
        executable = self.executable([(1, 192, 0x1000, 8, 16, 5)], 0x1010)
        report = inspector.inspect_bytes(bytes(_iso(executable=executable)))
        self.assertEqual(report["boot_executable"]["elf"]["entry_point_mappings"], [])
        self.assertTrue(any("outside all PT_LOAD" in warning for warning in report["warnings"]))

    def test_warns_for_file_backed_entry_without_execute_permission(self):
        executable = self.executable([(1, 192, 0x1000, 8, 16, 6)])
        report = inspector.inspect_bytes(bytes(_iso(executable=executable)))
        self.assertEqual(report["boot_executable"]["elf"]["entry_point_mappings"], [
            {"program_header_index": 0, "file_offset": 192, "executable": False, "file_backed": True},
        ])
        self.assertEqual(report["status"], "INSPECTED_WITH_WARNINGS")
        self.assertTrue(any("not in file-backed executable" in warning for warning in report["warnings"]))

    def test_warns_for_memory_only_entry_without_reading_or_allocating_memory(self):
        executable = self.executable([(1, 256, 0x100, 0, 0xFFFFFF00, 5)], 0x100)
        data = bytes(_iso(executable=executable))
        stream = RecordingStream(data)
        reader = inspector.IsoReader(stream, len(data), "memory-only.iso")
        reader.parse_pvd(reader.scan_pvd())
        boot = reader.find_child(reader.root, "SLUS_123.45;1")
        stream.read_sizes.clear()
        stream.read_offsets.clear()
        elf = reader.parse_elf(boot)
        self.assertEqual(elf["load_segments"][0]["virtual_memory_end"], 0x100000000)
        self.assertEqual(elf["load_segments"][0]["zero_fill_size"], 0xFFFFFF00)
        self.assertEqual(stream.read_sizes, [64, 32])
        self.assertEqual(stream.read_offsets, [21 * BLOCK, 21 * BLOCK + 52])
        self.assertEqual(elf["entry_point_mappings"][0]["file_offset"], None)
        report = inspector.inspect_bytes(data)
        self.assertEqual(report["status"], "INSPECTED_WITH_WARNINGS")

    def test_reports_overlap_without_selecting_a_loading_precedence(self):
        executable = self.executable([
            (1, 192, 0x1000, 16, 32, 5),
            (1, 208, 0x1008, 8, 16, 6),
        ], 0x100C)
        report = inspector.inspect_bytes(bytes(_iso(executable=executable)))
        elf = report["boot_executable"]["elf"]
        self.assertTrue(elf["load_segments_overlap"])
        self.assertEqual(elf["entry_point_mappings"], [
            {"program_header_index": 0, "file_offset": 204, "executable": True, "file_backed": True},
            {"program_header_index": 1, "file_offset": 212, "executable": False, "file_backed": True},
        ])
        self.assertTrue(any("memory ranges overlap" in warning for warning in report["warnings"]))
        self.assertTrue(any("maps to multiple" in warning for warning in report["warnings"]))

    def test_overlap_sweep_handles_nested_and_empty_segments(self):
        for headers, overlaps in (
            ([(1, 192, 0x1000, 0, 0x100, 5), (1, 192, 0x1010, 0, 0, 5),
              (1, 192, 0x1020, 0, 8, 5)], True),
            ([(1, 192, 0x1000, 0, 0, 5), (1, 192, 0x1000, 0, 16, 5)], False),
            ([(1, 192, 0x1000, 8, 32, 5), (1, 200, 0x1008, 0, 0, 5)], False),
            ([(1, 192, 0x1000, 8, 16, 5), (1, 200, 0x1010, 8, 16, 5)], False),
            ([(1, 192, 0x1000, 8, 16, 5), (1, 200, 0x1000, 8, 16, 5)], True),
        ):
            with self.subTest(headers=headers):
                report = inspector.inspect_bytes(bytes(_iso(executable=self.executable(headers))))
                self.assertEqual(report["boot_executable"]["elf"]["load_segments_overlap"], overlaps)

    def test_no_load_segments_have_no_entry_mappings(self):
        report = inspector.inspect_bytes(bytes(_iso(executable=self.executable([]))))
        elf = report["boot_executable"]["elf"]
        self.assertEqual(elf["entry_point_mappings"], [])
        self.assertFalse(elf["load_segments_overlap"])

    def test_entry_permissions_and_file_backing_are_not_combined_across_mappings(self):
        executable = self.executable([
            (1, 192, 0x1000, 8, 32, 5), (1, 200, 0x1008, 8, 16, 6),
        ], 0x100C)
        report = inspector.inspect_bytes(bytes(_iso(executable=executable)))
        self.assertEqual(report["boot_executable"]["elf"]["entry_point_mappings"], [
            {"program_header_index": 0, "file_offset": None, "executable": True, "file_backed": False},
            {"program_header_index": 1, "file_offset": 204, "executable": False, "file_backed": True},
        ])
        self.assertTrue(any("not in file-backed executable" in warning for warning in report["warnings"]))

    def test_load_map_cli_success_warnings_and_errors_are_read_only(self):
        cases = (
            (self.executable([(1, 192, 0x1000, 8, 16, 5)]), 0, "INSPECTED", None),
            (self.executable([(1, 192, 0x1000, 8, 16, 6)]), 0, "INSPECTED_WITH_WARNINGS", None),
            (self.executable([(1, 192, 0xFFFFFFF0, 8, 0x100, 5)], 0xFFFFFFF0),
             2, "ERROR", "ELF_LOAD_SEGMENT_ADDRESS_INVALID"),
            (self.executable([(1, 192, 0x2000, 8, 16, 5), (1, 200, 0x1000, 8, 16, 6)], 0x2000),
             2, "ERROR", "ELF_LOAD_SEGMENT_ORDER_INVALID"),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "load-map.iso"
            for executable, expected_code, expected_status, error_code in cases:
                data = bytes(_iso(executable=executable))
                path.write_bytes(data)
                for json_mode in (True, False):
                    with self.subTest(expected_status=expected_status, json_mode=json_mode):
                        command = [sys.executable, str(ROOT / "tools/rptp_inspect.py"), str(path)]
                        if json_mode:
                            command.append("--json")
                        runs = [subprocess.run(command, capture_output=True, text=True, check=False) for _ in range(2)]
                        for run in runs:
                            self.assertEqual(run.returncode, expected_code)
                            if json_mode:
                                self.assertEqual(run.stderr, "")
                                payload = json.loads(run.stdout)
                                self.assertEqual(payload["status"], expected_status)
                                if error_code:
                                    self.assertEqual(payload["error_code"], error_code)
                                else:
                                    self.assertIn("entry_point_mappings", payload["boot_executable"]["elf"])
                            elif error_code:
                                self.assertEqual(run.stdout, "")
                                self.assertIn(error_code, run.stderr)
                            else:
                                self.assertEqual(run.stderr, "")
                                self.assertIn(expected_status, run.stdout)
                        self.assertEqual(runs[0].stdout, runs[1].stdout)
                        self.assertEqual(runs[0].stderr, runs[1].stderr)
                        self.assertEqual(path.read_bytes(), data)
                        self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_load_map_is_deterministic_and_does_not_mutate_input(self):
        data = bytes(_iso(executable=self.executable([
            (1, 192, 0x1000, 8, 32, 5), (1, 200, 0x1008, 8, 16, 6),
        ], 0x100C)))
        before = hashlib.sha256(data).hexdigest()
        reports = [inspector.inspect_bytes(data) for _ in range(2)]
        self.assertEqual(json.dumps(reports[0], sort_keys=True), json.dumps(reports[1], sort_keys=True))
        self.assertEqual(hashlib.sha256(data).hexdigest(), before)
        self.assertNotIn("<memory>", json.dumps(reports[0]["boot_executable"]["elf"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
