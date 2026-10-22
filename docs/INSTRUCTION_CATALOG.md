# RPTP synthetic instruction catalog

- **Status date:** 2026-10-23
- **Scope:** narrow synthetic ELF32/EM_MIPS differential spike, not a complete R5900 implementation and not a compatibility list.
- **Provenance:** [ADR-0003](DECISIONS/ADR-0003-sealed-source-clean-room-policy.md), [PROVENANCE_PLAN.md](PROVENANCE_PLAN.md) and [REFERENCES.md](REFERENCES.md).
- **Gate status:** Gate 3 is not passed. This catalog records what the current synthetic tests actually exercise.

## Verification levels

- **Native differential:** the decoder, oracle and emitted C++ are exercised by a synthetic program; the generated native state equals the oracle state under a supported host compiler. The Windows/MSVC run is recorded in [VERIFICATION_LOG.md](VERIFICATION_LOG.md).
- **Decode only:** the decoder recognizes the encoding but no native differential exists. No instruction currently has this status.
- **Unsupported:** the decoder rejects the encoding explicitly. Unsupported instructions are never silently skipped or lowered to an approximation.

## Supported synthetic subset

| Instruction | Encoding | Current model | Evidence | Limits |
|---|---|---|---|---|
| `ADDIU` | I-type opcode `0x09` | Sign-extend the 16-bit immediate; add the low 32 bits of `rs`; sign-extend the 32-bit result to the spike's 64-bit register array. | Gate 0 fixture and native differential; [GATE0_REVIEW.md](GATE0_REVIEW.md). | This is the spike's 32-bit model, not complete 64-bit R5900 arithmetic. |
| `ADDU` | SPECIAL funct `0x21`, `shamt=0` | Add the low 32 bits of `rs` and `rt`; sign-extend the 32-bit result to 64 bits. | Gate 0 fixture and native differential. | No overflow trap and no 64-bit R5900 claim. |
| `ORI` | I-type opcode `0x0D` | Zero-extend the 16-bit immediate; OR the low 32 bits of `rs`; zero-extend the 32-bit result to 64 bits. A write to `$zero` is discarded. | Separate synthetic ORI program and native differential in `tests/test_instruction_ori.py`. | Added after the Gate 0 disposition; it is not part of the accepted Gate 0 fixture scope. The mixed sign/zero-extension model is synthetic. |
| `LW` | I-type opcode `0x23` | Sign-extend the 16-bit offset; form a 32-bit effective address; require initialized guest memory; sign-extend the loaded word to 64 bits. | Gate 0 fixture and native differential. | No MMIO, TLB, cache, alignment exception or timing behavior. |
| `SW` | I-type opcode `0x2B` | Sign-extend the 16-bit offset; form a 32-bit effective address; store the low 32 bits of `rt`. | Gate 0 fixture and native differential. | No MMIO, TLB, cache, alignment exception or timing behavior. |
| `BEQ` | I-type opcode `0x04` | Compare the 64-bit register values; target is `pc + 4 + (sign_extend(imm) << 2)` masked to 32 bits. The delay slot executes. | Gate 0 fixture and native differential. | The static target must be inside the spike's code model. Full R5900 branch behavior is not claimed. |
| `BNE` | I-type opcode `0x05` | Compare the 64-bit register values; target is `pc + 4 + (sign_extend(imm) << 2)` masked to 32 bits. The delay slot executes. | Gate 0 fixture and native differential. | The static target must be inside the spike's code model. Full R5900 branch behavior is not claimed. |
| `J` | J-type opcode `0x02` | Combine the high four bits of `pc + 4` with the word's low 26-bit target field shifted left by two. The delay slot executes. | Gate 0 fixture and native differential. | The static target must be inside the spike's code model. |
| `JAL` | J-type opcode `0x03` | Write `pc + 8` to `ra`; jump to the J-type target; the delay slot executes. | Gate 0 fixture and native differential. | No full R5900 call convention or pipeline behavior is claimed. |
| `JR` | SPECIAL funct `0x08`, `rt=rd=shamt=0` | Set the next control target to the low 32 bits of `rs`; the delay slot executes. A target outside the code model halts the synthetic program. | Gate 0 fixture and native differential. | No return-address stack, speculation or exception behavior. |
| `NOP` | SPECIAL word `0x00000000` | No architectural effect. | Gate 0 fixture and native differential. | Only the encoded all-zero NOP is recognized. |

## Explicitly unsupported

- All other opcodes, SPECIAL functions, immediate forms and register-field combinations are rejected with an explicit `Unsupported ...` diagnostic.
- The synthetic model does not implement FPU/COP1, MMI, COP0, exceptions, interrupts, TLB, caches, EE kernel services, IOP, DMA, VU, GS, SPU2, CDVD, controllers, memory cards, timers or hardware timing.
- The spike expects ELF32 little-endian `EM_MIPS`, one executable `PT_LOAD` segment and static control-flow targets inside that code model. It does not load retail PS2 executables.

## Verification commands

Through a Visual Studio developer environment for the MSVC path:

```powershell
python -m unittest tests.test_instruction_ori -v
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-msvc.ps1
```

The separate ORI test uses a runtime-generated synthetic ELF and does not modify the registered Gate 0 fixture. The Gate 0 fixture and its SHA-256 remain unchanged by this addition.
