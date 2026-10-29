# Native runtime foundation

- **Status:** native C++20 loader plus a synthetic execution harness; `Provisional independent` in [CLEAN_ROOM_AUDIT.md](CLEAN_ROOM_AUDIT.md). The harness is a differential-test vehicle, not the product execution path. No kernel, syscall, IOP, DMA, VU, GS, SPU2, ISO ingestion, boot or compatibility support exists.
- **Scope:** `runtime/` builds a static library `rptp_runtime` (sparse guest memory, a fail-closed ELF32/EM_MIPS loader and a sequential execution harness) plus the CLIs `rptp-load` and `rptp-run`.
- **Tests:** `runtime/tests/runtime_tests.cpp` (direct C++ loader and harness checks), `tests/test_runtime_loader.py` (independent Python-built images through `rptp-load`), `tests/test_runtime_execution.py` (independent images, ordinary- and likely-branch cases and differential comparison with the Python oracle through `rptp-run`) and `tests/test_cross_path_equivalence.py` (one shared synthetic program through the Python oracle, generated C++ and `rptp-run`); CTest `runtime_loader_tests`, `runtime_loader_cli`, `runtime_execution_cli` and `cross_path_equivalence`.
- **References:** `RPTP-REF-003` (`elf(5)`) for ELF32 header/program-header fields, `PT_LOAD` file-backed and zero-fill ranges, ascending load order, `e_entry` and `PF_X`; `RPTP-REF-001`, `RPTP-REF-002` and `RPTP-REF-005` for the Gate 0 instruction encodings and branch delay slot; `RPTP-REF-015` for the ordinary branch encodings (`BLEZ` p. 83, `BGTZ` p. 81, `BLTZ` p. 85, `BGEZ` p. 76, `BLTZAL` p. 86, `BGEZAL` p. 77) with their always-executed delay slots and unconditional link writes, and for the branch-likely encodings, target formula, take-only delay-slot rule, unconditional link write and `rs = 31` restriction (pages 75, 78, 80, 82, 84, 87, 89 and 91); `RPTP-REF-017` for the official CMake target and `cmake -E env` behavior used by the build wiring.

This document is the contract for the loader and harness. Anything not stated here is unsupported and must fail explicitly rather than being silently ignored.

## What the loader does

`rptp::runtime::load_elf` takes an in-memory image and `LoadLimits`, validates the image, and returns a `LoadOutcome`:

- `LoadOutcome::ok()` is true only when every check passed.
- On success it carries a `LoadReport` (entry point, accepted `PT_LOAD` segments, total file and memory bytes) and a populated `GuestMemory`.
- On failure it carries one `LoadError { code, message }`, an empty report and an empty `GuestMemory`. There is no partial-load success path.

`GuestMemory` holds non-overlapping guest-address regions in a `std::map`. File bytes are copied at mapping time; the remaining `p_memsz - p_filesz` bytes are zero-filled. `read`, `write` and `view` accept only ranges contained in a single region; a cross-region access fails instead of being split or silently truncated. Empty reads and writes succeed without touching memory.

## Accepted image

- ELF magic, `ELFCLASS32`, little-endian, ident version `EV_CURRENT` and `e_version == EV_CURRENT`.
- `e_type == ET_EXEC` and `e_machine == EM_MIPS`; `e_ehsize` is at least 52 and inside the image.
- The program-header table is inside the image, `e_phentsize` is at least 32 and `e_phoff` is at least `e_ehsize`.
- Only `PT_LOAD` program headers are loaded; other segment types are ignored, not interpreted.
- Per `PT_LOAD`: `p_filesz <= p_memsz`; the file range is inside the image; `p_align` is 0, 1 or a power of two; `p_vaddr` is congruent to `p_offset` modulo `p_align`; the memory range ends at or below `2^32`.
- Accepted segments are in non-decreasing `p_vaddr` order and their memory ranges do not overlap. The loader rejects overlap with `LOAD_SEGMENT_OVERLAP`.
- The entry point must lie inside a `PT_LOAD` memory range, inside its file-backed prefix and in a segment with `PF_X`. Otherwise loading fails with `LOAD_ENTRY_UNMAPPED`, `LOAD_ENTRY_NOT_FILE_BACKED` or `LOAD_ENTRY_NOT_EXECUTABLE`.

