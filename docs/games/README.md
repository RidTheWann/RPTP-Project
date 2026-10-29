# Game work records

Every game RPTP works on gets a folder under `docs/games/` and a `STATUS.md` file. The record must be created or updated whenever inspection, analysis, recompilation or runtime work is done on that game.

This is a work log, not a compatibility claim. An inspected ISO is not a bootable port, and a boot analysis is not playable gameplay.

## Rules

1. Create `docs/games/<lowercase-hyphen-slug>/STATUS.md`.
2. Record the title, region, serial, source availability, inspection date and current phase.
3. Update the index below and the game's `STATUS.md` in the same session as the work.
4. Keep claims proportional to evidence: `Inspected`, `Boot analysis`, `Runtime bring-up` and `Playable (tested)` are different states.
5. Never commit an ISO, BIOS, game executable, extracted asset or other proprietary game data.
6. Metadata is allowed: file name, size, volume/boot metadata and SHA-256 fingerprints. Do not record a personal absolute path.
7. Do not use sealed projects as references. Follow [ADR-0003](../DECISIONS/ADR-0003-sealed-source-clean-room-policy.md).
8. If a game is blocked, record the blocker and the next safe action instead of silently stopping.

## Status ladder

- **Not inspected:** a record exists but no read-only inspection has been recorded.
- **Inspected (read-only):** `rptp_inspect.py` completed and produced metadata.
- **Boot analysis:** boot path, ELF layout and dependencies are being analyzed. No native execution yet.
- **Runtime bring-up:** partial native execution exists; not playable.
- **Playable (tested):** repeatable gameplay is demonstrated and evidence is recorded. This status is never inferred from inspection.
- **Blocked:** the next step needs an owner decision or a missing dependency.

## Index

| Game | Region | Status | Last updated | Record |
|---|---|---|---|---|
| Black | USA | Boot analysis (static census) | 2026-10-29 | [black](black/STATUS.md) |
| Bully | USA | Boot analysis (static census) | 2026-10-29 | [bully](bully/STATUS.md) |
| Downhill Domination | USA | Boot analysis (static census) | 2026-10-29 | [downhill-domination](downhill-domination/STATUS.md) |
| God of War II | USA | Boot analysis (static census) | 2026-10-29 | [god-of-war-ii](god-of-war-ii/STATUS.md) |
| Grand Theft Auto - San Andreas (USA) — owner-described original | USA | Boot analysis (static census) | 2026-10-29 | [grand-theft-auto-san-andreas-usa-v300](grand-theft-auto-san-andreas-usa-v300/STATUS.md) |
| Grand Theft Auto - San Andreas (USA) — owner-described Indonesian-language mod | USA | Boot analysis (static census) | 2026-10-29 | [grand-theft-auto-san-andreas-indonesian-v6](grand-theft-auto-san-andreas-indonesian-v6/STATUS.md) |
| Need for Speed - Most Wanted (v2.00) | USA | Boot analysis (static census) | 2026-10-29 | [need-for-speed-most-wanted](need-for-speed-most-wanted/STATUS.md) |
| Resident Evil 4 | USA | Boot analysis (static census) | 2026-10-29 | [resident-evil-4](resident-evil-4/STATUS.md) |

**Recorded local evidence — 2026-10-28:** Bully and both San Andreas samples returned `INSPECTED_WITH_WARNINGS` for PT_LOAD memory overlaps; the other five returned `INSPECTED` without warnings. All eight surveys returned `SURVEYED` without warnings; every CLI run exited 0. Overlap is metadata, not evidence of corrupt/unsupported discs or compatibility; loading precedence remains undefined and unevaluated. Inspect/survey JSON was byte-identical across two runs per image. Whole-image SHA-256 before/after matched prior records, with size/mtime unchanged; God of War II was rehashed this time.

Inspector: `tools/rptp_inspect.py`, hardened revision `0c2264e`; source verification/full fingerprint: [VERIFICATION_LOG.md](../VERIFICATION_LOG.md). Per-game sections cite the local summary, inspect/survey and independent sparse ELF cross-check reports; documentation was checked without reopening discs. Load maps/zero-fill are metadata only ([RPTP-REF-003](../REFERENCES.md)). No extraction, content analysis, function discovery, boot, runtime, recompilation or compatibility was tested. Not CI verification; this paragraph records inspection evidence, and the census paragraph below adds static word counts only.

**Read-only boot-code census — 2026-10-29, current decoder:** all eight authorized boot executables were censused in memory with `tools/rptp_census.py` and the current `tools/rptp/isa.py` decoder (142 supported mnemonics, set SHA-256 `ddc255931fb49ecb0c8bc778037344e2e05ac32d8898fd77586db3162c904e13`), which includes branch-likely forms and `LD`/`SD`. Decoder-accepted word ratios range from 76.96% to 86.30% of file-backed PT_LOAD words; the counts include data and padding and are not a function-level measurement. This table supersedes the earlier pre-`SUBU` 58.3%–69.2% rows and the one-image 63.03% Downhill Domination figure; it is a decoder-acceptance change, not a runtime result. Whole-image SHA-256, size and mtime were unchanged before and after for every image; Downhill Domination JSON was byte-identical across three runs. The most frequent raw-unsupported encodings across the sample are `opcode_0x11`, `opcode_0x31` and `opcode_0x39`, recorded per title in each STATUS.md. No file was extracted or executed; no compatibility is inferred. Method and limitations: [BOOT_CENSUS.md](../BOOT_CENSUS.md).

**Owner-provided provenance:** the two GTA San Andreas USA records are separate samples. The owner describes one as the original (unmodified) sample and the other as an Indonesian-language mod. This distinction is declarative owner information, not a technical classification. Equal boot or `SYSTEM.CNF` hashes do not establish file equality or identify the modification; whole-image hashes and PVD identifiers are recorded in each record.

## STATUS.md template

```markdown
# <Game title> (<region>)

- **Status:** Not inspected | Inspected (read-only) | Boot analysis | Runtime bring-up | Playable (tested) | Blocked
- **Last updated:** YYYY-MM-DD
- **Sample provenance:** <owner-provided classification, if applicable>
- **RPTP inspector:** <tool and revision>
- **Source:** owner-provided local ISO; not committed
- **Filename:** <filename only>
- **Serial:** <serial, if known>
- **ISO size:** <bytes>
- **Volume ID:** <value or "(empty in PVD)">
- **SYSTEM.CNF / BOOT2:** <paths and sizes>
- **Boot executable:** <path, size, ELF metadata>
- **Fingerprints:** <SYSTEM.CNF and boot executable SHA-256>
- **Warnings:** <none or list>

## What was tested

## What is not tested

## Known limitations and blockers

## Next safe action
```
