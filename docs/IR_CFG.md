# RPTP minimal IR, CFG and lowering contract

- **Status date:** 2026-10-28
- **Scope:** synthetic ELF32/EM_MIPS input and the currently supported instruction subset only.
- **Status:** Gate 3 remains in progress. This is not a product recompiler, a complete R5900 model, a function-boundary recovery pass, a runtime, or a compatibility claim.
- **Implementation:** `tools/rptp_ir.py`; generated-code lowering: `tools/rptp_lower.py`
- **Tests:** `tests/test_ir_cfg.py`; `tests/test_cfg_reachability.py`; `tests/test_ir_lowering.py`; `tests/test_instruction_logical.py`; `tests/test_instruction_logical_width.py`; `tests/test_instruction_lui.py`; `tests/test_instruction_register_logic.py`; `tests/test_instruction_nor.py`; `tests/test_instruction_slt.py`; `tests/test_instruction_sltu.py`; `tests/test_instruction_slti.py`; `tests/test_instruction_sltiu.py`; `tests/test_instruction_daddiu.py`

## Purpose

This increment separates five concerns that were previously implicit in the Gate 0 spike:

1. decoding a supported synthetic instruction into an explicit IR instruction;
2. partitioning the validated synthetic code range into deterministic basic blocks;
3. reporting provisional function-entry candidates without claiming function extents;
4. traversing only the CFG's already-recorded successor edges from an explicit block root; and
5. lowering a validated result to deterministic C++ for the same synthetic execution model.

The Gate 0 differential spike and the separate ORI, ANDI/XORI, LUI, register-logical AND/OR/XOR/NOR, SLT, SLTU and DADDIU differentials remain independent execution and native-generation paths. The IR module does not execute code or emit C++; `tools/rptp_lower.py` consumes the IR and emits C++. Known-edge graph traversal is static analysis, not a runtime result.

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
| `signed16` | `ADDIU`, `DADDIU`, `SLTI`, `SLTIU`, `LW`, `SW`, `BEQ`, `BNE` | The 16-bit field is sign-extended for the existing synthetic semantic model. `DADDIU` adds the sign-extended immediate to the modeled 64-bit source modulo 2^64 without an overflow trap; `SLTI` compares the modeled 64-bit source as signed against the sign-extended immediate; `SLTIU` compares it as unsigned against the same sign-extended immediate. |
| `zero16` | `ANDI`, `ORI`, `XORI` | The 16-bit field is zero-extended. |
| `shifted16` | `LUI` | The raw 16-bit field is shifted left 16 bits, the low 16 bits are zero, and the 32-bit result is sign-extended to the modeled 64-bit value. |

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
- `ADDIU` and `ADDU` wrap at 32 bits and sign-extend the result; `DADDIU` adds the sign-extended 16-bit immediate modulo 2^64 without trapping on integer overflow; `ANDI`, `ORI` and `XORI` apply the logical operation with the zero-extended immediate across the full modeled 64-bit register (`ORI` and `XORI` preserve upper bits of `rs`, while `ANDI` zeroes bits 16..63 of the result); `AND`, `OR`, `XOR` and `NOR` apply the bitwise operation to the full modeled 64-bit register values; `SLT` compares the sign bits and then the unsigned magnitudes of the full modeled 64-bit values to produce a signed two's-complement result of `1` or `0`; `SLTU` compares the full modeled 64-bit values as unsigned integers and writes `1` or `0`; `LUI` shifts the immediate left 16 bits and sign-extends the 32-bit result; `LW` requires initialized memory and sign-extends the loaded word; `SW` stores the low 32 bits; `JAL` writes `pc + 8` to `$ra`; `JR` reads its target from the runtime register.
- A direct target is emitted from the validated IR. The lowerer does not re-decode the raw word, although it requires the raw word to be present and well-formed.
- Uninitialized `LW` throws. Generated `main` writes `LOWER_RUNTIME_ERROR: <detail>\n` to stderr and exits `2`.
- A non-code dynamic PC, including the return sentinel, halts the synthetic program. This matches the oracle; it is not a hardware exception or kernel model.
- The generated source is a test artifact. It is not optimized or linked into a product runtime, and it is not a complete R5900 recompiler.

The lowerer raises `LoweringError` with a stable code: `LOWER_INVALID_RESULT`, `LOWER_UNSUPPORTED_OP`, `LOWER_MALFORMED_INSTRUCTION`, `LOWER_INVALID_CONTROL`, `LOWER_INVALID_TARGET`, `LOWER_INVALID_DELAY_SLOT`, `LOWER_INVALID_BLOCK`, `LOWER_LIMIT_EXCEEDED` or `LOWER_INVALID_OPTION`. It never substitutes a target, skips an instruction, or emits an approximation.

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

