# Bully (USA)

- **Status:** Inspected (read-only)
- **Last updated:** 2026-10-22
- **RPTP inspector:** `tools/rptp_inspect.py` at `d51f0e7`
- **Source:** owner-provided local ISO; not committed
- **Filename:** `Bully (USA).iso`
- **Product code (from boot filename):** `SLUS_212.69`
- **Volume ID:** `BULLY`
- **ISO size:** 4,636,835,840 bytes
- **ISO size mod 2048:** 0
- **Sector count:** 2,264,080
- **ISO SHA-256:** `6c95edf7803aa79fdc816295cf2e03066599a6693f7d543fbcdb78d1d1128d5e`
- **Logical block size:** 2048
- **Volume space blocks:** 2,264,080
- **Volume space relation:** equal to the file sector count (0 bytes difference)
- **SYSTEM.CNF path:** `SYSTEM.CNF;1`
- **SYSTEM.CNF size:** 57 bytes
- **SYSTEM.CNF SHA-256:** `aa69ad2655f3ae3b58df05ac58e5180107184cc4dd544c2347f67ae1326c41f7`
- **BOOT2:** `cdrom0:\SLUS_212.69;1`
- **Boot executable:** `SLUS_212.69;1`
- **Boot executable size:** 5,132,120 bytes
- **Boot executable SHA-256:** `597d7816d922cf371d757e653368488c1983f95dcdea0dd70a733650727f52fc`
- **Boot extent:** LBA 757, 5,132,120 bytes, flags 0, volume sequence 1
- **Boot size vs 4 MiB cap:** 937,816 bytes above the 4,194,304-byte default materialization cap; read-only inspection completed without materializing the file
- **Directory survey:** 36 directories (35 non-root directory records), 248 files, max depth 2; 0 multi-extent records; 0 interleaved records; 0 skipped unsupported directories
- **Highest file extent end:** 4,636,833,792 bytes; 2,048 bytes below the volume-space end and file end
- **Largest file size:** 818,270,208 bytes
- **ELF:** ELF32, little-endian, EM_MIPS (8), ET_EXEC (2), entry `0x00100008`, 19 PT_LOAD
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

- Region is taken from the filename, not independently verified.
- The boot executable exceeds the 4 MiB default materialization cap; read-only metadata inspection still completed.
- This record is one authorized sample, not evidence of broad ISO or game compatibility.
- No safe extraction boundary or loader exists.
- Formal Gate 0 review and the ADR-0003 clean-room prerequisites remain owner-controlled.

## Next safe action

1. Keep this record updated if the image or inspector changes.
2. Keep extraction and execution out of scope until an owner-approved safe boundary exists.
3. Record additional authorized layouts without generalizing from this sample.
