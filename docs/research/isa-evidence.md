# R5900 ISA catalog evidence levels

- **Status date:** 2026-10-30
- **Baseline:** `origin/main` after the approved-reference branch-likely increment merged (`fcae099`, 2026-10-30); §3 and §4 were revised by the ordinary-branch evidence increment later on 2026-10-30.
- **Subject:** [`docs/research/r5900-isa.json`](r5900-isa.json) — schema version 1, 224 instruction entries, four cited sources, `"verified": true` on every entry.
- **Purpose:** Define honest, auditable evidence levels for the catalog so that its `"verified"` boolean, its `semantics` text and its page citations are not read as semantic proof or as an approved reference.
- **Scope:** Documentation and evidence classification only. This document adds no instruction semantics, corrects no catalog entry, quotes no text from the cited manuals, changes no JSON data and records no Gate, provenance or legal disposition. Only the owner can approve a reference.
- **Related:** [REFERENCES.md](../REFERENCES.md), [PROVENANCE_PLAN.md](../PROVENANCE_PLAN.md), [INSTRUCTION_CATALOG.md](../INSTRUCTION_CATALOG.md), [tests/test_isa_encodings.py](../../tests/test_isa_encodings.py), [ADR-0003](../DECISIONS/ADR-0003-sealed-source-clean-room-policy.md).

## 1. The `"verified": true` boolean is not evidence

All 224 catalog entries carry `"verified": true`, and all 224 carry a page citation to one of the catalog's cited documents. Neither fact is a verification result:

- Nothing in the repository defines what the boolean means. There is no recorded method, per-entry evidence pointer, reviewer, date or acceptance criterion behind it.
- `tests/test_isa_encodings.py::test_research_catalog_is_verified_and_complete` only asserts that the boolean is `True` for every entry (`self.assertIs(entry["verified"], True)`) and that the citation string is non-empty. The test locks the boolean in place; it does not check it.
- The catalog's page citations point into documents that are **not approved references** in [REFERENCES.md](../REFERENCES.md). The two Sony manuals and the catalog's fourth source (`ps2tek`) have no `RPTP-REF-*` row, and the manual PDFs are not stored in this repository. A citation string is a pointer, not a permission to use the cited document.
- A boolean that is always true and has no definition is not a confidence signal, so it must not be quoted as "verified semantics", and no catalog claim may be used as a hardware fact, as an approved implementation reference or as release evidence on the strength of the boolean, the `semantics` text or a page number.

**The `"verified"` flag is not semantic evidence. Evidence has to be recorded separately and per claim.** Sections 2–3 define the levels this repository can actually support today.

## 2. Evidence levels

The catalog mixes several different things: an encoding map (opcode/`funct`/operand fields), English `semantics` prose, citation strings, and an unqualified "verified" flag. The three levels below separate what the repository can demonstrate.

### Level A — `decoder-crosscheck` (structural encoding agreement only)

- **Basis:** `tests/test_isa_encodings.py` rebuilds one canonical 32-bit word per catalog entry from the entry's `class`, `opcode`, `funct` and `operands` fields and decodes it with `tools/rptp/isa.py`. The test requires the same mnemonic, the documented operand fields and a valid decode.
- **Coverage:** 216 of 224 entries. The test asserts exactly 216 encoded entries and 224 total. The eight excluded entries are the COP2 forms `QMFC2`, `QMTC2`, `CFC2`, `CTC2`, `BC2F`, `BC2FL`, `BC2T` and `BC2TL`; the test's `SKIPPED` map records why each cannot be represented at mnemonic granularity (the decoder exposes all COP2 macro-mode encodings as one opaque `cop2` placeholder).
- **What it proves:** the catalog's encoding fields are internally consistent with the decoder tables for the sampled field values, and no field mix-up in the test's sample changes the decoded mnemonic or operands. It also pins the MMI subtable layout, the standalone 11-bit function space, the MMI shift-amount field and the per-class entry counts.
- **What it does not prove:** semantics; hardware behavior; the correctness of any page citation; the `"verified"` flag; independence (the catalog and the decoder are both RPTP artifacts whose stated origins overlap, so agreement between them is not an independent cross-check of the underlying sources); or that an encoding the decoder rejects is invalid. The entry `semantics` text is never executed, `writes_hi_lo` is not compared per entry, and `delay_slot` is used only to compute an expected branch target.
- **What would be needed to move past Level A:** an approved neutral reference for the entry's encoding and operation, plus a test that fails if the operation is modeled wrongly (Level B); or owner approval of the cited manual with recorded permitted use and limits.

