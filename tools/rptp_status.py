# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import argparse
from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "docs" / "assets" / "rptp-status.svg"

COLORS = {
    "verified": ("#238636", "#2ea043", "#f0f6fc"),
    "partial": ("#9e6a03", "#d29922", "#f0f6fc"),
    "open": ("#21262d", "#30363d", "#8b949e"),
}

FOUNDATION = [
    ("License", "verified"),
    ("Branch policy", "verified"),
    ("CMake presets", "verified"),
    ("Doctor", "verified"),
    ("Artifact guard", "verified"),
    ("CI", "verified"),
    ("ADR-0003", "verified"),
    ("ISO 9660 PVD", "verified"),
    ("SYSTEM.CNF", "verified"),
    ("BOOT path", "verified"),
    ("ELF32 / PT_LOAD", "verified"),
    ("SHA-256", "verified"),
    ("Synthetic tests", "verified"),
    ("Real ISO sample", "verified"),
    ("Game work records", "verified"),
    ("Gate 0 formal", "partial"),
    ("Clean-room review", "partial"),
    ("ISO variants", "open"),
    ("Safe extraction", "open"),
    ("Multi-extent", "open"),
]

RUNTIME = [
    ("R5900 decoder", "partial"),
    ("Synthetic recompiler", "partial"),
    ("IR", "open"),
    ("Function discovery", "open"),
    ("EE kernel", "open"),
    ("Syscalls", "open"),
    ("DMA", "open"),
    ("IOP", "open"),
    ("CDVD", "open"),
    ("VU", "open"),
    ("GS", "open"),
    ("SPU2", "open"),
    ("PAD", "open"),
    ("MECARD", "open"),
    ("Timing", "open"),
    ("Native boot", "open"),
    ("First frame", "open"),
    ("Audio/input", "open"),
    ("Save/load", "open"),
    ("Gameplay", "open"),
]


def _count(items: list[tuple[str, str]], status: str) -> int:
    return sum(1 for _, item_status in items if item_status == status)


def _tile(x: int, y: int, label: str, status: str) -> str:
    fill, stroke, text = COLORS[status]
    return (
        f'<rect x="{x}" y="{y}" width="130" height="48" rx="5" '
        f'fill="{fill}" stroke="{stroke}"/>'
        f'<text x="{x + 65}" y="{y + 29}" text-anchor="middle" '
        f'font-size="11" fill="{text}">{escape(label)}</text>'
    )


def _grid(x: int, y: int, items: list[tuple[str, str]]) -> str:
    tiles = []
    for index, (label, status) in enumerate(items):
        column = index % 4
        row = index // 4
        tiles.append(_tile(x + column * 136, y + row * 54, label, status))
    return "".join(tiles)


def _bar(x: int, y: int, label: str, items: list[tuple[str, str]], tone: str) -> str:
    verified = _count(items, "verified")
    partial = _count(items, "partial")
    open_count = _count(items, "open")
    total = len(items)
    percent = verified / total * 100
    width = 540
    fill_width = width * verified / total
    value_color = "#3fb950" if tone == "verified" else "#d29922"
    return (
        f'<text x="{x}" y="{y}" font-size="14" font-weight="600" fill="#f0f6fc">'
        f'{escape(label)}</text>'
        f'<text x="{x + width}" y="{y}" text-anchor="end" font-size="14" '
        f'font-weight="700" fill="{value_color}">{percent:.1f}%</text>'
        f'<rect x="{x}" y="{y + 10}" width="{width}" height="16" rx="4" fill="#21262d"/>'
        f'<rect x="{x}" y="{y + 10}" width="{fill_width:.1f}" height="16" rx="4" '
        f'fill="{value_color}"/>'
        f'<text x="{x}" y="{y + 44}" font-size="11" fill="#8b949e">'
        f'{verified} verified · {partial} review/partial · {open_count} open</text>'
    )


def render_svg() -> str:
    foundation_verified = _count(FOUNDATION, "verified")
    runtime_verified = _count(RUNTIME, "verified")
    foundation_percent = foundation_verified / len(FOUNDATION) * 100
    runtime_percent = runtime_verified / len(RUNTIME) * 100
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="640" viewBox="0 0 1200 640" role="img" aria-labelledby="rptp-status-title rptp-status-desc">
  <title id="rptp-status-title">RPTP project status dashboard</title>
  <desc id="rptp-status-desc">Foundation checklist {foundation_percent:.1f} percent verified; runtime checklist {runtime_percent:.1f} percent verified. Percentages are scope checklists, not game compatibility or overall completion.</desc>
  <rect width="1200" height="640" rx="16" fill="#0d1117"/>
  <rect x="0.5" y="0.5" width="1199" height="639" rx="16" fill="none" stroke="#30363d"/>
  <g font-family="Segoe UI, Arial, sans-serif">
    <rect x="32" y="24" width="36" height="36" rx="8" fill="#161b22" stroke="#30363d"/>
    <path d="M41 42 l6 6 l12 -14" fill="none" stroke="#3fb950" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
    <text x="82" y="51" font-size="28" font-weight="700" fill="#f0f6fc">Status</text>
    <text x="1168" y="51" text-anchor="end" font-size="12" fill="#8b949e">Updated 2026-10-21</text>
    <text x="82" y="76" font-size="12" fill="#8b949e">Early research. Checklists measure implemented and verified scope, not game compatibility.</text>

    {_bar(40, 112, "Foundation checklist", FOUNDATION, "verified")}
    {_bar(620, 112, "Runtime checklist", RUNTIME, "partial")}

    <text x="40" y="194" font-size="20" font-weight="700" fill="#f0f6fc">Foundation &amp; inspection</text>
    <text x="40" y="216" font-size="12" fill="#8b949e">20 checklist items: build, policy, inspector and evidence</text>
    <text x="620" y="194" font-size="20" font-weight="700" fill="#f0f6fc">Runtime &amp; compatibility</text>
    <text x="620" y="216" font-size="12" fill="#8b949e">20 checklist items: decoder, recompiler and PS2 services</text>

    {_grid(40, 232, FOUNDATION)}
    {_grid(620, 232, RUNTIME)}

    <rect x="40" y="546" width="14" height="14" rx="3" fill="#238636" stroke="#2ea043"/>
    <text x="62" y="558" font-size="12" fill="#c9d1d9">Verified</text>
    <rect x="154" y="546" width="14" height="14" rx="3" fill="#9e6a03" stroke="#d29922"/>
    <text x="176" y="558" font-size="12" fill="#c9d1d9">Partial / review open</text>
    <rect x="340" y="546" width="14" height="14" rx="3" fill="#21262d" stroke="#30363d"/>
    <text x="362" y="558" font-size="12" fill="#c9d1d9">Not started</text>

    <text x="40" y="588" font-size="12" fill="#8b949e">Percentages count only the 20 labeled items in each checklist. They are not overall completion, boot support or game compatibility.</text>
    <text x="40" y="610" font-size="12" fill="#8b949e">Evidence: 53 Python tests · CTest 3/3 · one retail ISO inspected read-only · Gate 0 formal review pending.</text>
    <text x="40" y="632" font-size="12" fill="#8b949e">Next: broader retail ISO validation and safe extraction boundaries; runtime work remains gated.</text>
  </g>
</svg>
'''


def main() -> int:
    parser = argparse.ArgumentParser(description="Render the RPTP status dashboard SVG.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_svg(), encoding="utf-8", newline="\n")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
