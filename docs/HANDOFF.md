# Handoff — RPTP after Gate 0 publication

## Current position

- Public repository: RidTheWann/RPTP-Project, branch main.
- The README cover is published at docs/assets/rptp-cover.png; README should contain one cover reference.
- The isolated Gate 0 spike is published. The owner ran scripts/run-msvc.ps1 on Windows x64 and recorded PASS_LOCAL_DIFFERENTIAL_SPIKE, native_matches_oracle true and windows_msvc_verified true.
- The 12 original Gate 0 tests and artifact guard passed in the recorded Windows run. Linux/GCC and Linux/Clang spike evidence is also recorded.
- The work laptop is aligned to Visual Studio 2026 Build Tools 18.11.1 / MSVC 19.51.36260.0 and Python 3.13.16. Doctor, CMake configure, CTest and the Gate 0 spike pass locally.
- The ISO inspector was expanded with single-volume checks, `SYSTEM.CNF`/BOOT validation, PVD/root/boot metadata, SHA-256, ELF PT_LOAD checks, warnings, an explicit error taxonomy and deterministic mutation smoke tests. 33 ISO inspector tests and 53 total tests pass; CTest is 3/3.
- Downhill Domination (USA) was inspected read-only and recorded in `docs/games/downhill-domination/STATUS.md`. No boot or native port exists. Every game worked on must get a `docs/games/<slug>/STATUS.md` record.
- The project license is GPL-3.0-or-later for original RPTP material. Third-party licensing remains a per-dependency audit.
- Formal Gate 0 acceptance is pending human review.
- Historical source exposure involving PS2Recomp and PS2 Web Recomp remains documented; this must not be described as erased or resolved by the license decision.
- On 2026-10-21 the owner adopted ADR-0003: those projects and other emulator/recompiler implementations are sealed. Do not access them again; new work must be independently derived from neutral specifications and tests. `docs/CLEAN_ROOM_AUDIT.md` tracks component status; no file is certified clean-room, and the build/CI/doctor layer is `Review required`.

## Current phase

B1b repository/toolchain baseline and B1c ISO inspector prototype: CMake presets, rptp doctor, CTest wrappers, the synthetic-only ISO inspector, and Windows/MSVC + Linux CI are present. Main commit `371cec8` has green CI (run `39561754883`). The reconciliation branch `chore/post-gate0-reconcile` has not been pushed, so it has no CI result. A clean-checkout local Windows run at commit `83459c1` passed; it is recorded in STATE.md and is not a substitute for branch CI. Gate 2 synthetic hardening and one real ISO inspection are locally verified, but broader real ISO layouts, multi-extent support and safe extraction boundaries remain open. Do not access sealed projects; apply ADR-0003 to all new work. Do not expand R5900 instruction semantics or PS2 runtime implementation until the owner completes the formal Gate 0 review.

## Expected local commands

Windows, from Visual Studio Developer PowerShell or x64 Native Tools prompt:

    cmake --preset windows-msvc
    cmake --build --preset windows-msvc

Host toolchain:

    cmake --preset host
    cmake --build --preset host

If a CI job fails, record the exact runner, command and error before updating project state.

## Next review points

1. Human owner completes formal Gate 0 review.
2. Enforce ADR-0003: keep sealed projects off-limits, preserve provenance, and quarantine any work that cannot demonstrate independent derivation.
3. Arrange an independent review or re-derivation of the build/CI/doctor layer marked `Review required` in `docs/CLEAN_ROOM_AUDIT.md`; do not claim clean-room certification before it is recorded.
4. After the Gate 0 disposition, push the branch and require green CI before treating B1b as passed; keep every capability claim tied to reproducible evidence.
5. Continue validating the ISO inspector only against owner-authorized discs; keep `docs/games/` records current, record hashes and outcomes without committing game images, and do not promote compatibility from synthetic tests.
6. Review multi-extent, ISO 9660 variants and safe extraction boundaries before treating Gate 2 as passed.