### Level B — `test-defined + approved reference`

- **Basis:** the instruction has (1) an approved `RPTP-REF-*` row in [REFERENCES.md](../REFERENCES.md) that supports the encoding/operation used, and (2) executable RPTP tests that would fail if the modeled behavior is wrong — literal-expectation assertions, an oracle differential, an IR-lowering native differential, or the Gate 0 synthetic fixture and its native differential.
- **Coverage:** the synthetic instruction subset in [INSTRUCTION_CATALOG.md](../INSTRUCTION_CATALOG.md) — 42 instructions at this commit, mapped row by row in §3, including the six ordinary branch forms and the eight branch-likely forms added by the 2026-10-30 approved-reference increments (`RPTP-REF-015`, §3.1 and §3.2).
- **What it proves:** for each listed instruction, an approved generic reference supports the cited encoding/operation, and RPTP tests exercise the modeled behavior. The model itself is an RPTP test definition and is narrower than R5900 hardware wherever the limits column says so.
- **What it does not prove:** complete R5900 semantics; hardware behavior beyond the permitted-use scope of the cited reference; or the catalog entry's `semantics` text for that instruction (the catalog is not the evidence). It also does not promote any other catalog entry: the 183 catalog entries outside §3 remain at Level C even when the decoder recognizes their mnemonic.
- **Dual-model differential tests are not Level B by themselves.** `tests/test_native_diff.py`, `tests/test_oracle_edges.py` and `tests/test_oracle_fuzz.py` compare an RPTP Python oracle with RPTP generated C++. Agreement between two RPTP implementations shows internal consistency; it is not an approved reference and does not establish hardware behavior.

### Level C — `unverified / pending approved reference`

- **Basis:** the only support for the claim is the catalog's own `semantics` prose and a page citation to a document that is not an approved reference. No approved `RPTP-REF-*` and no executable test in this repository establishes the claim.
- **Coverage:** every catalog claim outside §3 — 183 of 224 entries at this commit (`NOP` is one of the 42 Level B instructions but is a decoder synonym rather than a catalog entry). This includes the eight COP2 entries that cannot round-trip (Level A also excludes them), the MMI/MMI0–MMI3/SPECIAL2 families, the HI/LO instructions, the REGIMM traps, the unaligned load/store forms, and the COP2 `LQC2`/`SQC2` entries.
- **Decoder labels are not evidence.** `tools/rptp/isa.py` attaches `generic-mips-cross-checked`, `manual-cross-checked` and `provisional` labels to its own decoder specs. After the 2026-10-30 wording correction the decoder docstring states that these labels are documentation metadata, not certification, and that the R5900 manual they partly refer to is pending an owner decision; even so, `manual-cross-checked` is not an approved reference and cannot be read as owner approval. An implemented oracle/emitter path for such an instruction does not move it to Level B.
- **What would change it:** owner approval of a cited document plus recorded permitted use and limits as a reference row; or re-derivation from an approved neutral reference plus an independent test; or removal/quarantine of the entry. Until then, no semantic claim outside §3 is approved for implementation or release use.

| Level | Label | Basis | What it proves | Sufficient for |
|---|---|---|---|---|
| A | `decoder-crosscheck` | `tests/test_isa_encodings.py` round-trip | Catalog fields agree with the RPTP decoder at the sampled values | Structural consistency only; not semantics |
| B | `test-defined + approved reference` | Approved `RPTP-REF-*` + executable tests | The cited operation is supported by an approved reference and tested in RPTP's synthetic model | The narrow synthetic model, within the recorded limits |
| C | `unverified / pending approved reference` | Catalog prose + page citation only | That a citation string exists | Nothing; pending owner review |

## 3. Supported synthetic subset mapped to approved references and tests

The table below is the complete list of RPTP synthetic instructions that have both an approved reference and executable tests: 42 instructions at this commit. The behavior descriptions live in [INSTRUCTION_CATALOG.md](../INSTRUCTION_CATALOG.md); this table records evidence provenance only and its limits column is part of the record.

