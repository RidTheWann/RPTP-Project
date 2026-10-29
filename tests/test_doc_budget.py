# SPDX-License-Identifier: GPL-3.0-or-later
"""Enforce the size budget for the current-status documents.

The budget keeps docs/STATE.md and docs/HANDOFF.md readable entry points:
each file must stay small and must not contain very long lines. Size is
measured from the UTF-8 encoding after converting CRLF or CR line endings to
LF, so a Windows checkout and a Linux checkout produce identical results.
"""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUDGETED_DOCUMENTS = ("docs/STATE.md", "docs/HANDOFF.md")
MAX_BYTES = 8192
MAX_LINE_CHARACTERS = 900


def decode_text(data: bytes) -> str:
    """Decode UTF-8 bytes and drop a leading byte-order mark."""
    return data.decode("utf-8").lstrip("\ufeff")


def normalize_newlines(text: str) -> str:
    """Convert CRLF and bare CR to LF so measurements do not depend on the host."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def byte_size(text: str) -> int:
    return len(text.encode("utf-8"))


def line_lengths(text: str) -> list[int]:
    """Length of every line without its terminator, after newline normalization."""
    return [len(line) for line in normalize_newlines(text).split("\n")]


class DocumentationBudgetTests(unittest.TestCase):
    def test_documents_are_within_byte_budget(self) -> None:
        for relative in BUDGETED_DOCUMENTS:
            with self.subTest(document=relative):
                path = ROOT / relative
                self.assertTrue(path.is_file(), f"{relative}: budgeted document is missing.")
                size = byte_size(normalize_newlines(decode_text(path.read_bytes())))
                self.assertLessEqual(
                    size,
                    MAX_BYTES,
                    f"{relative}: {size} UTF-8 bytes exceeds the {MAX_BYTES}-byte budget.",
                )

    def test_documents_are_within_line_length_budget(self) -> None:
        for relative in BUDGETED_DOCUMENTS:
            with self.subTest(document=relative):
                path = ROOT / relative
                self.assertTrue(path.is_file(), f"{relative}: budgeted document is missing.")
                lengths = line_lengths(decode_text(path.read_bytes()))
                longest = max(lengths) if lengths else 0
                offending = [
                    (number, length)
                    for number, length in enumerate(lengths, start=1)
                    if length > MAX_LINE_CHARACTERS
                ]
                self.assertEqual(
                    [],
                    offending,
                    f"{relative}: longest line is {longest} characters, over the "
                    f"{MAX_LINE_CHARACTERS}-character limit; offending lines "
                    f"(line, characters): {offending}.",
                )

    def test_measurement_ignores_newline_convention(self) -> None:
        sample = "# title\n" + "x" * MAX_LINE_CHARACTERS + "\n\u00e9t\u00e9\n"
        for newline in ("\r\n", "\r"):
            with self.subTest(newline=repr(newline)):
                variant = sample.replace("\n", newline)
                decoded = decode_text(variant.encode("utf-8"))
                self.assertEqual(byte_size(normalize_newlines(decoded)), byte_size(sample))
                self.assertEqual(line_lengths(decoded), line_lengths(sample))
        self.assertEqual([7, MAX_LINE_CHARACTERS, 3, 0], line_lengths(sample))


if __name__ == "__main__":
    unittest.main(verbosity=2)
