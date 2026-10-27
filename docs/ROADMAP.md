# RPTP roadmap — current working copy

## Gate 0 — Foundation research and native spike

**Technical spike: passed. Gate 0 is accepted as a technical pass for the narrow synthetic scope by explicit owner delegation on 2026-10-23. This is not a clean-room certification, an independent review or a Gate 2 disposition.**

- [x] Write an original synthetic ELF32/EM_MIPS fixture generator.
- [x] Parse ELF header and executable load segment with basic bounds checks.
- [x] Decode an explicit common-MIPS subset and fail on unsupported encodings.
- [x] Run an interpreter oracle and compare full register state, memory, stop PC and executed-PC trace against generated native C++.
- [x] Check generated-source determinism and fixture SHA allowlisting.
- [x] Record permitted public references and historical source exposure.
- [x] Write a renderer comparison plan; renderer selection remains open.
- [x] Run the generated program under MSVC on Windows x64 and record actual output.
- [x] Owner delegated and the agent recorded the narrow Gate 0 technical pass on 2026-10-23; independent provenance review remains a release prerequisite.
- [x] Human owner adopted the ADR-0003 sealed-source clean-room policy on 2026-10-21; prior exposure remains documented and affected work must be independently derived.

### Gate 0 evidence and limits

The Windows MSVC runner reported PASS_LOCAL_DIFFERENTIAL_SPIKE, windows_msvc_verified true and native_matches_oracle true; all original Gate 0 tests passed. The same fixture and generated-source SHA-256 values were reproduced across separate spike runs. Published commit `6499b05` is green on Windows x64/MSVC and Linux/GCC in CI run `39838955979`. See STATE.md.

The recorded disposition accepts only the synthetic ELF32/EM_MIPS instruction subset and the tested differential evidence. It does not prove full R5900 correctness, retail ISO support, a working PS2 runtime or commercial-game compatibility. Technical success does not resolve clean-room concerns. The [Gate 0 decision package](GATE0_REVIEW.md) records the accepted scope, limits and authority; the separate [provenance execution plan](PROVENANCE_PLAN.md) records the remaining reviews and forbidden material. Neither document is a clean-room certification.

## B1a — Project foundation

- [x] Select from-scratch static recompilation as the project direction.
- [x] Select GPL-3.0-or-later for original project material and publish the license text.
- [x] Record architecture, fixture, artifact and third-party-license boundaries.
- [x] Owner confirmed GPL-3.0-or-later on 2026-10-21.
- [x] Owner selected the ADR-0003 sealed-source policy: do not access sealed projects; preserve provenance and quarantine any work that cannot demonstrate independent derivation. Component status is tracked in `docs/CLEAN_ROOM_AUDIT.md`.

## B1b — Repository/toolchain baseline