| Instruction | Encoding | Approved reference | Test evidence | Limits |
|---|---|---|---|---|
| `ADDIU` | I-type opcode `0x09` | `RPTP-REF-001` | `tests/test_gate0_spike.py`, `tests/test_ir_lowering.py` | 32-bit model only; no complete 64-bit R5900 arithmetic claim. |
| `DADDIU` | I-type opcode `0x19` | `RPTP-REF-015` (DADDIU p. 127) | `tests/test_instruction_daddiu.py` | Narrow synthetic 64-bit model; generic MIPS64 reference, not a complete R5900 validation. |
| `DADDU` | SPECIAL funct `0x2D`, `shamt=0` | `RPTP-REF-015` (DADDU p. 132) | `tests/test_instruction_daddu.py` | Narrow synthetic 64-bit model; generic MIPS64 reference. |
| `ADDU` | SPECIAL funct `0x21`, `shamt=0` | `RPTP-REF-001` | `tests/test_gate0_spike.py`, `tests/test_ir_lowering.py` | 32-bit model; no overflow trap and no 64-bit claim. |
| `SUBU` | SPECIAL funct `0x23`, `shamt=0` | `RPTP-REF-015` (SUBU p. 355) | `tests/test_instruction_subu.py` | The reference marks a non-word-value source UNPREDICTABLE; RPTP resolves it by truncation, which is an RPTP test definition. |
| `SLL` | SPECIAL funct `0x00`, `rs=0`, 5-bit `shamt` | `RPTP-REF-002` | `tests/test_instruction_sll.py` | The sign-extension bridge into the 64-bit register array is RPTP test-defined. |
| `AND` | SPECIAL funct `0x24`, `shamt=0` | `RPTP-REF-001`, `RPTP-REF-002` (function code and name) | `tests/test_instruction_register_logic.py` | 64-bit operation width is RPTP test-defined. |
| `OR` | SPECIAL funct `0x25`, `shamt=0` | `RPTP-REF-001`, `RPTP-REF-002` | `tests/test_instruction_register_logic.py` | 64-bit operation width is RPTP test-defined. |
| `XOR` | SPECIAL funct `0x26`, `shamt=0` | `RPTP-REF-001`, `RPTP-REF-002` | `tests/test_instruction_register_logic.py` | 64-bit operation width is RPTP test-defined. |
| `NOR` | SPECIAL funct `0x27`, `shamt=0` | `RPTP-REF-001`, `RPTP-REF-002` | `tests/test_instruction_nor.py` | 64-bit operation width is RPTP test-defined. |
| `SLT` | SPECIAL funct `0x2A`, `shamt=0` | `RPTP-REF-001`, `RPTP-REF-002` | `tests/test_instruction_slt.py` | Signed 64-bit comparison width is RPTP test-defined. |
| `SLTU` | SPECIAL funct `0x2B`, `shamt=0` | `RPTP-REF-002` | `tests/test_instruction_sltu.py` | `RPTP-REF-001`'s SLTU row conflicts with `RPTP-REF-002` and is not used; unsigned 64-bit width is RPTP test-defined. |
| `SLTI` | I-type opcode `0x0A` | `RPTP-REF-014` | `tests/test_instruction_slti.py` | Sign-extension and signed comparison from the reference; 64-bit comparison width is RPTP test-defined. |
| `SLTIU` | I-type opcode `0x0B` | `RPTP-REF-014` | `tests/test_instruction_sltiu.py` | Sign-extended immediate plus unsigned comparison from the reference; 64-bit width is RPTP test-defined. |
| `ANDI` | I-type opcode `0x0C` | `RPTP-REF-001` (encoding) | `tests/test_instruction_logical.py`, `tests/test_instruction_logical_width.py` | Zero-extending immediate model is synthetic; the 64-bit width record cites `RPTP-REF-013` although that row's permitted use is scoped to `LUI` (see §6). |
| `ORI` | I-type opcode `0x0D` | `RPTP-REF-001` (encoding) | `tests/test_instruction_ori.py`, `tests/test_instruction_logical.py`, `tests/test_instruction_logical_width.py` | Full 64-bit logical operation recorded against `RPTP-REF-013`; that row's permitted-use scope is `LUI` (see §6). |
| `XORI` | I-type opcode `0x0E` | `RPTP-REF-001` (encoding) | `tests/test_instruction_logical.py`, `tests/test_instruction_logical_width.py` | Full 64-bit logical operation recorded against `RPTP-REF-013`; that row's permitted-use scope is `LUI` (see §6). |
| `LUI` | I-type opcode `0x0F`, `rs=0` | `RPTP-REF-013` (Revision 5.04, p. 225) | `tests/test_instruction_lui.py` | Revised 6.03 page was inaccessible; shifted/sign-extended model is synthetic. |
| `LW` | I-type opcode `0x23` | `RPTP-REF-001` | `tests/test_gate0_spike.py`, `tests/test_ir_lowering.py` | No MMIO, TLB, cache, alignment-exception or timing behavior. |
| `SW` | I-type opcode `0x2B` | `RPTP-REF-001` | `tests/test_gate0_spike.py`, `tests/test_ir_lowering.py` | No MMIO, TLB, cache, alignment-exception or timing behavior. |
| `LD` | I-type opcode `0x37` | `RPTP-REF-015` (LD p. 207) | `tests/test_instruction_ld_sd.py`, `tests/test_runtime_execution.py`, `runtime/tests/runtime_tests.cpp` | Two-word composition, 32-bit effective address and fail-closed alignment are RPTP test definitions. |
| `SD` | I-type opcode `0x3F` | `RPTP-REF-015` (SD p. 327) | `tests/test_instruction_ld_sd.py`, `tests/test_runtime_execution.py`, `runtime/tests/runtime_tests.cpp` | Two-word split, 32-bit effective address and fail-closed alignment are RPTP test definitions. |
| `BEQ` | I-type opcode `0x04` | `RPTP-REF-001` | `tests/test_gate0_spike.py`, `tests/test_ir_lowering.py` | Full R5900 branch behavior is not claimed; static targets must stay inside the synthetic code model. |
| `BNE` | I-type opcode `0x05` | `RPTP-REF-001` | `tests/test_gate0_spike.py`, `tests/test_ir_lowering.py` | Full R5900 branch behavior is not claimed; static targets must stay inside the synthetic code model. |
| `BLEZ` | I-type opcode `0x06` | `RPTP-REF-015` (BLEZ p. 83) | `tests/test_instruction_branch_plain.py`, `tests/test_runtime_execution.py`, `tests/test_cross_path_equivalence.py`, `tests/test_isa_encodings.py` | Taken when the signed low 64 bits of `rs` are `<= 0`; delay slot executes on both outcomes; no timing or exception claim. |
| `BGTZ` | I-type opcode `0x07` | `RPTP-REF-015` (BGTZ p. 81) | `tests/test_instruction_branch_plain.py`, `tests/test_runtime_execution.py`, `tests/test_cross_path_equivalence.py`, `tests/test_isa_encodings.py` | Taken when the signed low 64 bits of `rs` are `> 0`; delay slot executes on both outcomes; no timing or exception claim. |
| `BLTZ` | REGIMM opcode `0x01`, `rt=0x00` | `RPTP-REF-015` (BLTZ p. 85) | `tests/test_instruction_branch_plain.py`, `tests/test_runtime_execution.py`, `tests/test_cross_path_equivalence.py`, `tests/test_isa_encodings.py` | Taken when the signed low 64 bits of `rs` are `< 0`; delay slot executes on both outcomes; no timing or exception claim. |
| `BGEZ` | REGIMM opcode `0x01`, `rt=0x01` | `RPTP-REF-015` (BGEZ p. 76) | `tests/test_instruction_branch_plain.py`, `tests/test_runtime_execution.py`, `tests/test_cross_path_equivalence.py`, `tests/test_isa_encodings.py` | Taken when the signed low 64 bits of `rs` are `>= 0`; delay slot executes on both outcomes; no timing or exception claim. |
| `BLTZAL` | REGIMM opcode `0x01`, `rt=0x10` | `RPTP-REF-015` (BLTZAL p. 86) | `tests/test_instruction_branch_plain.py`, `tests/test_runtime_execution.py`, `tests/test_cross_path_equivalence.py`, `tests/test_isa_encodings.py` | Writes `GPR[31] = pc + 8` unconditionally, including on a not-taken branch; `rs = 31` is rejected fail-closed because the reference marks it UNPREDICTABLE; the rejection is RPTP policy. |
| `BGEZAL` | REGIMM opcode `0x01`, `rt=0x11` | `RPTP-REF-015` (BGEZAL p. 77) | `tests/test_instruction_branch_plain.py`, `tests/test_runtime_execution.py`, `tests/test_cross_path_equivalence.py`, `tests/test_isa_encodings.py` | Writes `GPR[31] = pc + 8` unconditionally, including on a not-taken branch; `rs = 31` is rejected fail-closed because the reference marks it UNPREDICTABLE; the rejection is RPTP policy. |
| `BEQL` | I-type opcode `0x14` | `RPTP-REF-015` (BEQL p. 75) | `tests/test_instruction_branch_likely.py`, `tests/test_isa_encodings.py` | Likely-branch nullification; low-64-bit comparison, 32-bit PC masking and trace/step accounting are RPTP test definitions; no timing or exception claim. |
| `BNEL` | I-type opcode `0x15` | `RPTP-REF-015` (BNEL p. 91) | `tests/test_instruction_branch_likely.py`, `tests/test_isa_encodings.py` | Same likely-branch model as `BEQL`; no timing or exception claim. |
| `BLEZL` | I-type opcode `0x16` | `RPTP-REF-015` (BLEZL p. 84) | `tests/test_instruction_branch_likely.py`, `tests/test_isa_encodings.py` | Taken when the signed low 64 bits of `rs` are `<= 0`; same test-defined model limits. |
| `BGTZL` | I-type opcode `0x17` | `RPTP-REF-015` (BGTZL p. 82) | `tests/test_instruction_branch_likely.py`, `tests/test_isa_encodings.py` | Taken when the signed low 64 bits of `rs` are `> 0`; same test-defined model limits. |
| `BLTZL` | REGIMM opcode `0x01`, `rt=0x02` | `RPTP-REF-015` (BLTZL p. 89) | `tests/test_instruction_branch_likely.py`, `tests/test_isa_encodings.py` | Taken when the signed low 64 bits of `rs` are `< 0`; same test-defined model limits. |
| `BGEZL` | REGIMM opcode `0x01`, `rt=0x03` | `RPTP-REF-015` (BGEZL p. 80) | `tests/test_instruction_branch_likely.py`, `tests/test_isa_encodings.py` | Taken when the signed low 64 bits of `rs` are `>= 0`; same test-defined model limits. |
| `BLTZALL` | REGIMM opcode `0x01`, `rt=0x12` | `RPTP-REF-015` (BLTZALL p. 87) | `tests/test_instruction_branch_likely.py`, `tests/test_isa_encodings.py` | Written `GPR[31] = pc + 8` unconditionally; `rs = 31` rejected fail-closed because the reference marks it UNPREDICTABLE; the rejection is RPTP policy. |
| `BGEZALL` | REGIMM opcode `0x01`, `rt=0x13` | `RPTP-REF-015` (BGEZALL p. 78) | `tests/test_instruction_branch_likely.py`, `tests/test_isa_encodings.py` | Written `GPR[31] = pc + 8` unconditionally; `rs = 31` rejected fail-closed because the reference marks it UNPREDICTABLE; the rejection is RPTP policy. |
| `J` | J-type opcode `0x02` | `RPTP-REF-001` | `tests/test_gate0_spike.py`, `tests/test_ir_lowering.py` | Static targets must stay inside the synthetic code model. |
| `JAL` | J-type opcode `0x03` | `RPTP-REF-001` | `tests/test_gate0_spike.py`, `tests/test_ir_lowering.py` | No full R5900 call convention or pipeline behavior is claimed. |
| `JR` | SPECIAL funct `0x08`, `rt=rd=shamt=0` | `RPTP-REF-001` | `tests/test_gate0_spike.py`, `tests/test_ir_lowering.py` | No return-address stack, speculation or exception behavior. |
| `NOP` | SPECIAL word `0x00000000` | none specific; RPTP test definition | `tests/test_gate0_spike.py`, `tests/test_ir_lowering.py` | Only the encoded all-zero NOP is recognized. |

