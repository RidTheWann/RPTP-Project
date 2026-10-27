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

## 2026-10-22 — Publication stack audit: larger-than-volume test correction

Base commit: `4f6369e`; the test and this log entry were uncommitted during the checks. Inspector source revision: `d51f0e7`.

- During the pre-publication audit, the R-018 entry's statement that existing tests already covered an image larger than its PVD volume was found to be inaccurate. No test constructed an image with data beyond the declared volume.
- Added `test_accepts_image_larger_than_pvd_volume` to `tests/test_iso_inspector.py`. The test appends one 2048-byte block to the synthetic image, expects `inspect_bytes` to return `INSPECTED`, and expects the survey to report 33 sectors, 32 volume-space blocks, relation `smaller` and signed delta `-2048` bytes.
- No production code, fixture or retail image was changed.
- `python -m unittest discover -s tests -v` — 85 tests, PASS.
- `python tools/check_forbidden_artifacts.py --root .` — PASS.
- `python -m compileall -q tools tests` — PASS.
- These results are local only; the commit is not pushed and has no CI run.

## 2026-10-23 - Gate 0 narrow technical disposition and provenance plan

Base commit: `6499b05d710837f3cae4b3f7e06fa5ab0cb9e55a`; the documentation, generated progress assets and progress-generator changes in this entry were uncommitted during the checks. Environment: Windows 11 x64, Python 3.13.16, Visual Studio 2026 Community, MSVC toolset 14.51.36231, CMake 4.4.4 and Ninja 1.13.2 through the Visual Studio developer environment.

- Published CI baseline: GitHub Actions run `39838955979` for `6499b05` reported success. The run page lists both jobs, `Windows x64 / MSVC` and `Linux / GCC`, with successful results. This is the published baseline; the snapshot commit in this entry is local and has no CI run.
- Owner authority: the 2026-10-23 owner instruction explicitly delegated recording of a technical pass for the narrow synthetic differential-spike scope. `docs/GATE0_REVIEW.md` records the accepted scope, non-claims and decision record. It is not a clean-room certification, independent review, legal opinion, Gate 2 disposition or game-compatibility claim.
- `docs/PROVENANCE_PLAN.md` records the concrete execution plan: current traceability, the per-increment reference/test/audit procedure, prohibited material, re-derivation and quarantine rules, and the independent reviews required before Gate 2 closure and product release.
- Status documents updated to remove the stale pending-Gate-0 claims: `README.md`, `docs/STATE.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`, `docs/EXECUTION_CONTEXT.md`, `docs/GATE0_REVIEW.md`, `docs/GATE2_EVIDENCE.md`, `docs/CLEAN_ROOM_AUDIT.md`, `docs/BUILD_PROVENANCE.md`, `docs/BUILDING_WINDOWS.md`, `docs/COMPATIBILITY.md`, `docs/ISO_INSPECTOR.md`, ADR-0001 and the eight indexed game records. Gate 2 remains open and read-only; no extraction, boot or compatibility claim was added.
- The build/CI/doctor layer remains `Review required`; the Gate 0 and ISO inspector components remain `Provisional independent`; no component was certified clean-room. The runtime/recompiler expansion row is recorded as a met prerequisite with no implementation beyond the synthetic spike.
- `python tools/rptp_progress.py` - PASS; regenerated `docs/progress.html`, `docs/assets/progress.svg`, `docs/assets/badge-foundation.svg` and `docs/assets/badge-runtime.svg`. The foundation badge moved from 72.2% to 77.8% (14 of 18 checklist items verified); the README uses the generated value.
- `python -m unittest discover -s tests -v` - 85 tests, PASS.
- `python tools/check_forbidden_artifacts.py --root .` - PASS.
- `python -m compileall -q tools tests` - PASS.
- Relative-link check: 92 relative links across 32 Markdown files - PASS; all resolve to existing repository paths.
- `git diff --check` - PASS for whitespace errors; Git emitted LF-to-CRLF normalization warnings for modified text and generated SVG files. No whitespace error was reported.
- `python tools/rptp_doctor.py` through `VsDevCmd.bat` - PASS; Python 3.13.16, MSVC 14.51.36231, CMake, Ninja, git, required layout and artifact guard all passed.
- `cmake --preset windows-msvc` and `cmake --build --preset windows-msvc` through `VsDevCmd.bat` - PASS; the build target ran CTest 3/3 PASS.
- `scripts/run-msvc.ps1` invoked from a temporary directory outside the repository through `VsDevCmd.bat` - `PASS_LOCAL_DIFFERENTIAL_SPIKE`; `native_matches_oracle: true`; `windows_msvc_verified: true`; 28 instructions; 22 trace steps; fixture SHA-256 `b21f1f7793236d1ccba7308cc82f42d9f89915c87c0b037c46d8170f28349ca9`; generated C++ SHA-256 `5316e0f51ba8b1fa1252e409f38cb9ac7db7606fee17b28ef0dcf1be162ae795`; the wrapper also ran the 85-test suite successfully.
- No retail ISO was inspected, extracted, modified, mounted, booted, emulated or executed in this session. No sealed project material was accessed. These are local results only; the snapshot commit is not pushed and has no CI run.

## 2026-10-23 - Gate 3 synthetic instruction catalog and ORI differential

Base commit: `89b70ff`; the source, test and documentation changes in this entry were uncommitted during the checks. Environment: Windows 11 x64, Python 3.13.16, Visual Studio 2026 Community, MSVC toolset 14.51.36231, CMake 4.4.4 and Ninja 1.13.2 through the Visual Studio developer environment. No retail ISO or sealed project material was accessed.

- Test-first check: before implementation, `python -m unittest tests.test_instruction_ori -v` failed on opcode `0x0D` with `Unsupported opcode 0x0D` in the decoder and `AttributeError` for the missing separate ORI fixture builder; the native case skipped because no compiler was on the plain-shell PATH.
- Implementation: added `ORI` (I-type opcode `0x0D`) to the synthetic decoder, oracle and C++ emitter; the model zero-extends the 16-bit immediate, ORs the low 32 bits of `rs`, zero-extends the 32-bit result to the spike's 64-bit register array, and discards writes to `$zero`. The helper is emitted only when the decoded program contains `ORI`.
- Registered Gate 0 fixture SHA-256 remains `b21f1f7793236d1ccba7308cc82f42d9f89915c87c0b037c46d8170f28349ca9`; the Gate 0 generated-C++ SHA-256 remains `5316e0f51ba8b1fa1252e409f38cb9ac7db7606fee17b28ef0dcf1be162ae795`. The accepted Gate 0 artifact and scope are unchanged.
- Separate runtime-generated ORI fixture SHA-256: `6c04b37fb40b3e7eaa29f82e7f21795bf930f0668aade41d04b1e058b8ff6dbc`; generated C++ SHA-256: `2aefb52babdd9e355fd3d12f3339c5c05ee60421be8bef0f17ae8f78d848c684`; six executed PCs; `t0 = 32769`, `t1 = 49153`, `v0 = 42`, `$zero = 0`, stop PC = `0x7FFF0000`, halted.
- Added `docs/INSTRUCTION_CATALOG.md` with the synthetic subset, verification levels, limits and references. Added `tests/test_instruction_ori.py`; updated `README.md`, `docs/STATE.md`, `docs/HANDOFF.md`, `docs/ROADMAP.md`, `docs/REFERENCES.md`, `docs/CLEAN_ROOM_AUDIT.md` and this log. No Gate 0 dossier or accepted-scope claim was rewritten.
- `python -m unittest discover -s tests -v` from the plain shell - 88 tests, OK with one skip: the native ORI differential skipped because `cl.exe` was not on that PATH. This skip is not a native verification.
- `python -m unittest tests.test_instruction_ori -v` through `VsDevCmd.bat -arch=x64 -host_arch=x64` - 3 tests, OK; the generated MSVC program matched the oracle.
- `scripts/run-msvc.ps1` invoked from a temporary directory outside the repository through `VsDevCmd.bat` - 88 tests, OK, no skip; Gate 0 report remained `PASS_LOCAL_DIFFERENTIAL_SPIKE`, `native_matches_oracle: true`, `windows_msvc_verified: true`, 28 instructions, 22 trace steps, with the unchanged fixture and generated-source hashes above.
- `cmake --preset windows-msvc` and `cmake --build --preset windows-msvc` through `VsDevCmd.bat` - PASS; doctor PASS and CTest 3/3 PASS.
- `python tools/check_forbidden_artifacts.py --root .` - PASS. `python -m compileall -q tools tests` - PASS.
- Relative-link check: 103 relative links across 32 Markdown files - PASS; all resolve to existing repository paths.
- `git diff --check` - PASS for whitespace errors; Git emitted LF-to-CRLF normalization warnings for modified text files. No whitespace error was reported.
- These are local results only; the changes are not pushed and have no CI run.

## 2026-10-23 - Gate 3 minimal IR and fail-closed CFG

Base commit: `f03429c`; the source, test and documentation changes in this entry were uncommitted during the checks. Environment: Windows 11 x64, Python 3.13.16, Visual Studio 2026 Community, MSVC toolset 14.51.36231, CMake 4.4.4 and Ninja 1.13.2 through the Visual Studio developer environment. No retail ISO or sealed project material was accessed.

