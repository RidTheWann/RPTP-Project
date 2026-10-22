# Gate 0 — decision evidence package

- **Status:** **Accepted — technical pass for the narrow synthetic differential-spike scope, recorded 2026-10-23 by explicit owner delegation.** This is a technical scope disposition, not a clean-room certification, independent review or legal opinion.
- **Prepared:** 2026-10-22
- **Disposition recorded:** 2026-10-23
- **Authority:** The project owner explicitly delegated recording of this technical pass to the agent on 2026-10-23. The owner remains the decision owner. The independent provenance review required before product release is separate and is tracked in [PROVENANCE_PLAN.md](PROVENANCE_PLAN.md).
- **Scope:** the synthetic ELF32/EM_MIPS differential spike and its reproducible checks. This package does not cover retail executables, the full R5900 ISA, the PS2 runtime, rendering, audio, input, storage or game compatibility.

## Disposition

Gate 0 is accepted as a **technical pass for the narrow synthetic scope only**. The accepted claim is limited to the synthetic ELF32/EM_MIPS fixture, its bounds-checked parser, the tested instruction subset, deterministic C++20 generation, compilation with MSVC on Windows x64, and native-versus-oracle equality for the tested register state, memory, stop PC and executed-PC trace.

The disposition does **not** accept or imply:

- full R5900 correctness, EE-specific floating-point/MMI behavior, COP0, exceptions, interrupts or timing;
- retail PS2 ELF or ISO support, extraction, boot, playability or compatibility with any commercial game;
- EE kernel, syscalls, IOP, DMA, VU, GS, SPU2, CDVD, controller or memory-card behavior;
- clean-room certification, independent provenance review or legal clearance; or
- a Gate 2, Gate 3 or later disposition. Gate 2 remains open and read-only.

## What the spike tested

The spike generates a synthetic ELF32/EM_MIPS fixture, parses its executable segment with bounds checks, decodes a controlled instruction subset, generates C++20, compiles it with MSVC, and compares the native result with the independent Python oracle. The subset is limited to ADDIU, ADDU, LW, SW, BEQ, BNE, J, JAL, JR and NOP, including delay-slot rules. Unsupported opcodes and malformed control flow fail explicitly.

## Recorded evidence

The results below come from the append-only [verification log](VERIFICATION_LOG.md). Historical rows retain their original dates and are not rewritten here.

| Check | Recorded result | Evidence |
|---|---|---|
| Windows x64/MSVC spike | PASS_LOCAL_DIFFERENTIAL_SPIKE; `windows_msvc_verified: true`; `native_matches_oracle: true` | [Windows x64/MSVC evidence](VERIFICATION_LOG.md#windows-x64msvc-evidence) |
| Synthetic program | 28 instructions; 22 executed trace steps | Same section |
| Compiler flags | `/std:c++20 /EHsc /W4 /WX /permissive- /utf-8` | Same section |
| Fixture SHA-256 | `b21f1f7793236d1ccba7308cc82f42d9f89915c87c0b037c46d8170f28349ca9` | Same section and [fixture manifest](../tests/fixtures/MANIFEST) |
| Generated C++ SHA-256 | `5316e0f51ba8b1fa1252e409f38cb9ac7db7606fee17b28ef0dcf1be162ae795` | Same section |
| Original Gate 0 unit tests | 12 passed at the time of the original spike | Same section |
| Linux host toolchains | GCC 14.2.0 and Clang 17.0.0 builds passed; hashes reproduced | [Linux host toolchain evidence](VERIFICATION_LOG.md#linux-host-toolchain-evidence) |
| Published CI baseline | Windows x64/MSVC and Linux/GCC jobs passed for the later published tip `9c4f675` (run `39860776782`); the Gate 0 fixture and evidence are unchanged | [Current status](STATE.md) |

The detailed spike report is a local, ignored build artifact at `build/gate0-msvc/report.json`; it is not committed. Regeneration is the reproducibility mechanism.

## Reproduction commands

From the repository root in a Visual Studio developer environment:

    python tools/rptp_doctor.py
    cmake --preset windows-msvc
    cmake --build --preset windows-msvc
    ctest --test-dir build/cmake-msvc --output-on-failure
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-msvc.ps1
    python -m unittest tests.test_gate0_spike -v

The build preset's `rptp-ci` target runs the doctor and the test suite. These commands regenerate the fixture and generated source; equality of both SHA-256 values across runs is part of the determinism check. A local run is not CI evidence. CI evidence exists only for the published commit identified above.

## Explicit limits

- The fixture is synthetic. No retail executable is executed by this spike.
- The instruction subset is narrow and is not a claim of R5900 correctness beyond those instructions.
- The spike does not implement or prove EE kernel, IOP, DMA, VU, GS, SPU2, CDVD or timing behavior.
- The artifact guard checks the repository working tree, not every possible host-side artifact.
- The build/CI/doctor layer is `Review required` in [CLEAN_ROOM_AUDIT.md](CLEAN_ROOM_AUDIT.md); this package does not independently certify its provenance.
- No runtime or renderer is selected; ADR-0002 remains a plan only.
- Gate 2 remains open, read-only and not passed under [ADR-0004](DECISIONS/ADR-0004-gate2-read-only-scope.md).

## Clean-room and provenance considerations

Gate 0 work predates the sealed-source policy recorded in [ADR-0003](DECISIONS/ADR-0003-sealed-source-clean-room-policy.md). Prior exposure is documented in [REFERENCES.md](REFERENCES.md) and cannot be erased. The owner's policy requires affected work to be independently derived; this technical differential pass does not by itself resolve provenance concerns.

An execution plan for traceability, re-derivation and independent review is recorded in [PROVENANCE_PLAN.md](PROVENANCE_PLAN.md). Recording that plan is not a clean-room certification and does not replace the independent review that must occur before product release.

## Decision record

The owner's 2026-10-23 instruction delegated and selected the first option: **record a formal technical pass for the narrow synthetic scope**, accepting the stated limits and keeping provenance follow-up separate.

The other options were not selected: the disposition is not being held pending independent provenance review, and the technical evidence was not rejected or required to be reworked. The owner has not recorded a clean-room disposition, a Gate 2 disposition or any commercial-compatibility claim.