NOP is the only Level B instruction without a catalog entry (the catalog lists 224 mnemonics and NOP is a decoder synonym for the all-zero word). All other 41 Level B instructions are catalog entries; the remaining 183 catalog entries stay at Level C.

### 3.1 Branch-likely forms (added 2026-10-30, `RPTP-REF-015`)

The eight branch-likely forms are Level B rows 25-32. `RPTP-REF-015` (MIPS64 Revision 5.04, pages 75, 78, 80, 82, 84, 87, 89 and 91) supports their encodings, PC-relative target, equality/zero-test conditions, take-only delay-slot execution, the unconditional `GPR[31] = PC + 8` link for the two link forms and the `rs = 31` UNPREDICTABLE restriction. `tests/test_instruction_branch_likely.py` covers both outcomes for all eight forms, delay-slot register and memory effects, `$zero`, unconditional link writes, the `rs = 31` rejection, CFG successors, deterministic generated C++ and a native differential against the oracle; `tests/test_isa_encodings.py` exercises the decoder and lowering path for the same forms. The branch-likely rows are implemented in the `tools/rptp` decoder/oracle/emitter path; the older `tools/rptp_ir.py`/`tools/rptp_lower.py` pipeline remains unchanged and does not implement them. The low-64-bit comparison, 32-bit PC masking, trace/step accounting, `$zero` suppression, memory representation and the fail-closed `rs = 31` rejection are RPTP test definitions, not hardware facts, and no branch-prediction, timing, exception or TLB behavior is claimed.