## Load limits and error taxonomy

Defaults: image at most 16 MiB, guest memory at most 64 MiB, at most 256 program headers and 64 accepted `PT_LOAD` segments. Limits must be positive; a zero limit is an internal configuration error. The byte budgets are RPTP safety limits, not PS2 hardware facts.

Errors use stable `LOAD_*` strings: `LOAD_IMAGE_TOO_SMALL`, `LOAD_IMAGE_TOO_LARGE`, `LOAD_NOT_ELF`, `LOAD_UNSUPPORTED_CLASS`, `LOAD_UNSUPPORTED_ENDIANNESS`, `LOAD_VERSION_INVALID`, `LOAD_TYPE_INVALID`, `LOAD_MACHINE_INVALID`, `LOAD_HEADER_SIZE_INVALID`, `LOAD_PROGRAM_HEADER_LIMIT`, `LOAD_PROGRAM_HEADERS_OUT_OF_BOUNDS`, `LOAD_SEGMENT_LIMIT`, `LOAD_SEGMENT_OUT_OF_BOUNDS`, `LOAD_SEGMENT_SIZE_INVALID`, `LOAD_SEGMENT_ALIGNMENT_INVALID`, `LOAD_SEGMENT_ADDRESS_INVALID`, `LOAD_SEGMENT_ORDER_INVALID`, `LOAD_SEGMENT_OVERLAP`, `LOAD_ENTRY_UNMAPPED`, `LOAD_ENTRY_NOT_FILE_BACKED`, `LOAD_ENTRY_NOT_EXECUTABLE`, `LOAD_GUEST_LIMIT`, `LOAD_MEMORY_CONFLICT` and `LOAD_INTERNAL`.

## Overlap policy

`elf(5)` requires ascending load order but does not define precedence for overlapping ranges, and the read-only inspector reports overlaps as warnings because it does not allocate memory. The native loader must materialize bytes, so it rejects any overlap: there is no silent last-writer or first-writer rule. This is an RPTP loader policy recorded here, not a derived hardware fact.

## What the execution harness does

`rptp::runtime::execute_loaded` runs a loaded report and guest memory sequentially from `e_entry` and returns an `ExecOutcome`. It executes only the documented synthetic subset: `ADDIU`, `ADDU`, `SUBU`, `DADDU`, `SLL`, `SLT`, `SLTU`, `SLTI`, `SLTIU`, `DADDIU`, `AND`, `OR`, `XOR`, `NOR`, `ANDI`, `ORI`, `XORI`, `LUI`, `LW`, `SW`, `LD`, `SD`, `BEQ`, `BNE`, `BLEZ`, `BGTZ`, `BLTZ`, `BGEZ`, `BLTZAL`, `BGEZAL`, `BEQL`, `BNEL`, `BLEZL`, `BGTZL`, `BLTZL`, `BGEZL`, `BLTZALL`, `BGEZALL`, `J`, `JAL`, `JR` and `NOP`, plus at most one branch-delay-slot instruction after each control transfer. `SLL` rejects nonzero `rs`, `LUI` rejects nonzero `rs`, and the register-register forms require `shamt=0`; malformed encodings fail with `EXEC_UNSUPPORTED_INSTRUCTION`.

