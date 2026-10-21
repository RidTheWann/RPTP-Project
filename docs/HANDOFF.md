# Handoff — RPTP after Gate 0 publication

## Current position

- Public repository: RidTheWann/RPTP-Project, branch main.
- The README cover is published at docs/assets/rptp-cover.png; README should contain one cover reference.
- The isolated Gate 0 spike is published. The owner ran scripts/run-msvc.ps1 on Windows x64 and recorded PASS_LOCAL_DIFFERENTIAL_SPIKE, native_matches_oracle true and windows_msvc_verified true.
- The 12 original Gate 0 tests and artifact guard passed in the recorded Windows run. Linux/GCC and Linux/Clang spike evidence is also recorded.
- The project license is GPL-3.0-or-later for original RPTP material. Third-party licensing remains a per-dependency audit.
- Formal Gate 0 acceptance is pending human review.
- Historical source exposure involving PS2Recomp and PS2 Web Recomp remains documented; this must not be described as erased or resolved by the license decision.

## Current phase

B1b repository/toolchain baseline and B1c ISO inspector prototype: CMake presets, rptp doctor, CTest wrappers, the synthetic-only ISO inspector, and Windows/MSVC + Linux CI are present. Main commit `371cec8` has green CI (run `39561754883`). The reconciliation branch `chore/post-gate0-reconcile` has not been pushed, so it has no CI result. The clean-checkout local Windows run is pending. Do not expand R5900 instruction semantics or PS2 runtime implementation until the owner has reviewed the source-exposure record.

## Expected local commands

Windows, from Visual Studio Developer PowerShell or x64 Native Tools prompt:

    cmake --preset windows-msvc
    cmake --build --preset windows-msvc

Host toolchain:

    cmake --preset host
    cmake --build --preset host

If a CI job fails, record the exact runner, command and error before updating project state.

## Next review points

1. Human owner confirms the license decision for the current session.
2. Human owner reviews historical source exposure and records the disposition.
3. Human owner completes formal Gate 0 review.
4. After these decisions, push the branch and require green CI before treating B1b as passed; keep every capability claim tied to reproducible evidence.
