# Instruction semantics evidence matrix

- **Status date:** 2026-10-30
- **Baseline:** `origin/main` commit `0944c84e8ed11c2d7db5d54ad23671b9a8de869d` (the merge that brought the branch-likely increment into `main`).
- **Scope:** Documentation and evidence classification only. This note adds no instruction semantics, changes no code, test, catalog entry or Gate status, and makes no compatibility claim.
- **Subject:** the 36-instruction Level B synthetic subset in [INSTRUCTION_CATALOG.md](../INSTRUCTION_CATALOG.md) and [isa-evidence.md](isa-evidence.md), including the eight branch-likely forms. There is no separate 36 + 8 set: the eight likely forms are rows 25-32 of the same 36-row matrix.
- **Method:** source reading at the baseline commit plus the focused test runs recorded in §8. No retail data, emulator or recompiler source, Sony manual, or unapproved reference was used. Manual use remains unapproved, so no manual text is quoted or relied on here.
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
- a statement that the 36 instructions are correct R5900 hardware behavior;
- a statement that the 28-op runtime harness represents the recompiler product path;
- a statement that decoder-supported mnemonics outside the 36 have approved semantics;
- a replacement for [INSTRUCTION_CATALOG.md](../INSTRUCTION_CATALOG.md), [IR_CFG.md](../IR_CFG.md), [RUNTIME.md](../RUNTIME.md) or [REFERENCES.md](../REFERENCES.md).

**Terverifikasi:** the repository has two Python implementation paths and one C++ runtime harness:

- **N** = the `tools/rptp/` package: `isa.py`, `cfg.py`, `ir.py`, `oracle.py`, `codegen.py`, `native.py`.
- **L** = the legacy pipeline: `tools/rptp_gate0_spike.py`, `tools/rptp_ir.py`, `tools/rptp_lower.py`.
- **R** = the C++ harness: `runtime/src/execution.cpp` and `runtime/tools/rptp_run.cpp`.

The runtime harness is a test vehicle, not a product runtime. [RUNTIME.md](../RUNTIME.md) records its 28-instruction subset and its explicit non-goals.

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

The per-instruction batch ran 156 tests: 130 passed and 26 native cases skipped because `cl` was not discoverable through those modules' compiler helper. The skipped native cases do not invalidate the Python/oracle assertions recorded in the same modules, but they are not claimed as native evidence.

### 2.3 Provenance codes