- Test-first check: before implementation, `python -m unittest tests.test_ir_cfg -v` failed with `FileNotFoundError` for the missing `tools/rptp_ir.py`; no IR or CFG implementation existed.
- Implementation: added `tools/rptp_ir.py` with a minimal `IRInstruction`, validated `BasicBlock` partition, `FunctionEntryCandidate` records, stable `AnalysisError` codes, and `analyze_words` / `analyze_elf` entry points. The module reuses the narrow Gate 0 decoder and does not execute code, emit C++, recover function extents or prove reachability.
- IR contract: each instruction retains PC, raw word, operation, register operands, explicit `signed16` / `zero16` immediate kind, direct target, modeled destination and `delay_slot_for`. Writes to `$zero` are not modeled as destinations. Control classes are `fallthrough`, `conditional_branch`, `direct_jump`, `direct_call`, `indirect_jump` and `return_candidate`.
- CFG contract: deterministic block starts cover the validated code range, direct branch/jump/call targets, conditional fallthrough, and post-delay partition points. Delay slots are owned exactly once by their transfer. Conditional successors are target then fallthrough; indirect/return blocks have no guessed successor. Function entries are limited to the ELF entry and validated `JAL` targets and remain candidate-only.
- Added `tests/test_ir_cfg.py` with 18 tests using a runtime-generated 15-instruction ELF. The tests cover instruction mapping, immediate-kind distinction, `$zero`, straight-line and conditional blocks, direct jump/call, delay ownership, `JR` return candidates, out-of-range and unaligned addresses, truncated/missing delay slots, target-into-delay-slot rejection, unsupported/malformed input, determinism and unchanged Gate 0/ORI hashes.
- Registered Gate 0 fixture SHA-256 remains `b21f1f7793236d1ccba7308cc82f42d9f89915c87c0b037c46d8170f28349ca9`; Gate 0 generated-C++ SHA-256 remains `5316e0f51ba8b1fa1252e409f38cb9ac7db7606fee17b28ef0dcf1be162ae795`. ORI fixture SHA-256 remains `6c04b37fb40b3e7eaa29f82e7f21795bf930f0668aade41d04b1e058b8ff6dbc`; ORI generated-C++ SHA-256 remains `2aefb52babdd9e355fd3d12f3339c5c05ee60421be8bef0f17ae8f78d848c684`. No Gate 0 instruction, fixture or accepted-scope claim changed.
- `python -m unittest discover -s tests -v` from the plain shell - 106 tests, OK with one skip: the native ORI differential skipped because `cl.exe` was not on that PATH. This skip is not a native verification.
- `scripts/run-msvc.ps1` invoked from a temporary directory outside the repository through `VsDevCmd.bat` - 106 tests, OK, no skip; Gate 0 report remained `PASS_LOCAL_DIFFERENTIAL_SPIKE`, `native_matches_oracle: true`, `windows_msvc_verified: true`, 28 instructions, 22 trace steps, with the unchanged fixture and generated-source hashes above.
- `cmake --preset windows-msvc` and `cmake --build --preset windows-msvc` through `VsDevCmd.bat` - PASS; doctor PASS and CTest 3/3 PASS. A separate plain-shell `ctest --test-dir build/cmake-msvc --output-on-failure` attempt failed only because `gate0_differential_spike` could not find `cl.exe` on PATH; rerunning CTest through `VsDevCmd.bat` passed 3/3.
- `python tools/check_forbidden_artifacts.py --root .` - PASS. `python -m compileall -q tools tests` - PASS. The synthetic fixture manifest was unchanged; no new binary fixture was committed.
- Relative-link check: 112 relative links across 34 Markdown files - PASS; all resolve to existing repository paths.
- `git diff --check` - PASS for whitespace errors; Git emitted LF-to-CRLF normalization warnings for modified text files. No whitespace error was reported.
- Added `docs/IR_CFG.md`; updated `README.md`, `docs/STATE.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`, `docs/INSTRUCTION_CATALOG.md`, `docs/CLEAN_ROOM_AUDIT.md` and this log. Gate 3 remains in progress and unpassed; no Gate 2 or later disposition changed.
- The IR/CFG analysis is host-Python only. This increment adds no native IR lowering, runtime behavior, function extents or compatibility claim. These are local results only; the changes are not pushed and have no CI run.

## 2026-10-23 - Gate 3 deterministic IR-to-C++ lowering

Base commit: `9c119177a7ba9615714b881a2e2219f07b2122d9`; the source, test and documentation changes in this entry were uncommitted during the checks. Environment: Windows 11 x64, Python 3.13.16, Visual Studio 2026 Community, MSVC toolset 14.51.36231, CMake 4.4.4 and Ninja 1.13.2 through the Visual Studio developer environment. No retail ISO or sealed project material was accessed.

- Published baseline re-checked this session: GitHub Actions run `39852791294` for `9c11917` reported success; the run page lists `Windows x64 / MSVC` (30s) and `Linux / GCC` (20s) as successful. This is the CI baseline; the lowering commit in this entry is local and has no CI run.
- Test-first check: before implementation, `python -m unittest tests.test_ir_lowering -v` raised `FileNotFoundError` for the missing `tools/rptp_lower.py`; no lowering module existed.
- Implementation: added `tools/rptp_lower.py` with `lower_to_cpp(result, *, return_sentinel=0x7FFF0000, max_steps=128)`. It validates an `AnalysisResult` without trusting it, re-checks code bounds and ordering, operation/control consistency, operands (including rejecting operands that do not belong to the operation) and immediate kinds, direct targets, delay-slot ownership, block coverage and successor sets, then emits deterministic C++20. Stable `LoweringError` codes cover invalid results, unsupported operations, malformed instructions, invalid control/targets/delay slots/blocks, limits and options.
- Generated-code behavior: a PC-keyed switch state machine preserves pending delay-slot targets, suppresses `$zero`, wraps `ADDIU`/`ADDU` at 32 bits, zero-extends `ORI`, uses a bounded `std::map` for initialized guest memory and emits fixed-order JSON. Uninitialized `LW` throws; generated `main` prints exactly `LOWER_RUNTIME_ERROR: read from uninitialized guest memory\n` to stderr and exits `2`. A non-code dynamic PC halts the synthetic model, matching the oracle.
- Added `tests/test_ir_lowering.py` with 11 tests: deterministic source, raw-word independence, no local paths/timestamps, the 29-instruction oracle differential, a 13-instruction dynamic-`JR` differential, the uninitialized-load failure path, and six fail-closed validation cases. Fixtures are generated at test time; no binary fixture or MANIFEST entry was added.
- Main lowering fixture: 29 instructions (`0x74` bytes), 26 executed PCs, return sentinel halt. Fixture SHA-256 `0309e92bd180203fd82f7a89d17c5c213b79515e8f2fa779803d32b62f9735b9`; generated C++ SHA-256 `8d8e960b3add141db18e78e9c86a8abdc90298117041602c4b7094da3e931a67`.
- Dynamic-`JR` fixture: 13 instructions (`0x34` bytes), 13 executed PCs, return sentinel halt, `v0 = 42`, `s1 = 9`. Fixture SHA-256 `47302fd9e04428a8dd38374896c7ba4890fd9eff5dd81ffff7168b8b968b5894`; generated C++ SHA-256 `074d639aab7e8fe42ef76b9ab6e2c9f4b8f4356501aa6469dfcbcf1115b937d0`.
- The registered Gate 0 fixture SHA-256 remains `b21f1f7793236d1ccba7308cc82f42d9f89915c87c0b037c46d8170f28349ca9`; Gate 0 generated C++ remains `5316e0f51ba8b1fa1252e409f38cb9ac7db7606fee17b28ef0dcf1be162ae795`. The ORI fixture remains `6c04b37fb40b3e7eaa29f82e7f21795bf930f0668aade41d04b1e058b8ff6dbc`; ORI generated C++ remains `2aefb52babdd9e355fd3d12f3339c5c05ee60421be8bef0f17ae8f78d848c684`.
- `python -m unittest tests.test_ir_lowering -v` from the plain shell - 11 tests, OK with 3 native skips because `cl.exe` was not on that PATH.
- `python -m unittest discover -s tests -v` from the plain shell - 117 tests, OK with 4 skips: the native ORI differential and the three native lowering tests skipped because no compiler was on that PATH.
- `scripts/run-msvc.ps1` invoked from a temporary directory outside the repository through `VsDevCmd.bat -arch=x64 -host_arch=x64` - 117 tests, OK, no skip; the three native lowering tests passed. The wrapper's Gate 0 report remained `PASS_LOCAL_DIFFERENTIAL_SPIKE`, `native_matches_oracle: true`, `windows_msvc_verified: true`, 28 instructions, 22 trace steps, with the unchanged fixture and generated-source hashes above.
- `python tools/rptp_doctor.py` through `VsDevCmd.bat` - PASS. `cmake --preset windows-msvc` and `cmake --build --preset windows-msvc` - PASS; CTest 3/3 PASS in 10.19s.
- `python tools/check_forbidden_artifacts.py --root .` - PASS. `python -m compileall -q tools tests` - PASS. The synthetic fixture manifest was unchanged.
- Relative-link check: 113 relative links across all 34 Markdown files - PASS; all resolve to existing repository paths.
- `python tools/rptp_progress.py` - PASS; regenerated `docs/progress.html`, `docs/assets/progress.svg` and `docs/assets/badge-runtime.svg`. The runtime checklist moved from 0.0% to 5.0% (1 of 20 items verified, `IR`); the foundation checklist remains 77.8% (14 of 18). `docs/assets/badge-foundation.svg` was unchanged.
- `git diff --check` - PASS for whitespace errors; Git emitted LF-to-CRLF normalization warnings for modified text and generated files. No whitespace error was reported.
- Documentation updated: `README.md`, `docs/STATE.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`, `docs/IR_CFG.md`, `docs/INSTRUCTION_CATALOG.md`, `docs/CLEAN_ROOM_AUDIT.md`, `docs/REFERENCES.md`, `docs/COMPATIBILITY.md`, `docs/EXECUTION_CONTEXT.md`, `docs/BUILD_PROVENANCE.md`, `docs/ISO_INSPECTOR.md`, `docs/GATE0_REVIEW.md`, `docs/GATE2_EVIDENCE.md`, the progress generator/assets and this log. No new ADR was required; no dependency was added.
- Gate 3 remains **not passed**. The generated code is a synthetic test artifact, not a product recompiler, runtime, function-extent result or compatibility claim. These are local results only; the changes are not pushed and have no CI run.

## 2026-10-23 - Gate 3 ANDI/XORI logical immediates

Base commit: `9c4f6756c4daddfb1a55fea95af1fffbd774b25b`; the source, test and documentation changes in this entry were uncommitted during the checks. Environment: Windows 11 x64, Python 3.13.16, Visual Studio 2026 Community, MSVC toolset 14.51.36231, CMake 4.4.4 and Ninja 1.13.2 through the Visual Studio developer environment. No retail ISO or sealed project material was accessed. Published baseline `9c4f675` is green in CI run `39860776782`; this increment has no CI run yet.

