# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import argparse
from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ASSETS = DOCS / "assets"
SNAPSHOT_DATE = "2026-10-23"

COLORS = {
    "verified": ("#238636", "#2ea043", "#f0f6fc"),
    "partial": ("#9e6a03", "#d29922", "#f0f6fc"),
    "open": ("#21262d", "#30363d", "#8b949e"),
}

STATUS_LABELS = {
    "verified": "Verified",
    "partial": "Partial / review open",
    "open": "Open",
}

FOUNDATION = [
    ("License", "verified"),
    ("CMake presets", "verified"),
    ("Doctor", "verified"),
    ("Artifact guard", "verified"),
    ("CI", "verified"),
    ("ISO 9660 PVD", "verified"),
    ("SYSTEM.CNF", "verified"),
    ("BOOT path", "verified"),
    ("ELF32 / PT_LOAD", "verified"),
    ("SHA-256", "verified"),
    ("Synthetic tests", "verified"),
    ("Real ISO sample", "verified"),
    ("Game work records", "verified"),
    ("Gate 0 formal", "verified"),
    ("Clean-room review", "partial"),
    ("ISO variants", "open"),
    ("Extraction design", "open"),
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

PAGE_CSS = """
    :root {
      color-scheme: dark;
      --bg: #0d1117;
      --panel: #161b22;
      --panel-strong: #21262d;
      --border: #30363d;
      --text: #e6edf3;
      --muted: #8b949e;
      --link: #58a6ff;
      --green: #3fb950;
      --green-bg: #238636;
      --green-border: #2ea043;
      --amber: #d29922;
      --amber-bg: #9e6a03;
      --amber-border: #bb8009;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: "Segoe UI", Arial, sans-serif;
      line-height: 1.55;
    }

    main {
      width: min(1100px, 100%);
      margin: 0 auto;
      padding: 32px 20px 56px;
    }

    a { color: var(--link); }

    header { margin-bottom: 24px; }

    .eyebrow {
      margin: 0 0 4px;
      color: var(--green);
      font-size: 0.8rem;
      font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }

    h1 {
      margin: 0;
      font-size: clamp(2rem, 5vw, 3rem);
      line-height: 1.15;
    }

    .lede {
      max-width: 760px;
      margin: 12px 0 0;
      color: var(--muted);
    }

    .map {
      display: block;
      width: 100%;
      height: auto;
      margin: 0 0 8px;
      border-radius: 10px;
    }

    .updated,
    .generated {
      margin: 0;
      color: var(--muted);
      font-size: 0.85rem;
    }

    .generated { margin-top: 4px; }

    .details {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
      margin: 28px 0 32px;
    }

    .section {
      padding: 18px;
      min-width: 0;
      border: 1px solid var(--border);
      border-radius: 10px;
      background: var(--panel);
    }

    .section h2 {
      margin: 0;
      font-size: 1.05rem;
    }

    .section > p {
      margin: 3px 0 14px;
      color: var(--muted);
      font-size: 0.9rem;
    }

    .table-wrap { overflow-x: auto; }

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.92rem;
    }

    th,
    td {
      padding: 8px 6px;
      border-bottom: 1px solid var(--border);
      text-align: left;
      vertical-align: top;
    }

    th {
      color: var(--muted);
      font-size: 0.78rem;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }

    th:last-child,
    td:last-child { text-align: right; }

    tbody tr:last-child td { border-bottom: 0; }

    .pill {
      display: inline-block;
      padding: 1px 8px;
      border: 1px solid var(--border);
      border-radius: 999px;
      font-size: 0.78rem;
      white-space: nowrap;
    }

    .pill.verified {
      border-color: var(--green-border);
      background: rgba(35, 134, 54, 0.22);
      color: #7ee787;
    }

    .pill.partial {
      border-color: var(--amber-border);
      background: rgba(158, 106, 3, 0.22);
      color: #e3b341;
    }

    .pill.open {
      background: var(--panel-strong);
      color: var(--muted);
    }

    .notes {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
      margin-bottom: 32px;
    }

    .notes h2 {
      margin: 0 0 10px;
      font-size: 1.05rem;
    }

    .notes p,
    .notes ul {
      margin: 0;
      color: var(--muted);
    }

    .notes ul { padding-left: 20px; }

    .notes li + li { margin-top: 6px; }

    .notes strong { color: var(--text); }

    footer {
      padding-top: 18px;
      border-top: 1px solid var(--border);
      color: var(--muted);
      font-size: 0.85rem;
    }

    footer p { margin: 0; }

    @media (max-width: 760px) {
      main { padding-top: 24px; }

      .details,
      .notes { grid-template-columns: 1fr; }
    }
"""


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


def render_progress_svg() -> str:
    foundation_verified = _count(FOUNDATION, "verified")
    runtime_verified = _count(RUNTIME, "verified")
    foundation_percent = foundation_verified / len(FOUNDATION) * 100
    runtime_percent = runtime_verified / len(RUNTIME) * 100
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="576" viewBox="0 0 1200 576" role="img" aria-labelledby="rptp-progress-title rptp-progress-desc">
  <title id="rptp-progress-title">RPTP progress map</title>
  <desc id="rptp-progress-desc">Foundation checklist {foundation_percent:.1f} percent verified; runtime checklist {runtime_percent:.1f} percent verified. Percentages are scope checklists, not game compatibility or overall completion.</desc>
  <rect width="1200" height="576" rx="16" fill="#0d1117"/>
  <rect x="0.5" y="0.5" width="1199" height="575" rx="16" fill="none" stroke="#30363d"/>
  <g font-family="Segoe UI, Arial, sans-serif">
    <text x="1168" y="24" text-anchor="end" font-size="12" fill="#8b949e">Updated {SNAPSHOT_DATE}</text>

    {_bar(40, 44, "Foundation checklist", FOUNDATION, "verified")}
    {_bar(620, 44, "Runtime checklist", RUNTIME, "partial")}

    <text x="40" y="126" font-size="20" font-weight="700" fill="#f0f6fc">Foundation &amp; inspection</text>
    <text x="40" y="148" font-size="12" fill="#8b949e">{len(FOUNDATION)} checklist items: build, inspector and evidence</text>
    <text x="620" y="126" font-size="20" font-weight="700" fill="#f0f6fc">Runtime &amp; compatibility</text>
    <text x="620" y="148" font-size="12" fill="#8b949e">{len(RUNTIME)} checklist items: decoder, recompiler and PS2 services</text>

    {_grid(40, 164, FOUNDATION)}
    {_grid(620, 164, RUNTIME)}

    <rect x="40" y="452" width="14" height="14" rx="3" fill="#238636" stroke="#2ea043"/>
    <text x="62" y="464" font-size="12" fill="#c9d1d9">Verified</text>
    <rect x="154" y="452" width="14" height="14" rx="3" fill="#9e6a03" stroke="#d29922"/>
    <text x="176" y="464" font-size="12" fill="#c9d1d9">Partial / review open</text>
    <rect x="340" y="452" width="14" height="14" rx="3" fill="#21262d" stroke="#30363d"/>
    <text x="362" y="464" font-size="12" fill="#c9d1d9">Not started</text>

    <text x="40" y="504" font-size="12" fill="#8b949e">Percentages count only the labeled items in each checklist. They are not overall completion, boot support or game compatibility.</text>
    <text x="40" y="526" font-size="12" fill="#8b949e">Evidence: Python test suite passes · CTest results in the verification log · authorized retail ISOs inspected read-only · Gate 0 formal review pending.</text>
    <text x="40" y="548" font-size="12" fill="#8b949e">Next: ISO-variant review. Extraction design is deferred future work; interleaved layouts remain unsupported and runtime work remains gated.</text>
  </g>
</svg>
'''


def render_badge(label: str, value: str, tone: str) -> str:
    fill, stroke, _ = COLORS[tone]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="220" height="28" viewBox="0 0 220 28" role="img" aria-label="{escape(label)}: {value} verified">
  <title>{escape(label)}: {value} verified</title>
  <rect width="220" height="28" rx="4" fill="#161b22" stroke="#30363d"/>
  <rect x="120" width="100" height="28" rx="4" fill="{fill}" stroke="{stroke}"/>
  <g font-family="Segoe UI, Arial, sans-serif" font-size="12" fill="#f0f6fc">
    <text x="10" y="18">{escape(label)}</text>
    <text x="210" y="18" text-anchor="end" font-weight="700">{value}</text>
  </g>
</svg>
'''


def _table_rows(items: list[tuple[str, str]]) -> str:
    return "".join(
        f'<tr><td>{escape(label)}</td>'
        f'<td><span class="pill {status}">{STATUS_LABELS[status]}</span></td></tr>'
        for label, status in items
    )


def render_html() -> str:
    foundation_verified = _count(FOUNDATION, "verified")
    runtime_verified = _count(RUNTIME, "verified")
    foundation_percent = foundation_verified / len(FOUNDATION) * 100
    runtime_percent = runtime_verified / len(RUNTIME) * 100
    return f'''<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="RPTP checklist progress. Scope status only; not game compatibility.">
  <title>RPTP progress</title>
  <style>{PAGE_CSS}</style>
</head>
<body>
  <main>
    <header>
      <p class="eyebrow">RPTP project</p>
      <h1>Progress</h1>
      <p class="lede">Early research. These checklists measure implemented and verified scope, not game compatibility or overall completion.</p>
    </header>

    <img class="map" src="assets/progress.svg" alt="RPTP progress map: foundation checklist {foundation_percent:.1f} percent verified; runtime checklist {runtime_percent:.1f} percent verified.">
    <p class="updated">Last updated {SNAPSHOT_DATE}</p>
    <p class="generated">Generated by <a href="https://github.com/RidTheWann/RPTP-Project">tools/rptp_progress.py</a>. Raw evidence is tracked in <a href="STATE.md">docs/STATE.md</a>.</p>

    <div class="details">
      <section class="section" aria-labelledby="foundation-heading">
        <h2 id="foundation-heading">Foundation &amp; inspection</h2>
        <p>{len(FOUNDATION)} checklist items: build, inspector and evidence.</p>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th scope="col">Checklist item</th>
                <th scope="col">Status</th>
              </tr>
            </thead>
            <tbody>
              {_table_rows(FOUNDATION)}
            </tbody>
          </table>
        </div>
      </section>

      <section class="section" aria-labelledby="runtime-heading">
        <h2 id="runtime-heading">Runtime &amp; compatibility</h2>
        <p>{len(RUNTIME)} checklist items: decoder, recompiler and PS2 services.</p>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th scope="col">Checklist item</th>
                <th scope="col">Status</th>
              </tr>
            </thead>
            <tbody>
              {_table_rows(RUNTIME)}
            </tbody>
          </table>
        </div>
      </section>
    </div>

    <div class="notes">
      <section class="section">
        <h2>What these numbers mean</h2>
        <ul>
          <li><strong>Verified:</strong> the item has recorded evidence in <a href="STATE.md">docs/STATE.md</a>.</li>
          <li><strong>Partial / review open:</strong> technical work exists, but a required review or follow-up is pending.</li>
          <li><strong>Open:</strong> no implementation or evidence yet.</li>
          <li><strong>Policy decisions:</strong> recorded in the ADRs; they are not counted as verified items.</li>
        </ul>
        <p>Percentages count only the labeled items in each checklist. They are not overall completion, boot support or game compatibility.</p>
      </section>

      <section class="section">
        <h2>Evidence snapshot</h2>
        <ul>
          <li>The Python test suite passes; CTest and Gate 0 results are recorded in <a href="VERIFICATION_LOG.md">docs/VERIFICATION_LOG.md</a>.</li>
          <li>The current authorized retail sample has been inspected read-only; records are in the <a href="games/README.md">game work index</a>. No boot, recompilation or gameplay exists.</li>
          <li>Formal Gate 0 disposition and the clean-room review of the build/CI/doctor layer remain pending.</li>
        </ul>
        <p>Next bounded work: ISO-variant review. Extraction design is deferred future work under ADR-0004. Interleaved layouts remain unsupported; runtime and recompiler expansion remain gated by formal Gate 0.</p>
      </section>
    </div>

    <footer>
      <p>
        <a href="https://github.com/RidTheWann/RPTP-Project#readme">Project README</a>
        &middot; <a href="STATE.md">State</a>
        &middot; <a href="ROADMAP.md">Roadmap</a>
      </p>
    </footer>
  </main>
</body>
</html>
'''


def main() -> int:
    parser = argparse.ArgumentParser(description="Render the RPTP progress page and SVG assets.")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()

    docs = args.root / "docs"
    assets = docs / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    foundation_verified = _count(FOUNDATION, "verified")
    runtime_verified = _count(RUNTIME, "verified")
    files = {
        docs / "progress.html": render_html(),
        assets / "progress.svg": render_progress_svg(),
        assets / "badge-foundation.svg": render_badge(
            "foundation", f"{foundation_verified / len(FOUNDATION) * 100:.1f}%", "verified"
        ),
        assets / "badge-runtime.svg": render_badge(
            "runtime", f"{runtime_verified / len(RUNTIME) * 100:.1f}%", "partial"
        ),
    }

    for path, text in files.items():
        path.write_text(text, encoding="utf-8", newline="\n")
        print(f"Wrote {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
