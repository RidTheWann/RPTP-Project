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

## 2026-10-28 — Git-only branch/PR/CI policy bootstrap

- The owner explicitly approved replacing the old direct-main rule with isolated increment branches, PRs, CI fixes and suitable verified merges. After logging the GitHub CLI into the owner account, they requested CI before any merge. This increment publishes only that approved Git workflow and its status/evidence, not the earlier local inspector/DADDIU/retail changes, a product feature, or a new reference policy.
- Actual `gh auth status --hostname github.com` and host-qualified `gh repo view` verified the active RidTheWann account and repository write access. Source preflight returned `PREFLIGHT_OK`. Fresh `git fetch origin` left local/main and origin/main equal at `3fdc19c9c6ff7d4039c6b5f80615c97c6d8722e8` (ahead/behind 0/0). The original checkout had 26 dirty paths; all were fingerprinted before work and remain untouched by this isolated increment.
- Existing PR #7 (`policy/conceptual-references-feature-pr-flow`, observed head `49226da4d080086fffd82f7484785aabdda1c222`) overlaps Git policy but also contains Proposed conceptual-reference/provenance changes and lacks the complete owner-approved merge/preservation safeguards. PR #8 is separate SUBU work. Neither active branch is reused, modified or merged here. ADR-0003 and the accepted legal/license/Gate boundaries remain unchanged; this increment does not accept or reproduce proposed ADR-0005.
- Run ID `f0941a3674334d2285e53f92dcb54a79` was generated/recorded before creating branch `automation/f0941a3674334d2285e53f92dcb54a79` and the linked worktree under ignored `build/automation-worktrees/`. Target preflight verified a clean exact-bound source/run/worktree at the freshly fetched baseline. No owner work was stashed, reset, restored, copied wholesale or staged.
- The policy assertion failed before the edit: the baseline lacked integration-main, exact-head compiler CI, expected-head merge, actual-merge CI and isolation/no-force-push clauses. After replacing only the Working protocol Git paragraph, it printed `APPROVED_POLICY_SCOPE_PASS`; the complete preceding mission/legal/license/clean-room text matches the baseline. STATE/HANDOFF are aligned with the approved policy and identify excluded unpublished work; source, tests, workflow, fixtures and dependencies are unchanged.
- Focused worktree command `python -B -m unittest tests.test_build_contract tests.test_doc_budget tests.test_license_headers tests.test_progress_consistency -v`: `Ran 10 tests in 0.032s`, `OK`; artifact guard and `git diff --check` passed. Separate user-profile guard suite: `Ran 31 tests in 0.060s`, `OK`. Those external helper tests are local evidence, not part of repository CI or a live merge guarantee.
- Main-branch API metadata reported `protected: false` and the same baseline SHA; no protection/permission/configuration was modified. The workflow must still check both exact-head compiler jobs, current review/merge state and a pinned merge head, then actual merge-commit CI. Native/hosted results are recorded only after observation; neither local testing nor this policy change passes a Gate or certifies provenance.
- A read-only general-purpose correctness reviewer found no blocking issue in the Git-policy/STATE/HANDOFF diff and confirmed that source/workflows, accepted ADR/license/Gate dispositions remain unchanged. A nonblocking wording suggestion was applied to STATE: exact-head CI is a pre-merge prerequisite; actual merge-commit CI is monitored after merge. This is a scope/correctness review, not an independent provenance disposition.
- Full local x64 MSVC chain completed with exit 0: doctor, artifact guard, compileall, `python -m unittest discover -s tests -v`, `cmake --preset windows-msvc`, `cmake --build --preset windows-msvc`, and `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-msvc.ps1`. Local output: `build/policy-msvc.log` in the isolated worktree. Full suites reported `Ran 236 tests in 40.657s`, `OK`, and `Ran 236 tests in 34.416s`, `OK`; CTest reported `100% tests passed out of 3`, total 36.44 seconds. The smaller baseline suite excludes the earlier unpublished inspection additions; no test was weakened or removed.
- Gate 0 report remains `PASS_LOCAL_DIFFERENTIAL_SPIKE`, `native_matches_oracle: true`, `windows_msvc_verified: true`, C++20 and `/W4 /WX`, with fixture/generated SHA-256 `b21f1f7793236d1ccba7308cc82f42d9f89915c87c0b037c46d8170f28349ca9` / `5316e0f51ba8b1fa1252e409f38cb9ac7db7606fee17b28ef0dcf1be162ae795`. Local baseline success is not hosted CI, product compatibility or provenance certification.
- Post-review documentation/license/progress checks passed `Ran 5 tests in 0.022s`, `OK`; whitespace was clean. `FINAL_SCOPE_AND_PRESERVATION_PASS` confirmed exactly four task-owned document paths, an empty index/untracked set, the untouched 107,808-byte evidence prefix (SHA-256 `1ab3ccb6630b9ecfc64a65a06dcc10892d0eac6bb568cbcfc46555e565785c12`) and all original dirty-file fingerprints. Hosted CI and merge are pending at this commit; observed outcomes must be recorded later without rewriting this tested history.

### Observed hosted verification before the final evidence commit