- Test-first check: before implementation, `python -m unittest tests.test_instruction_logical -v` reported 6 errors, 1 pass and 1 skip. The errors came from decoder rejection of the new `ANDI`/`XORI` encodings; the already-existing unsupported-opcode test passed, and the native differential skipped without a compiler on `PATH`.
- Added `tests/test_instruction_logical.py` with 8 tests: decode and zero-extension, unknown-opcode rejection, IR destination/immediate checks, oracle masking/toggling/zero-extension, native lowering differential, deterministic source independent of raw words, malformed immediate-kind rejection and missing-operand rejection.
- Implementation: `tools/rptp_gate0_spike.py` recognizes I-type opcodes `0x0C` (`ANDI`) and `0x0E` (`XORI`) and applies the low-32-bit operation with a zero-extended immediate, zero-extended result and `$zero` suppression. `tools/rptp_ir.py` classifies both as fallthrough `ZERO16` operations with modeled destinations. `tools/rptp_lower.py` validates both operations and emits dynamic `andi32`/`ori32`/`xori32` helpers only when used; the existing ORI-only output is unchanged.
- Logical-immediate fixture: 18 instructions (`0x48` bytes), 18 executed PCs, return sentinel halt. Fixture SHA-256 `475209a09cadcd0e95fb52f7e5a44c5001d4eee97528d3c578d011c123a74c15`; generated C++ SHA-256 `2eece492ca8626d70d5bc7f45cecc02e731ea5244c0cefeb0d57673141e90306`.
- The registered Gate 0 fixture SHA-256 remains `b21f1f7793236d1ccba7308cc82f42d9f89915c87c0b037c46d8170f28349ca9`; Gate 0 generated C++ remains `5316e0f51ba8b1fa1252e409f38cb9ac7db7606fee17b28ef0dcf1be162ae795`. The ORI fixture and generated C++ hashes are also unchanged.
- `python -m unittest tests.test_instruction_logical -v` from the plain shell - 8 tests, OK with 1 native skip because `cl.exe` was not on that PATH.
- `python -m unittest tests.test_ir_cfg tests.test_ir_lowering tests.test_instruction_ori -v` - PASS; the unchanged Gate 0/ORI invariants and existing lowering behavior were rechecked.
- `python -m unittest discover -s tests` from the plain shell - 125 tests, OK with 5 skips: the native ORI differential, the three native lowering tests and the new native logical-immediate test skipped because no compiler was on that PATH.
- `scripts/run-msvc.ps1` through `VsDevCmd.bat -arch=x64 -host_arch=x64` - 125 tests, OK, no skip. The native `ANDI`/`XORI` differential passed. The Gate 0 report remained `PASS_LOCAL_DIFFERENTIAL_SPIKE`, `native_matches_oracle: true`, `windows_msvc_verified: true`, 28 instructions, 22 trace steps, with the unchanged fixture and generated-source hashes above.
- `python tools/rptp_doctor.py` through `VsDevCmd.bat` - PASS. `cmake --preset windows-msvc` and `cmake --build --preset windows-msvc` - PASS; CTest 3/3 PASS in 11.81s.
- `python -m compileall -q tools tests` - PASS. `python tools/check_forbidden_artifacts.py` - PASS. The synthetic fixture manifest was unchanged; no binary fixture was added.
- Relative-link check: 114 relative links across 32 Markdown files (README plus `docs/`) - PASS; all resolve to existing repository paths.
- `python tools/rptp_progress.py` - PASS; regenerated the progress page and SVG assets. `tests.test_progress_consistency` passed. Checklist percentages are unchanged (foundation 77.8%, runtime 5.0%).
- `git diff --check` - PASS for whitespace errors; Git emitted LF-to-CRLF normalization warnings for modified text and generated files. No whitespace error was reported.
- Documentation updated: `README.md`, `docs/STATE.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`, `docs/IR_CFG.md`, `docs/INSTRUCTION_CATALOG.md`, `docs/CLEAN_ROOM_AUDIT.md`, `docs/REFERENCES.md`, `docs/COMPATIBILITY.md`, `docs/EXECUTION_CONTEXT.md`, `docs/BUILD_PROVENANCE.md`, `docs/ISO_INSPECTOR.md`, `docs/GATE0_REVIEW.md`, `docs/GATE2_EVIDENCE.md`, the progress generator/assets and this log. No new ADR was required; no dependency was added.
- Gate 3 remains **not passed**. `ANDI`/`XORI` are synthetic-only additions; there is no product recompiler, function discovery, runtime or compatibility claim. These are local results only; the changes are not pushed and have no CI run.

## 2026-10-23 - Gate 3 LUI shifted immediate

Base commit: `83c7c6aa460111a6b57ab25ffb745c205d8c39ff`; the source, test and documentation changes in this entry were uncommitted during the checks. Environment: Windows 11 x64, Python 3.13.16, Visual Studio 2026 Community, MSVC toolset 14.51.36231, CMake 4.4.4 and Ninja 1.13.2 through the Visual Studio developer environment. No retail ISO or sealed project material was accessed. Published baseline `83c7c6a` is green in CI run `39908025708`; this increment has no CI run yet.

- Reference check: the requested MIPS64 Revision 6.03 official PDF URL redirected and then returned HTTP 403. A Rev 6.03 mirror confirmed the document identity and table of contents, but its LUI page was not extractable. The full-text Rev 5.04 mirror was readable; page 225 states that the 16-bit immediate is shifted left 16 bits, concatenated with 16 zeros, and the 32-bit result is sign-extended. The checked passage and access limits are recorded as `RPTP-REF-013`; R-021 records the residual provenance limitation. No claim is made that the Rev 6.03 LUI page was inspected.
- Test-first check: before implementation, `python -m unittest tests.test_instruction_lui -v` reported 8 tests with 2 failures, 5 errors and 1 skip. The decoder rejected opcode `0x0F` as unsupported; the native differential skipped because `cl.exe` was not on the plain-shell `PATH`. The output was not synthesized or backfilled.
- Added `tests/test_instruction_lui.py` with 8 tests: decode of the shifted immediate and zero `rs`, nonzero-`rs` rejection, IR immediate-kind/destination metadata, fail-closed IR rejection, all five boundary values plus `$zero` in the oracle, native oracle/IR-lowering equality, deterministic source independent of raw-word-only changes, and malformed metadata rejection (nonzero/missing `rs`, wrong immediate kind, out-of-range immediate, wrong destination).
- Implementation: `tools/rptp_gate0_spike.py` decodes opcode `0x0F` only when `rs=0`, records the raw immediate, and in the oracle shifts it left 16 bits and sign-extends the 32-bit result; `$zero` writes are suppressed. `tools/rptp_ir.py` adds the `shifted16` immediate kind and the modeled destination, and rejects nonzero `rs`. `tools/rptp_lower.py` validates `lui` metadata independently, emits a conditional `lui32` helper, and does not re-decode raw words. `spike.emit_cpp` was not used or extended for this path.
- The existing `tests/test_instruction_logical.py` test that treated `0x0F` as an unknown opcode was updated to assert that it is not treated as a logical immediate and is rejected for nonzero `rs`; this follows the new supported encoding and is not a weakened assertion.
- LUI fixture: 9 instructions (`0x24` bytes), 9 executed PCs, return sentinel halt. It contains five boundary immediates, one `$zero` destination, `ADDIU`, `JR $ra` and a NOP delay slot. Fixture SHA-256 `e62d461c04b56905a709b59d38c6bb69f2e408890e567926cdf49a69cc8e53e3`; generated C++ SHA-256 `af8c7313f6a4b28bc34655aedc489743f695b8dde943ee8881ea6e4f83cdab30`. Fixture size is 4132 bytes; generated source size is 5270 bytes.
- The registered Gate 0 fixture and generated C++ hashes remain `b21f1f7793236d1ccba7308cc82f42d9f89915c87c0b037c46d8170f28349ca9` and `5316e0f51ba8b1fa1252e409f38cb9ac7db7606fee17b28ef0dcf1be162ae795`. The ORI fixture and generated C++ hashes remain `6c04b37fb40b3e7eaa29f82e7f21795bf930f0668aade41d04b1e058b8ff6dbc` and `2aefb52babdd9e355fd3d12f3339c5c05ee60421be8bef0f17ae8f78d848c684`. The ANDI/XORI fixture and generated C++ hashes remain `475209a09cadcd0e95fb52f7e5a44c5001d4eee97528d3c578d011c123a74c15` and `2eece492ca8626d70d5bc7f45cecc02e731ea5244c0cefeb0d57673141e90306`. No binary fixture or MANIFEST entry was added.
- `python -m unittest tests.test_instruction_lui -v` from the plain shell - 8 tests, OK with 1 native skip because `cl.exe` was not on that PATH.
- `python -m unittest tests.test_ir_cfg -v` - 18 tests, OK. `python -m unittest tests.test_ir_lowering -v` - 11 tests, OK with 3 native skips in the plain shell.
- `python -m unittest discover -s tests -v` from the plain shell - 133 tests, OK with 6 skips: the native ORI, ANDI/XORI, LUI and three native lowering tests skipped because no compiler was on that PATH.
- `scripts/run-msvc.ps1` through `VsDevCmd.bat -arch=x64 -host_arch=x64` - 133 tests, OK, no skip. The native LUI differential passed. The Gate 0 report remained `PASS_LOCAL_DIFFERENTIAL_SPIKE`, `native_matches_oracle: true`, `windows_msvc_verified: true`, 28 instructions, 22 trace steps, with the unchanged fixture and generated-source hashes above.
- `python tools/rptp_doctor.py` from the plain shell - FAIL because `cl.exe` was not on `PATH`; from the Visual Studio developer environment - PASS. `cmake --preset windows-msvc` and `cmake --build --preset windows-msvc` - PASS; the build target ran CTest 3/3 PASS. `CMakePresets.json` has no `testPresets`, so `ctest --preset windows-msvc` is not defined; `ctest --test-dir build/cmake-msvc --output-on-failure` - 3/3 PASS.
- `python tools/check_forbidden_artifacts.py --root .` - PASS. `python -m compileall -q tools tests` - PASS. The synthetic fixture manifest was unchanged.
- Relative-link check: 116 relative links across 32 Markdown files - PASS; all resolve to existing repository paths.
- `python tools/rptp_progress.py` - PASS; regenerated the progress page and SVG assets. Checklist percentages are unchanged (foundation 77.8%, runtime 5.0%).
- `git diff --check` - PASS for whitespace errors; Git emitted LF-to-CRLF normalization warnings for modified text and generated files. No whitespace error was reported.
- Documentation updated: `README.md`, `docs/STATE.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`, `docs/IR_CFG.md`, `docs/INSTRUCTION_CATALOG.md`, `docs/CLEAN_ROOM_AUDIT.md`, `docs/REFERENCES.md`, `docs/RISKS.md`, `docs/COMPATIBILITY.md`, `docs/EXECUTION_CONTEXT.md`, `docs/BUILD_PROVENANCE.md`, `docs/ISO_INSPECTOR.md`, `docs/GATE0_REVIEW.md`, `docs/GATE2_EVIDENCE.md`, the progress generator/assets and this log. No new ADR was required; no dependency was added.
- Gate 3 remains **not passed**. `LUI` is a synthetic-only addition; there is no product recompiler, function discovery, runtime or compatibility claim. These are local results only; the changes are not pushed and have no CI run.

