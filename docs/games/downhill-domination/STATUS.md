# Downhill Domination (USA)

- **Status:** Inspected (read-only)
- **Last updated:** 2026-10-28
- **RPTP inspector:** `tools/rptp_inspect.py`, hardened revision `0c2264e`; source SHA-256 verification and full fingerprint: [verification log](../../VERIFICATION_LOG.md)
- **Source:** owner-provided local ISO; not committed
- **Filename:** `Downhill Domination (USA).iso`
- **Serial:** SCUS-97177
- **ISO size:** 2,530,869,248 bytes
- **ISO size mod 2048:** 0
- **Sector count:** 1,235,776
- **ISO SHA-256:** `0fe2b77713d3440cc3030741ea0b18f49e3feaa09671a30a421e0d4888a7eb86`
- **Volume ID:** (empty in PVD)
- **Logical block size:** 2048
- **Volume space blocks:** 1,235,776
- **Volume space relation:** equal to the file sector count (0 bytes difference)
- **SYSTEM.CNF path:** `SYSTEM.CNF;1`
- **SYSTEM.CNF size:** 54 bytes
- **SYSTEM.CNF SHA-256:** `9c10d67879c4b0479a9344e54329dbe2f060f812e8f3875ead7dbe7a5b56d9bf`
- **BOOT2:** `cdrom0:\SCUS_971.77;1`
- **Boot executable:** `SCUS_971.77;1`
- **Boot executable size:** 1,691,684 bytes
- **Boot executable SHA-256:** `adfda7b73a8f05fb20a3f0f318772e9d3797fd4d6c0a6c0078ae392df0f0cf0c`
- **Boot extent:** LBA 2770, 1,691,684 bytes, flags 0, volume sequence 1
- **Boot size vs 4 MiB cap:** 2,502,620 bytes below the 4,194,304-byte default materialization cap
- **Directory survey:** 15 directories (14 non-root directory records), 2,338 files, max depth 1; 0 multi-extent records; 0 interleaved records; 0 skipped unsupported directories
- **Highest file extent end:** 2,530,839,544 bytes; 29,704 bytes below the volume-space end and file end
- **Largest file size:** 109,658,116 bytes
- **ELF:** ELF32, little-endian, EM_MIPS (8), ET_EXEC (2), entry `0x0010A008`, 1 PT_LOAD
- **Warnings:** none
- **Outcome:** `INSPECTED`

## What was tested

### Historical runs — 2026-10-21/22

Historical inspector: `25b4ab8` (initial record at `5d9db90`; pre-push `14e6f02`).

- Read-only inspection and metadata-only directory survey on 2026-10-22; initial inspection was on 2026-10-21.
- Result: `INSPECTED`.
- ISO 9660 primary volume descriptor, root directory, `SYSTEM.CNF`, `BOOT2` path and boot ELF metadata were parsed successfully.
- No files were extracted or modified; the ELF was not executed.

### 2026-10-28 — repeated read-only CLI and ELF metadata checks

Recorded owner-authorized local evidence from main; documentation checked against the reports below without reopening the ISO. Not CI verification.

- CLI inspect ran twice: exit 0, `INSPECTED`, no warnings, byte-identical JSON. Survey ran twice: exit 0, `SURVEYED`, no warnings, byte-identical JSON.
- Whole-image SHA-256 was recomputed before and after these runs, unchanged and matching the previous hash above; size and mtime were unchanged.
- Read-only ELF load map: 1 PT_LOAD; file/virtual ranges and zero-fill metadata were reported, with PH0 zero-fill of 6,301,456 bytes and no memory overlaps. No loading or zero-fill execution was tested ([RPTP-REF-003](../../REFERENCES.md)).
- Entry `0x0010A008` maps uniquely to PF_X file-backed bytes in program header 0 at ELF-relative file offset 4,104 bytes. Independent sparse ELF-header/entry/overlap cross-check agrees.
- Evidence: local `build/elf-retail-summary.json`, `build/elf-retail-downhill-domination.inspect.json`, `build/elf-retail-downhill-domination.survey.json` and `build/elf-retail-independent-check.json`.
- No extraction, content analysis, function discovery, boot, runtime, recompilation or compatibility testing was performed.

## What is not tested

- Booting the game or any PS2 runtime service.
- Recompiling the executable.
- Function discovery, R5900 semantics beyond the synthetic Gate 0 subset, VU, GS, IOP, CDVD, audio, input, memory card or timing.
- Gameplay or any compatibility claim.
- Other regions, revisions or disc layouts.

## Known limitations and blockers

- The PVD volume identifier is empty; the inspector accepts it, but it is not a game title source.
- The current retail sample includes other authorized titles, but broad ISO-layout and game compatibility remain unverified.
- No safe extraction boundary or loader exists yet.
- The narrow Gate 0 technical pass for synthetic code was recorded on 2026-10-23; it does not authorize boot, recompilation or compatibility claims for this title. ADR-0003 clean-room prerequisites and independent provenance reviews remain in force. Do not start runtime or recompiler expansion from this inspection alone.

## Next safe action

1. Keep this record updated if the file is re-inspected or the RPTP inspector changes.
2. Record further owner-authorized ISO layouts before generalizing the inspector.
3. Analyze the boot ELF and dependencies only from permitted references and independent tests.
4. Do not implement or claim native boot/playability until the relevant gate criteria and independent provenance requirements are satisfied.
