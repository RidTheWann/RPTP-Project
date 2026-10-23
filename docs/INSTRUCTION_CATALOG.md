# RPTP synthetic instruction catalog

- **Status date:** 2026-10-23
- **Scope:** narrow synthetic ELF32/EM_MIPS differential spike, not a complete R5900 implementation and not a compatibility list.
- **Provenance:** [ADR-0003](DECISIONS/ADR-0003-sealed-source-clean-room-policy.md), [PROVENANCE_PLAN.md](PROVENANCE_PLAN.md) and [REFERENCES.md](REFERENCES.md).
- **Gate status:** Gate 3 is not passed. This catalog records what the current synthetic tests actually exercise. A documented IR, candidate-only CFG analysis and deterministic C++ lowering now exist for the same subset, including the `ANDI` and `XORI` logical immediates, the `LUI` shifted immediate and the `AND`/`OR`/`XOR` register operations; see [IR_CFG.md](IR_CFG.md).

## Verification levels

- **Native differential:** the decoder, oracle and emitted C++ are exercised by a synthetic program; the generated native state equals the oracle state under a supported host compiler. The Windows/MSVC run is recorded in [VERIFICATION_LOG.md](VERIFICATION_LOG.md).
- **Native IR-lowering differential:** the validated IR is passed to a separate lowering module, the generated C++ state machine is compiled, and its native state equals the oracle state. This proves the synthetic-generated path only. The current tests are in `tests/test_ir_lowering.py`, `tests/test_instruction_logical.py`, `tests/test_instruction_lui.py` and `tests/test_instruction_register_logic.py`.
- **Static IR/CFG:** the decoder feeds a host-Python IR and fail-closed block analysis. This does not by itself prove native lowering or runtime behavior. The current tests are in `tests/test_ir_cfg.py`.
- **Decode only:** the decoder recognizes the encoding but no native differential exists. No instruction currently has this status.
- **Unsupported:** the decoder rejects the encoding explicitly. Unsupported instructions are never silently skipped or lowered to an approximation.

## Supported synthetic subset

| Instruction | Encoding | Current model | Evidence | Limits |
|---|---|---|---|---|
| `ADDIU` | I-type opcode `0x09` | Sign-extend the 16-bit immediate; add the low 32 bits of `rs`; sign-extend the 32-bit result to the spike's 64-bit register array. | Gate 0 fixture and native differential; [GATE0_REVIEW.md](GATE0_REVIEW.md). | This is the spike's 32-bit model, not complete 64-bit R5900 arithmetic. |
| `ADDU` | SPECIAL funct `0x21`, `shamt=0` | Add the low 32 bits of `rs` and `rt`; sign-extend the 32-bit result to 64 bits. | Gate 0 fixture and native differential. | No overflow trap and no 64-bit R5900 claim. |
| `AND` | SPECIAL funct `0x24`, `shamt=0` | Bitwise AND the full modeled 64-bit `rs` and `rt`; write `rd`. A write to `$zero` is discarded. | Separate 24-instruction register-logical program, oracle checks and native IR-lowering differential in `tests/test_instruction_register_logic.py`. | Added after the Gate 0 disposition; it is not part of the accepted Gate 0 fixture scope. The 64-bit operation width is an RPTP test-defined model, not a complete R5900 hardware claim. |
| `OR` | SPECIAL funct `0x25`, `shamt=0` | Bitwise OR the full modeled 64-bit `rs` and `rt`; write `rd`. A write to `$zero` is discarded. | Separate 24-instruction register-logical program, oracle checks and native IR-lowering differential in `tests/test_instruction_register_logic.py`. | Added after the Gate 0 disposition; it is not part of the accepted Gate 0 fixture scope. The 64-bit operation width is an RPTP test-defined model, not a complete R5900 hardware claim. |
| `XOR` | SPECIAL funct `0x26`, `shamt=0` | Bitwise XOR the full modeled 64-bit `rs` and `rt`; write `rd`. A write to `$zero` is discarded. | Separate 24-instruction register-logical program, oracle checks and native IR-lowering differential in `tests/test_instruction_register_logic.py`. | Added after the Gate 0 disposition; it is not part of the accepted Gate 0 fixture scope. The 64-bit operation width is an RPTP test-defined model, not a complete R5900 hardware claim. |
| `ANDI` | I-type opcode `0x0C` | Zero-extend the 16-bit immediate; AND the low 32 bits of `rs`; zero-extend the 32-bit result to 64 bits. A write to `$zero` is discarded. | Separate synthetic logical-immediate program, oracle checks and native IR-lowering differential in `tests/test_instruction_logical.py`. | Added after the Gate 0 disposition; it is not part of the accepted Gate 0 fixture scope. The zero-extended 32-bit model is synthetic. |
| `ORI` | I-type opcode `0x0D` | Zero-extend the 16-bit immediate; OR the low 32 bits of `rs`; zero-extend the 32-bit result to 64 bits. A write to `$zero` is discarded. | Separate synthetic ORI program and native differential in `tests/test_instruction_ori.py`; also exercised by the IR-lowering fixture and the logical-immediate fixture. | Added after the Gate 0 disposition; it is not part of the accepted Gate 0 fixture scope. The mixed sign/zero-extension model is synthetic. |
| `XORI` | I-type opcode `0x0E` | Zero-extend the 16-bit immediate; XOR the low 32 bits of `rs`; zero-extend the 32-bit result to 64 bits. A write to `$zero` is discarded. | Separate synthetic logical-immediate program, oracle checks and native IR-lowering differential in `tests/test_instruction_logical.py`. | Added after the Gate 0 disposition; it is not part of the accepted Gate 0 fixture scope. The zero-extended 32-bit model is synthetic. |
| `LUI` | I-type opcode `0x0F`, with `rs=0` | Shift the raw 16-bit immediate left 16 bits, concatenate 16 zero bits, and sign-extend the 32-bit result to 64 bits. A write to `$zero` is discarded; nonzero `rs` is rejected. | Separate synthetic LUI program, oracle checks, IR metadata checks, malformed IR rejection and native IR-lowering differential in `tests/test_instruction_lui.py`. | Added after the Gate 0 disposition; it is not part of the accepted Gate 0 fixture scope. The shifted/sign-extended model is synthetic and limited to the listed reference. |
| `LW` | I-type opcode `0x23` | Sign-extend the 16-bit offset; form a 32-bit effective address; require initialized guest memory; sign-extend the loaded word to 64 bits. | Gate 0 fixture and native differential. | No MMIO, TLB, cache, alignment exception or timing behavior. |
| `SW` | I-type opcode `0x2B` | Sign-extend the 16-bit offset; form a 32-bit effective address; store the low 32 bits of `rt`. | Gate 0 fixture and native differential. | No MMIO, TLB, cache, alignment exception or timing behavior. |
| `BEQ` | I-type opcode `0x04` | Compare the 64-bit register values; target is `pc + 4 + (sign_extend(imm) << 2)` masked to 32 bits. The delay slot executes. | Gate 0 fixture and native differential. | The static target must be inside the spike's code model. Full R5900 branch behavior is not claimed. |
| `BNE` | I-type opcode `0x05` | Compare the 64-bit register values; target is `pc + 4 + (sign_extend(imm) << 2)` masked to 32 bits. The delay slot executes. | Gate 0 fixture and native differential. | The static target must be inside the spike's code model. Full R5900 branch behavior is not claimed. |
| `J` | J-type opcode `0x02` | Combine the high four bits of `pc + 4` with the word's low 26-bit target field shifted left by two. The delay slot executes. | Gate 0 fixture and native differential. | The static target must be inside the spike's code model. |
| `JAL` | J-type opcode `0x03` | Write `pc + 8` to `ra`; jump to the J-type target; the delay slot executes. | Gate 0 fixture and native differential. | No full R5900 call convention or pipeline behavior is claimed. |
| `JR` | SPECIAL funct `0x08`, `rt=rd=shamt=0` | Set the next control target to the low 32 bits of `rs`; the delay slot executes. A target outside the code model halts the synthetic program. | Gate 0 fixture and native differential. | No return-address stack, speculation or exception behavior. |
| `NOP` | SPECIAL word `0x00000000` | No architectural effect. | Gate 0 fixture and native differential. | Only the encoded all-zero NOP is recognized. |

