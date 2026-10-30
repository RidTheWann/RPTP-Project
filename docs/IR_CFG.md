# RPTP minimal IR, CFG and lowering contract

- **Status date:** 2026-10-31
- **Scope:** synthetic ELF32/EM_MIPS input and the currently supported instruction subset only.
- **Status:** Gate 3 remains in progress. This is not a product recompiler, a complete R5900 model, a function-boundary recovery pass, a runtime, or a compatibility claim.
- **Implementation:** `tools/rptp_ir.py`; generated-code lowering: `tools/rptp_lower.py`
- **Branch-likely and doubleword-shift implementation:** `tools/rptp/isa.py`, `tools/rptp/cfg.py`, `tools/rptp/ir.py`, `tools/rptp/oracle.py` and `tools/rptp/codegen.py`
- **Tests:** `tests/test_ir_cfg.py`; `tests/test_cfg_reachability.py`; `tests/test_ir_lowering.py`; `tests/test_instruction_logical.py`; `tests/test_instruction_logical_width.py`; `tests/test_instruction_lui.py`; `tests/test_instruction_register_logic.py`; `tests/test_instruction_nor.py`; `tests/test_instruction_slt.py`; `tests/test_instruction_sltu.py`; `tests/test_instruction_slti.py`; `tests/test_instruction_sltiu.py`; `tests/test_instruction_daddiu.py`; `tests/test_instruction_daddu.py`; `tests/test_instruction_sll.py`; `tests/test_instruction_subu.py`; `tests/test_instruction_ld_sd.py`; `tests/test_instruction_branch_likely.py`; `tests/test_instruction_dshift.py`; `tests/test_runtime_execution.py`; `tests/test_cross_path_equivalence.py`; `tests/test_pipeline_path_contract.py`; `tests/test_isa_encodings.py`

## Purpose

This increment separates five concerns that were previously implicit in the Gate 0 spike:

1. decoding a supported synthetic instruction into an explicit IR instruction;
2. partitioning the validated synthetic code range into deterministic basic blocks;
3. reporting provisional function-entry candidates without claiming function extents;
4. traversing only the CFG's already-recorded successor edges from an explicit block root; and
5. lowering a validated result to deterministic C++ for the same synthetic execution model.

The Gate 0 differential spike and the separate ORI, ANDI/XORI, LUI, SLL, register-logical AND/OR/XOR/NOR, SLT, SLTU, DADDIU, DADDU, SUBU, LD/SD and doubleword-shift differentials remain independent execution and native-generation paths. The IR module does not execute code or emit C++; `tools/rptp_lower.py` consumes the IR and emits C++. Known-edge graph traversal is static analysis, not a runtime result.

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
| `signed16` | `ADDIU`, `DADDIU`, `SLTI`, `SLTIU`, `LW`, `SW`, `LD`, `SD`, `BEQ`, `BNE` | The 16-bit field is sign-extended for the existing synthetic semantic model. `DADDIU` adds the sign-extended immediate to the modeled 64-bit source modulo 2^64 without an overflow trap; `SLTI` compares the modeled 64-bit source as signed against the sign-extended immediate; `SLTIU` compares it as unsigned against the same sign-extended immediate. |
| `zero16` | `ANDI`, `ORI`, `XORI` | The 16-bit field is zero-extended. |
| `shifted16` | `LUI` | The raw 16-bit field is shifted left 16 bits, the low 16 bits are zero, and the 32-bit result is sign-extended to the modeled 64-bit value. |
| `shift5` | `SLL` | The 5-bit `shamt` field selects a 0..31 bit left shift of the low 32 bits of `rt`; the truncated 32-bit result is sign-extended to the modeled 64-bit value. |

The raw word is kept even when the normalized fields are sufficient. A destination of `None` means the modeled instruction does not write an architectural register in this subset; this includes writes to `$zero` and non-writing instructions such as `SW` and `SD`.

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

## Known-edge graph reachability

`tools/rptp_ir.py:analyze_known_edge_reachability(result, root_pc)` validates an existing `AnalysisResult`, starts at the explicit root block, and traverses only the successor edges already stored in `BasicBlock.successors`. It does not synthesize a fallthrough, resolve an indirect `JR` target, add a call-return edge, or inspect instruction semantics to discover paths.

