# RPTP project state — Gate 0 / B1a

- **Snapshot date:** 2026-10-21
- **Remote repository:** `RidTheWann/RPTP-Project` was verified public, empty (`size: 0`), with default branch `main` during the earlier check. Verify remote state again before pushing.
- **Local project folder:** `D:\RPTP-Project` was not a Git working tree at the latest local check (`Test-Path .git` returned `False`). Do not run Git commit/push from that folder until it is connected to a real clone.
- **Active gate:** Gate 0 — foundation research and spike.
- **Technical spike status:** **Passed on Windows x64/MSVC and Linux host toolchains.**
- **Formal Gate 0 disposition:** Pending human review.
- **Project license:** `GPL-3.0-or-later` selected by the project owner on 2026-10-21; the root `LICENSE` in this update package contains the full GNU GPL version 3 text. Review third-party licenses separately. Historical source exposure and clean-room review remain separate concerns.
- **CLI/log/error language:** English (human decision recorded 2026-10-21).
- **Architecture choice:** From-scratch static ahead-of-time recompilation; no browser output.

## Verified on Linux host toolchains

1. `python3 -m unittest discover -s tests -v` — **12 tests passed**.
2. `python3 tools/check_forbidden_artifacts.py --root .` — passed; only the manifest-registered synthetic ELF fixture is allowed.
3. `python3 tools/rptp_gate0_spike.py --out build/gate0 --compiler g++` — passed on Linux x86-64 with GCC 14.2.0.
4. Repeating the spike in a separate output directory produced the same fixture SHA-256 (`b21f1f7793236d1ccba7308cc82f42d9f89915c87c0b037c46d8170f28349ca9`) and generated C++ SHA-256 (`5316e0f51ba8b1fa1252e409f38cb9ac7db7606fee17b28ef0dcf1be162ae795`).
5. An additional host build with Clang 17.0.0 also passed the differential spike; this does not substitute for MSVC/Windows testing.
6. The native trace has 22 executed steps and matches the reference interpreter's full tested state and trace for the supported subset.
7. Negative tests reject a truncated ELF, wrong machine ID, unsupported opcode, unregistered ELF, manifest allowlisting outside `tests/fixtures/`, and ISO artifacts.

## Latest Windows verification

- **Command:** `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-msvc.ps1`
- **Report status:** `PASS_LOCAL_DIFFERENTIAL_SPIKE`.
- **Compiler:** MSVC x64, version `19.51.36260.0`.
- **Compile flags:** `/std:c++20 /EHsc /W4 /WX /permissive- /utf-8`.
- **Artifact guard:** passed.
- **`windows_msvc_verified`:** `true`.
- **`native_matches_oracle`:** `true`.
- **Unit tests:** 12 passed.
- **Synthetic ELF:** 28 instructions; executable trace: 22 steps.
- **Fixture SHA-256:** `b21f1f7793236d1ccba7308cc82f42d9f89915c87c0b037c46d8170f28349ca9`.
- **Generated C++ SHA-256:** `5316e0f51ba8b1fa1252e409f38cb9ac7db7606fee17b28ef0dcf1be162ae795`.
- The report is at `build/gate0-msvc/report.json`. Build outputs should remain local and must not be committed.

## Not verified / blockers

- Formal Gate 0 acceptance still requires human review against the gate's complete criteria; `PASS_LOCAL_DIFFERENTIAL_SPIKE` is the status of this narrow technical spike, not the whole project.
- The spike covers only a synthetic ELF32/EM_MIPS fixture and ADDIU, ADDU, LW, SW, BEQ, BNE, J, JAL, JR and NOP, including the tested delay-slot behavior. It does not prove full R5900 accuracy, parse a retail ISO, boot a commercial game, or implement PS2 kernel services, VU, GS, IOP, audio or other hardware behavior.
- Historical source exposure remains recorded in `docs/REFERENCES.md` and ADR-0001. Technical README, release and issue/PR descriptions for PS2Recomp were viewed. For PS2 Web Recomp, technical README, repository tree, top-level `CMakeLists.txt`, `scripts/port.sh`, `scripts/windows.py` and the top-level MIT license were viewed. The recorded accessible output does not show runtime `.cpp` implementation fetched. A historical exposure cannot be erased; the project owner must review whether the exposure is compatible with the intended clean-room process.
- Renderer: no renderer code has been tested or selected; ADR-0002 remains a plan.
- The exact full text of master prompt v1.2 was not available to the execution runtime; the attached file was v1.0 and the artifact URL was inaccessible. The stated v1.2 amendments were applied as described by the user, and this limitation is recorded in `docs/EXECUTION_CONTEXT.md`.
- Selecting GPL-3.0-or-later does not resolve third-party dependency licensing or the documented clean-room review. Record dependency versions, licenses and required notices before adding/vendoring them.

## Next steps (maximum three)

1. Human owner reviews the historical source-exposure record and decides whether to proceed, quarantine affected areas, or restart any affected work.
2. Human owner reviews all Gate 0 criteria and records the formal disposition; do not claim whole-gate acceptance based only on the narrow spike.
3. Clone the empty public repository into a fresh Git working tree before any Git operation. Publish only the documentation/license update until the implementation publication decision is resolved.

## Handoff

The spike is intentionally small and self-contained. Read `README.md`, `docs/EXECUTION_CONTEXT.md`, `docs/DECISIONS/ADR-0001-foundation-and-clean-room.md`, `docs/REFERENCES.md` and `docs/RISKS.md` before continuing. Do not infer full PS2 compatibility from this Gate 0 spike pass.
