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
         load_align: int = 0x1000, load_vaddr: int | None = None, data_size: int = 128) -> bytes:
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

    def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(size)
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