### 3.2 Ordinary branch forms (added 2026-10-30, `RPTP-REF-015`)

The six non-likely branch forms are Level B rows 37-42 and the newest addition in this family. `RPTP-REF-015` (MIPS64 Revision 5.04, pages 76, 77, 81, 83, 85 and 86) supports their encodings, the 18-bit signed PC-relative target added to the delay-slot address, the signed zero-test conditions, the delay slot executing after the branch on both outcomes, the unconditional `GPR[31] = PC + 8` link for `BLTZAL`/`BGEZAL` and the `rs = 31` UNPREDICTABLE restriction. `tests/test_instruction_branch_plain.py` covers both outcomes for all six forms, delay-slot register and memory effects, `$zero`, unconditional link writes, the `rs = 31` rejection, CFG successors, deterministic generated C++ and a native differential against the oracle; `tests/test_runtime_execution.py` and `runtime/tests/runtime_tests.cpp` add the independent runtime differential and direct C++ cases; `tests/test_cross_path_equivalence.py` drives the same six forms through the Python oracle, generated C++ and `rptp-run`; `tests/test_isa_encodings.py` exercises the decoder and lowering path. The decoder and oracle already recognized these six forms at the increment base; this change promotes them to Level B, adds the fail-closed `rs = 31` rejection for the link forms, and adds native and cross-path coverage. The older `tools/rptp_ir.py`/`tools/rptp_lower.py` pipeline remains unchanged: its only conditional branches are `BEQ` and `BNE`, so it rejects these six. The low-64-bit comparison, 32-bit PC masking, trace/step accounting, `$zero` suppression, memory representation and the fail-closed `rs = 31` rejection are RPTP test definitions, not hardware facts, and no branch-prediction, timing, exception or TLB behavior is claimed.

