# RPTP verification log

Append-only evidence log. This file is not read at session start; the current status is [docs/STATE.md](STATE.md). Preserve existing entries and append new evidence below them.

## Verification performed on 2026-10-21

The commands below were run from Developer PowerShell x64 on the work laptop. The C1/C2/C3 runs predate the work-laptop toolchain alignment; the post-alignment run uses Visual Studio 2026 Build Tools 18.11.1 and Python 3.13.16. The canonical home-PC software/version reference is the record at commit `371cec8`; work-laptop runs are separate and do not replace it.

    python tools/rptp_doctor.py
    cmake --preset windows-msvc
    cmake --build --preset windows-msvc
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-msvc.ps1
    python -m unittest discover -s tests -v

- RPTP doctor: PASS.
- CMake configure: PASS; C++ compiler identified.
- CMake build/CTest: PASS; 3 of 3 tests passed (`artifact_guard`, `python_unit_tests`, `gate0_differential_spike`).
- Python unit tests: PASS; 34 tests at this earlier checkpoint (12 original Gate 0, 16 ISO inspector, 6 doctor). The current suite is 53 tests.
- GitHub Actions run `39561754883` on commit `371cec8`: Windows x64/MSVC and Linux/GCC jobs both completed successfully.
- PR #1 CI run `39594147110`: Windows x64/MSVC and Linux/GCC all passed.
- CI runs `39594267744` and `39594304857`: both passed.

### Work-laptop clean-checkout run (C2)

On 2026-10-21 the repository was cloned into `<temp>\rptp-clean` from the local repository at pre-push commit `83459c1` (now `b4d6fa7` after an email-only rewrite; tree unchanged), outside the working tree. From Developer PowerShell for Visual Studio 2022 (x64), in that clean clone:

    python tools/rptp_doctor.py
    cmake --preset windows-msvc
    cmake --build --preset windows-msvc
    python -m unittest discover -s tests -v

- RPTP doctor: PASS.
- CMake configure: PASS.
- CMake build/CTest: PASS; 3 of 3 tests passed.
- Python unit tests: PASS; 34 tests at this earlier checkpoint. The current suite is 53 tests.
- Generated Gate 0 report: `PASS_LOCAL_DIFFERENTIAL_SPIKE`, `windows_msvc_verified: true`, `native_matches_oracle: true`, 22 trace steps; fixture and generated-C++ SHA-256 values match the recorded values.
- This is a **clean-checkout local run**, not a substitute for CI. CI was subsequently verified by runs `39594147110` and `39594304857`.

### Work-laptop license-header verification (C3)

After adding the SPDX headers and `tests/test_license_headers.py`, the same doctor, configure, build/CTest and unittest commands were run in the working checkout:

- RPTP doctor: PASS.
- CMake configure: PASS.
- CMake build/CTest: PASS; 3 of 3 tests passed.
- Python unit tests: PASS; 35 tests at this earlier checkpoint (12 Gate 0, 16 ISO inspector, 6 doctor, 1 license-header check). The current suite is 53 tests.
- `git grep -n -i -E 'D:\\|C:\\Users' -- docs evidence README.md` matched only the documented generic example paths in README.md and ISO_INSPECTOR.md; no personal path was found.

### Work-laptop post-alignment verification (VS 2026)

The work laptop was aligned to the `371cec8` software reference and the checks were rerun on 2026-10-21:

- Visual Studio 2026 Build Tools 18.11.1; MSVC x64 19.51.36260.0, toolset 14.51.36231.
- Python 3.13.16; CMake 4.1.0; Ninja 1.13.2; Windows 11 SDK 10.0.26100.
- Required components installed: Desktop C++ Build Tools workload (`Microsoft.VisualStudio.Workload.VCTools`), MSVC x64/x86 latest, Windows 11 SDK, and C++ CMake tools.
- Optional components not installed: C++ ATL, C++ Build Insights, Just-In-Time debugger, C++ profiling tools.
- RPTP doctor: PASS (Python 3.13.16, MSVC 19.51.36260, CMake, Ninja, git, artifact guard).
- CMake configure: PASS; compiler identified as MSVC 19.51.36260.0.
- CMake build/CTest: PASS; 3 of 3 tests passed.
- Python unit tests: PASS; 53 tests (12 Gate 0, 33 ISO inspector, 6 doctor, 1 license-header check, 1 game-record check).
- Gate 0 report: `PASS_LOCAL_DIFFERENTIAL_SPIKE`, `windows_msvc_verified: true`, `native_matches_oracle: true`, 22 trace steps; local ignored reports at `build/cmake-msvc/gate0/report.json` and `build/gate0-msvc/report.json`.
- CI run `39594304857` passed; B1b technical checks pass. The clean-room review of the build/CI/doctor layer remains open.

### ISO inspector hardening verification (Gate 2 synthetic scope)

