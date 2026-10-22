# Execution context

Snapshot date: 2026-10-23.

## Human-approved project decisions

- Native Windows x64 target; static ahead-of-time recompilation to native C++ plus a from-scratch PS2 runtime.
- C++20/MSVC as the primary Windows toolchain; Linux/GCC and Clang are useful host-test environments.
- CLI, diagnostics, and logs in English.
- Original synthetic fixtures only, registered by path, SHA-256, origin and license status.
- Every game worked on gets a `docs/games/<slug>/STATUS.md` record; update the game index and status in the same session. Never commit game images or extracted assets.
- Do not copy emulator/recompiler implementation source. The exact historical source-exposure record is retained in docs/REFERENCES.md and ADR-0001. ADR-0003 seals those projects: do not access them again, and derive new work from neutral specifications and independent tests.
- GPL-3.0-or-later is the selected license for original RPTP material. Third-party licenses and notices remain separate.
- README may describe project goals, feature status, requirements and limitations, but must not be used to reproduce external implementation details.

## Current repository state

- Public repository: RidTheWann/RPTP-Project. Published tip: `9c4f675`; CI run `39860776782` passed Windows x64/MSVC and Linux/GCC. The local ANDI/XORI logical-immediate increment is not published.
- Published commits include the licensing/documentation baseline, the synthetic Gate 0 implementation/evidence, README cover, the minimal IR/CFG increment, and subsequent README/roadmap/status corrections.
- The cover file is docs/assets/rptp-cover.png; README should contain exactly one reference to it.
- Gate 0 was run locally with Windows x64 MSVC; the recorded result is PASS_LOCAL_DIFFERENTIAL_SPIKE, with native_matches_oracle true and windows_msvc_verified true. Gate 0 test and CTest results are recorded in `docs/VERIFICATION_LOG.md`.
- On 2026-10-23 the owner explicitly delegated recording of a technical pass for the narrow synthetic Gate 0 scope. `docs/GATE0_REVIEW.md` records the accepted scope and limits; it is not a clean-room certification or independent review.
- `docs/PROVENANCE_PLAN.md` records the concrete provenance execution plan, including per-increment requirements and the independent reviews still required before release.
- These results cover only the synthetic instruction subset. They do not establish retail ISO support, full R5900 semantics, PS2 runtime completeness or commercial-game compatibility. Gate 2 remains open and read-only.

## Current work

The repository baseline includes CMake presets, an environment doctor, unit tests for diagnostic behavior, and CI for Windows/MSVC plus Linux/host compiler. PR #1 merged as `5bf62b2`; the current published tip is `9c4f675`, and CI run `39860776782` passed on both jobs. The 2026-10-23 ANDI/XORI logical-immediate increment is local until the owner publishes it and is not CI-verified; see `git log origin/main..main`. This infrastructure must be authored independently and must not use previously viewed PS2 Web Recomp build files as templates; the agent-led re-derivation record and contract tests are in `docs/BUILD_PROVENANCE.md` and `tests/test_build_contract.py`, and the audit status remains `Review required`. The ISO inspector has been exercised against eight owner-authorized retail ISO images read-only (Black, Bully, Downhill Domination, God of War II, the owner-described original and Indonesian-language mod San Andreas samples, Need for Speed - Most Wanted and Resident Evil 4); the results are metadata records, not boots or ports. Gate 2 is read-only under ADR-0004; extraction is deferred future work. Gate 3 now includes a synthetic IR, logical-immediate coverage and deterministic C++ lowering, but remains in progress without function discovery, real-game generation or a product recompiler. The next permitted increment must follow `docs/PROVENANCE_PLAN.md`.

## Open owner review

The owner resolved the clean-room handling question on 2026-10-21 by adopting ADR-0003: PS2Recomp, PS2 Web Recomp, PCSX2, Play! and other emulator/recompiler implementations are sealed. Do not access them; derive affected work independently and preserve provenance. The component audit in `docs/CLEAN_ROOM_AUDIT.md` marks the build/CI/doctor layer `Review required` and does not certify any file. The project has already published the isolated Gate 0 spike; that fact does not erase historical exposure. The narrow Gate 0 technical pass is recorded, but independent provenance reviews and the Gate 2 disposition remain owner decisions.

The exact full text of revised master prompt v1.2 was not available to the earlier execution runtime. Known amendments are summarized rather than represented as a verbatim copy. The 2026-10-23 owner instruction is the recorded authority for the delegated Gate 0 disposition and provenance-plan work; it is summarized in the repository, not reproduced verbatim.
