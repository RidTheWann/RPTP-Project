# SPDX-License-Identifier: GPL-3.0-or-later
"""Check that README progress claims match the progress generator."""

from __future__ import annotations

import hashlib
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


def asset_digest(relative: str) -> str:
    """Content digest after newline normalization so hosts agree on the value."""
    text = (ROOT / relative).read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


class ProgressConsistencyTests(unittest.TestCase):
    def test_snapshot_date_comes_from_verification_log(self) -> None:
        log_text = (ROOT / "docs/VERIFICATION_LOG.md").read_text(encoding="utf-8")
        dates = re.findall(r"^## (\d{4}-\d{2}-\d{2})", log_text, flags=re.MULTILINE)
        self.assertTrue(dates, "docs/VERIFICATION_LOG.md must contain dated sections.")
        expected = max(dates)
        self.assertEqual(
            progress.latest_log_date(ROOT / "docs"),
            expected,
            "The progress snapshot date must be the newest dated VERIFICATION_LOG.md section.",
        )
        svg = (ROOT / "docs/assets/progress.svg").read_text(encoding="utf-8")
        html = (ROOT / "docs/progress.html").read_text(encoding="utf-8")
        self.assertIn(f"Updated {expected}", svg, "progress.svg carries a stale snapshot date.")
        self.assertIn(f"Last updated {expected}", html, "progress.html carries a stale snapshot date.")

    def test_generated_assets_match_the_generator(self) -> None:
        for path, text in progress.rendered_files(ROOT / "docs").items():
            relative = path.relative_to(ROOT)
            with self.subTest(asset=str(relative)):
                self.assertEqual(
                    (ROOT / relative).read_text(encoding="utf-8"),
                    text,
                    f"{relative} is stale; run python tools/rptp_progress.py.",
                )

    def test_readme_image_urls_are_cache_busted(self) -> None:
        snapshot = progress.latest_log_date(ROOT / "docs")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for asset in ("badge-foundation.svg", "badge-runtime.svg", "progress.svg"):
            digest = asset_digest(f"docs/assets/{asset}")
            with self.subTest(asset=asset):
                self.assertIn(
                    f"assets/{asset}?v={snapshot}-{digest}",
                    readme,
                    "README image URLs must carry the snapshot date and content digest "
                    "so GitHub's image proxy refetches them after every change.",
                )

    def test_readme_reports_catalogued_instruction_count(self) -> None:
        instructions = progress.catalogued_instructions(ROOT / "docs")
        self.assertGreater(len(instructions), 0, "The catalog must list synthetic instructions.")
        self.assertIn("SUBU", instructions, "The catalog has a SUBU row.")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(
            f"{len(instructions)} catalogued synthetic instructions",
            readme,
            "README must report the catalogued synthetic instruction count.",
        )

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