**Status: technical baseline verified. The latest synthetic code increments `69d7c11` (`SLTI`, run #44) and `25267b6` (`SLTIU`, run #45) passed Windows x64/MSVC and Linux/GCC. The build/CI/doctor layer remains `Review required` in `docs/CLEAN_ROOM_AUDIT.md`; CI success is not a clean-room certification. Gate 0 remains a narrow technical pass, Gate 2 remains open, and Gate 3 remains not passed.

- [x] Add a CMake project baseline and repeatable windows-msvc / host presets.
- [x] Add rptp doctor environment and artifact-guard diagnostics.
- [x] Add unit tests for doctor checks and error-path reporting.
- [x] Add GitHub Actions jobs for Windows x64/MSVC and Linux/GCC.
- [x] Ignore CMake/Visual Studio outputs and keep build files local.
- [x] Confirm both GitHub Actions jobs passed on the previously published commit (`371cec8`, run `39561754883`).
- [x] Confirm PR #1 CI (`39594147110`) passed the Windows and Linux jobs, then merge.
- [x] Confirm CI runs (`39594267744`) and (`39594304857`) passed after the merge.
- [x] Confirm post-publication CI run (`39664774001`) passed on Windows x64/MSVC and Linux/GCC for `d334139`.
- [x] Confirm CI run (`39838955979`) passed on Windows x64/MSVC and Linux/GCC for the later published tip `6499b05`.
- [x] Confirm CI run (`39852791294`) passed on Windows x64/MSVC and Linux/GCC for the later published tip `9c11917`.
- [x] Confirm CI run (`39860776782`) passed on Windows x64/MSVC and Linux/GCC for the later published tip `9c4f675`.
- [x] Confirm CI run (`39908025708`) passed on Windows x64/MSVC and Linux/GCC for the later published tip `83c7c6a`.
- [x] Confirm CI run (`39920189021`) passed on Windows x64/MSVC and Linux/GCC for the later published tip `3dbe3f1`.
- [x] Confirm CI run (`39994586188`) passed on Windows x64/MSVC and Linux/GCC for the later published tip `f3782c9`.
- [x] Confirm CI run (`39999387250`) passed on Windows x64/MSVC and Linux/GCC for the later published tip `b98ee1d`.
- [x] Confirm CI run (`40003992195`) passed on Windows x64/MSVC and Linux/GCC for the later published tip `bbb1738`.
- [x] Confirm CI run (`40007604212`) passed on Windows x64/MSVC and Linux/GCC for the later published tip `e239527`.
- [x] Confirm dependency/license inventory remains complete before introducing any dependency; no third-party code is currently vendored or linked.
- [x] Re-run the full Windows CMake preset from a clean checkout (local run at pre-push commit `83459c1` (now `b4d6fa7`; content unchanged); not a substitute for CI).

### B1b pass criteria

A clean checkout can configure/build/test using documented commands; CI is green on supported jobs; dependency and artifact checks pass; no unapproved dependency or proprietary game data is introduced; build results are reproducible enough to compare and diagnose.

## B1c — Read-only ISO inspection prototype

**Prototype expanded with metadata, explicit validation and deterministic malformed-input tests. The read-only ISO inspector and its test suite also passed in current Windows/MSVC and Linux/GCC CI (run #45); the owner-authorized retail sample remains inspection-only and broad compatibility remains unverified.

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

**Status: synthetic hardening and a read-only retail sample validation are implemented and locally verified; multi-extent/ISO-variant review and the independent ISO inspector provenance review remain open. The narrow Gate 0 technical pass is recorded but does not close Gate 2. Gate 2 is a read-only milestone under [ADR-0004](DECISIONS/ADR-0004-gate2-read-only-scope.md); extraction is deferred future work. Gate 2 is not passed.** The criterion-to-evidence map is maintained in [GATE2_EVIDENCE.md](GATE2_EVIDENCE.md); it is evidence, not a disposition.

- Expand the B1c prototype into read-only ISO9660 parsing and SYSTEM.CNF inspection across the documented formats.
- Identify boot executable metadata and calculate hashes.
- Record the read-only Gate 2 scope; defer extraction, its threat model and any output-directory design to a separate future decision.
- Add synthetic ISO/ELF fixtures only, plus malformed-input and fuzz-oriented tests.
- Do not require or commit user game images to CI.
- Keep the inspector read-only and fail explicitly on unsupported layouts; do not infer game compatibility.

**Verified locally:** single-volume PVD validation, root `SYSTEM.CNF` inspection, BOOT path resolution, PVD/root/boot metadata, SHA-256, ELF PT_LOAD checks, metadata-only directory survey, explicit error codes, deterministic JSON, CLI JSON success/error, the ISO inspector suite and the full Python suite. CTest results and the retail sample are recorded in `docs/VERIFICATION_LOG.md`.

**Still open:** retail layouts beyond the current sample, interleaved-file support, multi-extent and ISO-variant review, and the independent ISO inspector provenance review. Extraction is outside Gate 2 and requires a separate ADR and threat model. Clean-room handling is recorded in ADR-0003 and the execution steps in [PROVENANCE_PLAN.md](PROVENANCE_PLAN.md).

**Pass criteria:** deterministic inspection results on synthetic fixtures, robust rejection of malformed inputs, no write path to the input or host, and clear reporting when an image is unsupported.

## Gate 3 — Recompiler MVP

**Status: not passed. The synthetic instruction catalog records the tested subset and evidence in [INSTRUCTION_CATALOG.md](INSTRUCTION_CATALOG.md). Separate ORI, ANDI/XORI, LUI, register-logical AND/OR/XOR/NOR, SLT/SLTU, SLTI/SLTIU, DADDIU and SUBU programs have independent synthetic fixtures and native differentials. `SLTI` (`69d7c11`, run #44) and `SLTIU` (`25267b6`, run #45) are CI-green; DADDIU and its regression-test correction passed run #50 on Windows x64/MSVC and Linux/GCC; `SUBU` (`a76ddbc`, test-first `a253136`) has local Linux/GCC evidence but remains not CI-verified pending hosted checks; the accepted Gate 0 fixture and scope are unchanged. A documented IR, fail-closed CFG/function-entry-candidate analysis, conservative known-edge traversal and deterministic C++ lowering are recorded in [IR_CFG.md](IR_CFG.md), `tests/test_ir_cfg.py`, `tests/test_cfg_reachability.py`, `tools/rptp_lower.py`, `tests/test_ir_lowering.py`, `tests/test_instruction_logical.py`, `tests/test_instruction_lui.py`, `tests/test_instruction_register_logic.py`, `tests/test_instruction_nor.py`, `tests/test_instruction_slt.py`, `tests/test_instruction_sltu.py`, `tests/test_instruction_slti.py` and `tests/test_instruction_sltiu.py`, `tests/test_instruction_daddiu.py`. The known-edge report and lowerer do not prove runtime reachability, dead code or function extents. No product recompiler or real-game code generation exists yet.

- Maintain an instruction catalog with explicit verification status and permitted references.
- Expand the oracle interpreter before adding corresponding native lowering.
- [x] Add a minimal documented IR and deterministic fail-closed block analysis over a runtime-generated synthetic ELF, with candidate-only function entries.
- [x] Add conservative known-edge graph reachability over existing CFG successors, with explicit unresolved-transfer, direct-call and validation limits; no edge is synthesized.
- [x] Introduce deterministic IR-to-C++ generation for the documented synthetic subset; the existing spike and ORI paths remain separate differentials.
- [x] Add differential tests for each supported instruction family and edge cases in the current synthetic subset.
- [x] Fail explicitly on unsupported instructions rather than silently producing incorrect output.

**Verified locally:** the reachability suite covers linear and conditional traversal, explicit non-entry roots, direct `J`/`JAL` targets, unresolved indirect transfers, return candidates, the direct-call continuation caveat, invalid roots, malformed block partitions, stable ordering, determinism and non-mutation. No edge is synthesized and no runtime-reachability claim is made. The 29-instruction lowering fixture executes 26 PCs and matches the oracle for registers, memory, stop PC and trace; a 13-instruction dynamic-JR fixture executes 13 PCs and also matches. An 18-instruction fixture covers zero-extended `ANDI`/`XORI` masking, toggling, `$zero`, overlap and boundary behavior and also matches. A 9-instruction `LUI` fixture covers all immediate boundaries, shifted/sign-extended results, `$zero` and malformed metadata and also matches. A 24-instruction register-logical fixture covers full 64-bit `AND`/`OR`/`XOR` bitwise results, upper-bit patterns, all-zero/all-one values, `$zero`, source/destination aliases and malformed encodings/IR, and also matches. A 16-instruction `NOR` fixture covers full 64-bit complement-of-union results, upper-bit patterns, all-zero/all-one values, `$zero`, source/destination aliases and malformed encodings/IR, and also matches. A 20-instruction `SLT` fixture covers signed two's-complement 64-bit ordering, negative/positive and high-bit patterns, equality, `$zero`, source/destination aliases and malformed encodings/IR, and also matches; the generated helper is additionally checked at `INT64_MIN`/`INT64_MAX`. A 26-instruction `SLTU` fixture covers unsigned 64-bit ordering, bit-31/bit-63 divergence, equality, all-ones, `$zero`, source/destination aliases and malformed encodings/IR, and also matches; the generated helper is additionally checked at unsigned 64-bit boundaries. A 24-instruction `SLTI` fixture and a 21-instruction `SLTIU` fixture separately test signed and unsigned comparisons against sign-extended immediates; both generated native paths passed CI with literal-oracle assertions and boundary harnesses. Uninitialized loads exit 2 with `LOWER_RUNTIME_ERROR: read from uninitialized guest memory`. The generated C++ is deterministic and independent of the raw word value. MSVC native tests pass; the full wrapper, CMake/CTest and the unchanged Gate 0/ORI hashes are recorded in `docs/VERIFICATION_LOG.md`.

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