## 4. Catalog coverage inventory (structural only)

These are structural counts of the JSON data and the decoder, not semantic claims. The test-pinned counts are asserted by `tests/test_isa_encodings.py`; the others are a read-only inspection at this commit.

| Property | Count | Notes |
|---|---|---|
| Catalog entries | 224 | Pinned by `test_research_catalog_is_verified_and_complete`; mnemonics unique. |
| `"verified": true` entries | 224 | No definition; see §1. |
| Entries with a citation string | 224 | Non-empty citation is asserted; the page pointer is not checked against any source. |
| Citations to the Sony EE Core Instruction Set Manual | 216 | Includes the 8 branch-likely entries; manual use is not approved. |
| Citations to the Sony VU User's Manual | 8 | Exactly the eight COP2 entries excluded from Level A. |
| Level A round-trip entries | 216 | Pinned by `test_every_encodable_entry_decodes_exactly` and `test_skip_list_is_small_explicit_and_complete`. |
| Entries with no mnemonic-level decoder representation | 8 | The COP2 forms; decoder exposes an opaque `cop2` placeholder. |
| Catalog entries with a decoder-supported mnemonic | 141 | `ins.supported` is true for these; structural only. |
| Catalog entries without a decoder-supported mnemonic | 83 | Decode either as an unsupported named spec or as `unknown_*`; decode acceptance is not semantics. |
| Level B instructions | 42 | §3 table; 41 are catalog entries, plus `NOP`. |
| Catalog entries at Level C | 183 | Everything outside §3. |

