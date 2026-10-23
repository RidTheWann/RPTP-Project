# Compatibility status

No commercial PS2 game has been booted or tested for gameplay. The current owner-authorized retail sample has been inspected read-only.

| Test item | Type | Current result | What this result means |
|---|---|---|---|
| `gate0-r5900-subset.elf` | Original synthetic ELF32/EM_MIPS fixture | `Inspect passed` / `Recompile passed` on Windows x64/MSVC and Linux host compilers | The specific instruction sequence compiles to native C++ and matches its test oracle. It is not a PS2 retail game and is not a compatibility claim. |
| Synthetic IR lowering fixtures | Generated ELF32/EM_MIPS at test time | `Recompile passed` on Windows x64/MSVC | The 29-instruction lowering fixture (26 executed PCs), a 13-instruction dynamic-JR fixture, an 18-instruction logical-immediate fixture, a 9-instruction LUI fixture, a 24-instruction register-logical fixture and a 16-instruction NOR fixture match the oracle for registers, memory, stop PC and trace. Uninitialized loads exit 2. Synthetic-only; not a game or compatibility claim. |
| Synthetic ISO inspector fixtures | Generated ISO/ELF test data | `Inspect passed` | Metadata, malformed-input rejection, chunked-read limits, deterministic in-memory and file-based mutation checks and CLI JSON paths pass in the ISO inspector suite. No real disc is involved. |
| Black (USA) | Retail PS2 ISO | `Inspect passed (read-only)` | The inspector resolved `SYSTEM.CNF` and `BOOT2` and reported boot metadata. No boot, recompilation or gameplay was tested. See [the game record](games/black/STATUS.md). |
| Bully (USA) | Retail PS2 ISO | `Inspect passed (read-only)` | The boot executable is larger than the default 4 MiB materialization cap; read-only metadata inspection still completed. No extraction, boot, recompilation or gameplay was tested. See [the game record](games/bully/STATUS.md). |
| Downhill Domination (USA) | Retail PS2 ISO | `Inspect passed (read-only)` | The inspector resolved `SYSTEM.CNF` and `BOOT2` and reported ELF32/EM_MIPS metadata. No boot, recompilation or gameplay was tested. See [the game record](games/downhill-domination/STATUS.md). |
| God of War II (USA) | Retail PS2 ISO | `Inspect passed (read-only)` | The PVD volume space is smaller than the file; the directory survey covers only the PVD-addressable space. No boot, recompilation or gameplay was tested. See [the game record](games/god-of-war-ii/STATUS.md). |
| Grand Theft Auto - San Andreas (USA) — owner-described original | Retail PS2 ISO | `Inspect passed (read-only)` | Owner-provided provenance identifies this as the original USA sample; the classification is not technically verified. It shares boot and `SYSTEM.CNF` hashes with the Indonesian-language mod, but their whole-image hashes and PVD identifiers differ. Shared boot metadata does not identify modified files. No extraction, boot, recompilation or gameplay was tested. See [the game record](games/grand-theft-auto-san-andreas-usa-v300/STATUS.md). |
| Grand Theft Auto - San Andreas (USA) — owner-described Indonesian-language mod | Retail PS2 ISO | `Inspect passed (read-only)` | Owner-provided provenance identifies this as a USA sample modified with Indonesian-language changes; the changed file set, scope and method are unaudited. Shared boot and `SYSTEM.CNF` hashes do not establish file equality or locate the modification. No extraction, boot, recompilation or gameplay was tested. See [the game record](games/grand-theft-auto-san-andreas-indonesian-v6/STATUS.md). |
| Need for Speed - Most Wanted (USA) (v2.00) | Retail PS2 ISO | `Inspect passed (read-only)` | The boot executable is larger than the default 4 MiB materialization cap. No extraction, boot, recompilation or gameplay was tested. See [the game record](games/need-for-speed-most-wanted/STATUS.md). |
| Resident Evil 4 (USA) | Retail PS2 ISO | `Inspect passed (read-only)` | The inspector resolved `SYSTEM.CNF` and `BOOT2` and reported boot metadata. No boot, recompilation or gameplay was tested. See [the game record](games/resident-evil-4/STATUS.md). |
| Other retail PS2 ISOs outside the current sample | Retail game | `Not tested` | The current sample is not evidence of broad compatibility. No boot or game-compatibility claim is made. |
| Windows/MSVC | Build platform check | `Verified` | Visual Studio 2026 Community, MSVC toolset 14.51.36231: doctor, configure, CTest, Gate 0 differential spike and native synthetic lowering/logical-immediate/LUI/register-logical/NOR tests pass locally; results are recorded in [docs/VERIFICATION_LOG.md](VERIFICATION_LOG.md). |
| Linux/GCC | Build platform check | `Verified in CI` | Runs `39594267744`, `39594147110`, `39594304857`, `39664774001`, `39838955979`, `39852791294`, `39860776782`, `39908025708`, `39920189021` and `39994586188` passed. |

