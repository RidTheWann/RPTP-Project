# Downhill Domination (USA)

- **Status:** Inspected (read-only)
- **Last updated:** 2026-10-21
- **RPTP inspector:** `tools/rptp_inspect.py` at `5d9db90` (pre-push `14e6f02`; content unchanged)
- **Source:** owner-provided local ISO; not committed
- **Filename:** `Downhill Domination (USA).iso`
- **Serial:** SCUS-97177
- **ISO size:** 2,530,869,248 bytes
- **Volume ID:** (empty in PVD)
- **Logical block size:** 2048
- **Volume space blocks:** 1,235,776
- **SYSTEM.CNF path:** `SYSTEM.CNF;1`
- **SYSTEM.CNF size:** 54 bytes
- **SYSTEM.CNF SHA-256:** `9c10d67879c4b0479a9344e54329dbe2f060f812e8f3875ead7dbe7a5b56d9bf`
- **BOOT2:** `cdrom0:\SCUS_971.77;1`
- **Boot executable:** `SCUS_971.77;1`
- **Boot executable size:** 1,691,684 bytes
- **Boot executable SHA-256:** `adfda7b73a8f05fb20a3f0f318772e9d3797fd4d6c0a6c0078ae392df0f0cf0c`
- **Boot extent:** LBA 2770, 1,691,684 bytes, flags 0, volume sequence 1
- **ELF:** ELF32, little-endian, EM_MIPS (8), ET_EXEC (2), entry `0x0010A008`, 1 PT_LOAD
- **Warnings:** none

## What was tested

- Read-only inspection on 2026-10-21 using the owner-provided local ISO.
- Result: `INSPECTED`.
- ISO 9660 primary volume descriptor, root directory, `SYSTEM.CNF`, `BOOT2` path and boot ELF metadata were parsed successfully.
- No files were extracted or modified; the ELF was not executed.

## What is not tested

- Booting the game or any PS2 runtime service.
- Recompiling the executable.
- Function discovery, R5900 semantics beyond the synthetic Gate 0 subset, VU, GS, IOP, CDVD, audio, input, memory card or timing.
- Gameplay or any compatibility claim.
- Other regions, revisions or disc layouts.

## Known limitations and blockers

- The PVD volume identifier is empty; the inspector accepts it, but it is not a game title source.
- Only one retail ISO has been inspected. This does not establish support for other ISO layouts or multi-extent files.
- No safe extraction boundary or loader exists yet.
- Formal Gate 0 review and the ADR-0003 clean-room prerequisites remain owner-controlled. Do not start runtime or recompiler expansion from this inspection alone.

## Next safe action

1. Keep this record updated if the file is re-inspected or the RPTP inspector changes.
2. Record additional owner-authorized ISO layouts before generalizing the inspector.
3. Analyze the boot ELF and dependencies only from permitted references and independent tests.
4. Do not implement or claim native boot/playability until the formal Gate 0 disposition and the relevant gate criteria are satisfied.