| Code | Meaning |
|---|---|
| `P-G0` | Level B. The instruction is in the accepted Gate 0 synthetic scope; the Gate 0 component status is `Provisional independent`. Not certified. |
| `P-EXP` | Level B. Added after the Gate 0 disposition; the runtime/recompiler expansion component status is `Recorded`. Not certified. |
| `P-BL` | Level B. Added by the 2026-10-30 branch-likely increment; expansion status `Recorded`. Not certified. |
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
| 19 | `LW` | I-type opcode `0x23` | `OK` | `N + L*` | `N + L`; fallthrough | `N + L*` | `R*`; no 4-byte alignment check |
| 20 | `SW` | I-type opcode `0x2B` | `OK` | `N + L*` | `N + L`; fallthrough | `N + L*` | `R*`; no 4-byte alignment check |
| 21 | `LD` | I-type opcode `0x37` | `OK` | `N + L*` | `N + L`; fallthrough | `N + L*` | `R`; requires 8-byte alignment |
| 22 | `SD` | I-type opcode `0x3F` | `OK` | `N + L*` | `N + L`; fallthrough | `N + L*` | `R`; requires 8-byte alignment |
| 23 | `BEQ` | I-type opcode `0x04` | `OK` | `N + L` | `N + L`; both successors; delay always | `N + L` | `R`; delay always |
| 24 | `BNE` | I-type opcode `0x05` | `OK` | `N + L` | `N + L`; both successors; delay always | `N + L` | `R`; delay always |
| 25 | `BEQL` | I-type opcode `0x14` | `OK` | `N only` | `N only`; both successors; delay only if taken | `N only` | `none` |
| 26 | `BNEL` | I-type opcode `0x15` | `OK` | `N only` | `N only`; both successors; delay only if taken | `N only` | `none` |
| 27 | `BLEZL` | I-type opcode `0x16` | `OK` | `N only` | `N only`; both successors; delay only if taken | `N only` | `none` |
| 28 | `BGTZL` | I-type opcode `0x17` | `OK` | `N only` | `N only`; both successors; delay only if taken | `N only` | `none` |
| 29 | `BLTZL` | REGIMM opcode `0x01`, `rt=0x02` | `OK` | `N only` | `N only`; both successors; delay only if taken | `N only` | `none` |
| 30 | `BGEZL` | REGIMM opcode `0x01`, `rt=0x03` | `OK` | `N only` | `N only`; both successors; delay only if taken | `N only` | `none` |
| 31 | `BLTZALL` | REGIMM opcode `0x01`, `rt=0x12` | `OK`; `rs=31` rejected | `N only` | `N only`; both successors; delay only if taken; link `pc+8` | `N only` | `none` |
| 32 | `BGEZALL` | REGIMM opcode `0x01`, `rt=0x13` | `OK`; `rs=31` rejected | `N only` | `N only`; both successors; delay only if taken; link `pc+8` | `N only` | `none` |
| 33 | `J` | J-type opcode `0x02` | `OK` | `N + L` | `N + L`; one direct successor; delay always | `N + L` | `R`; delay always |
| 34 | `JAL` | J-type opcode `0x03` | `OK` | `N + L` | `N + L`; one direct successor; link `pc+8`; delay always | `N + L` | `R`; delay always |
| 35 | `JR` | SPECIAL funct `0x08`, `rt=rd=shamt=0` | `OK` | `N + L` | `N + L`; dynamic target; delay always | `N + L` | `R`; delay always |
| 36 | `NOP` | all-zero word `0x00000000` | `OK` | `N + L` | `N + L`; fallthrough | `N + L` | `R` |

