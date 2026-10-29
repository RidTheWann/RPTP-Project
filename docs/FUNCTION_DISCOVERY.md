# RPTP conservative function-discovery contract

- **Status date:** 2026-10-30
- **Scope:** validated ELF32/EM_MIPS `ET_EXEC` images supplied as an ELF file or as the in-memory boot executable of an ISO image.
- **Status:** Gate 3 remains in progress and is not passed. This is a read-only, static, direct-evidence report. It is not a product recompiler, a complete function-discovery pass, a function-extent claim, a dead-code proof, a runtime-reachability result or a compatibility claim.
- **Implementation:** `tools/rptp_discover.py`
- **Tests:** `tests/test_function_discovery.py`
- **Related contract:** [IR_CFG.md](IR_CFG.md)

## Purpose

This increment adds a deliberately conservative function-discovery prototype that reports only evidence visible in the validated image. It scans aligned 32-bit words in the file-backed executable `PT_LOAD` ranges with the current decoder in `tools/rptp/isa.py`, partitions those words at observed boundaries, and reports direct targets, indirect-transfer sites, unsupported encodings and candidate entry points.

The pass is intentionally not the existing trusted-seed CFG in `tools/rptp/cfg.py`. It does not propagate reachability, resolve jump tables, attach symbols, infer function extents or follow a return edge. Every candidate is labeled candidate-only.

## Read-only input contract

The tool accepts exactly one of:

```text
--elf FILE
--iso IMAGE
```

- An ELF file is opened and read only; no byte is written.
- An ISO image is opened read only and inspected with the validated `tools/rptp_inspect.py` path. The `SYSTEM.CNF` boot executable is read in memory, and only its file-backed executable segments are materialized for analysis. No file is extracted, created or modified, and there is no output directory of extracted content.
- The ELF must be ELF32, little-endian, `ET_EXEC`, `EM_MIPS (8)`, with at least one `PT_LOAD` carrying `PF_X` and at least one complete 32-bit word.
- The ELF entry point must be a 4-byte-aligned word inside exactly one scanned file-backed executable segment. An entry point in zero-fill, non-executable bytes, trailing bytes or a delay slot fails closed.
- File-backed executable word ranges must not overlap. Executable segments must be 4-byte aligned.
- Trailing 1-3 bytes after the last complete word in an executable segment are reported as a warning and are not decoded.
- The current inspector error taxonomy is propagated unchanged for malformed ELF/ISO input; discovery-specific failures use the stable `DISCOVER_*` codes below.

## Reported evidence

The report contains:

- `entry_point`: the validated ELF entry address.
- `branch_sites`: every decoded conditional or unconditional direct branch, with its direct target and `target_status`.
- `jump_sites`: every decoded direct `J`, with its direct target and `target_status`.
- `call_sites`: every decoded direct `JAL`, with its direct target and `target_status`.
- `direct_targets.branch`, `direct_targets.jump`, `direct_targets.call`: unique observed target addresses, site counts and status.
- `indirect_transfers`: every decoded `JR` or `JALR`, its register operand and an explicit `resolution: "unresolved"`. `JR $ra` is labeled `return_candidate`; no return path is proven.
- `unsupported_control`: unresolved control evidence for encodings the current decoder cannot model: unsupported `SYSCALL`/`BREAK` halts, opaque COP0 words (which could contain ERET), and any catalogued but unsupported control form.
- `unsupported_encodings`: a deterministic count summary grouped by raw encoding label.
- `diagnostics`: one explicit entry for every unsupported word, plus structural diagnostics. An unsupported word is never decoded as a known instruction and is never followed.
- `basic_blocks`: the syntactic partition of every scanned word, with `start`, `end`, `instruction_count`, `segment_index` and sorted `start_reasons`.
- `candidates`: candidate-only entry points derived only from the ELF entry and in-code direct `JAL` targets.
- `warnings`: aggregate evidence caveats such as trailing bytes, out-of-code targets, missing delay slots and transfer encodings observed inside a delay slot.
- `limitations`: the fixed non-claim text.

### Target status

Every direct branch, jump and call target is classified as one of:

| Status | Meaning |
|---|---|
| `in_code` | A 4-byte-aligned word address inside a scanned file-backed executable segment and not a delay slot. |
| `delay_slot` | Inside a scanned executable segment, but in a delay slot; it is reported and is not used as a block boundary. |
| `unaligned` | Not 4-byte aligned. |
| `executable_trailing_bytes` | In the final 1-3 bytes of an executable segment after the last complete word. |
| `file_backed_non_executable` | In file-backed bytes of a non-executable `PT_LOAD`. |
| `zero_fill` | In the zero-fill part of a `PT_LOAD`. |
| `outside_loaded_segments` | Outside every `PT_LOAD` range. |

