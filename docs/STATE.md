# RPTP project state — Gate 0 complete as a technical spike

- **Snapshot date:** 2026-10-21
- **Remote repository:** RidTheWann/RPTP-Project, public, default branch main.
- **Last previously verified project milestone:** commit 23892c6 published the Gate 0 implementation and evidence; cover and factual documentation corrections were subsequently committed.
- **Active work:** B1b repository/toolchain baseline.
- **Gate 0 technical spike:** passed on Windows x64/MSVC and Linux host toolchains.
- **Formal Gate 0 disposition:** pending human review.
- **License:** GPL-3.0-or-later selected for original RPTP material. Third-party dependencies retain their own licenses and notices.
- **Architecture:** from-scratch static ahead-of-time recompilation of supported Emotion Engine code to C++, plus a native Windows x64 runtime planned.
- **CLI/log/error language:** English.
- **Build outputs:** local only; do not commit build directories, Python caches or generated binaries.

## Windows x64 / MSVC evidence already recorded

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
- The detailed report remains a local ignored build artifact at build/gate0-msvc/report.json; it is not committed.

## Linux host toolchain evidence

- 12 original Gate 0 tests passed.
- Artifact guard passed; only the manifest-registered synthetic ELF fixture was allowed.
- GCC 14.2.0 and Clang 17.0.0 host builds passed the differential spike.
- Repeated runs produced the same fixture and generated-C++ hashes.
- The tested native program matched the oracle's tested state and execution trace for the supported subset.

## B1b infrastructure added in this revision

- CMakeLists.txt: CMake targets for rptp-doctor and rptp-ci.
- CMakePresets.json: host and Windows/MSVC presets.
- tools/rptp_doctor.py: environment checks, actionable toolchain failures and artifact-guard invocation.
- tests/test_rptp_doctor.py: deterministic checks for Python version, compiler detection, missing tools and missing project files.
- .github/workflows/ci.yml: Windows x64/MSVC and Linux/GCC jobs.
- Automated CI on this revision: pending; do not mark B1b pass criteria complete until both jobs pass.

## Scope and blockers

The spike covers a synthetic ELF32/EM_MIPS fixture and only ADDIU, ADDU, LW, SW, BEQ, BNE, J, JAL, JR and NOP, including tested delay-slot behavior. It does **not** establish complete R5900 semantics, retail ISO compatibility, booting a commercial game, or implementation of PS2 kernel services, VU, GS, IOP, CDVD, audio, controller, memory card, timing or save-state behavior.

1. **Formal Gate 0 review:** human owner must review the gate's criteria and record the formal disposition.
2. **Clean-room/source exposure:** prior technical exposure is documented in REFERENCES.md and ADR-0001. A historical exposure cannot be erased. The owner must decide whether affected areas require quarantine, restart or other explicit handling before expanding recompiler/runtime implementation.
3. **Renderer:** no renderer has been selected or tested; ADR-0002 remains a plan.
4. **Dependencies:** no new runtime dependency is introduced by the B1b scaffold. Continue to record license, version and required notices before adding or vendoring dependencies.
5. **Master prompt:** the exact full text of revised master prompt v1.2 was not available to the earlier runtime; known amendments are summarized rather than represented as a verbatim copy.

## Next steps

1. Inspect CI results for the new Windows/MSVC and Linux/GCC jobs, fixing failures from actual logs.
2. Owner reviews the historical source-exposure record and records the clean-room decision.
3. Owner performs formal Gate 0 review.
4. After those reviews, continue with the next approved phase; do not infer game compatibility from the synthetic spike.