Fixture metadata:

- SHA-256 of synthetic ELF: `b21f1f7793236d1ccba7308cc82f42d9f89915c87c0b037c46d8170f28349ca9`
- Generated C++ SHA-256: `5316e0f51ba8b1fa1252e409f38cb9ac7db7606fee17b28ef0dcf1be162ae795`
- Accepted Gate 0 fixture subset: ADDIU, ADDU, LW, SW, BEQ, BNE, J, JAL, JR, NOP. Separate post-disposition tests cover ORI, ANDI, XORI, LUI, AND, OR, XOR and NOR without changing this fixture.
- Latest observed host trace: 22 instruction PCs; identical to the reference interpreter for this fixture path.

ISO inspector evidence:

- The ISO inspector suite and the full Python suite pass; local Windows CTest and Gate 0 results are recorded in [docs/VERIFICATION_LOG.md](VERIFICATION_LOG.md).
- Supported: single-volume ISO 9660 primary volume descriptors, 2048-byte logical blocks, root `SYSTEM.CNF`, `BOOT2`/`BOOT` path resolution, ELF32 PT_LOAD metadata, and bounded/chunked file reads with a 4 MiB default cap.
- Retail sample: the current owner-authorized titles passed read-only inspection with no warnings. Seven have equal PVD volume space and file sector counts. `God of War II` declares 2,083,888 blocks (4,267,802,624 bytes) in an 8,533,671,936-byte image; its 15 reported files lie inside the declared volume, while 2,082,944 sectors remain outside the inspected volume and have no verified purpose or layer status. Four images (`Need for Speed - Most Wanted`, `Bully`, and both owner-described San Andreas samples) have boot executables above the 4 MiB default materialization cap; their read-only inspections still completed. No boot or port exists.
- The two GTA San Andreas records are separate owner-provided samples: an original USA sample and an Indonesian-language mod. This is declarative provenance, not a technical classification; shared boot metadata does not establish file equality or identify the modification.
- Directory surveys of the sample found no multi-extent or interleaved records. Those layouts remain explicitly rejected by normal inspection.
- ECMA-119 5th edition Table 8 and §§10.1.8–10.1.9 confirm that zero-based record bytes 26 and 27 are the file-unit and interleave-gap fields. Targeted tests reject either field independently; interleaved layouts remain unsupported.
- Explicitly unsupported: multi-volume sets, multi-extent files/directories, interleaved files/directories, Joliet/Rock Ridge extensions, 2352-byte raw sectors and broad retail-layout validation.
- The inspector is read-only and does not extract, boot, emulate or recompile a game.
- Gate 2 is a read-only milestone under [ADR-0004](DECISIONS/ADR-0004-gate2-read-only-scope.md); extraction is not implemented and requires a separate future decision and threat model.

A status may only be promoted for a real game after its serial/region, executable hash, RPTP version, tested behaviors, log and known issues are recorded. Per-game records under `docs/games/` may contain title/region/serial, sizes, hashes and boot metadata; they must not contain ISO images, extracted game files or proprietary assets.