The root must be 4-byte aligned, inside the analysed code range, not in a delay slot, and exactly equal to a known basic-block start. A bad root raises `AnalysisError` with `IR_REACHABILITY_INVALID_ROOT`, `IR_REACHABILITY_UNALIGNED_ROOT`, `IR_REACHABILITY_ROOT_OUT_OF_RANGE`, `IR_REACHABILITY_ROOT_IN_DELAY_SLOT` or `IR_REACHABILITY_ROOT_NOT_BLOCK_START`. A malformed result or block partition raises `IR_REACHABILITY_INVALID_RESULT` or `IR_REACHABILITY_INVALID_BLOCK`; the function never partially analyses an inconsistent graph.

`KnownEdgeReachability` reports:

- the selected `root_pc`;
- `reached_block_starts` and `not_reached_block_starts`, both in deterministic block order;
- `unresolved_transfer_blocks` reached blocks whose terminator is an indirect jump or return candidate;
- `direct_call_blocks` reached blocks whose terminator is a direct call; and
- the fixed `limitations` text.

The report's `model` is `known_edge_cfg_graph`. A block in `not_reached_block_starts` is only absent from this traversal: it is not proven semantically dead, impossible to execute, or outside a function. The recorded limitation text states that unresolved indirect jumps have no successor; that a direct call has no modeled return edge, so a caller continuation can be absent even when runtime execution could return; and that the result is not runtime reachability or a function-extent claim.

## Function-entry candidates

Only two origins are reported:

1. the validated ELF entry point (`elf_entry`);
2. a validated direct `JAL` target (`jal_target`).

Each candidate is labeled `candidate` with the limitation text stored by the module. The candidate records contain no function extent, symbol name, reachability result, or confident return-path claim; the separate known-edge report does not extend those candidate records. Multiple call sites are recorded for a `JAL` target so later analysis can distinguish evidence sources.

## IR-to-C++ lowering contract

`tools/rptp_lower.py:lower_to_cpp(result, *, return_sentinel=0x7FFF0000, max_steps=128)` validates an `AnalysisResult` and emits one deterministic C++20 source string. The generated program is a PC-keyed `switch` state machine for the existing synthetic model.

- The live state contains a 64-bit register array, a word-addressed `std::map` for initialized guest memory, a trace vector, the current PC and a halt flag. The output JSON is emitted in a fixed order.
- A control transfer records a pending target. Its delay slot executes next; the pending target is applied only after that slot. Conditional branches choose the direct target or `pc + 8` in the delay-slot step.
- `$zero` is suppressed by `write_register` and cleared after every executed instruction.
- `ADDIU` and `ADDU` wrap at 32 bits and sign-extend the result; `SUBU` subtracts the low 32 bits of `rt` from the low 32 bits of `rs` modulo 2^32 and sign-extends the result without an overflow trap; `DADDU` adds the full modeled 64-bit register values modulo 2^64 without an overflow trap; `DADDIU` adds the sign-extended 16-bit immediate modulo 2^64 without trapping on integer overflow; `ANDI`, `ORI` and `XORI` apply the logical operation with the zero-extended immediate across the full modeled 64-bit register (`ORI` and `XORI` preserve upper bits of `rs`, while `ANDI` zeroes bits 16..63 of the result); `AND`, `OR`, `XOR` and `NOR` apply the bitwise operation to the full modeled 64-bit register values; `SLT` compares the sign bits and then the unsigned magnitudes of the full modeled 64-bit values to produce a signed two's-complement result of `1` or `0`; `SLTU` compares the full modeled 64-bit values as unsigned integers and writes `1` or `0`; `LUI` shifts the immediate left 16 bits and sign-extends the 32-bit result; `SLL` shifts the low 32 bits of `rt` left by the 5-bit shift amount, truncates to 32 bits and sign-extends the result; `LW` requires initialized memory and a 4-byte-aligned effective address, then sign-extends the loaded word; `SW` requires a 4-byte-aligned effective address and stores the low 32 bits; `LD` requires an 8-byte-aligned address and both words initialized, then combines the low word at the address and the high word at address + 4 without sign extension; `SD` requires an 8-byte-aligned address and writes the low and high 32-bit halves as two words; `JAL` writes `pc + 8` to `$ra`; `JR` reads its target from the runtime register.
- A direct target is emitted from the validated IR. The lowerer does not re-decode the raw word, although it requires the raw word to be present and well-formed.
- Uninitialized or unaligned `LW` throws. Unaligned `SW` throws, as do unaligned, uninitialized or partially initialized `LD` and unaligned `SD`. Generated `main` writes `LOWER_RUNTIME_ERROR: <detail>\n` to stderr and exits `2`.
- The 4-byte `LW`/`SW` requirement is an RPTP fail-closed model choice, not a claim about hardware alignment exceptions, exception delivery or timing. It matches the Python oracle and the native `rptp-run` harness; `tests/test_runtime_execution.py` checks the runtime and oracle rejections, and `tests/test_cross_path_equivalence.py` compares the aligned shared program across the oracle, generated C++ and `rptp-run`.
- A non-code dynamic PC, including the return sentinel, halts the synthetic program. This matches the oracle; it is not a hardware exception or kernel model.
- The generated source is a test artifact. It is not optimized or linked into a product runtime, and it is not a complete R5900 recompiler.

