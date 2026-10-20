# RPTP — Gate 0 Local Spike

**Scope:** Gate 0 feasibility evidence only. This folder is a local working bundle and has not been pushed to `RidTheWann/RPTP-Project`.

RPTP is intended to be a native Windows x64 static recompilation project: user-supplied PS2 ISO → inspection → ELF analysis → Emotion Engine recompilation to C++ → native Windows build plus a native runtime. This Gate 0 spike validates only a small, synthetic ELF32/EM_MIPS instruction subset. It is not a PS2 game loader, not a full R5900 recompiler, and not evidence that any commercial game works.

## What this spike demonstrates

- Creates a synthetic little-endian ELF32 `ET_EXEC`/`EM_MIPS` fixture from original instruction encoders in `tools/rptp_gate0_spike.py`.
- Parses the ELF header and one executable `PT_LOAD` segment with basic bounds checks.
- Decodes a deliberately limited common-MIPS subset: `ADDIU`, `ADDU`, `LW`, `SW`, `BEQ`, `BNE`, `J`, `JAL`, `JR`, and `NOP`.
- Executes the program in a reference interpreter used only as a test oracle.
- Emits deterministic C++ with static instruction cases; control transfer and delay-slot execution are represented in the generated native program.
- Compiles and runs the generated program, then compares its full register array, memory writes, final PC/halt state, and executed-PC trace against the oracle.
- Verifies that binary fixtures are covered by `tests/fixtures/MANIFEST`; ISO files are never allowlisted.

The subset's arithmetic behavior is not a statement of complete R5900 semantics. In particular, MMI, COP0/COP1/COP2 details, exceptions, interrupts, memory translation, timing, and the PS2 kernel are outside this proof.

## Run locally with a host C++ compiler

Requires Python 3.10+ and a C++20 compiler. The current evidence was produced with Python 3.13.5 and GCC 14.2.0 on Linux x86-64. A second Linux host build with Clang 17.0.0 also passed; neither host build proves MSVC compatibility.

```bash
python3 -m unittest discover -s tests -v
python3 tools/check_forbidden_artifacts.py --root .
python3 tools/rptp_gate0_spike.py --out build/gate0 --compiler g++
```

The generated report and comparison artifacts are written under `build/gate0/`. Build output is deliberately excluded from the source repository by `.gitignore` and the artifact scanner.

## Verify with MSVC on Windows

Use **Developer PowerShell for Visual Studio** or an x64 Native Tools command prompt with MSVC, CMake-independent C++ standard-library headers, and Python available on `PATH`:

```powershell
python tools\check_forbidden_artifacts.py --root .
python tools\rptp_gate0_spike.py --out build\gate0-msvc --compiler cl
python -m unittest discover -s tests -v
```

The gate is **not passed** until the same generated-source differential check completes with MSVC on Windows and the command output is captured in `docs/STATE.md`. A host GCC pass does not prove MSVC compatibility.

## Current gate state

See [`docs/STATE.md`](docs/STATE.md), [`docs/ROADMAP.md`](docs/ROADMAP.md), and [`docs/DECISIONS/ADR-0001-foundation-and-clean-room.md`](docs/DECISIONS/ADR-0001-foundation-and-clean-room.md). The RPTP license remains pending formal ADR approval. No `LICENSE` file is included in this bundle.
