# RPTP project state — Gate 0 technical spike passed; formal disposition pending

- **Snapshot date:** 2026-10-21
- **Remote repository:** RidTheWann/RPTP-Project, public, default branch main.
- **Current main:** `371cec896095738ff16b9a81460b8b183063eae3`; the latest RPTP CI run on this commit is green.
- **Reconciliation branch:** `chore/post-gate0-reconcile`; it has local Gate 0 reconciliation, environment-alignment and ISO inspector hardening commits. It has not been pushed, so no branch CI exists.
- **Architecture:** from-scratch static ahead-of-time recompilation of supported Emotion Engine code to C++, plus a native Windows x64 runtime planned.
- **License:** GPL-3.0-or-later was confirmed by the owner on 2026-10-21. The decision remains recorded in ADR-0001; no license decision was changed here.
- **CLI/log/error language:** English.
- **Build outputs:** local only; do not commit build directories, Python caches or generated binaries.

## Single current status

- **Gate 0 technical spike:** passed on Windows x64/MSVC and on the recorded Linux host toolchains. Formal Gate 0 disposition remains pending owner review.
- **B1b repository/toolchain baseline:** CMake presets, the RPTP doctor, CTest targets and Windows/Linux CI are present. CI is green on current main only. The Windows preset passed locally on the work laptop and in a clean clone at commit `83459c1`; the branch itself has not run CI, so B1b is not passed.
- **B1c ISO inspector prototype / Gate 2 synthetic hardening:** single-volume PVD parsing, root `SYSTEM.CNF` regular single-extent validation, BOOT path resolution, PVD/root/boot metadata, SHA-256, ELF PT_LOAD checks, warnings and an explicit error taxonomy are implemented. 33 ISO inspector tests and 52 total tests pass. Real retail ISO layouts, multi-extent support, safe extraction boundaries and broad disc compatibility remain unverified.
- **Owner decisions still open:** formal Gate 0 review and clean-room/source-exposure handling.

## Verification performed on 2026-10-21

The commands below were run from Developer PowerShell x64 on the work laptop. The C1/C2/C3 runs predate the work-laptop toolchain alignment; the post-alignment run uses Visual Studio 2026 Build Tools 18.11.1 and Python 3.13.16. The canonical home-PC software/version reference is the record at commit `371cec8`; work-laptop runs are separate and do not replace it.

    python tools/rptp_doctor.py
    cmake --preset windows-msvc
    cmake --build --preset windows-msvc
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-msvc.ps1
    python -m unittest discover -s tests -v

- RPTP doctor: PASS.
- CMake configure: PASS; C++ compiler identified.
- CMake build/CTest: PASS; 3 of 3 tests passed (`artifact_guard`, `python_unit_tests`, `gate0_differential_spike`).
- Python unit tests: PASS; 34 tests in total (12 original Gate 0, 16 ISO inspector, 6 doctor).
- GitHub Actions run `39561754883` on main commit `371cec8`: Windows x64/MSVC and Linux/GCC jobs both completed successfully.

### Work-laptop clean-checkout run (C2)

On 2026-10-21 the branch was cloned into `<temp>\rptp-clean` from the local repository at commit `83459c1`, outside the working tree. From Developer PowerShell for Visual Studio 2022 (x64), in that clean clone:

    python tools/rptp_doctor.py
    cmake --preset windows-msvc
    cmake --build --preset windows-msvc
    python -m unittest discover -s tests -v

- RPTP doctor: PASS.
- CMake configure: PASS.
- CMake build/CTest: PASS; 3 of 3 tests passed.
- Python unit tests: PASS; 34 tests.
- Generated Gate 0 report: `PASS_LOCAL_DIFFERENTIAL_SPIKE`, `windows_msvc_verified: true`, `native_matches_oracle: true`, 22 trace steps; fixture and generated-C++ SHA-256 values match the recorded values.
- This is a **clean-checkout local run**, not a substitute for CI on this branch. The branch was not pushed, so no branch CI result exists.

### Work-laptop license-header verification (C3)

After adding the SPDX headers and `tests/test_license_headers.py`, the same doctor, configure, build/CTest and unittest commands were run in the working checkout:

