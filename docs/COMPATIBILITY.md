# Compatibility status

No commercial PS2 game has been tested by this project. The ISO inspector is implemented, but no retail disc layout has been validated.

| Test item | Type | Current result | What this result means |
|---|---|---|---|
| `gate0-r5900-subset.elf` | Original synthetic ELF32/EM_MIPS fixture | `Inspect passed` / `Recompile passed` on Windows x64/MSVC and Linux host compilers | The specific instruction sequence compiles to native C++ and matches its test oracle. It is not a PS2 retail game and is not a compatibility claim. |
| Synthetic ISO inspector fixtures | Generated ISO/ELF test data | `Inspect passed` | Metadata, malformed-input rejection, deterministic mutation smoke and CLI JSON paths pass in the 33-test ISO inspector suite. No real disc is involved. |
| Any retail PS2 ISO | Retail game | `Not tested` | The inspector exists, but no real retail ISO layout has been validated. No boot or game-compatibility claim is made. |
| Windows/MSVC | Build platform check | `Verified` | Visual Studio 2026 Build Tools, MSVC 19.51.36260.0: doctor, configure, CTest 3/3 and Gate 0 differential spike pass locally. |
| Linux/GCC | Build platform check | `Verified on main CI` | GitHub Actions run `39561754883` on commit `371cec8` passed. This reconciliation branch has not run CI. |

Fixture metadata:

- SHA-256 of synthetic ELF: `b21f1f7793236d1ccba7308cc82f42d9f89915c87c0b037c46d8170f28349ca9`
- Generated C++ SHA-256: `5316e0f51ba8b1fa1252e409f38cb9ac7db7606fee17b28ef0dcf1be162ae795`
- Supported subset: ADDIU, ADDU, LW, SW, BEQ, BNE, J, JAL, JR, NOP.
- Latest observed host trace: 22 instruction PCs; identical to the reference interpreter for this fixture path.

ISO inspector evidence:

- 33 ISO inspector tests, 52 tests in the full Python suite, and CTest 3/3 on the local Windows environment.
- Supported: single-volume ISO 9660 primary volume descriptors, 2048-byte logical blocks, root `SYSTEM.CNF`, `BOOT2`/`BOOT` path resolution, and ELF32 PT_LOAD metadata.
- Explicitly unsupported: multi-volume sets, multi-extent files/directories, Joliet/Rock Ridge extensions, 2352-byte raw sectors and real retail-disc validation.
- The inspector is read-only and does not extract, boot, emulate or recompile a game.

A status may only be promoted for a real game after its serial/region, executable hash, RPTP version, tested behaviors, log and known issues are recorded. Do not include ISO hashes or game assets unless policy explicitly allows the metadata; this initial report includes only the synthetic fixture hash.