- CTest: PASS; 3 of 3 targets after the inspector changes (`artifact_guard`, `python_unit_tests`, `gate0_differential_spike`).
- Full Python suite: PASS; 53 tests.
- ISO inspector suite: PASS; 33 tests covering PVD/root metadata, single-volume enforcement, `SYSTEM.CNF` directory/multi-extent rejection, BOOT path resolution, ELF PT_LOAD bounds/size/alignment validation, warnings, deterministic reports, CLI JSON success/error and a 250-case seeded mutation smoke test.
- Game work-record check: PASS; every folder under `docs/games/` has an indexed `STATUS.md`.
- Determinism: repeated inspection of the same bytes produces identical JSON.
- Automated tests use synthetic images only. One owner-authorized real ISO, Downhill Domination (USA), was inspected read-only with `rptp_inspect.py`; no extraction, boot, emulation or recompilation was tested. Its status is recorded under `docs/games/downhill-domination/STATUS.md`.

## Windows x64/MSVC evidence

Command:

    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-msvc.ps1

- Report status: PASS_LOCAL_DIFFERENTIAL_SPIKE.
- Compiler: MSVC x64, version 19.51.36260.0.
- Flags: /std:c++20 /EHsc /W4 /WX /permissive- /utf-8.
- Artifact guard: passed.
- windows_msvc_verified: true.
- native_matches_oracle: true.
- Original Gate 0 unit tests: 12 passed.
- Synthetic ELF: 28 instructions; executed trace: 22 steps.
- Fixture SHA-256: b21f1f7793236d1ccba7308cc82f42d9f89915c87c0b037c46d8170f28349ca9.
- Generated C++ SHA-256: 5316e0f51ba8b1fa1252e409f38cb9ac7db7606fee17b28ef0dcf1be162ae795.
- The detailed report remains a local ignored build artifact at `build/gate0-msvc/report.json`; it is not committed.

## Work-laptop evidence

The sanitized files under `evidence/windows-msvc/` were captured before the work-laptop toolchain alignment. They remain historical local evidence and do not replace the home-PC software reference at commit `371cec8` or the post-alignment report above.

## Home-PC software reference

The home-PC software/version record is the one at commit `371cec8`: MSVC x64 `19.51.36260.0`, with Python 3.10+, CMake 3.25+, Ninja, and a C++20 compiler as documented in README.md and BUILDING_WINDOWS.md.

The work laptop now uses MSVC 19.51.36260.0 and Python 3.13.16. Its runs remain local evidence and do not replace this home-PC record or CI evidence.

## Linux host toolchain evidence

- Recorded host evidence (not rerun in this session): 12 original Gate 0 tests passed; the artifact guard passed; GCC 14.2.0 and Clang 17.0.0 builds passed the differential spike; repeated runs reproduced the fixture and generated-C++ hashes.
- The Linux/GCC CI job is green: runs `39594267744`, `39594147110` and `39594304857` completed successfully.

## 2026-10-22 — integrity pass local run

Environment: Windows, plain PowerShell without the MSVC developer environment. Python 3.13.16, CMake 4.4.4, Ninja 1.13.2, git 2.56.0; `cl.exe` was not on `PATH`.

    python tools/rptp_doctor.py
    cmake --preset windows-msvc
    cmake --build --preset windows-msvc
    python -m unittest discover -s tests -v
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-msvc.ps1

- RPTP doctor: FAIL; the only failing check is the missing `cl.exe`. Python, project layout, CMake, Ninja, git and the artifact guard pass.
- CMake configure (`windows-msvc`): PASS.
- CMake build: FAIL at the `rptp-doctor` target for the same missing `cl.exe`; this is an environment limitation, not a repository defect.
- Python unit tests: PASS; 54 tests. The suite grew by one progress-consistency test after the earlier 53-test entries above; the earlier entries remain as recorded.
- `ctest --test-dir build/cmake-msvc -R "artifact_guard|python_unit_tests"`: 2/2 passed. The Gate 0 CTest target was not run because MSVC is unavailable in this environment.
- `scripts/run-msvc.ps1`: exits 1 with the explicit `cl.exe` error before building.
- `python tools/check_forbidden_artifacts.py --root .`: PASS.

## 2026-10-22 — ISO inspector hardening local run

Environment: Windows, plain PowerShell without the MSVC developer environment. Python 3.13.16, CMake 4.4.4, Ninja 1.13.2, git 2.56.0; `cl.exe` was not on `PATH`.

Commands:

    python tools/rptp_doctor.py
    cmake --preset windows-msvc
    cmake --build --preset windows-msvc
    python -m unittest discover -s tests -v
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-msvc.ps1
    python tools/check_forbidden_artifacts.py --root .

