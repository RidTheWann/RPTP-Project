# Windows x64 build and verification

## Requirements

- Windows 10/11 x64.
- Visual Studio 2022 or newer / Visual Studio Build Tools with the C++ workload and Windows SDK.
- Python 3.10 or newer.
- CMake 3.25 or newer and Ninja.
- A writable checkout of this repository.

## Configure and run the full current checks

Open Developer PowerShell for Visual Studio or an x64 Native Tools prompt so cl.exe and its standard library are available.

    cmake --preset windows-msvc
    cmake --build --preset windows-msvc

The rptp-ci target first runs rptp doctor, then runs CTest for the artifact guard, Python unit tests and the Gate 0 generated-native differential test. Results and generated binaries are written below the ignored build/ directory.

To inspect the toolchain/environment without running all tests:

    python tools\rptp_doctor.py
    python tools\rptp_doctor.py --json

## Focused MSVC runner

The explicit runner is also available:

    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-msvc.ps1

It checks the artifact guard, compiles and executes the generated C++ with MSVC, and runs the Python tests. Preserve the complete output and inspect build/gate0-msvc/report.json.

## Evidence and limitations

Check for PASS_LOCAL_DIFFERENTIAL_SPIKE, native_matches_oracle: true, and windows_msvc_verified: true in the local report. The ignored build copy is a local artifact. A sanitized copy of the current Windows/MSVC report and its command record is checked in under `evidence/windows-msvc/`; `evidence/host-gcc/` holds the previously recorded GCC/Clang evidence.

This spike uses one original synthetic ELF32/EM_MIPS fixture and a deliberately limited instruction subset. It does not prove full R5900 behavior, retail ISO support, PS2 runtime services, or compatibility with any commercial game. Formal Gate 0 acceptance remains subject to human review, including the recorded clean-room exposure question.