`Terverifikasi`: every row above was checked by reading the named source in `tools/rptp/isa.py`, `tools/rptp/cfg.py`, `tools/rptp/ir.py`, `tools/rptp/oracle.py`, `tools/rptp/codegen.py`, `tools/rptp_gate0_spike.py`, `tools/rptp_ir.py`, `tools/rptp_lower.py` and `runtime/src/execution.cpp`. The runtime column records source support only; it is not execution evidence for this session.

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
| 19 | `LW` | `RPTP-REF-001` | `G0`, `IRL`, `RT†` | `P-G0` | Legacy and runtime paths do **not** check 4-byte alignment; `N` does. No MMIO, TLB, cache, alignment-exception or timing model. |
| 20 | `SW` | `RPTP-REF-001` | `G0`, `IRL`, `RT†` | `P-G0` | Legacy and runtime paths do **not** check 4-byte alignment; `N` does. No MMIO, TLB, cache or timing model. |
| 21 | `LD` | `RPTP-REF-015` p. 207 | `T-LDSD`, `RT†` | `P-EXP` | Requires 8-byte alignment; 32-bit effective address; two-word little-endian composition. `N` models 32 MiB default-zero RAM and a 128-bit register file; legacy/runtime use initialized or mapped word storage and 64-bit registers. |
| 22 | `SD` | `RPTP-REF-015` p. 327 | `T-LDSD`, `RT†` | `P-EXP` | Requires 8-byte alignment; splits `rt` into two words; `N` and legacy/runtime agree on the low 64 bits but not on the full memory/register model (§5.3). |
| 23 | `BEQ` | `RPTP-REF-001` | `G0`, `IRL`, `RT†` | `P-G0` | Delay slot always executes; full 64-bit comparison; static target must stay inside the synthetic code model. |
| 24 | `BNE` | `RPTP-REF-001` | `G0`, `IRL`, `RT†` | `P-G0` | Delay slot always executes; full 64-bit comparison; static target must stay inside the synthetic code model. |
| 25 | `BEQL` | `RPTP-REF-015` p. 75 | `BL` | `P-BL` | Delay slot executes only when taken; not-taken delay slot is nullified. `N only`; no runtime or legacy implementation. Low-64-bit comparison, 32-bit PC masking and trace/step accounting are RPTP test definitions. |
| 26 | `BNEL` | `RPTP-REF-015` p. 91 | `BL` | `P-BL` | Same likely-branch model as `BEQL`; `N only`; no runtime or legacy implementation. |
| 27 | `BLEZL` | `RPTP-REF-015` p. 84 | `BL` | `P-BL` | Taken when signed low 64 bits of `rs` are `<= 0`; `N only`; no runtime or legacy implementation. |
| 28 | `BGTZL` | `RPTP-REF-015` p. 82 | `BL` | `P-BL` | Taken when signed low 64 bits of `rs` are `> 0`; `N only`; no runtime or legacy implementation. |
| 29 | `BLTZL` | `RPTP-REF-015` p. 89 | `BL` | `P-BL` | Taken when signed low 64 bits of `rs` are `< 0`; `N only`; no runtime or legacy implementation. |
| 30 | `BGEZL` | `RPTP-REF-015` p. 80 | `BL` | `P-BL` | Taken when signed low 64 bits of `rs` are `>= 0`; `N only`; no runtime or legacy implementation. |
| 31 | `BLTZALL` | `RPTP-REF-015` p. 87 | `BL` | `P-BL` | `GPR[31] = pc + 8` is written unconditionally; `rs=31` is rejected fail-closed because the reference marks it UNPREDICTABLE; the rejection is RPTP policy. `N only`; no runtime or legacy implementation. |
| 32 | `BGEZALL` | `RPTP-REF-015` p. 78 | `BL` | `P-BL` | Same unconditional link and `rs=31` rejection as `BLTZALL`; `N only`; no runtime or legacy implementation. |
| 33 | `J` | `RPTP-REF-001` | `G0`, `IRL`, `RT†` | `P-G0` | Static target must stay inside the synthetic code model; delay slot always executes. |
| 34 | `JAL` | `RPTP-REF-001` | `G0`, `IRL`, `RT†` | `P-G0` | Writes `pc+8` to `r31`; delay slot always executes; no full call convention or pipeline claim. |
| 35 | `JR` | `RPTP-REF-001` | `G0`, `IRL`, `RT†` | `P-G0` | Dynamic target is the low 32 bits of `rs`; no return-address stack, speculation or exception behavior; delay slot always executes. |
| 36 | `NOP` | none specific; RPTP test definition | `G0`, `IRL`, `RT†` | `P-TD` | Only the encoded all-zero word is recognized as `NOP`. |

`Terverifikasi` for the reference mapping: each approved-reference cell was checked against [REFERENCES.md](../REFERENCES.md) and [isa-evidence.md](isa-evidence.md) §3. `Belum diverifikasi` for the `RT†` cells: the runtime harness was not executed in this session. The reference pins support the encoding/operation model within the recorded limits; they do not establish complete R5900 semantics.

### 4.1 Branch-likely rows in detail

The eight likely forms are rows 25-32. Their shared implementation contract is:

- The condition is evaluated from the architectural state **before** the delay slot.
- On a taken branch the delay slot executes and the next PC is the direct target.
- On a not-taken branch the delay slot is nullified and the next PC is `pc + 8`.
- The CFG records both the direct target and the fallthrough, target first. Nullification is an execution-time effect, not a reachability filter.
- `BLTZALL` and `BGEZALL` write `GPR[31] = pc + 8` unconditionally, including when the branch is not taken.
- `rs = 31` on either link form is rejected fail-closed as RPTP policy because the approved reference marks the result UNPREDICTABLE.

`Terverifikasi` by source reading: `tools/rptp/isa.py` (`LIKELY_MNEMONICS`, `LINK_LIKELY_MNEMONICS`, target calculation and `rs=31` rejection), `tools/rptp/oracle.py` (`nullify_delay` and unconditional link write), `tools/rptp/ir.py` (`Control.likely`, `link_reg`) and `tools/rptp/codegen.py` (`if (taken) {` around delay operations). `Terverifikasi` by execution: `BL` passed 12 of 12 tests, including the MSVC native differential against the new oracle. `ISA` also decodes and statically lowers all eight forms, but it is structural evidence, not semantic execution evidence.

