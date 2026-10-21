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
