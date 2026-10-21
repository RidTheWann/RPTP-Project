# RPTP project state — Gate 0 technical spike passed; formal disposition pending

- **Snapshot date:** 2026-10-21
- **Remote repository:** RidTheWann/RPTP-Project, public, default branch main.
- **Current main:** `371cec896095738ff16b9a81460b8b183063eae3`; the latest RPTP CI run on this commit is green.
- **Architecture:** from-scratch static ahead-of-time recompilation of supported Emotion Engine code to C++, plus a native Windows x64 runtime planned.
- **License:** GPL-3.0-or-later was confirmed by the owner on 2026-10-21. The decision remains recorded in ADR-0001; no license decision was changed here.
- **CLI/log/error language:** English.
- **Build outputs:** local only; do not commit build directories, Python caches or generated binaries.

## Single current status

- **Gate 0 technical spike:** passed on Windows x64/MSVC and on the recorded Linux host toolchains. Formal Gate 0 disposition remains pending owner review.
- **B1b repository/toolchain baseline:** CMake presets, the RPTP doctor, CTest targets and Windows/Linux CI are present. CI is green on current main only. The Windows preset passed locally in this checkout and in a clean clone at commit `83459c1`; the branch itself has not run CI, so B1b is not passed.
- **B1c ISO inspector prototype:** implemented and covered by synthetic valid/malformed-input tests. It is not validated against real retail ISO layouts and does not establish broad disc compatibility.
- **Owner decisions still open:** formal Gate 0 review and clean-room/source-exposure handling.

## Verification performed on 2026-10-21

The commands below were run from Developer PowerShell for Visual Studio 2022, x64, in this checkout:

    python tools/rptp_doctor.py
    cmake --preset windows-msvc
    cmake --build --preset windows-msvc
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-msvc.ps1
    python -m unittest discover -s tests -v

- RPTP doctor: PASS (Python 3.11.9, MSVC, CMake, Ninja, git and artifact guard).
- CMake configure: PASS; C++ compiler identified as MSVC 19.44.35227.0.
- CMake build/CTest: PASS; 3 of 3 tests passed (`artifact_guard`, `python_unit_tests`, `gate0_differential_spike`).
- Python unit tests: PASS; 34 tests in total (12 original Gate 0, 16 ISO inspector, 6 doctor).
- GitHub Actions run `39561754883` on main commit `371cec8`: Windows x64/MSVC and Linux/GCC jobs both completed successfully.

### Clean-checkout local run (C2)

On 2026-10-21 the branch was cloned into `<temp>\rptp-clean` from the local repository at commit `83459c1`, outside the working tree. From Developer PowerShell for Visual Studio 2022 (x64), in that clean clone:

    python tools/rptp_doctor.py
    cmake --preset windows-msvc
    cmake --build --preset windows-msvc
    python -m unittest discover -s tests -v

- RPTP doctor: PASS.
- CMake configure: PASS; MSVC `19.44.35227.0`, toolset `14.44.35207`.
- CMake build/CTest: PASS; 3 of 3 tests passed.
- Python unit tests: PASS; 34 tests.
- Generated Gate 0 report: `PASS_LOCAL_DIFFERENTIAL_SPIKE`, `windows_msvc_verified: true`, `native_matches_oracle: true`, 22 trace steps; fixture and generated-C++ SHA-256 values match the recorded values.
- This is a **clean-checkout local run**, not a substitute for CI on this branch. The branch was not pushed, so no branch CI result exists.

## Windows x64/MSVC evidence

Command:

    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-msvc.ps1

- Report status: PASS_LOCAL_DIFFERENTIAL_SPIKE.
- Compiler: MSVC x64, version 19.44.35227 (cl 14.44.35207 toolset).
- Flags: /std:c++20 /EHsc /W4 /WX /permissive- /utf-8.
- Artifact guard: passed.
- windows_msvc_verified: true.
- native_matches_oracle: true.
- Original Gate 0 unit tests: 12 passed.
- Synthetic ELF: 28 instructions; executed trace: 22 steps.
- Fixture SHA-256: b21f1f7793236d1ccba7308cc82f42d9f89915c87c0b037c46d8170f28349ca9.
- Generated C++ SHA-256: 5316e0f51ba8b1fa1252e409f38cb9ac7db7606fee17b28ef0dcf1be162ae795.
- The local report is preserved as sanitized evidence at `evidence/windows-msvc/report.json`; the ignored build copy remains at `build/gate0-msvc/report.json`.