**Asymmetry:** none of the eight forms exists in `runtime/src/execution.cpp`, `tools/rptp_gate0_spike.py`, `tools/rptp_ir.py` or `tools/rptp_lower.py`. The runtime rejects their encodings with `EXEC_UNSUPPORTED_INSTRUCTION`. The older pipeline cannot analyze or lower them. The runtime differential tests therefore cannot cover this family, and the C++ runtime harness is not evidence for it.

## 5. Discrepancies and asymmetries

### 5.1 Branch-likely exists in `tools/rptp` but not in the runtime or the legacy pipeline

| Surface | Branch-likely present? | Evidence |
|---|---|---|
| `tools/rptp/isa.py` | Yes, all eight | Source read; `BL`; `ISA` |
| `tools/rptp/cfg.py` / `ir.py` | Yes, both successors and `Control.likely` | Source read; `BL` CFG test |
| `tools/rptp/oracle.py` | Yes, delay-slot nullification and unconditional link | Source read; `BL` |
| `tools/rptp/codegen.py` | Yes, emitted `if (taken)` delay block | Source read; `BL` generated-source and native differential |
| `tools/rptp_gate0_spike.py` | No | Source read: no `0x14`-`0x17` opcode cases and no REGIMM decode |
| `tools/rptp_ir.py` / `rptp_lower.py` | No | Source read: `rptp_lower._SUPPORTED_OPS` has 28 non-likely operations |
| `runtime/src/execution.cpp` | No | Source read: decoder switch has no `0x14`-`0x17` and no REGIMM; `Op` enum has 28 entries |
| `tests/test_runtime_execution.py` / `runtime/tests/runtime_tests.cpp` | No likely case | Source read |

Consequence: a program containing a likely branch is a valid subject for the `tools/rptp` analysis and native differential, but it fails closed in the C++ runtime harness and in the legacy pipeline. The branch-likely native differential compiles generated C++ directly via `tools/rptp/native.py`; it does not exercise `runtime/src/execution.cpp`.

### 5.2 `LW`/`SW` alignment policy differs by path

| Path | 4-byte alignment check for `LW`/`SW` | Memory model |
|---|---|---|
| `tools/rptp/oracle.py` | Yes: `address & 3` raises `ExecutionError` | Sparse 32 MiB main-RAM model, default-zero reads, per-byte write tracking, KSEG0/KSEG1 translation |
| `tools/rptp/codegen.py` | Yes: emitted `if ((ea & 3u) != 0u) throw ...` | 32 MiB zero-initialized RAM, image loaded at start, KSEG0/KSEG1 translation |
| `tools/rptp_gate0_spike.py` | No | Sparse word map; `LW` throws if the exact word was never initialized |
| `tools/rptp_lower.py` | No | Sparse word map; `load_word` throws on an uninitialized word |
| `runtime/src/execution.cpp` | No | Mapped ELF segment regions only; byte-addressed reads and writes; no KSEG translation |

`Terverifikasi` by source reading. Consequence: the same `LW` or `SW` at an address such as `base + 2` can succeed in the runtime harness, raise in the new oracle, and either throw or read a different word in the legacy path. No test currently asserts this divergence; `T-LDSD` covers `LD`/`SD` alignment, not `LW`/`SW`.

### 5.3 `LD`/`SD` memory and register-width policy differs by path

All paths check 8-byte alignment for `LD` and `SD`, but they do not share one memory or register model:

- `tools/rptp/oracle.py` reads from a 32 MiB default-zero RAM and writes a 128-bit register file. `LD` sign-extends the 64-bit value into the high half of the modeled 128-bit register; `SD` writes the low 64 bits as two little-endian words.
- `tools/rptp/codegen.py` follows the same 128-bit/default-zero model: `state.ram` is a zeroed 32 MiB vector and `sext64` fills the high half for `LD`.
- `tools/rptp_gate0_spike.py` and `tools/rptp_lower.py` use 64-bit registers and an initialized-word map. `LD` requires both words to be present; `load_word` throws on an uninitialized word. The value is combined as an unsigned 64-bit pair, not sign-extended into a 128-bit register.
- `runtime/src/execution.cpp` uses 64-bit registers and mapped ELF regions. `LD` requires one mapped 8-byte range; it does not fill the high half of a 128-bit register because the harness has no such state.

