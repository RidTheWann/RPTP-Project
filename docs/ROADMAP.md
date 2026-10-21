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
- [ ] Human owner reviews historical source exposure and determines clean-room handling before expanding affected implementation areas.

### Gate 0 evidence and limits

The Windows MSVC runner reported PASS_LOCAL_DIFFERENTIAL_SPIKE, windows_msvc_verified true and native_matches_oracle true; all 12 original Gate 0 tests passed. The same fixture and generated-source SHA-256 values were reproduced across separate spike runs. See STATE.md.

This verifies only the synthetic ELF32/EM_MIPS instruction subset. It does not prove full R5900 correctness, retail ISO support, a working PS2 runtime or commercial-game compatibility. Technical success does not automatically close the formal gate or resolve clean-room concerns.

## B1a — Project foundation

- [x] Select from-scratch static recompilation as the project direction.
- [x] Select GPL-3.0-or-later for original project material and publish the license text.
- [x] Record architecture, fixture, artifact and third-party-license boundaries.
- [ ] Complete owner review of historical source exposure and decide whether any affected work must be quarantined, restarted or otherwise handled.

## B1b — Repository/toolchain baseline

**Infrastructure scaffold added; automated CI result pending. This work does not expand the PS2 instruction/runtime implementation.**

- [x] Add a CMake project baseline and repeatable windows-msvc / host presets.
- [x] Add rptp doctor environment and artifact-guard diagnostics.
- [x] Add unit tests for doctor checks and error-path reporting.
- [x] Add GitHub Actions jobs for Windows x64/MSVC and Linux/GCC.
- [x] Ignore CMake/Visual Studio outputs and keep build files local.
- [ ] Confirm both GitHub Actions jobs pass on the published commit.
- [ ] Confirm dependency/license inventory remains complete before introducing any dependency.
- [ ] Re-run the full Windows CMake preset from a clean checkout.

### B1b pass criteria

A clean checkout can configure/build/test using documented commands; CI is green on supported jobs; dependency and artifact checks pass; no unapproved dependency or proprietary game data is introduced; build results are reproducible enough to compare and diagnose.

## Gate 2 — ISO Inspector

- Implement read-only ISO9660 parsing and SYSTEM.CNF inspection.
- Identify boot executable metadata and calculate hashes.
- Design safe extraction boundaries, path validation and an explicit error taxonomy.
- Add synthetic ISO/ELF fixtures only, plus malformed-input and fuzz-oriented tests.
- Do not require or commit user game images to CI.

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
