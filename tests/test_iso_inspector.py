from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("rptp_inspect", ROOT / "tools/rptp_inspect.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Cannot load tools/rptp_inspect.py")
inspector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inspector)

BLOCK = 2048
VOLUME_BLOCKS = 32


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


def _elf(machine: int = 8, phnum: int = 1) -> bytes:
    data = bytearray(84)
    data[:7] = b"\x7fELF" + bytes((1, 1, 1))
    data[16:18] = (2).to_bytes(2, "little")
    data[18:20] = machine.to_bytes(2, "little")
    data[20:24] = (1).to_bytes(4, "little")
    data[24:28] = (0x00100000).to_bytes(4, "little")
    data[28:32] = (52).to_bytes(4, "little")
    data[40:42] = (52).to_bytes(2, "little")
    data[42:44] = (32).to_bytes(2, "little")
    data[44:46] = phnum.to_bytes(2, "little")
    return bytes(data)


def _iso(config: bytes | None = b"BOOT2 = cdrom0:\\SLUS_123.45;1\nVER = 1.00\nVMODE = NTSC\n",
         executable: bytes | None = None, boot_lba: int = 21, block_size: int = BLOCK) -> bytearray:
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
    if config is not None:
        records.append(_record(20, len(config), b"SYSTEM.CNF;1"))
    exe = executable if executable is not None else _elf()
    records.append(_record(boot_lba, len(exe), b"SLUS_123.45;1"))
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
    return image


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
            inspector.inspect_bytes(bytes(_iso(executable=_elf(phnum=2))))
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