The lowerer raises `LoweringError` with a stable code: `LOWER_INVALID_RESULT`, `LOWER_UNSUPPORTED_OP`, `LOWER_MALFORMED_INSTRUCTION`, `LOWER_INVALID_CONTROL`, `LOWER_INVALID_TARGET`, `LOWER_INVALID_DELAY_SLOT`, `LOWER_INVALID_BLOCK`, `LOWER_LIMIT_EXCEEDED` or `LOWER_INVALID_OPTION`. It never substitutes a target, skips an instruction, or emits an approximation.

## Branch-likely contract (`tools/rptp` package)

The sections above describe the `tools/rptp_ir.py` / `tools/rptp_lower.py` pipeline. The newer `tools/rptp` package (decoder, CFG, host IR, oracle and C++ emitter) implements branch-likely in addition to that ordinary subset. The legacy pipeline is unchanged and does not claim these forms. [ADR-0005](DECISIONS/ADR-0005-canonical-execution-path.md) (Proposed; owner acceptance required) proposes `tools/rptp` as the canonical analysis front end, freezes the legacy pipeline and requires E1–E4 equivalence before retirement; `tests/test_path_contract.py` covers E1/E2 and `tests/test_native_legacy_equivalence.py` covers E3.

Supported forms:

- PRIMARY opcodes `0x14` `BEQL`, `0x15` `BNEL`, `0x16` `BLEZL` and `0x17` `BGTZL`.
- REGIMM `rt` values `0x02` `BLTZL`, `0x03` `BGEZL`, `0x12` `BLTZALL` and `0x13` `BGEZALL`.

Execution semantics:

1. The condition is evaluated from register state before the delay slot. Equality and inequality compare only bits 63..0 of `rs` and `rt`; less-than/greater-than tests interpret the low 64 bits as signed.
2. The direct target is `(pc + 4 + (sign_extend(imm16) << 2)) & 0xFFFFFFFF`.
3. If taken, the delay slot executes exactly once and PC becomes the direct target.
4. If not taken, the delay slot is nullified: it is not traced, does not increment the step count, and has no register, memory, HI/LO or other architectural effect. PC becomes `(pc + 8) & 0xFFFFFFFF`.
5. `BLTZALL` and `BGEZALL` write `GPR[31] = (pc + 8) & 0xFFFFFFFF` unconditionally, including when the branch is not taken. `rs = 31` is rejected fail-closed with an explicit unsupported diagnostic; the approved reference defines that case as UNPREDICTABLE, and rejecting it is an RPTP policy rather than a modelled hardware exception.
6. The condition and link write use state before the delay slot; they are not delayed or repeated by nullification.

CFG and reachability contract:

- A likely branch records both its direct target and its fallthrough as successors, target first and fallthrough second, exactly like an ordinary conditional branch.
- Nullification is execution semantics, not a static reachability filter. CFG discovery does not prune the fallthrough because a branch is likely, does not add a separate edge to the delay slot, and does not mark a likely control block unsupported merely for being likely.
- The delay slot remains part of the control block and is never an independent block start. When both successors are inside file-backed code, both are recorded and supported; an out-of-code target uses the existing target diagnostic and does not suppress a valid fallthrough successor.

