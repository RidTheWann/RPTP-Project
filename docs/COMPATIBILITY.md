# Compatibility status

No commercial PS2 game has been booted or tested for gameplay. The current owner-authorized retail sample has been inspected read-only.

| Test item | Type | Current result | What this result means |
|---|---|---|---|
| `gate0-r5900-subset.elf` | Original synthetic ELF32/EM_MIPS fixture | `Inspect passed` / `Recompile passed` on Windows x64/MSVC and Linux host compilers | The specific instruction sequence compiles to native C++ and matches its test oracle. It is not a PS2 retail game and is not a compatibility claim. |
| Synthetic ISO inspector fixtures | Generated ISO/ELF test data | `Inspect passed` | Metadata, malformed-input rejection, chunked-read limits, deterministic in-memory and file-based mutation checks and CLI JSON paths pass in the ISO inspector suite. No real disc is involved. |
| Black (USA) | Retail PS2 ISO | `Inspect passed (read-only)` | The inspector resolved `SYSTEM.CNF` and `BOOT2` and reported boot metadata. No boot, recompilation or gameplay was tested. See [the game record](games/black/STATUS.md). |
| Downhill Domination (USA) | Retail PS2 ISO | `Inspect passed (read-only)` | The inspector resolved `SYSTEM.CNF` and `BOOT2` and reported ELF32/EM_MIPS metadata. No boot, recompilation or gameplay was tested. See [the game record](games/downhill-domination/STATUS.md). |
| God of War II (USA) | Retail PS2 ISO | `Inspect passed (read-only)` | The PVD volume space is smaller than the file; the directory survey covers only the PVD-addressable space. No boot, recompilation or gameplay was tested. See [the game record](games/god-of-war-ii/STATUS.md). |
| Need for Speed - Most Wanted (USA) (v2.00) | Retail PS2 ISO | `Inspect passed (read-only)` | The boot executable is larger than the default 4 MiB materialization cap. No extraction, boot, recompilation or gameplay was tested. See [the game record](games/need-for-speed-most-wanted/STATUS.md). |
| Resident Evil 4 (USA) | Retail PS2 ISO | `Inspect passed (read-only)` | The inspector resolved `SYSTEM.CNF` and `BOOT2` and reported boot metadata. No boot, recompilation or gameplay was tested. See [the game record](games/resident-evil-4/STATUS.md). |
| Other retail PS2 ISOs outside the current sample | Retail game | `Not tested` | The current sample is not evidence of broad compatibility. No boot or game-compatibility claim is made. |
| Windows/MSVC | Build platform check | `Verified` | Visual Studio 2026 Build Tools, MSVC 19.51.36260.0: doctor, configure, CTest and Gate 0 differential spike pass locally; results are recorded in [docs/VERIFICATION_LOG.md](VERIFICATION_LOG.md). |
| Linux/GCC | Build platform check | `Verified in CI` | Runs `39594267744`, `39594147110` and `39594304857` passed. |

Fixture metadata:

- SHA-256 of synthetic ELF: `b21f1f7793236d1ccba7308cc82f42d9f89915c87c0b037c46d8170f28349ca9`
- Generated C++ SHA-256: `5316e0f51ba8b1fa1252e409f38cb9ac7db7606fee17b28ef0dcf1be162ae795`
- Supported subset: ADDIU, ADDU, LW, SW, BEQ, BNE, J, JAL, JR, NOP.
- Latest observed host trace: 22 instruction PCs; identical to the reference interpreter for this fixture path.

ISO inspector evidence:

- The ISO inspector suite and the full Python suite pass; local Windows CTest and Gate 0 results are recorded in [docs/VERIFICATION_LOG.md](VERIFICATION_LOG.md).
- Supported: single-volume ISO 9660 primary volume descriptors, 2048-byte logical blocks, root `SYSTEM.CNF`, `BOOT2`/`BOOT` path resolution, ELF32 PT_LOAD metadata, and bounded/chunked file reads with a 4 MiB default cap.
- Retail sample: the current owner-authorized titles passed read-only inspection with no warnings. Four have equal PVD volume space and file sector counts; `God of War II` reports a smaller PVD volume space (dual-layer is unverified). One boot executable (`Need for Speed - Most Wanted`) is larger than the 4 MiB default materialization cap. No boot or port exists.
- Directory surveys of the sample found no multi-extent or interleaved records. Those layouts remain explicitly rejected by normal inspection.
- Interleave field offsets are not verified against the ECMA-119 text; a zero-interleave sample does not validate them.
- Explicitly unsupported: multi-volume sets, multi-extent files/directories, interleaved files/directories, Joliet/Rock Ridge extensions, 2352-byte raw sectors and broad retail-layout validation.
- The inspector is read-only and does not extract, boot, emulate or recompile a game.

A status may only be promoted for a real game after its serial/region, executable hash, RPTP version, tested behaviors, log and known issues are recorded. Per-game records under `docs/games/` may contain title/region/serial, sizes, hashes and boot metadata; they must not contain ISO images, extracted game files or proprietary assets.
