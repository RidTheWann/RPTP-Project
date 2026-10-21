# Black (USA)

- **Status:** Inspected (read-only)
- **Last updated:** 2026-10-22
- **RPTP inspector:** `tools/rptp_inspect.py` at `25b4ab8`
- **Source:** owner-provided local ISO; not committed
- **Filename:** `Black (USA).iso`
- **Product code:** `SLUS_213.76`
- **Volume ID:** (empty in PVD)
- **ISO size:** 3,919,609,856 bytes
- **ISO size mod 2048:** 0
- **Sector count:** 1,913,872
- **ISO SHA-256:** `65768cade88bfbaf566b67a3ef7a0bda5a9669779833914ffe7cd73a3e45cccd`
- **Logical block size:** 2048
- **Volume space blocks:** 1,913,872
- **Volume space relation:** equal to the file sector count (0 bytes difference)
- **SYSTEM.CNF path:** `SYSTEM.CNF;1`
- **SYSTEM.CNF size:** 57 bytes
- **BOOT2 target:** `SLUS_213.76;1`
- **Boot executable:** `SLUS_213.76;1`
- **Boot executable size:** 3,371,868 bytes
- **Boot size vs 4 MiB cap:** 822,436 bytes below the 4,194,304-byte default materialization cap
- **Directory survey:** 41 directories (40 non-root directory records), 585 files, max depth 3; 0 multi-extent records; 0 interleaved records; 0 skipped unsupported directories
- **Highest file extent end:** 3,898,607,616 bytes; 21,002,240 bytes below the volume-space end and file end
- **Largest file size:** 117,669,888 bytes
- **Warnings:** none
- **Outcome:** `INSPECTED`

## What was tested

- Read-only inspection and metadata-only directory survey on 2026-10-22.
- The inspector resolved `SYSTEM.CNF`, the `BOOT2` target and the boot executable size.
- No files were extracted or modified; no executable was run.

## What is not tested

- Boot, native runtime, recompilation or gameplay.
- ELF layout, dependencies or executable contents beyond the existing inspector metadata pass.
- Other regions, revisions or disc layouts; compatibility is not established.

## Known limitations and blockers

- The PVD volume identifier is empty; the boot executable name is the only product code observed.
- This record is one authorized sample, not evidence of broad ISO or game compatibility.
- No safe extraction boundary or loader exists.
- Formal Gate 0 review and the ADR-0003 clean-room prerequisites remain owner-controlled.

## Next safe action

1. Keep this record updated if the image or inspector changes.
2. Do not extract or execute the game without an owner-approved safe extraction boundary.
3. Record additional authorized layouts without generalizing from this sample.