- Commit `6fbc4030f09244ab7ce20dbf1fefbc5a29f9116c` was pushed only to the recorded automation branch; draft [PR #9](https://github.com/RidTheWann/RPTP-Project/pull/9) targets main. Exact-head `ci.yml` push run [40597238185](https://github.com/RidTheWann/RPTP-Project/actions/runs/40597238185) completed successfully: Windows x64/MSVC job `122516135045` and Linux/GCC job `122516135578` both completed with `success`. The CLI watcher exited 0 and the run/job metadata was independently requeried.
- A fresh fetch still left origin/main at the original baseline; all 26 source-checkout fingerprints, its HEAD and empty index remained unchanged. The STATE publication wording now points to observed evidence and live exact-head queries instead of retaining a stale pending result. This additional evidence edit requires new exact-head CI; the earlier green run cannot authorize merging a later commit. No merge or actual merge-commit CI result exists at this snapshot.

## 2026-10-29 — Publication of preserved inspection evidence

These sections were produced on 2026-10-28 in the original checkout and preserved while the Git-only policy bootstrap was published. They are appended unmodified except for line-ending normalization; status statements inside them describe the earlier local state. Hosted CI for this publication is recorded separately.

## 2026-10-28 — main synchronization and DADDIU oracle regression hardening

### Synchronization and scope

- Starting branch: `main` at `dd1e5a4`. `git fetch origin main` succeeded; remote tip was `3fdc19c9c6ff7d4039c6b5f80615c97c6d8722e8`.
- `git rev-list --left-right --count main...origin/main` reported `0 8`; `git merge-base --is-ancestor main origin/main` succeeded. All local commits were already ancestors of remote main. Incoming history and diffs were reviewed; there were no divergent or equivalent local-only patches to select or replay.
- `git merge --ff-only origin/main` succeeded, followed by a `0 0` left/right count. `git ls-remote --heads origin main` independently returned the same full remote SHA. No branch, merge commit, cherry-pick, reset, stash or history rewrite was needed.
- The only starting uncommitted edit was a trailing blank line in `.gitignore`; its exact diff was preserved. No new commit or push was explicitly requested, so session changes remain uncommitted and no push was performed.
- Architecture was checked against `tools/rptp_inspect.py:622-644`, `tools/rptp_ir.py:563-581,614-672`, `tools/rptp_gate0_spike.py:615-684` and [IR_CFG.md](IR_CFG.md). The read-only metadata inspector, synthetic analyzer and generated C++ test path are separate stages, not an integrated ISO-to-native product. Known-edge traversal does not resolve indirect transfers or caller return edges; the interpreter remains a test oracle only.

### Baseline verification

The following commands ran in the repository after synchronization. MSVC commands used `VsDevCmd.bat -arch=x64 -host_arch=x64` from the installed Visual Studio developer environment, invoked through the Windows command processor.

```text
python tools/rptp_doctor.py
python tools/check_forbidden_artifacts.py --root .
python -m compileall -q tools tests
python -m unittest discover -s tests -v
cmake --preset windows-msvc
cmake --build --preset windows-msvc
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-msvc.ps1
```

- Doctor: PASS; Python `3.13.16`, x64 MSVC, CMake, Ninja, Git and artifact checks were found/passed. Artifact guard and compileall exited zero.
- Full unittest: `Ran 236 tests`, `OK`, no skips. CMake configure/build succeeded; CTest passed 3/3 targets. The wrapper also passed all 236 tests without skips.
- Baseline output: ignored local `build/sync-main-msvc.log`. Both `build/gate0-msvc/report.json` and `build/cmake-msvc/gate0/report.json` reported `PASS_LOCAL_DIFFERENTIAL_SPIKE`, `native_matches_oracle: true`, `windows_msvc_verified: true`, and 22 trace steps. Compiler commands retained C++20, `/W4` and `/WX`.
- Gate 0 fixture SHA-256 remained `b21f1f7793236d1ccba7308cc82f42d9f89915c87c0b037c46d8170f28349ca9`; generated C++ SHA-256 remained `5316e0f51ba8b1fa1252e409f38cb9ac7db7606fee17b28ef0dcf1be162ae795`.
- Two launcher attempts failed before any project test ran: Git Bash passed escaped quotes around the Visual Studio batch path, then an inline Python command had an unterminated string literal. Building the Windows command string with explicit quote characters resolved the launcher issue; these were not project regressions.
- Live GitHub Actions lookup was not verified: `gh run list` failed with `gh: command not found`, and common CLI installation locations did not provide an executable. No CLI or dependency was installed. Earlier hosted CI records above are preserved as historical evidence, not a new live CI assertion. No local Linux/GCC run was performed.

### Independent DADDIU regression evidence

- Read-only review found no current SLTI/SLTIU/DADDIU implementation defect in the narrow synthetic model, but identified an oracle-coverage gap in `tests/test_instruction_daddiu.py`. The original fixture produced the same complete oracle state when DADDIU dispatch was replaced in memory with ADDIU dispatch; the separate native boundary harness did not cover oracle execution.
- Independent synthetic vectors produced `0x0000000080000000` for `0x000000007FFFFFFF + 1` and `0xFFFFFFFF7FFFFFFF` for `0xFFFFFFFF80000000 - 1`. The 32-bit dispatch mutant instead produced `0xFFFFFFFF80000000` and `0x000000007FFFFFFF`, respectively. No production file was mutated.
- Added both vectors to the existing runtime-generated fixture and literal assertions for oracle and native results. No new opcode, production semantics, binary fixture, dependency or runtime feature was added. Reference remains `RPTP-REF-015`; this is synthetic regression evidence, not R5900 hardware validation.
- `python -m unittest tests.test_instruction_daddiu -v` under x64 MSVC: 9 tests passed, including the native fixture and native boundary harness, with no skips.
- Running the strengthened literal oracle test against the in-memory ADDIU-dispatch mutant yielded the expected single assertion failure: `18446744071562067968 != 2147483648`. The experiment required that failure and printed `EXPECTED_MUTATION_REJECTION`; the normal implementation passed. Risk `R-024` records the locally resolved coverage gap.
- `python -m unittest tests.test_doc_budget tests.test_license_headers -v`: 4 tests passed. `git diff --check -- docs tests/test_instruction_daddiu.py` passed; production modules, the registered fixture manifest and license were unchanged by the session edits.
- Updated bounded STATE/HANDOFF, the instruction catalog, references and provenance evidence; corrected the stale IR subset limitation to include the already-published SLTI, SLTIU and DADDIU operations. No Gate/ADR disposition or provenance status changed. Gate 2 remains open/read-only; Gate 3 remains not passed. Independent reviews and the pre-feature SLTI/SLTIU replay gap (`R-023`) remain open.

### Final verification and completion audit

- Re-ran every command listed above after the fixture, reference, risk and handoff edits. Doctor, artifact guard and compileall passed; full unittest reported `Ran 236 tests`, `OK`, without skips. CMake configure/build and CTest passed 3/3 targets; the MSVC wrapper again reported all 236 tests passing without skips, `PASS_LOCAL_DIFFERENTIAL_SPIKE`, `native_matches_oracle: true` and `windows_msvc_verified: true`. The strengthened DADDIU oracle/native tests ran successfully in both full-suite invocations. Final output is the ignored local `build/sync-main-final-msvc.log`.
- Final `git fetch origin main` succeeded and left `main...origin/main` at `0 0`. No tracked production/build/workflow code, license, ADR, registered fixture, game record or dependency was changed by the local hardening. The initial `.gitignore` edit remained byte-for-byte the same diff.
- Checked the complete local patch, whitespace for session files, bounded document sizes and line lengths, and normalized append-only preservation of every pre-session verification-log byte. STATE/HANDOFF remain inside their enforced budgets. The full suite covers the changed fixture's actual oracle and generated-native paths, not only a helper or manifest check.

| Requested outcome | Concrete evidence and limit |
|---|---|
| Synchronize main before further work | Fetch, ancestry check, reviewed eight incoming commits, fast-forward, and final zero-divergence check. |
| Compare local/remote work and select the best non-duplicating result | Every local commit was already an ancestor; no local-only equivalent patch existed. Fast-forward preserved all history and the existing edit without cherry-picking or discarding work. |
| Understand the project's complex reverse-engineering logic | Reviewed canonical provenance and IR contracts, read-only inspector and static-analysis entry points, new instruction code/tests, and independent signed/unsigned/modulo boundary evidence. No complete R5900 or product-runtime claim is made. |
| Resolve uncertainty from evidence and deliver autonomously | Reproduced the DADDIU oracle blind spot with an in-memory mutation, strengthened literal oracle/native regressions, and verified them under MSVC before updating the full handoff. No user question, new dependency, policy change or destructive action was needed. |
| Full handoff with honest verification and remaining boundaries | STATE/HANDOFF, catalog, IR contract, references, component evidence, risks and this append-only log updated. Local test/doc changes are uncommitted; no commit/push was requested. Live CI and Linux/GCC were not reverified, and existing independent-review/Gate blockers remain unchanged. |

## 2026-10-28 — primary-only inspection hardening and foundation verification

### Scope and permitted evidence

- Continued on `main` at `3fdc19c9c6ff7d4039c6b5f80615c97c6d8722e8`, preserving the prior DADDIU/documentation work and the owner's original `.gitignore` blank-line edit. No new Git synchronization, staging, commit, push, branch or history rewrite was performed in this phase.
- Selected one technical task: complete the primary-only ISO inspection acceptance/rejection envelope and validate the existing Windows/MSVC foundation. This adds metadata and safety checks, not extraction, a native loader, instruction semantics, runtime subsystems or compatibility evidence.
- Checked the official ECMA-119 fifth-edition PDF already registered as `RPTP-REF-006`. The PDF renderer was unavailable (`pdftoppm` missing); a temporary standard-library text extractor under ignored `build/` exposed readable clauses and page footers. No PDF package or other dependency was installed. Descriptor sequencing/types/versions, file sections, root record, flags and identifier/sector padding were checked; detailed clause pointers are in [REFERENCES.md](REFERENCES.md).
- Fetched the neutral `elf(5)` `p_align` paragraph (`RPTP-REF-003`) to verify power-of-two and address/offset congruence. Printable-ASCII identifiers, exact explicit-version BOOT matching, configuration parsing and resource budgets are documented RPTP safety/test contracts, not complete ISO grammar or PS2 hardware claims. No sealed material or retail image was accessed.

### Test-first findings and corrections

- Baseline `python -m unittest tests.test_iso_inspector -v`: `Ran 59 tests`, `OK`.
- Added `IsoFormatContractTests` before the production format changes: `Ran 17 tests`, `FAILED (failures=32, errors=2)`. Output: ignored `build/inspection-format-red.log`. Reproduced incorrect displaced-PVD LBA, absent inventory, enhanced-version rejection, acceptance of reserved/conflicting descriptors and invalid primary/record fields, late descriptor bounds and misleading multi-extent ambiguity errors.
- Added `IsoInputBoundaryTests` before their production changes: `Ran 9 tests`, `FAILED (failures=15, errors=1)`. Output: ignored `build/inspection-boundary-red.log`. Reproduced silent duplicate/config-byte repair, malformed quote handling, special-record budget bypass, missing byte budgets and acceptance of invalid empty/negative read ranges. The large-file streaming positive case preserved the materialization cap.
- Corrected two synthetic fixture issues without weakening assertions: set the required primary file-structure version to 1, and mutate padding on the even-length `SYSTEM.CNF;1` identifier rather than the odd-length boot identifier. The initial padding test targeted name data, not a padding byte. The focused suite then passed `Ran 85 tests`, `OK`; output: `build/inspection-focused-green.log`.
- A separate read-only correctness review identified five additional suspected gaps; it did not run tests, edit files or provide an independent provenance disposition. Added `IsoReviewRegressionTests` before the fixes: `Ran 10 tests`, `FAILED (failures=19, errors=2)` in `build/inspection-review-red.log`. Reproduced nonzero/hidden sector tails, repaired invalid identifiers, an explicit `;2` selecting `;1`, ambiguity despite an exact requested version, late directory fan-out limits and acceptance of incongruent ELF alignment.
- Fixed all five reproduced gaps: validate zero sector tails and primary identifiers in both modes; match explicitly versioned BOOT components without version substitution; deduplicate and limit extents before queueing; enforce PT_LOAD `p_vaddr`/`p_offset` congruence for alignment above 1. Corrected the runtime-generated ELF fixture's alignment from 4096 to 4 so offset 84 and virtual address `0x00100000` are congruent. Separate positive 0/1/4/4096 and negative 4096 cases retain explicit alignment coverage.
- Final focused suite before the full MSVC run: `Ran 95 tests`, `OK`; output: `build/inspection-review-green.log`. Extended the deterministic/read-only CLI test with sector-padding, identifier, missing explicit-version and ELF-congruence failures; each inspection/survey case runs twice, checks identical JSON, expected exit/status/error, unchanged input bytes and no extra files.
- Inspection inventories auxiliary headers with warnings but never follows auxiliary roots or executes boot records; encountered multi-extent/associated/record-formatted data is explicitly rejected before lookup. Survey counts file-section records and skips unsupported directories rather than reconstructing files. Raw limits include special entries; byte limits include padding; alias/cycle scheduling is bounded. A synthetic executable above 4 MiB is hashed with reads at most 64 KiB while whole-file materialization remains capped.

### Windows/MSVC foundation verification

The following command chain ran through `VsDevCmd.bat -arch=x64 -host_arch=x64`. All commands below exited zero; the chain stops on any failure.

```text
python tools/rptp_doctor.py
python tools/check_forbidden_artifacts.py --root .
python -m compileall -q tools tests
python -m unittest discover -s tests -v
cmake --preset windows-msvc
cmake --build --preset windows-msvc
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-msvc.ps1
```

- First full run after the initial hardening: doctor/artifact/compileall passed, Python suite and wrapper each reported `Ran 262 tests`, `OK`, and CTest passed 3/3. Output: ignored `build/inspection-foundation-msvc.log`.
- Final full run after all source and CLI-test corrections: doctor found Python `3.13.16`, x64 MSVC, CMake, Ninja and Git and passed artifact checks. Artifact guard and compileall passed. Full Python suite: `Ran 272 tests in 39.505s`, `OK`; wrapper suite: `Ran 272 tests in 39.014s`, `OK`. No skips were reported. CMake configure/build succeeded and CTest reported `100% tests passed out of 3`. Output: ignored `build/inspection-foundation-final-msvc.log`.
- Both local Gate 0 reports retain `PASS_LOCAL_DIFFERENTIAL_SPIKE`, `native_matches_oracle: true`, `windows_msvc_verified: true` and 22 trace steps. Compiler commands retain C++20, `/W4` and `/WX`. Fixture SHA-256 remains `b21f1f7793236d1ccba7308cc82f42d9f89915c87c0b037c46d8170f28349ca9`; generated C++ SHA-256 remains `5316e0f51ba8b1fa1252e409f38cb9ac7db7606fee17b28ef0dcf1be162ae795`. The inspector's synthetic ELF fixture change does not modify the registered Gate 0 fixture.
- After documentation edits, `python -m unittest tests.test_doc_budget tests.test_license_headers tests.test_progress_consistency -v` passed 5 tests. STATE/HANDOFF remain within their normalized UTF-8 byte/line budgets; `git diff --check -- docs tests/test_instruction_daddiu.py tests/test_iso_inspector.py tools/rptp_inspect.py` passed. These local runs are not hosted CI or Linux/GCC verification.

### Handoff and remaining boundaries

- Updated the existing primary-only format matrix, error taxonomy, references, Gate 2 evidence, ROADMAP technical-review item, bounded STATE/HANDOFF and component evidence. Risks R-025/R-026 record locally resolved format/lookup/config/resource gaps; R-027 records the remaining ELF loading-contract gap. The review observed virtual address `0xFFFFFFF0` with memory size `0x100` accepted by the metadata contract; no full address-space or PS2 loading model is claimed or added.
- Gate 2 remains open/read-only and not passed. Independent inspector provenance review, publication/green Windows x64/MSVC and Linux/GCC CI, and owner disposition remain outstanding. Gate 3 remains not passed; the ISO inspector, synthetic analyzer and native test lowerer are still separate prototypes, not an integrated ISO-to-native product. No boot or compatibility claim follows from these tests.
- The Gate 0 spike and inspector remain `Provisional independent`; the build/CI/doctor layer remains `Review required`. No Gate/ADR disposition, license, dependency, provenance status or certification changed. Technical review and agent correctness review do not substitute for independent provenance review.
- The tracked production change is limited to `tools/rptp_inspect.py`; all new fixtures are runtime-generated in the existing test module. Existing DADDIU changes are preserved. Build/workflow/doctor source, registered fixture manifest, license, ADRs, game records and dependency/configuration files are unchanged. No new tracked file or proprietary artifact was introduced. Changes remain uncommitted; commit/push were not requested.
- Final audit verified normalized append-only preservation of all 116,245 pre-phase evidence bytes (SHA-256 `85cb4e0f85062db17d6c55211d0c662ad7b8d91f4f64ec638f142064987ee9c1`) and the committed evidence prefix. Git scope contains only the expected 15 modified paths, including prior-session work; there are no staged or untracked files. The owner's `.gitignore` diff is still exactly one trailing blank line. STATE/HANDOFF measured 6,913/6,224 normalized UTF-8 bytes with longest lines 522/625 characters, within enforced budgets.

## 2026-10-28 — ELF32 load-map metadata and authorized retail revalidation

### Scope and neutral-reference evidence

- Owner requested continued local development, permitted local tool/reference downloads if needed, and explicitly provided the local PS2 ISO collection for testing. Selected one read-only increment: close the ELF32 address/order metadata gap before native-loader design and revalidate the same eight authorized discs. The startup status/log and canonical Gate/provenance/ADR documents were rechecked; `main` remains at `3fdc19c` with previous uncommitted work preserved. No commit, push or remote synchronization was requested or performed in this phase.
- `RPTP-REF-003` (`elf(5)`) was fetched from its already registered neutral URL and downloaded to ignored `build/elf-load-contract-reference.html`. Exact text checked: basic types define Elf32_Addr as unsigned 32-bit; PT_LOAD maps file bytes to the beginning of memory, defines extra bytes as zero and orders load headers by p_vaddr; e_entry is the initial virtual control-transfer address; PF_X denotes an executable segment. No emulator/recompiler implementation was accessed. No dependency was installed or added.
- New report fields are metadata: original program-header indexes, exclusive file/memory ends, zero-fill sizes, all entry mappings with ELF-relative offsets/null and execute/file-backed flags, and an overlap indicator. Every PT_LOAD rejects virtual-memory end above `2^32` or decreasing virtual addresses. An exclusive end exactly at `2^32`, equal start addresses and empty ranges are accepted. Overlap is warned, never silently repaired, rejected as universally invalid, or assigned loading precedence. No payload/segment memory is allocated by load-map construction; hashing retains bounded streaming.
- No extraction/write API, retail execution, loader, address-space/page policy, physical-address mapping, relocation support, instruction semantics or runtime subsystem was added. The separate synthetic parser/analyzer/lowerer is unchanged. R-027 remains open for actual loading policy and PS2 conventions; metadata success is not loader readiness.

### Test-first and correctness-review evidence

- `python -m unittest tests.test_iso_inspector.ElfLoadMapTests -v` before production implementation: `Ran 11 tests`, `FAILED (failures=4, errors=18)`. The existing inspector accepted both the over-width virtual range and decreasing load order; missing report fields produced expected errors. Output: ignored `build/elf-load-map-red.log`.
- After implementation, `python -m unittest tests.test_iso_inspector -v`: `Ran 106 tests in 3.413s`, `OK`. Output: ignored `build/elf-load-map-green.log`.
- A separate read-only correctness reviewer found no reproduced correctness/security regression and identified two missing boundary cases: an empty range inside a non-empty one without another overlap, and execute permission/file backing split across different entry mappings. Both already behaved correctly; independent literal regressions now prevent those blind spots. This agent correctness review is not an independent provenance disposition.
- Added the exact earlier R-027 range (`0xFFFFFFF0` plus `0x100` memory bytes) alongside the one-byte-overflow case, plus deterministic JSON/plain CLI success, warning and error cases. CLI tests assert return codes, stderr/stdout, byte equality, input preservation and no extra files.
- Final focused inspector run: `Ran 108 tests in 4.896s`, `OK`. Output: ignored `build/elf-load-map-final-green.log`. Synthetic fixtures remain runtime-generated in the existing test module; no game bytes or new persistent fixture were added.

### Authorized eight-disc read-only evidence

- Ran `python build/elf-retail-validation.py > build/elf-retail-validation.log 2>&1` using an ignored, standard-library-only local evidence harness. Each disc was opened read-only for a whole-image SHA-256 before and after two CLI inspection and two CLI survey runs. Each mode reproduced identical output and return codes with empty JSON stderr. Input size/mtime and both whole-image hashes matched; the current hashes also matched each prior game record.
- Inspector source SHA-256 for all runs: `a1bbc6f85f9d7bebad0441c548ec31f5a43aafe6973762101b033936b43a7986`. It was checked before/after the harness and again against the source during the independent raw-header audit. Local outputs: `build/elf-retail-summary.json`, per-disc `build/elf-retail-<slug>.inspect.json`/`.survey.json` and `build/elf-retail-validation.log`. Reports contain metadata only; local harness outputs do not add an inspector output-directory feature.

| Authorized sample | Inspection | PT_LOAD | Entry file offset (within boot ELF) | Survey / image preservation |
|---|---|---|---|---|
| Black USA | INSPECTED, no warnings | 1 | 4104 | SURVEYED; whole hash, size and mtime unchanged |
| Bully USA | INSPECTED_WITH_WARNINGS: load-memory overlap | 19 | 776 | SURVEYED; whole hash, size and mtime unchanged |
| Downhill Domination USA | INSPECTED, no warnings | 1 | 4104 | SURVEYED; whole hash, size and mtime unchanged |
| God of War II USA | INSPECTED, no warnings | 1 | 4104 | SURVEYED; whole hash recomputed and unchanged |
| San Andreas owner-described Indonesian-language mod | INSPECTED_WITH_WARNINGS: load-memory overlap | 10 | 392 | SURVEYED; whole hash, size and mtime unchanged |
| San Andreas owner-described original USA | INSPECTED_WITH_WARNINGS: load-memory overlap | 10 | 392 | SURVEYED; whole hash, size and mtime unchanged |
| Need for Speed Most Wanted USA v2.00 | INSPECTED, no warnings | 1 | 3371200 | SURVEYED; whole hash, size and mtime unchanged |
| Resident Evil 4 USA | INSPECTED, no warnings | 1 | 4104 | SURVEYED; whole hash, size and mtime unchanged |

- All entries map uniquely into file-backed PF_X bytes. Bully and both San Andreas ELF tables contain multiple non-empty, zero-file-size load ranges sharing a virtual start; the overlap warning is newly exposed metadata, not evidence that the discs are malformed or incompatible. No loading precedence, overlay semantics or memory-footprint claim is made. Independent sparse reads using `struct.unpack` cross-checked original program headers, entry offsets and pairwise interval intersections instead of reusing the inspector sweep. Output: `INDEPENDENT_RAW_ELF_METADATA_CHECK_PASS`; metadata: `build/elf-retail-independent-check.json`.
- God of War II still declares 2,083,888 blocks in the larger image; the extra 4,265,869,312 bytes were hashed for input identity but not parsed as ISO content. No second-layer interpretation follows. The two San Andreas samples retain their owner-declared original/mod provenance, distinct whole-image identities and shared boot/config hashes; no modification-content audit was performed.

### Full local Windows/MSVC evidence

The following command chain ran through `cmd.exe` and the x64 Visual Studio developer environment, launched by Python from Git Bash. Output was redirected to the ignored logs below:

```text
call "C:\Program Files\Microsoft Visual Studio\18\Community\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64
python tools/rptp_doctor.py
python tools/check_forbidden_artifacts.py --root .
python -m compileall -q tools tests
python -m unittest discover -s tests -v
cmake --preset windows-msvc
cmake --build --preset windows-msvc
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-msvc.ps1
```

- First full run before the final review-coverage additions passed doctor/artifact/compileall, both `Ran 283 tests` suites, CMake and CTest 3/3. Output: `build/elf-load-map-msvc.log`.
- Final run after all source/test changes passed doctor/artifact/compileall; full suite `Ran 285 tests in 39.224s`, `OK`; wrapper suite `Ran 285 tests in 38.730s`, `OK`; no skips. CMake configure/build passed and CTest reported `100% tests passed out of 3`. Output: `build/elf-load-map-final-msvc.log`.
- Both Gate 0 reports still show `PASS_LOCAL_DIFFERENTIAL_SPIKE`, `native_matches_oracle: true`, `windows_msvc_verified: true`, 22 trace steps, C++20 and `/W4 /WX`. Fixture SHA-256 remains `b21f1f7793236d1ccba7308cc82f42d9f89915c87c0b037c46d8170f28349ca9`; generated C++ SHA-256 remains `5316e0f51ba8b1fa1252e409f38cb9ac7db7606fee17b28ef0dcf1be162ae795`.
- These are local Windows/MSVC runs, not hosted CI or current Linux/GCC verification. Gate 2/3 remain not passed, independent provenance reviews remain open, and the build/CI/doctor layer remains `Review required`. No component/ADR/Gate disposition, license or clean-room certification changed.

### Final documentation and handoff audit

- Updated all eight existing game records and their index, then reviewed the actual nine-file diff. Historical runs and owner-declared original/mod provenance remain distinct from the current working-tree evidence. Statuses remain `Inspected (read-only)`; current outcomes distinguish the three overlap warnings from the five warning-free inspections. God of War II records the actual whole-image rehash without claiming a second layer. No disc was reopened by the documentation review.
- `python -B -m unittest tests.test_game_records tests.test_doc_budget tests.test_license_headers tests.test_progress_consistency -v`: `Ran 6 tests in 0.031s`, `OK`. Artifact guard passed and scoped `git diff --check` passed. Git emitted LF/CRLF normalization warnings for game records; no Git configuration was changed.
- The first report-comparison helper used the system-default text encoding and failed to locate a UTF-8 heading. Explicit UTF-8 reading resolved this helper-only issue. The final comparison printed `GAME_RECORD_REPORT_MATCH` for all eight records, checking hashes, outcomes, warnings, load counts, zero-fill sizes and entry offsets against the saved summary and independent sparse-header report. The inspector source fingerprint remains unchanged.
- STATE/HANDOFF measured 7,062/6,515 normalized UTF-8 bytes with longest lines 515/625 characters, within their enforced budgets. The committed evidence prefix and all 125,342 pre-phase normalized evidence bytes remain intact; pre-phase SHA-256 is `3d427193d7f38776383d3a7a7fd49bb14aee599d8ab1764bf12e216de24f4a26`.
- Final Git scope contains the expected 25 modified paths, including earlier uncommitted work and the owner's preserved `.gitignore` blank line; no staged or untracked nonignored files exist. HEAD remains `3fdc19c9c6ff7d4039c6b5f80615c97c6d8722e8`. Runtime/IR/lowerer, build/CI/doctor source, license, ADRs, fixture manifest and increment ledger are unchanged. No commit or push was performed.
- This read-only ELF metadata increment is locally verified, not an integrated native loader or compatibility result. R-027 loading precedence/physical mapping/relocation/PS2 convention work, independent provenance reviews, authorized publication with both CI jobs, and owner Gate 2 disposition remain outstanding. Extraction still requires a separate ADR and threat model.

## 2026-10-28 — Manual development automation setup and local safety checks

### Owner-authorized scope and installation

- The owner selected development plus validation, manual invocation first, user-profile installation, and roadmap-led increments. They explicitly authorized dedicated branches, commits, branch pushes, PRs, CI diagnosis/fixes and merges only after suitable verification, and approved alignment of the old main-only Git policy. No scheduler, repository-protection change, credential configuration or public trial PR was requested or performed.
- Installed the user-profile `rptp-develop` skill with `SKILL.md`, `scripts/workflow_guard.py` and `tests/test_workflow_guard.py`. It is not vendored/linked into RPTP and adds no product dependency. Each invocation selects one permitted increment, preserves prior work in a separate linked worktree, requires local verification/review and both exact-head compiler jobs, pins the merge head and checks CI for the actual merge commit. Legal, license, clean-room, architecture and Gate boundaries remain unchanged.
- Updated existing `AGENTS.md`, STATE/HANDOFF and REFERENCES; the adopted branch-policy change remains unpublished. Subsequent product runs require that policy to be published without silently bundling earlier uncommitted work. The original checkout was not switched, staged, committed or pushed during setup.
- GitHub CLI was absent. Official WinGet metadata identified GitHub CLI 2.103.3, GitHub, Inc., MIT license and the official release MSI. `winget download --id GitHub.cli --exact --version 2.103.3 --source winget --download-directory <user-tool-directory> --skip-dependencies --accept-package-agreements --accept-source-agreements` reported `Successfully verified installer hash`. The installer was administratively extracted with `msiexec.exe /a <msi> /qn /norestart TARGETDIR=<user-tool-image>`; the executable was copied into the user tool directory, without changing PATH or Git configuration.
- Independent MSI SHA-256 checks passed: `5073112b7abb5ffbba24b76aee7e89269af531218c0a42751f5f0bfb6440c2cc`. Actual executable output: `gh version 2.103.3 (2026-10-26)`. Upstream CLI retains its own license/notices; RPTP LICENSE/LICENSES and dependencies were not changed.

### Test-first guard development and review findings

- The standard-library helper issues only read-only Git/GitHub commands, uses argument arrays without a shell, bounds external execution, checks exact repository identity and write access, and avoids exposing raw credential-bearing stderr. Its checks are not a GitHub protection configuration or an independent provenance review.
- Initial tests failed before the helper existed (`ModuleNotFoundError`, one test-loader error), then `Ran 14 tests in 0.003s`, `OK`. Post-merge tests failed before `check_merged_ci` existed (`AttributeError`, nine errors), then `Ran 21 tests in 0.018s`, `OK` after implementation.
- A read-only general-purpose reviewer independently ran the 21-test suite successfully but found two publication-safety gaps: fetch URL alone did not cover separate push URLs, and namespace/linked-worktree checks did not enforce run ownership. No concrete false-ready CI case was reported in that review.
- Added regressions before the corrections. The first expanded run reported `Ran 26 tests in 0.035s`, `FAILED (errors=20)` for the absent binding API and updated command mocks. After retaining the original fetch-command mock, the focused push regression reproduced four actual false accepts: wrong/empty push destination and two mixed multi-push orders (`GuardError not raised`; `Ran 1 test in 0.023s`, `FAILED (failures=4)`). Post-merge branch-binding tests also failed before the new function contract (`Ran 3 tests in 0.013s`, `FAILED (errors=10)`). These are recorded red tests, not remaining failures.
- The corrected guard validates every effective fetch URL and every `git remote get-url --push --all origin` destination. Task checks require the source root and a fresh UUID-hex run ID recorded before creation; exact branch `automation/<run-id>`, task root under `build/automation-worktrees/<run-id>`, and shared source Git directory must match. Missing/malformed binding, another run, foreign common directory, dirty task, non-linked checkout and failed origin/main ancestry are rejected. Post-merge checks retain that binding and exact PR branch while omitting only ancestry against main that may have advanced after merge.
- Skill instructions require preflight immediately before every push and an explicit `HEAD:refs/heads/automation/<run-id>` refspec. The binding is an explicit run-context check, not authenticated session identity or concurrency locking; active-run and overlap checks remain procedural. The helper cannot enforce an agent's conduct outside its invocation and does not eliminate remote-state races; GitHub protections/reviews/queues must still be respected.
- After corrections: `Ran 26 tests in 0.062s`, `OK`. Added authentication/write-permission and CLI-dispatch coverage, then `python -B -m unittest discover -s <user-profile>/.qoder/skills/rptp-develop/tests -v`: `Ran 28 tests in 0.066s`, `OK`. Coverage includes latest exact-head push selection rather than older green fallback, required job duplicates/absence/failure/skip, changed PR head in the final query, actual merged-main SHA, JSON errors and credential-safe failures.

### CLI, project and native verification

- Official CLI help verified the actual `gh pr view`, `gh run list` and `gh run view` JSON fields used by the helper and `gh pr merge --merge --match-head-commit`. Evidence basis: `RPTP-REF-016`. Guard `--help` verified `--source-root`/`--run-id` flags. Skill metadata/name/description/body/file-set and Python compilation checks printed `SKILL_VALIDATION_PASS` and `GUARD_BINDING_FLAGS_VERIFIED`; no dependency or extra documentation file was introduced.
- Actual `gh auth status --hostname github.com` reported no logged-in GitHub hosts. The source preflight returned exit 2: `WORKFLOW_BLOCKED: Command failed (1): gh.exe auth status. Check tool availability and authentication.` The dirty original-checkout task preflight returned exit 2: `WORKFLOW_BLOCKED: Task worktree is dirty. Preserve existing work; do not stash, reset or broadly stage it.` Both failed closed without a traceback or mutation. Authentication/write access and live PR/merge/review/queue/hosted CI behavior remain unverified; credentials belong to the owner and no login was initiated.
- Focused project command `python -B -m unittest tests.test_build_contract tests.test_doc_budget tests.test_game_records tests.test_license_headers tests.test_progress_consistency -v` passed before review fixes (`Ran 11 tests in 0.035s`, `OK`) and after them (`Ran 11 tests in 0.024s`, `OK`). Artifact guard and `git diff --check -- AGENTS.md docs` passed; Git emitted only existing LF/CRLF normalization warnings for game records.
- Full local chain in the x64 MSVC developer environment: doctor, artifact guard, compileall, full unittest suite, `cmake --preset windows-msvc`, `cmake --build --preset windows-msvc`, and `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-msvc.ps1`. Background task completed with exit 0. Output: `build/manual-automation-msvc.log`.
- Actual full-suite outputs: `Ran 285 tests in 40.648s`, `OK`; wrapper suite `Ran 285 tests in 40.367s`, `OK`. CTest: `100% tests passed out of 3`, total 41.12 seconds. Doctor/artifact guard passed. Gate 0 report remains `PASS_LOCAL_DIFFERENTIAL_SPIKE`, `native_matches_oracle: true`, `windows_msvc_verified: true`, with C++20 and `/W4 /WX`; fixture/generated SHA-256 remain `b21f1f7793236d1ccba7308cc82f42d9f89915c87c0b037c46d8170f28349ca9` / `5316e0f51ba8b1fa1252e409f38cb9ac7db7606fee17b28ef0dcf1be162ae795`. This chain tested the project baseline; separate user-profile tests verify the guard, not a live GitHub workflow.
- Pre-append audit preserved all 136,298 normalized evidence bytes (SHA-256 `1da93d55c90d57fdc6adddf5d2127081e09108bca61af7f50863bbcf4d78fd42`), the owner's `.gitignore` fingerprint and the prior inspector fingerprint. HEAD remained `3fdc19c9c6ff7d4039c6b5f80615c97c6d8722e8`, with no staged files. STATE/HANDOFF measured 7,764/7,251 normalized UTF-8 bytes and longest lines 515/625, within enforced budgets. Git scope was the expected 26 modified paths, including preserved prior work and the added AGENTS policy edit; protected source/build/license/ADR/fixture paths were unchanged.
- No ISO was reopened, no retail code executed/extracted and no product feature added during automation setup. Gate 2/3 remain not passed, independent provenance reviews remain open, and build/CI/doctor remains `Review required`. Local installation/test evidence is not hosted CI, provenance certification or boot/compatibility support.
- Post-append audit printed `APPEND_ONLY_PREFIX_PASS`: the 107,808 committed evidence bytes and all 136,298 pre-automation bytes remain intact. It also printed `FINAL_PRESERVATION_PASS`: exactly 26 modified paths, no staged/untracked nonignored files, unchanged HEAD and preserved owner/inspector fingerprints. Final focused documentation/license/game/progress suite: `Ran 6 tests in 0.022s`, `OK`; artifact guard and scoped whitespace checks passed.

### Final review follow-up — pin the GitHub hostname

- The completed read-only review confirmed the effective-URL and explicit-run-binding corrections within their documented limits, and independently passed all 28 tests. It identified one further blocker: inheriting `GH_HOST` with an unqualified `OWNER/REPO` CLI target could route PR/CI checks and merge instructions to a same-named repository on another host. This was a local/mock finding, not an observed remote mutation; live GitHub integration remained unverified.
- Actual offline `gh help environment` documented `GH_HOST` host selection and the `[HOST/]OWNER/REPO` target form (`RPTP-REF-016`). New hostname/environment regressions failed before implementation: `Ran 31 tests in 0.065s`, `FAILED (failures=4)`, covering inherited alternate host, unqualified PR/current-head CI, merged-main CI and write-permission targets.
- Corrected every helper GitHub repository argument to `github.com/RidTheWann/RPTP-Project`; authentication explicitly targets `github.com`. Child-process `GH_HOST` and `GH_REPO` are pinned while the parent environment remains unchanged. Skill instructions now require the host-qualified target for every PR/create/edit/ready/watch/merge operation, rather than relying on environment or checkout inference. No credentials or Git/App settings were changed.
- Final user-profile suite: `python -B -m unittest discover -s <user-profile>/.qoder/skills/rptp-develop/tests -v`: `Ran 31 tests in 0.066s`, `OK`. Host-contract/skill/Python-compilation checks printed `FINAL_SKILL_HOST_CONTRACT_PASS`. An actual source-preflight subprocess with alternate `GH_HOST`/`GH_REPO` printed `HOST_PINNED_LIVE_GUARD 2` and the expected `gh.exe auth status` blocked diagnostic; `PARENT_ENVIRONMENT_PRESERVED` confirmed no parent override. This remains a fail-closed/auth-prerequisite smoke test, not authenticated remote success.
- Updated REFERENCES and current STATE/HANDOFF to include pinned-host coverage. Final focused project command passed `Ran 11 tests in 0.033s`, `OK`; artifact guard and scoped whitespace checks passed with only existing LF/CRLF warnings. Project source/build/CI/fixtures were not changed by this follow-up; the earlier full Windows/MSVC baseline remains separate from the final user-profile guard tests.
- Manual automation installation and local verification are complete. Owner GitHub authentication/write access and publication of the approved Git policy still gate a subsequent real development run. No live branch/PR/merge/hosted-CI claim, schedule, new dependency, Gate disposition, clean-room certification or retail execution is recorded.
- Final post-host-fix audit printed `FINAL_APPEND_ONLY_AND_PRIOR_WORK_PASS`: committed and pre-automation evidence prefixes, owner/inspector fingerprints, HEAD, empty staging/untracked set and the 26-path scope are preserved. STATE/HANDOFF measured 7,791/7,278 normalized UTF-8 bytes with longest lines 515/625. Scoped whitespace checks passed; no Git configuration or protection was modified.

## 2026-10-28 — Git-only policy publication and exact-commit CI

- After the owner completed CLI login, actual host-qualified authentication/permission checks verified the active RidTheWann account and repository write access. Fresh origin/main was `3fdc19c9c6ff7d4039c6b5f80615c97c6d8722e8`. Run `f0941a3674334d2285e53f92dcb54a79` created an isolated branch/worktree from that baseline; all 26 original dirty-file raw SHA-256 fingerprints, original HEAD and empty index matched before publication. No prior inspector/DADDIU/retail changes were copied, staged or included.
- Commits `6fbc4030f09244ab7ce20dbf1fefbc5a29f9116c` and `4ade0d41bbdedd0b5374fa44acbe995ddf05ece8` changed only AGENTS, STATE, HANDOFF and appended verification evidence. A read-only correctness reviewer found no blocking issue; a final UTF-8/newline-normalized scope review confirmed unchanged mission/legal/license/clean-room text and the append-only evidence prefix. Initial audit-script comparisons failed because Git blobs and Windows files used different line endings and the default subprocess decoding was not UTF-8; explicit UTF-8/newline normalization passed while all original raw fingerprints remained unchanged. No product test or implementation was changed to resolve those audit comparisons.
- The final-head local MSVC chain exited 0: doctor, artifact guard, compileall, full unittest, CMake configure/build and MSVC wrapper. Output in the isolated worktree: `build/final-policy-msvc.log`. Full suites: `Ran 236 tests in 34.172s`, `OK`, and `Ran 236 tests in 35.643s`, `OK`; CTest 3/3, total 36.43 seconds. Focused build/document/license/progress tests passed `Ran 10 tests in 0.032s`, `OK`. Separate profile-guard tests passed 31 tests; they are not part of hosted repository CI. The smaller committed baseline excludes earlier unpublished inspection additions; none were removed or weakened.
- [PR #9](https://github.com/RidTheWann/RPTP-Project/pull/9) was opened as draft, then made ready after review and verification. Final head `4ade0d41bbdedd0b5374fa44acbe995ddf05ece8` passed `ci.yml` push run [40597516240](https://github.com/RidTheWann/RPTP-Project/actions/runs/40597516240): Windows x64/MSVC job `122517080056`, Linux/GCC job `122517079642`. Its PR run [40597522743](https://github.com/RidTheWann/RPTP-Project/actions/runs/40597522743) also passed both jobs (`122517101144` / `122517100994`). Both watchers exited 0; exact run/job metadata was requeried rather than reusing an earlier head's result.
- After a fresh fetch, the bound guard returned `CI_READY` for the exact final head and run. It checked current PR head/review/merge readiness again before `gh pr merge --merge --match-head-commit 4ade0d41bbdedd0b5374fa44acbe995ddf05ece8`. No administrative override, direct main push, force-push, history rewrite, signing/hook bypass or protection change was used. The API subsequently reported `MERGED` with actual merge commit `b0206f5c9453f809f70d9ddee17c4ad1cebc84e9`.
- Actual main push run [40598028832](https://github.com/RidTheWann/RPTP-Project/actions/runs/40598028832) for that merge commit completed successfully: Windows x64/MSVC job `122518811875`, Linux/GCC job `122518811459`. Watcher exit 0, requeried metadata and bound `merged-ci --pr 9` returned `MERGE_CI_GREEN` for the actual merge SHA, not the feature SHA. The PR body records these post-commit observations; tested commit history is not rewritten to claim future results.
- Existing PR #7's conceptual-reference/provenance proposal and PR #8's SUBU work were not adopted, modified or merged. Accepted ADR-0003, license, Gate dispositions, fixtures, dependencies and product paths are unchanged. No ISO was reopened or extracted, no retail code executed, no schedule enabled and no compatibility/provenance certification claimed.
- Local main remains at `3fdc19c` while fetched origin/main contains the merge. The dirty checkout was not pulled, switched, reset, restored or stashed. Only publication/authentication wording in local STATE/HANDOFF/REFERENCES and this appended evidence are updated after the preservation check; prior product work and the entire 149,447-byte local evidence prefix remain preserved and uncommitted. Current-policy publication does not CI-verify those earlier changes.
- Final local handoff checks: `Ran 11 tests in 0.025s`, `OK`; artifact guard and scoped whitespace checks passed, with only existing game-record LF/CRLF warnings. `FINAL_PUBLICATION_HANDOFF_AUDIT_PASS` confirmed the 22 other original raw fingerprints, exactly the allowed status-line replacements, the untouched 149,447-byte evidence prefix (SHA-256 `988b9e588c06e974436a4d5c0b2bd222c0351549bc3965406a2877a9deb4a95d`), original main/HEAD, empty index/untracked set, original 26-path dirty scope and clean task worktree. Requeried PR metadata confirmed `MERGED`, the actual merge SHA and post-merge CI evidence in the public PR body. This local status/evidence follow-up remains uncommitted alongside earlier preserved work; no additional product or evidence-only PR was created.

## 2026-10-29 — Publication branch for preserved inspection work

- Run `3fe4dc55ebe14f91820347754b0aff34` created an isolated linked worktree from freshly fetched `origin/main` `b0206f5c9453f809f70d9ddee17c4ad1cebc84e9` after source preflight passed. The preserved inspector/load-map code, tests, game records and evidence were ported; the original checkout remains at `3fdc19c` with its 26-path dirty scope. `AGENTS.md` was not copied because main already contains the published policy.
- Focused pre-environment run: `python -m unittest tests.test_doc_budget tests.test_iso_inspector tests.test_instruction_daddiu -v` reported `Ran 120 tests in 13.903s`, `OK (skipped=2)`. The two skips were the native C++ differentials in a plain shell without `cl.exe`.
- Full chain in the x64 MSVC developer environment (`VsDevCmd.bat -arch=x64 -host_arch=x64`, Visual Studio 18 Community, MSVC 14.51.36231): doctor, artifact guard, compileall, full suite, CMake configure/build and `scripts/run-msvc.ps1` exited 0. Output: `build/automation-inspection-msvc.log` (local, ignored). Full suite `Ran 285 tests in 43.144s`, `OK`; wrapper suite `Ran 285 tests in 44.540s`, `OK`; CTest `100% tests passed out of 3`, 45.32 s. Both DADDIU native differentials ran and passed; the Gate 0 report retained `PASS_LOCAL_DIFFERENTIAL_SPIKE`, `native_matches_oracle: true` and `windows_msvc_verified: true`.
- Publication wording in STATE, HANDOFF, GATE2_EVIDENCE, ISO_INSPECTOR, ROADMAP, COMPATIBILITY and RISKS was updated from the former uncommitted state to the isolated-increment state. No hosted CI result was claimed before observation; exact-head and actual merge-commit results are appended only after observation. This section records local evidence only.
- No ISO was reopened, no retail code was executed or extracted, and no dependency, Gate disposition, clean-room status, boot or compatibility claim changed.

### Review follow-up — evidence wording and inspector error paths

- An independent read-only correctness review of the full change found no blocking defect. It identified stale game-record references to an `uncommitted working tree based on 3fdc19c`, a determinism claim that did not account for the path-derived `input_name`, and two untested inspector error paths. It also observed that survey accepts zero-length or loosely formed subdirectory metadata; that gap is recorded as R-028 instead of being silently fixed in this increment.
- The game records and index now cite the committed inspector revision `0c2264e`; the inspected file SHA-256 `a1bbc6f8c...` from the earlier runs matches that committed file. The ISO contract now scopes determinism to the supplied path plus bytes and documents that `input_name` is not content-derived.
- New tests cover `PRIMARY_VOLUME_DESCRIPTOR_MISSING`, `INVALID_VOLUME_SIZE` for declared volumes 0 and 16, and the path-derived `input_name` contract. Focused run: `python -m unittest tests.test_iso_inspector tests.test_doc_budget tests.test_game_records -v` reported `Ran 115 tests in 4.435s`, `OK`.
- The review also confirmed the DADDIU fixture literals, trace/PC and 18-instruction count, and found no premature exact-head CI claim. This is a technical review, not an independent provenance disposition.
- The post-fix Windows/MSVC chain exited 0: doctor, artifact guard, compileall, full suite, CMake configure/build, CTest and `scripts/run-msvc.ps1`. Output: `build/automation-inspection-msvc-fix.log` (local, ignored). Full suite `Ran 288 tests in 39.359s`, `OK`; wrapper suite `Ran 288 tests in 38.594s`, `OK`; CTest `100% tests passed out of 3`, 38.42 s. The Gate 0 report again reported `PASS_LOCAL_DIFFERENTIAL_SPIKE`, `native_matches_oracle: true` and `windows_msvc_verified: true`.

## 2026-10-29 — Inspection increment merge and SLL synthetic differential

- PR #10 was merged with the pinned head `1b9a0b461ab2d8d4e9afab1da1d04b1cd7929965` (`gh pr merge --match-head-commit`). The API reported state `MERGED`, merge commit `a1365b5255cde61973ca1bdda8742748bb9b0b2a` and `mergedAt` 2026-10-28T21:14:01Z. Exact-head push run `40769859822` had already passed both jobs.
- The main-branch push run `40770223526` for `a1365b5` completed with conclusion `success`; job `Windows x64 / MSVC` `123105097542` and job `Linux / GCC` `123105097819` both succeeded. The bound `merged-ci --pr 10` check returned `MERGE_CI_GREEN` with that merge SHA and run ID.
- Run `a1a9f33e87f84ee1b3c119f5cd706a2e` created a new isolated linked worktree from freshly fetched `origin/main` `a1365b5`. Test-first SLL work failed against the pre-feature tree: `Ran 10 tests`, `FAILED (failures=1, errors=6, skipped=2)` with `Unsupported SPECIAL instruction 0x00084FC0`, and the two skips were native differentials in a shell without `cl.exe`.
- Implementation: the decoder accepts SPECIAL funct `0x00` only with `rs=0`, keeps the all-zero word as `NOP` and rejects nonzero `rs`; the oracle shifts the low 32 bits of `rt` by the 5-bit amount, truncates to 32 bits and sign-extends into the modeled 64-bit array; the IR records `immediate_kind = shift5`; the lowerer validates `rs=0`, `rt`, `rd`, `shamt` 0..31 and the destination register, and emits an `sll32` helper only when needed. `RPTP-REF-002` supplies the encoding and 32-bit shift semantics; the sign-extension bridge is recorded as an RPTP test definition in `docs/REFERENCES.md`.
- Focused native run in the x64 MSVC environment (`VsDevCmd.bat -arch=x64 -host_arch=x64`, MSVC 14.51.36231): `python tests/test_instruction_sll.py -v` reported `Ran 10 tests in 3.160s`, `OK`; both native differentials executed rather than skipped.
- Full local chain exited 0: doctor, artifact guard, compileall, full suite, CMake configure/build and `scripts/run-msvc.ps1`. Full suite `Ran 298 tests in 41.185s`, `OK`; the wrapper completed and printed `MSVC Gate 0 spike completed`. CTest (`ctest --test-dir build/cmake-msvc --output-on-failure`) reported `100% tests passed out of 3`, total 41.44 s. The Gate 0 report retained `"status": "PASS_LOCAL_DIFFERENTIAL_SPIKE"`.
- SLL fixture SHA-256 `94b493a323f272488f0a3c65ae5995c8454be6688e3d84f1b786d5d360ae60b7`; generated C++ SHA-256 `67bd09d82178668e60f73bf4c50059cc82a2a4ac28b3d2a3048c050b75ead30d`; 17 instructions. A first CTest attempt in a plain shell failed only because `cl` was absent from `PATH`; rerunning inside the developer environment passed.
- No ISO was reopened or extracted, no retail code executed, and no dependency, Gate disposition, clean-room status, boot or compatibility claim changed.
- An independent read-only review of `57568ca` found no BLOCKER or SHOULD-FIX findings. Its NIT items were resolved in a follow-up commit: an IR-level `rs=0` rejection for SLL with a new fail-closed test, helper-harness coverage widened to shamt 0/1/4/16/30/31, and documentation consistency fixes in `docs/IR_CFG.md` and `docs/INSTRUCTION_CATALOG.md`. The reviewer independently recomputed the recorded fixture and generated-C++ hashes and both matched.
- Post-fix local chain exited 0: full suite `Ran 299 tests in 40.349s`, `OK`; focused SLL suite `Ran 11 tests in 3.392s`, `OK`; CTest `100% tests passed out of 3` in 42.33 s; Gate 0 report retained `PASS_LOCAL_DIFFERENTIAL_SPIKE`. These are local results, not hosted CI.

## 2026-10-29 — Read-only boot-code census increment

- Isolated worktree `build/automation-worktrees/abdad902f18f49b4b623fe6944740845`, branch `automation/abdad902f18f49b4b623fe6944740845`, based on freshly fetched `origin/main` `a1365b5255cde61973ca1bdda8742748bb9b0b2a`. No pre-existing checkout was modified.
- New `tools/rptp_census.py` counts aligned 4-byte words in file-backed `PT_LOAD` ranges of a validated ELF32 boot executable, classifies each with the current synthetic IR decoder, and labels rejected words only by raw encoding ID (`special_0xNN`, `regimm_0xNN`, `opcode_0xNN`). ISO input is inspected and read in memory; nothing is extracted, written, executed or recompiled. Limits: 16 MiB boot bytes, 4,194,304 words; deterministic JSON; CLI exit 0/2.
- New `tests/test_boot_census.py` builds synthetic ELFs and an ISO at test time. Six tests cover supported/raw-unsupported counts, trailing bytes, non-ELF and size-limit failures, determinism/non-mutation, the ISO in-memory path, input non-modification and CLI JSON success/error. No retail bytes are in tests.
- Earlier this session, before this log entry, all eight owner-authorized images were censused read-only in memory. Decoder-accepted ratios were 50.0%–59.2%; whole-image hashes were not recomputed in that run, and the two San Andreas samples produced identical boot hashes/counts consistent with prior records. Per-image figures, top raw encodings and limitations are in [BOOT_CENSUS.md](BOOT_CENSUS.md); each `docs/games/<slug>/STATUS.md` and the index were updated. Counts include data/padding and are planning evidence only.
- Documentation updated: `BOOT_CENSUS.md` (new), `INSTRUCTION_CATALOG.md`, `REFERENCES.md`, `CLEAN_ROOM_AUDIT.md`, `ROADMAP.md`, `STATE.md`, `HANDOFF.md`, `games/README.md` and eight game records. No component status, Gate disposition, fixture, dependency or policy changed.
- Full local chain in the x64 MSVC developer environment (`VsDevCmd.bat -arch=x64 -host_arch=x64`, Visual Studio 2026 Developer Command Prompt v18.11.1, MSVC 14.51.36231) exited 0: doctor, artifact guard, compileall, full suite, CMake configure/build (`MSVC 19.51.36260.0`), CTest and `scripts/run-msvc.ps1`. Output: `build/census-msvc.log` (local, ignored). Full suite `Ran 294 tests in 71.166s`, `OK`; wrapper suite `Ran 294 tests in 71.654s`, `OK`; CTest `100% tests passed out of 3` (artifact guard 0.08 s, Python suite 73.28 s, Gate 0 spike 3.57 s). Gate 0 report: `PASS_LOCAL_DIFFERENTIAL_SPIKE`, `native_matches_oracle: true`, `windows_msvc_verified: true`.
- No hosted CI result is claimed in this entry. Exact-head and actual merge-commit results are appended only after observation.

## 2026-10-29 — Native runtime loader foundation (increment R1)

- Isolated worktree `build/automation-worktrees/4879c9691c1f4fa0946ee03eb9e9fec9`, branch `automation/4879c9691c1f4fa0946ee03eb9e9fec9`, based on freshly fetched `origin/main` `88d7c68d7f8d3872ff94ef3543bc6b40f48a11c3`. No pre-existing checkout was modified.
- Hosted evidence observed this session for earlier increments: PR #11 head `7365736059d091d8a45ff51cf27771c4b01ac842` merged as `1ee2d4d0865c1f402b2dd53ce00e58ae67ddb5dc` at 2026-10-29T05:51:59Z with main CI run `40825838439` green; PR #12 head `a9da4a3276bd19f302e696760eae4fb6f413f03e` merged as `88d7c68d7f8d3872ff94ef3543bc6b40f48a11c3` at 2026-10-29T06:18:50Z with main CI run `40828451046` (`RPTP CI`) and pages run `40828450196` both green.
- New C++20 layer under `runtime/`: `GuestMemory` stores non-overlapping guest regions with single-region `read`/`write`/`view`, zero-fill and allocation budgets; `load_elf` validates ELF32 little-endian `ET_EXEC`/`EM_MIPS` headers and `PT_LOAD` sizes, file bounds, alignment congruence, 32-bit address-space bounds, ascending order and overlap; the entry point must be file-backed and executable; errors use stable `LOAD_*` codes. `rptp-load` adds deterministic `rptp.runtime.load.v1` JSON and exit codes `0`/`2`/`1`. Contract: [RUNTIME.md](RUNTIME.md).
- Test-first evidence: the first run against a stub loader failed 43 C++ checks, and the six Python CLI tests failed because no binary existed. Two fixture defects found during the red/green cycle were corrected before the green run: synthetic payload bytes initially overwrote the second program header (table spans 52..116), and error fixtures needed an explicit 84-byte image so the "table past image" case failed for the intended reason. The corrected C++ and Python suites then passed.
- Full local chain in the x64 MSVC developer environment (`VsDevCmd.bat -arch=x64 -host_arch=x64`, Visual Studio 2026 Developer Command Prompt v18.11.1, MSVC 14.51.36231): doctor `Overall status: PASS`; CMake configure/build (`MSVC 19.51.36260.0`); CTest `100% tests passed out of 5` (`artifact_guard`, `python_unit_tests`, `gate0_differential_spike`, `runtime_loader_tests` 0.01 s, `runtime_loader_cli` 0.25 s), total 85.48 s; `scripts/run-msvc.ps1` completed with `Ran 312 tests`, `OK (skipped=7)`. Full Python suite in the same environment: `Ran 312 tests in 5.167s`, `OK (skipped=29)`; the skips are the build-gated CLI tests and native differentials outside CTest.
- Gate 0 synthetic fixture through the new CLI (exit 0): `{"schema":"rptp.runtime.load.v1","status":"ok","image_bytes":4208,"entry_point":"0x00100000","load_segment_count":1,"total_file_bytes":112,"total_memory_bytes":112,"segments":[{"program_header_index":0,"virtual_address":"0x00100000","file_offset":4096,"file_size":112,"memory_size":112,"flags":5,"executable":true,"writable":false,"alignment":4096}]}`.
- License-header coverage was extended to project `.hpp`/`.cpp` files. The first full-suite run failed because tracked `evidence/host-gcc/generated.cpp` is captured build output, not authored source; the coverage rule now excludes `evidence/`, and the suite passed afterward.
- Exact-head CI on `6594ca68edf64b04aafc2354c73ddd17a184aee0` (run `40830441333`) failed both jobs in `test_license_headers`: the six new C++ files carry `// SPDX-License-Identifier: GPL-3.0-or-later`, while the policy expected the `#` form. Those files were untracked during the earlier local run, so `git ls-files --cached` skipped them. The policy now selects `//` for `.hpp`/`.cpp` and keeps `#` for Python, PowerShell, CMake and workflow files, with a new `test_expected_header_comment_style`; the full local suite then reported `Ran 314 tests in 5.287s`, `OK (skipped=29)`. A follow-up commit updates the PR head and exact-head CI must run again.
- Documentation updated: `RUNTIME.md` (new), `STATE.md`, `HANDOFF.md`, `ROADMAP.md` (B2 section and PR #11/#12 evidence), `CLEAN_ROOM_AUDIT.md`, `REFERENCES.md` (`RPTP-REF-017` plus the loader contract), `BUILD_PROVENANCE.md`, `INCREMENT_LEDGER.md`, `README.md` and this log. No component status change beyond adding the loader as `Provisional independent`.
- No ISO was reopened, extracted or executed; no retail bytes entered the repository or the tests. No dependency, Gate disposition, clean-room certification, boot or compatibility claim changed.
- Exact-head CI on `15886111b2cb1f62c7c769786e9d1ddb07cd4bf1` passed: push run `40830674504` and pull-request run `40830681043` both completed with `Windows x64 / MSVC` and `Linux / GCC` success; the read-only guard returned `CI_READY`.
- PR #13 merged with `--match-head-commit 1588611` at 2026-10-29T06:42:40Z as `5a5debfc5629312a0c07c5afcfd771c36a573bcb`. Main push run `40830858381` (`RPTP CI`) and pages run `40830857852` completed green; both jobs passed on the actual merge commit.
- The first exact-head attempt on `6594ca68edf64b04aafc2354c73ddd17a184aee0` (run `40830441333`) failed both jobs in `test_license_headers`; follow-up `1588611` corrected the C++ comment-prefix policy and is recorded above. No other CI failure was observed.

## 2026-10-29 — Documentation evidence merge (PR #14)

- Documentation-only increment based on freshly fetched `origin/main` `5a5debfc5629312a0c07c5afcfd771c36a573bcb` in an isolated worktree. It recorded the PR #13 loader evidence in `STATE.md`, `HANDOFF.md`, `ROADMAP.md`, `INCREMENT_LEDGER.md`, `CLEAN_ROOM_AUDIT.md` and this log, and trimmed `docs/STATE.md` back under the 8192-byte budget. No code, fixture, Gate disposition, component status or compatibility claim changed.
- The document-budget test passed locally after trimming. Exact-head CI on `88022cab1b1b12648fe71494f4a5fce99441708b` passed: push run `40831231418` and pull-request run `40831239066` both reported `Windows x64 / MSVC` and `Linux / GCC` success.
- PR #14 merged with pinned head `88022ca` at 2026-10-29T06:48:00Z as `d05500746be76b0594eefd40d06db02e1349b6c8`. Main push run `40831406065` (`RPTP CI`) and pages run `40831404626` both completed with conclusion `success`.

## 2026-10-29 — Synthetic execution harness (increment R2)

- Isolated worktree `build/automation-worktrees/aa1495849d5f4f959be4f924619afa3d`, branch `automation/aa1495849d5f4f959be4f924619afa3d`, based on freshly fetched `origin/main` `d05500746be76b0594eefd40d06db02e1349b6c8`. No pre-existing checkout was modified.
- New C++20 execution layer: `execute_loaded` runs the accepted Gate 0 subset (ADDIU, ADDU, LW, SW, BEQ, BNE, J, JAL, JR, NOP) with one explicit delay slot over a loaded image; all registers start at zero; fetch requires a mapped executable segment; an unmapped PC halts with `unmapped-pc`; `EXEC_*` codes cover unaligned entry/PC, unsupported instructions, non-executable fetch, fetch/memory faults, control in a delay slot, missing delay slot and the step budget. SW writes are recorded and emitted in deterministic address order. `rptp-run` adds deterministic `rptp.runtime.run.v1` JSON, `--trace`, `--max-steps` and image/guest limits with exit `0`/`2`/`1`. Contract: [RUNTIME.md](RUNTIME.md).
- Test-first evidence: the feature tests were added first; a local build failed with `fatal error C1083: Cannot open include file: 'rptp/runtime/execution.hpp'`, as expected before the header existed. The CLI loader-taxonomy test initially used a 16-byte input and observed `LOAD_IMAGE_TOO_SMALL` because size is checked before the magic; the test now builds a 64-byte non-ELF image and observes `LOAD_NOT_ELF`.
- New tests: direct C++ checks in `runtime/tests/runtime_tests.cpp` for arithmetic/memory, a 19-step branch/call/delay-slot program with expected trace and final PC, fail-closed cases (unsupported word, jump into data, store outside segments, control in a delay slot, missing delay slot, step limit, zero budget, unaligned entry) and determinism; `tests/test_runtime_execution.py` builds synthetic two-segment images and compares steps, trace, final PC, all 32 registers and memory writes against the Gate 0 oracle. CTest gained `runtime_execution_cli`.
- Local results in the x64 MSVC developer environment: C++ execution checks passed; the nine Python CLI execution tests reported `Ran 9 tests`, `OK`; the full Python suite reported `Ran 323 tests`, `OK (skipped=29)`; CTest reported `100% tests passed out of 6`, including `runtime_loader_tests` and `runtime_execution_cli`; `scripts/run-msvc.ps1` completed with `Ran 323 tests`, `OK (skipped=16)`. The Gate 0 fixture run through `rptp-run` exits `2` with `EXEC_MEMORY_FAULT` because its data store is outside the single RX segment; this is the expected fail-closed result, not a harness regression.
- Documentation updated in the increment: `RUNTIME.md`, `REFERENCES.md` (execution-harness contract paragraph), `README.md`, `BUILDING_WINDOWS.md` and `tests/test_build_contract.py`. No Gate disposition, component status, dependency, ISO access, boot or compatibility claim changed. No retail code was executed.
- Exact-head CI on `b8e1e722274ddcee2313183128557b3438c6f0de` passed: push run `40832421475` and pull-request run `40832433086` both reported `Windows x64 / MSVC` and `Linux / GCC` success; the read-only guard returned `CI_READY` with `mergeStateStatus` `CLEAN`.
- PR #15 merged with `--match-head-commit b8e1e72` at 2026-10-29T07:00:03Z as `ebcc2b0a0f355226c341c1a9bdc94a105c0fe9f9`. Main push run `40832620535` (`RPTP CI`) and pages run `40832619554` both completed with conclusion `success`.

## 2026-10-29 — Extended synthetic execution subset (increment R3)

- Isolated worktree `build/automation-worktrees/463f36d307684ef6a72ffd4a0248027a`, branch `automation/463f36d307684ef6a72ffd4a0248027a`, based on freshly fetched `origin/main` `6629c15667285a068d782575be92e1c5ed1b8fd0`. No pre-existing checkout was modified.
- Behavior: `execute_loaded` now also executes `SLL`, `SLT`, `SLTU`, `SLTI`, `SLTIU`, `DADDIU`, `AND`, `OR`, `XOR`, `NOR`, `ANDI`, `ORI`, `XORI` and `LUI` using the oracle's test-defined 64-bit register model. `LUI` and `SLL` require `rs=0`, register-register forms require `shamt=0`, and all other encodings still fail with `EXEC_UNSUPPORTED_INSTRUCTION`. The harness contract in `docs/RUNTIME.md` and `docs/REFERENCES.md` was updated in the same commit; this log entry records the evidence only.
- The extended tests and implementation were completed before the first local build; no red run is recorded for this increment. `runtime/tests/runtime_tests.cpp` adds a 23-instruction program with literal expected registers and one memory write plus three malformed-encoding failure cases. `tests/test_runtime_execution.py` adds an independent 23-instruction image and compares steps, trace, final PC, all 32 registers and memory writes against `tools/rptp_gate0_spike.execute_oracle`; the first instruction normalizes the oracle's `ra` sentinel.
- Local results in the x64 MSVC developer environment (`VsDevCmd.bat -arch=x64 -host_arch=x64`): CMake configure/build passed with `/W4 /WX`; CTest reported `100% tests passed out of 6`, including `runtime_loader_tests`, `runtime_loader_cli` and `runtime_execution_cli`; `tests.test_runtime_execution` with `RPTP_RUN_BINARY` reported `Ran 10 tests`, `OK`; the full Python suite reported `Ran 324 tests`, `OK (skipped=39)`; `scripts/run-msvc.ps1` completed with `Ran 324 tests`, `OK (skipped=17)`. The Gate 0 fixture still exits `2` with `EXEC_MEMORY_FAULT`.
- Exact-head CI on `6d8df3190ad60d4ecc01716e4e43b12575c8aae1` passed: push run `40834447751` and pull-request run `40834462851` both reported `Windows x64 / MSVC` and `Linux / GCC` success; the read-only guard returned `CI_READY` with `mergeStateStatus` `CLEAN`.
- PR #17 merged with `--match-head-commit 6d8df31` at 2026-10-29T07:18:43Z as `ddc0de56b575d7a2c6b13ddf59d316d5d089996b`. Main push run `40834619976` (`RPTP CI`) and pages run `40834619737` both completed with conclusion `success`.
- Documentation updated after the merge in the accompanying evidence increment: `STATE.md`, `HANDOFF.md`, `ROADMAP.md`, `INCREMENT_LEDGER.md`, `CLEAN_ROOM_AUDIT.md` and this log. No Gate disposition, component status, dependency, ISO access, boot or compatibility claim changed; no retail code was executed.

## 2026-10-29 — `DADDU` synthetic increment (PR #19)

- Isolated worktree `build/automation-worktrees/ec51e0dbfff44dde9ca70b8b596abf48`, branch `automation/ec51e0dbfff44dde9ca70b8b596abf48`, based on freshly fetched `origin/main` `0f34d9ebfc94679ae39e1844a25891fcfa9e3abe`. No pre-existing checkout was modified.
- Behavior: `SPECIAL` funct `0x2D` with `shamt=0` decodes as `DADDU` and adds two full modeled 64-bit register values modulo 2^64 without an overflow trap, per `RPTP-REF-015` (MIPS64 Vol II-A DADDU, printed p.132). The oracle, IR classifier, deterministic C++ lowerer and native execution harness share the semantics; nonzero `shamt` stays unsupported and `$zero` writes are discarded.
- Test-first evidence: `python -m unittest tests.test_instruction_daddu -v` initially reported `FAILED (errors=6, skipped=2)` with `Unsupported SPECIAL instruction 0x0109502D` at `0x0010000C`. The focused suite after implementation reported `Ran 11 tests`, `OK` under `VsDevCmd.bat -arch=x64 -host_arch=x64`, exercising the native lowered program and the independent native boundary helper.
- Local results in the x64 MSVC developer environment: CMake configure/build passed with `/W4 /WX`; CTest `rptp-ci` reported `100% tests passed out of 6`; `tests.test_runtime_execution` with `RPTP_RUN_BINARY` reported `Ran 10 tests`, `OK`, including literal checks for `daddu` results and `$zero`; `runtime/tests/runtime_tests.cpp` covers the 26-word extended subset plus nonzero-`shamt` rejection.
- Exact-head CI on `85f5b26493aeb4c50ba936d04b191d21826c0e5f` passed: push run `40836534432` and pull-request run `40836544427` both reported `Windows x64 / MSVC` and `Linux / GCC` success; the read-only guard returned `CI_READY` with `mergeStateStatus` `CLEAN`.
- PR #19 merged with `--match-head-commit 85f5b26` at 2026-10-29T07:38:13Z as `0225916c1f45a85a2078f4c67f2544db53b0cf59`. Main push run `40836707828` (`RPTP CI`) completed with `Windows x64 / MSVC` and `Linux / GCC` success; the guard returned `MERGE_CI_GREEN`.
- Local documentation checks on the evidence increment: `tests.test_doc_budget` reported `Ran 3 tests`, `OK`; full `python -m unittest discover -s tests` reported `Ran 335 tests`, `OK (skipped=41)` without the MSVC environment, so native-backed tests were skipped in that plain-shell run and the MSVC/CTest results above remain the native evidence. No Gate disposition, component status, dependency, ISO access, boot or compatibility claim changed; no retail code was executed.
- PR #20 merged with `--match-head-commit 824098f` at 2026-10-29T07:44:06Z as `0d4b497d688bb54dc6d6b11452e5db1cfae4f459` (exact-head runs `40837155964`/`40837160783`). Main push run `40837332410` passed `Windows x64 / MSVC` and `Linux / GCC`; the guard returned `MERGE_CI_GREEN`.

## 2026-10-29 — Read-only boot-code census refresh after `DADDU`

- Isolated worktree `build/automation-worktrees/024c29f3cdd8f3b3d06af5bb11ee7f18`, branch `automation/024c29f3cdd8f3b3d06af5bb11ee7f18`, based on freshly fetched `origin/main` `0d4b497d688bb54dc6d6b11452e5db1cfae4f459`. No pre-existing checkout was modified.
- All eight owner-authorized images in `D:\List Games` were reopened read-only through `tools/rptp_census.py <iso> --iso --json` with the current decoder after `SLL` and `DADDU`. Exit code was `0` for every image and no file was extracted, modified or executed. Whole-image hashes were not recomputed in this run; the two San Andreas samples again produced identical boot sizes and census counts.
- Current results: Black 473,481/801,120 (59.1%); Bully 760,604/1,282,560 (59.3%, `CENSUSED_WITH_WARNINGS`); Downhill Domination 259,646/413,500 (62.8%); God of War II 325,561/520,042 (62.6%); GTA San Andreas Indonesian v6 828,703/1,420,864 (58.3%, `CENSUSED_WITH_WARNINGS`); GTA San Andreas USA v3.00 828,703/1,420,864 (58.3%, `CENSUSED_WITH_WARNINGS`); Need for Speed - Most Wanted 847,057/1,224,439 (69.2%); Resident Evil 4 435,621/731,082 (59.6%). Raw JSON reports are local artifacts under `build/census/` and are not committed.
- The `CENSUSED_WITH_WARNINGS` statuses come from the previously recorded `PT_LOAD` memory overlaps, not from census counts. `special_0x2d` no longer appears among the top unsupported labels; the most frequent raw labels are `opcode_0x11`, `opcode_0x31`, `opcode_0x37`, `opcode_0x39` and `opcode_0x3f`. Counts include data and padding and remain planning evidence, not function-level, runtime, boot or compatibility measurements.
- Documentation updated: `BOOT_CENSUS.md`, all eight `docs/games/<slug>/STATUS.md` records, `docs/games/README.md`, `STATE.md`, `HANDOFF.md` and this log. No Gate disposition, component status, dependency or compatibility claim changed; no retail code was executed.

## 2026-10-29 — `SUBU` synthetic increment (PR #22)

- Isolated worktree `D:/RPTP-worktrees/ac396318567d48de98f9ad77127ad4e8`, branch `automation/ac396318567d48de98f9ad77127ad4e8`, based on freshly fetched `origin/main` `e9117118392896b3958da29971d87f7a3eefb349`. No pre-existing checkout was modified; the separate `D:\RPTP-Project` development checkout was left untouched.
- Behavior: `SPECIAL` funct `0x23` with `shamt=0` decodes as `SUBU` and subtracts the low 32 bits of `rt` from the low 32 bits of `rs` modulo 2^32, sign-extending the 32-bit result, per `RPTP-REF-015` (MIPS64 Vol II-A SUBU, printed p.355; the page number was confirmed from the locally extracted manual text, whose footer reads 355). `$zero` writes are discarded; nonzero `shamt`, `SUB` (`0x22`) and `DSUBU` (`0x2E`) stay unsupported. The reference marks a non-word-value source UNPREDICTABLE; truncation to the low 32 bits is the RPTP test definition that makes the result deterministic.
- This re-implements the closed PR #8 work test-first on current `origin/main` under the adopted increment-branch policy, with `RPTP-REF-015` instead of the reassigned `RPTP-REF-016`.
- Test-first evidence: before implementation `python -m unittest tests.test_instruction_subu -v` reported `Ran 13 tests`, `FAILED (errors=6, skipped=2)`; the two skips are the native differentials when no compiler is on `PATH`. After implementation the same focused command reported `Ran 13 tests`, `OK` with 0 skipped under `VsDevCmd.bat -arch=x64 -host_arch=x64`.
- Local results in the x64 MSVC developer environment (MSVC toolset `14.51.36231`, VS 2026 BuildTools): `tools/rptp_doctor.py` PASS, `tools/check_forbidden_artifacts.py --root .` PASS, CMake configure and build PASS with `/W4 /WX`, `python -m compileall -q tools tests` PASS, `python -m unittest discover -s tests` reported `Ran 348 tests`, `OK (skipped=17)`, and CTest reported `100% tests passed, 0 tests failed out of 6` (`artifact_guard`, `python_unit_tests`, `gate0_differential_spike`, `runtime_loader_tests`, `runtime_loader_cli`, `runtime_execution_cli`). The 17 skips are unrelated to this increment; the focused `SUBU` suite skipped none.
- Exact-head CI on `a20692e6b91aab29c45a90c9daefb71990029e64` passed: push run `40849253585` and pull-request run `40849277757` both reported `Windows x64 / MSVC` and `Linux / GCC` success, and the PR reported `mergeStateStatus` `CLEAN`.
- PR #22 merged with `--match-head-commit a20692e` at 2026-10-29T09:25:14Z as `21fdffc4ad9eaada7bad69204fd5a7ace4368d89`. Main push run `40849490715` (`RPTP CI`) completed with `Windows x64 / MSVC` and `Linux / GCC` success.
- Census: the eight-image figures in [BOOT_CENSUS.md](BOOT_CENSUS.md) were not refreshed and remain dated to the pre-`SUBU` decoder; this workplace machine holds only `Downhill Domination (USA).iso` under `D:\Game`, so a full read-only refresh needs the home machine and is tracked as `R-029` in [RISKS.md](RISKS.md). No image was opened, modified or executed in this increment.
- Documentation updated in the feature PR: `INSTRUCTION_CATALOG.md` (new `SUBU` row, lowering coverage, verification command), `IR_CFG.md` (lowering semantics, subset list, reference bullet), `RUNTIME.md` (executed subset and arithmetic model), `REFERENCES.md` (`RPTP-REF-015` extended to p.355 plus a `SUBU` model paragraph), `BOOT_CENSUS.md` (dated pre-`SUBU` note only, no figure change) and `CLEAN_ROOM_AUDIT.md` (test-path row). This evidence increment updates `INCREMENT_LEDGER.md`, `RISKS.md`, `STATE.md`, `HANDOFF.md` and this log. No Gate disposition, component status, dependency or compatibility claim changed.

## 2026-10-29 — evidence-derived progress page (PR #24)

- Isolated worktree `D:/RPTP-worktrees/36f0cae835d445d7aca86955ec0b427d`, branch `automation/36f0cae835d445d7aca86955ec0b427d`, based on `7be10c1`. Motivation: the published map kept `Updated 2026-10-24`, still ended its "Next" line at `SLTU`, and could not show the `SLL`, `DADDIU`, `DADDU` or `SUBU` increments.
- Behavior: `tools/rptp_progress.py` now derives the snapshot date from the newest dated `VERIFICATION_LOG.md` section and the supported subset from `INSTRUCTION_CATALOG.md` (26 instructions), publishing that count on the map, the page and the README. The clipped SVG notes were split into readable lines. Checklist statuses and percentages are unchanged (foundation 77.8%, runtime 5.0%); they count checklist items, not instructions.
- Test-first evidence: `python -m unittest tests.test_progress_consistency -v` reported `Ran 4 tests`, `FAILED (errors=3)` before the helpers existed; after implementation the same command reported `Ran 4 tests`, `OK`. New tests enforce the log-derived date, require rendered assets to equal the generator output, and require the README to report the catalogued count.
- Local results in the x64 MSVC developer environment (MSVC toolset `14.51.36231`): `tools/rptp_doctor.py` PASS, `tools/check_forbidden_artifacts.py --root .` PASS, CMake configure and build PASS with `/W4 /WX`, `python -m compileall -q tools tests` PASS, `python -m unittest discover -s tests` reported `Ran 351 tests`, `OK (skipped=17)`, and CTest reported `100% tests passed, 0 tests failed out of 6`. An earlier background run raced with an in-progress edit and failed only `docs/assets/progress.svg is stale`; the final tree was regenerated and re-verified from scratch, and that race is noted as process evidence only.
- Exact-head CI on `f3ab05f2b4663805452d98a91edcbbd0169c9a06` passed: push run `40852544274` and pull-request run `40852561578` reported `Windows x64 / MSVC` and `Linux / GCC` success, and the PR reported `mergeStateStatus` `CLEAN`.
- PR #24 merged with `--match-head-commit f3ab05f` as `cf2152e859ff5c5af9f663b9f94e0735fb84d071`. Main push run `40852773918` and `pages build and deployment` run `40852772990` succeeded. The live page at `https://ridthewann.github.io/RPTP-Project/progress.html` reports `Last updated 2026-10-29` and `26 instructions are catalogued`.
- Limitation: percentages still move only when a checklist item changes status; they are scope checklists, not instruction counts or completion. GitHub's image proxy can cache the README map, so the embedded image may lag the page. No Gate disposition, component status, dependency or compatibility claim changed.

## 2026-10-29 — README progress-image cache-busting (PR #26, PR #27)

- Isolated worktrees `D:/RPTP-worktrees/509b709b0aca47d6bcb5452a2b18b890` (PR #26) and `D:/RPTP-worktrees/c3173ee53e8040bfbc09fccc2b18d24f` (PR #27), branches `automation/509b709b0aca47d6bcb5452a2b18b890` and `automation/c3173ee53e8040bfbc09fccc2b18d24f`, based on `d96ebd2` and `b2ddedf`. No pre-existing checkout was modified.
- Symptom: after PR #24 and PR #25 the Pages page served `Last updated 2026-10-29`, while the README `<img>` still rendered `Updated 2026-10-24`. The Pages assets were fresh; GitHub's image proxy (`camo.githubusercontent.com`) had cached the SVG by URL, and the README URL had not changed.
- Behavior: README image URLs now end in `?v=<log-date>-<digest>`, where the digest is the first 12 hex characters of the SHA-256 of the asset text after CRLF→LF newline normalization, so any asset change alters the URL and forces a proxy refetch. `tests/test_progress_consistency.py` requires the exact versioned URLs for `badge-foundation.svg`, `badge-runtime.svg` and `progress.svg`; the generator itself is unchanged.
- Test-first evidence: in PR #26 the new URL test reported `Ran 5 tests`, `FAILED (failures=3)` before the README edit; in PR #27 the strengthened digest test again reported `Ran 5 tests`, `FAILED (failures=3)` with the date-only URLs in place. Both runs ended `Ran 5 tests`, `OK` after the edits.
- Local results in the feature worktrees: plain-shell `python -m unittest discover -s tests` reported `Ran 352 tests`, `OK (skipped=43)`; `tools/check_forbidden_artifacts.py --root .` passed. Native coverage came from the exact-head CI jobs below.
- Exact-head CI: PR #26 on `3940ba1` (push run `40854284453`, pull-request run `40854294006`) and PR #27 on `2873307` (push run `40854910369`, pull-request run `40854926548`) all reported `Windows x64 / MSVC` and `Linux / GCC` success.
- PR #26 merged with `--match-head-commit 3940ba1` at 2026-10-29T10:03:36Z as `b2ddedf`; main run `40854511196` and pages run `40854509623` succeeded. PR #27 merged with `--match-head-commit 2873307` at 2026-10-29T10:08:27Z as `f8c2c52`; main run `40855167007` and pages run `40855166084` succeeded.
- Verified after merge: `raw.githubusercontent.com` serves the three versioned URLs (progress digest `8df7b2fa06e4`), and the GitHub-rendered README points the progress image at a camo URL whose response contains `Updated 2026-10-29` and `26 catalogued synthetic instructions`.
- Limitation: the consistency test enforces the versioned URLs but does not rewrite `README.md`; after an asset change, run `python tools/rptp_progress.py`, update the README digests and re-run the suite. No Gate disposition, component status, dependency or compatibility claim changed; no retail code was executed.

## 2026-10-29 — documentation freshness audit

- Scope and worktree: `D:/RPTP-worktrees/docfresh`, branch `automation/docfresh`, based on `f967448` (the PR #28 merge). Documentation-only: no decoder, lowering, runtime, build, fixture or dependency change.
- Trigger: an audit of every document found stale current-status claims after PR #28 — STATE/HANDOFF ended at PR #27/`f8c2c52`; ROADMAP, README and COMPATIBILITY lacked the `SLL`, `DADDU` and `SUBU` fixtures or cited run #45; CLEAN_ROOM_AUDIT stopped at PR #17; PROVENANCE_PLAN said implementation had not started; RISKS R-024–R-026 called merged CI unverified and R-027 said no native loader existed; BUILD_PROVENANCE said three CTest targets; ISO_INSPECTOR said the hardened inspector was not merged; and the game records did not label the pre-`SUBU` census (`R-029`).
- Test-first evidence: on the unchanged documents, `python -m unittest tests.test_doc_freshness -v` reported `Ran 3 tests`, `FAILED (errors=1)` with `FileNotFoundError` for `docs/README.md`. After the map was created, the map test exposed a defect in its own path pattern that made root `README.md` and `AGENTS.md` unmatchable (`['AGENTS.md', 'README.md']` reported missing); the pattern was corrected and the suite reported `Ran 3 tests`, `OK`.
- Controls added: [README.md](README.md) maps every document; `AGENTS.md` makes documentation review and update mandatory before merge; `tests/test_doc_freshness.py` fails when a document is unmapped or a mapped path is absent, when STATE's snapshot date differs from the newest date here, or when the STATE/HANDOFF PR pointer lags the latest merge recorded here or omits its hash; `R-030` records the drift risk.
- Documents updated in this increment: STATE, HANDOFF, ROADMAP, COMPATIBILITY, CLEAN_ROOM_AUDIT, PROVENANCE_PLAN, RISKS, REFERENCES, INCREMENT_LEDGER, EXECUTION_CONTEXT, BUILD_PROVENANCE, ISO_INSPECTOR, IR_CFG, BOOT_CENSUS, the game index and all eight game records, README and AGENTS. Historical records (ADRs, Gate dispositions, dated game sections and earlier log entries) were preserved rather than rewritten; superseded facts were corrected in current-status prose or labelled with their measurement date.
- Local verification: `python -m unittest tests.test_doc_freshness tests.test_doc_budget tests.test_progress_consistency tests.test_license_headers tests.test_build_contract -v` reported `Ran 19 tests`, `OK`; `python -m unittest discover -s tests -v` reported `Ran 355 tests`, `OK (skipped=43)`; `tools/check_forbidden_artifacts.py --root .` and `python -m compileall -q tools tests` passed. In this plain shell, `python tools/rptp_doctor.py` reported PASS for Python `3.11.9`, project layout, CMake, git and the artifact guard, but FAIL for MSVC `cl.exe` and Ninja not being on `PATH`; no Visual Studio developer environment was opened, so CMake/CTest and the MSVC wrapper were not rerun for this documentation-only change. Both CI jobs run them.
- Merge reference for the log pointer: PR #28 merged as `f967448`; main run `40856000777` and pages run `40855999485` succeeded. This audit's own PR number and merge are not yet recorded; a follow-up evidence update records them.
- Limitation: the freshness controls detect stale pointers, dates and unmapped documents, not factual correctness. A green suite does not verify claims, and no Gate, provenance, runtime or compatibility status changed.

## 2026-10-29 — documentation-freshness controls (PR #29)

- Scope: `D:/RPTP-worktrees/docfresh`, branch `automation/docfresh`, based on `f967448`. Documentation and tooling only; no decoder, lowering, runtime, build, fixture or dependency change.
- Behavior: `docs/README.md` maps every document; `AGENTS.md` makes documentation review mandatory before merge; `tests/test_doc_freshness.py` fails when a document is unmapped or a mapped path is absent, when `docs/STATE.md`'s snapshot date differs from the newest date here, or when the STATE/HANDOFF PR pointer lags the latest merge recorded here or omits its hash. `R-030` records the drift risk.
- Test-first evidence: `python -m unittest tests.test_doc_freshness -v` on the unchanged tree reported `Ran 3 tests`, `FAILED (errors=1)` (`FileNotFoundError: docs/README.md`). After the map was added, the map test reported the root documents missing because its own path pattern could not match `README.md`/`AGENTS.md`; the pattern was corrected and the suite reported `Ran 3 tests`, `OK`.
- Local verification on `fb4b765`: focused `tests.test_doc_freshness`, `tests.test_doc_budget`, `tests.test_progress_consistency`, `tests.test_license_headers` and `tests.test_build_contract` reported `Ran 19 tests`, `OK`; full `python -m unittest discover -s tests -v` reported `Ran 355 tests`, `OK (skipped=43)`; artifact guard and compileall passed. A plain-shell doctor reported PASS for Python, project layout, CMake, git and the artifact guard but FAIL for MSVC `cl.exe` and Ninja on `PATH`; CMake/CTest and the MSVC wrapper were not rerun locally for this documentation-only change, and both CI jobs run them.
- Exact-head CI: `fb4b765` passed in push run `40857531896` and pull-request run `40857557005`; `Windows x64 / MSVC` and `Linux / GCC` succeeded in both.
- PR #29 merged with `--match-head-commit fb4b765` at 2026-10-29T10:27:49Z as `0d54d1c`; main run `40857762590` and pages run `40857761252` succeeded. This entry makes PR #29 the latest merge recorded here; STATE/HANDOFF now point at `0d54d1c`, and the next increment must update them in the same change or the freshness test fails.
- Limitation: these controls detect stale dates, pointers and unmapped files, not incorrect facts. Historical records remain preserved; no Gate, provenance, runtime or compatibility status changed.

## 2026-10-29 — post-`SUBU` one-image census refresh

- Isolated worktree `D:/RPTP-worktrees/census-post-subu`, branch `automation/census-post-subu`, based on freshly fetched `origin/main` `4c0df867663bf8610acdc2ebc2a9283a6701ae79`. The pre-existing `D:\RPTP-Project` development checkout and other worktrees were not modified.
- Scope: read-only evidence only. No decoder, IR, lowering, runtime, build, fixture, dependency or Gate disposition changed.
- Input: the same owner-authorized `D:\Game\Downhill Domination (USA).iso`, 2,530,869,248 bytes, whole-image SHA-256 `0fe2b77713d3440cc3030741ea0b18f49e3feaa09671a30a421e0d4888a7eb86`; boot `SCUS_971.77;1`, 1,691,684 bytes, SHA-256 `adfda7b73a8f05fb20a3f0f318772e9d3797fd4d6c0a6c0078ae392df0f0cf0c`. Measurement started 2026-10-29T10:54:49Z; the report completed at 10:54:56Z and a rerun at 10:55:34Z.
- Command: `python tools/rptp_census.py "<iso>" --iso --json` with the decoder at revision `4c0df86` that includes `SUBU` (`SPECIAL` funct `0x23`). Exit code 0, status `CENSUSED`, 1 `PT_LOAD`, 413,500 aligned words, 260,641 accepted (63.03%), 152,859 raw-unsupported, 29,124 zero words, 87,421 unique words, 0 trailing bytes, no warnings. The pre-`SUBU` count was 259,646 (62.8%), so 995 additional words are now decoder-accepted, matching the `SUBU` encoding count.
- Non-mutation: whole-image SHA-256, file size and mtime were identical before and after both runs (`diff` empty); the two JSON reports were byte-identical (`cmp` clean, report SHA-256 `f379549caa0dda045721466889611ed9a236d06f07f83dc683243f2331b953b4`); no file was extracted, written or executed. `python -m unittest tests.test_boot_census -v` reported `Ran 6 tests`, `OK` before and after the measurement.
- Sample limit: only this one of the eight owner-authorized images is present on the current machine. The other seven rows in [BOOT_CENSUS.md](BOOT_CENSUS.md) were not remeasured and remain labelled pre-`SUBU`; no value was estimated or interpolated. Raw JSON reports are local artifacts under `build/census/` and are not committed.
- Documentation updated: `BOOT_CENSUS.md` (new dated post-`SUBU` section with hashes, revision, timestamp, result and limits), `STATE.md`, `HANDOFF.md`, `EXECUTION_CONTEXT.md`, `RISKS.md` (`R-029`), `docs/games/downhill-domination/STATUS.md`, `docs/games/README.md` and `docs/README.md`. No Gate, provenance, dependency or compatibility claim changed; no retail code was executed.

## 2026-10-29 — census evidence merge record (PR #30 and PR #31)

- Scope: documentation-only evidence update. No decoder, IR, lowering, runtime, build, fixture or dependency change; no Gate, provenance or compatibility status changed.
- PR #30 merged as `4c0df867663bf8610acdc2ebc2a9283a6701ae79`; it is the revision the post-`SUBU` census measured. Its exact-head runs are not restated because they were not observed in this session; only the merge SHA is claimed.
- PR #31 merged with `--match-head-commit 1d5118a` at 2026-10-29T11:00:39Z as `330dfb4175cd7edceec49c1a26857f583aa2d557`. Head `1d5118ae64ab6c026ea0ea5945daa4a42672aca6` (`docs: record post-SUBU census refresh`) passed push run `40861735385` and pull-request run `40861760536`; `Windows x64 / MSVC` and `Linux / GCC` succeeded in both.
- Main run `40862024274` (`RPTP CI`) completed with `Windows x64 / MSVC` and `Linux / GCC` success; pages run `40862023752` succeeded.
- This entry makes PR #31 the latest merge recorded here; STATE and HANDOFF now cite `330dfb4` and the PR range through #31.
- Limitation: the merge run verifies the tree at `330dfb4`, not later commits. The census figures remain the measured pre-`LD`/`SD` numbers dated in the entry above; nothing was re-estimated.

## 2026-10-30 — current-status synchronization through PRs #32–#38

- Scope and worktree: `D:/rptp-wt/integration`, branch `automation/status-sync-pr38`, based on freshly fetched `origin/main` `0944c84e8ed11c2d7db5d54ad23671b9a8de869d`. Documentation and status evidence only: no decoder, IR, lowering, runtime, ISO inspector, build, fixture or dependency change; no Gate, provenance, dependency or compatibility disposition changed.
- Trigger: a read-only audit found that STATE, HANDOFF, ROADMAP, CLEAN_ROOM_AUDIT, INCREMENT_LEDGER and RISKS stopped at PR #31/`330dfb4` while PRs #32–#38 had merged, and CLEAN_ROOM_AUDIT still described the branch-likely increment as local and not CI-recorded.
- Merged increments recorded (PR metadata from the GitHub API; merge SHAs are in `origin/main` history):
  - PR #32 `docs: record census PR #31 merge evidence`, merged 2026-10-29T11:16:14Z as `74bc75883a63ac9139ee312f5e11465e13731c06` (head `93368d8`). Documentation only.
  - PR #33 `feat(ir): implement LD/SD aligned doubleword transfers`, merged 2026-10-29T11:46:36Z as `36572b8beab2c86c367eddd491250addba70df28` (head `289d169`); commits `37ce137` (LD/SD), `d35aa78` (SD write-fault handling) and `289d169` (test boundaries).
  - PR #34 `fix(tools): harden ISO inspector validation and record independent review`, merged 2026-10-29T11:50:31Z as `49cbbe50093c2caec31ce989623237bcb3466b37` (head `d979e7d`); commits `e6e8357` and `d979e7d`, including the review record in [ISO_INSPECTOR_REVIEW.md](ISO_INSPECTOR_REVIEW.md). Gate 2 remains not passed.
  - PR #35 `feat(recompiler): R5900 analysis pipeline with dual-model differential tests`, merged 2026-10-29T13:29:24Z as `93bbc9c1bf9a17822214a3e0ab90be1552c1eb1f` (head `3834556`); feature commit `5ddd1bb`.
  - PR #36 `fix(tools): accept positive ISO directory data lengths`, merged 2026-10-29T19:55:15Z as `9029fd9363f79df92ab34180c4a261f2f74c7794` (head `25525fb`).
  - PR #38 `feat(rptp): nullify likely-branch delay slots`, merged 2026-10-29T20:02:28Z as `fcae0996fc65b88e52284ee8dfeafbe1237bc1e6` (head `9e1dc08`); feature commit `b7416b7`.
  - PR #37 `docs: record honest evidence levels for the R5900 ISA catalog`, merged 2026-10-29T20:07:04Z as `0944c84e8ed11c2d7db5d54ad23671b9a8de869d` (head `3903ef6`); commits `36ba148` and `3903ef6`.
- CI observed in this session for those revisions: `0944c84` RPTP CI run `40946144443` and pages run `40946142068` succeeded; `3903ef6` push/pull-request runs `40945781892`/`40945775796`, `fcae099` run `40945454160`, `9029fd9` run `40944390342`, `36ba148` push/pull-request runs `40944334960`/`40944310399` and `93bbc9c` run `40882418852` succeeded. Exact-head runs for PRs #32–#34 were not re-observed in this session; only their merge SHAs are recorded.
- Documentation updated: STATE, HANDOFF, ROADMAP, CLEAN_ROOM_AUDIT, INCREMENT_LEDGER and RISKS were advanced to the PR #32–#38 evidence; historical and dated records were preserved rather than rewritten. `R-031` records the path-divergence risk between the Gate 0 spike, `tools/rptp`, the older `rptp_ir`/`rptp_lower` pipeline and the C++ harness.
- Local verification (this session, not CI): `python -m unittest tests.test_doc_freshness tests.test_doc_budget tests.test_progress_consistency tests.test_license_headers tests.test_build_contract tests.test_catalog_provenance` reported `Ran 24 tests` and `OK`; `python -m unittest discover -s tests` reported `Ran 477 tests` and `OK (skipped=52, expected failures=1)`; `python tools/check_forbidden_artifacts.py --root .` printed `Artifact guard passed: only manifest-registered synthetic binary fixtures are permitted.`; `python -m compileall -q tools tests` exited 0. `python tools/rptp_progress.py` regenerated `docs/progress.html` and the three SVGs for snapshot `2026-10-30`, and the README query strings now carry `fe0daceb7299` (foundation badge), `9b12a9028ce1` (runtime badge) and `cc56ff3003a8` (progress map). No hosted Windows/MSVC or Linux/GCC job had run for this branch when this line was written.
- Limitation: status synchronization only. A green suite does not verify semantic claims. The branch-likely model applies to the `tools/rptp` path and is not implemented in the C++ harness; the harness also does not check `LW`/`SW` alignment while the oracle rejects it. The census remains post-`SUBU` for one image and pre-`SUBU` for seven, and no row matches the head decoder. No Gate disposition, provenance status, dependency or compatibility claim changed.

## 2026-10-30 — status-sync merge record (PR #39)

- Scope: documentation-only merge evidence. No code, runtime, build, fixture or dependency change; no Gate, provenance or compatibility status changed.
- PR #39 `docs: synchronize current status through PR #38` merged 2026-10-30T03:31:56Z with `--match-head-commit b84b21fb6415103b2ab85207d960ed01d1715b89` as `b5858d955871f787f347c47e035a9f6a06fb8c67`. Exact-head runs `40949584690` and `40949554670` (`RPTP CI`) succeeded on `b84b21f`, covering the Windows x64/MSVC and Linux/GCC jobs.
- Main run `40949915999` (`RPTP CI`) and pages run `40949912612` succeeded on the merge commit `b5858d9`.
- This entry makes PR #39 the latest merge recorded here; STATE and HANDOFF now cite `b5858d9` and the PR range through #39.
- Limitation: the merge run verifies the tree at `b5858d9`, not later commits. The audit findings for the separate synthetic paths, the stale census rows and the `LW`/`SW` alignment divergence remain open; this merge only synchronizes the documents that describe them.

## 2026-10-30 — current-decoder eight-image census refresh

- Scope: read-only evidence plus a small census-tool change on branch `automation/census-refresh-pr`, originally measured on `origin/main` `0944c84` and rebased onto `origin/main` `0fd6186` (function discovery, PR #42). `tools/rptp/isa.py` is byte-identical between `0944c84` and `0fd6186`, so the decoder identity and figures below apply unchanged to the rebased tree. `tools/rptp_census.py` now uses the current `tools/rptp/isa.py` decoder instead of the legacy `rptp_ir.py`/`rptp_gate0_spike.py` path, so branch-likely forms and `LD`/`SD` are included in decoder acceptance. Every JSON report gains a deterministic `decoder` object: module path, supported-mnemonic count and the SHA-256 of the newline-joined sorted supported-mnemonic set. No timestamp or host path is added.
- Input sample: all eight owner-authorized images were present. Whole-image SHA-256, file size and mtime were measured before and after; every value was unchanged. The identities and boot hashes are recorded in [BOOT_CENSUS.md](BOOT_CENSUS.md); no game data was extracted or committed.
- Command: `python tools/rptp_census.py "<image>" --iso --json` run from the image directory so JSON records only a relative file name. All eight exited 0. Decoder identity: 142 supported mnemonics, set SHA-256 `ddc255931fb49ecb0c8bc778037344e2e05ac32d8898fd77586db3162c904e13`. Acceptance: Black 645,758/801,120 (80.61%); Bully 1,030,256/1,282,560 (80.33%, overlap warning); Downhill Domination 338,288/413,500 (81.81%); God of War II 423,583/520,042 (81.45%); both San Andreas samples 1,093,442/1,420,864 (76.96%, overlap warning); Need for Speed - Most Wanted 1,056,658/1,224,439 (86.30%); Resident Evil 4 588,952/731,082 (80.56%). These supersede the pre-`SUBU` 58.3%–69.2% table and the one-image 63.03% row; they are decoder acceptance, not runtime results.
- Determinism: Downhill Domination (USA) was censused three times and the JSON was byte-identical each time, including the decoder identity. No file was extracted, written or executed.
- Local tests: `python -m unittest tests.test_boot_census -v` reported `Ran 7 tests`, `OK`; `python tools/check_forbidden_artifacts.py --root .` reported the artifact guard passed; `python -m compileall -q tools tests` passed; `python -m unittest tests.test_boot_census tests.test_doc_freshness tests.test_doc_budget tests.test_license_headers -v` reported `Ran 15 tests`, `OK`; `python -m unittest discover -s tests` reported `Ran 498 tests`, `OK (skipped=57, expected failures=1)`.
- Documentation updated: `BOOT_CENSUS.md` (single current-decoder eight-image table with input hashes, mtimes, decoder identity and determinism evidence), `docs/README.md`, `EXECUTION_CONTEXT.md`, `RISKS.md` (`R-029` resolved), `docs/games/README.md` and all eight game records. `STATE.md` and `HANDOFF.md` are intentionally left for the integration step that records this branch's merge.
- Limitation: local runs are not CI. Counts include data and padding and are not function-level, runtime, boot or compatibility evidence; no Gate or provenance status changed.

## 2026-10-30 — merge record for PRs #40–#45

- Scope: documentation-only merge evidence for increments already present on `origin/main`. No code, runtime, build, fixture or dependency change; no Gate, provenance or compatibility status changed.
- Merged increments recorded (PR titles and merge/head SHAs confirmed in local `origin/main` history; the API query returned HTTP 401 in this shell, so no hosted metadata was re-fetched; merge times are commit timestamps):
  - PR #40 `docs: record status-sync PR #39 merge evidence`, merge commit `c3d42386cf76cfb9909fe9c9c5cfbf1df889f419` (head `2e9615e`), dated 2026-10-29T20:37:45Z. Documentation only.
  - PR #41 `feat(runtime): execute branch-likely instructions with nullified delay slots`, merged as `f1199158b9de867d58a0c10998d63000bb92cb71` (head `698a0da`), dated 2026-10-29T20:43:54Z; `RPTP-REF-015`; tests `tests/test_runtime_execution.py` and `runtime/tests/runtime_tests.cpp`.
  - PR #42 `feat(tools): add conservative direct-evidence function discovery`, merged as `0fd61861111564ad2f54e81b83ac35bd45bbe19a` (head `c687ff3`), dated 2026-10-29T20:45:45Z; tests `tests/test_function_discovery.py`; proves no function extents.
  - PR #43 `feat(runtime): enforce LW/SW alignment and add cross-path suite`, merged as `db2447163bb3cb125ce5721afa0af357273c2f41` (head `addac89`), dated 2026-10-29T20:50:00Z; tests `tests/test_runtime_execution.py`, `tests/test_cross_path_equivalence.py` and `runtime/tests/runtime_tests.cpp`.
  - PR #44 `feat(census): use the current decoder and refresh all eight images`, merged as `6a87b0658833551d1934551d8086908694ec5fb4` (head `e79d751`), dated 2026-10-29T20:52:35Z; tests `tests/test_boot_census.py`; the read-only measurements are recorded in [BOOT_CENSUS.md](BOOT_CENSUS.md).
  - PR #45 `docs: add synthetic generated-C++ performance baseline`, merged as `477e5bd18cd2cfe84ec7c98a5ddc370fd9d6b674` (head `e066fc1`), dated 2026-10-29T20:54:51Z; adds the research notes mapped in [docs/README.md](README.md).
- CI observed in this session for the merge commits: `c3d4238` run `40950738453` (pages `40950736391`), `f119915` run `40951638248` (pages `40951637699`), `0fd6186` run `40951915221` (pages `40951913937`), `db24471` run `40952522927` (pages `40952522180`), `6a87b06` run `40952892786` (pages `40952890100`) and `477e5bd` run `40953215166` (pages `40953213734`) succeeded, covering the Windows x64/MSVC and Linux/GCC jobs.
- This entry makes PR #45 the latest merge recorded here; STATE and HANDOFF now cite `477e5bd` and the PR range through #45.
- Limitation: merge runs verify the tree at each merge commit, not later commits. The remaining audit findings (canonical-path consolidation, the older pipelines, and the untested scopes) stay open; this record only synchronizes the documents that describe them. The documentation-sync increment that produced this entry is not itself merged yet and will be recorded in a follow-up evidence change.

## 2026-10-30 — merge record for PR #46

- Scope: documentation-only merge evidence. No code, runtime, build, fixture or dependency change; no Gate, provenance or compatibility status changed.
- PR #46 `docs: synchronize current status through PR #45` merged 2026-10-30T04:06:08+07:00 (2026-10-29T21:06:08Z) with `--match-head-commit 0af3660b36b8937ee761335b1f2405591f459c9b` as `3ee9ca255f62737115e3a7a6afde64b678ad9cda`. Exact-head runs `40954536932` (pull request) and `40954491552` (push) (`RPTP CI`) succeeded on `0af3660`, covering the Windows x64/MSVC and Linux/GCC jobs.
- Main run `40954856937` (`RPTP CI`) and pages run `40954856044` succeeded on the merge commit `3ee9ca2`.
- This entry makes PR #46 the latest merge recorded here; STATE and HANDOFF now cite `3ee9ca2` and the PR range through #46. The follow-up promised by the previous entry is therefore complete.
- Limitation: the merge run verifies the tree at `3ee9ca2`, not later commits. This increment only aligns the documents that point at PRs #40–#45; the separate synthetic paths, the older pipelines, the stale-row history in [BOOT_CENSUS.md](BOOT_CENSUS.md) and the remaining semantic-evidence gap stay open.

## 2026-10-30 — merge record for PRs #47–#49

- Scope: documentation-only merge evidence. No code, runtime, build, fixture or dependency change; no Gate, provenance or compatibility status changed.
- PR #47 `docs: record PR #46 merge evidence` merged 2026-10-30T04:13:27+07:00 (2026-10-29T21:13:27Z) pinned to head `6ad4bfef01fc27b29ecf4abc995b83ec4c73447d` as `00af3234a9b39ad06d343b7537f0a616a312e374`. Exact-head `RPTP CI` runs `40955545353` and `40955529450` succeeded on `6ad4bfe`; merge run `40955933002` (`RPTP CI`) and pages run `40955932381` succeeded on `00af323`.
- PR #48 `docs(research): align instruction matrix with runtime and census evidence` merged 2026-10-30T04:34:53+07:00 (2026-10-29T21:34:53Z) pinned to head `737b8315f1ebe9954721bbe01ae6bf45565ec003` as `257dc1ca1f9c447a457d21b9d5963091897ee153`. Exact-head `RPTP CI` runs `40958636134` and `40958613033` succeeded on `737b831`; merge run `40958996105` (`RPTP CI`) and pages run `40958995046` succeeded on `257dc1c`.
- PR #49 `docs(research): add read-only disc assets research plan` merged 2026-10-30T04:40:43+07:00 (2026-10-29T21:40:43Z) pinned to head `a0e8a00175132182cc6a240f23beb4a4396fb40d` as `be8269e6cee39ad320ec097bef1aa24fa608f029`. Exact-head `RPTP CI` runs `40958978027` and `40958971133` succeeded on `a0e8a00`; merge run `40959803393` (`RPTP CI`) and pages run `40959801865` succeeded on `be8269e`.
- Contents: PR #47 changed only [VERIFICATION_LOG.md](VERIFICATION_LOG.md) and the status pointers; PR #48 changed only [research/instruction-semantics-matrix.md](research/instruction-semantics-matrix.md); PR #49 added [research/disc-assets-plan.md](research/disc-assets-plan.md) and one mapping line in [docs/README.md](README.md). None touched code, runtime, build files, fixtures or dependencies.
- This entry makes PR #49 the latest merge recorded here; STATE and HANDOFF now cite `be8269e` and the PR range through #49. The follow-up promised by the previous entry is therefore complete.
- Limitation: the merge run verifies the tree at `be8269e`, not later commits. The separate synthetic paths, the older pipelines, the stale-row history in [BOOT_CENSUS.md](BOOT_CENSUS.md) and the remaining semantic-evidence gap stay open.

## 2026-10-30 — merge record for PR #50

- Scope: documentation-only merge evidence. No code, runtime, build, fixture or dependency change; no Gate, provenance or compatibility status changed.
- PR #50 `docs: synchronize current status through PR #49` merged 2026-10-30T04:48:04+07:00 (2026-10-29T21:48:04Z) as `a4b18bf3ec52464789d42332824afb986f6317b4`, head `7075048448cc18c76ada2e36620fd046b18b2b43`. Exact-head `RPTP CI` runs `40960386025` (pull request) and `40960369874` (push) succeeded on `7075048`; merge run `40960801533` (`RPTP CI`) and pages run `40960799512` succeeded on `a4b18bf`.
- This entry makes PR #50 the latest merge recorded here; STATE and HANDOFF now cite `a4b18bf` and the PR range through #50.
- Limitation: the merge run verifies the tree at `a4b18bf`, not later commits. PR #51 (the ordinary-branch increment) is open at this snapshot; its merge evidence will be recorded in a follow-up.

## 2026-10-30 — ordinary-branch increment local evidence (PR #51)

- Scope: synthetic runtime and analysis increment. Adds `BLEZ`, `BGTZ`, `BLTZ`, `BGEZ`, `BLTZAL` and `BGEZAL` to `runtime/src/execution.cpp`, `runtime/tests/runtime_tests.cpp`, `tests/test_runtime_execution.py` and `tests/test_cross_path_equivalence.py`; adds `tests/test_instruction_branch_plain.py`; promotes the six forms to Level B (`RPTP-REF-015`, pages 76, 77, 81, 83, 85 and 86) in the catalog, reference record, ISA evidence, runtime contract and semantics matrix. No product recompiler, kernel, boot or compatibility behavior; Gate 2 remains open and read-only and Gate 3 remains not passed.
- Branch `automation/827e7b9005d246449dc834d517d6f60d`, code commit `50dd4e74021ac8536cd416827ee72533fec419ea`, PR #51 (open at this snapshot; not counted as merged).
- Local commands and results (Windows x64/MSVC, 2026-10-30):
  - `python tools/rptp_doctor.py` → Overall status: PASS, with MSVC `cl.exe` 14.51.36231.
  - `python tools/check_forbidden_artifacts.py --root .` → passed.
  - `python -m compileall -q tools tests` → OK.
  - `cmake --preset windows-msvc`, `cmake --build --preset windows-msvc` → succeeded; `ctest --test-dir build/cmake-msvc --output-on-failure` → 7/7 tests passed (`artifact_guard`, `python_unit_tests`, `gate0_differential_spike`, `runtime_loader_tests`, `runtime_loader_cli`, `runtime_execution_cli`, `cross_path_equivalence`).
  - `python -m unittest discover -s tests -v` with `RPTP_LOAD_BINARY` and `RPTP_RUN_BINARY` set to the built tools → 516 tests, OK, 0 skipped, 1 expected failure.
  - `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-msvc.ps1` → artifact guard, Gate 0 spike and the full suite passed; 516 tests, OK, 0 skipped, 1 expected failure.
  - Focused modules: `tests.test_instruction_branch_plain` 10 tests OK; `tests.test_runtime_execution` 25 tests OK; `tests.test_cross_path_equivalence` 4 tests OK.
  - `git diff --check` → no whitespace errors; the only output was Git's LF/CRLF normalization warnings for generated assets.
- Limitations: local results are not hosted CI. The exact-head Windows x64/MSVC and Linux/GCC jobs and the merge-commit run are recorded only after PR #51 is pushed and merged. The increment is synthetic-only; no real ISO was needed, the local ISO corpus was not accessed, and no ISO, BIOS, game code or extracted asset was uploaded, committed or executed.

## 2026-10-30 — ordinary-branch review hardening (PR #51)

- Scope: review hardening for PR #51 only. Adds signed-low-64-bit condition cases (`0x00000000FFFFFFFF` positive and `0xFFFFFFFF00000001` negative) to `tests/test_instruction_branch_plain.py` and `tests/test_runtime_execution.py`, covering the Python oracle, generated C++ and the native `rptp-run` harness, and synchronizes stale PR pointers and test counts in `README.md`, [CLEAN_ROOM_AUDIT.md](CLEAN_ROOM_AUDIT.md), [COMPATIBILITY.md](COMPATIBILITY.md), [research/instruction-semantics-matrix.md](research/instruction-semantics-matrix.md) and [research/isa-evidence.md](research/isa-evidence.md). No runtime, decoder, oracle, emitter or build behavior changed; no Gate, provenance or compatibility status changed.
- Commit `854ae42a7b544fef0f0bed4dea197b3f93ddb6f0` on branch `automation/827e7b9005d246449dc834d517d6f60d`; PR #51 remains open at this snapshot.
- Local commands and results in the x64 MSVC environment (`VsDevCmd.bat -arch=x64 -host_arch=x64`, MSVC 14.51.36231, 2026-10-30):
  - `python tools/rptp_doctor.py` → Overall status: PASS.
  - `cmake --preset windows-msvc`, `cmake --build --preset windows-msvc` → succeeded; `ctest --test-dir build/cmake-msvc --output-on-failure` → 7/7 tests passed.
  - `python -m unittest discover -s tests` with `RPTP_LOAD_BINARY` and `RPTP_RUN_BINARY` set to the built tools → 519 tests, OK, 0 skipped, 1 expected failure.
  - Focused modules under the same environment: `tests.test_instruction_branch_plain` 12 tests, `tests.test_runtime_execution` 26 tests and `tests.test_cross_path_equivalence` 4 tests → 42 tests, OK, no skips.
  - `python -m unittest tests.test_doc_budget tests.test_doc_freshness tests.test_progress_consistency tests.test_license_headers tests.test_build_contract` → 19 tests, OK; `python tools/check_forbidden_artifacts.py --root .` passed; `git diff --check` reported no whitespace errors.
- These results supersede the earlier PR #51 entry counts (516 full-suite tests, 10 plain-branch tests, 25 runtime tests); that entry is kept unchanged because this log is append-only.
- Limitations: local results are not hosted CI. No real ISO was needed or accessed; no ISO, BIOS, game code or extracted asset was uploaded, committed or executed.

## 2026-10-30 — merge record for PR #51

- Scope: synthetic runtime and analysis increment. Adds `BLEZ`, `BGTZ`, `BLTZ`, `BGEZ`, `BLTZAL` and `BGEZAL` to the native harness and cross-path coverage, promotes the six forms to Level B, and hardens review with signed-high-bit differential cases; no product recompiler, kernel, boot or compatibility behavior. Gate 2 remains open and read-only; Gate 3 remains not passed.
- PR #51 `feat(runtime): execute the six ordinary branch forms` merged 2026-10-30T05:55:21+07:00 (2026-10-29T22:55:21Z) with `--match-head-commit 04c7406b9441143321d3af7508922842f634d87a` as `983da0fbed3a0684a8e59a25a338b7060356ad75`. Exact-head runs `40968891639` (pull request) and `40968885850` (push) succeeded on `04c7406`; merge run `40969465394` and pages run `40969464067` succeeded on `983da0f`.
- Contents: `50dd4e7` adds the six forms to `runtime/src/execution.cpp`, `runtime/tests/runtime_tests.cpp`, `tests/test_runtime_execution.py`, `tests/test_instruction_branch_plain.py` and `tests/test_cross_path_equivalence.py`, and updates the catalog, reference, ISA, runtime and matrix documents; `ae453e6` synchronizes the status documents; `854ae42` adds the signed-high-bit cases and fixes stale pointers and counts; `04c7406` records the hardening evidence.
- Independent review at head `04c7406` returned APPROVE with no blocking issues. Its non-blocking findings (taken delay-slot memory case stores zero, link-before-delay-slot ordering not directly exercised, `tools/rptp/ir.py:261` target-0 fallback, dead `oracle.py:350` guard) are recorded as `R-032` and were not fixed here.
- Post-merge follow-up: the review also surfaced stale current-status text; the follow-up corrects the Gate 0 fixture list in [COMPATIBILITY.md](COMPATIBILITY.md) and the decoder-label counts in [research/isa-evidence.md](research/isa-evidence.md). The corrected counts were re-computed from `tools/rptp/isa.py`: 143 `verification=MANUAL` specs, 137 of them matched to catalog mnemonics, and the 216 matched entries split 71 generic / 137 manual / 8 provisional. No code, runtime or build file changed.
- This entry makes PR #51 the latest merge recorded here; STATE and HANDOFF now cite `983da0f` and the PR range through #51.
- Limitation: the merge run verifies the tree at `983da0f`, not later commits. The canonical-product-path item `R-031` and the new review gaps `R-032` stay open; the legacy pipelines still reject the six ordinary forms.

## 2026-10-30 — merge record for PR #52

- Scope: documentation-only merge evidence. No code, runtime, build, fixture or dependency change; no Gate, provenance or compatibility status changed.
- PR #52 `docs: record PR #51 merge and synchronize status` merged 2026-10-30T06:14:47+07:00 (2026-10-29T23:14:47Z) with `--match-head-commit 9bd6268c2911a383b51e09a38d60c16022f16af7` as `ed934de301932bc1871985ebd344b4eca9cbbe92`. Exact-head `RPTP CI` runs `40971454507` (pull request) and `40971449743` (push) succeeded on `9bd6268`; merge run `40971796930` (`RPTP CI`) and pages run `40971795286` succeeded on `ed934de`.
- Contents: 13 Markdown documents only. The PR recorded the PR #51 merge evidence in this log, advanced the STATUS/HANDOFF/ROADMAP/EXECUTION_CONTEXT/COMPATIBILITY/BUILD_PROVENANCE/CLEAN_ROOM_AUDIT/IR_CFG/README pointers to PR #51, added the PR #50/#51 ledger rows, corrected the decoder-label counts in [research/isa-evidence.md](research/isa-evidence.md) and the Gate 0 fixture list in [COMPATIBILITY.md](COMPATIBILITY.md), and recorded the review-derived `R-032` gaps in [RISKS.md](RISKS.md).
- Independent read-only audit at head `9bd6268` returned APPROVE after the earlier REQUEST CHANGES was addressed (`docs/CLEAN_ROOM_AUDIT.md` and `docs/IR_CFG.md` still cited `a4b18bf` as the latest merge). Documentation freshness, budget, progress-consistency and game-record tests passed at that head.
- This entry makes PR #52 the latest merge recorded here; STATE and HANDOFF now cite `ed934de` and the PR range through #52. The follow-up promised by the previous entry is complete.
- Limitation: the merge run verifies the tree at `ed934de`, not later commits. `R-031` and `R-032` stay open; the next increment addresses `R-032` only after this documentation synchronization merges.

## 2026-10-30 — merge record for PR #53

- Scope: documentation-only merge evidence. No code, runtime, build, fixture or dependency change; no Gate, provenance or compatibility status changed.
- PR #53 `docs: record PR #52 merge and synchronize status` merged 2026-10-30T11:34:46+07:00 (2026-10-30T04:34:46Z) with `--match-head-commit 96cfd88d37c7d09ac0958ebe8c70175e07902d00` as `58788147876cb0408a11dcebfc652ee74c179731`. Exact-head `RPTP CI` runs `41003477712` (pull request) and `41003465898` (push) succeeded on `96cfd88`; merge run `41003680466` (`RPTP CI`) and pages run `41003679107` succeeded on `5878814`.
- Contents: 11 Markdown documents only. The PR recorded the PR #52 merge evidence in this log, advanced the STATE/HANDOFF/ROADMAP/EXECUTION_CONTEXT/COMPATIBILITY/BUILD_PROVENANCE/CLEAN_ROOM_AUDIT/IR_CFG/README pointers to PR #52 and added the PR #52 ledger row.
- This entry makes PR #53 the latest merge recorded here; STATE and HANDOFF now cite `5878814` and the PR range through #53.
- Limitation: the merge run verifies the tree at `5878814`, not later commits. `R-031` and `R-032` stay open; the next increment addresses `R-032`.

## 2026-10-30 — R-032 branch-hardening increment (pre-merge)

- Scope: closes the four `R-032` review gaps for the six ordinary branch forms in the `tools/rptp` host IR and oracle. No runtime, decoder, emitter, build or product behavior changed; no Gate, provenance or compatibility status changed.
- Changes: `tools/rptp/ir.py` now emits a decoded branch target of address 0 instead of substituting the fallthrough (`target is not None`); `tools/rptp/oracle.py` drops the always-true `and state.registers` guard; `tests/test_instruction_branch_plain.py` stores a nonzero value (`0x5A`) in the taken BLEZ delay slot, adds a BLTZAL/BGEZAL delay slot that reads `GPR[31]` after the link write on both outcomes, and asserts target-0 lowering directly; `tests/test_cross_path_equivalence.py` makes the taken BGEZAL delay slot read `$ra`, so the oracle, generated C++ and `rptp-run` must all write the link before the delay slot runs.
- Local commands and results in the x64 MSVC environment (MSVC 14.51.36231, 2026-10-30):
  - `python tools/rptp_doctor.py` → Overall status: PASS.
  - `cmake --preset windows-msvc` and `cmake --build --preset windows-msvc` → succeeded; standalone `ctest --test-dir build/cmake-msvc --output-on-failure` → 7/7 tests passed, including `runtime_execution_cli` and `cross_path_equivalence`.
  - `python -m unittest discover -s tests` with `RPTP_LOAD_BINARY` and `RPTP_RUN_BINARY` set to the built tools → 521 tests, OK, 0 skipped, 1 expected failure.
  - `python -m unittest tests.test_doc_budget tests.test_doc_freshness tests.test_progress_consistency tests.test_license_headers tests.test_build_contract` → 19 tests, OK; `python tools/check_forbidden_artifacts.py --root .` passed; `git diff --check` reported no whitespace errors.
- Limitations: local results are not hosted CI. No real ISO was needed or accessed; no ISO, BIOS, game code or extracted asset was uploaded, committed or executed. `R-031` (canonical product path) remains open; this increment does not declare one.

## 2026-10-30 — R-032 exact-head CI and independent review (pre-merge)

- Exact-head `RPTP CI` runs `41005061054` (push) and `41005075117` (pull request) succeeded on `5374828` for both Windows x64/MSVC and Linux/GCC. That head contains the `R-032` fixes and tests, the PR #53 merge record and the pointer synchronization.
- An independent read-only review at `5374828` returned APPROVE with no blocking issues. Its non-blocking notes were that [RISKS.md](RISKS.md) still cited pre-fix line numbers and that the pre-CI log wording was slightly strong; the resolution entry and this record address both.
- `R-032` is marked resolved in [RISKS.md](RISKS.md) only after these results; the exact-head tree already holds the behavior and tests, and the follow-up commit is documentation-only. `R-031` remains open.

## 2026-10-30 — merge record for PR #54

- Scope: synthetic host-IR, oracle and regression-test hardening for the six ordinary branch forms. Closes `R-032`; no runtime, decoder, emitter or build behavior changed, and no Gate, provenance or compatibility status changed.
- PR #54 `fix(rptp): harden zero-address branch lowering and delay-slot link order` merged 2026-10-30T11:58:58+07:00 (2026-10-30T04:58:58Z) with `--match-head-commit 3c4c6fee62e6aece2ea059f5498c52e36ee7885b` as `90e4f6226fefb2e2938dd11115b3107e2346f3dc`. Exact-head runs `41005061054` (push) and `41005075117` (pull request) succeeded on `5374828`; runs `41005626121` (push) and `41005630440` (pull request) succeeded on `3c4c6fe`; merge run `41005859751` (`RPTP CI`) and pages run `41005858879` succeeded on `90e4f62`.
- Contents: `7fe39d9` fixes the zero-address target fallback and the dead oracle guard, and adds the nonzero delay-slot store, link-visibility, target-0 and cross-path delay-slot `$ra` tests; `5374828` records the PR #53 merge, rolls the status pointers, adds the PR #53 ledger row, documents the target-0 rule and records the local evidence; `3c4c6fe` marks `R-032` resolved after the green exact-head CI and the independent read-only review.
- An independent read-only agent review at `5374828` returned APPROVE with no blocking issues; its non-blocking wording notes are addressed in `3c4c6fe`. It is a session-recorded delegated agent review, not a GitHub formal review. This entry makes PR #54 the latest merge recorded here; STATE and HANDOFF now cite `90e4f62` and the PR range through #54.
- Limitation: the merge run verifies the tree at `90e4f62`, not later commits. `R-031` (canonical product path) remains open; the increment does not declare one.

## 2026-10-30 — merge record for PR #56

- Scope: documentation-only post-merge synchronization for PR #54. No code, runtime, build, fixture or dependency change; no Gate, provenance or compatibility status changed.
- PR #56 `docs: record PR #54 merge and synchronize status` merged 2026-10-30T12:10:53+07:00 (2026-10-30T05:10:53Z) with `--match-head-commit 1039020e55bfd799332818de1162c6730dc77039` as `f8f75480f2588b83d4d9f667514515d2140b790a`. Exact-head `RPTP CI` runs `41006747520` (push) and `41006752009` (pull request) succeeded on `1039020`; merge run `41006977122` (`RPTP CI`) and pages run `41006976205` succeeded on `f8f7548`.
- Contents: 12 Markdown documents. The PR recorded the PR #54 merge evidence and exact-head runs in this log, added the PR #54 ledger row, advanced the STATE, HANDOFF, README, ROADMAP, COMPATIBILITY, EXECUTION_CONTEXT, BUILD_PROVENANCE, CLEAN_ROOM_AUDIT and IR_CFG pointers to PR #54, and qualified the `R-032` review provenance and final-head runs.
- The merging agent verified the cited run IDs and the documentation diff before the pinned merge; no independent reviewer was involved in this documentation-only merge. This entry makes PR #56 the latest merge recorded here; STATE and HANDOFF now cite `f8f7548` and the PR range through #56.
- Limitation: the merge run verifies the tree at `f8f7548`, not later commits. `R-031` remains open; `R-032` stays resolved.

## 2026-10-30 — canonical-path proposal and E1/E2 contract (pre-merge)

- Scope: proposes ADR-0005 (status Proposed; owner acceptance required) to declare `tools/rptp` plus the native runtime harness the canonical execution path, freeze the Gate 0 spike and `rptp_ir`/`rptp_lower`, and require E1–E4 before any legacy retirement. Adds `tests/test_path_contract.py` as executable E1/E2 evidence. No decoder, oracle, IR, emitter, runtime or build behavior changed; no path is declared canonical, and no Gate, provenance or compatibility status changed.
- References: `RPTP-REF-001`, `RPTP-REF-015`; policy ADR-0001 and ADR-0003; existing synthetic catalog and Gate 0 scope. The ADR records `R-031` and the four-path inventory.
- Tests: `tests/test_path_contract.py` pins the 28-operation legacy lowering set, its containment in `tools/rptp/isa.py`, the canonical-only 14 branch forms, and runs one synthetic program containing every legacy operation through both Python oracles with identical low-64 registers, halt PC and executed-PC trace. E3 (native legacy/canonical comparison) and E4 (fail-closed parity) stay open.
- Local commands and results in the x64 MSVC environment (Visual Studio 2026 18.11.1, MSVC 14.51.36231, 2026-10-30):
  - `python tools/rptp_doctor.py` → Overall status: PASS.
  - `cmake --preset windows-msvc` and `cmake --build --preset windows-msvc` → succeeded; the build preset ran CTest and 7/7 tests passed in 150.23 s, including `python_unit_tests`, `runtime_execution_cli` and `cross_path_equivalence`.
  - `python -m unittest discover -s tests` with `RPTP_LOAD_BINARY` and `RPTP_RUN_BINARY` set to the built tools → 527 tests, OK, 0 skipped, 1 expected failure (120.889 s).
  - `python -m unittest tests.test_path_contract` → 6 tests, OK; the documentation control suite (budget, freshness, path contract, license headers, build contract, progress consistency) → 25 tests, OK.
  - `python tools/check_forbidden_artifacts.py --root .` passed; `git diff --check` reported no whitespace errors.
- Limitations: local results are not hosted CI. No real ISO was needed or accessed; no ISO, BIOS, game code or extracted asset was uploaded, committed or executed. The ADR is Proposed; only the owner can accept it and close `R-031`. E3/E4 remain open.

## 2026-10-30 — merge record for PR #57

- Scope: documentation plus one Python contract test. PR #57 `docs(adr): propose ADR-0005 canonical execution path with E1/E2 contract` adds [ADR-0005](DECISIONS/ADR-0005-canonical-execution-path.md) (Status: Proposed; owner acceptance required), [tests/test_path_contract.py](../tests/test_path_contract.py), the PR #56 merge record, the PR #56 ledger row and the sync of every latest-merge pointer. No decoder, oracle, IR, emitter, runtime, build or dependency behavior changed; no Gate, provenance or compatibility status changed.
- PR #57 merged 2026-10-30T12:28:00+07:00 (2026-10-30T05:28:00Z) with `--match-head-commit 88143ad00b79c6a00ebe4647a4b0665adb0cca52` as `5326059b40c68ba5eb31586ddbd7b2c082df532b`. Exact-head `RPTP CI` runs `41008377188` (push) and `41008382350` (pull request) succeeded on `88143ad`; merge run `41008593520` (`RPTP CI`) and pages run `41008593428` succeeded on `5326059`.
- Review: an independent read-only agent review at `62a96cb` returned CHANGES REQUIRED for two stale `docs/research` statements that still called ADR-0005 a future/placeholder ADR, plus non-blocking E1 wording and `R-032` precision nits. Fix commit `88143ad` resolved them and a delta re-review returned APPROVE. These are session records, not GitHub formal reviews; the merging agent rechecked the cited runs and diff before the pinned merge.
- Contents: 20 unique files across two commits (18 in the first, plus two `docs/research` corrections in the fix commit). The contract test holds 6 tests: E1 pins the 28-operation legacy lowering set, its containment in `tools/rptp/isa.py` and the canonical-only 14 branch forms; E2 runs a 51-instruction synthetic program through both Python oracles and asserts identical low-64 registers, halt PC 0 and the same 49-step trace.
- This entry makes PR #57 the latest merge recorded here; STATE and HANDOFF now cite `5326059` and the PR range through #57. `R-031` remains open pending owner acceptance of ADR-0005; `R-032` stays resolved. E3/E4 remain open.

## 2026-10-31 — merge records for PR #59 and PR #60 (verified)

- Scope: PR #59 is documentation-only post-merge synchronization; PR #60 pins fail-closed legacy branch handling in a test. This entry adds no behavior and changes no Gate, provenance or compatibility status.
- PR #59 `docs: record PR #57 merge and mark ADR-0005 E1/E2 CI-verified` merged 2026-10-30T05:36:20Z as `7a2b98f81eb53331c8c54d57680a4b10c54739d7`. Push run `41011409128` (`RPTP CI`) completed successfully on that commit; an earlier push run `41009361036` on the same commit also succeeded, and pages run `41009360784` completed successfully.
- PR #60 `test: pin fail-closed legacy branch handling` merged 2026-10-30T06:11:35Z as `c1f1adebd779f90453955e772d362058133db6ff`. Push run `41012644771` (`RPTP CI`) and pages run `41012644318` completed successfully on that commit.
- Verification method: read-only `gh pr list`, `gh api repos/RidTheWann/RPTP-Project/commits/<sha>/check-runs` and `gh run list` against `github.com/RidTheWann/RPTP-Project` on 2026-10-31. The `check-runs` API reports `Windows x64 / MSVC` and `Linux / GCC` completed with conclusion `success` for both merge commits.
- This entry makes PR #60 the latest merge recorded here; STATE and HANDOFF cite `c1f1ade` and the PR range through #60. `R-031` remains open pending owner acceptance of ADR-0005; `R-032` stays resolved. E3/E4 remain open.

## 2026-10-31 — doubleword-shift family in the native harness (pre-merge)

- Scope: adds the nine MIPS64 doubleword shifts `DSLL` (`0x38`), `DSLL32` (`0x3C`), `DSLLV` (`0x14`), `DSRA` (`0x3B`), `DSRA32` (`0x3F`), `DSRAV` (`0x17`), `DSRL` (`0x3A`), `DSRL32` (`0x3E`) and `DSRLV` (`0x16`) to `runtime/src/execution.cpp` and its tests, promotes the canonical `tools/rptp` forms to Level B evidence, and extends the cross-path and path-contract suites. Immediate forms require `rs = 0` and shift by `sa` (`sa + 32` for the `32` variants); variable forms require `shamt = 0` and shift by `GPR[rs] & 63`; arithmetic right shifts replicate the sign bit; `$zero` writes are discarded. `SPECIAL` funct `0x15` remains unsupported. No kernel, syscall, ISO, extraction, boot or compatibility behavior changed; no Gate, provenance or compatibility status changed.
- References: `RPTP-REF-015` (MIPS64 Revision 5.04 pages 168–176) for encodings, shift amounts, the variable shift amount and sign replication. The 64-bit shift width, trace/step accounting, `$zero` suppression, reserved-field rejection and generated-source shape are RPTP test definitions, not hardware facts.
- Tests-first: the new `tests.test_runtime_execution.RuntimeExecutionCliTests.test_doubleword_shift_family_matches_the_python_oracle` was run against a pre-change `rptp-run` built from `c1f1ade` and failed with exit code 2 (`Ran 1 test`, `FAILED (failures=1)`, assertion `0 != 2`). The same test passes on the changed harness below.
- Local commands and results in the x64 MSVC environment (Visual Studio 2026 18.11.1, MSVC 14.51.36231, 2026-10-31):
  - `python tools/rptp_doctor.py` → Overall status: PASS.
  - `python tools/check_forbidden_artifacts.py --root .` → artifact guard passed.
  - `python -m compileall -q tools tests` → exit 0.
  - Full suite with `RPTP_LOAD_BINARY` and `RPTP_RUN_BINARY` set to the built tools → `Ran 541 tests in 62.201s`, `OK (expected failures=1)`, 0 skipped.
  - Focused `tests.test_instruction_dshift tests.test_runtime_execution tests.test_cross_path_equivalence tests.test_pipeline_path_contract` with the same binaries → `Ran 44 tests in 4.691s`, `OK`, 0 skipped (`tests.test_instruction_dshift` is 8 of them).
  - `cmake --preset windows-msvc` and `cmake --build --preset windows-msvc` → succeeded; the build preset ran CTest and 7/7 tests passed in 59.67 s.
  - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-msvc.ps1` → `Ran 541 tests in 55.047s`, `OK (skipped=37, expected failures=1)`; the 37 skips are the runtime-CLI cases because the wrapper does not set the binary paths. The Gate 0 spike completed.
  - `git diff --check` → exit 0; it reported only expected LF→CRLF normalization warnings for the regenerated progress assets.
- Limitations: local results are not hosted CI. No real ISO was accessed; no ISO, BIOS, game code or extracted asset was downloaded, committed or executed. The canonical decoder accepts a variable-form doubleword shift whose reserved `shamt` field is nonzero while the native harness rejects it with `EXEC_UNSUPPORTED_INSTRUCTION`; that E4 divergence remains open and is recorded in [RISKS.md](RISKS.md) (`R-031`), [REFERENCES.md](REFERENCES.md) and [IR_CFG.md](IR_CFG.md). E3/E4 remain open; no path is canonical and no Gate or compatibility status changed.

## 2026-10-31 — doubleword-shift review fixes (pre-merge)

- Scope: responds to the delegated read-only correctness review of `c1f1ade..9b21d8b`. The review found no semantic defect in the nine doubleword shifts; it returned fix-before-merge for two documentation coverage claims and noted low-severity test gaps. This entry changes no runtime, decoder, oracle, IR, emitter, build or dependency behavior, and no Gate, provenance or compatibility status.
- Findings addressed: `README.md` described the 21-instruction fixture as covering shift-amount boundaries and reserved-field rejection, but its reserved-field cases live in the native harness tests and it does not exercise amount 0 or 63; `docs/INSTRUCTION_CATALOG.md` attributed `$zero` suppression to `tests/test_instruction_dshift.py`, whose program has no doubleword shift targeting `$0`. Both statements now describe the fixture accurately. A new decode test, `tests.test_instruction_dshift.DoublewordShiftDecodeTests.test_canonical_decoder_accepts_a_nonzero_reserved_shamt`, pins the documented canonical-side acceptance of a nonzero reserved `shamt` and asserts the field is retained, so the open E4 divergence cannot change silently.
- Review notes not addressed here: the native `$zero` check is tautological because the harness resets register zero after every step; no amount-0/63 boundary cases were added; the pre-existing `write_bytes` test helper has no bounds check. These are non-blocking and remain recommendations, not claims.
- Exact-head hosted evidence before this fix: `RPTP CI` runs `41122478679` (push) and `41122486890` (pull request) completed successfully on `9b21d8b` for both `Windows x64 / MSVC` and `Linux / GCC`, verified with `gh run view` against `github.com/RidTheWann/RPTP-Project`.
- Local commands and results in the x64 MSVC environment (Visual Studio 2026 18.11.1, MSVC 14.51.36231, 2026-10-31):
  - Focused `tests.test_instruction_dshift tests.test_runtime_execution tests.test_cross_path_equivalence tests.test_pipeline_path_contract` with the built binaries → `Ran 45 tests in 4.749s`, `OK`, 0 skipped.
  - Full suite with `RPTP_LOAD_BINARY` and `RPTP_RUN_BINARY` set → `Ran 542 tests in 56.325s`, `OK (expected failures=1)`, 0 skipped.
  - `ctest --test-dir build/cmake-msvc --output-on-failure` → 7/7 tests passed in 60.00 s.
  - Documentation controls (budget, freshness, progress consistency, catalog provenance, license headers) → 18 tests, `OK`; `python -m compileall -q tools tests` → exit 0; `git diff --check` → exit 0 with only an LF→CRLF notice.
- Limitations: local results are not hosted CI; the review fixes require a new exact-head run. No ISO was accessed and no game content was used. E4 and `R-031` remain open.

## 2026-10-31 — merge record for PR #62

- Scope: records the merge of PR #62 "feat(runtime): execute the nine R5900 doubleword shift forms" and the post-merge hosted runs. No source, test, build or dependency behavior changed with this entry; no Gate, provenance or compatibility status changed.
- Exact-head evidence: the newest push and pull-request `RPTP CI` runs for head `f3c84ea6bf922a597d3069b6f52e33e553c29c8d` (`41123553676` and `41123562073`) completed successfully for both `Windows x64 / MSVC` and `Linux / GCC`.
- Merge: the merge command pinned `--match-head-commit f3c84ea6bf922a597d3069b6f52e33e553c29c8d`; the PR API state reached `MERGED` with merge commit `cc85c1a7673f110584f6ad029002fb6e85c36df6`, recorded at 2026-10-30T20:31:32Z (2026-10-31T03:31:32+07:00).
- Post-merge: merge-commit `RPTP CI` run `41123907950` and Pages run `41123907198` completed successfully on `cc85c1a`; the workflow guard reported `MERGE_CI_GREEN`.
- Review: a delegated read-only correctness review of `c1f1ade..9b21d8b` returned fix-before-merge for two documentation coverage claims; `9b21d8b` and `f3c84ea` addressed them, and the delta review approved. The review is a session record, not a GitHub formal review.
- Pointers: STATE, HANDOFF, README, ROADMAP, BUILD_PROVENANCE, EXECUTION_CONTEXT and COMPATIBILITY now cite `cc85c1a` (PR #62, run `41123907950`) as the latest merge, with `c1f1ade` (PR #60, run `41012644771`) and `7a2b98f` (PR #59, run `41011409128`) immediately before it. The research baselines move to `cc85c1a`.
- Limitations: the hosted evidence covers only the commits named above; it is not a compatibility, boot, Gate or clean-room result. E3/E4 remain open, `R-031` remains open pending owner acceptance of ADR-0005, and the canonical decoder still accepts a nonzero reserved `shamt` on the variable doubleword shifts while the native harness rejects it. No ISO, BIOS or game content was accessed.

## 2026-10-31 — merge record for PR #63

- Scope: records the merge of PR #63 "docs: record the PR #62 merge and synchronize status" and the post-merge hosted runs. Documentation only; no source, test, build or dependency behavior changed with this entry, and no Gate, provenance or compatibility status changed.
- Merge: the PR API reported `merged: true` at 2026-10-30T20:40:44Z (2026-10-31T03:40:44+07:00) with merge commit `248aad8dd9a773b900664661139b8f775f77ce6a`.
- Post-merge: merge-commit `RPTP CI` run `41125085510` and Pages run `41125085108` completed successfully on `248aad8`; both were read from the GitHub REST API on 2026-10-31. The `RPTP CI` job list reports `Windows x64 / MSVC` and `Linux / GCC` with conclusion `success`.
- Pointers: STATE, HANDOFF, README, ROADMAP, BUILD_PROVENANCE, EXECUTION_CONTEXT and COMPATIBILITY now cite `248aad8` (PR #63, run `41125085510`) as the latest merge, with `cc85c1a` (PR #62, run `41123907950`) and `c1f1ade` (PR #60, run `41012644771`) immediately before it.
- Limitations: the hosted evidence covers only the named commits; it is not a compatibility, boot, Gate or clean-room result. E3/E4 remain open and `R-031` remains open pending owner acceptance of ADR-0005. No ISO, BIOS or game content was accessed.

## 2026-10-31 — E3 native equivalence local evidence (pre-merge)

- Scope: local evidence for the E3 increment on PR #61 (branch `automation/e3-native-legacy-equivalence`). The increment executes one shared 28-operation synthetic program (49 steps) through the legacy generated C++, the canonical oracle, the canonical generated C++ and the native `rptp-run` harness, normalizing only the documented representations (memory layout, halt-reason vocabulary, `$ra` sentinel) and skipping a leg with an explicit reason when its prerequisites are absent. No decoder, oracle, emitter, runtime or build behavior changed with this entry; no Gate, provenance or compatibility status changed. The commands below were run on the final branch content before this record was committed; the hosted exact-head and merge-commit runs are appended by the follow-up documentation increment.
- Test change in this entry: `tests/test_native_legacy_equivalence.py` runs the divergence-mutation assertions unconditionally against the oracle baseline and in a separate test against the legacy baseline, which skips with an explicit reason (never passes silently) when MSVC is unavailable; it also mutates the halt reason, so the comparator cannot silently accept a wrong halt reason or a legacy-only drift.
- Local commands and results in the x64 MSVC environment (Visual Studio 2026 Developer PowerShell 18.11.1, MSVC 14.51.36231, 2026-10-31):
  - `cmake --build --preset windows-msvc` (`rptp-ci`) → doctor `PASS`, artifact guard passed, CTest 8/8 passed in 68.11 s, including `python_unit_tests` 59.89 s, `native_legacy_equivalence` 4.00 s and `cross_path_equivalence` 2.17 s.
  - Full suite inside the MSVC environment with `RPTP_LOAD_BINARY` and `RPTP_RUN_BINARY` set → `Ran 550 tests in 59.724s`, `OK (expected failures=1)`, 0 skipped.
  - Full suite in a plain shell with the same binaries → `Ran 550 tests in 38.885s`, `OK (skipped=29, expected failures=1)`; every skip is "No C++ compiler available", so no equivalence leg was skipped.
  - `scripts/run-msvc.ps1` inside the MSVC environment → `Ran 550 tests in 58.594s`, `OK (skipped=39, expected failures=1)`; the 39 skips are the runtime-CLI legs because the wrapper does not set `RPTP_LOAD_BINARY`/`RPTP_RUN_BINARY`; the MSVC Gate 0 spike completed.
  - Focused `python -m unittest tests.test_native_legacy_equivalence -v` → `Ran 8 tests in 4.327s`, `OK`, including the legacy-baseline mutation test compiled by MSVC.
  - `python -m compileall -q tools tests` → exit 0; `python tools/check_forbidden_artifacts.py --root .` → passed; `git diff --check` → exit 0 with only LF→CRLF notices.
- Limitations: local results are not hosted CI; exact-head hosted jobs are required before merge. E3 coverage is limited to the shared synthetic subset; no function extent, runtime reachability, product runtime or compatibility claim follows. E4 remains open, including the reserved-`shamt` divergence, and `R-031` remains open pending owner acceptance of ADR-0005. No ISO, BIOS or game content was accessed.