- All 32 general-purpose registers start at zero; writes to register zero are discarded.
- The 32-bit-arithmetic model matches the oracle: `ADDIU`/`ADDU` add the low 32 bits and sign-extend the 32-bit sum; `SUBU` subtracts the low 32 bits of `rt` from the low 32 bits of `rs` modulo 2^32 and sign-extends the 32-bit difference without an overflow trap; `SLL` shifts the low 32 bits, truncates to 32 bits and sign-extends; `SLTI` sign-extends its immediate and compares full 64-bit signed values; `SLTIU` sign-extends its immediate to 64 bits and compares unsigned; `DADDU` adds two full 64-bit values modulo 2^64; `DADDIU` adds a sign-extended immediate to the full 64-bit value; `ANDI` zero-extends its immediate and clears bits 16..63; `ORI`/`XORI` zero-extend their immediates and preserve the upper bits of `rs`; `LUI` shifts the raw immediate left 16 bits and sign-extends the 32-bit result; `AND`/`OR`/`XOR`/`NOR`/`SLT`/`SLTU` operate on full 64-bit values. `LW` sign-extends the loaded little-endian word to 64 bits. `SW` stores the low 32 bits of `rt`. `LW` and `SW` require a 4-byte-aligned effective address; the alignment rule is described below. `LD` requires an 8-byte-aligned effective address, reads the little-endian low word at that address and the high word at address + 4, and combines them into an unsigned 64-bit value without sign extension; `SD` requires the same alignment and splits `rt` into two little-endian words at the address and address + 4. `BEQ`/`BNE` compare the full 64-bit register values.
- Branch and jump targets use the catalog model: `pc + 4 + (sign_extend(imm) << 2)` masked to 32 bits for branches, and the high four bits of `pc + 4` combined with the shifted 26-bit field for `J`/`JAL`. `JAL` writes `pc + 8` to `r31`; `JR` targets the low 32 bits of `rs`.
- The ordinary branches use the same PC-relative target. `BLEZ`/`BGTZ`/`BLTZ`/`BGEZ` compare the signed low 64 bits of `rs` with zero (`BLEZ` is `rs <= 0`, `BGTZ` is `rs > 0`, `BLTZ` is `rs < 0` and `BGEZ` is `rs >= 0`); `BLTZAL`/`BGEZAL` use `rs < 0` and `rs >= 0` and are procedure calls. `BLTZAL`/`BGEZAL` write `(pc + 8) & 0xFFFFFFFF` to `r31` unconditionally, before the delay slot, including when the branch is not taken; a write to `$zero` is discarded. `rs = 31` for either link form is rejected with `EXEC_UNSUPPORTED_INSTRUCTION` because the approved reference defines the result as UNPREDICTABLE; that rejection is an RPTP policy, not a modelled hardware exception.
- The likely branches use the same PC-relative target. `BEQL`/`BNEL` compare the full 64-bit register values for equality/inequality; `BLEZL`/`BGTZL`/`BLTZL`/`BGEZL`/`BLTZALL`/`BGEZALL` compare the signed low 64 bits of `rs` with zero (`BLEZL` is `rs <= 0`, `BGTZL` is `rs > 0`, `BLTZL`/`BLTZALL` are `rs < 0` and `BGEZL`/`BGEZALL` are `rs >= 0`). `BLTZALL`/`BGEZALL` write `(pc + 8) & 0xFFFFFFFF` to `r31` unconditionally, before the delay slot; a write to `$zero` is discarded. `rs = 31` for either link form is rejected with `EXEC_UNSUPPORTED_INSTRUCTION` because the approved reference defines the result as UNPREDICTABLE; that rejection is an RPTP policy, not a modelled hardware exception.
- A taken likely branch executes its delay slot exactly once. A not-taken likely branch nullifies it: the harness still fetches and validates the next word (mapped, executable, four-byte aligned, fully fetched, supported and not a control transfer) but performs no register, memory or trace effect, does not increment `steps`, and continues at `(pc + 8) & 0xFFFFFFFF`. A missing, non-executable, unaligned, partial, unsupported or control delay-slot word still fails closed. `BEQ`, `BNE`, `BLEZ`, `BGTZ`, `BLTZ`, `BGEZ`, `BLTZAL`, `BGEZAL`, `J`, `JAL` and `JR` always execute their delay slot.
- A control transfer inside a delay slot is unsupported and fails with `EXEC_DELAY_SLOT_CONTROL`; a missing delay slot fails with `EXEC_DELAY_SLOT_MISSING`.
- Instruction fetch requires a PC inside an executable loaded segment, four-byte alignment and four mapped bytes. The guest halts successfully only when the next PC is outside every loaded segment (`halt_reason: "unmapped-pc"`); a mapped but non-executable PC, an unaligned PC and a partial fetch are explicit failures.
- Loads and stores must stay inside one mapped region. Unmapped or cross-region access fails with `EXEC_MEMORY_FAULT`; an unaligned `LW`/`SW` or `LD`/`SD` effective address also fails with `EXEC_MEMORY_FAULT` before any memory byte is read or written, and a doubleword range that leaves its region fails the same way. `SD` checks the full eight-byte range before writing either word. There is no MMIO, TLB, cache, alignment exception or timing model.
- A positive step budget bounds executed instructions; exceeding it fails with `EXEC_STEP_LIMIT`. The default budget is 1,000,000 instructions. A nullified likely delay slot is validated but is not an executed instruction, so it neither appears in `steps` nor consumes the budget.
- Execution is deterministic and single-threaded. The harness tracks successful word stores and reports the final value per address in sorted order; `SD` records its low and high words as two separate entries. The trace, when requested, contains one entry per executed instruction PC and no entry for a nullified likely delay slot. It is not a product interpreter, generated-code runtime, scheduler or boot path.

