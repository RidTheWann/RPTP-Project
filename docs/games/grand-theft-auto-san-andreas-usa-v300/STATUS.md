# Grand Theft Auto - San Andreas (USA) (v3.00)

- **Status:** Inspected (read-only)
- **Last updated:** 2026-10-22
- **RPTP inspector:** `tools/rptp_inspect.py` at `d51f0e7`
- **Source:** owner-provided local ISO; not committed
- **Filename:** `Grand Theft Auto - San Andreas (USA) (v3.00).iso`
- **Product code (from boot filename):** `SLUS_209.46`
- **Volume ID:** `SAN_ANDREAS`
- **ISO size:** 4,517,036,032 bytes
- **ISO size mod 2048:** 0
- **Sector count:** 2,205,584
- **ISO SHA-256:** `c94e9b16ffab9ab04dbf15109e8716a2bf0a853a246bd3d2641bf354a5068e6d`
- **Logical block size:** 2048
- **Volume space blocks:** 2,205,584
- **Volume space relation:** equal to the file sector count (0 bytes difference)
- **PVD publisher / data preparer:** `ROCKSTAR GAMES` / `ROCKSTAR NORTH`
- **PVD volume set identifier:** `SAN_ANDREAS`
- **SYSTEM.CNF path:** `SYSTEM.CNF;1`
- **SYSTEM.CNF size:** 57 bytes
- **SYSTEM.CNF VER:** 3.00
- **SYSTEM.CNF SHA-256:** `7d48c5d05735d54498a2e7e96c9e687ed2f9c1c00a820a36f4c3f2240d8da0bd`
- **BOOT2:** `cdrom0:\SLUS_209.46;1`
- **Boot executable:** `SLUS_209.46;1`
- **Boot executable size:** 5,684,592 bytes
- **Boot executable SHA-256:** `84d4980a1253c5490ebbd039ef17384af875de75636a21f3451951093e8fc789`
- **Boot extent:** LBA 787, 5,684,592 bytes, flags 0, volume sequence 1
- **Boot size vs 4 MiB cap:** 1,490,288 bytes above the 4,194,304-byte default materialization cap; read-only inspection completed without materializing the file
- **Directory survey:** 29 directories (28 non-root directory records), 299 files, max depth 3; 0 multi-extent records; 0 interleaved records; 0 skipped unsupported directories
- **Highest file extent end:** 4,496,060,416 bytes; 20,975,616 bytes below the volume-space end and file end
- **Largest file size:** 478,615,552 bytes
- **ELF:** ELF32, little-endian, EM_MIPS (8), ET_EXEC (2), entry `0x00100008`, 10 PT_LOAD
- **Warnings:** none
- **Outcome:** `INSPECTED`

## What was tested

- Read-only inspection and metadata-only directory survey on 2026-10-22 with the inspector at `d51f0e7`.
- The inspector resolved `SYSTEM.CNF`, the `BOOT2` target, boot extent and ELF metadata.
- Input size and last-write timestamp were unchanged before and after the survey and inspection runs.
- No files were extracted or modified; no executable was run.

## What is not tested

- Boot, native runtime, recompilation or gameplay.
- Executable contents, dependencies or function discovery beyond the inspector metadata pass.
- Other regions, revisions or disc layouts; compatibility is not established.
- Extraction or materialization of the boot executable above the 4 MiB cap.

## Known limitations and blockers

- Region and revision are taken from the filename and the observed `SYSTEM.CNF VER = 3.00`; they are not independently verified against a catalogue.
- The boot executable SHA-256 and `SYSTEM.CNF` SHA-256 match the [Indonesian v6 record](../grand-theft-auto-san-andreas-indonesian-v6/STATUS.md), but the whole-image hashes and PVD identifiers differ. Do not treat the records as interchangeable.
- The boot executable exceeds the 4 MiB default materialization cap; read-only metadata inspection still completed.
- This record is one authorized sample, not evidence of broad ISO or game compatibility.
- No safe extraction boundary or loader exists.
- Formal Gate 0 review and the ADR-0003 clean-room prerequisites remain owner-controlled.

## Next safe action

1. Keep this record updated if the image or inspector changes.
2. Keep extraction and execution out of scope until an owner-approved safe boundary exists.
3. Record additional authorized layouts without generalizing from this sample.