IR and native lowering:

- `Control.likely` distinguishes a likely branch from an ordinary branch, while `delay_ops` remains the single attached delay slot.
- The oracle skips the delay slot on a not-taken likely branch. The generated C++ emits the delay operations, including their trace calls, inside `if (taken) { ... }`. Both select the target or `pc + 8` only after the delay phase.
- Unknown encodings remain `unknown_*`. A likely branch is never silently decoded, lowered or emitted as an ordinary branch.
- A decoded branch target of address 0 is a valid direct target. `tools/rptp/ir.py` treats a missing target as `None` and never substitutes the fallthrough for a decoded zero address; `tests/test_instruction_branch_plain.py` covers the lowering directly. This is a host-IR contract, not a hardware-address claim.

Evidence: `tests/test_instruction_branch_likely.py` covers taken and not-taken outcomes for all eight forms, register and memory delay-slot effects, `$zero`, unconditional link writes, `rs = 31` rejection, CFG successors, deterministic generated source and a native differential against the oracle. `tests/test_isa_encodings.py` checks decoding and lowering for every supported mnemonic. The encodings, PC-relative target, condition tests, take-only delay-slot execution with `NullifyCurrentInstruction()`, unconditional `GPR[31] = PC + 8` link and `rs = 31` UNPREDICTABLE restriction are cited to `RPTP-REF-015` (MIPS64 Revision 5.04 pages 75, 78, 80, 82, 84, 87, 89 and 91); the 32-bit PC masking, the low-64-bit register comparison width, trace/step accounting, `$zero` suppression, memory representation, the fail-closed `rs = 31` rejection and generated-source shape are RPTP test definitions.

## Doubleword-shift contract (`tools/rptp` package)

The `tools/rptp` package also implements the nine R5900 doubleword shift forms. The legacy pipeline is unchanged and rejects all nine. The forms are:

- Immediate forms `DSLL` (`SPECIAL` funct `0x38`), `DSLL32` (`0x3C`), `DSRL` (`0x3A`), `DSRL32` (`0x3E`), `DSRA` (`0x3B`) and `DSRA32` (`0x3F`) require `rs = 0` and shift the low 64 bits of `rt` by the 5-bit `sa` field, or by `sa + 32` for the three `32` variants.
- Variable forms `DSLLV` (`0x14`), `DSRLV` (`0x16`) and `DSRAV` (`0x17`) require `shamt = 0` and shift by `GPR[rs] & 63`.

Execution semantics:

1. Left and logical-right shifts fill with zeros; arithmetic-right shifts replicate the sign bit.
2. The result replaces the low 64 bits of `rd` and is sign-extended from bit 63 into the modeled 128-bit register pair. A write to `$zero` is discarded.
3. A nonzero reserved `rs` on an immediate form is rejected fail-closed by the canonical decoder.
4. `tools/rptp/isa.py` accepts a variable-form word whose reserved `shamt` is nonzero as supported and valid, while `runtime/src/execution.cpp` rejects it with `EXEC_UNSUPPORTED_INSTRUCTION`. This is an open E4 divergence recorded in [RISKS.md](RISKS.md); neither path silently reinterprets the word.
5. `SPECIAL` funct `0x15` is not a defined form and remains unsupported.

CFG and lowering:

- The nine forms are ordinary fallthrough instructions; they create no successors, and the existing delay-slot and block-partition rules are unchanged.
- `tools/rptp/ir.py` lowers an immediate form to a 64-bit `shift` op with `imm = sa` or `sa + 32`, and a variable form to a 64-bit `shift_var` op whose `b` field names the amount register. `tools/rptp/codegen.py` emits the 64-bit shift and `rptp::sext64`.
- The legacy `tools/rptp_ir.py`/`tools/rptp_lower.py` pipeline rejects all nine forms as unsupported; `tests/test_pipeline_path_contract.py` pins that rejection.