Class distribution of the 224 entries (from the JSON only): `special` 52, `mips3` 41, `special2` 25, `mmi0` 25, `mmi2` 22, `mmi1` 18, `regimm` 16, `mmi3` 13, `cop2` 10, `lqsq` 2. The decoder declares 142 supported mnemonics after the branch-likely increment (134 before it), and 141 of the 224 catalog entries are among them. The decoder-label distribution for the 216 entries that match a decoder spec by mnemonic is `generic-mips-cross-checked` 77, `manual-cross-checked` 131 and `provisional` 8; the decoder docstring now documents these labels as metadata, and they are not evidence (§2, Level C).

## 5. The eight COP2 entries (pending schema decision)

The eight entries that cannot be round-trip tested are all COP2 forms, and all eight cite the VU User's Manual in the catalog. The page pointers below are copied from the catalog's own citation strings; they are not verified by this document.

| Mnemonic | Catalog class | Page pointer recorded in the catalog |
|---|---|---|
| `QMFC2` | `cop2` | VU User's Manual v6.0 p. 237 |
| `CFC2` | `cop2` | VU User's Manual v6.0 p. 234 |
| `QMTC2` | `cop2` | VU User's Manual v6.0 p. 238 |
| `CTC2` | `cop2` | VU User's Manual v6.0 p. 235 |
| `BC2F` | `cop2` | VU User's Manual v6.0 p. 230 |
| `BC2T` | `cop2` | VU User's Manual v6.0 p. 231 |
| `BC2FL` | `cop2` | VU User's Manual v6.0 p. 232 |
| `BC2TL` | `cop2` | VU User's Manual v6.0 p. 233 |

The decoder currently maps primary opcode `0x12` to a single opaque `cop2` placeholder, and `tests/test_isa_encodings.py::test_cop2_entries_are_exposed_as_an_opaque_placeholder` asserts that behavior. That is a decoder design state, not evidence for any of the eight names. Whether the catalog should keep, merge, drop or re-derive these entries is an owner decision (§7).

## 6. Reference-scope and wording observations

These are audit observations, not semantic corrections and not catalog edits:

1. **`RPTP-REF-013` scope gap.** [REFERENCES.md](../REFERENCES.md) scopes that row's permitted use to narrow `LUI` semantics, while a later recorded note in the same file cites `RPTP-REF-013` for the `ORI`/`XORI` (and by extension `ANDI`) 64-bit logical-immediate model. The row and the note need reconciliation by the owner/Lead; this increment does not change either.
2. **Decoder wording (corrected 2026-10-30).** The decoder docstring used to describe its sources as "neutral public documentation" including the Sony/Toshiba EE Core Instruction Set Manual and used the label vocabulary without qualification. The approved-reference branch-likely increment rewrote that docstring: it records the R5900 manual as pending an owner decision, describes `ps2tek` as a secondary cross-check that is not an `RPTP-REF`, and states that `generic-mips-cross-checked`/`manual-cross-checked`/`provisional` are documentation metadata rather than certification. The label values are unchanged (137 `verification=MANUAL` specs, 131 of them matched to catalog mnemonics) and remain not evidence; `tools/rptp/cfg.py` still surfaces the label in diagnostics. This increment neither edits `tools/rptp/` nor treats the label as an approved reference.
3. **Test wording (corrected 2026-10-30).** The encoding-conformance test used to describe the JSON as "the repository's verified research catalog (224 entries, all `verified: true`)" and its test name said the catalog "is verified". The branch-likely increment renamed it to `test_research_catalog_entries_are_present_and_complete` and documented the boolean as a catalog bookkeeping marker that is not hardware verification; §1 of this document relies on that corrected wording.
4. **`ps2tek`.** The catalog's fourth source `ps2tek` is a secondary cross-check only. It is not recorded as an `RPTP-REF-*` row, is not an approved reference, and must not be used for behavior claims; the same applies to its mentions in `tools/rptp/isa.py` and `docs/research/function-discovery.md`. This increment adds no reference row for it.
5. **No manual files in the repository.** The catalog stores the manual URLs only; the PDFs are not committed (`tests/test_catalog_provenance.py` guards that no manual-named file appears in the repository). Repository hygiene requires this to stay true even if the owner later approves a limited citation use.

