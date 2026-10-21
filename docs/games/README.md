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
| Black | USA | Inspected (read-only) | 2026-10-22 | [black](black/STATUS.md) |
| Bully | USA | Inspected (read-only) | 2026-10-22 | [bully](bully/STATUS.md) |
| Downhill Domination | USA | Inspected (read-only) | 2026-10-22 | [downhill-domination](downhill-domination/STATUS.md) |
| God of War II | USA | Inspected (read-only) | 2026-10-22 | [god-of-war-ii](god-of-war-ii/STATUS.md) |
| Grand Theft Auto - San Andreas (USA) — owner-described original | USA | Inspected (read-only) | 2026-10-22 | [grand-theft-auto-san-andreas-usa-v300](grand-theft-auto-san-andreas-usa-v300/STATUS.md) |
| Grand Theft Auto - San Andreas (USA) — owner-described Indonesian-language mod | USA | Inspected (read-only) | 2026-10-22 | [grand-theft-auto-san-andreas-indonesian-v6](grand-theft-auto-san-andreas-indonesian-v6/STATUS.md) |
| Need for Speed - Most Wanted (v2.00) | USA | Inspected (read-only) | 2026-10-22 | [need-for-speed-most-wanted](need-for-speed-most-wanted/STATUS.md) |
| Resident Evil 4 | USA | Inspected (read-only) | 2026-10-22 | [resident-evil-4](resident-evil-4/STATUS.md) |

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