Evidence: `tests/test_instruction_dshift.py` covers decoding, CFG support, IR lowering, literal oracle values, deterministic generated source and a native differential against the oracle for all nine forms. `tests/test_runtime_execution.py` and `runtime/tests/runtime_tests.cpp` add the CLI-versus-oracle differential, direct C++ cases and reserved-field rejection; `tests/test_cross_path_equivalence.py` drives all nine forms through the Python oracle, generated C++ and `rptp-run`. The encodings, immediate and variable shift amounts and arithmetic sign replication are cited to `RPTP-REF-015` (MIPS64 Revision 5.04 pages 168–176); the 64-bit shift width, 128-bit register-pair sign extension, `$zero` suppression and fail-closed reserved-field rejection are RPTP test definitions.

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
- unsupported or malformed control-flow structure;
- a reachability root that is non-integer, unaligned, out of range, in a delay slot, or not a known block start; and
- a reachability result or block partition that does not match a freshly validated CFG.

The module never substitutes a plausible target for an indirect `JR`, and it never silently skips an unsupported instruction. Known-edge reachability follows only stored successors; it fails closed if a stored successor is unknown. The lowerer repeats the structural checks it needs rather than trusting an arbitrary result object: code bounds and count, instruction order, operand and immediate consistency, control class, direct targets, delay-slot ownership, exact block coverage and successor sets, and the instruction limit. Invalid lowering options are rejected separately.

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

The reachability tests build small synthetic instruction maps at test time. They independently check a linear graph, a conditional branch with both stored successors, a root other than the ELF entry, direct `J`/`JAL` targets, sorted multiple not-reached blocks, an unresolved indirect `JR`, a return candidate, the `JAL` continuation caveat, invalid roots, malformed block partitions, deterministic repeated analysis and non-mutation of `AnalysisResult`. No graph edge is added by the test fixtures.

The synthetic lowering tests build the following additional ELFs at test time:

- The main lowering fixture has 29 instructions (`0x74` bytes) and contains the ten-opcode Gate 0 subset plus `ORI`, both branch outcomes, direct and indirect control flow, delay slots, `$zero` writes, 32-bit wraparound, `ORI` zero-extension, memory load/store and an unreachable instruction. It executes 26 PCs and stops at the return sentinel. The fixture SHA-256 is `0309e92bd180203fd82f7a89d17c5c213b79515e8f2fa779803d32b62f9735b9`; the generated C++ SHA-256 is `42214b2cc462958541c7281130d5c9b8ff09f0a309195c831519f1af13e48103`.
- The dynamic-JR fixture has 13 instructions (`0x34` bytes) and returns through a runtime register target after a `JAL` to a synthetic helper. It executes 13 PCs and stops at the return sentinel. The fixture SHA-256 is `47302fd9e04428a8dd38374896c7ba4890fd9eff5dd81ffff7168b8b968b5894`; the generated C++ SHA-256 is `074d639aab7e8fe42ef76b9ab6e2c9f4b8f4356501aa6469dfcbcf1115b937d0`.
- The logical-immediate fixture has 18 instructions (`0x48` bytes) and composes `ANDI`/`XORI` with `ADDIU` and `ORI`. It covers positive and high-bit immediates, zero-extension, `$zero`, destination/source overlap, all-zero/all-one values and masking/toggling. It executes 18 PCs and stops at the return sentinel. The fixture SHA-256 is `475209a09cadcd0e95fb52f7e5a44c5001d4eee97528d3c578d011c123a74c15`; the generated C++ SHA-256 is `3a42d2ff1dfc53609330fe25838b1425f61d20fa7e54723f4f21f77616840baa`.
- The LUI fixture has 9 instructions (`0x24` bytes): five boundary immediates, one `$zero` destination, `ADDIU`, `JR $ra` and a NOP delay slot. It covers `0x0000`/`0x0001`/`0x7FFF`/`0x8000`/`0xFFFF`, shifted/sign-extended results and `$zero` suppression. It executes 9 PCs and stops at the return sentinel. The fixture SHA-256 is `e62d461c04b56905a709b59d38c6bb69f2e408890e567926cdf49a69cc8e53e3`; the generated C++ SHA-256 is `af8c7313f6a4b28bc34655aedc489743f695b8dde943ee8881ea6e4f83cdab30`.
- The register-logical fixture has 24 instructions (`0x60` bytes) and composes `AND`, `OR` and `XOR` with `LUI` and `ADDIU`. It covers upper-bit patterns, intersection/union/difference, all-zero and all-one values, `$zero` destination suppression, destination/source aliasing and distinct destinations. It executes 24 PCs and stops at the return sentinel. The fixture SHA-256 is `c1a37d766bdb6ed11630726339116d5f793239d46dccfc3da8b50ed4ab086863`; the generated C++ SHA-256 is `a23bb334efdf437d2b852f12746be1b15ce50f0c46d8a84101a7e16475f86ad7`.
- The NOR fixture has 16 instructions (`0x40` bytes) and composes `NOR` with `LUI` and `ADDIU`. It covers all-zero and all-one results, upper-bit patterns, `rs == rt`, `$zero` destination suppression, destination/source aliasing and the two distinct alias directions. It executes 16 PCs and stops at the return sentinel. The fixture SHA-256 is `21e8eb8c01844341374857cd0d866f26e476bc280c8070161f7d7c42756064f6`; the generated C++ SHA-256 is `96aeeef878ee7ec523cdf21d6ecd6f6c7022bfbda02d8329bc01be20a0eb0572`.
- The SLT fixture has 20 instructions (`0x50` bytes) and composes `SLT` with `ADDIU`, `LUI`, `JR $ra` and a NOP delay slot. It covers negative/zero, positive/negative, equality, `$zero` destination and source, both source/destination alias directions and high-bit sign patterns. It executes 20 PCs and stops at the return sentinel. The fixture SHA-256 is `9bb286bc242c7822fe8af36e25a8245d1fba75fda2cc21a94c4eee0a6b196fa3`; the generated C++ SHA-256 is `fba70199d9448267f13a95ab03e1216858dbe8f7a3a77b9858d5f7963db2b2da`.
- The SLTU fixture has 26 instructions (`0x68` bytes) and composes `SLTU` with `ADDIU`, `LUI`, `JR $ra` and a NOP delay slot. It covers equality, zero/nonzero and all-ones operands, `$zero` destination and source, both source/destination alias directions, bit-31 and bit-63 values where unsigned and signed ordering diverge. It executes 26 PCs and stops at the return sentinel. The fixture SHA-256 is `d5670163e001a2abaf6e1d7d41f97d836880be3b7af2461f4fd7624d7ea4aa21`; the generated C++ SHA-256 is `6bdeac71496ff490fd889c6315ea4dddcfe9ccfb693e90f7f081c5a02f9b49d6`.
- The LD/SD fixture has 20 instructions (`0x50` bytes) and composes `LD` and `SD` with `LUI`, `DADDIU`, `DADDU`, `ADDIU` and `LW`. It covers a sign-extended doubleword whose high word is `0xFFFFFFFF`, a positive doubleword with a zero high word, positive, negative and zero offsets, `$zero` as the load destination and as the store source, and little-endian word-pair memory. It executes 20 PCs and stops at the return sentinel. The fixture SHA-256 is `e6650f04791b7b2b37b263591156d88a771b36a6a6618708d91446120a7fedf5`; the generated C++ SHA-256 is `4aad86b4347669e3796589e1ecb5b8e49d5bf2eba2f05f6c4cd855fe4cbfc917`.

The generated native state is compared with the oracle for registers, memory, stop PC, halt flag and executed-PC trace. The SLT boundary test also emits a generated-source harness and seeds `State` directly at `INT64_MIN`/`INT64_MAX`; the SLTU oracle helper additionally checks `0`, `1`, `INT64_MIN`, `INT64_MAX` and `UINT64_MAX`, and the generated harness seeds `State` at high-bit and bit-31 divergences because the synthetic encoder cannot materialize arbitrary 64-bit constants; this exercises the generated helpers and state machine, while the encoded fixtures exercise the normal paths. A separate one-instruction fixture checks the uninitialized-load diagnostic and exit code.

The registered Gate 0 fixture and the ORI fixture are not modified. Their fixture and generated-C++ hashes are checked by `tests/test_ir_cfg.py`; the lowering tests use separate synthetic fixtures.