- RPTP doctor: PASS.
- CMake configure: PASS.
- CMake build/CTest: PASS; 3 of 3 tests passed.
- Python unit tests: PASS; 35 tests (12 Gate 0, 16 ISO inspector, 6 doctor, 1 license-header check).
- `git grep -n -i -E 'D:\\|C:\\Users' -- docs evidence README.md` matched only the documented generic example paths in README.md and ISO_INSPECTOR.md; no personal path was found.

### Work-laptop post-alignment verification (VS 2026)

The work laptop was aligned to the `371cec8` software reference and the checks were rerun on 2026-10-21:

- Visual Studio 2026 Build Tools 18.11.1; MSVC x64 19.51.36260.0, toolset 14.51.36231.
- Python 3.13.16; CMake 4.1.0; Ninja 1.13.2; Windows 11 SDK 10.0.26100.
- Required components installed: Desktop C++ Build Tools workload (`Microsoft.VisualStudio.Workload.VCTools`), MSVC x64/x86 latest, Windows 11 SDK, and C++ CMake tools.
- Optional components not installed: C++ ATL, C++ Build Insights, Just-In-Time debugger, C++ profiling tools.
- RPTP doctor: PASS (Python 3.13.16, MSVC 19.51.36260, CMake, Ninja, git, artifact guard).
- CMake configure: PASS; compiler identified as MSVC 19.51.36260.0.
- CMake build/CTest: PASS; 3 of 3 tests passed.
- Python unit tests: PASS; 52 tests (12 Gate 0, 33 ISO inspector, 6 doctor, 1 license-header check).
- Gate 0 report: `PASS_LOCAL_DIFFERENTIAL_SPIKE`, `windows_msvc_verified: true`, `native_matches_oracle: true`, 22 trace steps; local ignored reports at `build/cmake-msvc/gate0/report.json` and `build/gate0-msvc/report.json`.
- Branch CI has not run; B1b is still not passed.

### ISO inspector hardening verification (Gate 2 synthetic scope)

- CTest: PASS; 3 of 3 targets after the inspector changes (`artifact_guard`, `python_unit_tests`, `gate0_differential_spike`).
- Full Python suite: PASS; 52 tests.
- ISO inspector suite: PASS; 33 tests covering PVD/root metadata, single-volume enforcement, `SYSTEM.CNF` directory/multi-extent rejection, BOOT path resolution, ELF PT_LOAD bounds/size/alignment validation, warnings, deterministic reports, CLI JSON success/error and a 250-case seeded mutation smoke test.
- Determinism: repeated inspection of the same bytes produces identical JSON.
- Scope: synthetic images only. No retail ISO, multi-extent merging, extraction, emulation or recompilation was tested.

## Windows x64/MSVC evidence

Command:

    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-msvc.ps1

- Report status: PASS_LOCAL_DIFFERENTIAL_SPIKE.
- Compiler: MSVC x64, version 19.51.36260.0.
- Flags: /std:c++20 /EHsc /W4 /WX /permissive- /utf-8.
- Artifact guard: passed.
- windows_msvc_verified: true.
- native_matches_oracle: true.
- Original Gate 0 unit tests: 12 passed.
- Synthetic ELF: 28 instructions; executed trace: 22 steps.
- Fixture SHA-256: b21f1f7793236d1ccba7308cc82f42d9f89915c87c0b037c46d8170f28349ca9.
- Generated C++ SHA-256: 5316e0f51ba8b1fa1252e409f38cb9ac7db7606fee17b28ef0dcf1be162ae795.
- The detailed report remains a local ignored build artifact at `build/gate0-msvc/report.json`; it is not committed.

## Work-laptop evidence

The sanitized files under `evidence/windows-msvc/` were captured before the work-laptop toolchain alignment. They remain historical local evidence and do not replace the home-PC software reference at commit `371cec8` or the post-alignment report above.

## Home-PC software reference

The home-PC software/version record is the one at commit `371cec8`: MSVC x64 `19.51.36260.0`, with Python 3.10+, CMake 3.25+, Ninja, and a C++20 compiler as documented in README.md and BUILDING_WINDOWS.md.

The work laptop now uses MSVC 19.51.36260.0 and Python 3.13.16. Its runs remain local evidence and do not replace this home-PC record or branch CI.

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
