# SPDX-License-Identifier: GPL-3.0-or-later
"""Guard the R5900 ISA catalog's documented provenance status.

``docs/research/r5900-isa.json`` carries a ``"verified": true`` boolean and
page citations to manuals that are not approved references. The catalog is
useful as an encoding map, but its boolean must never be presented as verified
semantics and the catalog itself must never be registered as an approved
reference. These checks keep the documentation map, the provenance note and
the evidence-level document consistent:

* the documentation map does not describe the catalog as verified semantics
  derived from public neutral specifications;
* ``docs/research/isa-evidence.md`` exists, is mapped, and defines the three
  evidence levels with the pending-owner status spelled out;
* every instruction row in ``docs/INSTRUCTION_CATALOG.md`` has an evidence
  row in ``isa-evidence.md`` that names at least one existing test path;
* the approved-reference table does not list the catalog, the Sony manuals or
  ``ps2tek``, and no manual-named PDF is stored in the repository.

This is a documentation-consistency test, not a provenance review: a green run
proves that the wording has not regressed, not that any catalog entry is
correct.
"""

from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
CATALOG = DOCS / "research" / "r5900-isa.json"
EVIDENCE = DOCS / "research" / "isa-evidence.md"
DOCUMENTATION_MAP = DOCS / "README.md"
REFERENCES = DOCS / "REFERENCES.md"
INSTRUCTION_CATALOG = DOCS / "INSTRUCTION_CATALOG.md"

FORBIDDEN_CATALOG_CLAIMS = (
    "verified R5900/MMI decoding and semantics",
    "derived from public neutral specifications",
    "verified research catalog",
)

SKIPPED_COP2_ENTRIES = (
    "QMFC2",
    "QMTC2",
    "CFC2",
    "CTC2",
    "BC2F",
    "BC2FL",
    "BC2T",
    "BC2TL",
)

EVIDENCE_LEVEL_LABELS = (
    "decoder-crosscheck",
    "test-defined + approved reference",
    "unverified / pending approved reference",
)

CATALOG_ROW = re.compile(r"^\| `([A-Z][A-Z0-9.]*)` \|")
TEST_PATH = re.compile(r"(?:tests|runtime/tests)/[A-Za-z0-9_./-]+\.(?:py|cpp)")
REFERENCE_ROW = re.compile(r"^\| RPTP-REF-\d{3} \|")
MANUAL_FILE_NAME = re.compile(r"(ee[_-]?core|vu[_-]?users|ps2[_-]?docs)", re.IGNORECASE)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def catalog_instruction_rows() -> list[tuple[str, str]]:
    """Return (mnemonic, full row text) for the supported-subset table."""
    rows: list[tuple[str, str]] = []
    for line in read(INSTRUCTION_CATALOG).splitlines():
        match = CATALOG_ROW.match(line)
        if match:
            rows.append((match.group(1), line))
    return rows


def evidence_rows() -> dict[str, str]:
    """Return {mnemonic: row} for the evidence document's supported-subset table."""
    rows: dict[str, str] = {}
    for line in read(EVIDENCE).splitlines():
        match = CATALOG_ROW.match(line)
        if match:
            rows[match.group(1)] = line
    return rows