The registered Gate 0 fixture targets the Python oracle's flat memory map: its store to `0x00002000` lies outside its single RX `PT_LOAD` segment, so `rptp-run` rejects it with `EXEC_MEMORY_FAULT`. The harness differential tests therefore use two-segment images that declare a writable data segment; the fixture remains the Gate 0 oracle differential and is not silently remapped.

## Word and doubleword alignment policy

`LW`, `SW`, `LD` and `SD` require aligned effective addresses. `LW` and `SW` require a 4-byte-aligned 32-bit effective address; `LD` and `SD` require 8-byte alignment. An unaligned access fails closed with `EXEC_MEMORY_FAULT` and a message naming the operation: `unaligned word load`, `unaligned word store`, `unaligned doubleword load` or `unaligned doubleword store`. The check runs before the memory region is read or modified, so an unaligned `SW` or `SD` writes no bytes and an unaligned `LW` or `LD` loads nothing.

This is an RPTP fail-closed model choice, not a claim about R5900 hardware alignment exceptions, exception delivery, handler state or timing. The Python oracle, the generated C++ and this harness enforce the same policy independently; the cross-path suite below checks that they agree.

## Cross-path equivalence matrix

`tests/test_cross_path_equivalence.py` builds one deterministic synthetic ELF at test time and executes the same guest program through the Python oracle, the generated C++ state machine and the `rptp-run` harness. The program covers 32-bit arithmetic with wraparound, `SUBU`/`DADDIU`/`DADDU`, shifts, logical register and immediate forms, `LW`/`SW`, an `LD` of `0x8000000000000000` followed by signed and unsigned 64-bit boundary comparisons, a taken `BEQ` whose delay slot changes the compared register, a not-taken `BNE` whose delay slot still executes, a `J` with a delay slot, and the six ordinary branch forms `BLEZ`, `BGTZ`, `BLTZ`, `BGEZ`, `BLTZAL` and `BGEZAL` with taken/not-taken outcomes, always-executed delay slots and unconditional link writes. It ends with a jump outside every loaded segment.

| Compared state | Python oracle | Generated C++ | `rptp-run` | Normalization before comparison |
|---|---|---|---|---|
| Final GPRs | 128-bit register pairs | 128-bit register pairs | 32 zero-padded 64-bit hex strings | Low 64 bits of each oracle/generated pair; runtime strings parsed as 64-bit. The high pair lane is outside the modeled 64-bit state. |
| Final data bytes | Final memory map | Final memory map | Sorted per-word `memory_writes` | Oracle/generated writes are byte-addressed; each runtime word is expanded to four little-endian bytes. Only the initialized data range at `0x2000..0x2017` is compared. |
| Stop PC | `pc` | `pc` | `final_pc` | Parsed as integers. |
| Halt reason | `reason` = `pc_outside_code` | `reason` = `pc_outside_code` | `halt_reason` = `unmapped-pc` | Explicit documented mapping: the same successful stop outside every loaded segment has a different label in the harness. |
| Halted | `halted` | `halted` | `status == "ok"` | Boolean. |
| Step count and trace | `steps`, `trace` | `steps`, `trace` | `steps`, `trace` | The shared program contains no likely branch, so it has no nullified delay slots, and no unsupported block; the executed-PC traces are directly comparable. |

