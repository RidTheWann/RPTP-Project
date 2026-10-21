# Recompile Ps2 To PC (RPTP)

![RPTP project cover](docs/assets/rptp-cover.png)


**From PlayStation 2 ISO to native Windows x64 — through static recompilation.**

RPTP is an open-source research project exploring how to transform a user-owned PlayStation 2 game image into a native Windows x64 build by statically recompiling supported Emotion Engine (EE) code to C++, alongside a from-scratch runtime for the PS2 services a game needs.

> **Development status: early research.** The published Gate 0 spike is a narrow, passing synthetic differential test. It is not a PS2 ISO loader, a complete R5900 recompiler, or evidence that any commercial game boots or runs.

## Project goals

- Recompile supported EE code into native C++ and build for Windows x64.
- Implement the required PS2 runtime services independently, incrementally and with tests.
- Prioritize measured correctness, performance, reproducibility and compatibility over broad unsupported claims.
- Keep the implementation from scratch; do not copy emulator or recompiler implementation source.
- Build an open, transparent project that can be inspected, tested and improved by the community.

## Current status

### Gate 0 — synthetic recompilation spike

**Technical spike: passed on Windows x64/MSVC and Linux host compilers. Formal Gate 0 acceptance: pending owner review.**

The published spike currently demonstrates:

- A generated, manifest-registered synthetic ELF32/EM_MIPS test fixture.
- Basic ELF header and executable-segment bounds checks.
- A limited instruction subset: `ADDIU`, `ADDU`, `LW`, `SW`, `BEQ`, `BNE`, `J`, `JAL`, `JR` and `NOP`.
- A reference interpreter and deterministic C++ generation.
- Native-vs-oracle comparison of tested register state, memory writes, final PC/halt state and executed-PC trace, including tested delay-slot behavior.
- An artifact guard and 12 unit tests.

The Windows run used MSVC x64 with C++20 and strict warnings. Both `windows_msvc_verified` and `native_matches_oracle` were true in the run report. The tested native trace contains 22 steps.

**Not implemented or proven:** retail ISO inspection/boot, full R5900 semantics, function discovery for real games, EE kernel/syscalls, VU, GS graphics, IOP, CDVD, audio, controller, memory card, timing, or commercial-game compatibility.

## Development phases

1. **Gate 0 — Foundation and spike:** technical differential test completed; formal review remains open.
2. **B1a — Project foundation:** license and architecture decision recorded; clean-room/source-exposure review remains an explicit concern.
3. **B1b — Repository/toolchain baseline:** CLI, CMake, diagnostics, CI, dependency/license checks and reproducible builds.
4. **ISO Inspector:** read-only ISO9660 and `SYSTEM.CNF` inspection, executable metadata, hashing, safe extraction and malformed-input tests.
5. **Recompiler MVP:** verified instruction catalog, decoder, IR, function discovery, deterministic code generation and differential tests.
6. **First-game vertical slice:** boot, minimum runtime services, graphics, audio/input/save and repeatable gameplay.
7. **Compatibility and release:** expand subsystem coverage using measured blockers, then validate clean-machine builds and release artifacts.

The detailed plan and pass criteria live in [docs/ROADMAP.md](docs/ROADMAP.md). See [docs/STATE.md](docs/STATE.md) for current evidence and limitations.

## Build and test the Gate 0 spike

Requirements: Python 3.10+ and a C++20 compiler. On Windows, use Developer PowerShell for Visual Studio or an x64 Native Tools command prompt.

### Windows / MSVC

```powershell
python tools\check_forbidden_artifacts.py --root .
python tools\rptp_gate0_spike.py --out build\gate0-msvc --compiler cl
python -m unittest discover -s tests -v
```

Or run the repository wrapper:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-msvc.ps1
```

### Linux / GCC

```bash
python3 tools/check_forbidden_artifacts.py --root .
python3 -m unittest discover -s tests -v
python3 tools/rptp_gate0_spike.py --out build/gate0 --compiler g++
```

Build outputs are local and should not be committed. Only synthetic binary fixtures explicitly registered in `tests/fixtures/MANIFEST` are permitted; do not add commercial ISOs, BIOS files, game executables, or proprietary assets.

## Architecture and clean-room boundaries

- **Approach:** from-scratch static ahead-of-time recompilation; native Windows x64 target.
- **Generated output:** C++ compiled by the target host toolchain.
- **Verification:** deterministic output, reference-oracle differential tests, fixture hashes and explicit unsupported-instruction errors.
- **Clean room:** do not copy implementation source from emulators or recompilers. Prior technical-source exposure is documented in [docs/REFERENCES.md](docs/REFERENCES.md) and [ADR-0001](docs/DECISIONS/ADR-0001-foundation-and-clean-room.md); it must not be ignored or represented as erased.

## License

Original RPTP project material is offered under **GNU GPL-3.0-or-later**, subject to the license text and applicable notices. See [LICENSE](LICENSE) and [docs/LICENSES.md](docs/LICENSES.md). Third-party material retains its own license. This project license does not grant rights to distribute PS2 BIOS files, commercial game images, proprietary assets, or game-derived output.

## Contributing

Start with the current state, roadmap, risk register and architecture decisions. Submit reproducible evidence with changes; keep claims proportional to tests. New binary fixtures require a manifest entry documenting their synthetic origin, hash and license status.

**Play it. Change it. Fork it. Build it together.**