## 2026-10-24 - Gate 3 AND/OR/XOR register logical operations

Base commit: `3dbe3f1a6dce810c5573a07a07508c5f64043e36`; the source, test and documentation changes in this entry were uncommitted during the checks. Environment: Windows 11 x64, Python 3.13.16, Visual Studio 2026 Community, MSVC toolset 14.51.36231, CMake 4.4.4 and Ninja 1.13.2 through the Visual Studio developer environment. No retail ISO or sealed project material was accessed. Published baseline `3dbe3f1` is green in CI run `39920189021`; this increment has no CI run.

- Reference check: the already-recorded `RPTP-REF-001` and `RPTP-REF-002` entries cover the generic MIPS `SPECIAL` function codes and bitwise operation names used here. The full modeled 64-bit operation width is an RPTP test definition, not a claim of complete R5900 hardware behavior.
- Test-first check: before implementation, `python -m unittest tests.test_instruction_register_logic -v` failed because the decoder rejected `SPECIAL` functions `0x24`-`0x26`, and the oracle, IR and lowerer did not support the three operations. The native differential skipped because `cl.exe` was not on the plain-shell `PATH`. The output was not synthesized or backfilled.
- Added `tests/test_instruction_register_logic.py` with 10 tests: decode of the three functions and zero `shamt`, nonzero-`shamt` and unsupported-function/opcode rejection, IR destination/operand/fallthrough metadata, fail-closed IR rejection, full 64-bit oracle results, deterministic lowering independent of raw words, malformed-metadata rejection, unsupported-operation rejection and native oracle/IR-lowering equality.
- Implementation: `tools/rptp_gate0_spike.py` decodes `SPECIAL` funct `0x24` (`AND`), `0x25` (`OR`) and `0x26` (`XOR`) only when `shamt=0`; the oracle applies the bitwise operation to the full modeled 64-bit register values and suppresses `$zero`. `tools/rptp_ir.py` classifies the operations as fallthrough and records `rd`, `rs` and `rt`. `tools/rptp_lower.py` validates all three operands, the expected destination and control metadata, then emits direct full-width C++ bitwise expressions without re-decoding raw words. `spike.emit_cpp` was not changed.
- The existing unsupported-operation test in `tests/test_ir_lowering.py` now uses `nor` instead of `xor`, because `xor` is supported. The fail-closed assertion itself is unchanged and was not weakened.
- Register-logical fixture: 24 instructions (`0x60` bytes), 24 executed PCs, return sentinel halt. It composes `AND`, `OR` and `XOR` with `LUI` and `ADDIU` and covers upper-bit patterns, intersection/union/difference, all-zero/all-one values, `$zero` suppression, destination/source aliasing and distinct destinations. Fixture size is 4192 bytes; generated source size is 7680 bytes. Fixture SHA-256 `c1a37d766bdb6ed11630726339116d5f793239d46dccfc3da8b50ed4ab086863`; generated C++ SHA-256 `a23bb334efdf437d2b852f12746be1b15ce50f0c46d8a84101a7e16475f86ad7`.
- The registered Gate 0 fixture and generated C++ hashes remain `b21f1f7793236d1ccba7308cc82f42d9f89915c87c0b037c46d8170f28349ca9` and `5316e0f51ba8b1fa1252e409f38cb9ac7db7606fee17b28ef0dcf1be162ae795`. The ORI fixture and generated C++ hashes remain `6c04b37fb40b3e7eaa29f82e7f21795bf930f0668aade41d04b1e058b8ff6dbc` and `2aefb52babdd9e355fd3d12f3339c5c05ee60421be8bef0f17ae8f78d848c684`. The ANDI/XORI fixture and generated C++ hashes remain `475209a09cadcd0e95fb52f7e5a44c5001d4eee97528d3c578d011c123a74c15` and `2eece492ca8626d70d5bc7f45cecc02e731ea5244c0cefeb0d57673141e90306`. The LUI fixture and generated C++ hashes remain `e62d461c04b56905a709b59d38c6bb69f2e408890e567926cdf49a69cc8e53e3` and `af8c7313f6a4b28bc34655aedc489743f695b8dde943ee8881ea6e4f83cdab30`. No binary fixture or MANIFEST entry was added.
- `python -m unittest tests.test_instruction_register_logic -v` from the plain shell - 10 tests, OK with 1 native skip because `cl.exe` was not on that PATH.
- `python -m unittest discover -s tests -v` from the plain shell - 143 tests, OK with 7 skips: the native ORI, ANDI/XORI, LUI, register-logical and three native lowering tests skipped because no compiler was on that PATH.
- `scripts/run-msvc.ps1` through `VsDevCmd.bat -arch=x64 -host_arch=x64` - 143 tests, OK, no skip; the native register-logical differential passed. The Gate 0 report remained `PASS_LOCAL_DIFFERENTIAL_SPIKE`, `native_matches_oracle: true`, `windows_msvc_verified: true`, 28 instructions, 22 trace steps, with the unchanged fixture and generated-source hashes above.
- `python tools/rptp_doctor.py` through `VsDevCmd.bat` - PASS; Python 3.13.16, MSVC 14.51.36231, CMake, Ninja, git, required layout and artifact guard all passed. `cmake --preset windows-msvc` and `cmake --build --preset windows-msvc` - PASS; the build target ran CTest 3/3 PASS. `ctest --test-dir build/cmake-msvc --output-on-failure` - 3/3 PASS.
- `python -m compileall -q tools tests` - PASS. `python tools/check_forbidden_artifacts.py --root .` - PASS. The synthetic fixture manifest was unchanged.
- Relative-link check: 117 relative links across 32 Markdown files - PASS; all resolve to existing repository paths.
- `python tools/rptp_progress.py` - PASS; regenerated the progress page and SVG assets. Checklist percentages are unchanged (foundation 77.8%, runtime 5.0%); the generated text includes `AND`/`OR`/`XOR`.
- `git diff --check` - PASS for whitespace errors; Git emitted LF-to-CRLF normalization warnings for modified text and generated files. No whitespace error was reported.
- Documentation updated: `README.md`, `docs/STATE.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`, `docs/IR_CFG.md`, `docs/INSTRUCTION_CATALOG.md`, `docs/CLEAN_ROOM_AUDIT.md`, `docs/REFERENCES.md`, `docs/COMPATIBILITY.md`, `docs/EXECUTION_CONTEXT.md`, `docs/BUILD_PROVENANCE.md`, `docs/ISO_INSPECTOR.md`, `docs/GATE0_REVIEW.md`, `docs/GATE2_EVIDENCE.md`, the progress generator/assets and this log. No new ADR was required; no dependency was added.
- Gate 3 remains **not passed**. `AND`, `OR` and `XOR` are synthetic-only additions; there is no product recompiler, function discovery, runtime or compatibility claim. These are local results only; the changes are not pushed and have no CI run.

## 2026-10-24 - Gate 3 NOR register operation

Base commit: `f3782c90a638789163a0b6ad4f174642d0070c5a`; the source, test and documentation changes in this entry were uncommitted during the checks. Environment: Windows 11 x64, Python 3.13.16, Visual Studio 2026 Community, MSVC toolset 14.51.36231, CMake 4.4.4 and Ninja 1.13.2 through the Visual Studio developer environment. No retail ISO or sealed project material was accessed. Published baseline `f3782c9` is green in CI run `39994586188` on Windows x64/MSVC and Linux/GCC; this increment has no CI run.