## Minimal IR, CFG and lowering coverage

[IR_CFG.md](IR_CFG.md) defines the additional contract for the same subset. It records raw words, normalized operands, explicit signed/zero-extended immediates, `$zero` destination handling, control-flow classes, direct targets, delay-slot ownership, deterministic basic blocks, and candidate-only function entries. `tools/rptp_lower.py` consumes the validated IR and emits deterministic C++20 for the same synthetic model, with native differential coverage in `tests/test_ir_lowering.py`, `tests/test_instruction_logical.py`, `tests/test_instruction_lui.py` and `tests/test_instruction_register_logic.py`.

The lowering tests cover the supported operations, both branch outcomes, direct and indirect control flow, delay slots, `$zero` writes, 32-bit wraparound, zero-extended logical immediates, the shifted/sign-extended LUI immediate, full modeled 64-bit register logical operations and memory load/store. A separate one-instruction fixture covers uninitialized-memory failure. These tests do not add product runtime behavior, reachability, function extents or a complete R5900 model. Gate 3 remains in progress.

## Explicitly unsupported

- All other opcodes, SPECIAL functions, immediate forms and register-field combinations are rejected with an explicit `Unsupported ...` diagnostic.
- The synthetic model does not implement FPU/COP1, MMI, COP0, exceptions, interrupts, TLB, caches, EE kernel services, IOP, DMA, VU, GS, SPU2, CDVD, controllers, memory cards, timers or hardware timing.
- The spike expects ELF32 little-endian `EM_MIPS`, one executable `PT_LOAD` segment and static control-flow targets inside that code model. It does not load retail PS2 executables.

## Verification commands

Through a Visual Studio developer environment for the MSVC path:

```powershell
python -m unittest tests.test_instruction_logical -v
python -m unittest tests.test_instruction_lui -v
python -m unittest tests.test_instruction_register_logic -v
python -m unittest tests.test_instruction_ori -v
python -m unittest tests.test_ir_cfg -v
python -m unittest tests.test_ir_lowering -v
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-msvc.ps1
```

The separate logical-immediate, LUI, register-logical and ORI tests use runtime-generated synthetic ELFs and do not modify the registered Gate 0 fixture. The IR/CFG test also builds a synthetic ELF at test time and checks the unchanged Gate 0 and ORI hashes. The lowering tests build separate synthetic ELFs and leave the registered fixture untouched. None of these additions modifies the registered Gate 0 fixture. The IR-lowering path is the only path that compiles generated C++ from the IR; the original spike remains a separate differential path.
