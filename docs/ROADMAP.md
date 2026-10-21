# RPTP roadmap — current working copy

## Gate 0 — Foundation research and native spike

**Technical spike: passed. Formal Gate 0 disposition: pending human review.**

- [x] Write an original synthetic ELF32/EM_MIPS fixture generator.
- [x] Parse ELF header and executable load segment with basic bounds checks.
- [x] Decode an explicit common-MIPS subset and fail on unsupported encodings.
- [x] Run an interpreter oracle and compare full register state, memory, stop PC and executed-PC trace against generated native C++.
- [x] Check generated-source determinism and fixture SHA allowlisting.
- [x] Record permitted public references and historical source exposure.
- [x] Write a renderer comparison plan; renderer selection remains open.
- [x] Run the generated program under MSVC on Windows x64 and record actual output.
- [ ] Human owner reviews all Gate 0 criteria and records the formal disposition.
- [x] Human owner adopted the ADR-0003 sealed-source clean-room policy on 2026-10-21; prior exposure remains documented and affected work must be independently derived.

### Gate 0 evidence and limits

The Windows MSVC runner reported PASS_LOCAL_DIFFERENTIAL_SPIKE, windows_msvc_verified true and native_matches_oracle true; all original Gate 0 tests passed. The same fixture and generated-source SHA-256 values were reproduced across separate spike runs. See STATE.md.

This verifies only the synthetic ELF32/EM_MIPS instruction subset. It does not prove full R5900 correctness, retail ISO support, a working PS2 runtime or commercial-game compatibility. Technical success does not automatically close the formal gate or resolve clean-room concerns.

## B1a — Project foundation

- [x] Select from-scratch static recompilation as the project direction.
- [x] Select GPL-3.0-or-later for original project material and publish the license text.
- [x] Record architecture, fixture, artifact and third-party-license boundaries.
- [x] Owner confirmed GPL-3.0-or-later on 2026-10-21.
- [x] Owner selected the ADR-0003 sealed-source policy: do not access sealed projects; preserve provenance and quarantine any work that cannot demonstrate independent derivation. Component status is tracked in `docs/CLEAN_ROOM_AUDIT.md`.

## B1b — Repository/toolchain baseline

**Status: technical baseline verified. CI is green, and the clean-checkout local Windows run passed. The build/CI/doctor layer is `Review required` in `docs/CLEAN_ROOM_AUDIT.md` and must not be described as clean-room certified. Formal Gate 0 remains pending. This work does not expand the PS2 instruction/runtime implementation.**

- [x] Add a CMake project baseline and repeatable windows-msvc / host presets.
- [x] Add rptp doctor environment and artifact-guard diagnostics.
- [x] Add unit tests for doctor checks and error-path reporting.
- [x] Add GitHub Actions jobs for Windows x64/MSVC and Linux/GCC.
- [x] Ignore CMake/Visual Studio outputs and keep build files local.
- [x] Confirm both GitHub Actions jobs passed on the previously published commit (`371cec8`, run `39561754883`).
- [x] Confirm PR #1 CI (`39594147110`) passed the Windows and Linux jobs, then merge.
- [x] Confirm CI runs (`39594267744`) and (`39594304857`) passed after the merge.
- [x] Confirm post-publication CI run (`39664774001`) passed on Windows x64/MSVC and Linux/GCC for `d334139`.
- [x] Confirm dependency/license inventory remains complete before introducing any dependency; no third-party code is currently vendored or linked.
- [x] Re-run the full Windows CMake preset from a clean checkout (local run at pre-push commit `83459c1` (now `b4d6fa7`; content unchanged); not a substitute for CI).

### B1b pass criteria

A clean checkout can configure/build/test using documented commands; CI is green on supported jobs; dependency and artifact checks pass; no unapproved dependency or proprietary game data is introduced; build results are reproducible enough to compare and diagnose.

## B1c — Read-only ISO inspection prototype

**Prototype expanded with metadata, explicit validation and deterministic malformed-input tests. The ISO inspector suite and the full Python suite pass locally; CI is green. The current owner-authorized retail sample has been inspected read-only; broad compatibility remains unverified.**