The SLL fixture in `tests/test_instruction_sll.py` has 17 instructions (`0x44` bytes) and composes `SLL` with `ADDIU`, `LUI`, `ORI` and a NOP delay slot. It covers shift amounts 0/1/4/16/30/31, 32-bit truncation, sign extension of bit 31, an all-ones source, `$zero` destination suppression, source/destination aliasing and a sign-extended input whose low 32 bits are shifted. It executes 17 PCs and stops at the return sentinel. The fixture SHA-256 is `94b493a323f272488f0a3c65ae5995c8454be6688e3d84f1b786d5d360ae60b7`; the generated C++ SHA-256 is `67bd09d82178668e60f73bf4c50059cc82a2a4ac28b3d2a3048c050b75ead30d`.

The DADDIU fixture in `tests/test_instruction_daddiu.py` checks positive and negative signed-32-bit boundary crossings against literal oracle and native results. It expects `0x0000000080000000` from `0x000000007FFFFFFF + 1` and `0xFFFFFFFF7FFFFFFF` from `0xFFFFFFFF80000000 - 1`. An in-memory oracle mutation using ADDIU dispatch is rejected by the strengthened fixture; production semantics remain unchanged. The separate native harness still covers full 64-bit wraparound boundaries.

## Limitations

- The separate read-only direct-evidence report in `tools/rptp_discover.py` scans every aligned word of file-backed executable `PT_LOAD` bytes and reports candidate-only entry evidence with explicit unsupported diagnostics; see [FUNCTION_DISCOVERY.md](FUNCTION_DISCOVERY.md). It does not replace this CFG contract, and it adds no reachability, code/data separation or function-extent claim here.
- The subset is the existing synthetic ten-opcode Gate 0 subset plus `ORI`, `ANDI`, `XORI`, `LUI`, `SLL`, `AND`, `OR`, `XOR`, `NOR`, `SLT`, `SLTU`, `SLTI`, `SLTIU`, `DADDIU`, `DADDU`, `SUBU`, `LD` and `SD`. The `tools/rptp` package separately adds the six ordinary branch forms, the eight branch-likely forms and the nine doubleword shift forms described above. No other opcode is added by these increments, and the legacy `tools/rptp_ir.py` pipeline does not implement these forms.
- The CFG is a syntactic partition of the validated code range. Known-edge graph reachability is not runtime reachability, dead-code proof or function discovery.
- Function entries are candidates only. There are no function extents, symbols, call graphs with return edges, or confident `JR $ra` return-path claims. The direct-call continuation caveat is explicit in the reachability report.
- The IR is lowered only for the synthetic model. The generated C++ is not optimized, not a product recompiler or runtime, and not a substitute for the separate instruction differential tests.
- A dynamic non-code PC halts the synthetic program. There is no R5900 exception, fault, pipeline, MMIO, kernel, IOP, VU, GS, SPU2, CDVD, controller, memory-card, or timing model.
- No retail ELF, ISO, BIOS, or game-derived material is used by these tests.

## References and evidence

