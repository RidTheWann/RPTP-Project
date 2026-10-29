# Grand Theft Auto - San Andreas (USA) — owner-described Indonesian-language mod

- **Status:** Boot analysis (static census)
- **Last updated:** 2026-10-29
- **Sample provenance:** Owner-provided: a USA San Andreas sample modified with Indonesian-language changes. This classification is declarative owner information, not a result derived from the filename or metadata; the modified file set and method are not audited.
- **RPTP inspector:** `tools/rptp_inspect.py`, hardened revision `0c2264e`; source SHA-256 verification and full fingerprint: [verification log](../../VERIFICATION_LOG.md)
- **Source:** owner-provided local ISO; not committed
- **Filename:** `Grand Theft Auto - San Andreas (Indonesian v6).iso`
- **Product code (from boot filename):** `SLUS_209.46`
- **Volume ID:** `GTASA_PS2_ID_KHN`
- **ISO size:** 3,866,394,624 bytes
- **ISO size mod 2048:** 0
- **Sector count:** 1,887,888
- **ISO SHA-256:** `4a00e35c7b4e1dd56a6f255cba4eb7e0f5aa7a175c2c3aff9b1e3c4f90e6304f`
- **Logical block size:** 2048
- **Volume space blocks:** 1,887,888
- **Volume space relation:** equal to the file sector count (0 bytes difference)
- **PVD publisher / data preparer:** `KH4N` / `ROCKSTAR`
- **PVD volume set identifier:** (empty)
- **SYSTEM.CNF path:** `SYSTEM.CNF;1`
- **SYSTEM.CNF size:** 57 bytes
- **SYSTEM.CNF VER:** 3.00
- **SYSTEM.CNF SHA-256:** `7d48c5d05735d54498a2e7e96c9e687ed2f9c1c00a820a36f4c3f2240d8da0bd`
- **BOOT2:** `cdrom0:\SLUS_209.46;1`
- **Boot executable:** `SLUS_209.46;1`
- **Boot executable size:** 5,684,592 bytes
- **Boot executable SHA-256:** `84d4980a1253c5490ebbd039ef17384af875de75636a21f3451951093e8fc789`
- **Boot extent:** LBA 857, 5,684,592 bytes, flags 0, volume sequence 1
- **Boot size vs 4 MiB cap:** 1,490,288 bytes above the 4,194,304-byte default materialization cap; read-only inspection completed without materializing the file
- **Directory survey:** 29 directories (28 non-root directory records), 299 files, max depth 3; 0 multi-extent records; 0 interleaved records; 0 skipped unsupported directories
- **Highest file extent end:** 3,866,388,699 bytes; 5,925 bytes below the volume-space end and file end
- **Largest file size:** 478,615,552 bytes
- **ELF:** ELF32, little-endian, EM_MIPS (8), ET_EXEC (2), entry `0x00100008`, 10 PT_LOAD
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
- Read-only ELF load map: 10 PT_LOAD; file/virtual ranges and zero-fill metadata were reported, including zero-file-size segments with overlapping memory ranges. PH0 zero-fill is 2,239,232 bytes. No loading or zero-fill execution was tested ([RPTP-REF-003](../../REFERENCES.md)).
- Entry `0x00100008` maps uniquely to PF_X file-backed bytes in program header 0 at ELF-relative file offset 392 bytes. Independent sparse ELF-header/entry/overlap cross-check agrees.
- The overlap warning is metadata only; loading precedence remains undefined and is not evaluated. It is not evidence of corruption, an unsupported disc or compatibility.
- Evidence: local `build/elf-retail-summary.json`, `build/elf-retail-grand-theft-auto-san-andreas-indonesian-v6.inspect.json`, `build/elf-retail-grand-theft-auto-san-andreas-indonesian-v6.survey.json` and `build/elf-retail-independent-check.json`.
- No extraction, content analysis, function discovery, boot, runtime, recompilation or compatibility testing was performed; owner-provided mod provenance remains unaudited.

### 2026-10-29 — read-only boot-code census refresh

- `python tools/rptp_census.py <iso> --iso --json` completed in memory with exit 0 and status `CENSUSED_WITH_WARNINGS`; no file was extracted, modified or executed.
- Census with the decoder after `SLL` and `DADDU`, before `SUBU` (`R-029`): 1,420,864 aligned words across 10 PT_LOAD segment(s); 828,703 (58.3%) accepted; 592,161 raw-unsupported words. These figures supersede the earlier pre-`DADDU` count.
- Most frequent unsupported raw encodings: `opcode_0x11` (133,433); `opcode_0x31` (74,361); `opcode_0x39` (45,517).
- Counts include data and padding and are not a function-level, runtime, boot or compatibility measurement. See [BOOT_CENSUS.md](../../BOOT_CENSUS.md).

## What is not tested

- The list of files changed, translation scope, modification method, and whether all intended Indonesian-language content is covered; read-only metadata does not determine these.
- A file-by-file comparison with the owner-described original sample; shared boot and `SYSTEM.CNF` hashes do not establish file equality or locate the modification.
- Boot, native runtime, recompilation or gameplay.
- Executable contents, dependencies or function discovery beyond the inspector metadata pass.
- Other regions, revisions or disc layouts; compatibility is not established.
- Extraction or materialization of the boot executable above the 4 MiB cap.

## Known limitations and blockers

- The sample type is owner-provided: the owner identifies this as an Indonesian-language modification of the USA sample. The modified file set, translation scope and modification method are not audited.
- The filename label `Indonesian v6` and `SYSTEM.CNF VER = 3.00` do not independently establish the mod's version, source, or contents.
- The other record is the owner-described [original USA sample](../grand-theft-auto-san-andreas-usa-v300/STATUS.md). The boot executable SHA-256 and `SYSTEM.CNF` SHA-256 match, but the whole-image hashes and PVD identifiers differ. That proves the images are not byte-identical; it does not identify which files changed or explain the modification.
- The shared boot metadata is consistent with shared boot configuration and executable data; it is not a parser defect and does not prove that all other files are identical.
- The boot executable exceeds the 4 MiB default materialization cap; read-only metadata inspection still completed.
- This record is one authorized sample, not evidence of broad ISO or game compatibility.
- No safe extraction boundary or loader exists.
- The narrow Gate 0 technical pass for synthetic code was recorded on 2026-10-23; it does not authorize boot, recompilation or compatibility claims for this title. ADR-0003 clean-room prerequisites and independent provenance reviews remain in force.

## Next safe action

1. Keep this record updated if the image or inspector changes.
2. Preserve the owner-provided original/mod distinction; do not infer changed files, revision, or compatibility from the filename or shared boot metadata.
3. Any content audit requires an owner-approved extraction boundary; keep extraction and execution out of scope until then.