## 7. Owner decisions needed

The following are questions for the owner. This document records evidence and options only; it does not answer them, does not propose a semantic correction and does not claim that any answer is legally sufficient.

1. **Sony manual use.** Should limited use of the two Sony manuals (EE Core Instruction Set Manual v6.0 and VU User's Manual v6.0) be approved, rejected or approved with limits? If approved, the permitted use, limits and access date must be recorded as reference rows, and any implementation that relies on them must be labeled with that reference. Current status (relayed 2026-10-30): manual use is postponed; only the approved `RPTP-REF-001`–`017` may be used. If it is rejected, the catalog entries and any manual-derived implementation or wording that cite those documents must be quarantined and re-derived or removed.
2. **Catalog quarantine.** Should `docs/research/r5900-isa.json` be quarantined until this evidence classification and the reference decision are final? Options include (a) keep it as clearly-labelled, non-authoritative research data with this document linked from the map, (b) mark every entry as pending in the JSON itself after an owner-approved schema change, or (c) remove the catalog from the repository until it can be re-derived from approved references. Option (b) would break `tests/test_isa_encodings.py`, so it is a code-and-test decision, not just a documentation edit.
3. **Per-entry evidence enum.** Should the `"verified": true` boolean be replaced by an evidence class such as `citation_only`, `decoder_crosscheck`, `test_defined`, `approved_reference` or `pending_owner`, with a test that allows only those values? If yes, who records the per-entry value, and which vocabulary is authoritative? A migration requires a JSON schema change, test changes and an owner decision; this increment does not touch the JSON.
4. **The eight COP2 entries.** Should the catalog keep all eight COP2 forms as unresolved placeholders, collapse them into a single opaque `cop2` entry, or re-derive them from an approved VU/COP2 reference? They currently cannot be round-trip tested, and their citations are exactly the eight VU-manual citations in §5.
5. **`ps2tek`.** Should `ps2tek` stay a secondary, unrecorded cross-check (current status), be removed from the catalog metadata and the code comments that cite it, or be formally reviewed for reference status later? It is not a permitted reference now and must not be used for behavior claims, and this increment adds no reference row for it.
6. **Reference-scope reconciliation and evidence vocabulary.** The wording part of the decoder/label issue was corrected by the 2026-10-30 branch-likely increment; two questions remain. Should `RPTP-REF-013`'s permitted-use cell be widened to cover the recorded `ORI`/`XORI`/`ANDI` model, or should those notes be re-derived against a reference whose row already covers them? And should the decoder's `manual-cross-checked`/`provisional` label vocabulary be renamed or mapped onto the three levels in this document?

## 8. Non-claims

- This document does not claim that any catalog entry is correct or incorrect, verified or unverified in a legal sense; it records what the repository can and cannot demonstrate.
- It is not an R5900 hardware reference, not a compatibility list, not a Gate disposition and not a clean-room certification.
- It does not approve any manual, any page citation or any vendor document, and it does not conclude that any use is legally permissible.
- It does not change the accepted Gate 0 scope, the Gate 3 status, the runtime harness, the decoder behavior or the catalog data.
- Mentioning a page number or a source name that already appears in the catalog is a pointer to recorded metadata, not a reproduction of the cited text.

## 9. How to reproduce the inventory

The structural checks in this document are reproducible from the repository:

    python -m unittest tests.test_isa_encodings -v
    python -m unittest tests.test_instruction_branch_plain -v
    python -m unittest tests.test_instruction_branch_likely -v
    python -m unittest tests.test_catalog_provenance -v

The catalog and decoder counts in §4 are a read-only inspection of `docs/research/r5900-isa.json`, `tools/rptp/isa.py` and `tests/test_isa_encodings.py`; the tests above pin the 224/216 split and the Level B table check pins that every instruction in [INSTRUCTION_CATALOG.md](../INSTRUCTION_CATALOG.md) has a row in §3. A green run shows only that this classification is internally consistent; it does not turn any Level C entry into evidence.