The generated-native leg requires an MSVC installation discoverable by `tools/rptp/native.py`; the runtime leg requires `RPTP_RUN_BINARY` to point at a built `rptp-run` executable, which CTest supplies as `$<TARGET_FILE:rptp-run>`. When a leg is unavailable the test is skipped with an explicit reason and is never reported as a pass; when a leg is available but disagrees, the test fails. Agreement on this single synthetic program is evidence about these three implementations of the synthetic model, not proof of general cross-path equivalence, hardware behavior or game compatibility.

## Execution error taxonomy

Stable `EXEC_*` strings: `EXEC_ENTRY_UNALIGNED`, `EXEC_PC_UNALIGNED`, `EXEC_UNSUPPORTED_INSTRUCTION`, `EXEC_PC_NOT_EXECUTABLE`, `EXEC_FETCH_FAULT`, `EXEC_MEMORY_FAULT`, `EXEC_DELAY_SLOT_CONTROL`, `EXEC_DELAY_SLOT_MISSING`, `EXEC_STEP_LIMIT` and `EXEC_INTERNAL`. On failure the outcome carries one error and an empty result; there is no partial success.

## CLI contract

    rptp-load [--json] [--max-image-bytes N] [--max-guest-bytes N] IMAGE
    rptp-run [--json] [--trace] [--max-steps N] [--max-image-bytes N] [--max-guest-bytes N] IMAGE

- Exit `0`: image accepted and, for `rptp-run`, execution halted; with `--json`, one deterministic object with `"schema": "rptp.runtime.load.v1"` or `"rptp.runtime.run.v1"` and `"status": "ok"`.
- Exit `2`: load or execution rejected; with `--json`, the same schema with `"status": "error"` and `error.code` / `error.message`. Without `--json`, the error code and message go to stderr and stdout stays empty.
- Exit `1`: usage or file-read failure.
- Load JSON includes `image_bytes`, `entry_point` as a zero-padded 32-bit hex string, `load_segment_count`, `total_file_bytes`, `total_memory_bytes` and a segment array with the original program-header index, address, file offset, sizes, flags and alignment.
- Run JSON includes `image_bytes`, `entry_point`, `steps`, `halt_reason`, `final_pc`, 32 zero-padded 64-bit register strings, sorted `memory_writes` entries and a `trace` array. The trace is empty unless `--trace` is supplied. Output contains no timestamps, host paths or unordered data.

## Build and test

    cmake --preset windows-msvc
    cmake --build --preset windows-msvc
    ctest --test-dir build/cmake-msvc -R runtime_loader --output-on-failure
    ctest --test-dir build/cmake-msvc -R runtime_execution --output-on-failure
    ctest --test-dir build/cmake-msvc -R cross_path --output-on-failure

The Python CLI tests run only when CTest supplies `RPTP_LOAD_BINARY` or `RPTP_RUN_BINARY`; outside CTest they skip instead of guessing a binary path. The same rule supplies the runtime leg of the cross-path suite, while its generated-native leg discovers MSVC independently. The loader and harness have been exercised on synthetic images and the test suite's generated images. The harness has not been run against a retail boot executable, and no guest instruction is recompiled by this layer.

## Non-goals

- No product recompiler, generated-code execution, function discovery or complete R5900 model. The harness implements the narrow synthetic subset above only.
- No EE kernel, syscall, IOP, DMA, VU, GS, SPU2, CDVD, memory-card, controller, interrupt or timing behavior.
- No ISO reading: both CLIs take an ELF image file, not a disc image. ISO inspection remains the separate read-only `tools/rptp_inspect.py`.
- No claim that a loaded or executed synthetic image is a compatible game or that any game boots.