Consequence: a fresh in-range `LD` in the new oracle can return zero, while the legacy path throws and the runtime path may fault if the address is outside a loaded segment. The Level B `LD`/`SD` tests are written against the legacy/runtime 64-bit model (`T-LDSD`, `RT†`), not the new 128-bit model. This is a model difference, not evidence that either model matches R5900 hardware.

### 5.4 There are two Python oracles and two emitters

- **New oracle:** `tools/rptp/oracle.py`, used by `BL` and by the `tools/rptp` codegen differential. It implements all 36 Level B instructions and many beyond-Level-B instructions, with a 128-bit register file, 32 MiB default-zero RAM, KSEG translation and alignment checks.
- **Legacy oracle:** `tools/rptp_gate0_spike.execute_oracle`, used by `tests/test_runtime_execution.py` as the expected side of the runtime differential. It implements only the 28 non-likely Level B instructions, with 64-bit registers, an initialized-word map and no `LW`/`SW` alignment check.
- **New emitter:** `tools/rptp/codegen.py`, which supports the 36 and many beyond-Level-B instructions, branch-likely control and the 128-bit model.
- **Legacy emitter:** `tools/rptp_lower.py`, which has exactly 28 supported operations and no branch-likely.

`Terverifikasi` by source reading. The two differential families answer different questions: `BL` compares new oracle vs new generated C++; `tests/test_runtime_execution.py` compares legacy oracle vs the C++ runtime harness. Agreement in one family does not prove agreement with the other, and neither proves hardware behavior.

### 5.5 The 141/142 decoder count is broader than the 36-row Level B set

`tools/rptp/isa.py` declares 142 supported mnemonics at this baseline. One is `NOP`, which is not a catalog entry; the other 141 match catalog entries. Those 141 include all 35 catalog entries in Level B plus 106 Level C entries. Decoder acceptance is not semantics, and the 36-row matrix does not cover the other 106 supported catalog mnemonics. `ISA` exercises their decode/lower paths, but no Level B evidence exists for them. See §6 for the full count reconciliation.

### 5.6 Test-run asymmetries in this session

- `BL`'s native differential passed because `tools/rptp/native.py` found MSVC. The legacy per-instruction tests use a separate `compiler_available()` helper that only checks `cl` on `PATH` or `CXX`; it did not find a compiler, so 26 native cases skipped. This is a test-harness discovery difference, not a semantic result.
- `RT†` tests skipped because `RPTP_RUN_BINARY` was unset and no runtime build was present. The C++ `runtime_tests.cpp` binary was not built.
- `IRL`'s three native cases skipped for the same `cl` discovery reason.
- No full `unittest discover`, no CI run and no CTest run were performed in this session.

### 5.7 Runtime and legacy fail closed on different inputs

The runtime rejects `LQC2`/`SQC2`, control transfers in a delay slot, missing delay slots, unaligned `LD`/`SD`, cross-region accesses and unmapped accesses. The legacy pipeline rejects unsupported operations during lowering and uninitialized `LW` at generated-program runtime. The new path rejects `rs=31` for link-likely at decode time. These are different fail-closed surfaces; a clean error from one path is not a shared taxonomy. See [RUNTIME.md](../RUNTIME.md) and [IR_CFG.md](../IR_CFG.md) for the contract-level lists.

## 6. What the numbers mean

These numbers are frequently conflated. They answer different questions, and **none of them is a compatibility metric**.

