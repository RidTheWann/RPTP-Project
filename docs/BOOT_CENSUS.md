# Read-only boot-code census

- **Date:** 2026-10-29
- **Tool:** `tools/rptp_census.py`
- **Status:** Inspection evidence only. The census is static metadata; it is not a loader, recompiler, runtime, compatibility result or Gate disposition.
- **References:** ELF32 `PT_LOAD` structure and file-backed/zero-fill fields follow [RPTP-REF-003](REFERENCES.md); instruction encodings accepted by the current synthetic decoder are catalogued in [INSTRUCTION_CATALOG.md](INSTRUCTION_CATALOG.md). Unsupported labels are raw encoding identifiers, not semantic claims.

## Purpose

The census answers one question without executing or extracting anything: which instruction encodings occur in the file-backed `PT_LOAD` bytes of a boot executable, and how many are accepted by the current synthetic IR decoder? It gives the runtime and recompiler work a measured priority list instead of guessing which instruction family to add next.

The census is a companion to [ISO_INSPECTOR.md](ISO_INSPECTOR.md). It reuses the inspector's validated ISO and ELF parsing, then reads the boot ELF bytes in memory. It does not write an extracted file, modify the input, launch code or infer compatibility.

## Usage

```powershell
python tools/rptp_census.py "D:\Games\your-owned-game.iso" --iso --json
python tools/rptp_census.py path\to\boot.elf --elf --json
python tools/rptp_census.py path\to\boot.elf --elf
```

`--max-boot-bytes` changes the input safety limit (default 16 MiB). The ISO path is resolved through the same `SYSTEM.CNF`/boot rules as the inspector. Exit code is `0` for a completed census and `2` for an expected error. JSON output is deterministic for the same bytes.

## Report contract

- `source`: input kind, image size, boot path/size/SHA-256, or ELF size/SHA-256.
- `elf`: entry point, machine, ELF type, load-segment metadata and entry mappings copied from the validated ELF load map.
- `census.word_count`, `zero_word_count`, `nonzero_word_count`, `unique_word_count`, `supported_word_count`, `unsupported_word_count`, `supported_ratio`, `trailing_bytes` and per-segment counts.
- `opcodes`: every label with count and `supported` flag, sorted by descending count and then label.
- `unsupported_encodings`: the same records for labels the current decoder rejects.
- `warnings`: non-fatal ELF/load observations such as overlap or a non-executable entry, plus uncounted trailing bytes.
- `limitations`: the fixed non-claims listed below.

Supported labels use the current decoder's operation names (`addiu`, `daddiu`, `nop`, ...). Unsupported labels are stable raw identifiers: `special_0xNN` for opcode 0 function fields, `regimm_0xNN` for opcode 1 `rt` fields, and `opcode_0xNN` for other primary opcodes. Those identifiers describe an encoding, not an instruction name or behavior.

## Local read-only evidence — 2026-10-29

All eight owner-authorized images were inspected and censused in memory. No file was extracted or modified; whole-image hashes were not recomputed in this run. The two San Andreas samples share the same boot executable SHA-256 and produce identical census counts, consistent with the previously recorded shared boot hash.

| Image | Boot size (bytes) | PT_LOAD | Words | Decoder-accepted | Status | Most frequent unsupported labels |
|---|---:|---:|---:|---:|---|---|
| Black (USA) | 3,371,868 | 1 | 801,120 | 406,159 (50.7%) | `CENSUSED` | `special_0x2d` 58,215; `opcode_0x11` 35,149; `opcode_0x12` 29,211 |
| Bully (USA) | 5,132,120 | 19 | 1,282,560 | 640,730 (50.0%) | `CENSUSED_WITH_WARNINGS` | `special_0x2d` 104,020; `opcode_0x11` 85,141; `opcode_0x31` 58,096 |
| Downhill Domination (USA) | 1,691,684 | 1 | 413,500 | 223,497 (54.1%) | `CENSUSED` | `special_0x2d` 31,782; `opcode_0x11` 23,903; `opcode_0x37` 16,726 |
| God of War II (USA) | 2,125,688 | 1 | 520,042 | 277,381 (53.3%) | `CENSUSED` | `special_0x2d` 40,580; `opcode_0x11` 28,957; `opcode_0x12` 23,930 |
| GTA San Andreas (Indonesian v6) | 5,684,592 | 10 | 1,420,864 | 714,339 (50.3%) | `CENSUSED_WITH_WARNINGS` | `opcode_0x11` 133,433; `special_0x2d` 91,977; `opcode_0x31` 74,361 |
| GTA San Andreas (USA v3.00) | 5,684,592 | 10 | 1,420,864 | 714,339 (50.3%) | `CENSUSED_WITH_WARNINGS` | `opcode_0x11` 133,433; `special_0x2d` 91,977; `opcode_0x31` 74,361 |
| Need for Speed - Most Wanted (v2.00) | 4,918,740 | 1 | 1,224,439 | 724,764 (59.2%) | `CENSUSED` | `special_0x2d` 111,122; `opcode_0x37` 53,806; `opcode_0x11` 49,291 |
| Resident Evil 4 (USA) | 3,096,892 | 1 | 731,082 | 376,290 (51.5%) | `CENSUSED` | `special_0x2d` 52,487; `opcode_0x11` 31,396; `opcode_0x37` 13,623 |

The warning status for Bully and both San Andreas samples comes from the previously reported `PT_LOAD` memory overlaps, not from the census counts. Raw JSON reports are local artifacts under `build/census/` and are not committed.

The counts include data, padding and embedded tables, so they are an upper-bound description of code-like words, not a function-level measurement. The ratio measures decoder coverage of those words, not runtime correctness. The consistent `special_0x2d` and `opcode_0x11`/`opcode_0x12` presence across titles is evidence for prioritization only; no instruction semantics are claimed by this document.

These figures were measured with the decoder revision before `DADDU` (`SPECIAL` funct `0x2D`) support. Once that increment is merged, `special_0x2d` words become decoder-accepted and the percentages will rise; a read-only refresh is a separate evidence increment, and the numbers above remain dated to the pre-`DADDU` revision.

## Commands and tests

```powershell
python -m unittest tests.test_boot_census -v
python -m unittest discover -s tests -v
```

`tests/test_boot_census.py` builds synthetic ELF and ISO inputs at test time. It covers supported and raw-unsupported counts, trailing bytes, deterministic output, non-mutation, the ISO in-memory path, size limits, malformed ELF rejection and CLI JSON/error behavior. No retail bytes are included in tests.

## Error codes

The census adds:

- `CENSUS_SIZE_LIMIT`: the ELF or boot executable exceeds `--max-boot-bytes`.
- `CENSUS_WORD_LIMIT`: the counted words exceed the fixed 4,194,304-word safety limit.

ISO and ELF structure errors use the existing inspector codes in [ISO_INSPECTOR.md](ISO_INSPECTOR.md#error-taxonomy).

## Limitations and non-claims

- The census reads `PT_LOAD` file-backed bytes as aligned words; it cannot tell code from data, identify functions, reconstruct basic blocks or prove reachability.
- A decoder-accepted word is not a correct semantic implementation and is not exercised by the census.
- Unsupported labels are encoding identifiers only. They do not assert an instruction name, format or hardware behavior.
- No extraction, execution, recompilation, native loading, boot or compatibility is performed or implied.
- The retail sample is eight owner-authorized images on 2026-10-29; broader disc layouts and other revisions remain unverified.
- The census does not change the read-only Gate 2 scope or the Gate 3 status.
