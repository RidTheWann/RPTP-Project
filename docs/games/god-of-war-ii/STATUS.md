# God of War II (USA)

- **Status:** Boot analysis (static census)
- **Last updated:** 2026-10-29
- **RPTP inspector:** `tools/rptp_inspect.py`, hardened revision `0c2264e`; source SHA-256 verification and full fingerprint: [verification log](../../VERIFICATION_LOG.md)
- **Source:** owner-provided local ISO; not committed
- **Filename:** `God of War II (USA).iso`
- **Product code:** `SCUS_974.81`
- **Volume ID:** `GODOFWAR2`
- **ISO size:** 8,533,671,936 bytes
- **ISO size mod 2048:** 0
- **Sector count:** 4,166,832
- **ISO SHA-256:** `266b08b7823c569be205dc9377b0e2212fbcb9080c4d65029f15040ae62d9f98` (recomputed before and after the 2026-10-28 runs; matches the earlier record)
- **Logical block size:** 2048
- **Volume space blocks:** 2,083,888
- **Volume space bytes:** 4,267,802,624
- **Volume space relation:** smaller than the file sector count by 2,082,944 sectors (4,265,869,312 bytes); the declared volume ends at byte 4,267,802,624
- **PVD publisher / data preparer:** `SCEA INC` / `PHILW`
- **PVD volume set identifier:** `GODOFWAR2`
- **SYSTEM.CNF path:** `SYSTEM.CNF;1`
- **SYSTEM.CNF size:** 57 bytes
- **SYSTEM.CNF SHA-256:** `5e3b5adc35f6bb256a8aa1cae64694139f7d864b812795c2df99efc9215a1cef`
- **BOOT2:** `cdrom0:\SCUS_974.81;1`
- **Boot executable:** `SCUS_974.81;1`
- **Boot executable size:** 2,125,688 bytes
- **Boot executable SHA-256:** `fd403603be46dea70d130695820d28b3f31de6d7e48484a5f006398a605f7dd6`
- **Boot extent:** LBA 282, 2,125,688 bytes, flags 0, volume sequence 1
- **Boot size vs 4 MiB cap:** 2,068,616 bytes below the 4,194,304-byte default materialization cap
- **Directory survey:** 1 directory (root), 15 files, max depth 0; 0 multi-extent records; 0 interleaved records; 0 skipped unsupported directories
- **Survey extent boundary:** every reported file extent lies inside the declared volume; the highest ends 32,768 bytes before the volume-space end
- **Highest file extent end:** 4,267,769,856 bytes; 32,768 bytes below the volume-space end and 4,265,902,080 bytes below the file end
- **Largest file size:** 4,264,382,464 bytes
- **Warnings:** none
- **Outcome:** `INSPECTED`

## What was tested

### Historical runs — 2026-10-22

Historical inspectors: `d51f0e7` (re-run at `f8feb27`); whole-image SHA-256 recorded at `25b4ab8`, not recomputed in that pass.

- Read-only inspection and metadata-only directory survey on 2026-10-22 with inspector `d51f0e7`.
- A separate in-memory metadata read parsed the PVD and root directory records and reproduced the size/volume relation without using the inspector.
- The inspector resolved `SYSTEM.CNF`, the `BOOT2` target and the boot executable size.
- All 15 reported file extents fit inside the declared volume. The largest file, `PART1.PAK;1`, ends 32,768 bytes before the volume-space end.
- No files were extracted or modified; no executable was run.
- Input size and last-write time were unchanged before and after the two runs. The whole-image SHA-256 was not recomputed.

### 2026-10-28 — repeated read-only CLI and ELF metadata checks

Recorded owner-authorized local evidence from main; documentation checked against the reports below without reopening the ISO. Not CI verification.

- CLI inspect ran twice: exit 0, `INSPECTED`, no warnings, byte-identical JSON. Survey ran twice: exit 0, `SURVEYED`, no warnings, byte-identical JSON.
- Whole-image SHA-256 was actually recomputed before and after these runs, unchanged and matching the previous hash above; size and mtime were unchanged. The historical no-rehash statement applies only to the earlier pass.
- Read-only ELF load map: 1 PT_LOAD; file/virtual ranges and zero-fill metadata were reported, with PH0 zero-fill of 540,760 bytes and no memory overlaps. No loading or zero-fill execution was tested ([RPTP-REF-003](../../REFERENCES.md)).
- Entry `0x00100008` maps uniquely to PF_X file-backed bytes in program header 0 at ELF-relative file offset 4,104 bytes. Independent sparse ELF-header/entry/overlap cross-check agrees.
- The PVD/file gap remains 4,265,869,312 bytes; whole-image hashing does not classify those extra bytes or establish a second layer. The survey remains PVD-addressable only.
- Evidence: local `build/elf-retail-summary.json`, `build/elf-retail-god-of-war-ii.inspect.json`, `build/elf-retail-god-of-war-ii.survey.json` and `build/elf-retail-independent-check.json`.
- No extraction, content analysis, function discovery, boot, runtime, recompilation or compatibility testing was performed.

### 2026-10-29 — read-only boot-code census refresh

- `python tools/rptp_census.py <iso> --iso --json` completed in memory with exit 0 and status `CENSUSED`; no file was extracted, modified or executed.
- Census with the decoder after `SLL` and `DADDU`, before `SUBU` (`R-029`): 520,042 aligned words across 1 PT_LOAD segment(s); 325,561 (62.6%) accepted; 194,481 raw-unsupported words. These figures supersede the earlier pre-`DADDU` count.
- Most frequent unsupported raw encodings: `opcode_0x11` (28,957); `opcode_0x12` (23,930); `opcode_0x1e` (16,920).
- Counts include data and padding and are not a function-level, runtime, boot or compatibility measurement. See [BOOT_CENSUS.md](../../BOOT_CENSUS.md).

## What is not tested

- Boot, native runtime, recompilation or gameplay.
- ELF layout, dependencies or executable contents beyond the existing inspector metadata pass.
- The purpose, format or contents of the 4,265,869,312 bytes after the declared volume; whether they are a second layer, padding or another structure.
- Whether this image is actually dual-layer.
- Other regions, revisions or disc layouts; compatibility is not established.

## Known limitations and blockers

- ECMA-119 §9.4.9 (p. 26) defines the PVD volume-space field as the number of logical blocks in which the volume is recorded. This image declares 2,083,888 blocks, ending at byte 4,267,802,624, while the file continues to 8,533,671,936 bytes.
- The purpose of the extra bytes and any layer structure remain unverified; no inspected metadata establishes a second layer or a layer boundary.
- The directory survey covers only the PVD-addressable space. Extra image data was not treated as ISO 9660 content or inspected.
- Current tests cover a synthetic image larger than its PVD volume; no parser defect was reproduced by this sample.
- This record is one authorized sample, not evidence of broad ISO or game compatibility.
- No safe extraction boundary or loader exists.
- The narrow Gate 0 technical pass for synthetic code was recorded on 2026-10-23; it does not authorize boot, recompilation or compatibility claims for this title. ADR-0003 clean-room prerequisites and independent provenance reviews remain in force.

## Next safe action

1. Keep this record updated if the image or inspector changes.
2. Keep R-018 open until the extra image data has a standards-backed explanation.
3. Do not extract, execute or assume support for any second layer without an owner-approved plan.
4. Record additional authorized layouts without generalizing from this sample.
