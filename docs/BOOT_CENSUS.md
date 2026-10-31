# Read-only boot-code census

- **Date:** 2026-10-29
- **Tool:** `tools/rptp_census.py`
- **Decoder:** `tools/rptp/isa.py`, unchanged from repository revision `0944c84e8ed11c2d7db5d54ad23671b9a8de869d` at measurement time; 142 supported mnemonics; supported-mnemonic set SHA-256 `ddc255931fb49ecb0c8bc778037344e2e05ac32d8898fd77586db3162c904e13`. This is the decoder/catalog supported set, not the smaller synthetic tested subset in [INSTRUCTION_CATALOG.md](INSTRUCTION_CATALOG.md).
- **Decoder note (2026-10-31):** the current decoder declares 146 supported mnemonics after the four COP1 transfer forms `LWC1`/`SWC1`/`MFC1`/`MTC1` were added under `RPTP-REF-015`. The 2026-10-29 table below was measured with the 142-mnemonic set and was not re-measured, so its accepted counts and ratios are a lower bound relative to today's decoder; the `opcode_0x11`, `opcode_0x31` and `opcode_0x39` label counts are unchanged because those labels were unsupported at measurement time.
- **Status:** Inspection evidence only. The census is static metadata; it is not a loader, recompiler, runtime, compatibility result or Gate disposition.
- **References:** ELF32 `PT_LOAD` structure and file-backed/zero-fill fields follow [RPTP-REF-003](REFERENCES.md); instruction encodings accepted by the current decoder are catalogued in [INSTRUCTION_CATALOG.md](INSTRUCTION_CATALOG.md) and [IR_CFG.md](IR_CFG.md). Unsupported labels are raw encoding identifiers, not semantic claims.

## Purpose

The census answers one question without executing or extracting anything: which instruction encodings occur in the file-backed `PT_LOAD` bytes of a boot executable, and how many are accepted by the current R5900 decoder? It gives the runtime and recompiler work a measured priority list instead of guessing which instruction family to add next.

The census is a companion to [ISO_INSPECTOR.md](ISO_INSPECTOR.md). It reuses the inspector's validated ISO and ELF parsing, then reads the boot ELF bytes in memory. It does not write an extracted file, modify the input, launch code or infer compatibility.

## Usage

```powershell
python tools/rptp_census.py "D:\Games\your-owned-game.iso" --iso --json
python tools/rptp_census.py path\to\boot.elf --elf --json
python tools/rptp_census.py path\to\boot.elf --elf
```

`--max-boot-bytes` changes the input safety limit (default 16 MiB). The ISO path is resolved through the same `SYSTEM.CNF`/boot rules as the inspector. Exit code is `0` for a completed census and `2` for an expected error. JSON output is deterministic for the same bytes.

## Report contract

- `decoder`: the decoder module path, its supported-mnemonic count and the SHA-256 of the newline-joined, sorted supported-mnemonic set. These values identify the decoder state without a timestamp or a host path.
- `source`: input kind, image size, boot path/size/SHA-256, or ELF size/SHA-256.
- `elf`: entry point, machine, ELF type, load-segment metadata and entry mappings copied from the validated ELF load map.
- `census.word_count`, `zero_word_count`, `nonzero_word_count`, `unique_word_count`, `supported_word_count`, `unsupported_word_count`, `supported_ratio`, `trailing_bytes` and per-segment counts.
- `opcodes`: every label with count and `supported` flag, sorted by descending count and then label.
- `unsupported_encodings`: the same records for labels the current decoder rejects.
- `warnings`: non-fatal ELF/load observations such as overlap or a non-executable entry, plus uncounted trailing bytes.
- `limitations`: the fixed non-claims listed below.

Supported labels use the current decoder's operation names (`addiu`, `daddiu`, `daddu`, `beql`, `ld`, `sd`, ...). Unsupported labels are stable raw identifiers: `special_0xNN` for opcode 0 function fields, `regimm_0xNN` for opcode 1 `rt` fields, and `opcode_0xNN` for other primary opcodes. Those identifiers describe an encoding, not an instruction name or behavior.

## Local read-only evidence — 2026-10-29, current decoder

All eight owner-authorized images were inspected and censused in memory. Whole-image SHA-256, file size and mtime were measured before and after the census runs and were unchanged for every image. No file was extracted or modified.

### Input identity

