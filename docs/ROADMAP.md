# RPTP roadmap — current working copy

## Gate 0 — Foundation research and native spike

**State: partially evidenced; not passed.**

- [x] Write an original synthetic ELF32/EM_MIPS fixture generator.
- [x] Parse ELF header and executable load segment with basic bounds checks.
- [x] Decode an explicit common-MIPS subset and fail on unsupported encodings.
- [x] Run an interpreter oracle and compare full register state, memory, stop PC, and executed-PC trace against generated native C++.
- [x] Check generated source determinism and fixture SHA allowlisting.
- [x] Record permitted public references and historical source exposure.
- [x] Write a renderer comparison plan; renderer selection remains open.
- [ ] Run the generated program under MSVC on Windows x64 and record actual output.
- [ ] Human review and Gate 0 decision.

### Gate 0 pass condition

The same reproducible synthetic ELF must produce generated C++ that compiles and runs on Windows with MSVC and whose complete state/trace matches the oracle. A Linux GCC result is supplemental only. Gate 0 remains not passed until the Windows evidence exists.

## Gate 1 — Repository/toolchain baseline (B1b)

**Blocked until license ADR approval.** Build repository structure, CMake presets, CLI `rptp doctor`, structured logging, CI for MSVC Debug/Release, dependency/license audit, artifact guard, and the live project-state documents. No implementation code should be pushed to the public repository before the license gate is cleared.

## Gate 2 — ISO Inspector

Implement ISO9660 read-only parsing, `SYSTEM.CNF`, executable identification, hashing, safe extraction, error taxonomy, fixture manifest enforcement and parser fuzzing.

## Gate 3 — Recompiler MVP

Implement an instruction catalog with explicit verification status, oracle interpreter, decoder, IR, deterministic C++ generation, static function discovery, unsupported-instruction diagnostics and differential tests. Follow the broad 20–60 person-week initial estimate in `RISKS.md` only as low-confidence planning data.

## Gate 4 — First game vertical slice

- **4a Boot:** startup path, minimum kernel/syscalls, CDVD, IOP and logging.
- **4b Graphics:** first correct reference frame from the native GS path.
- **4c Audio/input/save:** essential sound, controller and memory-card paths.
- **4d Gameplay:** repeatable boot to menu to gameplay; cold boot and save/load checks.

Select the first title after the Inspector can produce measured metadata and feature indicators. Do not select solely by popularity.

## Gate 5 — Runtime and compatibility expansion

Expand services based on real blockers; add a second title with different subsystem demands and preserve passing regression cases.

## Gate 6 — GUI

Only after the CLI build/run workflow is stable: ISO selection, output path, progress, logs, local game management, controller configuration and native run button.

## Gate 7 — Stable release

Windows clean-machine test, reproducible build checks, dependency/license audit, versioning, user documentation, compatibility reports and release workflow.