class CatalogProvenanceTests(unittest.TestCase):
    def test_documentation_map_marks_the_catalog_as_pending(self) -> None:
        map_text = read(DOCUMENTATION_MAP)
        for forbidden in FORBIDDEN_CATALOG_CLAIMS:
            with self.subTest(claim=forbidden):
                self.assertNotIn(forbidden, map_text)

        catalog_lines = [
            line
            for line in map_text.splitlines()
            if "docs/research/r5900-isa.json" in line
        ]
        self.assertEqual(
            len(catalog_lines),
            1,
            "docs/README.md must map docs/research/r5900-isa.json exactly once.",
        )
        line = catalog_lines[0]
        self.assertIn(
            "pending",
            line.lower(),
            "The catalog map entry must state that provenance is pending review; "
            "it must not present the catalog as verified semantics.",
        )
        self.assertIn(
            "isa-evidence.md",
            line,
            "The catalog map entry must link docs/research/isa-evidence.md.",
        )
        self.assertIn(
            "docs/research/isa-evidence.md",
            map_text,
            "docs/research/isa-evidence.md must be listed in the documentation map.",
        )

    def test_evidence_document_defines_the_levels_and_pending_status(self) -> None:
        self.assertTrue(EVIDENCE.is_file(), "docs/research/isa-evidence.md is missing.")
        text = read(EVIDENCE)
        for label in EVIDENCE_LEVEL_LABELS:
            with self.subTest(label=label):
                self.assertIn(label, text)
        self.assertIn("not semantic evidence", text)
        self.assertIn("Owner decisions needed", text)
        for mnemonic in SKIPPED_COP2_ENTRIES:
            with self.subTest(mnemonic=mnemonic):
                self.assertIn(f"`{mnemonic}`", text)
        # The document must not cite an unapproved manual as an approved
        # reference row of its own; it may only repeat catalog page pointers.
        self.assertNotIn("RPTP-REF-018", text)

    def test_evidence_table_covers_every_catalog_instruction_with_a_test(self) -> None:
        rows = evidence_rows()
        catalog_rows = catalog_instruction_rows()
        self.assertGreaterEqual(
            len(catalog_rows),
            28,
            "The supported-subset table in docs/INSTRUCTION_CATALOG.md was not parsed; "
            "the row format may have changed.",
        )
        for mnemonic, _line in catalog_rows:
            with self.subTest(mnemonic=mnemonic):
                self.assertIn(
                    mnemonic,
                    rows,
                    f"{mnemonic} has no evidence row in docs/research/isa-evidence.md.",
                )
                test_paths = TEST_PATH.findall(rows[mnemonic])
                self.assertTrue(
                    test_paths,
                    f"{mnemonic}'s evidence row names no test path.",
                )
                for relative in test_paths:
                    self.assertTrue(
                        (ROOT / relative).is_file(),
                        f"{mnemonic}'s evidence row names a missing test: {relative}.",
                    )

    def test_approved_reference_table_does_not_register_unapproved_sources(self) -> None:
        refs = read(REFERENCES)
        reference_rows = [
            line for line in refs.splitlines() if REFERENCE_ROW.match(line)
        ]
        self.assertGreaterEqual(
            len(reference_rows),
            17,
            "The RPTP-REF table was not parsed; the row format may have changed.",
        )
        forbidden_fragments = ("r5900-isa", "ps2tek", "PS2Docs", "psi-rockin")
        for row in reference_rows:
            label = row.split("|")[1].strip()
            for fragment in forbidden_fragments:
                with self.subTest(reference=label, fragment=fragment):
                    self.assertNotIn(
                        fragment,
                        row,
                        f"{label} registers an unapproved R5900/PS2 source as an "
                        "approved reference; the manual and ps2tek use is pending.",
                    )

        status_note = "R5900 ISA catalog provenance status"
        self.assertIn(
            status_note,
            refs,
            "docs/REFERENCES.md must keep the catalog provenance status note.",
        )
        self.assertIn("none of the three is an approved reference", refs)
        self.assertIn(
            "not stored in the repository",
            refs,
            "The provenance note must state that the manual PDFs are not stored.",
        )
        self.assertIn(
            "not a legal conclusion",
            refs,
            "The provenance note must not read as a legal conclusion.",
        )

    def test_no_manual_pdf_is_stored_in_the_repository(self) -> None:
        tracked = subprocess.run(
            ["git", "ls-files", "-z", "--cached"],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if tracked.returncode:
            self.skipTest("git metadata is unavailable; cannot list tracked files")
        offending = [
            path
            for path in tracked.stdout.decode("utf-8").split("\0")
            if path and MANUAL_FILE_NAME.search(Path(path).name)
        ]
        self.assertEqual(
            [],
            offending,
            "Manual-named files must not be committed; the manuals are cited by "
            "pointer only and their PDFs are not stored in the repository.",
        )
        self.assertEqual(
            [path.name for path in (DOCS / "research").glob("*.pdf")],
            [],
            "docs/research must not store manual PDFs.",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