## MSVC compiler version history

Each run is recorded separately; older notes are not rewritten as if they were current evidence.

- **Earlier recorded note, commit `e3d5ff8` (2026-10-21 05:43 +0700):** MSVC x64 version `19.51.36260.0` was reported for `scripts/run-msvc.ps1`. The note does not record the run date or environment, and no matching report exists in repository history. Status: **reported, not verified (dilaporkan, belum terverifikasi)**.
- **Reconciliation session C1, 2026-10-21, local checkout:** Windows 11 x64, Developer PowerShell for Visual Studio 2022 Build Tools 17.14.32 x64, `cl` 19.44.35227 for x64, toolset `14.44.35207`; CMake identified `19.44.35227.0`. Status: **Terverifikasi** by `evidence/windows-msvc/report.json` and `commands.txt`.
- **Reconciliation session C2, 2026-10-21, clean clone at `83459c1`:** Windows 11 x64, Developer PowerShell for Visual Studio 2022 Build Tools 17.14.32 x64, `cl` 19.44.35227 for x64, toolset `14.44.35207`; CMake identified `19.44.35227.0`; doctor PASS, 3/3 CTest targets passed, 34 Python tests passed. Status: **Terverifikasi** as a local clean-checkout run, not as branch CI.

The earlier `19.51.36260.0` value and the verified `19.44.35227` value are therefore separate runs, not a replacement of one historical note by another. The report JSON does not contain a separate `cl` version field; it records the compiler executable path for toolset `14.44.35207`. The matching `cl` banner version from the same environment is `19.44.35227`, as recorded in `commands.txt`.

## Linux host toolchain evidence

- Recorded host evidence (not rerun in this session): 12 original Gate 0 tests passed; the artifact guard passed; GCC 14.2.0 and Clang 17.0.0 builds passed the differential spike; repeated runs reproduced the fixture and generated-C++ hashes.
- The Linux/GCC CI job on current main completed successfully in run `39561754883`.

## Scope and blockers

The spike covers a synthetic ELF32/EM_MIPS fixture and only ADDIU, ADDU, LW, SW, BEQ, BNE, J, JAL, JR and NOP, including tested delay-slot behavior. It does **not** establish complete R5900 semantics, retail ISO compatibility, booting a commercial game, or implementation of PS2 kernel services, VU, GS, IOP, CDVD, audio, controller, memory card, timing or save-state behavior.

1. **Formal Gate 0 review:** the human owner must review the gate's criteria and record the formal disposition.
2. **Clean-room/source exposure:** prior technical exposure is documented in REFERENCES.md and ADR-0001. A historical exposure cannot be erased. The owner must decide whether affected areas require quarantine, restart or other explicit handling before expanding recompiler/runtime implementation.
3. **License confirmation (resolved):** the owner confirmed GPL-3.0-or-later on 2026-10-21; SPDX headers were added to covered project source, build and workflow files.
4. **Renderer:** no renderer has been selected or tested; ADR-0002 remains a plan.
5. **Dependencies:** no new runtime dependency was introduced by the repository/toolchain baseline. Continue to record license, version and required notices before adding or vendoring dependencies.
6. **Master prompt:** the exact full text of revised master prompt v1.2 was not available to the earlier runtime; known amendments are summarized rather than represented as a verbatim copy.

## Next steps

1. Owner records formal Gate 0 and clean-room dispositions.
2. Push the branch and require green CI before treating B1b as passed; the clean-checkout local run is not branch CI.
3. Validate the ISO inspector only against owner-authorized discs, recording hashes and outcomes without committing game images.
4. Continue only with the next owner-approved phase; do not infer game compatibility from the synthetic spike.
