# Need for Speed - Most Wanted (USA) (v2.00)

- **Status:** Inspected (read-only)
- **Last updated:** 2026-10-22
- **RPTP inspector:** `tools/rptp_inspect.py` at `25b4ab8`
- **Source:** owner-provided local ISO; not committed
- **Filename:** `Need for Speed - Most Wanted (USA) (v2.00).iso`
- **Product code:** `SLUS_212.67`
- **Volume ID:** (empty in PVD)
- **ISO size:** 3,702,456,320 bytes
- **ISO size mod 2048:** 0
- **Sector count:** 1,807,840
- **ISO SHA-256:** `b2286fb3067351323fef17e006f7715f23b5cbf5bfd7be6aad406176e3e759d2`
- **Logical block size:** 2048
- **Volume space blocks:** 1,807,840
- **Volume space relation:** equal to the file sector count (0 bytes difference)
- **SYSTEM.CNF path:** `SYSTEM.CNF;1`
- **SYSTEM.CNF size:** 57 bytes
- **BOOT2 target:** `SLUS_212.67;1`
- **Boot executable:** `SLUS_212.67;1`
- **Boot executable size:** 4,918,740 bytes
- **Boot size vs 4 MiB cap:** 724,436 bytes above the 4,194,304-byte default materialization cap
- **Directory survey:** 5 directories (4 non-root directory records), 21 files, max depth 2; 0 multi-extent records; 0 interleaved records; 0 skipped unsupported directories
- **Highest file extent end:** 3,681,464,000 bytes; 20,992,320 bytes below the volume-space end and file end
- **Largest file size:** 1,010,616,320 bytes
- **Warnings:** none
- **Outcome:** `INSPECTED`

## What was tested

- Read-only inspection and metadata-only directory survey on 2026-10-22.
- The inspector resolved `SYSTEM.CNF`, the `BOOT2` target and the boot executable size.
- The audit recorded that the boot executable is larger than the default materialization cap.
- No files were extracted or modified; no executable was run.

## What is not tested

- Boot, native runtime, recompilation or gameplay.
- ELF layout, dependencies or executable contents beyond the existing inspector metadata pass.
- Extraction or materialization of the oversized boot executable.
- Other regions, revisions or disc layouts; compatibility is not established.

## Known limitations and blockers

- The PVD volume identifier is empty; the boot executable name is the only product code observed.
- The boot executable exceeds the 4 MiB default materialization cap; the current inspection still completed, but extraction support is not established.
- This record is one authorized sample, not evidence of broad ISO or game compatibility.
- No safe extraction boundary or loader exists.
- Formal Gate 0 review and the ADR-0003 clean-room prerequisites remain owner-controlled.

## Next safe action

1. Keep this record updated if the image or inspector changes.
2. Revisit the materialization cap before building extraction, using measured retail boot sizes.
3. Do not extract or execute the game without an owner-approved safe extraction boundary.
