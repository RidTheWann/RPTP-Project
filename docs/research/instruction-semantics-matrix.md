# Instruction semantics evidence matrix

- **Status date:** 2026-10-31
- **Baseline:** `origin/main` commit `248aad8dd9a773b900664661139b8f775f77ce6a` (the merge of PR #63). The original measurement baseline was `0944c84e8ed11c2d7db5d54ad23671b9a8de869d`; the runtime-coverage rows were revised at the current baseline after PR #41 (branch-likely in the C++ harness) and PR #43 (`LW`/`SW` alignment), as recorded under **Revision** below.
- **Scope:** Documentation and evidence classification only. This note adds no instruction semantics, changes no code, test, catalog entry or Gate status, and makes no compatibility claim.
- **Subject:** the 51-instruction Level B synthetic subset in [INSTRUCTION_CATALOG.md](../INSTRUCTION_CATALOG.md) and [isa-evidence.md](isa-evidence.md), including the six ordinary branch forms, the eight branch-likely forms and the nine doubleword shift forms. There is no separate set: the six ordinary forms are rows 37-42, the eight likely forms are rows 25-32 and the nine doubleword shifts are rows 43-51 of the same 51-row matrix.
- **Method:** source reading at the baseline commit plus the focused test runs recorded in §8. No retail data, emulator or recompiler source, Sony manual, or unapproved reference was used. The Sony manual and the R5900 catalog remain unapproved; the only manual used is the MIPS Technologies MIPS64 Revision 5.04 record under `RPTP-REF-015`, and no manual text is quoted here.
- **Revision (2026-10-30, ordinary-branch increment):** adds rows 37-42 for `BLEZ`, `BGTZ`, `BLTZ`, `BGEZ`, `BLTZAL` and `BGEZAL`, promotes them from Level C to Level B under `RPTP-REF-015` (MIPS64 Revision 5.04 pages 76, 77, 81, 83, 85 and 86) and extends the native harness and the cross-path suite to the same six forms with always-executed delay slots and unconditional link writes. The C++ runtime harness had 42 operations at that point (now 51 after the 2026-10-31 doubleword-shift increment). Section 6 recalculates the Level B/Level C split; §7.2 records that the fallback was executed and corrects its earlier claim that the legacy pipeline supported these forms. The legacy pipeline and the Gate 0 spike remain at 28 non-likely operations with `BEQ`/`BNE` as their only conditional branches.
- **Revision (2026-10-30, after PR #41 and PR #43):** the C++ runtime harness decodes and executes all Level B operations available at that baseline, including the eight likely forms, and it rejects unaligned `LW`/`SW` with `EXEC_MEMORY_FAULT`. Those two gaps are closed in `R`. The legacy pipeline and the Gate 0 spike remain at 28 non-likely operations with no `LW`/`SW` alignment check. The `RT†` execution column and §8 remain the original baseline session, where the runtime binary was not built; the runtime corrections here are **Terverifikasi by source reading**, not by execution in that session. The ordinary-branch increment later added six operations, bringing the harness to 42 at that point; the doubleword-shift increment brought it to 51.
- **Revision (2026-10-31, doubleword-shift increment):** adds rows 43-51 for `DSLL`, `DSLL32`, `DSLLV`, `DSRA`, `DSRA32`, `DSRAV`, `DSRL`, `DSRL32` and `DSRLV`, promotes them from Level C to Level B under `RPTP-REF-015` (MIPS64 Revision 5.04 pages 168–176) and extends the native harness and the cross-path suite to the same nine forms with literal 64-bit results and reserved-field rejection. The C++ runtime harness now has 51 operations. Section 6 recalculates the Level B/Level C split; §4.3 records the DS contract and the open canonical-decoder/harness `shamt` divergence. The decoder and its supported set are unchanged: the nine forms were already decoder-supported. The legacy pipeline and the Gate 0 spike remain at 28 non-likely operations and reject all nine.
- **Revision (2026-10-30, census refresh):** the eight-image read-only census was re-measured on 2026-10-29 with the current decoder and is recorded in [BOOT_CENSUS.md](../BOOT_CENSUS.md). The refreshed range is 76.96%-86.30%, superseding the pre-`SUBU` 58.3%-69.2% range and the one-image 63.03% figure. Sections 6, 7 and 9 now cite the refreshed values; the census was not rerun for this note.
- **Evidence labels:** `Terverifikasi` = read in source or run in this session and shown in §8; `Belum diverifikasi` = not run, not checked against a source, or dependent on a recorded run not repeated here; `Dugaan` = inference or planning judgement. These labels follow [AGENTS.md](../../AGENTS.md) §4.

## 1. Purpose and non-claims

The repository now has more than one implementation path. A decoder acceptance is not an execution result, and the Python oracle is not the C++ runtime. This note separates, per instruction:

1. decoder recognition;
2. Python oracle implementation;
3. CFG and delay-slot handling;
4. IR lowering and C++ emission;
5. C++ runtime-harness execution;
6. approved-reference support;
7. executable test evidence;
8. provenance status;
9. limits and gaps.

The two matrices use the same row number and mnemonic as a join key. Matrix A records implementation coverage; Matrix B records evidence, provenance and limits. A path cell says that the path exists, not that every path agrees with every other path. The disagreements are the subject of §5.

This note is **not**:

- a Gate disposition, a clean-room certification or a compatibility result;
- a statement that the 51 instructions are correct R5900 hardware behavior;
- a statement that the 51-op runtime harness represents the recompiler product path;
- a statement that decoder-supported mnemonics outside the 51 have approved semantics;
- a replacement for [INSTRUCTION_CATALOG.md](../INSTRUCTION_CATALOG.md), [IR_CFG.md](../IR_CFG.md), [RUNTIME.md](../RUNTIME.md) or [REFERENCES.md](../REFERENCES.md).

**Terverifikasi:** the repository has two Python implementation paths and one C++ runtime harness:

- **N** = the `tools/rptp/` package: `isa.py`, `cfg.py`, `ir.py`, `oracle.py`, `codegen.py`, `native.py`.
- **L** = the legacy pipeline: `tools/rptp_gate0_spike.py`, `tools/rptp_ir.py`, `tools/rptp_lower.py`.
- **R** = the C++ harness: `runtime/src/execution.cpp` and `runtime/tools/rptp_run.cpp`.

The runtime harness is a test vehicle, not a product runtime. [RUNTIME.md](../RUNTIME.md) records its 51-instruction subset and its explicit non-goals.

**Terverifikasi at the revision baseline:** `runtime/src/execution.cpp` decodes all eight likely forms (`0x14`-`0x17` and REGIMM `rt=0x02/0x03/0x12/0x13`), all six ordinary branch forms (`0x06`/`0x07` and REGIMM `rt=0x00/0x01/0x10/0x11`), the nine doubleword shift forms (`SPECIAL` funct `0x14`, `0x16`, `0x17`, `0x38`, `0x3A`, `0x3B`, `0x3C`, `0x3E`, `0x3F`) and `BEQ`/`BNE`, checks `address & 3` for `LW`/`SW` and `address & 7` for `LD`/`SD`, rejects a nonzero reserved `rs`/`shamt` on the doubleword shifts, and its `Op` enum has 51 entries (`Nop` through `Jr`). `tools/rptp_lower.py` `_SUPPORTED_OPS` and `tools/rptp_gate0_spike.py` still implement 28 operations with `BEQ`/`BNE` as their only conditional branches and no `LW`/`SW` alignment check. The runtime therefore no longer lacks the ordinary/likely branch, doubleword-shift or `LW`/`SW` alignment coverage; the remaining asymmetries are the legacy pipeline and the memory/register model differences recorded in §5.

## 2. Matrix legend

### 2.1 Path codes

| Code | Meaning |
|---|---|
| `OK` | The decoder recognizes the canonical encoding and marks the mnemonic supported. |
| `N + L` | Both the `tools/rptp/` path and the legacy path implement the instruction for the listed stage. |
| `N only` | Only the `tools/rptp/` path implements the instruction for the listed stage. |
| `N + L*` | Both implement it, but a material policy difference is recorded in §5. |
| `R` | The C++ runtime harness decodes and executes the instruction. |
| `none` | The path has no implementation; the encoding fails closed. |

### 2.2 Test-evidence codes

| Code | Test path | Execution in this session |
|---|---|---|
| `G0` | `tests/test_gate0_spike.py` | Ran: 12 tests, all passed. |
| `IRL` | `tests/test_ir_lowering.py` | Ran: 11 tests, 8 passed and 3 native lowerings skipped because the test helper could not find `cl`/`c++`. |
| `RT†` | `tests/test_runtime_execution.py` and `runtime/tests/runtime_tests.cpp` | **Not executed.** The 16 Python runtime tests skipped because `RPTP_RUN_BINARY` was unset and no build was present; the C++ test binary was not built. |
| `BL` | `tests/test_instruction_branch_likely.py` | Ran: 12 tests, all passed, including the MSVC native differential. |
| `PB` | `tests/test_instruction_branch_plain.py` | Ran in the ordinary-branch increment session: 12 tests after review hardening, all passed, including the native differential and the signed-low-64-bit cases. |
| `ISA` | `tests/test_isa_encodings.py` | Ran: all tests passed. Structural decode/lowering coverage only; not semantic proof. |
| `T-DADDIU` | `tests/test_instruction_daddiu.py` | Ran in the per-instruction batch; Python/oracle and lowering-source assertions passed; native parts skipped where recorded. |
| `T-DADDU` | `tests/test_instruction_daddu.py` | Same batch status as `T-DADDIU`. |
| `T-SUBU` | `tests/test_instruction_subu.py` | Same batch status. |
| `T-SLL` | `tests/test_instruction_sll.py` | Same batch status. |
| `T-REG` | `tests/test_instruction_register_logic.py` | Same batch status; covers `AND`, `OR`, `XOR`. |
| `T-NOR` | `tests/test_instruction_nor.py` | Same batch status. |
| `T-SLT` | `tests/test_instruction_slt.py` | Same batch status. |
| `T-SLTU` | `tests/test_instruction_sltu.py` | Same batch status. |
| `T-SLTI` | `tests/test_instruction_slti.py` | Same batch status. |
| `T-SLTIU` | `tests/test_instruction_sltiu.py` | Same batch status. |
| `T-LOG` | `tests/test_instruction_logical.py` | Same batch status; covers `ANDI` and `XORI`. |
| `T-LOGW` | `tests/test_instruction_logical_width.py` | Same batch status; 64-bit width cases for `ANDI`, `ORI`, `XORI`. |
| `T-ORI` | `tests/test_instruction_ori.py` | Same batch status. |
| `T-LUI` | `tests/test_instruction_lui.py` | Same batch status. |
| `T-LDSD` | `tests/test_instruction_ld_sd.py` | Same batch status; covers `LD` and `SD`. |
| `T-DS` | `tests/test_instruction_dshift.py`, with runtime and cross-path legs in `tests/test_runtime_execution.py` and `tests/test_cross_path_equivalence.py` | Ran in the doubleword-shift increment session (2026-10-31); results recorded in §8. Covers all nine doubleword shift forms. |

The per-instruction batch ran 156 tests: 130 passed and 26 native cases skipped because `cl` was not discoverable through those modules' compiler helper. The skipped native cases do not invalidate the Python/oracle assertions recorded in the same modules, but they are not claimed as native evidence.

### 2.3 Provenance codes

| Code | Meaning |
|---|---|
| `P-G0` | Level B. The instruction is in the accepted Gate 0 synthetic scope; the Gate 0 component status is `Provisional independent`. Not certified. |
| `P-EXP` | Level B. Added after the Gate 0 disposition; the runtime/recompiler expansion component status is `Recorded`. Not certified. |
| `P-BL` | Level B. Added by the 2026-10-30 branch-likely increment; expansion status `Recorded`. Not certified. |
| `P-PB` | Level B. Added by the 2026-10-30 ordinary-branch increment; expansion status `Recorded`. Not certified. |
| `P-DS` | Level B. Added by the 2026-10-31 doubleword-shift increment; expansion status `Recorded`. Not certified. |
| `P-TD` | Level B. `NOP` has no specific approved reference; its semantics are an RPTP test definition. Not certified. |

`Provisional independent`, `Recorded` and `Review required` are component-level labels from [CLEAN_ROOM_AUDIT.md](../CLEAN_ROOM_AUDIT.md) and [PROVENANCE_PLAN.md](../PROVENANCE_PLAN.md). They are not per-instruction certifications. The build/CI/doctor layer remains `Review required`; no component is clean-room certified.

## 3. Matrix A — implementation coverage

| # | Instruction | Encoding | Decoder | Python oracle | CFG / delay slot | IR + emitter | C++ runtime |
|---:|---|---|---|---|---|---|---|
| 1 | `ADDIU` | I-type opcode `0x09` | `OK` | `N + L` | `N + L`; fallthrough | `N + L` | `R` |
| 2 | `DADDIU` | I-type opcode `0x19` | `OK` | `N + L` | `N + L`; fallthrough | `N + L` | `R` |
| 3 | `ADDU` | SPECIAL funct `0x21`, `shamt=0` | `OK` | `N + L` | `N + L`; fallthrough | `N + L` | `R` |
| 4 | `DADDU` | SPECIAL funct `0x2D`, `shamt=0` | `OK` | `N + L` | `N + L`; fallthrough | `N + L` | `R` |
| 5 | `SUBU` | SPECIAL funct `0x23`, `shamt=0` | `OK` | `N + L` | `N + L`; fallthrough | `N + L` | `R` |
| 6 | `SLL` | SPECIAL funct `0x00`, `rs=0`, 5-bit `shamt` | `OK` | `N + L` | `N + L`; fallthrough | `N + L` | `R` |
| 7 | `AND` | SPECIAL funct `0x24`, `shamt=0` | `OK` | `N + L` | `N + L`; fallthrough | `N + L` | `R` |
| 8 | `OR` | SPECIAL funct `0x25`, `shamt=0` | `OK` | `N + L` | `N + L`; fallthrough | `N + L` | `R` |
| 9 | `XOR` | SPECIAL funct `0x26`, `shamt=0` | `OK` | `N + L` | `N + L`; fallthrough | `N + L` | `R` |
| 10 | `NOR` | SPECIAL funct `0x27`, `shamt=0` | `OK` | `N + L` | `N + L`; fallthrough | `N + L` | `R` |
| 11 | `SLT` | SPECIAL funct `0x2A`, `shamt=0` | `OK` | `N + L` | `N + L`; fallthrough | `N + L` | `R` |
| 12 | `SLTU` | SPECIAL funct `0x2B`, `shamt=0` | `OK` | `N + L` | `N + L`; fallthrough | `N + L` | `R` |
| 13 | `SLTI` | I-type opcode `0x0A` | `OK` | `N + L` | `N + L`; fallthrough | `N + L` | `R` |
| 14 | `SLTIU` | I-type opcode `0x0B` | `OK` | `N + L` | `N + L`; fallthrough | `N + L` | `R` |
| 15 | `ANDI` | I-type opcode `0x0C` | `OK` | `N + L` | `N + L`; fallthrough | `N + L` | `R` |
| 16 | `ORI` | I-type opcode `0x0D` | `OK` | `N + L` | `N + L`; fallthrough | `N + L` | `R` |
| 17 | `XORI` | I-type opcode `0x0E` | `OK` | `N + L` | `N + L`; fallthrough | `N + L` | `R` |
| 18 | `LUI` | I-type opcode `0x0F`, `rs=0` | `OK` | `N + L` | `N + L`; fallthrough | `N + L` | `R` |
| 19 | `LW` | I-type opcode `0x23` | `OK` | `N + L*` | `N + L`; fallthrough | `N + L*` | `R`; requires 4-byte alignment |
| 20 | `SW` | I-type opcode `0x2B` | `OK` | `N + L*` | `N + L`; fallthrough | `N + L*` | `R`; requires 4-byte alignment |
| 21 | `LD` | I-type opcode `0x37` | `OK` | `N + L*` | `N + L`; fallthrough | `N + L*` | `R`; requires 8-byte alignment |
| 22 | `SD` | I-type opcode `0x3F` | `OK` | `N + L*` | `N + L`; fallthrough | `N + L*` | `R`; requires 8-byte alignment |
| 23 | `BEQ` | I-type opcode `0x04` | `OK` | `N + L` | `N + L`; both successors; delay always | `N + L` | `R`; delay always |
| 24 | `BNE` | I-type opcode `0x05` | `OK` | `N + L` | `N + L`; both successors; delay always | `N + L` | `R`; delay always |
| 25 | `BEQL` | I-type opcode `0x14` | `OK` | `N only` | `N only`; both successors; delay only if taken | `N only` | `R`; delay only if taken |
| 26 | `BNEL` | I-type opcode `0x15` | `OK` | `N only` | `N only`; both successors; delay only if taken | `N only` | `R`; delay only if taken |
| 27 | `BLEZL` | I-type opcode `0x16` | `OK` | `N only` | `N only`; both successors; delay only if taken | `N only` | `R`; delay only if taken |
| 28 | `BGTZL` | I-type opcode `0x17` | `OK` | `N only` | `N only`; both successors; delay only if taken | `N only` | `R`; delay only if taken |
| 29 | `BLTZL` | REGIMM opcode `0x01`, `rt=0x02` | `OK` | `N only` | `N only`; both successors; delay only if taken | `N only` | `R`; delay only if taken |
| 30 | `BGEZL` | REGIMM opcode `0x01`, `rt=0x03` | `OK` | `N only` | `N only`; both successors; delay only if taken | `N only` | `R`; delay only if taken |
| 31 | `BLTZALL` | REGIMM opcode `0x01`, `rt=0x12` | `OK`; `rs=31` rejected | `N only` | `N only`; both successors; delay only if taken; link `pc+8` | `N only` | `R`; delay only if taken; link `pc+8` |
| 32 | `BGEZALL` | REGIMM opcode `0x01`, `rt=0x13` | `OK`; `rs=31` rejected | `N only` | `N only`; both successors; delay only if taken; link `pc+8` | `N only` | `R`; delay only if taken; link `pc+8` |
| 33 | `J` | J-type opcode `0x02` | `OK` | `N + L` | `N + L`; one direct successor; delay always | `N + L` | `R`; delay always |
| 34 | `JAL` | J-type opcode `0x03` | `OK` | `N + L` | `N + L`; one direct successor; link `pc+8`; delay always | `N + L` | `R`; delay always |
| 35 | `JR` | SPECIAL funct `0x08`, `rt=rd=shamt=0` | `OK` | `N + L` | `N + L`; dynamic target; delay always | `N + L` | `R`; delay always |
| 36 | `NOP` | all-zero word `0x00000000` | `OK` | `N + L` | `N + L`; fallthrough | `N + L` | `R` |
| 37 | `BLEZ` | I-type opcode `0x06` | `OK` | `N only` | `N only`; both successors; delay always | `N only` | `R`; delay always |
| 38 | `BGTZ` | I-type opcode `0x07` | `OK` | `N only` | `N only`; both successors; delay always | `N only` | `R`; delay always |
| 39 | `BLTZ` | REGIMM opcode `0x01`, `rt=0x00` | `OK` | `N only` | `N only`; both successors; delay always | `N only` | `R`; delay always |
| 40 | `BGEZ` | REGIMM opcode `0x01`, `rt=0x01` | `OK` | `N only` | `N only`; both successors; delay always | `N only` | `R`; delay always |
| 41 | `BLTZAL` | REGIMM opcode `0x01`, `rt=0x10` | `OK`; `rs=31` rejected | `N only` | `N only`; both successors; delay always; link `pc+8` | `N only` | `R`; delay always; link `pc+8` |
| 42 | `BGEZAL` | REGIMM opcode `0x01`, `rt=0x11` | `OK`; `rs=31` rejected | `N only` | `N only`; both successors; delay always; link `pc+8` | `N only` | `R`; delay always; link `pc+8` |
| 43 | `DSLL` | SPECIAL funct `0x38`, `rs=0` | `OK` | `N only` | `N only`; fallthrough | `N only` | `R`; nonzero reserved `rs` rejected |
| 44 | `DSLL32` | SPECIAL funct `0x3C`, `rs=0` | `OK` | `N only` | `N only`; fallthrough | `N only` | `R`; nonzero reserved `rs` rejected |
| 45 | `DSLLV` | SPECIAL funct `0x14`, `shamt=0` | `OK`; reserved `shamt` not rejected | `N only` | `N only`; fallthrough | `N only` | `R`; nonzero reserved `shamt` rejected |
| 46 | `DSRL` | SPECIAL funct `0x3A`, `rs=0` | `OK` | `N only` | `N only`; fallthrough | `N only` | `R`; nonzero reserved `rs` rejected |
| 47 | `DSRL32` | SPECIAL funct `0x3E`, `rs=0` | `OK` | `N only` | `N only`; fallthrough | `N only` | `R`; nonzero reserved `rs` rejected |
| 48 | `DSRLV` | SPECIAL funct `0x16`, `shamt=0` | `OK`; reserved `shamt` not rejected | `N only` | `N only`; fallthrough | `N only` | `R`; nonzero reserved `shamt` rejected |
| 49 | `DSRA` | SPECIAL funct `0x3B`, `rs=0` | `OK` | `N only` | `N only`; fallthrough | `N only` | `R`; nonzero reserved `rs` rejected |
| 50 | `DSRA32` | SPECIAL funct `0x3F`, `rs=0` | `OK` | `N only` | `N only`; fallthrough | `N only` | `R`; nonzero reserved `rs` rejected |
| 51 | `DSRAV` | SPECIAL funct `0x17`, `shamt=0` | `OK`; reserved `shamt` not rejected | `N only` | `N only`; fallthrough | `N only` | `R`; nonzero reserved `shamt` rejected |

`Terverifikasi`: every row above was checked by reading the named source in `tools/rptp/isa.py`, `tools/rptp/cfg.py`, `tools/rptp/ir.py`, `tools/rptp/oracle.py`, `tools/rptp/codegen.py`, `tools/rptp_gate0_spike.py`, `tools/rptp_ir.py`, `tools/rptp_lower.py` and `runtime/src/execution.cpp`. The runtime column records source support only; it is not execution evidence for this session. Rows 37-42 were appended on 2026-10-30 to preserve the historical row numbers of the original 36-row matrix; they are the six ordinary branch forms. Rows 43-51 were appended on 2026-10-31 and are the nine doubleword shift forms; the decoder column records that the canonical decoder accepts a nonzero reserved `shamt` on the three variable forms while the harness rejects it (§4.3, §5.7).

## 4. Matrix B — approved reference, tests, provenance and limits

| # | Instruction | Approved reference | Executable evidence | Provenance | Limits and gaps |
|---:|---|---|---|---|---|
| 1 | `ADDIU` | `RPTP-REF-001` | `G0`, `IRL`, `RT†` | `P-G0` | 32-bit result sign-extended into the modeled register; no overflow trap and no complete 64-bit claim. |
| 2 | `DADDIU` | `RPTP-REF-015` p. 127 | `T-DADDIU`, `RT†` | `P-EXP` | Full modeled 64-bit addition modulo 2^64; no overflow trap. Post-Gate-0 synthetic model. |
| 3 | `DADDU` | `RPTP-REF-015` p. 132 | `T-DADDU`, `RT†` | `P-EXP` | Full modeled 64-bit addition modulo 2^64; no overflow trap. |
| 4 | `ADDU` | `RPTP-REF-001` | `G0`, `IRL`, `RT†` | `P-G0` | Low-32-bit addition, sign-extended; no overflow trap. |
| 5 | `SUBU` | `RPTP-REF-015` p. 355 | `T-SUBU`, `RT†` | `P-EXP` | Low-32-bit subtraction modulo 2^32, sign-extended; the reference marks a non-word-value source UNPREDICTABLE, and RPTP resolves it deterministically by truncation. |
| 6 | `SLL` | `RPTP-REF-002` | `T-SLL`, `RT†` | `P-EXP` | Low-32-bit shift, truncate to 32 bits, sign-extend; nonzero `rs` rejected; only the all-zero word is `NOP`. |
| 7 | `AND` | `RPTP-REF-001`, `RPTP-REF-002` | `T-REG`, `RT†` | `P-EXP` | Full modeled 64-bit width is an RPTP test definition. |
| 8 | `OR` | `RPTP-REF-001`, `RPTP-REF-002` | `T-REG`, `RT†` | `P-EXP` | Full modeled 64-bit width is an RPTP test definition. |
| 9 | `XOR` | `RPTP-REF-001`, `RPTP-REF-002` | `T-REG`, `RT†` | `P-EXP` | Full modeled 64-bit width is an RPTP test definition. |
| 10 | `NOR` | `RPTP-REF-001`, `RPTP-REF-002` | `T-NOR`, `RT†` | `P-EXP` | Full modeled 64-bit width is an RPTP test definition. |
| 11 | `SLT` | `RPTP-REF-001`, `RPTP-REF-002` | `T-SLT`, `RT†` | `P-EXP` | Signed 64-bit comparison width is an RPTP test definition. |
| 12 | `SLTU` | `RPTP-REF-002` | `T-SLTU`, `RT†` | `P-EXP` | `RPTP-REF-001`'s SLTU row conflicts with `RPTP-REF-002` and is not used; unsigned 64-bit width is an RPTP test definition. |
| 13 | `SLTI` | `RPTP-REF-014` | `T-SLTI`, `RT†` | `P-EXP` | Sign-extended immediate and signed comparison from the reference; 64-bit comparison width is an RPTP test definition. |
| 14 | `SLTIU` | `RPTP-REF-014` | `T-SLTIU`, `RT†` | `P-EXP` | Sign-extended immediate plus unsigned comparison from the reference; 64-bit width is an RPTP test definition. |
| 15 | `ANDI` | `RPTP-REF-001` (encoding) | `T-LOG`, `T-LOGW`, `RT†` | `P-EXP` | Zero-extending immediate model is synthetic; the 64-bit width record cites `RPTP-REF-013`, whose permitted-use row is scoped to `LUI` (scope gap in [isa-evidence.md](isa-evidence.md) §6). |
| 16 | `ORI` | `RPTP-REF-001` (encoding) | `T-ORI`, `T-LOG`, `T-LOGW`, `IRL`, `RT†` | `P-EXP` | Upper bits of `rs` are preserved; the 64-bit width record has the same `RPTP-REF-013` scope gap. |
| 17 | `XORI` | `RPTP-REF-001` (encoding) | `T-LOG`, `T-LOGW`, `RT†` | `P-EXP` | Upper bits of `rs` are preserved; the 64-bit width record has the same `RPTP-REF-013` scope gap. |
| 18 | `LUI` | `RPTP-REF-013` p. 225 | `T-LUI`, `RT†` | `P-EXP` | Shifted/sign-extended 32-bit model; `rs=0` required; the revised 6.03 page was inaccessible and the model is synthetic. |
| 19 | `LW` | `RPTP-REF-001` | `G0`, `IRL`, `RT†` | `P-G0` | `N` and `R` require 4-byte alignment and fail closed; the legacy paths do **not** check it. No MMIO, TLB, cache, alignment-exception or timing model. |
| 20 | `SW` | `RPTP-REF-001` | `G0`, `IRL`, `RT†` | `P-G0` | `N` and `R` require 4-byte alignment and fail closed; the legacy paths do **not** check it. No MMIO, TLB, cache or timing model. |
| 21 | `LD` | `RPTP-REF-015` p. 207 | `T-LDSD`, `RT†` | `P-EXP` | Requires 8-byte alignment; 32-bit effective address; two-word little-endian composition. `N` models 32 MiB default-zero RAM and a 128-bit register file; legacy/runtime use initialized or mapped word storage and 64-bit registers. |
| 22 | `SD` | `RPTP-REF-015` p. 327 | `T-LDSD`, `RT†` | `P-EXP` | Requires 8-byte alignment; splits `rt` into two words; `N` and legacy/runtime agree on the low 64 bits but not on the full memory/register model (§5.3). |
| 23 | `BEQ` | `RPTP-REF-001` | `G0`, `IRL`, `RT†` | `P-G0` | Delay slot always executes; full 64-bit comparison; static target must stay inside the synthetic code model. |
| 24 | `BNE` | `RPTP-REF-001` | `G0`, `IRL`, `RT†` | `P-G0` | Delay slot always executes; full 64-bit comparison; static target must stay inside the synthetic code model. |
| 25 | `BEQL` | `RPTP-REF-015` p. 75 | `BL`, `RT†` | `P-BL` | Delay slot executes only when taken; not-taken delay slot is nullified. `N + R`; legacy has no implementation. Low-64-bit comparison, 32-bit PC masking and trace/step accounting are RPTP test definitions. |
| 26 | `BNEL` | `RPTP-REF-015` p. 91 | `BL`, `RT†` | `P-BL` | Same likely-branch model as `BEQL`; `N + R`; legacy has no implementation. |
| 27 | `BLEZL` | `RPTP-REF-015` p. 84 | `BL`, `RT†` | `P-BL` | Taken when signed low 64 bits of `rs` are `<= 0`; `N + R`; legacy has no implementation. |
| 28 | `BGTZL` | `RPTP-REF-015` p. 82 | `BL`, `RT†` | `P-BL` | Taken when signed low 64 bits of `rs` are `> 0`; `N + R`; legacy has no implementation. |
| 29 | `BLTZL` | `RPTP-REF-015` p. 89 | `BL`, `RT†` | `P-BL` | Taken when signed low 64 bits of `rs` are `< 0`; `N + R`; legacy has no implementation. |
| 30 | `BGEZL` | `RPTP-REF-015` p. 80 | `BL`, `RT†` | `P-BL` | Taken when signed low 64 bits of `rs` are `>= 0`; `N + R`; legacy has no implementation. |
| 31 | `BLTZALL` | `RPTP-REF-015` p. 87 | `BL`, `RT†` | `P-BL` | `GPR[31] = pc + 8` is written unconditionally; `rs=31` is rejected fail-closed because the reference marks it UNPREDICTABLE; the rejection is RPTP policy and both `N` and `R` decode paths apply it. `N + R`; legacy has no implementation. |
| 32 | `BGEZALL` | `RPTP-REF-015` p. 78 | `BL`, `RT†` | `P-BL` | Same unconditional link and `rs=31` rejection as `BLTZALL`; `N + R`; legacy has no implementation. |
| 33 | `J` | `RPTP-REF-001` | `G0`, `IRL`, `RT†` | `P-G0` | Static target must stay inside the synthetic code model; delay slot always executes. |
| 34 | `JAL` | `RPTP-REF-001` | `G0`, `IRL`, `RT†` | `P-G0` | Writes `pc+8` to `r31`; delay slot always executes; no full call convention or pipeline claim. |
| 35 | `JR` | `RPTP-REF-001` | `G0`, `IRL`, `RT†` | `P-G0` | Dynamic target is the low 32 bits of `rs`; no return-address stack, speculation or exception behavior; delay slot always executes. |
| 36 | `NOP` | none specific; RPTP test definition | `G0`, `IRL`, `RT†` | `P-TD` | Only the encoded all-zero word is recognized as `NOP`. |
| 37 | `BLEZ` | `RPTP-REF-015` p. 83 | `PB` | `P-PB` | Taken when signed low 64 bits of `rs` are `<= 0`; delay slot always executes. `N + R`; legacy has no implementation. Low-64-bit comparison, 32-bit PC masking and trace/step accounting are RPTP test definitions. |
| 38 | `BGTZ` | `RPTP-REF-015` p. 81 | `PB` | `P-PB` | Taken when signed low 64 bits of `rs` are `> 0`; delay slot always executes. `N + R`; legacy has no implementation. |
| 39 | `BLTZ` | `RPTP-REF-015` p. 85 | `PB` | `P-PB` | Taken when signed low 64 bits of `rs` are `< 0`; delay slot always executes. `N + R`; legacy has no implementation. |
| 40 | `BGEZ` | `RPTP-REF-015` p. 76 | `PB` | `P-PB` | Taken when signed low 64 bits of `rs` are `>= 0`; delay slot always executes. `N + R`; legacy has no implementation. |
| 41 | `BLTZAL` | `RPTP-REF-015` p. 86 | `PB` | `P-PB` | `GPR[31] = pc + 8` is written unconditionally, including when the branch is not taken; delay slot always executes; `rs=31` is rejected fail-closed because the reference marks it UNPREDICTABLE, and both `N` and `R` decode paths apply that policy. `N + R`; legacy has no implementation. |
| 42 | `BGEZAL` | `RPTP-REF-015` p. 77 | `PB` | `P-PB` | Same unconditional link, always-executed delay slot and `rs=31` rejection as `BLTZAL`. `N + R`; legacy has no implementation. |
| 43 | `DSLL` | `RPTP-REF-015` p. 168 | `T-DS` | `P-DS` | 64-bit width and 128-bit register-pair sign extension are RPTP test definitions; nonzero reserved `rs` rejected; legacy has no implementation. |
| 44 | `DSLL32` | `RPTP-REF-015` p. 169 | `T-DS` | `P-DS` | 64-bit width, `shamt + 32` amount and 128-bit sign extension are RPTP test definitions; nonzero reserved `rs` rejected; legacy has no implementation. |
| 45 | `DSLLV` | `RPTP-REF-015` p. 170 | `T-DS` | `P-DS` | 64-bit width and masked variable amount are RPTP test definitions; the canonical decoder accepts a nonzero reserved `shamt` while the harness rejects it (open E4 divergence); legacy has no implementation. |
| 46 | `DSRL` | `RPTP-REF-015` p. 174 | `T-DS` | `P-DS` | 64-bit width and 128-bit sign extension are RPTP test definitions; nonzero reserved `rs` rejected; legacy has no implementation. |
| 47 | `DSRL32` | `RPTP-REF-015` p. 175 | `T-DS` | `P-DS` | 64-bit width, `shamt + 32` amount and 128-bit sign extension are RPTP test definitions; nonzero reserved `rs` rejected; legacy has no implementation. |
| 48 | `DSRLV` | `RPTP-REF-015` p. 176 | `T-DS` | `P-DS` | 64-bit width and masked variable amount are RPTP test definitions; the canonical decoder accepts a nonzero reserved `shamt` while the harness rejects it (open E4 divergence); legacy has no implementation. |
| 49 | `DSRA` | `RPTP-REF-015` p. 171 | `T-DS` | `P-DS` | 64-bit width, sign replication and 128-bit sign extension are RPTP test definitions; nonzero reserved `rs` rejected; legacy has no implementation. |
| 50 | `DSRA32` | `RPTP-REF-015` p. 172 | `T-DS` | `P-DS` | 64-bit width, `shamt + 32` amount, sign replication and 128-bit sign extension are RPTP test definitions; nonzero reserved `rs` rejected; legacy has no implementation. |
| 51 | `DSRAV` | `RPTP-REF-015` p. 173 | `T-DS` | `P-DS` | 64-bit width, masked variable amount and sign replication are RPTP test definitions; the canonical decoder accepts a nonzero reserved `shamt` while the harness rejects it (open E4 divergence); legacy has no implementation. |

`Terverifikasi` for the reference mapping: each approved-reference cell was checked against [REFERENCES.md](../REFERENCES.md) and [isa-evidence.md](isa-evidence.md) §3. `Belum diverifikasi` for the `RT†` cells: the runtime harness was not executed in the original matrix session. The reference pins support the encoding/operation model within the recorded limits; they do not establish complete R5900 semantics. The `PB` cells were executed in the ordinary-branch increment session (12 tests after review hardening, all passed); the runtime half of rows 37-42 was executed through `tests/test_runtime_execution.py` in the same increment session, as recorded in §4.2 and [VERIFICATION_LOG.md](../VERIFICATION_LOG.md).

### 4.1 Branch-likely rows in detail

The eight likely forms are rows 25-32. Their shared implementation contract is:

- The condition is evaluated from the architectural state **before** the delay slot.
- On a taken branch the delay slot executes and the next PC is the direct target.
- On a not-taken branch the delay slot is nullified and the next PC is `pc + 8`.
- The CFG records both the direct target and the fallthrough, target first. Nullification is an execution-time effect, not a reachability filter.
- `BLTZALL` and `BGEZALL` write `GPR[31] = pc + 8` unconditionally, including when the branch is not taken.
- `rs = 31` on either link form is rejected fail-closed as RPTP policy because the approved reference marks the result UNPREDICTABLE.

`Terverifikasi` by source reading: `tools/rptp/isa.py` (`LIKELY_MNEMONICS`, `LINK_MNEMONICS`, target calculation and `rs=31` rejection), `tools/rptp/oracle.py` (`nullify_delay` and unconditional link write), `tools/rptp/ir.py` (`Control.likely`, `link_reg`) and `tools/rptp/codegen.py` (`if (taken) {` around delay operations). `Terverifikasi` by execution: `BL` passed 12 of 12 tests, including the MSVC native differential against the new oracle. `ISA` also decodes and statically lowers all eight forms, but it is structural evidence, not semantic execution evidence.

`Terverifikasi` by source reading at the revision baseline: `runtime/src/execution.cpp` decodes the same eight forms (`kOpcodeBeql`-`kOpcodeBgtzl` and REGIMM `kRegimmBltzl`/`kRegimmBgezl`/`kRegimmBltzall`/`kRegimmBgezall`), rejects `rs=31` on both link forms, and implements nullified delay slots. `runtime/tests/runtime_tests.cpp` has `test_execution_likely_branch_forms`, `test_execution_likely_combined_program`, `test_execution_likely_nullification_and_failures` and `test_execution_likely_pc_masking`; `tests/test_runtime_execution.py` has the matching Python-side cases. Those runtime tests were **not executed** in the original session (`RT†`), so they are source evidence here, not execution evidence.

**Asymmetry:** none of the eight forms exists in `tools/rptp_gate0_spike.py`, `tools/rptp_ir.py` or `tools/rptp_lower.py`; the legacy pipeline cannot analyze or lower them. The legacy runtime differential therefore cannot cover this family. The C++ harness and the `N` path both implement it, but `tests/test_cross_path_equivalence.py` does not include a likely-branch program, so there is still no single test that drives all three paths on the same likely branch.

### 4.2 Ordinary branch rows in detail

The six non-likely branch forms are rows 37-42. Their shared implementation contract is:

- The condition is evaluated from the architectural state **before** the delay slot.
- The delay slot **always** executes, whether the branch is taken or not; there is no nullification.
- The target is the sign-extended 18-bit offset added to `pc + 4`, with the 32-bit PC mask used by the existing branch model.
- The CFG records both the direct target and the fallthrough, target first. There is no nullification filter.
- `BLTZAL` and `BGEZAL` write `GPR[31] = pc + 8` unconditionally, including when the branch is not taken.
- `rs = 31` on either link form is rejected fail-closed as RPTP policy because the approved reference marks the result UNPREDICTABLE.

`Terverifikasi` by source reading: `tools/rptp/isa.py` (`BRANCH_MNEMONICS`, `LINK_MNEMONICS` and the `rs=31` rejection), `tools/rptp/oracle.py` (the `blez`/`bgtz`/`bltz`/`bgez` conditions and the unconditional link write), `tools/rptp/ir.py` (`Control.cond`, `link_reg`, `likely=False`) and `tools/rptp/codegen.py` (no `if (taken) {` around the delay block). `Terverifikasi` by execution: `PB` passed 12 of 12 tests after review hardening, including the native differential against the oracle and the signed-low-64-bit cases.

`Terverifikasi` by execution in the ordinary-branch increment session: `tests/test_runtime_execution.py` ran 26 tests after review hardening, all passed with the built `rptp-run` binary, including `test_plain_branch_forms_match_the_python_oracle` and `test_plain_link_forms_with_rs_31_fail_closed`. `runtime/tests/runtime_tests.cpp` adds `test_execution_plain_branch_forms` and `test_execution_plain_branch_failures`; the CTest result is recorded in [VERIFICATION_LOG.md](../VERIFICATION_LOG.md).

**Asymmetry:** none of the six forms exists in `tools/rptp_gate0_spike.py`, `tools/rptp_ir.py` or `tools/rptp_lower.py`; the legacy pipeline's only conditional branches are `BEQ`/`BNE`. The `N` path, the C++ harness and `tests/test_cross_path_equivalence.py` now cover all six forms on one shared synthetic program.

### 4.3 Doubleword-shift rows in detail

The nine doubleword shift forms are rows 43-51. Their shared implementation contract is:

- Immediate forms (`DSLL`, `DSLL32`, `DSRL`, `DSRL32`, `DSRA`, `DSRA32`) require `rs = 0` and shift by the 5-bit `sa` field, or by `sa + 32` for the three `32` variants.
- Variable forms (`DSLLV`, `DSRLV`, `DSRAV`) require `shamt = 0` and shift by `GPR[rs] & 63`.
- The shift operates on the low 64 bits of `rt`; left and logical-right shifts fill with zeros, arithmetic-right shifts replicate the sign bit.
- The result replaces the low 64 bits of `rd` and is sign-extended from bit 63 into the modeled 128-bit register pair; a write to `$zero` is discarded.
- A nonzero reserved `rs` (immediate forms) is rejected fail-closed by the canonical decoder; a nonzero reserved `shamt` (variable forms) is rejected by the native harness but not by the canonical decoder (§5.7).

`Terverifikasi` by source reading: `tools/rptp/isa.py` (funct tables, supported mnemonics and reserved-`rs` checks), `tools/rptp/cfg.py`/`ir.py` (fallthrough classification and `shift`/`shift_var` ops), `tools/rptp/oracle.py` (64-bit shifts and `sext64`), `tools/rptp/codegen.py` (`rptp::sext64` emission) and `runtime/src/execution.cpp` (`kFunctDsllv`–`kFunctDsra32`, the `shift_right_arithmetic_64` helper and reserved-field rejection). `Terverifikasi` by execution in the doubleword-shift increment session: `T-DS` covers all nine forms, including literal oracle results, the native differential and the cross-path suite; results are recorded in §8.

**Asymmetry:** none of the nine forms exists in `tools/rptp_gate0_spike.py`, `tools/rptp_ir.py` or `tools/rptp_lower.py`; `tests/test_pipeline_path_contract.py` pins their rejection. `SPECIAL` funct `0x15` is not a defined form and remains unsupported in every path. The canonical decoder and the native harness disagree on a nonzero reserved `shamt` for the variable forms; that divergence is recorded in §5.7 and [RISKS.md](../RISKS.md).

## 5. Discrepancies and asymmetries

[ADR-0005](../DECISIONS/ADR-0005-canonical-execution-path.md) (Proposed; owner acceptance required) proposes `tools/rptp` plus the native harness as the canonical path, freezes the legacy paths and defines the E1–E4 equivalence gates before any retirement. The asymmetries below remain factual and open.

### 5.1 Branch-likely exists in `tools/rptp` and the C++ runtime but not in the legacy pipeline

| Surface | Branch-likely present? | Evidence |
|---|---|---|
| `tools/rptp/isa.py` | Yes, all eight | Source read; `BL`; `ISA` |
| `tools/rptp/cfg.py` / `ir.py` | Yes, both successors and `Control.likely` | Source read; `BL` CFG test |
| `tools/rptp/oracle.py` | Yes, delay-slot nullification and unconditional link | Source read; `BL` |
| `tools/rptp/codegen.py` | Yes, emitted `if (taken)` delay block | Source read; `BL` generated-source and native differential |
| `tools/rptp_gate0_spike.py` | No | Source read: no `0x14`-`0x17` opcode cases and no REGIMM decode |
| `tools/rptp_ir.py` / `rptp_lower.py` | No | Source read: `rptp_lower._SUPPORTED_OPS` has 28 non-likely operations |
| `runtime/src/execution.cpp` | Yes, all eight since PR #41 | Source read: decoder has `0x14`-`0x17`, REGIMM `0x02`/`0x03`/`0x12`/`0x13`, and `rs=31` rejection; `Op` enum has 51 entries after the doubleword-shift increment |
| `tests/test_runtime_execution.py` / `runtime/tests/runtime_tests.cpp` | Yes, four likely and two ordinary-branch test functions; the likely tests were not executed in the original session | Source read; `RT†`; `PB` |

Consequence: a program containing a likely branch is now valid for the `tools/rptp` analysis, its generated C++, and the C++ runtime harness; it still fails closed in the legacy pipeline. The branch-likely native differential compiles generated C++ directly via `tools/rptp/native.py`; it does not exercise `runtime/src/execution.cpp`. No test drives the three paths on the same likely program.

The six ordinary forms have the same asymmetry for the same reason: `tools/rptp`, the C++ harness and the cross-path suite implement them (rows 37-42), while `tools/rptp_gate0_spike.py`, `tools/rptp_ir.py` and `tools/rptp_lower.py` reject them. §4.2 records the contract and evidence.

### 5.2 `LW`/`SW` alignment policy differs only in the legacy paths

| Path | 4-byte alignment check for `LW`/`SW` | Memory model |
|---|---|---|
| `tools/rptp/oracle.py` | Yes: `address & 3` raises `ExecutionError` | Sparse 32 MiB main-RAM model, default-zero reads, per-byte write tracking, KSEG0/KSEG1 translation |
| `tools/rptp/codegen.py` | Yes: emitted `if ((ea & 3u) != 0u) throw ...` | 32 MiB zero-initialized RAM, image loaded at start, KSEG0/KSEG1 translation |
| `tools/rptp_gate0_spike.py` | No | Sparse word map; `LW` throws if the exact word was never initialized |
| `tools/rptp_lower.py` | No | Sparse word map; `load_word` throws on an uninitialized word |
| `runtime/src/execution.cpp` | Yes since PR #43: `(address & 3U) != 0U` fails with `EXEC_MEMORY_FAULT` | Mapped ELF segment regions only; byte-addressed reads and writes; no KSEG translation |

`Terverifikasi` by source reading. Consequence: the same `LW` or `SW` at an address such as `base + 2` now raises in both the new oracle and the runtime harness, but can still succeed or silently read a different word in the legacy paths. `tests/test_runtime_execution.py` has paired runtime/oracle tests (`test_unaligned_word_load_fails_closed_in_runtime_and_oracle`, `test_unaligned_word_store_fails_closed_in_runtime_and_oracle`); `T-LDSD` covers `LD`/`SD`. The cross-path equivalence suite does not include an unaligned-fault case, so the legacy divergence is still untested.

### 5.3 `LD`/`SD` memory and register-width policy differs by path

All paths check 8-byte alignment for `LD` and `SD`, but they do not share one memory or register model:

- `tools/rptp/oracle.py` reads from a 32 MiB default-zero RAM and writes a 128-bit register file. `LD` sign-extends the 64-bit value into the high half of the modeled 128-bit register; `SD` writes the low 64 bits as two little-endian words.
- `tools/rptp/codegen.py` follows the same 128-bit/default-zero model: `state.ram` is a zeroed 32 MiB vector and `sext64` fills the high half for `LD`.
- `tools/rptp_gate0_spike.py` and `tools/rptp_lower.py` use 64-bit registers and an initialized-word map. `LD` requires both words to be present; `load_word` throws on an uninitialized word. The value is combined as an unsigned 64-bit pair, not sign-extended into a 128-bit register.
- `runtime/src/execution.cpp` uses 64-bit registers and mapped ELF regions. `LD` requires one mapped 8-byte range; it does not fill the high half of a 128-bit register because the harness has no such state.

Consequence: a fresh in-range `LD` in the new oracle can return zero, while the legacy path throws and the runtime path may fault if the address is outside a loaded segment. The Level B `LD`/`SD` tests are written against the legacy/runtime 64-bit model (`T-LDSD`, `RT†`), not the new 128-bit model. This is a model difference, not evidence that either model matches R5900 hardware.

### 5.4 There are two Python oracles and two emitters

- **New oracle:** `tools/rptp/oracle.py`, used by `BL`, `PB`, `T-DS` and the `tools/rptp` codegen differential. It implements all 51 Level B instructions and many beyond-Level-B instructions, with a 128-bit register file, 32 MiB default-zero RAM, KSEG translation and alignment checks.
- **Legacy oracle:** `tools/rptp_gate0_spike.execute_oracle`, used by `tests/test_runtime_execution.py` as the expected side of the runtime differential. It implements 28 of the 43 non-likely Level B instructions: the original arithmetic/logic/memory set with `BEQ`/`BNE` as its only conditional branches, but not the six ordinary branch forms or the nine doubleword shifts. It uses 64-bit registers, an initialized-word map and no `LW`/`SW` alignment check.
- **New emitter:** `tools/rptp/codegen.py`, which supports the 51 and many beyond-Level-B instructions, ordinary and branch-likely control, the nine doubleword shifts and the 128-bit model.
- **Legacy emitter:** `tools/rptp_lower.py`, which has exactly 28 supported operations, `BEQ`/`BNE` as its only conditional branches and no branch-likely, ordinary-branch or doubleword-shift forms.
- **C++ harness:** `runtime/src/execution.cpp` supports the 51 Level B operations, ordinary-branch always-executed delay slots, branch-likely nullification, doubleword-shift reserved-field rejection and alignment checks, but with 64-bit registers and mapped ELF regions rather than the 128-bit/default-zero model.

`Terverifikasi` by source reading. The two differential families answer different questions: `BL` and `PB` compare the new oracle against new generated C++; `tests/test_runtime_execution.py` compares the legacy oracle against the C++ runtime harness for the 28 operations the legacy oracle implements, and separately the new oracle against the C++ runtime for the ordinary, likely, alignment and `LD`/`SD` cases. Agreement in one family does not prove agreement with the other, and neither proves hardware behavior.

### 5.5 The 141/142 decoder count is broader than the 51-row Level B set

`tools/rptp/isa.py` declares 142 supported mnemonics at this baseline. One is `NOP`, which is not a catalog entry; the other 141 match catalog entries. Those 141 include all 50 catalog entries in Level B plus 91 Level C entries. Decoder acceptance is not semantics, and the 51-row matrix does not cover the other 91 supported catalog mnemonics. `ISA` exercises their decode/lower paths, but no Level B evidence exists for them. See §6 for the full count reconciliation.

### 5.6 Test-run asymmetries in this session

- `BL`'s native differential passed because `tools/rptp/native.py` found MSVC. The legacy per-instruction tests use a separate `compiler_available()` helper that only checks `cl` on `PATH` or `CXX`; it did not find a compiler, so 26 native cases skipped. This is a test-harness discovery difference, not a semantic result.
- `RT†` tests skipped because `RPTP_RUN_BINARY` was unset and no runtime build was present. The C++ `runtime_tests.cpp` binary was not built.
- `IRL`'s three native cases skipped for the same `cl` discovery reason.
- No full `unittest discover`, no CI run and no CTest run were performed in this session.

### 5.7 Runtime and legacy fail closed on different inputs

The runtime rejects `LQC2`/`SQC2`, control transfers in a delay slot, missing delay slots, unaligned `LW`/`SW`/`LD`/`SD`, a nonzero reserved `rs`/`shamt` on the doubleword shifts, cross-region accesses and unmapped accesses, and `rs=31` on link-likely. The legacy pipeline rejects unsupported operations during lowering and uninitialized `LW` at generated-program runtime, but it does not check `LW`/`SW` alignment or know the likely, ordinary-branch or doubleword-shift forms. The new path and the runtime therefore share the likely `rs=31` rejection policy and both reject a nonzero reserved `rs` on the immediate doubleword shifts, while the canonical decoder still accepts a nonzero reserved `shamt` on the variable forms and the legacy path has no equivalent. These are still different fail-closed surfaces; a clean error from one path is not a shared taxonomy. See [RUNTIME.md](../RUNTIME.md) and [IR_CFG.md](../IR_CFG.md) for the contract-level lists.

## 6. What the numbers mean

These numbers are frequently conflated. They answer different questions, and **none of them is a compatibility metric**.

| Number | What it counts | What it does not mean |
|---:|---|---|
| 224 | Mnemonic entries in `docs/research/r5900-isa.json` | Not verified semantics. Every entry carries `"verified": true` as an undefined bookkeeping marker; see [isa-evidence.md](isa-evidence.md) §1. |
| 216 | Catalog entries that round-trip through the decoder in `ISA` (Level A) | Encoding-field consistency at sampled values only. Excludes 8 COP2 names that collapse to one opaque placeholder. |
| 51 | Level B synthetic instructions: 50 catalog entries plus `NOP` | The 51 are the only rows with an approved reference and executable tests. Includes the 6 ordinary forms, the 8 branch-likely forms and the 9 doubleword shifts. It is not a hardware subset and not a game-compatibility set. |
| 174 | Catalog entries outside Level B (Level C) | Pending approved reference and/or executable semantic tests. Decoder recognition does not move a row out of Level C. |
| 141 | Catalog entries whose mnemonic is in the decoder's supported set | Structural decoder acceptance only. Includes 91 Level C entries; it is not a semantics count. |
| 142 | Supported mnemonics declared by `tools/rptp/isa.py` | 141 catalog matches plus `NOP`. Not a count of tested or approved instructions. |
| 51 | Instructions executed by the C++ runtime harness | The full Level B set, including the 6 ordinary forms, the 8 likely forms, the 9 doubleword shifts and `NOP`. It excludes all Level C instructions and is not the product runtime's final scope. |
| 28 | Instructions supported by the legacy pipeline and the Gate 0 spike | A subset of the 43 non-likely Level B instructions: it excludes the 6 ordinary branch forms, the 9 doubleword shifts, the 8 likely forms and all Level C instructions, and it has no `LW`/`SW` alignment check. |
| 76.96%-86.30% | Aligned-word decoder-acceptance range across the eight boot images in the refreshed census (2026-10-29, current decoder) | Static words in file-backed `PT_LOAD` ranges, including data, padding and tables. Not runtime coverage and not compatibility. Supersedes the pre-`SUBU` 58.3%-69.2% range. |
| 81.81% | Downhill Domination in the refreshed census (338,288 / 413,500) | One image, current decoder. Supersedes the 63.03% post-`SUBU` figure. Not a compatibility percentage. |
| 51/51 | Runtime harness operations that have a decoder/oracle/emitter counterpart | Agreement of two RPTP models, not hardware validation. |

The catalog arithmetic is internally consistent and can be checked without rerunning anything:

- `224 = 50 Level B catalog entries + 174 Level C catalog entries`.
- `216 = 50 Level B catalog entries + 166 Level C entries that round-trip` (the other 8 Level C entries are the COP2 names outside Level A).
- `174 = 91 Level C entries with decoder-supported mnemonics + 83 Level C entries without`.
- `141 = 50 Level B catalog entries + 91 Level C entries`.
- `142 = 141 + NOP`.

So a row can be decoder-supported and still be Level C; a row can be Level A and still be Level C; and a row can be in the 51 and still be absent from the legacy pipeline. Conversely, neither the 51-op runtime harness nor the 28-op legacy pipeline is a small version of the 224-entry catalog: the former is exactly Level B, and the latter is a 28-operation subset of the 43 non-likely Level B instructions.

`Terverifikasi`: the 224/216/8 and 141/83 split is pinned by `tests/test_isa_encodings.py`; the 51-row Level B mapping is pinned by `tests/test_catalog_provenance.py` against [INSTRUCTION_CATALOG.md](../INSTRUCTION_CATALOG.md). `Terverifikasi` as recorded values: the 76.96%-86.30% range and its input hashes are in [BOOT_CENSUS.md](../BOOT_CENSUS.md), and the decoder identity recorded there matches the current `tools/rptp/isa.py`. `Belum diverifikasi`: the census was not rerun for this note.

## 7. Prioritized next-instruction recommendation (planning only)

This section is a **planning recommendation**, not a Gate disposition, not a scope approval and not a claim that any instruction is ready. Any implementation increment still needs an approved reference, an independent test that fails before the change, a fail-closed policy and the provenance record required by [PROVENANCE_PLAN.md](../PROVENANCE_PLAN.md).

### 7.1 Frequency evidence available today

The only frequency evidence in the repository is the refreshed table in [BOOT_CENSUS.md](../BOOT_CENSUS.md), measured 2026-10-29 with the current decoder (142 supported mnemonics). It must not be rerun for this note; another increment owns that measurement. The table is a top-three list per image, not a complete histogram, and the labels are raw encoding identifiers, not instruction semantics.

| Raw label (refreshed top-three entry) | Recorded counts where it appears | Caveat |
|---|---:|---|
| `opcode_0x11` | 23,903 (Downhill); 28,957 (God of War II); 31,396 (Resident Evil 4); 35,149 (Black); 49,291 (NFS Most Wanted); 85,141 (Bully); 133,433 (each GTA sample) | Opaque COP1 placeholder in the decoder; combines transfers, arithmetic and PS2-specific behavior. |
| `opcode_0x31` | 9,381 (Downhill); 12,352 (Resident Evil 4); 13,385 (Black); 18,591 (NFS Most Wanted); 58,096 (Bully); 74,361 (each GTA sample) | Decoder spec names the encoding `LWC1`; census label is only the primary opcode. |
| `opcode_0x39` | 7,081 (Downhill); 10,017 (Resident Evil 4); 16,594 (NFS Most Wanted); 34,483 (Bully); 45,517 (each GTA sample) | Decoder spec names the encoding `SWC1`; census label is only the primary opcode. |
| `opcode_0x12` | 23,930 (God of War II); 29,211 (Black) | Opaque COP2 placeholder; VU macro-mode behavior is not approved semantics. |
| `opcode_0x3e` | 8,219 (God of War II) | Decoder spec names the encoding `SQC2`; still unsupported by the decoder and runtime. |

The pre-refresh table also recorded `opcode_0x1e`, `opcode_0x37` and `opcode_0x3f` as raw-unsupported labels. They no longer appear in the refreshed top-three lists because `LQ`/`SQ` and `LD`/`SD` are decoder-supported; decoder acceptance is still not semantic evidence, and the runtime harness does not execute `LQ`/`SQ`.

`Terverifikasi` as recorded values: the counts and labels above are copied from the refreshed table in [BOOT_CENSUS.md](../BOOT_CENSUS.md). `Belum diverifikasi`: the ranking beyond each image's top three, because no complete histogram was recorded; the census was not rerun, and data/padding remains mixed into every count. `Dugaan`: implementation-complexity ordering below.

### 7.2 Complexity ordering

| Candidate | Frequency evidence | Semantic risk | Implementation cost | Assessment |
|---|---|---|---|---|
| COP1 transfer-only subset: `LWC1`, `SWC1`, and `MFC1`/`MTC1` if a sub-breakdown confirms them | `opcode_0x31`/`0x39` are top-three in three images; `opcode_0x11` is top-three in all eight | Medium: requires a COP1 register file and a reference that covers the transfer semantics; no FPU arithmetic or paired-single needed | Medium: 32-bit register transfers plus load/store addressing, bounded to COP1 data movement | Best next candidate, but gated on reference approval and a census sub-breakdown. |
| Non-likely branch family: `BLEZ`, `BGTZ`, `BLTZ`, `BGEZ`, `BLTZAL`, `BGEZAL` | Not in the recorded top-three lists; frequency unknown | Low: the ordinary branch contract is implemented in `tools/rptp` and the C++ harness; the legacy pipeline still rejects it | Low: promoted to Level B and runtime coverage on 2026-10-30; no remaining implementation work | Executed fallback after COP1 reference approval was unavailable. It closed the runtime gap but did not change the legacy pipeline. |
| Full COP1 arithmetic or paired-single | `opcode_0x11` is the largest label in most images | High: rounding, NaN, flags and PS2-specific paired-single behavior are not in the approved evidence base | High | Do not start from this note. |
| COP2/VU macro mode | `opcode_0x12` is top-three in two images; `opcode_0x3e` (`SQC2`) is top-three in one | High: no approved VU/COP2 semantics | Very high | Blocked pending an owner reference decision. |
| `LQ`/`SQ` and 128-bit GPR runtime state | `LQ`/`SQ` are decoder-supported, so the refreshed table no longer lists `opcode_0x1e`; the pre-refresh counts are not current frequency evidence | High: 128-bit register file changes the runtime model; no approved reference and no Level B evidence; the runtime harness does not execute them | High | Lower priority than COP1 transfers; frequency must be re-established from a supported-label histogram. |

### 7.3 Recommendation

**Primary:** plan the next increment as a **COP1 transfer-only** step, not COP1 arithmetic. Start with `LWC1` and `SWC1`, and add `MFC1`/`MTC1` only if a census sub-breakdown shows they are material. Before implementation:

1. obtain an owner-approved reference that covers COP1 transfer semantics and record its permitted use in [REFERENCES.md](../REFERENCES.md);
2. have the census owner produce a read-only sub-breakdown of `opcode_0x11` and confirm that the transfer forms, not arithmetic, dominate the count;
3. decide whether the COP1 register file is 32-bit or wider and how it coexists with the 64-bit runtime model;
4. define fail-closed behavior for every unsupported COP1 sub-encoding.

**Fallback executed (2026-10-30):** the six non-likely branch forms were promoted to rows 37-42 at Level B, and the native harness and cross-path suite now cover them. Their semantics were already implemented in `tools/rptp`; the increment added the runtime, tests and evidence. The legacy pipeline still rejects them. The COP1 transfer-only recommendation remains primary and unstarted.

**Fallback executed (2026-10-31):** the nine doubleword shift forms were promoted to rows 43-51 at Level B, and the native harness and cross-path suite now cover them. Their semantics were already implemented in `tools/rptp`; the increment added the runtime, tests and evidence and recorded the open variable-`shamt` divergence. The legacy pipeline still rejects them. The COP1 transfer-only recommendation remains primary and unstarted.

**Do not** use the historical `opcode_0x37`/`0x3f` counts as a reason to revisit `LD`/`SD`; the refreshed census no longer lists them as unsupported because those instructions are decoder-supported. **Do not** treat the 76.96%-86.30% decoder-acceptance range as a target or a compatibility score.

`Dugaan`: the primary recommendation is a planning judgement based on the recorded top-three labels and relative implementation cost. It is not a measurement of residual unsupported code and not a Gate 3 scope decision.

## 8. How to reproduce

Run from the repository root in a Developer PowerShell x64 for the MSVC paths. The documentation-only checks do not need a compiler.

```powershell
# Focused evidence set used for this note
python -m unittest tests.test_instruction_branch_likely tests.test_instruction_dshift tests.test_runtime_execution tests.test_cross_path_equivalence tests.test_isa_encodings tests.test_catalog_provenance -v

# Supporting contracts
python -m unittest tests.test_gate0_spike tests.test_ir_lowering tests.test_ir_cfg tests.test_cfg_reachability -v
python -m unittest tests.test_doc_freshness tests.test_doc_budget tests.test_license_headers -v
python tools/check_forbidden_artifacts.py --root .
```

Observed in the original matrix session:

- Focused evidence set: **50 tests, OK, 16 skipped**. All 16 skips were `tests.test_runtime_execution` because `RPTP_RUN_BINARY` was unset.
- Supporting contracts: **59 tests, OK, 3 skipped**. The 3 skips were the native cases in `tests.test_ir_lowering` because `cl`/`c++` was not discoverable through that module's helper.
- Per-instruction batch: **156 tests, OK, 26 skipped** native cases. Python/oracle and lowering-source assertions ran.
- `tests.test_instruction_branch_likely`: **12 tests, OK**, including the MSVC native differential.
- Artifact guard: **passed**.

Observed in the ordinary-branch increment session (2026-10-30):

- `tests.test_instruction_branch_plain`: **12 tests, OK**, including the native differential and signed-low-64-bit cases.
- `tests.test_runtime_execution` with `RPTP_RUN_BINARY`: **26 tests, OK**, including the signed-low-64-bit cases.
- `tests.test_cross_path_equivalence` with `RPTP_RUN_BINARY`: **4 tests, OK**, all three legs active.
- The full suite, CTest, artifact guard and documentation checks are recorded in [VERIFICATION_LOG.md](../VERIFICATION_LOG.md).

Observed in the doubleword-shift increment session (2026-10-31):

- `tests.test_instruction_dshift`: **8 tests, OK**, including the generated-native MSVC differential.
- Focused doubleword-shift evidence set (`tests.test_instruction_dshift tests.test_runtime_execution tests.test_cross_path_equivalence tests.test_pipeline_path_contract`) with `RPTP_LOAD_BINARY` and `RPTP_RUN_BINARY`: **44 tests, OK, 0 skipped**.
- The new `test_doubleword_shift_family_matches_the_python_oracle` run against a pre-change `rptp-run` built at `c1f1ade` failed with exit code 2 (`FAILED (failures=1)`), the expected unsupported-instruction rejection before the harness cases were added.
- Full suite with the built binaries: **541 tests, OK, 0 skipped, 1 expected failure**. CTest: **7/7 passed**. The MSVC wrapper passed the same 541 tests with 37 runtime-CLI skips because it does not set the binary paths.
- The full commands and results are recorded in [VERIFICATION_LOG.md](../VERIFICATION_LOG.md).

To run the runtime-harness evidence that was not run here:

```powershell
cmake --preset windows-msvc
cmake --build --preset windows-msvc
ctest --test-dir build/cmake-msvc --output-on-failure
```

`ctest` sets `RPTP_RUN_BINARY` for `tests.test_runtime_execution` through the CMake test wiring. Alternatively, build `rptp-run` and set `RPTP_RUN_BINARY` to the resulting executable before rerunning the module. Without that binary, the `RT†` evidence remains `Belum diverifikasi` by execution even though the source support is present.

The counts in §6 can be re-read without rerunning the census:

```powershell
python -c "import json; from pathlib import Path; from tools.rptp import isa; e=json.loads(Path('docs/research/r5900-isa.json').read_text(encoding='utf-8'))['instructions']; print(len(e), len(isa.SUPPORTED_MNEMONICS), sum(x['mnemonic'].lower() in isa.SUPPORTED_MNEMONICS for x in e))"
```

The census is deliberately not rerun here; [BOOT_CENSUS.md](../BOOT_CENSUS.md) is the owner of that measurement.

## 9. What remains unverified

- **C++ runtime execution of the 51 Level B instructions:** source-read at the revision baseline; `RT†` tests and `runtime/tests/runtime_tests.cpp` were not executed in the original session. The ordinary-branch increment session did execute `tests/test_runtime_execution.py` (26 tests after review hardening) against a built `rptp-run`; the CTest result is recorded in [VERIFICATION_LOG.md](../VERIFICATION_LOG.md). The doubleword-shift increment session executed the runtime differential for the nine new forms; its observed results are recorded in §8.
- **Legacy native differentials:** 26 per-instruction native cases and 3 `IRL` native cases skipped for compiler-discovery reasons; their Python/oracle assertions passed.
- **New-path Level B differentials other than ordinary, likely and doubleword-shift branches:** no new-path native differential was run for the remaining 28 non-likely rows. `ISA` proves decode and static lowering, not execution.
- **Branch-likely in the runtime harness:** implemented since PR #41 with four likely test functions, but those tests are source-read only in this note; `BL`'s native differential still uses generated C++, not `runtime/src/execution.cpp`.
- **`LW`/`SW` alignment agreement:** runtime and oracle agreement is asserted in `tests/test_runtime_execution.py`, but that module was not executed here; the legacy paths still lack the check and no cross-path test asserts the legacy divergence. The same untested-divergence caveat applies to the KSEG translation difference and the 128-bit vs 64-bit register model.
- **Cross-path likely branches and unaligned faults:** `tests/test_cross_path_equivalence.py` covers arithmetic, logic, shifts, `LW`/`SW`, `LD`/`SD`, the six ordinary branch forms and the nine doubleword shift forms, but not the eight likely forms or an unaligned-fault case. The ordinary-branch increment added the six ordinary forms and the doubleword-shift increment added the nine shift forms to the shared program; the likely forms remain uncovered by this suite.
- **Hardware behavior:** no hardware measurement and no manual use; no claim that any model matches R5900 silicon.
- **Census measurement:** the eight-image table was refreshed on 2026-10-29 with the current decoder (142 supported mnemonics, set SHA-256 `ddc255931fb49ecb0c8bc778037344e2e05ac32d8898fd77586db3162c904e13`), so the 76.96%-86.30% range is current recorded evidence rather than a pre-`SUBU` figure. It measures decoder acceptance over data-inclusive `PT_LOAD` words, not function-level or runtime coverage; this note did not rerun it, and only each image's top three labels are recorded.
- **Gate, provenance and compatibility:** no Gate disposition, no clean-room certification and no compatibility claim. Gate 3 remains not passed; Gate 2 remains open and read-only.

## 10. References

Internal evidence:

- [INSTRUCTION_CATALOG.md](../INSTRUCTION_CATALOG.md) — per-instruction synthetic model and limits.
- [isa-evidence.md](isa-evidence.md) — Level A/B/C definitions, counts and reference-scope observations.
- [IR_CFG.md](../IR_CFG.md) — IR, CFG, branch-likely contract and legacy pipeline boundary.
- [RUNTIME.md](../RUNTIME.md) — 51-op runtime harness contract, alignment policy and fail-closed errors.
- [REFERENCES.md](../REFERENCES.md) — approved `RPTP-REF-*` rows and permitted-use limits.
- [PROVENANCE_PLAN.md](../PROVENANCE_PLAN.md) — per-increment evidence obligations.
- [CLEAN_ROOM_AUDIT.md](../CLEAN_ROOM_AUDIT.md) — component-level provenance status.
- [BOOT_CENSUS.md](../BOOT_CENSUS.md) — recorded read-only frequency evidence; not rerun here.
- [VERIFICATION_LOG.md](../VERIFICATION_LOG.md) — dated historical verification record.

Approved references used by the matrix rows: `RPTP-REF-001`, `RPTP-REF-002`, `RPTP-REF-013`, `RPTP-REF-014` and `RPTP-REF-015`, within the limits recorded in [REFERENCES.md](../REFERENCES.md). `NOP` has no specific reference and is an RPTP test definition. No Sony manual, sealed-project material or unapproved catalog citation is used as evidence in this note.
