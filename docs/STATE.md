# RPTP project state — Gate 0 / B1a

- **Snapshot date:** 2026-10-21
- **Remote repository:** [RidTheWann/RPTP-Project](https://github.com/RidTheWann/RPTP-Project), public, default branch `main`.
- **Latest previously verified implementation commit:** `23892c6` — `feat: publish Gate 0 native recompilation spike`.
- **Active phase:** Gate 0 technical spike completed; formal owner review pending. B1a foundation decisions are recorded; B1b is the next implementation phase after clean-room review.
- **License:** `GPL-3.0-or-later` selected by the project owner on 2026-10-21 for original RPTP project material. Third-party components retain their own licenses and notices.
- **Architecture:** from-scratch static ahead-of-time recompilation of supported Emotion Engine code to C++, with a native Windows x64 runtime planned.
- **CLI/log/error language:** English.
- **Build output:** local only; do not commit build directories or Python cache.

## Verified on Windows x64 / MSVC

Command:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-msvc.ps1
```

Recorded output:

- Report status: `PASS_LOCAL_DIFFERENTIAL_SPIKE`.
- Compiler: MSVC x64, version `19.51.36260.0`.
- Flags: `/std:c++20 /EHsc /W4 /WX /permissive- /utf-8`.
- Artifact guard: passed.
- `windows_msvc_verified`: `true`.
- `native_matches_oracle`: `true`.
- Unit tests: 12 passed.
- Synthetic ELF: 28 instructions; executed trace: 22 steps.
- Fixture SHA-256: `b21f1f7793236d1ccba7308cc82f42d9f89915c87c0b037c46d8170f28349ca9`.
- Generated C++ SHA-256: `5316e0f51ba8b1fa1252e409f38cb9ac7db7606fee17b28ef0dcf1be162ae795`.
- The local report is generated at `build/gate0-msvc/report.json`; it must remain out of version control.

## Verified on Linux host toolchains

- 12 unit tests passed.
- Artifact guard passed; only the manifest-registered synthetic ELF fixture was allowed.
- GCC 14.2.0 and Clang 17.0.0 host builds passed the differential spike.
- Repeated runs produced the same fixture and generated-C++ hashes.
- The tested native program matched the oracle's full tested state and execution trace for the supported subset.

## What the evidence does and does not mean

The spike covers a synthetic ELF32/EM_MIPS fixture and only `ADDIU`, `ADDU`, `LW`, `SW`, `BEQ`, `BNE`, `J`, `JAL`, `JR` and `NOP`, including tested delay-slot behavior.

It does **not** establish complete R5900 semantics, retail ISO compatibility, booting a commercial game, or implementation of PS2 kernel services, VU, GS, IOP, CDVD, audio, controller, memory card, timing or save-state behavior. `PASS_LOCAL_DIFFERENTIAL_SPIKE` is a narrow technical result, not a compatibility claim.

## Open decisions and blockers

1. **Formal Gate 0 review:** human owner must review the gate criteria and record the disposition.
2. **Clean-room/source exposure:** prior technical material exposure is documented in [REFERENCES.md](REFERENCES.md) and [ADR-0001](DECISIONS/ADR-0001-foundation-and-clean-room.md). A historical exposure cannot be erased. The owner must decide whether any affected area requires quarantine, restart or another explicit handling before expanding it.
3. **Renderer:** no renderer has been selected or tested; ADR-0002 remains a plan.
4. **Dependencies:** record versions, licenses and required notices before introducing or vendoring third-party code.
5. **Master prompt:** the exact full text of master prompt v1.2 was not available to the execution runtime; this limitation is recorded in [EXECUTION_CONTEXT.md](EXECUTION_CONTEXT.md).

## Next steps

1. Owner review of the historical source-exposure record and explicit clean-room decision.
2. Owner review and formal disposition of Gate 0.
3. After the above, begin B1b with CMake/toolchain baseline, CI, CLI diagnostics and dependency/license checks.

## Handoff

Read [README.md](../README.md), [EXECUTION_CONTEXT.md](EXECUTION_CONTEXT.md), [ADR-0001](DECISIONS/ADR-0001-foundation-and-clean-room.md), [REFERENCES.md](REFERENCES.md), [RISKS.md](RISKS.md) and [ROADMAP.md](ROADMAP.md) before expanding implementation. Keep every feature claim tied to evidence; do not infer full PS2 compatibility from this spike.