Only `in_code` targets are followed. Other statuses remain reported as unresolved evidence and are never converted into a block boundary or candidate.

### Basic-block partition

The partition is syntactic, not semantic:

- a new block starts at each scanned segment start;
- at the ELF entry point;
- at each control instruction;
- at each unsupported word treated as opaque;
- directly after a transfer and its delay slot;
- directly after an opaque unsupported word;
- at every in-code direct branch, jump or call target.

A transfer and its delay slot stay in one block unless a target points inside the delay slot; in that case the target is diagnosed and does not split the pair. A block is not a function, a reachable region or a proven extent. The partition covers every scanned word exactly once.

## Candidate-only contract

Only two candidate origins exist:

1. `elf_entry` for the validated ELF entry point;
2. `jal_target` for a direct `JAL` target whose status is `in_code`.

Candidates are merged by address and retain sorted origins and call-site addresses. Each record has `candidate_only: true`, no name, no end address, no size, no extent, no reachability result and no return-path claim. A `JAL` target outside the scanned code is reported as an unresolved target, not as a candidate.

The absence of a candidate is not evidence that no function exists there. The presence of a candidate is not evidence that the address is a real function entry at runtime.

## Unsupported and indirect policy

- `JR` and `JALR` targets are register values and are never guessed.
- An unsupported encoding is reported with its address, raw 32-bit word, decoder mnemonic, encoding label, instruction class, validity, delay-slot position and decoder note.
- An unsupported word is treated as an opaque one-word partition boundary. The tool does not consume a following word as its delay slot, even when the catalog knows a control form with a delay slot, because the actual instruction is not supported.
- Unknown encodings are not claimed to be control transfers. `SYSCALL`/`BREAK` and opaque COP0 are additionally listed in `unsupported_control` because their control effect is known to be terminal or potentially terminal but is not modeled.
- A transfer or halt encoding inside a delay slot is diagnosed and is not processed as an independent transfer.

## Determinism

The JSON report is deterministic for the same input and options:

- lists and unique targets are sorted by numeric address or by a documented secondary key;
- dictionaries are emitted with sorted keys by the CLI;
- unsupported encoding summaries are sorted by descending count then encoding label;
- no timestamp, wall-clock value, environment value, absolute host path or absolute source path is included;
- `source.input_name` is the basename only; an ISO report also includes the disc-internal `boot_path`;
- the ELF file SHA-256 or ISO boot-executable SHA-256 is included for provenance.

## Error taxonomy and exit codes

Successful discovery exits `0`. Expected input or analysis failure exits `2` and emits `{"status":"ERROR","error_code":...,"message":...}` in JSON mode. An unexpected programming failure is not converted into a partial report.

| Code | Meaning |
|---|---|
| `DISCOVER_INPUT_NOT_FOUND` | The input path does not exist. |
| `DISCOVER_INPUT_NOT_FILE` | The input path is not a regular file. |
| `DISCOVER_INPUT_UNREADABLE` | The input could not be read. |
| `DISCOVER_SIZE_LIMIT` | The ELF file or ISO BOOT executable exceeds `--max-input-bytes`. |
| `DISCOVER_INSTRUCTION_LIMIT` | The executable word count exceeds `--max-instructions`. |
| `DISCOVER_DIAGNOSTIC_LIMIT` | Diagnostics would exceed `--max-diagnostics`; the tool fails closed instead of truncating evidence. |
| `DISCOVER_INVALID_LIMIT` | A limit option is not a positive integer. |
| `DISCOVER_UNSUPPORTED_MACHINE` | The ELF machine id is not EM_MIPS (8). |
| `DISCOVER_UNSUPPORTED_TYPE` | The ELF type is not ET_EXEC (2). |
| `DISCOVER_NO_LOAD_SEGMENTS` | The ELF has no `PT_LOAD`. |
| `DISCOVER_NO_EXECUTABLE_CODE` | No file-backed executable `PT_LOAD` has a complete 32-bit word. |
| `DISCOVER_SEGMENT_UNALIGNED` | An executable segment is not 4-byte aligned. |
| `DISCOVER_CODE_OVERLAP` | File-backed executable word ranges overlap. |
| `DISCOVER_ENTRY_UNALIGNED` | The entry point is not 4-byte aligned. |
| `DISCOVER_ENTRY_NOT_IN_CODE` | The entry point is not inside one scanned executable word range. |
| `DISCOVER_ENTRY_IN_DELAY_SLOT` | The entry point is a delay-slot word. |
| `DISCOVER_SEGMENT_READ` | A segment read did not return its declared file bytes. |
| `DISCOVER_INTERNAL_BLOCK_BOUNDARY` | Internal block partition inconsistency; fail closed. |
| `DISCOVER_INTERNAL_COUNT_MISMATCH` | Internal unsupported-count inconsistency; fail closed. |

