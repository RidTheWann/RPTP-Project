# Bully (USA)

- **Status:** Boot analysis (static census)
- **Last updated:** 2026-10-29
- **RPTP inspector:** `tools/rptp_inspect.py`, hardened revision `0c2264e`; source SHA-256 verification and full fingerprint: [verification log](../../VERIFICATION_LOG.md)
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
- **Warnings:** `BOOT ELF PT_LOAD memory ranges overlap; loading precedence is not evaluated.`
- **Outcome:** `INSPECTED_WITH_WARNINGS`

## What was tested

### Historical run — 2026-10-22

Historical outcome: `INSPECTED`, no warnings reported by `d51f0e7`.

- Read-only inspection and metadata-only directory survey on 2026-10-22 with the inspector at `d51f0e7`.
- The inspector resolved `SYSTEM.CNF`, the `BOOT2` target, boot extent and ELF metadata.
- Input size and last-write timestamp were unchanged before and after the survey and inspection runs.
- No files were extracted or modified; no executable was run.

### 2026-10-28 — repeated read-only CLI and ELF metadata checks

Recorded owner-authorized local evidence from main; documentation checked against the reports below without reopening the ISO. Not CI verification.

- CLI inspect ran twice: exit 0, `INSPECTED_WITH_WARNINGS`, byte-identical JSON. Survey ran twice: exit 0, `SURVEYED`, no warnings, byte-identical JSON.
- Whole-image SHA-256 was recomputed before and after these runs, unchanged and matching the previous hash above; size and mtime were unchanged.
- Read-only ELF load map: 19 PT_LOAD; file/virtual ranges and zero-fill metadata were reported, including zero-file-size segments with overlapping memory ranges. PH0 zero-fill is 1,515,648 bytes. No loading or zero-fill execution was tested ([RPTP-REF-003](../../REFERENCES.md)).
- Entry `0x00100008` maps uniquely to PF_X file-backed bytes in program header 0 at ELF-relative file offset 776 bytes. Independent sparse ELF-header/entry/overlap cross-check agrees.
- The overlap warning is metadata only; loading precedence remains undefined and is not evaluated. It is not evidence of corruption, an unsupported disc or compatibility.
- Evidence: local `build/elf-retail-summary.json`, `build/elf-retail-bully.inspect.json`, `build/elf-retail-bully.survey.json` and `build/elf-retail-independent-check.json`.
- No extraction, content analysis, function discovery, boot, runtime, recompilation or compatibility testing was performed.

### 2026-10-29 — read-only boot-code census

- `python tools/rptp_census.py <iso> --iso --json` completed in memory with exit 0 and status `CENSUSED_WITH_WARNINGS`; no file was extracted, modified or executed.
- Census: 1,282,560 aligned words across 19 PT_LOAD segment(s); 640,730 (50.0%) accepted by the current synthetic decoder; 641,830 raw-unsupported words.
- Most frequent unsupported raw encodings: `special_0x2d` (104,020); `opcode_0x11` (85,141); `opcode_0x31` (58,096).
- Counts include data and padding and are not a function-level, runtime, boot or compatibility measurement. See [BOOT_CENSUS.md](../../BOOT_CENSUS.md).

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
- The narrow Gate 0 technical pass for synthetic code was recorded on 2026-10-23; it does not authorize boot, recompilation or compatibility claims for this title. ADR-0003 clean-room prerequisites and independent provenance reviews remain in force.

## Next safe action

1. Keep this record updated if the image or inspector changes.
2. Keep extraction and execution out of scope until an owner-approved safe boundary exists.
3. Record additional authorized layouts without generalizing from this sample.