| Image | ISO size (bytes) | ISO mtime (UTC) | Whole-image SHA-256 | Boot executable | Boot size (bytes) | Boot SHA-256 |
|---|---:|---|---|---|---:|---|
| Black (USA) | 3,919,609,856 | 1996-12-24T16:32:00Z | `65768cade88bfbaf566b67a3ef7a0bda5a9669779833914ffe7cd73a3e45cccd` | `SLUS_213.76;1` | 3,371,868 | `141b05209570458af9c8e27ab1911f258da6353909d813cd572df026254ffe4c` |
| Bully (USA) | 4,636,835,840 | 2026-10-21T19:07:41Z | `6c95edf7803aa79fdc816295cf2e03066599a6693f7d543fbcdb78d1d1128d5e` | `SLUS_212.69;1` | 5,132,120 | `597d7816d922cf371d757e653368488c1983f95dcdea0dd70a733650727f52fc` |
| Downhill Domination (USA) | 2,530,869,248 | 1996-12-24T16:32:00Z | `0fe2b77713d3440cc3030741ea0b18f49e3feaa09671a30a421e0d4888a7eb86` | `SCUS_971.77;1` | 1,691,684 | `adfda7b73a8f05fb20a3f0f318772e9d3797fd4d6c0a6c0078ae392df0f0cf0c` |
| God of War II (USA) | 8,533,671,936 | 1996-12-24T16:32:00Z | `266b08b7823c569be205dc9377b0e2212fbcb9080c4d65029f15040ae62d9f98` | `SCUS_974.81;1` | 2,125,688 | `fd403603be46dea70d130695820d28b3f31de6d7e48484a5f006398a605f7dd6` |
| Grand Theft Auto - San Andreas (Indonesian v6) | 3,866,394,624 | 2021-06-07T13:47:27Z | `4a00e35c7b4e1dd56a6f255cba4eb7e0f5aa7a175c2c3aff9b1e3c4f90e6304f` | `SLUS_209.46;1` | 5,684,592 | `84d4980a1253c5490ebbd039ef17384af875de75636a21f3451951093e8fc789` |
| Grand Theft Auto - San Andreas (USA) (v3.00) | 4,517,036,032 | 2026-10-21T19:09:11Z | `c94e9b16ffab9ab04dbf15109e8716a2bf0a853a246bd3d2641bf354a5068e6d` | `SLUS_209.46;1` | 5,684,592 | `84d4980a1253c5490ebbd039ef17384af875de75636a21f3451951093e8fc789` |
| Need for Speed - Most Wanted (USA) (v2.00) | 3,702,456,320 | 1996-12-24T16:32:00Z | `b2286fb3067351323fef17e006f7715f23b5cbf5bfd7be6aad406176e3e759d2` | `SLUS_212.67;1` | 4,918,740 | `aa58f301c7215ab2885ab93dff68de9cb66371a139977e53d0c1b181a61bad14` |
| Resident Evil 4 (USA) | 4,435,836,928 | 1996-12-24T16:32:00Z | `eb0874cf29dc48c994fd183e52a3b186b47b0a341281a0c2db24a1f18757cb66` | `SLUS_211.34;1` | 3,096,892 | `465d144f526603d0dcc35ad1fdb4e82cc3a1481c22289f321482cc910fb9f1ad` |

### Census results

