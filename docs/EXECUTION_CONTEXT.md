# Execution context

Snapshot date: 2026-10-21.

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

- Public repository: RidTheWann/RPTP-Project, default branch main.
- Published commits include the licensing/documentation baseline, the synthetic Gate 0 implementation/evidence, README cover, and subsequent README/roadmap corrections.
- The cover file is docs/assets/rptp-cover.png; README should contain exactly one reference to it.
- Gate 0 was run locally with Windows x64 MSVC; the recorded result is PASS_LOCAL_DIFFERENTIAL_SPIKE, with native_matches_oracle true, windows_msvc_verified true, and 12 original Gate 0 tests passing.
- These results cover only the synthetic instruction subset. They do not establish retail ISO support, full R5900 semantics, PS2 runtime completeness or commercial-game compatibility.

## Current work

The repository baseline includes CMake presets, an environment doctor, unit tests for diagnostic behavior, and CI for Windows/MSVC plus Linux/host compiler. Main commit `371cec8` has green CI; the reconciliation branch has not been pushed and therefore has no branch CI result. This infrastructure must be authored independently and must not use previously viewed PS2 Web Recomp build files as templates. The ISO inspector has been exercised against one owner-authorized retail ISO (Downhill Domination USA); the result is a read-only metadata record, not a boot or port.

## Open owner review

The owner resolved the clean-room handling question on 2026-10-21 by adopting ADR-0003: PS2Recomp, PS2 Web Recomp, PCSX2, Play! and other emulator/recompiler implementations are sealed. Do not access them; derive affected work independently and preserve provenance. The component audit in `docs/CLEAN_ROOM_AUDIT.md` marks the build/CI/doctor layer `Review required` and does not certify any file. The project has already published the isolated Gate 0 spike; that fact does not erase historical exposure. Formal Gate 0 acceptance remains a human review decision.

The exact full text of revised master prompt v1.2 was not available to the earlier execution runtime. Known amendments are summarized rather than represented as a verbatim copy.
