# Handoff — RPTP after Gate 0 publication

## Current position

- Public repository: RidTheWann/RPTP-Project.
- The README cover is published at docs/assets/rptp-cover.png; README should contain one cover reference.
- The isolated Gate 0 spike is published. The owner ran scripts/run-msvc.ps1 on Windows x64 and recorded PASS_LOCAL_DIFFERENTIAL_SPIKE, native_matches_oracle true and windows_msvc_verified true.
- The original Gate 0 tests and artifact guard passed in the recorded Windows run. Linux/GCC and Linux/Clang spike evidence is also recorded.
- The work laptop is aligned to Visual Studio 2026 Build Tools 18.11.1 / MSVC 19.51.36260.0 and Python 3.13.16. Doctor, CMake configure, CTest and the Gate 0 spike pass locally.
- The ISO inspector was expanded with single-volume checks, `SYSTEM.CNF`/BOOT validation, PVD/root/boot metadata, SHA-256, ELF PT_LOAD checks, warnings, an explicit error taxonomy, chunked read limits, explicit interleaved/multi-extent rejection, a metadata-only directory survey and deterministic in-memory/file-based mutation tests. The ISO inspector suite and the full Python suite pass; CTest results are recorded in `docs/VERIFICATION_LOG.md`.
- The current owner-authorized retail sample is inspected read-only and indexed in `docs/games/README.md`. No boot or native port exists. Every game worked on must get a `docs/games/<slug>/STATUS.md` record. Gate 2 is read-only under ADR-0004; extraction is deferred future work and requires a separate threat model.
- The project license is GPL-3.0-or-later for original RPTP material. Third-party licensing remains a per-dependency audit.
- 2026-10-22 integrity pass: README, checklist and badge agree; the full test suite and the artifact guard pass locally. A plain shell has no MSVC `cl.exe`; when run through `VsDevCmd.bat`, the doctor, Windows preset, CTest (3/3) and `scripts/run-msvc.ps1` pass locally.
- 2026-10-22 build provenance pass: CMake test registration was reduced to one helper, `scripts/run-msvc.ps1` now resolves the repository from `$PSScriptRoot`, and `tests/test_build_contract.py` guards the documented build/CI/wrapper contracts. `docs/BUILD_PROVENANCE.md` records the official reference basis. The build/CI/doctor layer remains `Review required` pending independent review.
- 2026-10-22 ISO inspector hardening: added checked bounds and chunked reads with a 4 MiB default cap, explicit `INTERLEAVED_UNSUPPORTED` rejection for directory records, multi-extent child-directory rejection, deterministic-error coverage and file-based mutation hash-invariance tests. The full Python suite and artifact guard pass locally; MSVC/CTest pass locally through the Visual Studio developer environment. CI run `39664774001` passed on Windows x64/MSVC and Linux/GCC.
- 2026-10-22 survey robustness: tests now cover seeded survey mutations, malformed directory records, unsafe extents, exact depth/directory/record limits, unsupported file/directory records, file hash preservation and CLI JSON errors. A multi-extent PVD root is now rejected explicitly with `MULTI_EXTENT_UNSUPPORTED`; the previous survey traversal was the demonstrated gap.
- 2026-10-22 retail validation: the current authorized sample completed read-only inspection and directory survey. The surveys found no multi-extent or interleaved records. `God of War II` reports a PVD volume space smaller than the file (dual-layer unverified); four images have boot executables above the 4 MiB cap. The two San Andreas images are separate owner-provided samples: an original USA sample and an Indonesian-language mod. They share boot and `SYSTEM.CNF` hashes but have different whole-image hashes and PVD identifiers; shared boot metadata does not establish file equality or identify modified files. No extraction or execution was performed. The interleave BP 27/28 field mapping was later checked against ECMA-119; interleaved layouts remain unsupported.
- 2026-10-22 local ISO campaign: all eight images in the owner's local folder were surveyed read-only at `d51f0e7`; the three new images were also inspected read-only. New records are indexed under `docs/games/`. No reproducible parser defect was found and no production code was changed.
- 2026-10-22 GTA sample provenance: the owner clarified that the two San Andreas samples are intentional different images, one original USA and one Indonesian-language mod. Slugs were retained to avoid breaking existing links and history; headings, index entries, compatibility notes and records now label the owner-provided distinction. Targeted read-only rechecks matched the recorded metadata. R-020 now describes the unaudited modification details, not an unknown identity.
- Session-3 commits through `d334139`, including the survey capability, are published on `main`; CI run `39664774001` passed both supported jobs. Local commits after `d334139` include `6ae4a3a`, `33d8392` and `800b90a` plus later documentation/test records; run `git log origin/main..main` for the current list. None is pushed or CI-verified.
- Formal Gate 0 acceptance is pending human review.
- Historical source exposure involving PS2Recomp and PS2 Web Recomp remains documented; this must not be described as erased or resolved by the license decision.
- On 2026-10-21 the owner adopted ADR-0003: those projects and other emulator/recompiler implementations are sealed. Do not access them again; new work must be independently derived from neutral specifications and tests. `docs/CLEAN_ROOM_AUDIT.md` tracks component status; no file is certified clean-room, and the build/CI/doctor layer is `Review required`.

## Current phase

B1b repository/toolchain baseline and B1c ISO inspector prototype: CMake presets, rptp doctor, CTest wrappers, the synthetic-only ISO inspector, and Windows/MSVC + Linux CI are present. PR #1 merged as `5bf62b2`; CI runs `39594267744`, `39594147110`, `39594304857` and `39664774001` passed for the published history. A clean-checkout local Windows run at pre-push commit `83459c1` (now `b4d6fa7`; content unchanged) passed; it is recorded in `docs/VERIFICATION_LOG.md`. Gate 2 synthetic hardening and a read-only retail sample validation are locally verified; the interleave field mapping is spec-checked. ISO variants, multi-extent support and interleaved-file support remain open; extraction is outside the read-only Gate 2 scope and remains future work. Do not access sealed projects; apply ADR-0003 to all new work. Do not expand R5900 instruction semantics or PS2 runtime implementation until the owner completes the formal Gate 0 review.

## Expected local commands

Windows, from Visual Studio Developer PowerShell or x64 Native Tools prompt:

    cmake --preset windows-msvc
    cmake --build --preset windows-msvc

Host toolchain:

    cmake --preset host
    cmake --build --preset host

If a CI job fails, record the exact runner, command and error before updating project state.

## Next review points

1. Human owner completes formal Gate 0 review using [GATE0_REVIEW.md](GATE0_REVIEW.md) as the evidence package; the package itself does not close the gate.
2. Enforce ADR-0003: keep sealed projects off-limits, preserve provenance, and quarantine any work that cannot demonstrate independent derivation.
3. Arrange an independent review or re-derivation of the build/CI/doctor layer marked `Review required` in `docs/CLEAN_ROOM_AUDIT.md`; do not claim clean-room certification before it is recorded.
4. Keep every capability claim tied to reproducible evidence. B1b technical checks pass locally and CI is green for published `d334139`; later local commits are not CI-verified. The independent clean-room review of the build/CI/doctor layer remains open.
5. Continue validating the ISO inspector only against owner-authorized discs; keep `docs/games/` records current, record hashes and outcomes without committing game images, and do not promote compatibility from synthetic tests.
6. Review multi-extent and other ISO 9660 variants before treating Gate 2 as passed; interleaved layouts remain unsupported despite the spec-checked field mapping. Gate 2 is read-only under ADR-0004; extraction is deferred future work and requires a separate threat model.
