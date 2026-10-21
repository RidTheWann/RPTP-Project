# God of War II (USA)

- **Status:** Inspected (read-only)
- **Last updated:** 2026-10-22
- **RPTP inspector:** `tools/rptp_inspect.py` at `25b4ab8`
- **Source:** owner-provided local ISO; not committed
- **Filename:** `God of War II (USA).iso`
- **Product code:** `SCUS_974.81`
- **Volume ID:** `GODOFWAR2`
- **ISO size:** 8,533,671,936 bytes
- **ISO size mod 2048:** 0
- **Sector count:** 4,166,832
- **ISO SHA-256:** `266b08b7823c569be205dc9377b0e2212fbcb9080c4d65029f15040ae62d9f98`
- **Logical block size:** 2048
- **Volume space blocks:** 2,083,888
- **Volume space relation:** smaller than the file sector count by 2,082,944 sectors (4,265,869,312 bytes)
- **SYSTEM.CNF path:** `SYSTEM.CNF;1`
- **SYSTEM.CNF size:** 57 bytes
- **BOOT2 target:** `SCUS_974.81;1`
- **Boot executable:** `SCUS_974.81;1`
- **Boot executable size:** 2,125,688 bytes
- **Boot size vs 4 MiB cap:** 2,068,616 bytes below the 4,194,304-byte default materialization cap
- **Directory survey:** 1 directory (root), 15 files, max depth 0; 0 multi-extent records; 0 interleaved records; 0 skipped unsupported directories
- **Highest file extent end:** 4,267,769,856 bytes; 32,768 bytes below the volume-space end and 4,265,902,080 bytes below the file end
- **Largest file size:** 4,264,382,464 bytes
- **Warnings:** none
- **Outcome:** `INSPECTED`

## What was tested

- Read-only inspection and metadata-only directory survey on 2026-10-22.
- The inspector resolved `SYSTEM.CNF`, the `BOOT2` target and the boot executable size.
- No files were extracted or modified; no executable was run.

## What is not tested

- Boot, native runtime, recompilation or gameplay.
- ELF layout, dependencies or executable contents beyond the existing inspector metadata pass.
- The second layer or any data outside the PVD volume space.
- Other regions, revisions or disc layouts; compatibility is not established.

## Known limitations and blockers

- The PVD volume space is smaller than the image file. **Dugaan:** the image is dual-layer and the PVD describes only the first layer; this is unverified.
- The directory survey covers only the PVD-addressable space.
- This record is one authorized sample, not evidence of broad ISO or game compatibility.
- No safe extraction boundary or loader exists.
- Formal Gate 0 review and the ADR-0003 clean-room prerequisites remain owner-controlled.

## Next safe action

1. Keep this record updated if the image or inspector changes.
2. Do not extract, execute or assume support for the second layer without an owner-approved plan.
3. Record additional authorized layouts without generalizing from this sample.