- Precondition check: `git fetch --prune origin` showed `HEAD = origin/main = f3782c90a638789163a0b6ad4f174642d0070c5a`, and `git merge-base --is-ancestor f3782c9 origin/main` passed. GitHub REST reported run `39994586188` (`RPTP CI`, push) completed successfully with both `Windows x64 / MSVC` and `Linux / GCC` jobs successful.
- Reference check: the already-recorded `RPTP-REF-001` and `RPTP-REF-002` entries cover `NOR` `SPECIAL` funct `0x27` and the bitwise operation name. The neutral reference pages were checked again on 2026-10-24. The full modeled 64-bit operation width is an RPTP test definition, not a claim of complete R5900 hardware behavior.
- Test-first check: before implementation, `python -m unittest tests.test_instruction_nor -v` ran 10 tests and failed with `errors=6, skipped=1`; the representative failure was `IR_UNSUPPORTED_INSTRUCTION: Unsupported SPECIAL instruction 0x01095027 at 0x00100008 at 0x00100008`. The native differential skipped because `cl.exe` was not on the plain-shell `PATH`. The output was not synthesized or backfilled.
- Added `tests/test_instruction_nor.py` with 10 tests: decode of funct `0x27` and zero `shamt`, nonzero-`shamt` and unsupported-function/opcode rejection, IR destination/operand/fallthrough metadata, fail-closed IR rejection, full 64-bit oracle results, deterministic lowering independent of raw words, malformed-metadata rejection, unsupported-operation rejection and native oracle/IR-lowering equality.
- Implementation: `tools/rptp_gate0_spike.py` decodes `SPECIAL` funct `0x27` (`NOR`) only when `shamt=0`; the oracle applies `~(rs | rt)` to the full modeled 64-bit register values and suppresses `$zero`. `tools/rptp_ir.py` classifies `nor` as fallthrough and records `rd`, `rs` and `rt`. `tools/rptp_lower.py` validates all three operands, the expected destination and control metadata, then emits the direct full-width C++ expression `~(s.registers[rs] | s.registers[rt])` without re-decoding raw words. `spike.emit_cpp` was not changed.
- The existing unsupported-operation tests in `tests/test_instruction_register_logic.py` and `tests/test_ir_lowering.py` now use `slt` instead of `nor`, because `nor` is supported. The fail-closed assertions themselves are unchanged and were not weakened.
- NOR fixture: 16 instructions (`0x40` bytes), 4160 bytes including the ELF wrapper, 16 executed PCs, return sentinel halt. It composes `NOR` with `LUI` and `ADDIU` and covers all-zero/all-one results, upper-bit patterns, `rs == rt`, `$zero` suppression, destination/source aliasing in both directions and malformed encodings/IR. Generated source size is 6453 bytes. Fixture SHA-256 `21e8eb8c01844341374857cd0d866f26e476bc280c8070161f7d7c42756064f6`; generated C++ SHA-256 `96aeeef878ee7ec523cdf21d6ecd6f6c7022bfbda02d8329bc01be20a0eb0572`.
- The registered Gate 0 fixture and generated C++ hashes remain `b21f1f7793236d1ccba7308cc82f42d9f89915c87c0b037c46d8170f28349ca9` and `5316e0f51ba8b1fa1252e409f38cb9ac7db7606fee17b28ef0dcf1be162ae795`. The ORI fixture and generated C++ hashes remain `6c04b37fb40b3e7eaa29f82e7f21795bf930f0668aade41d04b1e058b8ff6dbc` and `2aefb52babdd9e355fd3d12f3339c5c05ee60421be8bef0f17ae8f78d848c684`. The ANDI/XORI fixture and generated C++ hashes remain `475209a09cadcd0e95fb52f7e5a44c5001d4eee97528d3c578d011c123a74c15` and `2eece492ca8626d70d5bc7f45cecc02e731ea5244c0cefeb0d57673141e90306`. The LUI fixture and generated C++ hashes remain `e62d461c04b56905a709b59d38c6bb69f2e408890e567926cdf49a69cc8e53e3` and `af8c7313f6a4b28bc34655aedc489743f695b8dde943ee8881ea6e4f83cdab30`. The prior AND/OR/XOR hashes also remained `c1a37d766bdb6ed11630726339116d5f793239d46dccfc3da8b50ed4ab086863` and `a23bb334efdf437d2b852f12746be1b15ce50f0c46d8a84101a7e16475f86ad7`. No binary fixture or MANIFEST entry was added.
- `python -m unittest tests.test_instruction_nor -v` after implementation from the plain shell - 10 tests, OK with 1 native skip because `cl.exe` was not on that PATH.
- `python -m unittest discover -s tests -v` from the plain shell - 153 tests, OK with 8 skips: the native ORI, ANDI/XORI, LUI, register-logical, NOR and three native lowering tests skipped because no compiler was on that PATH.
- `scripts/run-msvc.ps1` through `VsDevCmd.bat -arch=x64 -host_arch=x64` - 153 tests, OK, no skip; the native NOR differential passed. The Gate 0 report remained `PASS_LOCAL_DIFFERENTIAL_SPIKE`, `native_matches_oracle: true`, `windows_msvc_verified: true`, 28 instructions and 22 trace steps.
- `python tools/rptp_doctor.py` through `VsDevCmd.bat` - PASS; Python 3.13.16, MSVC 14.51.36231, CMake, Ninja, git, required layout and artifact guard all passed. `cmake --preset windows-msvc` and `cmake --build --preset windows-msvc` - PASS; the build target ran CTest 3/3 PASS. `ctest --test-dir build/cmake-msvc --output-on-failure` - 3/3 PASS.
- `python -m compileall -q tools tests` - PASS. `python tools/check_forbidden_artifacts.py --root .` - PASS. The synthetic fixture manifest was unchanged.
- Relative-link check: 118 relative links across 32 Markdown files - PASS; all resolve to existing repository paths.
- `python tools/rptp_progress.py` - PASS; regenerated the progress page and SVG assets. Checklist percentages are unchanged (foundation 77.8%, runtime 5.0%); the generated text includes `NOR`.
- `git diff --check` - PASS for whitespace errors; Git emitted LF-to-CRLF normalization warnings for modified text and generated files. No whitespace error was reported.
- Documentation updated: `README.md`, `docs/STATE.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`, `docs/IR_CFG.md`, `docs/INSTRUCTION_CATALOG.md`, `docs/CLEAN_ROOM_AUDIT.md`, `docs/REFERENCES.md`, `docs/COMPATIBILITY.md`, `docs/EXECUTION_CONTEXT.md`, `docs/BUILD_PROVENANCE.md`, `docs/ISO_INSPECTOR.md`, `docs/GATE0_REVIEW.md`, `docs/GATE2_EVIDENCE.md`, the progress generator/assets and this log. No new ADR was required; no dependency was added.
- Gate 3 remains **not passed**. `NOR` is a synthetic-only addition; there is no product recompiler, function discovery, runtime or compatibility claim. These are local results only; the changes are not pushed and have no CI run.

## 2026-10-24 - Gate 3 SLT register comparison

Base commit: `b98ee1dce7056105468f2f412bbaa996d576cc61`; the source, test and documentation changes in this entry were uncommitted during the checks. Environment: Windows 11 x64, Python 3.13.16, Visual Studio 2026 Community, MSVC toolset 14.51.36231, CMake 4.4.4 and Ninja 1.13.2 through the Visual Studio developer environment. No retail ISO or sealed project material was accessed. Published baseline `b98ee1d` is green in CI run `39999387250` on Windows x64/MSVC and Linux/GCC; this increment has no CI run.

- Precondition check from the prior published state: `HEAD = origin/main = b98ee1dce7056105468f2f412bbaa996d576cc61`; GitHub REST reported run `39999387250` (`RPTP CI`, push) completed successfully with both `Windows x64 / MSVC` and `Linux / GCC` jobs successful.
- Reference check: the permitted `RPTP-REF-001` (University of Waterloo MIPS encoding reference) and `RPTP-REF-002` (UNSW MIPS guide) pages were fetched again on 2026-10-24. Both identify `SLT` as `SPECIAL` function code `0x2A` and describe signed set-on-less-than. The full modeled 64-bit width is an RPTP test definition, not a claim of complete R5900 hardware behavior.
- Test-first check: before implementation, `python -m unittest tests.test_instruction_slt -v` ran 12 tests and failed with `errors=12, skipped=2`; the representative failure was `ValueError: Unsupported SPECIAL instruction 0x0109502A at 0x00100000`, with IR failures reporting `IR_UNSUPPORTED_INSTRUCTION`. The two native tests skipped because `cl.exe` was not on the plain-shell `PATH`. The output was not synthesized or backfilled.
- Added `tests/test_instruction_slt.py` with 12 tests: decode of funct `0x2A` and zero `shamt`, nonzero-`shamt` and unsupported-function/opcode rejection, IR destination/operand/fallthrough metadata, fail-closed IR rejection, signed 64-bit oracle results, helper boundary cases, deterministic lowering independent of raw words, malformed-metadata rejection, unsupported-operation rejection, native oracle/IR-lowering equality and a generated-helper boundary differential.
- Implementation: `tools/rptp_gate0_spike.py` adds `sign_extend_64`/`slt64` and decodes `SPECIAL` funct `0x2A` (`SLT`) only when `shamt=0`; the oracle compares signed two's-complement 64-bit values and suppresses `$zero`. `tools/rptp_ir.py` classifies `slt` as fallthrough and records `rd`, `rs` and `rt`. `tools/rptp_lower.py` validates all three operands, the expected destination and control metadata, then emits a conditional `slt64` helper that compares sign bits first and unsigned magnitudes for same-sign values, avoiding implementation-defined signed casts. `spike.emit_cpp` was not changed.
- The existing unsupported-operation tests in `tests/test_instruction_nor.py`, `tests/test_instruction_register_logic.py` and `tests/test_ir_lowering.py` now use `sltu` instead of `slt`, because `slt` is supported. The fail-closed assertions themselves are unchanged and were not weakened.
- SLT fixture: 20 instructions (`0x50` bytes), 4176 bytes including the ELF wrapper, 20 executed PCs, return sentinel halt. It composes `SLT` with `ADDIU`, `LUI`, `JR $ra` and a NOP delay slot and covers negative/zero, positive/negative, equality, `$zero` destination and source, both alias directions and high-bit sign patterns. Fixture SHA-256 `9bb286bc242c7822fe8af36e25a8245d1fba75fda2cc21a94c4eee0a6b196fa3`; generated C++ SHA-256 `fba70199d9448267f13a95ab03e1216858dbe8f7a3a77b9858d5f7963db2b2da`.
- The registered Gate 0 fixture and generated C++ hashes remain `b21f1f7793236d1ccba7308cc82f42d9f89915c87c0b037c46d8170f28349ca9` and `5316e0f51ba8b1fa1252e409f38cb9ac7db7606fee17b28ef0dcf1be162ae795`. The ORI, ANDI/XORI, LUI, AND/OR/XOR, NOR and 29-instruction lowering fixture/generated-source hashes were recomputed and remained unchanged. No binary fixture or MANIFEST entry was added.
- The SLT boundary native test emits a generated-source harness and seeds `State` directly at `INT64_MIN`/`INT64_MAX`, because the synthetic encoder cannot materialize arbitrary 64-bit constants. This is a documented test seam; the encoded 20-instruction fixture exercises the normal path.
- `python -m unittest tests.test_instruction_slt -v` from the plain shell - 12 tests, OK with 2 native skips because `cl.exe` was not on that PATH.
- `python -m unittest tests.test_instruction_slt -v` through `VsDevCmd.bat -arch=x64 -host_arch=x64` - 12 tests, OK, no skip; both native SLT tests passed.
- `python -m unittest discover -s tests` from the plain shell - 165 tests, OK with 10 skips: the native ORI, ANDI/XORI, LUI, register-logical, NOR, SLT and three native lowering tests skipped because no compiler was on that PATH.
- `scripts/run-msvc.ps1` through `VsDevCmd.bat -arch=x64 -host_arch=x64` - 165 tests, OK, no skip; the native SLT differential and boundary differential passed. The Gate 0 report remained `PASS_LOCAL_DIFFERENTIAL_SPIKE`, `native_matches_oracle: true`, `windows_msvc_verified: true`, 28 instructions and 22 trace steps.
- `python tools/rptp_doctor.py` through `VsDevCmd.bat` - PASS; Python 3.13.16, MSVC 14.51.36231, CMake, Ninja, git, required layout and artifact guard all passed. `cmake --preset windows-msvc` and `cmake --build --preset windows-msvc` - PASS; the build target ran CTest 3/3 PASS. `ctest --test-dir build/cmake-msvc --output-on-failure` - 3/3 PASS.
- `python -m compileall -q tools tests` - PASS. `python tools/check_forbidden_artifacts.py --root .` - PASS. The synthetic fixture manifest was unchanged.
- Relative-link check: 119 relative Markdown links across 32 files - PASS; all resolve to existing repository paths.
- `python tools/rptp_progress.py` - PASS; regenerated the progress page and SVG assets with the 2026-10-24 snapshot date. Checklist percentages are unchanged (foundation 77.8%, runtime 5.0%); the generated text includes `SLT`.
- `git diff --check` - PASS for whitespace errors; Git emitted LF-to-CRLF normalization warnings for modified text and generated files. No whitespace error was reported.
- Documentation updated: `README.md`, `docs/STATE.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`, `docs/IR_CFG.md`, `docs/INSTRUCTION_CATALOG.md`, `docs/CLEAN_ROOM_AUDIT.md`, `docs/REFERENCES.md`, `docs/COMPATIBILITY.md`, `docs/EXECUTION_CONTEXT.md`, `docs/BUILD_PROVENANCE.md`, `docs/ISO_INSPECTOR.md`, `docs/GATE0_REVIEW.md`, `docs/GATE2_EVIDENCE.md`, the progress generator/assets and this log. No new ADR was required; no dependency was added.
- Gate 3 remains **not passed**. `SLT` is a synthetic-only addition; there is no product recompiler, function discovery, runtime or compatibility claim. These are local results only; the changes are not pushed and have no CI run.