- Test-first evidence: the new `max_read_bytes`/`chunk_size` tests failed with `TypeError` before the API existed; the multi-extent directory and three interleaved-layout tests failed with `AssertionError: InspectError not raised` before the checks existed.
- Full Python suite: PASS; 65 tests.
- ISO inspector suite: PASS; 44 tests. Coverage includes bounded/chunked reads, short reads, truncated volume space, huge extents, multi-extent child directories, interleaved directory records, deterministic error code/message and file-based mutation hash invariance.
- `python tools/check_forbidden_artifacts.py --root .`: PASS.
- RPTP doctor: FAIL; the only failing check is the missing `cl.exe`. Python, project layout, CMake, Ninja, git and the artifact guard pass.
- CMake configure (`windows-msvc`): PASS.
- CMake build: FAIL at the `rptp-doctor` target for the same missing `cl.exe`; no C++ compilation was attempted, so the Windows build and Gate 0 CTest target are **Belum diverifikasi** in this environment.
- `scripts/run-msvc.ps1`: exits 1 with the explicit `cl.exe` error before building.
- No real ISO was inspected in this session. All new tests use synthetic images in memory or in a temporary directory.
- These are local results only, not CI evidence. The hardening commits were not pushed.

## 2026-10-22 — R-015 evidence-count chore

Commit: `b7e7dd9 docs: remove stale test counts from audit context` (3 files, 4 insertions, 4 deletions).

- `docs/CLEAN_ROOM_AUDIT.md`: the Gate 0 evidence cell no longer hard-codes the test count; the ISO-inspector cell no longer hard-codes the suite/CTest counts and points to this log.
- `docs/EXECUTION_CONTEXT.md`: the summary points to this log instead of restating counts.
- `docs/RISKS.md`: R-015 closed.
- No behavior, license, dependency or clean-room status changed.
- The full `docs/CLEAN_ROOM_AUDIT.md` diff is required in the session report.

## 2026-10-22 — retail ISO validation and directory survey

Environment: Windows x64, Python 3.13.16, MSVC toolset 14.51.36231 through a Visual Studio developer environment. Paths to the owner-authorized images are omitted deliberately.

Commands:

    python tools/rptp_inspect.py "<authorized-folder>/<image>" --json
    python tools/rptp_inspect.py "<authorized-folder>/<image>" --survey --json
    Get-FileHash -Algorithm SHA256 "<authorized-folder>/<image>"
    python -m unittest discover -s tests -v
    python tools/check_forbidden_artifacts.py --root .

Results:

| Image | Bytes | Sectors | SHA-256 | Outcome |
|---|---:|---:|---|---|
| `Black (USA).iso` | 3,919,609,856 | 1,913,872 | `65768cade88bfbaf566b67a3ef7a0bda5a9669779833914ffe7cd73a3e45cccd` | `INSPECTED` |
| `Downhill Domination (USA).iso` | 2,530,869,248 | 1,235,776 | `0fe2b77713d3440cc3030741ea0b18f49e3feaa09671a30a421e0d4888a7eb86` | `INSPECTED` |
| `God of War II (USA).iso` | 8,533,671,936 | 4,166,832 | `266b08b7823c569be205dc9377b0e2212fbcb9080c4d65029f15040ae62d9f98` | `INSPECTED` |
| `Need for Speed - Most Wanted (USA) (v2.00).iso` | 3,702,456,320 | 1,807,840 | `b2286fb3067351323fef17e006f7715f23b5cbf5bfd7be6aad406176e3e759d2` | `INSPECTED` |
| `Resident Evil 4 (USA).iso` | 4,435,836,928 | 2,165,936 | `eb0874cf29dc48c994fd183e52a3b186b47b0a341281a0c2db24a1f18757cb66` | `INSPECTED` |

- All five images are 2048-byte aligned and report a 2048-byte logical block size. No warnings were reported.
- A second `Get-FileHash` pass matched all five whole-file SHA-256 values recorded in the table and game records.
- Four images report PVD volume space equal to the file sector count. `God of War II` reports 2,083,888 volume-space blocks against 4,166,832 file sectors, smaller by 2,082,944 sectors (4,265,869,312 bytes). Second-layer/dual-layer media is **Dugaan**, not verified.
- Directory survey results:
  - Black: 41 directories (40 directory records), 585 files, depth 3, 0 multi-extent, 0 interleaved, 0 skipped; highest extent end 3,898,607,616; largest file 117,669,888.
  - Downhill Domination: 15 directories (14 directory records), 2,338 files, depth 1, 0 multi-extent, 0 interleaved, 0 skipped; highest extent end 2,530,839,544; largest file 109,658,116.
  - God of War II: 1 directory, 15 files, depth 0, 0 multi-extent, 0 interleaved, 0 skipped; highest extent end 4,267,769,856; largest file 4,264,382,464.
  - Need for Speed - Most Wanted: 5 directories (4 directory records), 21 files, depth 2, 0 multi-extent, 0 interleaved, 0 skipped; highest extent end 3,681,464,000; largest file 1,010,616,320.
  - Resident Evil 4: 2 directories (1 directory record), 8 files, depth 1, 0 multi-extent, 0 interleaved, 0 skipped; highest extent end 4,414,846,976; largest file 1,963,034,624.