- [x] Parse ISO 9660 primary volume descriptor and validate dual-endian fields.
- [x] Enforce single-volume PVD and directory volume sequences.
- [x] Locate root `SYSTEM.CNF` and resolve `BOOT2` / legacy `BOOT` path safely.
- [x] Require `SYSTEM.CNF` to be a regular single-extent file; reject multi-extent boot executables.
- [x] Validate ELF32 little-endian header and program-header table bounds.
- [x] Validate PT_LOAD file bounds, `p_filesz <= p_memsz` and alignment; report load segments and warnings.
- [x] Report PVD/root, `SYSTEM.CNF` and boot executable metadata with SHA-256 without extracting or modifying files.
- [x] Define an explicit, stable inspection error taxonomy.
- [x] Add synthetic-only tests for valid input, malformed-image paths and deterministic mutation smoke.
- [x] Add CLI JSON success/error tests.
- [x] Confirm CI passes on Windows/MSVC and Linux/GCC.
- [x] Record an initial owner-authorized real-ISO inspection (Downhill Domination USA) in `docs/games/downhill-domination/STATUS.md`.
- [x] Validate against a broader owner-authorized set of real ISO layouts; record exact hashes and test outcomes without committing game images.
- [x] Check the directory-record file-unit/interleave-gap field mapping against ECMA-119 and add independent synthetic tests for each byte.
- [ ] Review ISO 9660 variants and multi-extent handling before claiming broad disc compatibility.

This phase is an inspector only. It does not launch a game, implement the PS2 runtime, or establish clean-room/legal disposition.

## Gate 2 — ISO Inspector expansion

**Status: synthetic hardening and a read-only retail sample validation are implemented and locally verified; multi-extent/ISO-variant review, safe extraction boundaries and formal Gate 0 disposition remain open. Gate 2 is not passed.**

- Expand the B1c prototype into read-only ISO9660 parsing and SYSTEM.CNF inspection across the documented formats.
- Identify boot executable metadata and calculate hashes.
- Design safe extraction boundaries, path validation and an explicit error taxonomy.
- Add synthetic ISO/ELF fixtures only, plus malformed-input and fuzz-oriented tests.
- Do not require or commit user game images to CI.
- Keep the inspector read-only and fail explicitly on unsupported layouts; do not infer game compatibility.

**Verified locally:** single-volume PVD validation, root `SYSTEM.CNF` inspection, BOOT path resolution, PVD/root/boot metadata, SHA-256, ELF PT_LOAD checks, metadata-only directory survey, explicit error codes, deterministic JSON, CLI JSON success/error, the ISO inspector suite and the full Python suite. CTest results and the retail sample are recorded in `docs/VERIFICATION_LOG.md`.

**Still open:** retail layouts beyond the current sample, interleaved-file support, multi-extent and ISO-variant review, safe extraction boundaries and the owner's formal Gate 0 disposition. Clean-room handling is recorded in ADR-0003.

**Pass criteria:** deterministic inspection results on synthetic fixtures, robust rejection of malformed inputs, no writes outside the requested output directory, and clear reporting when an image is unsupported.

## Gate 3 — Recompiler MVP

- Maintain an instruction catalog with explicit verification status and permitted references.
- Expand the oracle interpreter before adding corresponding native lowering.
- Introduce a documented intermediate representation (IR), decoder, basic-block/function discovery and deterministic C++ generation.
- Add differential tests for each supported instruction family and edge cases.
- Fail explicitly on unsupported instructions rather than silently producing incorrect output.

**Pass criteria:** per-instruction differential coverage, deterministic generated source, useful diagnostics and measured correctness on synthetic programs. A larger opcode count alone is not acceptance.

## Gate 4 — First-game vertical slice

Choose the first title only after the Inspector can report measured metadata and subsystem indicators; do not select solely by popularity.

- **4a Boot:** startup path, minimum kernel/syscalls, CDVD, IOP and logging.
- **4b Graphics:** first correct reference frame from an independently implemented native GS path.
- **4c Audio/input/save:** essential sound, controller and memory-card paths.
- **4d Gameplay:** repeatable boot to menu to gameplay; cold boot and save/load checks.

Each milestone needs repeatable evidence, documented limitations and a regression fixture that does not contain proprietary game data.

## Gate 5 — Runtime and compatibility expansion

Expand services based on measured blockers. Add a second title with different subsystem demands only after the first vertical slice has repeatable evidence. Preserve passing regressions.

## Gate 6 — GUI

Only after CLI build/run workflows are stable: ISO selection, output path, progress, logs, local game management, controller configuration and native run button.

## Gate 7 — Stable release

Windows clean-machine testing, reproducible build checks, dependency/license audit, versioning, user documentation, compatibility reports and release workflow.

## Planning note

The effort ranges in RISKS.md are low-confidence planning data, not delivery promises. The agent may recommend changes; the human project owner approves architecture, licensing and clean-room decisions.