## 2026-10-24 - Gate 3 known-edge CFG graph reachability

Base commit: `bbb17385c8639f5b6695cafe9b6c3d7977aa72f9`; the source, test and documentation changes in this entry were uncommitted during the checks. Environment: Windows 11 x64, Python 3.13.16, Visual Studio 2026 Community, MSVC toolset 14.51.36231, CMake 4.4.4 and Ninja 1.13.2 through the Visual Studio developer environment. No retail ISO or sealed project material was accessed. Published baseline `bbb1738` is green in CI run `40003992195` on Windows x64/MSVC and Linux/GCC; this increment has no CI run.

- Precondition check from the prior published state: `HEAD = origin/main = bbb17385c8639f5b6695cafe9b6c3d7977aa72f9`; GitHub REST reported run `40003992195` (`RPTP CI`, push) completed successfully with both `Windows x64 / MSVC` and `Linux / GCC` jobs successful.
- Reference check: no new external hardware behavior was added. Reachability is defined over the existing RPTP CFG successor sets and test-defined validation rules; the limitations explicitly deny runtime reachability, dead-code and function-extent claims. No sealed implementation material was used.
- Test-first check: before implementation, the initial 17-test `tests/test_cfg_reachability.py` module reported 17 errors because `analyze_known_edge_reachability` did not exist. One deterministic-ordering test was added afterward and the final module contains 18 tests. The failure output was not synthesized or backfilled.
- Added `tests/test_cfg_reachability.py` with 18 synthetic tests: linear traversal, a conditional branch's two stored successors, an explicit non-entry root, direct `J` and `JAL` targets, the absent call-return edge, an unreferenced block, stable ordering of multiple unreached blocks, unresolved indirect `JR`, a return candidate, unaligned/out-of-range/delay-slot/non-block-start/non-integer roots, missing/duplicate/overlapping blocks, malformed successors, invalid result objects, deterministic repeated analysis and non-mutation.
- Implementation: `tools/rptp_ir.py` adds `KNOWN_EDGE_REACHABILITY_MODEL`, `KNOWN_EDGE_LIMITATIONS`, stable `IR_REACHABILITY_*` errors, the frozen `KnownEdgeReachability` result with `to_dict()`, and `analyze_known_edge_reachability(result, root_pc)`. It re-derives the CFG with `discover_blocks`, requires an exact block partition and matching code bounds, validates the root as a known block start outside delay slots, and traverses only stored successors.
- The report preserves deterministic block order, records reached and not-reached starts, reached unresolved indirect/return blocks and reached direct-call blocks, and fails closed on an unknown successor. It synthesizes no fallthrough, indirect target or call-return edge. The limitation text states the unresolved-jump and direct-call continuation caveats and says the report is not runtime reachability, dead-code evidence or a function-extent claim.
- No binary fixture or `MANIFEST` entry was added. Existing fixture and generated-source hash regressions for the registered Gate 0, ORI, ANDI/XORI, LUI, register-logical, NOR and SLT paths remained green; no registered fixture was modified.
- `python -m unittest tests.test_cfg_reachability -v` from the plain shell - 18 tests, OK.
- `python -m unittest discover -s tests -v` from the plain shell - 183 tests, OK with 10 skips: the native ORI, ANDI/XORI, LUI, register-logical, NOR, SLT, SLT-boundary and three native lowering tests skipped because no compiler was on that PATH.
- `scripts/run-msvc.ps1` through `VsDevCmd.bat -arch=x64 -host_arch=x64` - 183 tests, OK, no skip. The Gate 0 report remained `PASS_LOCAL_DIFFERENTIAL_SPIKE`, `native_matches_oracle: true`, `windows_msvc_verified: true`, 28 instructions and 22 trace steps, with unchanged fixture and generated-source hashes.
- `python tools/rptp_doctor.py` through `VsDevCmd.bat` - PASS; Python 3.13.16, MSVC 14.51.36231, CMake, Ninja, git, required layout and artifact guard all passed. `cmake --preset windows-msvc` and `cmake --build --preset windows-msvc` - PASS; the build target ran CTest 3/3 PASS. `ctest --test-dir build/cmake-msvc --output-on-failure` - 3/3 PASS.
- `python -m compileall -q tools tests` - PASS. `python tools/check_forbidden_artifacts.py --root .` - PASS. The synthetic fixture manifest was unchanged.
- Relative-link check: 120 relative Markdown links across 32 files - PASS; all resolve to existing repository paths.
- `python tools/rptp_progress.py` - PASS; regenerated the progress page and SVG assets with the 2026-10-24 snapshot date. Checklist percentages are unchanged (foundation 77.8%, runtime 5.0%); the generated text includes known-edge reachability.
- `git diff --check` - PASS for whitespace errors; Git emitted LF-to-CRLF normalization warnings for modified text and generated files. No whitespace error was reported.
- Documentation updated: `README.md`, `docs/STATE.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`, `docs/IR_CFG.md`, `docs/INSTRUCTION_CATALOG.md`, `docs/CLEAN_ROOM_AUDIT.md`, `docs/REFERENCES.md`, `docs/COMPATIBILITY.md`, `docs/EXECUTION_CONTEXT.md`, `docs/BUILD_PROVENANCE.md`, `docs/ISO_INSPECTOR.md`, `docs/GATE0_REVIEW.md`, `docs/GATE2_EVIDENCE.md`, the progress generator/assets and this log. No new ADR was required; no dependency was added.
- Gate 3 remains **not passed**. Known-edge graph reachability is a synthetic/static analysis addition; it is not runtime reachability, function discovery, product code generation or a compatibility claim. These are local results only; the changes are not pushed and have no CI run.

## 2026-10-24 - Gate 3 SLTU unsigned comparison

Base commit: `e239527cb9cae396da1229aa172553a883321954`; the source, test and documentation changes in this entry were uncommitted during the checks. Environment: Windows 11 x64, Python 3.13.16, Visual Studio 2026 Community, MSVC toolset 14.51.36231, CMake 4.4.4, Ninja 1.13.2 and Git 2.56.0 through the Visual Studio developer environment. No retail ISO or sealed project material was accessed. Published baseline `e239527` is green in CI run `40007604212` on Windows x64/MSVC and Linux/GCC; this increment has no CI run.