- Boot executable sizes: Black 3,371,868; Downhill Domination 1,691,684; God of War II 2,125,688; Need for Speed - Most Wanted 4,918,740; Resident Evil 4 3,096,892. One boot executable is 724,436 bytes above the 4 MiB default materialization cap; the cap was not changed.
- The existing inspector performed its normal metadata pass, including its existing boot hashing/ELF metadata path. No independent ELF analysis, extraction or execution was added; no game files were copied into the repository.
- No `*.crdownload` file was present; other files in the owner folder were ignored. No write command targeted the owner folder.
- Survey test-first evidence: the three `IsoReader.survey` tests failed with `AttributeError: 'IsoReader' object has no attribute 'survey'` and the CLI test failed on the unrecognized `--survey` argument before implementation; all four pass afterward.
- Survey text fix: the new unsigned-delta test failed with `smaller than the file by -8192 bytes`; after the fix it passes, and equal volume space prints `equal to the file size`.
- ISO inspector suite: PASS; 49 tests. Full Python suite: PASS; 70 tests. Artifact guard: PASS.
- `git diff --check`: PASS.
- Interleave-field offsets remain **Belum diverifikasi: not checked against the spec text**. The sample had zero interleaved records and does not validate those offsets.
- Local MSVC verification via the Visual Studio developer environment: doctor PASS; `windows-msvc` configure/build PASS; CTest 3/3 PASS; `scripts/run-msvc.ps1` report `PASS_LOCAL_DIFFERENTIAL_SPIKE`, `native_matches_oracle: true`, `windows_msvc_verified: true`.
- These are local results only, not CI evidence. The session-3 commits are not pushed; the session prompt prohibited pushing.

## 2026-10-22 — state reconciliation and ECMA-119 interleave-field verification

Environment: Windows x64, Python 3.13.16, MSVC toolset 14.51.36231, CMake 4.1.0 and Ninja 1.13.2 through the Visual Studio 18 Community developer environment.

