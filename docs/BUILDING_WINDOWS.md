# Windows verification for Gate 0

1. Extract/copy this local bundle to a writable folder. Do not copy its `build/` directory into the public repository.
2. Install Python 3 and Visual Studio Build Tools with the C++ workload and Windows SDK.
3. Open **Developer PowerShell for Visual Studio** or an x64 Native Tools command prompt so `cl.exe` and its C++ standard library are available.
4. Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run-msvc.ps1
```

5. Preserve the full terminal output and `build/gate0-msvc/report.json`. Check that the report says `PASS_LOCAL_DIFFERENTIAL_SPIKE`, `native_matches_oracle: true`, and compiler command points to `cl.exe`.
6. Only after the result is reproduced should `docs/STATE.md` be updated to record MSVC evidence and ask the human owner for Gate Review.

Do not set `windows_msvc_verified` manually. It is currently emitted as `false` by design; that field must only change in the implementation when the run actually occurred with MSVC on Windows and the result was validated.
