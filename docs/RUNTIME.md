# Native runtime foundation

- **Status:** native C++20 loader plus a synthetic execution harness; `Provisional independent` in [CLEAN_ROOM_AUDIT.md](CLEAN_ROOM_AUDIT.md). The harness is a differential-test vehicle, not the product execution path. No kernel, syscall, IOP, DMA, VU, GS, SPU2, ISO ingestion, boot or compatibility support exists.
- **Scope:** `runtime/` builds a static library `rptp_runtime` (sparse guest memory, a fail-closed ELF32/EM_MIPS loader and a sequential execution harness) plus the CLIs `rptp-load` and `rptp-run`.
- **Tests:** `runtime/tests/runtime_tests.cpp` (direct C++ loader and harness checks), `tests/test_runtime_loader.py` (independent Python-built images through `rptp-load`) and `tests/test_runtime_execution.py` (independent images and differential comparison with the Python oracle through `rptp-run`); CTest `runtime_loader_tests`, `runtime_loader_cli` and `runtime_execution_cli`.
- **References:** `RPTP-REF-003` (`elf(5)`) for ELF32 header/program-header fields, `PT_LOAD` file-backed and zero-fill ranges, ascending load order, `e_entry` and `PF_X`; `RPTP-REF-001`, `RPTP-REF-002` and `RPTP-REF-005` for the Gate 0 instruction encodings and branch delay slot; `RPTP-REF-017` for the official CMake target and `cmake -E env` behavior used by the build wiring.

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

`rptp::runtime::execute_loaded` runs a loaded report and guest memory sequentially from `e_entry` and returns an `ExecOutcome`. It executes only the documented synthetic subset: `ADDIU`, `ADDU`, `DADDU`, `SLL`, `SLT`, `SLTU`, `SLTI`, `SLTIU`, `DADDIU`, `AND`, `OR`, `XOR`, `NOR`, `ANDI`, `ORI`, `XORI`, `LUI`, `LW`, `SW`, `BEQ`, `BNE`, `J`, `JAL`, `JR` and `NOP`, plus one branch-delay-slot instruction after each transfer. `SLL` rejects nonzero `rs`, `LUI` rejects nonzero `rs`, and the register-register forms require `shamt=0`; malformed encodings fail with `EXEC_UNSUPPORTED_INSTRUCTION`.

- All 32 general-purpose registers start at zero; writes to register zero are discarded.
- The 32-bit-arithmetic model matches the oracle: `ADDIU`/`ADDU` add the low 32 bits and sign-extend the 32-bit sum; `SLL` shifts the low 32 bits, truncates to 32 bits and sign-extends; `SLTI` sign-extends its immediate and compares full 64-bit signed values; `SLTIU` sign-extends its immediate to 64 bits and compares unsigned; `DADDU` adds two full 64-bit values modulo 2^64; `DADDIU` adds a sign-extended immediate to the full 64-bit value; `ANDI` zero-extends its immediate and clears bits 16..63; `ORI`/`XORI` zero-extend their immediates and preserve the upper bits of `rs`; `LUI` shifts the raw immediate left 16 bits and sign-extends the 32-bit result; `AND`/`OR`/`XOR`/`NOR`/`SLT`/`SLTU` operate on full 64-bit values. `LW` sign-extends the loaded little-endian word to 64 bits. `SW` stores the low 32 bits of `rt`. `BEQ`/`BNE` compare the full 64-bit register values.
- Branch and jump targets use the catalog model: `pc + 4 + (sign_extend(imm) << 2)` masked to 32 bits for branches, and the high four bits of `pc + 4` combined with the shifted 26-bit field for `J`/`JAL`. `JAL` writes `pc + 8` to `r31`; `JR` targets the low 32 bits of `rs`.
- Every control transfer executes its delay slot. A control transfer inside a delay slot is unsupported and fails with `EXEC_DELAY_SLOT_CONTROL`; a missing delay slot fails with `EXEC_DELAY_SLOT_MISSING`.
- Instruction fetch requires a PC inside an executable loaded segment, four-byte alignment and four mapped bytes. The guest halts successfully only when the next PC is outside every loaded segment (`halt_reason: "unmapped-pc"`); a mapped but non-executable PC, an unaligned PC and a partial fetch are explicit failures.
- Loads and stores must stay inside one mapped region. Unmapped or cross-region access fails with `EXEC_MEMORY_FAULT`; there is no MMIO, TLB, cache, alignment exception or timing model.
- A positive step budget bounds execution; exceeding it fails with `EXEC_STEP_LIMIT`. The default budget is 1,000,000 instructions.
- Execution is deterministic and single-threaded. The harness tracks successful word stores and reports the final value per address in sorted order; it is not a product interpreter, generated-code runtime, scheduler or boot path.

The registered Gate 0 fixture targets the Python oracle's flat memory map: its store to `0x00002000` lies outside its single RX `PT_LOAD` segment, so `rptp-run` rejects it with `EXEC_MEMORY_FAULT`. The harness differential tests therefore use two-segment images that declare a writable data segment; the fixture remains the Gate 0 oracle differential and is not silently remapped.

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

The Python CLI tests run only when CTest supplies `RPTP_LOAD_BINARY` or `RPTP_RUN_BINARY`; outside CTest they skip instead of guessing a binary path. The loader and harness have been exercised on synthetic images and the test suite's generated images. The harness has not been run against a retail boot executable, and no guest instruction is recompiled by this layer.

## Non-goals

- No product recompiler, generated-code execution, function discovery or complete R5900 model. The harness implements the narrow synthetic subset above only.
- No EE kernel, syscall, IOP, DMA, VU, GS, SPU2, CDVD, memory-card, controller, interrupt or timing behavior.
- No ISO reading: both CLIs take an ELF image file, not a disc image. ISO inspection remains the separate read-only `tools/rptp_inspect.py`.
- No claim that a loaded or executed synthetic image is a compatible game or that any game boots.
