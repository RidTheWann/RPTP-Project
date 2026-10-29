# Native runtime foundation

- **Status:** first native C++20 layer; `Provisional independent` in [CLEAN_ROOM_AUDIT.md](CLEAN_ROOM_AUDIT.md). No instruction execution, kernel, syscall, IOP, DMA, VU, GS, SPU2, ISO ingestion, boot or compatibility support exists.
- **Scope:** `runtime/` builds a static library `rptp_runtime` (sparse guest memory plus a fail-closed ELF32/EM_MIPS loader) and a CLI `rptp-load` that reports a loaded image as deterministic JSON.
- **Tests:** `runtime/tests/runtime_tests.cpp` (direct C++ checks) and `tests/test_runtime_loader.py` (independent Python-built synthetic images driven through the CLI), registered as CTest tests `runtime_loader_tests` and `runtime_loader_cli`.
- **References:** `RPTP-REF-003` (`elf(5)`) for ELF32 header/program-header fields, `PT_LOAD` file-backed and zero-fill ranges, ascending load order, `e_entry` and `PF_X`; `RPTP-REF-017` for the official CMake target and `cmake -E env` behavior used by the build wiring.

This document is the contract for the loader. Anything not stated here is unsupported and must fail explicitly rather than being silently ignored.

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

## Limits and error taxonomy

Defaults: image at most 16 MiB, guest memory at most 64 MiB, at most 256 program headers and 64 accepted `PT_LOAD` segments. Limits must be positive; a zero limit is an internal configuration error. The byte budgets are RPTP safety limits, not PS2 hardware facts.

Errors use stable `LOAD_*` strings: `LOAD_IMAGE_TOO_SMALL`, `LOAD_IMAGE_TOO_LARGE`, `LOAD_NOT_ELF`, `LOAD_UNSUPPORTED_CLASS`, `LOAD_UNSUPPORTED_ENDIANNESS`, `LOAD_VERSION_INVALID`, `LOAD_TYPE_INVALID`, `LOAD_MACHINE_INVALID`, `LOAD_HEADER_SIZE_INVALID`, `LOAD_PROGRAM_HEADER_LIMIT`, `LOAD_PROGRAM_HEADERS_OUT_OF_BOUNDS`, `LOAD_SEGMENT_LIMIT`, `LOAD_SEGMENT_OUT_OF_BOUNDS`, `LOAD_SEGMENT_SIZE_INVALID`, `LOAD_SEGMENT_ALIGNMENT_INVALID`, `LOAD_SEGMENT_ADDRESS_INVALID`, `LOAD_SEGMENT_ORDER_INVALID`, `LOAD_SEGMENT_OVERLAP`, `LOAD_ENTRY_UNMAPPED`, `LOAD_ENTRY_NOT_FILE_BACKED`, `LOAD_ENTRY_NOT_EXECUTABLE`, `LOAD_GUEST_LIMIT`, `LOAD_MEMORY_CONFLICT` and `LOAD_INTERNAL`.

## Overlap policy

`elf(5)` requires ascending load order but does not define precedence for overlapping ranges, and the read-only inspector reports overlaps as warnings because it does not allocate memory. The native loader must materialize bytes, so it rejects any overlap: there is no silent last-writer or first-writer rule. This is an RPTP loader policy recorded here, not a derived hardware fact.

## CLI contract

    rptp-load [--json] [--max-image-bytes N] [--max-guest-bytes N] IMAGE

- Exit `0`: image accepted; with `--json`, one deterministic object with `"schema": "rptp.runtime.load.v1"` and `"status": "ok"`.
- Exit `2`: load rejected; with `--json`, the same schema with `"status": "error"` and `error.code` / `error.message`. Without `--json`, the error code and message go to stderr and stdout stays empty.
- Exit `1`: usage or file-read failure.
- Success JSON includes `image_bytes`, `entry_point` as a zero-padded 32-bit hex string, `load_segment_count`, `total_file_bytes`, `total_memory_bytes` and a segment array with the original program-header index, address, file offset, sizes, flags and alignment. Output contains no timestamps, host paths or unordered data.

## Build and test

    cmake --preset windows-msvc
    cmake --build --preset windows-msvc
    ctest --test-dir build/cmake-msvc -R runtime_loader --output-on-failure

The Python CLI tests run only when CTest supplies `RPTP_LOAD_BINARY`; outside CTest they skip instead of guessing a binary path. The loader has been exercised on synthetic images, the Gate 0 synthetic fixture and the test suite's generated images. It has not been run against a retail boot executable, and no instruction is executed or recompiled by this layer.

## Non-goals

- No R5900 instruction semantics, interpreter, dispatch loop or recompilation.
- No EE kernel, syscall, IOP, DMA, VU, GS, SPU2, CDVD, memory-card, controller or timing behavior.
- No ISO reading: the CLI takes an ELF image file, not a disc image. ISO inspection remains the separate read-only `tools/rptp_inspect.py`.
- No claim that a loaded image is a compatible game or that any game boots.