- Precondition check from the prior published state: `HEAD = origin/main = e239527cb9cae396da1229aa172553a883321954`; GitHub REST reported run `40007604212` (`RPTP CI`, push) completed successfully with both `Windows x64 / MSVC` and `Linux / GCC` jobs successful. The GitHub Pages run `40007602332` also completed successfully.
- Reference check: the permitted `RPTP-REF-002` (UNSW MIPS guide) was fetched again on 2026-10-24 and explicitly lists `SLTU` as `SPECIAL` funct `0x2B` with unsigned set-on-less-than semantics. `RPTP-REF-001` was fetched as a generic encoding cross-check, but its current SLTU table row reports a conflicting function value; it is outside the RPTP permitted-use scope for `SLTU` and was not used for the function-code claim. The owner prompt explicitly specifies `0x2B`. The discrepancy is recorded in `docs/REFERENCES.md` and `docs/IR_CFG.md`. No new external source was introduced.
- Test-first check: before implementation, `python -m unittest tests.test_instruction_sltu -v` from the plain shell reported 12 tests, `errors=19` including subtest failures, and `skipped=2`. The two native tests skipped because `cl.exe` was not on that `PATH`. The failure output was not synthesized or backfilled.
- Added `tests/test_instruction_sltu.py` with 12 tests: decode of funct `0x2B` and zero `shamt`, nonzero-`shamt` and unsupported-function/opcode rejection, IR destination/operand/fallthrough metadata, fail-closed IR rejection, unsigned 64-bit oracle results, helper boundary cases, deterministic lowering independent of raw words, malformed-metadata rejection, unsupported-operation rejection, native oracle/IR-lowering equality and a generated-helper boundary differential.
- Existing unsupported-operation coverage was updated, not weakened: `SLTU` is no longer used as an unsupported example; the decode rejection uses funct `0x2C` and the lowerer rejection uses `dadd` in `tests/test_instruction_slt.py`, `tests/test_instruction_nor.py`, `tests/test_instruction_register_logic.py` and `tests/test_ir_lowering.py`.
- Implementation: `tools/rptp_gate0_spike.py` adds `sltu64` and decodes `SPECIAL` funct `0x2B` only when `shamt=0`; the oracle masks both operands to 64 bits and compares them as unsigned. `tools/rptp_ir.py` classifies `sltu` as fallthrough and records `rd`, `rs` and `rt`. `tools/rptp_lower.py` validates the three operands, expected destination and control metadata, emits only the required comparison helper, and uses `sltu64` for inline unsigned less-than. `spike.emit_cpp` was not changed.
- SLTU fixture: 26 instructions (`0x68` code bytes), 4200 bytes including the ELF wrapper, 26 executed PCs, return sentinel halt. It composes `SLTU` with `ADDIU`, `LUI`, `JR $ra` and a NOP delay slot and covers equality, zero/nonzero and all-ones operands, `$zero` destination and source, both alias directions and bit-31/bit-63 values where unsigned and signed ordering diverge. Fixture SHA-256 `d5670163e001a2abaf6e1d7d41f97d836880be3b7af2461f4fd7624d7ea4aa21`; generated C++ SHA-256 `6bdeac71496ff490fd889c6315ea4dddcfe9ccfb693e90f7f081c5a02f9b49d6`.
- The SLTU helper test covers `0`, `1`, `INT64_MIN`, `INT64_MAX` and `UINT64_MAX` unsigned ordering cases. The native boundary harness emits generated source and seeds `State` directly with high-bit and bit-31 divergences, because the synthetic encoder cannot materialize arbitrary 64-bit constants; the encoded 26-instruction fixture exercises the normal path.
- No binary fixture or `MANIFEST` entry was added. Existing fixture and generated-source hash regressions for the registered Gate 0, ORI, ANDI/XORI, LUI, register-logical, NOR and SLT paths remained green; no registered fixture was modified. The existing SLT fixture and generated-source SHA-256 values remained `9bb286bc242c7822fe8af36e25a8245d1fba75fda2cc21a94c4eee0a6b196fa3` and `fba70199d9448267f13a95ab03e1216858dbe8f7a3a77b9858d5f7963db2b2da`.
- `python -m unittest tests.test_instruction_sltu -v` from the plain shell - 12 tests, OK with 2 native skips because `cl.exe` was not on that PATH.
- `python -m unittest discover -s tests -v` from the plain shell - 195 tests, OK with 12 skips: native SLTU and prior native compiler-dependent tests skipped because no compiler was on that PATH.
- `python -m unittest tests.test_instruction_sltu -v` through `VsDevCmd.bat -arch=x64 -host_arch=x64` - 12 tests, OK, no skip; both native SLTU tests passed.
- `scripts/run-msvc.ps1` through `VsDevCmd.bat -arch=x64 -host_arch=x64` - 195 tests, OK, no skip; both native SLTU tests passed. The artifact guard passed, and the Gate 0 report remained `PASS_LOCAL_DIFFERENTIAL_SPIKE`, `native_matches_oracle: true`, `windows_msvc_verified: true`, 28 instructions and 22 trace steps.
- `python tools/rptp_doctor.py` through `VsDevCmd.bat` - PASS; Python 3.13.16, MSVC 14.51.36231, CMake, Ninja, git, required layout and artifact guard all passed. `cmake --preset windows-msvc` and `cmake --build --preset windows-msvc` - PASS; CTest 3/3 PASS. `ctest --test-dir build/cmake-msvc --output-on-failure` - 3/3 PASS.
- `python -m compileall -q tools tests` - PASS. `python tools/check_forbidden_artifacts.py --root .` - PASS. The synthetic fixture manifest was unchanged.
- Relative-link check: 121 relative Markdown links across 34 tracked files - PASS; all resolve to existing repository paths.
- `python tools/rptp_progress.py` - PASS; regenerated the progress page and SVG assets with the 2026-10-24 snapshot date. Checklist percentages are unchanged (foundation 77.8%, runtime 5.0%); the generated text includes `SLTU`.
- `git diff --check` - PASS for whitespace errors; Git emitted LF-to-CRLF normalization warnings for modified text and generated files. No whitespace error was reported.
- Documentation updated: `README.md`, `docs/STATE.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`, `docs/IR_CFG.md`, `docs/INSTRUCTION_CATALOG.md`, `docs/CLEAN_ROOM_AUDIT.md`, `docs/REFERENCES.md`, `docs/COMPATIBILITY.md`, `docs/EXECUTION_CONTEXT.md`, `docs/BUILD_PROVENANCE.md`, `docs/ISO_INSPECTOR.md`, `docs/GATE0_REVIEW.md`, `docs/GATE2_EVIDENCE.md`, the progress generator/assets and this log. No new ADR was required; no dependency was added.
- Gate 3 remains **not passed**. `SLTU` is a synthetic-only unsigned-comparison addition; there is no product recompiler, function discovery, runtime or compatibility claim. These are local results only; the changes are not pushed and have no CI run.

## 2026-10-26 - Gate 3 ORI and XORI 64-bit register width correction

Base commit: 1d5575d; environment: Windows 11 x64, Python 3.13.16, Visual Studio 2026 Community, MSVC toolset 14.51.36231, CMake 4.4.4, Ninja 1.13.2 and Git 2.56.0 through the Visual Studio developer environment (VsDevCmd.bat -arch=x64 -host_arch=x64). No retail ISO or sealed project material was accessed. Published baseline e239527 is green in CI run 40007604212; this correction increment is local.

- Audit finding F1 reproduction: tests/test_instruction_logical_width.py was created first with literal expected constants. Before implementation changes, running python -m unittest tests/test_instruction_logical_width.py -v failed with 9 failures across oracle and lowered native execution: test_oracle_ori_preserves_upper_bits (3 subtest failures: 0x8000000080000000 | 0xFFFF returned 0x8000FFFF instead of 0x800000008000FFFF; 0xFFFFFFFF00000000 | 0x1234 returned 0x1234 instead of 0xFFFFFFFF00001234; 0x100000000 | 0x1 returned 1 instead of 0x100000001), test_oracle_xori_preserves_upper_bits (3 subtest failures: 0x8000000080000000 ^ 0xFFFF returned 0x8000FFFF instead of 0x800000008000FFFF; 0xFFFFFFFF0000F0F0 ^ 0x00FF returned 0xF00F instead of 0xFFFFFFFF0000F00F; 0x100000000 ^ 0x1 returned 1 instead of 0x100000001), test_native_helpers_preserve_or_zero_upper_bits (failed with ORI fail: got 0x8000ffff), test_reproducer_oracle_preserves_64_bit_width (returned 4294967295 instead of 18446744073709551615), and test_reproducer_native_matches_literal_constants (returned 4294967295 instead of 18446744073709551615).
- Reference verification: MIPS64 Volume II-A (MD00087; RPTP-REF-013) defines ORI as GPR[rt] <- GPR[rs] OR zero_extend(immediate) and XORI as GPR[rt] <- GPR[rs] XOR zero_extend(immediate) across the full register width; RPTP-REF-002 confirms basic logical operation definitions. The zero-extended 16-bit immediate leaves upper bits unaffected by OR and XOR, preserving upper bits of rs.
- Implementation: tools/rptp_gate0_spike.py updated execute_oracle to compute (r[rs] | (imm & 0xFFFF)) & 0xFFFFFFFFFFFFFFFF for ori and (r[rs] ^ (imm & 0xFFFF)) & 0xFFFFFFFFFFFFFFFF for xori. emit_cpp updated ori32 helper to lhs | static_cast<std::uint64_t>(immediate). tools/rptp_lower.py updated logical_helpers to emit lhs {operator} static_cast<std::uint64_t>(immediate).
- Tests updated: tests/test_instruction_logical.py updated T4 and S1 assertions from truncated 32-bit values to full 64-bit values (T4 = 0xFFFFFFFFFFFFFFFF, S1 = 0xFFFFFFFFFFFF0000). tests/test_instruction_sltu.py line 189 updated T5 assertion from 0x0000000080000000 to SIGN_EXTENDED_HIGH (0xFFFFFFFF80000000) because lui t5, 0x8000 sign-extends to 64 bits and ori t5, t5, 0 preserves those upper bits under 64-bit semantics rather than truncating.
- Artifact hashes: Gate 0 registered fixture SHA-256 (b21f1f7793236d1ccba7308cc82f42d9f89915c87c0b037c46d8170f28349ca9) and generated C++ SHA-256 (5316e0f51ba8b1fa1252e409f38cb9ac7db7606fee17b28ef0dcf1be162ae795) remain unchanged. Post-Gate-0 ORI fixture ELF SHA-256 (6c04b37fb40b3e7eaa29f82e7f21795bf930f0668aade41d04b1e058b8ff6dbc) remains unchanged. ORI generated C++ SHA-256 changed from 2aefb52babdd9e355fd3d12f3339c5c05ee60421be8bef0f17ae8f78d848c684 to 9d0d9fe3af4f1198cab447e802d364cf6b38dc00137f3583d0d6361ad2a50672 due to the corrected ori32 helper emission; updated in tests/test_ir_cfg.py.
- Verification results:
  - python tools/rptp_doctor.py - PASS (all 17 files present, MSVC found, cmake/ninja/git ok, artifact guard passed).
  - python tools/check_forbidden_artifacts.py --root . - PASS.
  - cmake --preset windows-msvc - PASS.
  - cmake --build --preset windows-msvc - PASS (CTest 3/3 passed in 26.48s: artifact guard, python unit tests 202/202, gate 0 differential test).
  - python -m unittest discover -s tests -v - 202 tests passed, 0 failures, 0 errors.
  - powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-msvc.ps1 - PASS (PASS_LOCAL_DIFFERENTIAL_SPIKE, windows_msvc_verified: true, native_matches_oracle: true, 202 tests passed).