| Image | PT_LOAD | Aligned words | Decoder-accepted | Accepted share | Raw-unsupported | Zero words | Status | Most frequent unsupported labels |
|---|---:|---:|---:|---:|---:|---:|---|---|
| Black (USA) | 1 | 801,120 | 645,758 | 80.61% | 155,362 | 46,773 | `CENSUSED` | `opcode_0x11` 35,149; `opcode_0x12` 29,211; `opcode_0x31` 13,385 |
| Bully (USA) | 19 | 1,282,560 | 1,030,256 | 80.33% | 252,304 | 100,907 | `CENSUSED_WITH_WARNINGS` | `opcode_0x11` 85,141; `opcode_0x31` 58,096; `opcode_0x39` 34,483 |
| Downhill Domination (USA) | 1 | 413,500 | 338,288 | 81.81% | 75,212 | 29,124 | `CENSUSED` | `opcode_0x11` 23,903; `opcode_0x31` 9,381; `opcode_0x39` 7,081 |
| God of War II (USA) | 1 | 520,042 | 423,583 | 81.45% | 96,459 | 29,000 | `CENSUSED` | `opcode_0x11` 28,957; `opcode_0x12` 23,930; `opcode_0x3e` 8,219 |
| Grand Theft Auto - San Andreas (Indonesian v6) | 10 | 1,420,864 | 1,093,442 | 76.96% | 327,422 | 135,850 | `CENSUSED_WITH_WARNINGS` | `opcode_0x11` 133,433; `opcode_0x31` 74,361; `opcode_0x39` 45,517 |
| Grand Theft Auto - San Andreas (USA) (v3.00) | 10 | 1,420,864 | 1,093,442 | 76.96% | 327,422 | 135,850 | `CENSUSED_WITH_WARNINGS` | `opcode_0x11` 133,433; `opcode_0x31` 74,361; `opcode_0x39` 45,517 |
| Need for Speed - Most Wanted (USA) (v2.00) | 1 | 1,224,439 | 1,056,658 | 86.30% | 167,781 | 165,090 | `CENSUSED` | `opcode_0x11` 49,291; `opcode_0x31` 18,591; `opcode_0x39` 16,594 |
| Resident Evil 4 (USA) | 1 | 731,082 | 588,952 | 80.56% | 142,130 | 104,648 | `CENSUSED` | `opcode_0x11` 31,396; `opcode_0x31` 12,352; `opcode_0x39` 10,017 |

The warning status for Bully and both San Andreas samples comes from the previously reported `PT_LOAD` memory overlaps, not from the census counts. Both San Andreas samples share the same boot executable SHA-256 and produce identical census counts, consistent with the previously recorded shared boot hash. Raw JSON reports are local artifacts under `build/census/` and are not committed.

The counts include data, padding and embedded tables, so they are an upper-bound description of code-like words, not a function-level measurement. The ratio measures decoder coverage of those words, not runtime correctness. The consistent `opcode_0x11`, `opcode_0x31` and `opcode_0x39` presence across titles is evidence for prioritization only; no instruction semantics are claimed by this document.

This table is the first eight-image census measured with the current `tools/rptp` decoder, which adds branch-likely forms and `LD`/`SD` beyond the earlier legacy pipeline. It supersedes the pre-`SUBU` 58.3%–69.2% table and the later one-image 63.03% Downhill Domination figure; those rows were not interpolated or reused. The wider decoder raises the observed range to 76.96%–86.30%, but the change is decoder acceptance, not a runtime result. The data/padding caveat above still applies.

### Determinism and non-mutation

- Downhill Domination (USA) was censused three times with the same command; the JSON reports were byte-identical, including the decoder identity fields.
- Whole-image SHA-256, file size and mtime were identical before and after the census for all eight images.
- No file was extracted, written or executed during the measurement.

## Commands and tests

```powershell
python -m unittest tests.test_boot_census -v
python -m unittest discover -s tests -v
```

`tests/test_boot_census.py` builds synthetic ELF and ISO inputs at test time. It covers supported and raw-unsupported counts, branch-likely acceptance, decoder identity, trailing bytes, deterministic output, non-mutation, the ISO in-memory path, size limits, malformed ELF rejection and CLI JSON/error behavior. No retail bytes are included in tests.

## Error codes

The census adds:

- `CENSUS_SIZE_LIMIT`: the ELF or boot executable exceeds `--max-boot-bytes`.
- `CENSUS_WORD_LIMIT`: the counted words exceed the fixed 4,194,304-word safety limit.

ISO and ELF structure errors use the existing inspector codes in [ISO_INSPECTOR.md](ISO_INSPECTOR.md#error-taxonomy).

## Limitations and non-claims

- The census reads `PT_LOAD` file-backed bytes as aligned words; it cannot tell code from data, identify functions, reconstruct basic blocks or prove reachability.
- A decoder-accepted word is not a correct semantic implementation and is not exercised by the census.
- Accepted words include every mnemonic in the decoder's supported set regardless of that entry's per-instruction verification label, including provisional and manual-cross-checked entries whose R5900 citations are not owner-approved. Acceptance is neither a provenance nor a semantics claim.
- Unsupported labels are encoding identifiers only. They do not assert an instruction name, format or hardware behavior.
- No extraction, execution, recompilation, native loading, boot or compatibility is performed or implied.
- The retail sample is eight owner-authorized images on 2026-10-29; broader disc layouts and other revisions remain unverified.
- The census does not change the read-only Gate 2 scope or the Gate 3 status.
