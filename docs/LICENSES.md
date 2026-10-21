# Licensing and third-party notices

## Original RPTP project material

Original RPTP project software, source code, documentation, build scripts, tests and synthetic fixtures are intended to be licensed under the **GNU General Public License, version 3 or (at your option) any later version (`GPL-3.0-or-later`)**, unless an individual file or accompanying notice states otherwise. The repository-root `LICENSE` contains the complete GNU GPL version 3 text; project metadata/notices select the “or later” option. See `docs/DECISIONS/ADR-0001-foundation-and-clean-room.md` for the decision record.

GPL allows commercial use. When conveying a covered work, comply with its applicable conditions, including preserving notices and providing the required corresponding source for covered object-code distributions. Private modification without conveyance does not by itself create a general obligation to publish those changes. Refer to the complete license text for exact requirements.

The license does not grant rights to distribute PlayStation 2 BIOS files, commercial game ISOs, proprietary game executables/assets or game-derived generated code. It also does not, by itself, confer trademark rights in the project name or logo or guarantee public recognition beyond applicable license and copyright-notice requirements.

## SPDX headers

The owner confirmed `GPL-3.0-or-later` for original RPTP material on 2026-10-21. Project-owned source, build and automation files carry this identifier as their first comment line, after any shebang:

    # SPDX-License-Identifier: GPL-3.0-or-later

The policy covers tracked `.py`, `.ps1`, `CMakeLists.txt`, and `.github/workflows/*.yml` files. `tests/test_license_headers.py` checks the header position for git-tracked files; files that are not tracked by git are skipped.

Binary fixtures and data files are not annotated with SPDX comments because a comment would change or corrupt their content. Their origin and license status are recorded in `tests/fixtures/MANIFEST` or the relevant documentation instead. JSON, Markdown, the root `LICENSE`, and third-party files are outside this header policy; third-party material retains its own notices and must not be relabeled as RPTP-owned code.

## Third-party dependencies

Each third-party dependency retains its applicable upstream license and notices. Before adding or vendoring a dependency, record at least its name, version or commit, source URL, SPDX license identifier (where established), license text/notice location, redistribution constraints, and the reason it is needed. Verify compatibility and comply with all required notices; do not assume a dependency is GPL-3.0-or-later merely because it is used by RPTP.

Do not vendor a dependency whose license or provenance has not been verified. Keep source-exposure restrictions in ADR-0001 in force independently of license compatibility.

## Game and console materials

- Do not commit or distribute commercial ISO files, PS2 BIOS, proprietary game executables, game assets, or game-derived generated C++/binaries.
- Keep local generated build outputs and game-specific outputs out of version control unless a separate documented legal review explicitly authorizes an artifact.
- Synthetic test fixtures must be independently created and registered in `tests/fixtures/MANIFEST` with their hash, origin and license status.

## Notices and changes

Retain license and attribution notices required by each upstream component. Add a `NOTICE` file if required by a component or distribution. Review this document whenever dependencies or redistributable assets change.
