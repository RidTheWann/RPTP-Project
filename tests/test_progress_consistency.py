# SPDX-License-Identifier: GPL-3.0-or-later
"""Check that README progress claims match the progress generator."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("rptp_progress", ROOT / "tools/rptp_progress.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Cannot load tools/rptp_progress.py")
progress = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(progress)


class ProgressConsistencyTests(unittest.TestCase):
    def test_readme_matches_progress_checklist(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        foundation_total = len(progress.FOUNDATION)
        foundation_verified = progress._count(progress.FOUNDATION, "verified")
        expected_percent = f"{foundation_verified / foundation_total * 100:.1f}%"

        match = re.search(r"Foundation checklist: ([\d.]+%) verified", readme)
        self.assertIsNotNone(match, "README must contain the foundation badge percentage.")
        assert match is not None
        self.assertEqual(
            match.group(1),
            expected_percent,
            f"README foundation badge says {match.group(1)}, tools/rptp_progress.py says "
            f"{expected_percent} ({foundation_total} items, {foundation_verified} verified).",
        )

        counts_line = f"Foundation ({foundation_total} items) and runtime ({len(progress.RUNTIME)} items)"
        self.assertIn(
            counts_line,
            readme,
            "README checklist item counts must come from tools/rptp_progress.py.",
        )

        verified_labels = {
            label
            for label, status in progress.FOUNDATION + progress.RUNTIME
            if status == "verified"
        }
        self.assertNotIn(
            "ADR-0003",
            verified_labels,
            "A policy decision must not be counted as a verified checklist item.",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
