# RPTP minimal IR and control-flow contract

- **Status date:** 2026-10-23
- **Scope:** synthetic ELF32/EM_MIPS input and the currently supported instruction subset only.
- **Status:** Gate 3 remains in progress. This is not a product recompiler, a complete R5900 model, a function-boundary recovery pass, a runtime, or a compatibility claim.
- **Implementation:** `tools/rptp_ir.py`
- **Tests:** `tests/test_ir_cfg.py`

## Purpose

This increment separates three concerns that were previously implicit in the Gate 0 spike:

1. decoding a supported synthetic instruction into an explicit IR instruction;
2. partitioning the validated synthetic code range into deterministic basic blocks; and
3. reporting provisional function-entry candidates without claiming function extents or reachability.

The existing Gate 0 differential spike and ORI differential remain the execution and native-generation path. The IR module does not execute code and does not emit C++.

## IR contract

Each `IRInstruction` retains the instruction address, raw 32-bit word, normalized operation name, register operands, immediate value and immediate encoding kind, control-flow classification, direct target, modeled destination register, and delay-slot ownership.

The supported control-flow classifications are:

| Value | Meaning |
|---|---|
| `fallthrough` | Ordinary instruction; the next instruction follows unless this is a delay slot. |
| `conditional_branch` | `BEQ` or `BNE`; both a direct target and a fallthrough exist. |
| `direct_jump` | `J`; the direct target is the next control destination. |
| `direct_call` | `JAL`; the direct target is also a function-entry candidate, and the modeled destination register is `$ra`. |
| `indirect_jump` | `JR` of a register other than `$ra`; the dynamic target is not guessed. |
| `return_candidate` | `JR $ra`; recorded as a return candidate, not as a proven function return. |

Immediate semantics are explicit:

| Kind | Instructions | Meaning |
|---|---|---|
| `signed16` | `ADDIU`, `LW`, `SW`, `BEQ`, `BNE` | The 16-bit field is sign-extended for the existing synthetic semantic model. |
| `zero16` | `ORI` | The 16-bit field is zero-extended. |

The raw word is kept even when the normalized fields are sufficient. A destination of `None` means the modeled instruction does not write an architectural register in this subset; this includes writes to `$zero` and non-writing instructions such as `SW`.

`delay_slot_for` is set on the delay-slot instruction and names the transfer that owns it. A transfer block contains the transfer and its delay slot exactly once. A delay slot is never emitted as an independent block entry.

## Basic-block discovery

`analyze_words` and `analyze_elf` validate a contiguous, 4-byte-aligned synthetic code range. Block starts are derived from:

- the first instruction in the validated range;
- the ELF entry point;
- direct branch, jump, and call targets;
- conditional fallthrough;
- the instruction after a transfer's delay slot, which partitions the remaining code range.

The partition covers every instruction in the range exactly once. **A block start is not a reachability or function-boundary claim.** Unreachable bytes still belong to a syntactic block so that coverage and overlap can be checked.

Successors are deterministic:

- conditional branch: target first, then fallthrough;
- direct jump or call: the direct target;
- indirect jump or return candidate: no statically guessed successor;
- ordinary block ending before another block: the next partition start;
- block ending at the range end: no successor.

The call target of a `JAL` is represented as a function-entry candidate. The instruction after a call is a syntactic partition start, not proof of a return path.

## Function-entry candidates

Only two origins are reported:

1. the validated ELF entry point (`elf_entry`);
2. a validated direct `JAL` target (`jal_target`).

Each candidate is labeled `candidate` with the limitation text stored by the module. The result contains no function extent, symbol name, reachability result, or confident return-path claim. Multiple call sites are recorded for a `JAL` target so later analysis can distinguish evidence sources.

## Fail-closed validation

The analysis raises `AnalysisError` with a stable `code` and an optional address. Examples of rejected conditions include:

- invalid or truncated ELF input;
- empty, non-contiguous, unaligned, or oversized code ranges;
- an entry point outside the range or inside a delay slot;
- unsupported or malformed instruction words;
- missing delay slots and control transfers inside delay slots;
- direct targets that are out of range, unaligned, or point into a delay slot;
- conditional fallthrough outside the range;
- missing or malformed delay-slot ownership;
- overlapping or uncovered block partitions;
- unsupported or malformed control-flow structure.

The module never substitutes a plausible target for an indirect `JR`, and it never silently skips an unsupported instruction.

## Synthetic fixture

The CFG tests build a 15-instruction ELF at test time with `tools/rptp_gate0_spike.py:build_elf_from_rows`. The program contains both conditional and unconditional transfers, `J`, `JAL`, `JR $ra`, and NOP delay slots. Its expected block starts are:

```text
0x00100000
0x00100010
0x00100018
0x00100020
0x00100028
0x00100030
```

The expected function-entry candidates are the ELF entry at `0x00100000` and the `JAL` target at `0x00100030`. The tests verify deterministic bytes and analysis output. No new binary fixture is written or committed, so the fixture manifest is unchanged.

The registered Gate 0 fixture and the ORI fixture are not modified. Their fixture and generated-C++ hashes are checked by `tests/test_ir_cfg.py`.

## Limitations

- The subset is the existing synthetic ten-opcode Gate 0 subset plus `ORI`; no new instruction opcode is added by this increment.
- The CFG is a syntactic partition of the validated code range. It does not prove reachability.
- Function entries are candidates only. There are no function extents, symbols, call graphs with return edges, or confident `JR $ra` return-path claims.
- The IR is not lowered to native code, not optimized, and not executed. The existing spike remains the only differential execution path.
- No R5900 exceptions, pipeline behavior, MMIO, kernel, IOP, VU, GS, SPU2, CDVD, controller, memory-card, or timing behavior is modeled.
- No retail ELF, ISO, BIOS, or game-derived material is used by these tests.

## References and evidence

- Generic instruction encodings and MIPS naming: `RPTP-REF-001`, `RPTP-REF-002`.
- Generic ELF structure: `RPTP-REF-003`.
- Delay-slot background: `RPTP-REF-005`, used only as a secondary cross-check for the existing synthetic model.
- The block, immediate, `$zero`, and candidate rules are defined by this repository's tests and are not a hardware specification.

Local verification is recorded in [VERIFICATION_LOG.md](VERIFICATION_LOG.md). The IR/CFG tests are host-Python tests; this increment adds no native code. Native MSVC coverage remains required for the existing applicable differential tests. Hosted CI for local commits remains pending owner publication.

## Verification commands

```powershell
python -m unittest tests.test_ir_cfg -v
python -m unittest discover -s tests -v
```