The generated native state is compared with the oracle for registers, memory, stop PC, halt flag and executed-PC trace. The SLT boundary test also emits a generated-source harness and seeds `State` directly at `INT64_MIN`/`INT64_MAX`; the SLTU oracle helper additionally checks `0`, `1`, `INT64_MIN`, `INT64_MAX` and `UINT64_MAX`, and the generated harness seeds `State` at high-bit and bit-31 divergences because the synthetic encoder cannot materialize arbitrary 64-bit constants; this exercises the generated helpers and state machine, while the encoded fixtures exercise the normal paths. A separate one-instruction fixture checks the uninitialized-load diagnostic and exit code.

The registered Gate 0 fixture and the ORI fixture are not modified. Their fixture and generated-C++ hashes are checked by `tests/test_ir_cfg.py`; the lowering tests use separate synthetic fixtures.

The DADDIU fixture in `tests/test_instruction_daddiu.py` checks positive and negative signed-32-bit boundary crossings against literal oracle and native results. It expects `0x0000000080000000` from `0x000000007FFFFFFF + 1` and `0xFFFFFFFF7FFFFFFF` from `0xFFFFFFFF80000000 - 1`. An in-memory oracle mutation using ADDIU dispatch is rejected by the strengthened fixture; production semantics remain unchanged. The separate native harness still covers full 64-bit wraparound boundaries.

## Limitations

- The subset is the existing synthetic ten-opcode Gate 0 subset plus `ORI`, `ANDI`, `XORI`, `LUI`, `AND`, `OR`, `XOR`, `NOR`, `SLT`, `SLTU`, `SLTI`, `SLTIU` and `DADDIU`. No other opcode is added by these increments.
- The CFG is a syntactic partition of the validated code range. Known-edge graph reachability is not runtime reachability, dead-code proof or function discovery.
- Function entries are candidates only. There are no function extents, symbols, call graphs with return edges, or confident `JR $ra` return-path claims. The direct-call continuation caveat is explicit in the reachability report.
- The IR is lowered only for the synthetic model. The generated C++ is not optimized, not a product recompiler or runtime, and not a substitute for the separate instruction differential tests.
- A dynamic non-code PC halts the synthetic program. There is no R5900 exception, fault, pipeline, MMIO, kernel, IOP, VU, GS, SPU2, CDVD, controller, memory-card, or timing model.
- No retail ELF, ISO, BIOS, or game-derived material is used by these tests.

## References and evidence

- Generic instruction encodings and MIPS naming: `RPTP-REF-001`, `RPTP-REF-002`. `RPTP-REF-002` covers the `SLT` and `SLTU` function codes and comparison names; the modeled 64-bit widths and test behavior are RPTP definitions. `RPTP-REF-001` was not used for the `SLTU` function-code value because its current SLTU table row conflicts with `RPTP-REF-002`.
- Generic ELF structure: `RPTP-REF-003`.
- Delay-slot background: `RPTP-REF-005`, used only as a secondary cross-check for the existing synthetic model.
- `LUI` shifted-immediate semantics: `RPTP-REF-013`, MIPS64 Revision 5.04 page 225. The Rev 6.03 LUI page was not directly accessible; the limitation is recorded in [REFERENCES.md](REFERENCES.md).
- The block, immediate, `$zero`, candidate, known-edge reachability and lowering rules are defined by this repository's tests and are not a hardware specification.
- The generated C++ state machine, JSON shape, failure text and exit code are test-defined behavior, not R5900 or PS2 hardware behavior.

Local and hosted verification evidence is recorded in [VERIFICATION_LOG.md](VERIFICATION_LOG.md). The SLTI increment (`69d7c11`) passed CI run #44; SLTIU (`25267b6`) passed run #45 on Windows x64/MSVC and Linux/GCC. Both are synthetic signed/unsigned comparisons against sign-extended immediates only; Gate 3 remains in progress and not passed.

## Verification commands

```powershell
python -m unittest tests.test_instruction_logical -v
python -m unittest tests.test_instruction_lui -v
python -m unittest tests.test_instruction_register_logic -v
python -m unittest tests.test_instruction_nor -v
python -m unittest tests.test_instruction_slt -v
python -m unittest tests.test_instruction_sltu -v
python -m unittest tests.test_ir_cfg -v
python -m unittest tests.test_cfg_reachability -v
python -m unittest tests.test_ir_lowering -v
python -m unittest discover -s tests -v
```
