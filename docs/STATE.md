# RPTP project state — Gate 0 technical spike passed; formal disposition pending

- **Snapshot date:** 2026-10-21
- **Remote repository:** RidTheWann/RPTP-Project, public, default branch main.
- **Current main:** `371cec896095738ff16b9a81460b8b183063eae3`; the latest RPTP CI run on this commit is green.
- **Architecture:** from-scratch static ahead-of-time recompilation of supported Emotion Engine code to C++, plus a native Windows x64 runtime planned.
- **License:** GPL-3.0-or-later is recorded as the owner's selected project license in ADR-0001. No new owner confirmation was supplied for this reconciliation session, and no license decision was changed here.
- **CLI/log/error language:** English.
- **Build outputs:** local only; do not commit build directories, Python caches or generated binaries.

## Single current status

- **Gate 0 technical spike:** passed on Windows x64/MSVC and on the recorded Linux host toolchains. Formal Gate 0 disposition remains pending owner review.
- **B1b repository/toolchain baseline:** CMake presets, the RPTP doctor, CTest targets and Windows/Linux CI are present. CI is green on current main, and the Windows preset passed locally in this session. A clean-checkout re-run remains open.
- **B1c ISO inspector prototype:** implemented and covered by synthetic valid/malformed-input tests. It is not validated against real retail ISO layouts and does not establish broad disc compatibility.
- **Owner decisions still open:** formal Gate 0 review, clean-room/source-exposure handling, and explicit license confirmation for this session.

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

## Windows x64/MSVC evidence

Command:

    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-msvc.ps1

- Report status: PASS_LOCAL_DIFFERENTIAL_SPIKE.
- Compiler: MSVC x64, version 19.44.35227 (cl 14.44.35207 toolset). The earlier 19.51.36260.0 value in this document did not match the current verified environment and has been corrected.
- Flags: /std:c++20 /EHsc /W4 /WX /permissive- /utf-8.
- Artifact guard: passed.
- windows_msvc_verified: true.
- native_matches_oracle: true.
- Original Gate 0 unit tests: 12 passed.
- Synthetic ELF: 28 instructions; executed trace: 22 steps.
- Fixture SHA-256: b21f1f7793236d1ccba7308cc82f42d9f89915c87c0b037c46d8170f28349ca9.
- Generated C++ SHA-256: 5316e0f51ba8b1fa1252e409f38cb9ac7db7606fee17b28ef0dcf1be162ae795.
- The local report is preserved as sanitized evidence at `evidence/windows-msvc/report.json`; the ignored build copy remains at `build/gate0-msvc/report.json`.

## Linux host toolchain evidence

- Recorded host evidence (not rerun in this session): 12 original Gate 0 tests passed; the artifact guard passed; GCC 14.2.0 and Clang 17.0.0 builds passed the differential spike; repeated runs reproduced the fixture and generated-C++ hashes.
- The Linux/GCC CI job on current main completed successfully in run `39561754883`.

## Scope and blockers

The spike covers a synthetic ELF32/EM_MIPS fixture and only ADDIU, ADDU, LW, SW, BEQ, BNE, J, JAL, JR and NOP, including tested delay-slot behavior. It does **not** establish complete R5900 semantics, retail ISO compatibility, booting a commercial game, or implementation of PS2 kernel services, VU, GS, IOP, CDVD, audio, controller, memory card, timing or save-state behavior.

1. **Formal Gate 0 review:** the human owner must review the gate's criteria and record the formal disposition.
2. **Clean-room/source exposure:** prior technical exposure is documented in REFERENCES.md and ADR-0001. A historical exposure cannot be erased. The owner must decide whether affected areas require quarantine, restart or other explicit handling before expanding recompiler/runtime implementation.
3. **License confirmation:** ADR-0001 records the owner's GPL-3.0-or-later selection, but this session did not receive a fresh confirmation. The owner must confirm before any license-related file changes, including SPDX headers.
4. **Renderer:** no renderer has been selected or tested; ADR-0002 remains a plan.
5. **Dependencies:** no new runtime dependency was introduced by the repository/toolchain baseline. Continue to record license, version and required notices before adding or vendoring dependencies.
6. **Master prompt:** the exact full text of revised master prompt v1.2 was not available to the earlier runtime; known amendments are summarized rather than represented as a verbatim copy.

## Next steps

1. Owner confirms the license decision and records formal Gate 0 and clean-room dispositions.
2. Re-run the Windows preset from a clean checkout to close the remaining B1b criterion.
3. Validate the ISO inspector only against owner-authorized discs, recording hashes and outcomes without committing game images.
4. Continue only with the next owner-approved phase; do not infer game compatibility from the synthetic spike.