| Number | What it counts | What it does not mean |
|---:|---|---|
| 224 | Mnemonic entries in `docs/research/r5900-isa.json` | Not verified semantics. Every entry carries `"verified": true` as an undefined bookkeeping marker; see [isa-evidence.md](isa-evidence.md) §1. |
| 216 | Catalog entries that round-trip through the decoder in `ISA` (Level A) | Encoding-field consistency at sampled values only. Excludes 8 COP2 names that collapse to one opaque placeholder. |
| 36 | Level B synthetic instructions: 35 catalog entries plus `NOP` | The 36 are the only rows with an approved reference and executable tests. Includes the 8 branch-likely forms. It is not a hardware subset and not a game-compatibility set. |
| 189 | Catalog entries outside Level B (Level C) | Pending approved reference and/or executable semantic tests. Decoder recognition does not move a row out of Level C. |
| 141 | Catalog entries whose mnemonic is in the decoder's supported set | Structural decoder acceptance only. Includes 106 Level C entries; it is not a semantics count. |
| 142 | Supported mnemonics declared by `tools/rptp/isa.py` | 141 catalog matches plus `NOP`. Not a count of tested or approved instructions. |
| 28 | Instructions executed by the C++ runtime harness, and separately by the legacy pipeline | Exactly the non-likely Level B subset. It excludes the 8 likely forms and all Level C instructions. It is not the product runtime's final scope. |
| 58.3%-69.2% | Pre-`SUBU` aligned-word decoder-acceptance range across eight boot images | Static words in file-backed `PT_LOAD` ranges, including data, padding and tables. Not runtime coverage and not compatibility. |
| 63.03% | Post-`SUBU` Downhill Domination decoder-acceptance ratio (260,641 / 413,500) | One image, one decoder revision. Not a compatibility percentage. |
| 28/28 | Runtime harness operations that have a decoder/oracle/emitter counterpart | Agreement of two RPTP models, not hardware validation. |

The catalog arithmetic is internally consistent and can be checked without rerunning anything:

- `224 = 35 Level B catalog entries + 189 Level C catalog entries`.
- `216 = 35 Level B catalog entries + 181 Level C entries that round-trip` (the other 8 Level C entries are the COP2 names outside Level A).
- `189 = 106 Level C entries with decoder-supported mnemonics + 83 Level C entries without`.
- `141 = 35 Level B catalog entries + 106 Level C entries`.
- `142 = 141 + NOP`.

So a row can be decoder-supported and still be Level C; a row can be Level A and still be Level C; and a row can be in the 36 and still be implemented only in `tools/rptp` and absent from the runtime. Conversely, the 28-op runtime harness is not a small version of the 224-entry catalog: it is exactly the non-likely Level B set.

`Terverifikasi`: the 224/216/8 and 141/83 split is pinned by `tests/test_isa_encodings.py`; the 36-row Level B mapping is pinned by `tests/test_catalog_provenance.py` against [INSTRUCTION_CATALOG.md](../INSTRUCTION_CATALOG.md). `Belum diverifikasi`: the 58.3%-69.2% and 63.03% figures were not remeasured in this session; they are the recorded values in [BOOT_CENSUS.md](../BOOT_CENSUS.md).

## 7. Prioritized next-instruction recommendation (planning only)

This section is a **planning recommendation**, not a Gate disposition, not a scope approval and not a claim that any instruction is ready. Any implementation increment still needs an approved reference, an independent test that fails before the change, a fail-closed policy and the provenance record required by [PROVENANCE_PLAN.md](../PROVENANCE_PLAN.md).

### 7.1 Frequency evidence available today

The only frequency evidence in the repository is the dated table in [BOOT_CENSUS.md](../BOOT_CENSUS.md). It must not be rerun for this note; another increment owns that measurement. The table is a top-three list per image, not a complete histogram, and the labels are raw encoding identifiers, not instruction semantics.

