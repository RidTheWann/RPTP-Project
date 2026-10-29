# Build, CI and doctor provenance

- **Date:** 2026-10-22
- **Scope:** `CMakeLists.txt`, `CMakePresets.json`, `.github/workflows/ci.yml`, `tools/rptp_doctor.py`, `scripts/run-msvc.ps1` and their contract tests.
- **Status:** **agent-led re-derivation record; `Review required` remains in [CLEAN_ROOM_AUDIT.md](CLEAN_ROOM_AUDIT.md).** This document is not an independent review and is not clean-room certification.

## Why this layer is under review

The exposure record in [REFERENCES.md](REFERENCES.md) includes PS2 Web Recomp build configuration and scripts. The repository records the current build layer as original work, but functional overlap alone cannot be resolved by an agent assertion. Under [ADR-0003](DECISIONS/ADR-0003-sealed-source-clean-room-policy.md), affected work must be independently derived and reviewed, and the agent must not consult sealed material.

This pass does three limited things: it records the official references behind each build behavior, makes the Windows wrapper independent of the caller's working directory, and adds contract tests so later drift is visible. It does not erase the exposure record and does not upgrade the audit status.

## Reference basis

| Behavior | Contract | Permitted reference |
|---|---|---|
| CMake minimum and preset schema | CMake 3.25; preset schema version 6; Ninja; build trees under `build/` | RPTP-REF-007 |
| CTest registration | Three named tests; Python interpreter; source-root working directory; exit status is the result | RPTP-REF-008 |
| Windows toolchain setup | `VsDevCmd.bat -arch=x64 -host_arch=x64`; `cl.exe` from the developer environment | RPTP-REF-009 |
| CI shape | `push`, `pull_request`, `workflow_dispatch`; `contents: read`; Windows and Ubuntu runners; 15-minute timeout; Python 3.13 | RPTP-REF-010 |
| Python test invocation | `unittest discover -s tests -v`; non-zero exit on failure | RPTP-REF-011 |
| Wrapper location | `$PSScriptRoot` resolves the script directory; the wrapper changes to the repository root and restores the caller's location | RPTP-REF-012 |
| Native runtime targets | `add_library(rptp_runtime STATIC ...)` and `add_executable(rptp-load ...)`; `PUBLIC` include directory and `cxx_std_20`; `PRIVATE` `/W4 /WX` or `-Wall -Wextra -Wpedantic -Werror`; CTest passes the built CLI path to the Python suite through `cmake -E env RPTP_LOAD_BINARY=...` | RPTP-REF-017 |

No build behavior in this layer was derived from a sealed project's build files or scripts during this pass. The references above are official tool documentation, not implementation templates.

## Current contracts

- **Configure:** `CMakeLists.txt` requires CMake 3.25, declares a C++ project, finds Python 3.10 or newer, and includes CTest. `CMakePresets.json` defines the `windows-msvc` and `host` configure presets with Ninja and Debug builds, and matching build presets that target `rptp-ci`.
- **Doctor:** the `rptp-doctor` target invokes the Python doctor against the project source root. The doctor checks the required layout, Python version, available compiler, CMake, Ninja, git and the artifact guard.
- **Tests:** `artifact_guard`, `python_unit_tests` and `gate0_differential_spike` are registered through one helper so every test runs with the source root as its working directory. The differential test writes only to the CMake binary directory.
- **CI run history:** the Windows job runs as `Windows x64 / MSVC` and the Linux job as `Linux / GCC`. Listed CI run IDs, the ones that reported a green run, are recorded in [ROADMAP.md](ROADMAP.md) and [COMPATIBILITY.md](COMPATIBILITY.md).
- **Aggregate target:** `rptp-ci` depends on `rptp-doctor` and runs `ctest --output-on-failure`.
- **CI:** both jobs check out the source, install Python 3.13 and run the doctor plus the matching configure/build preset. The Windows job resolves Visual Studio through `vswhere.exe` and enters the x64 developer environment. The workflow has read-only repository permissions and no secrets.
- **Runtime targets:** `runtime/src/elf_loader.cpp`, `runtime/src/guest_memory.cpp` and `runtime/src/execution.cpp` build into the `rptp_runtime` static library with `runtime/include` as a public include directory; `runtime/tools/rptp_load.cpp` builds `rptp-load` and `runtime/tools/rptp_run.cpp` builds `rptp-run`. All use the project C++20 requirement and strict warnings. When `BUILD_TESTING` is on, `rptp-runtime-tests` and the `runtime_loader_tests` / `runtime_loader_cli` / `runtime_execution_cli` CTest entries are registered; the CLI tests set `RPTP_LOAD_BINARY` and `RPTP_RUN_BINARY` with `cmake -E env`. `rptp-ci` depends on the doctor, `rptp-load`, `rptp-run` and the runtime test target when testing is enabled. Contract tests for this wiring are covered by the build-contract and Python suites; loader and harness behavior is documented in [RUNTIME.md](RUNTIME.md).
- **Wrapper:** `scripts/run-msvc.ps1` resolves the repository from its own location, checks Python and `cl.exe`, runs the artifact guard, the differential spike and the unit suite, and restores the previous directory in a `finally` block.

`tests/test_build_contract.py` guards these statements against accidental drift. It is a contract test, not a provenance review.

## Evidence and limits

- The contract tests are local evidence and do not constitute a provenance review. An earlier code tip `25267b6` passed build, doctor and CTest in CI run #45 on Windows x64/MSVC and Linux/GCC. This does not resolve the build/CI/doctor layer's `Review required` status.
- The wrapper change was checked through the current Visual Studio developer environment and invoked from a temporary working directory outside the repository. A local pass is not a clean-machine guarantee.
- The doctor and workflow are not proven correct for every Visual Studio edition, runner image, shell, locale or filesystem.
- No dependency was added, and no third-party action or CMake module was vendored.
- The exposure record remains accurate. If a reviewer finds structural or expressive similarity to sealed material, the affected files must be quarantined and re-derived rather than defended.

## Local verification environment

- **Recorded 2026-10-24 (moved from docs/HANDOFF.md during the P2 documentation budget pass):** the work laptop is aligned to Visual Studio 2026 Community, MSVC toolset 14.51.36231 and Python 3.13.16. At that time the doctor, CMake configure, CTest and the Gate 0 spike passed locally. The ISO inspector hardening and survey work of 2026-10-22 also passed the full Python suite and the artifact guard locally; CTest results are recorded in [VERIFICATION_LOG.md](VERIFICATION_LOG.md).
- A plain shell has no MSVC `cl.exe`; the MSVC checks are run through `VsDevCmd.bat` or the repository wrapper. That 2026-10-22 integrity pass ran doctor, the Windows preset, CTest (3/3) and `scripts/run-msvc.ps1` successfully.
- This is local environment context, not CI evidence and not a clean-machine guarantee. The canonical software/version reference remains the home-PC record at commit `371cec8`; per-run results are in [VERIFICATION_LOG.md](VERIFICATION_LOG.md).

## What would change the status

Only an independent reviewer may record what was compared and why this layer is not derived from sealed material, as required by [CLEAN_ROOM_AUDIT.md](CLEAN_ROOM_AUDIT.md) and [PROVENANCE_PLAN.md](PROVENANCE_PLAN.md). Until then the status stays `Review required`, and the layer must not be described as clean-room certified.
