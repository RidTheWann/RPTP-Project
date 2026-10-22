# ADR-0001 — Foundation, from-scratch decision, and clean-room boundaries

- **Date:** 2026-10-21
- **Status:** Accepted — from-scratch direction, GPL-3.0-or-later and the sealed-source policy in ADR-0003 approved; the narrow Gate 0 technical pass was recorded on 2026-10-23 by explicit owner delegation
- **Decision owner:** Human project owner
- **Related:** Gate 0 / B1a; `docs/REFERENCES.md`; `docs/RISKS.md`

## Context

RPTP is intended to transform a user-owned PlayStation 2 ISO into a native Windows x64 build through static ahead-of-time recompilation of Emotion Engine code to C++, together with a native runtime for the PS2 services required by the game.

The human owner chose a from-scratch implementation rather than a fork/hybrid. This is an explicit project constraint, not evidence that the undertaking will be small. It increases the risk in instruction semantics, function discovery, scheduling/timing, vector units, graphics, IOP and system services.

## Decision

1. Keep the from-scratch implementation direction for Gate 0.
2. Do not copy source code from PS2 emulators/recompilers into RPTP.
3. Use documented, permitted technical references and independent experiments; record each non-trivial behavior claim in `docs/REFERENCES.md`.
4. Keep README use within the human-approved limits: project purpose, feature status, target platforms, requirements and known limitations—not implementation recipes.
5. Treat any unverified third-party license as not approved for implementation use.
6. Generate synthetic fixtures in-project and register every binary fixture in `tests/fixtures/MANIFEST` with hash, origin and license status. Commercial ISO/BIOS/game executable data is never allowlisted.
7. Use English for CLI, diagnostics and logs. Keep local build outputs out of version control.
8. The project owner selected **GNU GPL version 3 or (at the owner's option) any later version (`GPL-3.0-or-later`)** on 2026-10-21 for original RPTP project material. The root `LICENSE` contains the complete GNU GPL version 3 text; project notices and metadata select the “or later” option. Unless a file or separate notice states otherwise, original project software, documentation, build scripts, tests and synthetic fixtures are intended to be offered under this project license. Third-party components retain their applicable licenses and notices. This decision does not license or authorize redistribution of PS2 BIOS files, commercial ISOs, proprietary game assets, game executables, or game-derived generated code.

## Prior-source exposure record

Prior-session tool outputs establish that technical material from both candidate projects was already seen. The precise scope is recorded in `docs/REFERENCES.md` and summarized here to avoid understating exposure:

- **PS2Recomp:** technical README, top-level GPL-3.0 license text, repository tree/metadata, v0.3/v0.4 release notes, and issue/PR descriptions #370/#371 were viewed. The available conversation/tool outputs do not show any `.cpp` file content being fetched.
- **PS2 Web Recomp:** technical README, repository tree, top-level `CMakeLists.txt`, `scripts/port.sh`, `scripts/windows.py`, and top-level MIT license were viewed. This is more than README exposure; the build configuration and two source scripts were also displayed. No `runtime/src/*.cpp` implementation was fetched in the recorded tool outputs.
- The content above is an exposure record only. The current Gate 0 code was authored independently from the public generic MIPS/ELF references listed in `docs/REFERENCES.md`; these prior project artifacts must not be consulted as implementation templates. The GPL choice is a project-level licensing decision, not permission to copy or adapt source from PS2Recomp or any other implementation.

A historical exposure cannot be erased. On 2026-10-21 the owner resolved the handling question by adopting ADR-0003: the projects are sealed, no further access is permitted, and affected work must be independently derived from neutral specifications and tests. This does not erase the exposure record or create a legal guarantee.

## Gate 0 evidence

The local differential spike has passed on Linux host toolchains and on Windows x64 using MSVC.

The Windows run was executed through `scripts/run-msvc.ps1`. The artifact guard passed, the generated C++ compiled with the MSVC x64 compiler under C++20 with `/W4 /WX`, and all 12 unit tests passed.

The recorded report at `build/gate0-msvc/report.json` has:
- `status`: `PASS_LOCAL_DIFFERENTIAL_SPIKE`
- `windows_msvc_verified`: `true`
- `native_matches_oracle`: `true`
- `trace_steps`: `22`
- Fixture SHA-256: `b21f1f7793236d1ccba7308cc82f42d9f89915c87c0b037c46d8170f28349ca9`
- Generated C++ SHA-256: `5316e0f51ba8b1fa1252e409f38cb9ac7db7606fee17b28ef0dcf1be162ae795`

The spike covers only a synthetic ELF32/EM_MIPS fixture and a limited instruction subset: ADDIU, ADDU, LW, SW, BEQ, BNE, J, JAL, JR and NOP, including delay slots. The generated native program matches the reference interpreter for the tested state and execution trace.

**Technical spike status: passed. Gate 0 disposition: accepted as a technical pass for the narrow synthetic scope on 2026-10-23, recorded under explicit owner delegation.** The accepted scope covers the synthetic fixture, tested instruction subset, deterministic C++ generation and native-versus-oracle differential result. It does not cover retail executables, full R5900 behavior, the PS2 runtime, game boot or compatibility. See [GATE0_REVIEW.md](../GATE0_REVIEW.md).

This evidence does not establish complete R5900 accuracy, retail ISO compatibility, game boot, or support for PS2 kernel services, VU, GS, IOP, audio or other hardware behavior. Continue to use explicit test evidence and compatibility milestones for all broader claims.

The technical disposition is not a clean-room certification or independent review. The concrete provenance execution plan, including the reviews still required before release, is recorded in [PROVENANCE_PLAN.md](../PROVENANCE_PLAN.md).

## Consequences

- More time is required before a game can be expected to boot.
- Every supported instruction family needs independent semantic tests and explicit verification status.
- Game-specific compatibility is earned per title; generated executable presence does not count as playable.
- Original covered RPTP software distributed in source or binary form must comply with GPL-3.0-or-later's applicable conditions. For covered object-code distributions, provide or offer the corresponding source as required by the license. Preserve license and copyright notices. GPL permits commercial use and does not guarantee public recognition, protect a project name as a trademark, or prevent compliant forks.
- Third-party components do not become GPL-3.0-or-later merely by inclusion; retain their own licenses and required notices. Before expanding recompiler/runtime implementation, apply ADR-0003 and follow the per-increment procedure and review gates in [PROVENANCE_PLAN.md](../PROVENANCE_PLAN.md). The historical exposure record remains part of the project record.

## Re-evaluation criteria

Run Gate Review if any of the following occurs:

- Gate 0 cannot produce identical oracle/native traces with MSVC after the current reproducible spike is used correctly.
- Three consecutive sessions produce no measurable progress.
- The Gate 3 or Gate 4 effort range is exceeded without a credible path to the gate's pass criteria.
- Critical R5900 behavior cannot be verified from permitted references or tests.
- A legal, license, source exposure, or intellectual-property question remains unresolved.

Gate Review must present evidence, root cause, options and consequences. The agent recommends; only the human owner approves an architecture or license change.