Inspector codes such as `BOOT_EXECUTABLE_NOT_ELF`, `UNSUPPORTED_ELF_CLASS`, `UNSUPPORTED_ELF_ENDIANNESS`, `ELF_LOAD_SEGMENT_*`, `SYSTEM_CNF_*` and ISO extent errors are propagated unchanged. They are stable inspector codes, not discovery-specific codes.

## Resource limits

| CLI option | Default | Meaning |
|---|---:|---|
| `--max-input-bytes` | 16,777,216 | ELF file size or ISO BOOT executable size. The ISO image itself is streamed and is not fully materialized. |
| `--max-instructions` | 4,194,304 | Total scanned executable 32-bit words. |
| `--max-diagnostics` | 1,000,000 | Total diagnostic entries before fail-closed exit. |
| `--chunk-size` | 1,048,576 | ISO read chunk size. |

A limit is a safety bound, not a claim that an image under the bound is trustworthy or analyzable.

## Non-claims

This tool does **not** claim:

- complete function discovery, function boundaries or function extents;
- code/data separation: every aligned executable word is scanned, including data and padding;
- runtime reachability, dead-code proof, call-return edges or a call graph with return paths;
- symbol names, source signatures, ABI reconstruction or variable recovery;
- that a candidate is a real function or that a direct target is reachable;
- that unsupported bytes are data, or that unknown bytes are not control transfers;
- boot, runtime, emulation, recompilation, rendering, gameplay or game compatibility;
- R5900 semantics beyond the current synthetic decoder catalog, or any PS2 kernel, COP, VU, exception, TLB, cache or timing behavior.

A candidate list is evidence for later review, not a result to lower blindly.

## Reproduction commands

```powershell
python tools/rptp_discover.py --elf <path-to-validated.elf> --json
python tools/rptp_discover.py --iso "<path-to-authorized-image.iso>" --json
python tools/rptp_discover.py --elf <path-to-validated.elf>
python -m unittest tests.test_function_discovery -v
python tools/check_forbidden_artifacts.py --root .
```

The ISO command opens the image read only, inspects `SYSTEM.CNF`, reads the boot executable in memory and writes only the report to standard output. It does not extract a game file.

## Tests

`tests/test_function_discovery.py` uses synthetic ELF and ISO fixtures only. It covers:

- a direct-call chain and merged candidate origins;
- a loop/branch target and the syntactic block partition;
- indirect `JR` and `JALR` sites, including `JR $ra` as an unresolved return candidate;
- unsupported `SYSCALL`, `BREAK`, COP0, COP1, catalogued-but-unsupported and unknown encodings;
- unsupported and control encodings inside delay slots;
- missing delay slots;
- out-of-code and delay-slot targets;
- trailing segment bytes;
- malformed ELF inputs, stable error codes and fail-closed limits;
- deterministic JSON, read-only input handling and no artifact creation;
- an ISO boot executable read in memory with unchanged bytes and mtime;
- candidate-only records with no extent fields.

No retail ELF, ISO, BIOS or game-derived material is used by the tests.

## References and evidence

- ELF32 structure and `PT_LOAD`/entry semantics: `RPTP-REF-003` (elf(5)).
- Generic MIPS control encodings, branch/jump target formulas and register names: `RPTP-REF-001`, `RPTP-REF-002`.
- Delay-slot background: `RPTP-REF-005`, used as a secondary cross-check for the existing synthetic decoder model.
- Branch-likely catalog entries reported by the existing decoder: `RPTP-REF-015`.
- The decoder catalog, unsupported labels, block partition, target status, candidate-only policy, diagnostic shape, limits and JSON shape are RPTP test definitions. They are not a hardware specification or an independent review of R5900 semantics.

The increment does not use any emulator or recompiler implementation, issue, pull request or release note, and does not use a Sony manual. See [REFERENCES.md](REFERENCES.md) and [DECISIONS/ADR-0004-gate2-read-only-scope.md](DECISIONS/ADR-0004-gate2-read-only-scope.md).
