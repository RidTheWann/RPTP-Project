# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise the built rptp-load CLI against synthetic ELF32 images.

The C++ test executable covers the loader library. These tests drive the
compiled CLI with independently constructed images and check the JSON contract,
exit codes and determinism. They are skipped unless CTest provides the binary.
"""

from __future__ import annotations

import json
import os
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path

BINARY = os.environ.get("RPTP_LOAD_BINARY", "")
SCHEMA = "rptp.runtime.load.v1"
DEFAULT_ALIGNMENT = 4


def build_elf(
    entry: int,
    segments: list[dict[str, int]],
    payload: bytes = b"",
    payload_offset: int = 116,
    image_size: int | None = None,
) -> bytes:
    size = max(52 + 32 * len(segments), payload_offset + len(payload), image_size or 0)
    image = bytearray(size)
    image[0:4] = b"\x7fELF"
    image[4] = 1
    image[5] = 1
    image[6] = 1
    struct.pack_into(
        "<HHIIIIIHHHHHH",
        image,
        16,
        2,  # ET_EXEC
        8,  # EM_MIPS
        1,  # EV_CURRENT
        entry,
        52,
        0,
        0,
        52,
        32,
        len(segments),
        0,
        0,
        0,
    )
    for index, segment in enumerate(segments):
        struct.pack_into(
            "<IIIIIIII",
            image,
            52 + 32 * index,
            1,  # PT_LOAD
            segment["offset"],
            segment["vaddr"],
            segment["vaddr"],
            segment["filesz"],
            segment["memsz"],
            segment["flags"],
            segment.get("align", DEFAULT_ALIGNMENT),
        )
    image[payload_offset : payload_offset + len(payload)] = payload
    return bytes(image)


def valid_image() -> bytes:
    return build_elf(
        0x00100000,
        [
            {"offset": 116, "vaddr": 0x00100000, "filesz": 4, "memsz": 4, "flags": 5},
            {"offset": 120, "vaddr": 0x00100010, "filesz": 2, "memsz": 4, "flags": 6},
        ],
        payload=b"\x10\x20\x30\x40\xaa\xbb",
    )


@unittest.skipUnless(BINARY and Path(BINARY).is_file(), "RPTP_LOAD_BINARY is not a built executable")
class RuntimeLoadCliTests(unittest.TestCase):
    def run_cli(self, image: bytes | None, *arguments: str) -> tuple[subprocess.CompletedProcess[str], Path]:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "input.elf"
        if image is not None:
            path.write_bytes(image)
        command = [BINARY, *arguments]
        if image is not None:
            command.append(str(path))
        return subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False), path

    def test_valid_image_reports_deterministic_json(self) -> None:
        image = valid_image()
        first, path = self.run_cli(image, "--json")
        self.assertEqual(0, first.returncode, first.stderr)
        self.assertEqual("", first.stderr.strip())
        document = json.loads(first.stdout)
        self.assertEqual(SCHEMA, document["schema"])
        self.assertEqual("ok", document["status"])
        self.assertEqual(len(image), document["image_bytes"])
        self.assertEqual("0x00100000", document["entry_point"])
        self.assertEqual(2, document["load_segment_count"])
        self.assertEqual(6, document["total_file_bytes"])
        self.assertEqual(8, document["total_memory_bytes"])
        self.assertEqual(2, len(document["segments"]))
        code, data = document["segments"]
        self.assertEqual("0x00100000", code["virtual_address"])
        self.assertEqual(116, code["file_offset"])
        self.assertTrue(code["executable"])
        self.assertFalse(code["writable"])
        self.assertEqual("0x00100010", data["virtual_address"])
        self.assertFalse(data["executable"])
        self.assertTrue(data["writable"])
        self.assertEqual(image, path.read_bytes())

        second, _ = self.run_cli(image, "--json")
        self.assertEqual(0, second.returncode, second.stderr)
        self.assertEqual(first.stdout, second.stdout)

    def test_overlap_is_rejected(self) -> None:
        image = build_elf(
            0x00100000,
            [
                {"offset": 116, "vaddr": 0x00100000, "filesz": 4, "memsz": 8, "flags": 5},
                {"offset": 120, "vaddr": 0x00100004, "filesz": 2, "memsz": 2, "flags": 6},
            ],
            payload=b"\x01\x02\x03\x04\x05\x06",
        )
        result, _ = self.run_cli(image, "--json")
        self.assertEqual(2, result.returncode)
        document = json.loads(result.stdout)
        self.assertEqual(SCHEMA, document["schema"])
        self.assertEqual("error", document["status"])
        self.assertEqual("LOAD_SEGMENT_OVERLAP", document["error"]["code"])

    def test_entry_in_zero_fill_is_rejected(self) -> None:
        image = build_elf(
            0x00100002,
            [{"offset": 116, "vaddr": 0x00100000, "filesz": 2, "memsz": 4, "flags": 5}],
            payload=b"\x01\x02",
        )
        result, _ = self.run_cli(image, "--json")
        self.assertEqual(2, result.returncode)
        self.assertEqual("LOAD_ENTRY_NOT_FILE_BACKED", json.loads(result.stdout)["error"]["code"])

    def test_malformed_magic_is_rejected(self) -> None:
        image = bytearray(valid_image())
        image[1] = ord("X")
        result, _ = self.run_cli(bytes(image), "--json")
        self.assertEqual(2, result.returncode)
        self.assertEqual("LOAD_NOT_ELF", json.loads(result.stdout)["error"]["code"])

    def test_limits_are_enforced(self) -> None:
        image = valid_image()
        result, _ = self.run_cli(image, "--json", "--max-image-bytes", "64")
        self.assertEqual(2, result.returncode)
        self.assertEqual("LOAD_IMAGE_TOO_LARGE", json.loads(result.stdout)["error"]["code"])
        result, _ = self.run_cli(image, "--json", "--max-guest-bytes", "7")
        self.assertEqual(2, result.returncode)
        self.assertEqual("LOAD_GUEST_LIMIT", json.loads(result.stdout)["error"]["code"])

    def test_error_without_json_uses_stderr(self) -> None:
        result, _ = self.run_cli(b"not an elf")
        self.assertEqual(2, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertIn("LOAD_IMAGE_TOO_SMALL", result.stderr)

    def test_usage_and_read_errors_exit_one(self) -> None:
        result = subprocess.run([BINARY], capture_output=True, text=True, encoding="utf-8", check=False)
        self.assertEqual(1, result.returncode)
        self.assertIn("usage:", result.stderr)
        result, _ = self.run_cli(valid_image(), "--json", "--max-image-bytes", "0")
        self.assertEqual(1, result.returncode)
        self.assertEqual("", result.stdout)
        result = subprocess.run(
            [BINARY, "--json", str(Path(tempfile.gettempdir()) / "rptp-missing-input.elf")],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(1, result.returncode)


if __name__ == "__main__":
    unittest.main(verbosity=2)