| Raw label (historical top-three entry) | Recorded counts where it appears | Caveat |
|---|---:|---|
| `opcode_0x11` | 23,903 (Downhill); 28,957 (God of War II); 31,396 (Resident Evil 4); 35,149 (Black); 49,291 (NFS Most Wanted); 85,141 (Bully); 133,433 (each GTA sample) | Opaque COP1 placeholder in the decoder; combines transfers, arithmetic and PS2-specific behavior. |
| `opcode_0x31` | 58,096 (Bully); 74,361 (each GTA sample) | Decoder spec names the encoding `LWC1`; census label is only the primary opcode. |
| `opcode_0x39` | 34,483 (Bully); 45,517 (each GTA sample) | Decoder spec names the encoding `SWC1`; census label is only the primary opcode. |
| `opcode_0x12` | 23,930 (God of War II); 29,211 (Black) | Opaque COP2 placeholder; VU macro-mode behavior is not approved semantics. |
| `opcode_0x1e` | 12,620 (Resident Evil 4); 16,920 (God of War II); 25,759 (Black) | Decoder spec names the encoding `LQ`; requires 128-bit GPR state in the runtime. |
| `opcode_0x37` / `opcode_0x3f` | 13,623-53,806 and 15,142-46,493 | These are `LD`/`SD`, now supported; the census table predates that support, so these counts must not be used to justify adding them again. |

`Terverifikasi` as recorded values: the counts and labels above are copied from [BOOT_CENSUS.md](../BOOT_CENSUS.md). `Belum diverifikasi`: the residual ranking after the `SUBU`, `LD`, `SD` and branch-likely increments; the table was not re-run, and data/padding remains mixed into every count. `Dugaan`: implementation-complexity ordering below.

### 7.2 Complexity ordering

| Candidate | Frequency evidence | Semantic risk | Implementation cost | Assessment |
|---|---|---|---|---|
| COP1 transfer-only subset: `LWC1`, `SWC1`, and `MFC1`/`MTC1` if a sub-breakdown confirms them | `opcode_0x31`/`0x39` are top-three in three images; `opcode_0x11` is top-three in all eight | Medium: requires a COP1 register file and a reference that covers the transfer semantics; no FPU arithmetic or paired-single needed | Medium: 32-bit register transfers plus load/store addressing, bounded to COP1 data movement | Best next candidate, but gated on reference approval and a census sub-breakdown. |
| Non-likely branch family: `BLEZ`, `BGTZ`, `BLTZ`, `BGEZ`, `BLTZAL`, `BGEZAL` | Not in the recorded top-three lists; frequency unknown | Low: the ordinary branch contract is already implemented in `tools/rptp` and the legacy 28-op path | Low-medium: promote evidence, add runtime support with the existing delay-slot model | Best fallback if COP1 reference approval is unavailable. It closes a path gap rather than chasing a large opaque family. |
| Full COP1 arithmetic or paired-single | `opcode_0x11` is the largest label in most images | High: rounding, NaN, flags and PS2-specific paired-single behavior are not in the approved evidence base | High | Do not start from this note. |
| COP2/VU macro mode | `opcode_0x12` is top-three in two images | High: no approved VU/COP2 semantics | Very high | Blocked pending an owner reference decision. |
| `LQ`/`SQ` and 128-bit GPR runtime state | `opcode_0x1e` is top-three in three images | High: 128-bit register file changes the runtime model; no approved reference for the Level B table | High | Lower priority than COP1 transfers despite the frequency. |

### 7.3 Recommendation

**Primary:** plan the next increment as a **COP1 transfer-only** step, not COP1 arithmetic. Start with `LWC1` and `SWC1`, and add `MFC1`/`MTC1` only if a census sub-breakdown shows they are material. Before implementation:

1. obtain an owner-approved reference that covers COP1 transfer semantics and record its permitted use in [REFERENCES.md](../REFERENCES.md);
2. have the census owner produce a read-only sub-breakdown of `opcode_0x11` and confirm that the transfer forms, not arithmetic, dominate the count;
3. decide whether the COP1 register file is 32-bit or wider and how it coexists with the 64-bit runtime model;
4. define fail-closed behavior for every unsupported COP1 sub-encoding.

**Fallback:** if step 1 cannot be met, promote the six non-likely branch forms to a tested evidence row and close the runtime gap; their semantics are already implemented in `tools/rptp` and are closer to the existing branch contract. This is a lower-frequency, lower-risk increment.

**Do not** use `opcode_0x37`/`0x3f` as a reason to revisit `LD`/`SD`; those labels are historical and the instructions are already supported. **Do not** treat the 63.03% decoder-acceptance figure as a target or a compatibility score.

`Dugaan`: the primary recommendation is a planning judgement based on the recorded top-three labels and relative implementation cost. It is not a measurement of residual unsupported code and not a Gate 3 scope decision.