- Modeled instruction width audit: all 20 modeled opcodes (nop, addu, addiu, and, or, xor, nor, slt, sltu, andi, ori, xori, lui, lw, sw, beq, bne, j, jal, jr) audited; no other width defect found.
- Gate status: Gate 2 remains open and read-only; Gate 3 remains not passed.


## 2026-10-27 — Gate 3 synthetic SLTI signed-immediate increment (CI run #44)

Commit: `69d7c1160e0a7ebcd2b8efa151b67f0da7fcd27b`. Scope: synthetic I-type `SLTI` opcode `0x0A`, signed 16-bit immediate and signed comparison against the project-defined 64-bit register model. Reference: `RPTP-REF-014`. No retail ISO, game binary, BIOS or sealed implementation material was accessed. Gate 0 fixture and its accepted scope were unchanged.

- Tests: `tests/test_instruction_slti.py` covers decoder, IR, literal-oracle, signed-64/immediate-boundary, deterministic output, malformed-input and native C++ differential cases. Native differential tests ran in both supported hosted compiler jobs.
- GitHub Actions run [#44](https://github.com/RidTheWann/RPTP-Project/actions/runs/40470003967): Windows x64/MSVC job `122074563032` and Linux/GCC job `122074563423` both completed successfully.
- On both runners, the artifact guard, full Python unit suite and Gate 0 differential target passed; CTest reported `100% tests passed, 0 tests failed out of 3`.
- A separate pre-fix failure run was not captured in this session; this procedural gap is recorded as `R-023` in [RISKS.md](RISKS.md).
- Gate 3 remains not passed. This is a synthetic test model, not a product recompiler, runtime, boot or compatibility result. No Gate or ADR disposition changed.

## 2026-10-27 — Gate 3 synthetic SLTIU unsigned-immediate increment (CI run #45)

Commit: `25267b6911ec438479d346d0c68cea5679c34dcb`. Scope: synthetic I-type `SLTIU` opcode `0x0B`; sign-extend the 16-bit immediate first, then compare as unsigned against the project-defined 64-bit register model. Generic instruction semantics are cross-checked against `RPTP-REF-014`. Gate 0 fixture and its accepted scope were unchanged.

- Tests: `tests/test_instruction_sltiu.py` covers literal oracle results, sign-extension and `UINT64_MAX` boundaries, `$zero`, aliases, IR metadata, malformed lowering metadata, deterministic source and native C++ execution. The existing `tests/test_instruction_slti.py` rejects unrelated unsupported opcodes rather than treating SLTIU as unsupported. Native tests ran in both supported hosted compiler jobs.
- GitHub Actions run [#45](https://github.com/RidTheWann/RPTP-Project/actions/runs/40470558441): Windows x64/MSVC job `122076404638` and Linux/GCC job `122076404168` both completed successfully.
- On both runners, the artifact guard, full Python unit suite and Gate 0 differential target passed; CTest reported `100% tests passed, 0 tests failed out of 3`.
- A separate pre-fix failure run was not captured in this session; this procedural gap is recorded as `R-023` in [RISKS.md](RISKS.md).
- Gate 3 remains not passed. This is a synthetic test model, not a product recompiler, runtime, boot or compatibility result. No Gate or ADR disposition changed.


## 2026-10-27 — Gate 3 synthetic DADDIU 64-bit immediate addition (CI run #50)

Test-first commit: `e5a2127aaafe4083d2491998ad6fe085dfa63bae`. Implementation commit: `f83dd8156973cde38c1185c9817e9f96a5073f33`. Regression-test correction: `f8b31d21c3e1ac3c5ca2a8f30618c95e68e66ef8`. No retail ISO, BIOS, game executable or sealed implementation material was accessed.

- Behavior: decode `DADDIU` (I-type opcode `0x19`), sign-extend its 16-bit immediate, add it to the modeled 64-bit source modulo 2^64, and suppress writes to `$zero`. The trapping `DADDI` (opcode `0x18`) remains unsupported. The model is limited to this synthetic IR/lowering path and does not claim complete R5900 behavior.
- Reference: `RPTP-REF-015`, the neutral MIPS64 instruction-set manual entry for DADDIU. The source record explicitly notes that the PDF could not be visually opened by the web renderer; the behavior is constrained by the repository's literal-oracle and native tests rather than represented as a full visual reference review.
- Test-first evidence: CI run #47 on the test-only commit failed because opcode `0x19` was still unsupported; seven DADDIU-dependent tests errored while attempting to decode/build the synthetic fixture. This was the intended pre-implementation failure.
- Implementation and regression correction: commit `f83dd81` added the decoder, oracle behavior, IR signed-immediate and destination metadata, lowerer validation, deterministic C++ helper, and fail-closed test. CI run #49 then isolated one stale test assumption: `tests/test_instruction_sltiu.py` used the newly supported name `daddiu` as its unsupported-operation example. Commit `f8b31d2` corrected that negative test to use `daddi`, which remains unsupported; no expected DADDIU result or assertion was removed.
- Hosted verification: GitHub Actions run [#50](https://github.com/RidTheWann/RPTP-Project/actions/runs/40474315598), commit `f8b31d21c3e1ac3c5ca2a8f30618c95e68e66ef8`, completed successfully. Linux/GCC job `122088657620` and Windows x64/MSVC job `122088658043` both passed. Each CTest invocation reported 3/3 targets passed: artifact guard, Python unit tests, and Gate 0 differential spike.
- Isolated helper check in this session: GCC compiled the equivalent C++20 modulo-64-bit helper with `-Wall -Wextra -Werror -pedantic`; output was `0 8000000000000000 8000000000000001 ffffffffffffffff` for `UINT64_MAX+1`, `INT64_MAX+1`, `INT64_MIN+1`, and `0+(-1)`. This is a focused helper check, not a local full-repository run.
- No repository checkout was available in this execution environment, so local doctor, CMake/MSVC wrapper and full local unittest commands were not run. The hosted CI results are the verification evidence for this increment.
- No registered fixture, `tests/fixtures/MANIFEST`, dependency, Gate/ADR disposition or product path changed. Gate 2 remains open and read-only; Gate 3 remains not passed. No product recompiler, runtime, boot or game-compatibility claim is made.
## 2026-10-27 — Gate 3 synthetic SUBU 32-bit subtraction (local run, not CI)

Test-first commit: `32ce91475b1a57b05187a6424b26030b9231e2e1`. Implementation commit: `a3cb73feb0830f40c40d91670fef9e79d2dcd6e3`. Environment: agent sandbox, Ubuntu 24.04, Python 3.12.3, g++ 13.3.0, CMake 4.4.4 and Ninja 1.13.2 installed into the sandbox with pip for this run only (not a repository dependency); checkout of `main` at `3fdc19c`. No retail ISO, BIOS, game executable or sealed implementation material was accessed; reference lookups used generic MIPS educational pages only (`RPTP-REF-016`).

- Behavior: decode `SUBU` (`SPECIAL` funct `0x23`, `shamt=0`), subtract the low 32 bits of `rt` from the low 32 bits of `rs` modulo 2^32, sign-extend to 64 bits, ignore upper source bits, no trap, suppress writes to `$zero`. The trapping `SUB` (funct `0x22`) remains unsupported. Limits: `R-024`.
- Baseline before changes: `python3 tools/check_forbidden_artifacts.py --root .` passed; `python3 -m unittest discover -s tests` ran 236 tests, OK.
- Test-first (red) run on the test-only commit state: `python3 -m unittest tests.test_instruction_subu` ran 13 tests, `FAILED (errors=8)`. Each error was `IR_UNSUPPORTED_INSTRUCTION: Unsupported SPECIAL instruction 0x01098023 at 0x00100010`, the expected failure because funct `0x23` was not decoded. The 5 fail-closed rejection tests already held.
- Green run after implementation: the same module ran 13 tests, OK. Full suite: 249 tests, OK (236 baseline plus 13). The artifact guard passed and `python3 -m compileall -q tools tests` succeeded.
- Generated C++ for the SUBU fixture compiled with `g++ -std=c++20 -Wall -Wextra -Werror -pedantic -O2` (return code 0); every native differential in the suite compiles with the same warnings-as-errors flags. The lowered SUBU fixture source has SHA-256 `34a2b9aec89098593657f0bccc6fc610e86605e5514cb088a6b4ff82befdfaf9` (a test artifact, not a registered fixture).
- `python3 tools/rptp_doctor.py`: PASS once CMake and Ninja were present; it reported FAIL before they were installed, which was an environment gap only.
- `cmake --preset host` and `cmake --build --preset host`: doctor PASS; CTest 3/3 passed (artifact guard, Python unit tests, Gate 0 differential spike).
- Not run: the Windows x64/MSVC preset, `scripts/run-msvc.ps1` and any MSVC `/W4 /WX` compile (no `cl.exe` in the sandbox). Nothing was pushed, so there is no hosted CI result; these commits are not CI-verified until the Windows x64/MSVC and Linux/GCC jobs pass on a pushed commit.
- No registered fixture, `tests/fixtures/MANIFEST`, dependency, Gate/ADR disposition or product path changed. The Gate 0 and ORI hashes checked by `tests/test_ir_cfg.py` are unchanged. Gate 2 remains open and read-only; Gate 3 remains not passed. No product recompiler, runtime, boot or game-compatibility claim is made.
