# Execution context

Snapshot date: 2026-10-21.

## Human-approved project decisions

- Native Windows x64 target; static ahead-of-time recompilation to native C++ plus a from-scratch PS2 runtime.
- C++20/MSVC as the primary Windows toolchain; Linux/GCC and Clang are useful host-test environments.
- CLI, diagnostics, and logs in English.
- Original synthetic fixtures only, registered by path, SHA-256, origin and license status.
- Do not copy emulator/recompiler implementation source. The exact historical source-exposure record is retained in docs/REFERENCES.md and ADR-0001.
- GPL-3.0-or-later is the selected license for original RPTP material. Third-party licenses and notices remain separate.
- README may describe project goals, feature status, requirements and limitations, but must not be used to reproduce external implementation details.

## Current repository state

- Public repository: RidTheWann/RPTP-Project, default branch main.
- Published commits include the licensing/documentation baseline, the synthetic Gate 0 implementation/evidence, README cover, and subsequent README/roadmap corrections.
- The cover file is docs/assets/rptp-cover.png; README should contain exactly one reference to it.
- Gate 0 was run locally with Windows x64 MSVC; the recorded result is PASS_LOCAL_DIFFERENTIAL_SPIKE, with native_matches_oracle true, windows_msvc_verified true, and 12 original Gate 0 tests passing.
- These results cover only the synthetic instruction subset. They do not establish retail ISO support, full R5900 semantics, PS2 runtime completeness or commercial-game compatibility.

## Current work

The current infrastructure milestone adds CMake presets, an environment doctor, unit tests for diagnostic behavior, and CI for Windows/MSVC plus Linux/host compiler. This infrastructure must be authored independently and must not use previously viewed PS2 Web Recomp build files as templates.

## Open owner review

The owner still needs to explicitly review the documented historical source exposure and decide whether any affected area should be quarantined, restarted or otherwise handled before expanding recompiler/runtime implementation. The project has already published the isolated Gate 0 spike; that fact does not erase historical exposure. Formal Gate 0 acceptance also remains a human review decision.

The exact full text of revised master prompt v1.2 was not available to the earlier execution runtime. Known amendments are summarized rather than represented as a verbatim copy.