## 8. How to reproduce

Run from the repository root in a Developer PowerShell x64 for the MSVC paths. The documentation-only checks do not need a compiler.

```powershell
# Focused evidence set used for this note
python -m unittest tests.test_instruction_branch_likely tests.test_runtime_execution tests.test_isa_encodings tests.test_catalog_provenance -v

# Supporting contracts
python -m unittest tests.test_gate0_spike tests.test_ir_lowering tests.test_ir_cfg tests.test_cfg_reachability -v
python -m unittest tests.test_doc_freshness tests.test_doc_budget tests.test_license_headers -v
python tools/check_forbidden_artifacts.py --root .
```

Observed in this session:

- Focused evidence set: **50 tests, OK, 16 skipped**. All 16 skips were `tests.test_runtime_execution` because `RPTP_RUN_BINARY` was unset.
- Supporting contracts: **59 tests, OK, 3 skipped**. The 3 skips were the native cases in `tests.test_ir_lowering` because `cl`/`c++` was not discoverable through that module's helper.
- Per-instruction batch: **156 tests, OK, 26 skipped** native cases. Python/oracle and lowering-source assertions ran.
- `tests.test_instruction_branch_likely`: **12 tests, OK**, including the MSVC native differential.
- Artifact guard: **passed**.

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

- **C++ runtime execution of the 28 non-likely instructions:** source-read only in this session; `RT†` tests and `runtime/tests/runtime_tests.cpp` were not executed.
- **Legacy native differentials:** 26 per-instruction native cases and 3 `IRL` native cases skipped for compiler-discovery reasons; their Python/oracle assertions passed.
- **New-path Level B differentials other than branch-likely:** no new-path native differential was run for the 28 non-likely rows. `ISA` proves decode and static lowering, not execution.
- **Branch-likely in the runtime harness:** no such implementation or test exists. `BL`'s native differential uses generated C++, not `runtime/src/execution.cpp`.
- **`LW`/`SW` alignment divergence:** documented from source but not covered by a test that asserts the paths disagree. The same applies to the KSEG translation difference and the 128-bit vs 64-bit register model.
- **Hardware behavior:** no hardware measurement and no manual use; no claim that any model matches R5900 silicon.
- **Census residual ranking:** the eight-image table is pre-`SUBU` and pre-`LD`/`SD`; the post-`SUBU` refresh is one image. No rerun was performed for this note.
- **Gate, provenance and compatibility:** no Gate disposition, no clean-room certification and no compatibility claim. Gate 3 remains not passed; Gate 2 remains open and read-only.

## 10. References

Internal evidence:

- [INSTRUCTION_CATALOG.md](../INSTRUCTION_CATALOG.md) — per-instruction synthetic model and limits.
- [isa-evidence.md](isa-evidence.md) — Level A/B/C definitions, counts and reference-scope observations.
- [IR_CFG.md](../IR_CFG.md) — IR, CFG, branch-likely contract and legacy pipeline boundary.
- [RUNTIME.md](../RUNTIME.md) — 28-op runtime harness contract and fail-closed errors.
- [REFERENCES.md](../REFERENCES.md) — approved `RPTP-REF-*` rows and permitted-use limits.
- [PROVENANCE_PLAN.md](../PROVENANCE_PLAN.md) — per-increment evidence obligations.
- [CLEAN_ROOM_AUDIT.md](../CLEAN_ROOM_AUDIT.md) — component-level provenance status.
- [BOOT_CENSUS.md](../BOOT_CENSUS.md) — recorded read-only frequency evidence; not rerun here.
- [VERIFICATION_LOG.md](../VERIFICATION_LOG.md) — dated historical verification record.

Approved references used by the matrix rows: `RPTP-REF-001`, `RPTP-REF-002`, `RPTP-REF-013`, `RPTP-REF-014` and `RPTP-REF-015`, within the limits recorded in [REFERENCES.md](../REFERENCES.md). `NOP` has no specific reference and is an RPTP test definition. No Sony manual, sealed-project material or unapproved catalog citation is used as evidence in this note.