- Generic instruction encodings and MIPS naming: `RPTP-REF-001`, `RPTP-REF-002`. `RPTP-REF-002` covers the `SLT` and `SLTU` function codes and comparison names; the modeled 64-bit widths and test behavior are RPTP definitions. `RPTP-REF-001` was not used for the `SLTU` function-code value because its current SLTU table row conflicts with `RPTP-REF-002`.
- Generic ELF structure: `RPTP-REF-003`.
- Delay-slot background: `RPTP-REF-005`, used only as a secondary cross-check for the existing synthetic model.
- Branch-likely encoding, PC-relative target, condition, take-only delay-slot execution, nullification and link rules: `RPTP-REF-015`, MIPS64 Revision 5.04 pages 75 (BEQL), 78 (BGEZALL; entry continues on p. 79), 80 (BGEZL), 82 (BGTZL), 84 (BLEZL), 87 (BLTZALL; entry continues on p. 88), 89 (BLTZL) and 91 (BNEL). The `rs = 31` UNPREDICTABLE restriction on the two link forms is implemented as an explicit fail-closed rejection, an RPTP test definition. The low-64-bit register comparison width, 32-bit PC masking, trace/step accounting, `$zero` suppression, memory representation and generated-source shape are RPTP test definitions recorded in [REFERENCES.md](REFERENCES.md).
- `LUI` shifted-immediate semantics: `RPTP-REF-013`, MIPS64 Revision 5.04 page 225. The Rev 6.03 LUI page was not directly accessible; the limitation is recorded in [REFERENCES.md](REFERENCES.md).
- `SLL` 32-bit shift encoding and semantics: `RPTP-REF-002`; the sign-extension bridge into the modeled 64-bit register array is test-defined and recorded in [REFERENCES.md](REFERENCES.md).
- `SUBU` 32-bit subtract encoding and semantics: `RPTP-REF-015`, MIPS64 Revision 5.04 page 355. That entry marks a non-word-value source UNPREDICTABLE; this model resolves that case deterministically by truncating both sources to their low 32 bits, matching the accepted `ADDU` model. The resolution is test-defined and recorded in [REFERENCES.md](REFERENCES.md).
- `DSLL`, `DSLL32`, `DSLLV`, `DSRA`, `DSRA32`, `DSRAV`, `DSRL`, `DSRL32` and `DSRLV` encodings, shift amounts and arithmetic sign replication: `RPTP-REF-015`, MIPS64 Revision 5.04 pages 168–176. The 64-bit shift width, 128-bit register-pair sign extension, `$zero` suppression and fail-closed reserved-field rejection are RPTP test definitions recorded in [REFERENCES.md](REFERENCES.md). The canonical decoder versus harness divergence on a nonzero variable-form `shamt` is recorded in [RISKS.md](RISKS.md).
- `LD`/`SD` doubleword transfer encoding and semantics: `RPTP-REF-015`, MIPS64 Revision 5.04 pages 207 and 327. The signed 16-bit offset and aligned doubleword transfer are referenced; the 32-bit effective-address truncation, the two-word little-endian memory model and the fail-closed alignment rejection are RPTP test definitions recorded in [REFERENCES.md](REFERENCES.md).
- `LW`/`SW` word transfer encodings: `RPTP-REF-001` and `RPTP-REF-002`. The 4-byte effective-address alignment requirement and its fail-closed `EXEC_MEMORY_FAULT` / `LOWER_RUNTIME_ERROR` rejection are RPTP model policies and test definitions, not a hardware alignment-exception model; the cross-path matrix is recorded in [RUNTIME.md](RUNTIME.md).
- The block, immediate, `$zero`, candidate, known-edge reachability and lowering rules are defined by this repository's tests and are not a hardware specification.
- The generated C++ state machine, JSON shape, failure text and exit code are test-defined behavior, not R5900 or PS2 hardware behavior.

Local and hosted verification evidence is recorded in [VERIFICATION_LOG.md](VERIFICATION_LOG.md). The SLTI increment (`69d7c11`) passed CI run #44; SLTIU (`25267b6`) passed run #45, DADDIU run #50, DADDU run `40836707828`, SUBU run `40849490715`, PR #49 merge `be8269e` run `40959803393`, PR #51 merge `983da0f` run `40969465394`, the PR #52 merge `ed934de` run `40971796930`, the PR #53 merge `5878814` run `41003680466`, the PR #54 merge `90e4f62` run `41005859751`, the PR #56 merge `f8f7548` run `41006977122`, the PR #57 merge `5326059` run `41008593520`, the PR #59 merges `7a2b98f` runs `41011409128`/`41009361036`, the PR #60 merge `c1f1ade` run `41012644771`, the PR #62 merge `cc85c1a` run `41123907950` and the latest merge `248aad8` (PR #63) run `41125085510` on Windows x64/MSVC and Linux/GCC. These are synthetic-model runs against the recorded references only; Gate 3 remains in progress and not passed.

## Verification commands

```powershell
python -m unittest tests.test_instruction_logical -v
python -m unittest tests.test_instruction_lui -v
python -m unittest tests.test_instruction_register_logic -v
python -m unittest tests.test_instruction_nor -v
python -m unittest tests.test_instruction_slt -v
python -m unittest tests.test_instruction_sltu -v
python -m unittest tests.test_instruction_subu -v
python -m unittest tests.test_instruction_ld_sd -v
python -m unittest tests.test_instruction_branch_likely -v
python -m unittest tests.test_instruction_dshift -v
python -m unittest tests.test_ir_cfg -v
python -m unittest tests.test_cfg_reachability -v
python -m unittest tests.test_ir_lowering -v
python -m unittest discover -s tests -v
```