- P0 documentation commit: `6ae4a3a docs: reconcile published state with CI evidence`.
- Published baseline before this work: `d334139d11526e2abc4fad7d4ad09eced3b7da4a`; local `main` matched `origin/main`. CI run `39664774001` passed Windows x64/MSVC and Linux/GCC.
- Stale claims corrected: `docs/STATE.md` no longer says local `main` is ahead and CI-unverified; `docs/HANDOFF.md` no longer says session-3 commits are local/unpushed; current CI `39664774001` is recorded in `docs/ISO_INSPECTOR.md`, `docs/COMPATIBILITY.md` and `docs/ROADMAP.md`; `docs/EXECUTION_CONTEXT.md` now records five inspected titles instead of one.
- Source retrieved: official [ECMA-119, 5th edition, December 2024 PDF](https://ecma-international.org/wp-content/uploads/ECMA-119_5th_edition_december_2024.pdf). Text extraction from the PDF confirmed Table 8 on p. 37 assigns BP 27 to File unit size and BP 28 to Interleave gap size; §§10.1.8–10.1.9 on p. 40 define both as 8-bit fields, zero unless the file section is interleaved. The zero-based indexes are 26 and 27.
- Tests added: independent cases for file-unit-only and interleave-gap-only values on `SYSTEM.CNF`, the boot executable and a subdirectory; all must raise `INTERLEAVED_UNSUPPORTED`, and file-based cases must leave the input SHA-256 unchanged. No parser offset change was made.
- Focused run: `python -m unittest tests.test_iso_inspector.IsoInspectorTests.test_ecma119_bp27_bp28_rejected_independently tests.test_iso_inspector.IsoInspectorTests.test_interleaved_field_rejection_preserves_input_bytes -v` — 2 tests, PASS.
- Full Python suite: `python -m unittest discover -s tests -v` — 72 tests, PASS. ISO inspector subset: 51 tests.
- Artifact guard: `python tools/check_forbidden_artifacts.py --root .` — PASS.
- `cmake --preset windows-msvc` and `cmake --build --preset windows-msvc` — PASS; build target reported CTest 3/3. There is no `windows-msvc` CTest preset, so the direct follow-up used `ctest --test-dir build/cmake-msvc --output-on-failure` — 3/3 PASS.
- `scripts/run-msvc.ps1` through the developer environment — `PASS_LOCAL_DIFFERENTIAL_SPIKE`, `native_matches_oracle: true`, `windows_msvc_verified: true`, fixture SHA-256 `b21f1f7793236d1ccba7308cc82f42d9f89915c87c0b037c46d8170f28349ca9`, generated C++ SHA-256 `5316e0f51ba8b1fa1252e409f38cb9ac7db7606fee17b28ef0dcf1be162ae795`.
- Updated `docs/REFERENCES.md`, `docs/RISKS.md` R-017, `docs/STATE.md`, `docs/HANDOFF.md`, `docs/ISO_INSPECTOR.md`, `docs/COMPATIBILITY.md`, `docs/ROADMAP.md` and the generated progress text. Interleaved layouts remain unsupported.
- These are local results only. The new commits are not pushed and are not CI-verified; the current master prompt prohibits pushing.

## 2026-10-22 — read-only Gate 2 scope and build provenance

Environment: Windows x64, Python 3.13.16, MSVC toolset 14.51.36231, CMake 4.1.0 and Ninja 1.13.2 through the Visual Studio 18 Community developer environment.

- Scope decision recorded in `docs/DECISIONS/ADR-0004-gate2-read-only-scope.md`; Gate 2 extraction remains unimplemented and future-only. Gate 2 is still not passed.
- Gate 0 decision package added at `docs/GATE0_REVIEW.md`; it records prior evidence and owner options and does not close the gate.
- Official references checked and recorded as `RPTP-REF-007`–`012`: CMake 3.25 presets manual, CMake 3.25 `add_test`, Microsoft MSVC command-line setup, GitHub Actions workflow syntax, Python `unittest` and PowerShell `about_Scripts`.
- Agent-led build re-derivation: CMake test registration now uses one helper; `scripts/run-msvc.ps1` resolves the repository through `$PSScriptRoot`, restores the caller location in a `finally` block, and passes when invoked from a temporary directory. Build provenance and its limits are recorded in `docs/BUILD_PROVENANCE.md`; the audit status remains `Review required`.
- `tests/test_build_contract.py`: 5 tests, PASS. It guards the CMake/preset/workflow/wrapper contracts and checks the recorded reference IDs and review status.
- `python tools/rptp_doctor.py` through `VsDevCmd.bat` — PASS; Python 3.13.16, MSVC 14.51.36231, all required paths present, artifact guard PASS.
- `cmake --preset windows-msvc` and `cmake --build --preset windows-msvc` through `VsDevCmd.bat` — PASS; the build target reported CTest 3/3 PASS.
- `ctest --test-dir build/cmake-msvc --output-on-failure` from a plain shell — artifact guard and Python tests passed; `gate0_differential_spike` failed explicitly with `Compiler 'cl' was not found on PATH`. The same command through `VsDevCmd.bat` — 3/3 PASS. This is an environment limitation, not a repository defect.
- `python -m unittest discover -s tests -v` — 77 tests, PASS. The license-header check initially skipped the new test while it was untracked; after staging, the license-header, build-contract and progress-consistency tests passed.
- Artifact guard: `python tools/check_forbidden_artifacts.py --root .` — PASS.
- `scripts/run-msvc.ps1` invoked from a temporary directory outside the repository through `VsDevCmd.bat` — `PASS_LOCAL_DIFFERENTIAL_SPIKE`, `native_matches_oracle: true`, `windows_msvc_verified: true`, 28 instructions, 22 trace steps, `/std:c++20 /EHsc /W4 /WX /permissive- /utf-8`, fixture SHA-256 `b21f1f7793236d1ccba7308cc82f42d9f89915c87c0b037c46d8170f28349ca9`, generated C++ SHA-256 `5316e0f51ba8b1fa1252e409f38cb9ac7db7606fee17b28ef0dcf1be162ae795`.
- No retail ISO was inspected in this session. No sealed project material was accessed.
- These are local results only. The new commits are not pushed and are not CI-verified.

## 2026-10-22 — directory survey robustness

Environment: Windows x64, Python 3.13.16, MSVC toolset 14.51.36231, CMake 4.1.0 and Ninja 1.13.2 through the Visual Studio 18 Community developer environment.

- Test-first review of `IsoReader.survey` and `--survey`. Added seven focused tests for seeded survey mutations, malformed directory record length/identifier/cross-block cases, unsafe extents, exact depth/directory/record limits, unsupported file/directory records, file-based mutation hash preservation and CLI JSON success/error preservation.
- First focused run:
  - `python -m unittest tests.test_iso_inspector.IsoInspectorTests.test_survey_rejects_multi_extent_root tests.test_iso_inspector.IsoInspectorTests.test_survey_rejects_malformed_directory_records tests.test_iso_inspector.IsoInspectorTests.test_survey_enforces_limits_at_boundaries tests.test_iso_inspector.IsoInspectorTests.test_survey_counts_unsupported_file_and_directory_records tests.test_iso_inspector.IsoInspectorTests.test_survey_mutations_raise_only_inspect_errors tests.test_iso_inspector.IsoInspectorTests.test_survey_file_mutations_preserve_input_bytes tests.test_iso_inspector.IsoInspectorTests.test_cli_survey_json_preserves_input_for_success_and_error -v`
  - Result: 6 passed, 1 failed. `test_survey_rejects_multi_extent_root` demonstrated that a PVD root with the multi-extent flag was traversed and reported as `SURVEYED` instead of being rejected. This was the only demonstrated production defect in the selected cases.
- Fix: `parse_pvd` now rejects a multi-extent root with `MULTI_EXTENT_UNSUPPORTED`. The same focused run after the fix: 7/7 PASS. No survey limit, record-parser, read-only or hash behavior was changed.
- Full Python suite: `python -m unittest discover -s tests -v` — 84 tests, PASS.
- Artifact guard: `python tools/check_forbidden_artifacts.py --root .` — PASS.
- `git diff --check` — PASS.
- `python tools/rptp_doctor.py` through `VsDevCmd.bat` — PASS; Python 3.13.16, MSVC 14.51.36231, CMake, Ninja, git and artifact guard present.
- `cmake --preset windows-msvc` and `cmake --build --preset windows-msvc` through `VsDevCmd.bat` — PASS; the build target reported CTest 3/3 PASS.
- `ctest --test-dir build/cmake-msvc --output-on-failure` through `VsDevCmd.bat` — 3/3 PASS.
- `scripts/run-msvc.ps1` invoked from a temporary directory outside the repository through `VsDevCmd.bat` — `PASS_LOCAL_DIFFERENTIAL_SPIKE`, `native_matches_oracle: true`, `windows_msvc_verified: true`, 28 instructions, 22 trace steps; the wrapper also ran the 84-test suite successfully.
- No retail ISO was inspected in this session. No sealed project material was accessed.
- These are local results only. The new commits are not pushed and are not CI-verified.

## 2026-10-22 — local retail survey and new game records

Inspector source revision: `d51f0e7` (the evidence/documentation changes in this entry were uncommitted during the runs). Environment: Windows x64, Python 3.13.16, MSVC toolset 14.51.36231, CMake 4.1.0 and Ninja 1.13.2 through the Visual Studio 18 Community developer environment.

- Inventory: eight regular `*.iso` files in the owner's local image folder. Labels and byte sizes only; no absolute input paths are recorded here. Black (USA) 3,919,609,856; Bully (USA) 4,636,835,840; Downhill Domination (USA) 2,530,869,248; God of War II (USA) 8,533,671,936; Grand Theft Auto - San Andreas (Indonesian v6) 3,866,394,624; Grand Theft Auto - San Andreas (USA) (v3.00) 4,517,036,032; Need for Speed - Most Wanted (USA) (v2.00) 3,702,456,320; Resident Evil 4 (USA) 4,435,836,928.
- Command per image: `python tools/rptp_inspect.py "<image>" --survey --json`. All eight exited `0` with status `SURVEYED`; no multi-extent records, interleaved records or skipped unsupported directories were reported.
- Survey counts (`directory_count` / `file_count` / `max_depth`): Black 41/585/3; Bully 36/248/2; Downhill Domination 15/2338/1; God of War II 1/15/0; San Andreas Indonesian 29/299/3; San Andreas USA 29/299/3; Need for Speed 5/21/2; Resident Evil 4 2/8/1.
- PVD volume space relative to the file: seven images `equal`; God of War II `smaller` by 4,265,869,312 bytes. Every input's byte size and last-write time were unchanged after its survey.
- Commands for the three new images: `python tools/rptp_inspect.py "<image>" --json`. All three exited `0` with status `INSPECTED` and no warnings. Input size and last-write time were unchanged.
- Bully: whole-image SHA-256 `6c95edf7803aa79fdc816295cf2e03066599a6693f7d543fbcdb78d1d1128d5e`; volume ID `BULLY`; boot `SLUS_212.69;1`, 5,132,120 bytes, SHA-256 `597d7816d922cf371d757e653368488c1983f95dcdea0dd70a733650727f52fc`; `SYSTEM.CNF` SHA-256 `aa69ad2655f3ae3b58df05ac58e5180107184cc4dd544c2347f67ae1326c41f7`; 19 `PT_LOAD` records.
- San Andreas Indonesian v6: whole-image SHA-256 `4a00e35c7b4e1dd56a6f255cba4eb7e0f5aa7a175c2c3aff9b1e3c4f90e6304f`; volume ID `GTASA_PS2_ID_KHN`; boot `SLUS_209.46;1`, 5,684,592 bytes, SHA-256 `84d4980a1253c5490ebbd039ef17384af875de75636a21f3451951093e8fc789`; `SYSTEM.CNF` SHA-256 `7d48c5d05735d54498a2e7e96c9e687ed2f9c1c00a820a36f4c3f2240d8da0bd`; 10 `PT_LOAD` records.
- San Andreas USA v3.00: whole-image SHA-256 `c94e9b16ffab9ab04dbf15109e8716a2bf0a853a246bd3d2641bf354a5068e6d`; volume ID `SAN_ANDREAS`; the same boot and `SYSTEM.CNF` hashes as the Indonesian image; 10 `PT_LOAD` records. The filename variant labels are not independently verified; both `SYSTEM.CNF` files report `VER = 3.00`.
- The four boot executables above the 4 MiB materialization cap were Need for Speed 4,918,740; Bully 5,132,120; and both San Andreas images 5,684,592 bytes. Their read-only inspections completed; the cap was not changed.
- Records added: `docs/games/bully/STATUS.md`, `docs/games/grand-theft-auto-san-andreas-indonesian-v6/STATUS.md` and `docs/games/grand-theft-auto-san-andreas-usa-v300/STATUS.md`; `docs/games/README.md` and `docs/COMPATIBILITY.md` were updated. Existing five records and their whole-image hashes were not re-derived.
- No parser defect was reproduced by the eight real images, so no production code or synthetic fixture was changed.
- `python -m unittest discover -s tests -v` — 84 tests, PASS.
- `python tools/check_forbidden_artifacts.py --root .` — PASS.
- `python tools/rptp_doctor.py` directly from the non-developer shell — FAIL only because `cl.exe` was not on `PATH`; the same command through `VsDevCmd.bat` — overall PASS.
- `cmake --preset windows-msvc` and `cmake --build --preset windows-msvc` through `VsDevCmd.bat` — PASS; CTest 3/3 PASS. A separate `ctest --test-dir build/cmake-msvc --output-on-failure` — 3/3 PASS.
- `scripts/run-msvc.ps1` invoked from a temporary directory outside the repository through `VsDevCmd.bat` — `PASS_LOCAL_DIFFERENTIAL_SPIKE`, `native_matches_oracle: true`, `windows_msvc_verified: true`, 28 instructions, 22 trace steps.
- `git diff --check` — PASS.
- Read-only throughout: no image was extracted, modified, mounted, booted, emulated or executed. Raw local JSON contains absolute input paths and remains under ignored `build/session-iso-validation/`.
- No sealed project material was accessed. These results are local only; the current evidence changes are not pushed and have no CI run.

## 2026-10-22 — GTA San Andreas sample provenance clarification

Base commit: `c58f127`; the documentation changes in this entry were uncommitted during the checks. Inspector source revision: `d51f0e7`.

- Owner-provided provenance recorded: the two GTA San Andreas USA images are intentional, separate samples. The owner describes one as the original USA sample and the other as a USA sample modified with Indonesian-language changes. This classification is declarative owner information, not a result derived from the filename or metadata. The modified file set and method are not audited.
- Targeted command per image: `python tools/rptp_inspect.py "<image>" --json`. Both exited `0` with status `INSPECTED` and no warnings.
- Targeted command per image: `python tools/rptp_inspect.py "<image>" --survey --json`. Both exited `0` with status `SURVEYED`; each reported 29 directories, 299 files, max depth 3, 0 multi-extent records, 0 interleaved records and equal PVD volume space. Input size and last-write time were unchanged before and after the two runs.
- Original sample: 4,517,036,032 bytes; volume ID `SAN_ANDREAS`; boot `SLUS_209.46;1`, 5,684,592 bytes, SHA-256 `84d4980a1253c5490ebbd039ef17384af875de75636a21f3451951093e8fc789`; `SYSTEM.CNF` SHA-256 `7d48c5d05735d54498a2e7e96c9e687ed2f9c1c00a820a36f4c3f2240d8da0bd`; `SYSTEM.CNF VER = 3.00`.
- Indonesian-language mod sample: 3,866,394,624 bytes; volume ID `GTASA_PS2_ID_KHN`; the same boot and `SYSTEM.CNF` sizes and hashes; `SYSTEM.CNF VER = 3.00`.
- Whole-image hashes were retained from the earlier record and were not recomputed in this run: original `c94e9b16ffab9ab04dbf15109e8716a2bf0a853a246bd3d2641bf354a5068e6d`; Indonesian-language mod `4a00e35c7b4e1dd56a6f255cba4eb7e0f5aa7a175c2c3aff9b1e3c4f90e6304f`.
- Shared boot and `SYSTEM.CNF` hashes are consistent with shared boot configuration and executable data. They do not establish that all other files are equal and do not locate the language modification. The different whole-image hashes and PVD identifiers prove only that the images are not byte-identical.
- No image was extracted, mounted, modified, booted, emulated or executed. Raw input paths were not added to tracked files.
- Updated the two game records, `docs/games/README.md`, `docs/COMPATIBILITY.md`, `docs/GATE2_EVIDENCE.md`, `docs/ISO_INSPECTOR.md`, `docs/RISKS.md`, `docs/STATE.md` and `docs/HANDOFF.md`. R-020 now records the unaudited modification details and the risk of overstating shared boot metadata, rather than treating the sample identity as unknown.
- No parser or production-code defect was found; no source, test or fixture changed.
- `python -m unittest discover -s tests -v` — 84 tests, PASS.
- `python tools/check_forbidden_artifacts.py --root .` — PASS.
- `python tools/rptp_doctor.py` directly from the non-developer shell — FAIL only because `cl.exe` was not on `PATH`; through `VsDevCmd.bat` — overall PASS.
- `cmake --preset windows-msvc` and `cmake --build --preset windows-msvc` through `VsDevCmd.bat` — PASS; CTest 3/3 PASS. Separate `ctest --test-dir build/cmake-msvc --output-on-failure` — 3/3 PASS.
- `scripts/run-msvc.ps1` invoked from a temporary directory outside the repository through `VsDevCmd.bat` — `PASS_LOCAL_DIFFERENTIAL_SPIKE`, `native_matches_oracle: true`, `windows_msvc_verified: true`, 28 instructions, 22 trace steps.
- `git diff --check` — PASS after the documentation changes.
- No sealed project material was accessed. These results are local only; the documentation commit is not pushed and has no CI run.

## 2026-10-22 — R-018 God of War II PVD-boundary investigation

Base commit: `f8feb27`; the documentation changes in this entry were uncommitted during the checks. Inspector source revision: `d51f0e7`. Environment: Windows x64, Python 3.13.16, MSVC toolset 14.51.36231, CMake 4.1.0 and Ninja 1.13.2 through the Visual Studio 18 Community developer environment.

- Input: owner-provided `God of War II (USA).iso`; 8,533,671,936 bytes; last-write time `1996-12-24T16:32:00Z`. Size and last-write time were unchanged before and after the read-only runs. The whole-image SHA-256 from the earlier record was not recomputed.
- Command: `python tools/rptp_inspect.py "<local image>" --json` — exit `0`, status `INSPECTED`, no warnings. Volume ID `GODOFWAR2`; PVD volume space 2,083,888 blocks at 2048 bytes per block; `SYSTEM.CNF;1` 57 bytes; `BOOT2` `cdrom0:\SCUS_974.81;1`; boot `SCUS_974.81;1` 2,125,688 bytes; boot SHA-256 `fd403603be46dea70d130695820d28b3f31de6d7e48484a5f006398a605f7dd6`; `SYSTEM.CNF` SHA-256 `5e3b5adc35f6bb256a8aa1cae64694139f7d864b812795c2df99efc9215a1cef`.
- Command: `python tools/rptp_inspect.py "<local image>" --survey --json` — exit `0`, status `SURVEYED`. 1 directory, 15 files, max depth 0, 0 multi-extent records, 0 interleaved records, 0 skipped unsupported directories. PVD volume space 4,267,802,624 bytes; relation `smaller`; signed delta `-4,265,869,312` bytes; 2,082,944 sectors beyond the declared volume. Highest file extent end 4,267,769,856 bytes; largest file 4,264,382,464 bytes.
- Derived with checked integer arithmetic: 2,083,888 × 2048 = 4,267,802,624; 8,533,671,936 ÷ 2048 = 4,166,832 sectors with remainder 0; 4,166,832 − 2,083,888 = 2,082,944 sectors; 2,082,944 × 2048 = 4,265,869,312 bytes. The highest reported file extent ends 32,768 bytes before the declared volume boundary.
- A separate in-memory metadata reader parsed only the volume descriptors and root directory records, without using `tools/rptp_inspect.py`. It read ISO 9660 descriptors at LBA 16 (primary, type 1) and LBA 17 (terminator, type 255), verified the dual-endian PVD and root fields, and reproduced the volume-space relation, 15 root records, highest extent end and largest file size. It did not write, extract or modify data.
- ECMA-119 source: official [5th edition, December 2024 PDF](https://ecma-international.org/wp-content/uploads/ECMA-119_5th_edition_december_2024.pdf), §9.4.9 (p. 26): Volume space size (BP 81 to 88) is a 32-bit number of logical blocks in which the volume space of the volume is recorded. This defines the declared-volume boundary; it does not explain the extra image bytes or PS2 layer geometry.
- Result: all 15 reported file extents are inside the declared volume. The data after the PVD-declared volume remains unexplained; a dual-layer explanation is **Dugaan**, not verified. No parser defect was reproduced. Existing tests already cover an image larger than its PVD volume, an out-of-volume extent and a truncated volume, so no production code or fixture changed.
- Documentation updated: the God of War II record, `RISKS.md` R-018, `GATE2_EVIDENCE.md`, `ISO_INSPECTOR.md`, `COMPATIBILITY.md`, `REFERENCES.md`, `STATE.md` and `HANDOFF.md`.
- `python -m unittest discover -s tests -v` — 84 tests, PASS.
- `python tools/check_forbidden_artifacts.py --root .` — PASS.
- `python tools/rptp_doctor.py` through `VsDevCmd.bat` — overall PASS. `cmake --preset windows-msvc` and `cmake --build --preset windows-msvc` — PASS; CTest 3/3 PASS. A separate `ctest --test-dir build/cmake-msvc --output-on-failure` — 3/3 PASS.
- `git diff --check` — PASS after the documentation changes.
- Read-only throughout: no image was extracted, modified, mounted, booted, emulated or executed. No absolute input path was added to tracked files and no sealed project material was accessed. These results are local only; the documentation commit is not pushed and has no CI run.
