# Gate 0 — decision evidence package

- **Status:** technical evidence package; **formal Gate 0 disposition pending**. This document does not close the gate and is not a certification.
- **Prepared:** 2026-10-22
- **Owner decision requested:** review the evidence and record the formal Gate 0 disposition.
- **Scope:** the synthetic ELF32/EM_MIPS differential spike and its reproducible checks. This package does not cover retail executables, the full R5900 ISA, the PS2 runtime, rendering, audio, input, storage or game compatibility.

## What the spike tested

The spike generates a synthetic ELF32/EM_MIPS fixture, parses its executable segment with bounds checks, decodes a controlled instruction subset, generates C++20, compiles it with MSVC, and compares the native result with the independent Python oracle. The subset is limited to ADDIU, ADDU, LW, SW, BEQ, BNE, J, JAL, JR and NOP, including delay-slot rules. Unsupported opcodes and malformed control flow fail explicitly.

## Recorded evidence

The following results come from the append-only [verification log](VERIFICATION_LOG.md). They were not rerun while preparing this package.

| Check | Recorded result | Evidence |
|---|---|---|
| Windows x64/MSVC spike | PASS_LOCAL_DIFFERENTIAL_SPIKE; `windows_msvc_verified: true`; `native_matches_oracle: true` | [Windows x64/MSVC evidence](VERIFICATION_LOG.md#windows-x64msvc-evidence) |
| Synthetic program | 28 instructions; 22 executed trace steps | Same section |
| Compiler flags | `/std:c++20 /EHsc /W4 /WX /permissive- /utf-8` | Same section |
| Fixture SHA-256 | `b21f1f7793236d1ccba7308cc82f42d9f89915c87c0b037c46d8170f28349ca9` | Same section and [fixture manifest](../tests/fixtures/MANIFEST) |
| Generated C++ SHA-256 | `5316e0f51ba8b1fa1252e409f38cb9ac7db7606fee17b28ef0dcf1be162ae795` | Same section |
| Original Gate 0 unit tests | 12 passed | Same section |
| Linux host toolchains | GCC 14.2.0 and Clang 17.0.0 builds passed; hashes reproduced | [Linux host toolchain evidence](VERIFICATION_LOG.md#linux-host-toolchain-evidence) |
| CI baseline | Windows x64/MSVC and Linux/GCC jobs passed for published `d334139` (run `39664774001`) | [Current status](STATE.md) |

The detailed spike report is a local, ignored build artifact at `build/gate0-msvc/report.json`; it is not committed. Regeneration is the reproducibility mechanism.

## Reproduction commands

From the repository root in a Visual Studio developer environment:

    python tools/rptp_doctor.py
    cmake --preset windows-msvc
    cmake --build --preset windows-msvc
    ctest --test-dir build/cmake-msvc --output-on-failure
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-msvc.ps1
    python -m unittest tests.test_gate0_spike -v

The build preset's `rptp-ci` target runs the doctor and the test suite. These commands regenerate the fixture and generated source; equality of both SHA-256 values across runs is part of the determinism check. A local run is not CI evidence, and this package does not claim that any later local commit has passed CI.

## Explicit limits

- The fixture is synthetic. No retail executable is executed by this spike.
- The instruction subset is narrow and is not a claim of R5900 correctness beyond those instructions.
- The spike does not implement or prove EE kernel, IOP, DMA, VU, GS, SPU2, CDVD or timing behavior.
- The artifact guard checks the repository working tree, not every possible host-side artifact.
- The build/CI/doctor layer is `Review required` in [CLEAN_ROOM_AUDIT.md](CLEAN_ROOM_AUDIT.md); this package does not independently certify its provenance.
- No runtime or renderer is selected; ADR-0002 remains a plan only.

## Clean-room and provenance considerations

Gate 0 work predates the sealed-source policy recorded in [ADR-0003](DECISIONS/ADR-0003-sealed-source-clean-room-policy.md). Prior exposure is documented in [REFERENCES.md](REFERENCES.md) and cannot be erased. The owner's policy requires affected work to be independently derived; a technical differential pass does not by itself resolve provenance concerns. Updated build provenance and independent contract evidence are separate follow-up work and must not be described as clean-room certification.

## Decision options for the owner

1. **Record a formal technical pass for the narrow synthetic scope**, accepting the stated limits and the separate provenance follow-up.
2. **Keep the disposition pending** until independent provenance review or re-derivation is recorded.
3. **Reject or require rework** if the evidence, scope or provenance is insufficient.

Only the owner may choose and record this disposition. The agent does not recommend treating a local run or this package as a Gate closure.
