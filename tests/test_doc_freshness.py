# SPDX-License-Identifier: GPL-3.0-or-later
"""Check that current-status documents track the append-only evidence log."""

from __future__ import annotations

import re
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

LOG_DATE = re.compile(r"^## (\d{4}-\d{2}-\d{2})", flags=re.MULTILINE)
LOGGED_MERGE = re.compile(r"PR #(\d+) merged[^\n]*?as `([0-9a-f]{7,40})`")
SNAPSHOT_DATE = re.compile(r"^- \*\*Snapshot date:\*\* (\d{4}-\d{2}-\d{2})$", flags=re.MULTILINE)
PR_RANGE = re.compile(r"PRs? #10–#(\d+)")
MAP_PATH = re.compile(r"`((?:docs/|README|AGENTS)[A-Za-z0-9_./-]*\.md)`")


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class DocumentationFreshnessTests(unittest.TestCase):
    def test_state_snapshot_date_matches_latest_log_entry(self) -> None:
        log = read("docs/VERIFICATION_LOG.md")
        dates = LOG_DATE.findall(log)
        self.assertTrue(dates, "docs/VERIFICATION_LOG.md must have dated sections.")
        state = read("docs/STATE.md")
        match = SNAPSHOT_DATE.search(state)
        self.assertIsNotNone(match, "docs/STATE.md must record a snapshot date.")
        assert match is not None
        self.assertEqual(
            match.group(1),
            max(dates),
            "docs/STATE.md snapshot date must equal the newest VERIFICATION_LOG.md date; "
            "record the increment's evidence before updating STATE.",
        )

    def test_state_and_handoff_track_the_latest_logged_merge(self) -> None:
        log = read("docs/VERIFICATION_LOG.md")
        merges = LOGGED_MERGE.findall(log)
        self.assertTrue(merges, "docs/VERIFICATION_LOG.md must record merged PRs.")
        latest_pr, latest_sha = max((int(pr), sha) for pr, sha in merges)

        for name, text in (
            ("docs/STATE.md", read("docs/STATE.md")),
            ("docs/HANDOFF.md", read("docs/HANDOFF.md")),
        ):
            with self.subTest(document=name):
                match = PR_RANGE.search(text)
                self.assertIsNotNone(
                    match,
                    f"{name} must state the merged PR range as 'PR #10–#N'.",
                )
                assert match is not None
                recorded_pr = int(match.group(1))
                self.assertGreaterEqual(
                    recorded_pr,
                    latest_pr,
                    f"{name} stops at PR #{recorded_pr}, but VERIFICATION_LOG.md "
                    f"records PR #{latest_pr}; update the pointer.",
                )
                if recorded_pr == latest_pr:
                    self.assertIn(
                        f"`{latest_sha[:7]}`",
                        text,
                        f"{name} must cite merge `{latest_sha[:7]}` for PR #{latest_pr}.",
                    )

    def test_documentation_map_lists_every_document(self) -> None:
        map_text = read("docs/README.md")
        mapped = set(MAP_PATH.findall(map_text))
        self.assertIn(
            "docs/README.md",
            mapped,
            "docs/README.md must list itself so the map is discoverable.",
        )

        documents = {"README.md", "AGENTS.md"}
        documents.update(
            path.relative_to(ROOT).as_posix() for path in DOCS.rglob("*.md")
        )
        missing = sorted(documents - mapped)
        self.assertEqual(
            missing,
            [],
            f"docs/README.md is missing documents: {missing}. Add every document to the map.",
        )
        absent = sorted(path for path in mapped if not (ROOT / path).is_file())
        self.assertEqual(
            absent,
            [],
            f"docs/README.md maps files that do not exist: {absent}.",
        )

        for name in ("README.md", "AGENTS.md"):
            self.assertIn(
                "docs/README.md",
                read(name),
                f"{name} must link the documentation map.",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
