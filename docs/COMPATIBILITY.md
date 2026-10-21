# Compatibility status

No commercial PS2 game has been booted or tested for gameplay. One owner-authorized retail ISO has been inspected read-only.

| Test item | Type | Current result | What this result means |
|---|---|---|---|
| `gate0-r5900-subset.elf` | Original synthetic ELF32/EM_MIPS fixture | `Inspect passed` / `Recompile passed` on Windows x64/MSVC and Linux host compilers | The specific instruction sequence compiles to native C++ and matches its test oracle. It is not a PS2 retail game and is not a compatibility claim. |
| Synthetic ISO inspector fixtures | Generated ISO/ELF test data | `Inspect passed` | Metadata, malformed-input rejection, deterministic mutation smoke and CLI JSON paths pass in the 33-test ISO inspector suite. No real disc is involved. |
| Downhill Domination (USA) | Retail PS2 ISO | `Inspect passed (read-only)` | The inspector resolved `SYSTEM.CNF` and `BOOT2` and reported ELF32/EM_MIPS metadata. No boot, recompilation or gameplay was tested. See [the game record](games/downhill-domination/STATUS.md). |
| Other retail PS2 ISOs | Retail game | `Not tested` | One real ISO layout is not evidence of broad compatibility. No boot or game-compatibility claim is made. |
| Windows/MSVC | Build platform check | `Verified` | Visual Studio 2026 Build Tools, MSVC 19.51.36260.0: doctor, configure, CTest 3/3 and Gate 0 differential spike pass locally. |
| Linux/GCC | Build platform check | `Verified on main CI` | GitHub Actions run `39561754883` on commit `371cec8` passed. The development branch CI result is pending under the two-branch policy in `docs/BRANCH_POLICY.md`. |

Fixture metadata:

- SHA-256 of synthetic ELF: `b21f1f7793236d1ccba7308cc82f42d9f89915c87c0b037c46d8170f28349ca9`
- Generated C++ SHA-256: `5316e0f51ba8b1fa1252e409f38cb9ac7db7606fee17b28ef0dcf1be162ae795`
- Supported subset: ADDIU, ADDU, LW, SW, BEQ, BNE, J, JAL, JR, NOP.
- Latest observed host trace: 22 instruction PCs; identical to the reference interpreter for this fixture path.

ISO inspector evidence:

- 33 ISO inspector tests, 53 tests in the full Python suite, and CTest 3/3 on the local Windows environment.
- Supported: single-volume ISO 9660 primary volume descriptors, 2048-byte logical blocks, root `SYSTEM.CNF`, `BOOT2`/`BOOT` path resolution, and ELF32 PT_LOAD metadata.
- Real-world sample: `Downhill Domination (USA)` passed read-only inspection; `BOOT2` resolves to `SCUS_971.77`, an ELF32/EM_MIPS executable with one PT_LOAD segment and no warnings. No boot or port exists.
- Explicitly unsupported: multi-volume sets, multi-extent files/directories, Joliet/Rock Ridge extensions, 2352-byte raw sectors and broad retail-layout validation.
- The inspector is read-only and does not extract, boot, emulate or recompile a game.

A status may only be promoted for a real game after its serial/region, executable hash, RPTP version, tested behaviors, log and known issues are recorded. Per-game records under `docs/games/` may contain title/region/serial, sizes, hashes and boot metadata; they must not contain ISO images, extracted game files or proprietary assets.
