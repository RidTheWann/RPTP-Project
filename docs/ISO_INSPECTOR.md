# ISO Inspector

## Purpose

`tools/rptp_inspect.py` is the read-only inspection step in RPTP's ISO-to-native pipeline. It reports ISO metadata and resolves the boot executable referenced by `SYSTEM.CNF`. It does not extract files, write to the image, emulate code, recompile code, or launch a game.

## Usage

From the repository root:

```powershell
python tools/rptp_inspect.py "D:\Games\your-owned-game.iso"
python tools/rptp_inspect.py "D:\Games\your-owned-game.iso" --json
python tools/rptp_inspect.py "D:\Games\your-owned-game.iso" --survey --json
```

Exit code is `0` for an inspected image and `2` for an expected inspection error. In JSON mode, expected failures return a machine-readable object with `status: "ERROR"`, a stable `error_code`, and a human-readable `message`.

## Report contents

- `iso9660`: volume identifier, volume-set size and sequence, system/volume-set/publisher/preparer/application identifiers, volume-space blocks, logical block size, primary-volume-descriptor LBA, and root-directory extent metadata.
- `system_cnf`: path, size, SHA-256, selected `BOOT2` or `BOOT` key, boot value, device, parsed fields, and extent metadata.
- `boot_executable`: resolved path components, device, size, SHA-256, extent metadata, and ELF metadata.
- `boot_executable.elf`: ELF32 class/endianness/type, machine, entry point, program-header-table metadata, PT_LOAD count, and PT_LOAD segment metadata.
- `warnings`: non-fatal observations such as a missing `cdrom0:` device prefix, a non-MIPS machine, a non-ET_EXEC type, no PT_LOAD segment, or an entry point outside all PT_LOAD segments.
- `limitations`: a short reminder of the intentionally narrow scope.

JSON output is sorted by key and the report is deterministic for the same input bytes. Expected failures are deterministic too: the same input produces the same error code and message.

## Directory survey

`--survey` performs a metadata-only directory walk and reports image/sector counts, PVD volume-space relation, directory and file counts, maximum depth, multi-extent and interleaved record counts, the highest file-extent end and the largest file size. It reads directory records, not regular-file data: it does not extract, hash or parse file contents and does not require `SYSTEM.CNF` or an ELF.

- `.` and `..` entries are excluded from counts.
- Directory counts include the root and count unique extents; depth 0 is the root.
- Multi-extent and interleaved records are counted but their directories are not traversed. The main inspection still rejects those layouts. The PVD root record itself must be a supported single-extent, non-interleaved directory; otherwise the survey fails explicitly.
- `highest_file_extent_end_bytes` uses the first reported extent for multi-extent files.
- Survey limits are 64 levels, 100,000 directories and 1,000,000 records.

## Checks performed

- Image size is a multiple of 2048 bytes and large enough for a volume-descriptor set.
- Volume descriptors are scanned within a fixed bound, must carry the `CD001` signature and version 1, and must end with a terminator.
- The primary volume descriptor is present, and its volume-space, logical-block, volume-set and volume-sequence fields are validated in their ISO 9660 dual-endian forms.
- ECMA-119 §9.4.9 (p. 26) defines the volume-space field as the declared number of logical blocks. An image smaller than that declaration is rejected; an image larger than it is accepted, and only the declared volume is inspected. Data beyond that boundary is not treated as ISO 9660 content.
- Only single-volume sets with 2048-byte logical blocks are accepted.
- The root directory record is non-empty, is a directory, lies within the declared volume, and is single-extent.
- Directory records have valid lengths, non-empty identifiers, volume sequence 1, do not cross a logical-block boundary, and stay within fixed entry and directory bounds. Per ECMA-119, zero-based record bytes 26 and 27 are the eight-bit file-unit and interleave-gap fields; either non-zero value is rejected with `INTERLEAVED_UNSUPPORTED`.
- Root `SYSTEM.CNF` must be a regular, single-extent file within the size limit. `BOOT2` takes precedence over legacy `BOOT`.
- BOOT path resolution accepts `\` or `/`, rejects `.` and `..` components, bounds path depth, and rejects missing, ambiguous, intermediate-file and directory targets.
- The boot file must be ELF32, little-endian, version 1, with a valid header and program-header table.
- Every PT_LOAD segment must fit inside the executable, cannot have `p_filesz > p_memsz`, and must use 0, 1 or a power-of-two alignment.
- SHA-256 is calculated for both `SYSTEM.CNF` and the boot executable; both files are streamed in bounded chunks.
- Whole-file materialization is streamed in configurable chunks and capped by `max_read_bytes` (default 4 MiB); `SYSTEM.CNF` keeps its separate 1 MiB cap. The Python entry points accept both `max_read_bytes` and `chunk_size` (default 1 MiB).
- No file content is extracted and no write is performed.

## Error taxonomy

Expected failures use these stable codes.

### Input

- `INPUT_NOT_FOUND`: the requested path does not exist.
- `INPUT_NOT_FILE`: the requested path is not a regular file.
- `INPUT_UNREADABLE`: the file cannot be opened or read.

### Image and volume descriptors

- `IMAGE_TOO_SMALL`: the image cannot contain a volume-descriptor set.
- `IMAGE_ALIGNMENT_INVALID`: the image size is not a multiple of 2048 bytes.
- `IMAGE_BOUNDS`: a requested byte range lies outside the image.
- `IMAGE_TRUNCATED`: the image is shorter than a declared structure or the PVD volume space.
- `VOLUME_DESCRIPTOR_SIGNATURE`: a descriptor lacks the `CD001` signature.
- `VOLUME_DESCRIPTOR_VERSION`: a descriptor has an unsupported version.
- `VOLUME_DESCRIPTOR_TERMINATOR_MISSING`: no terminator was found within the scan bound.
- `PRIMARY_VOLUME_DESCRIPTOR_MISSING`: no primary volume descriptor was found.
- `UNSUPPORTED_LOGICAL_BLOCK_SIZE`: the logical block size is not 2048 bytes.
- `UNSUPPORTED_VOLUME_SET`: the image is a multi-volume set or uses a non-1 volume sequence.
- `INVALID_VOLUME_SIZE`: the declared volume is too small.
- `ROOT_RECORD_INVALID`: the PVD root record is missing or invalid.
- `BOTH_ENDIAN_MISMATCH`: an ISO 9660 dual-endian field disagrees.
- `TRUNCATED_FIELD`: a fixed-width field extends beyond its containing structure.

### Directories and extents

- `DIRECTORY_RECORD_LENGTH_INVALID`: a directory record length is invalid.
- `DIRECTORY_IDENTIFIER_EMPTY`: a directory record has an empty identifier.
- `DIRECTORY_IDENTIFIER_TRUNCATED`: a directory identifier extends beyond its record.
- `DIRECTORY_RECORD_CROSSES_BLOCK`: a directory record crosses a logical-block boundary.
- `DIRECTORY_ENTRY_LIMIT`: a directory exceeds the configured entry limit.
- `EXTENT_OUT_OF_BOUNDS`: an extent lies outside the image or declared volume.
- `UNSUPPORTED_VOLUME_SEQUENCE`: a directory record references another volume sequence.
- `NOT_A_DIRECTORY`: a directory operation was requested on a file.
- `MULTI_EXTENT_UNSUPPORTED`: a multi-extent directory, `SYSTEM.CNF`, or boot executable was encountered.
- `INTERLEAVED_UNSUPPORTED`: a directory record declares a non-zero file-unit or interleave-gap value; interleaved layouts are not supported.
- `SURVEY_DEPTH_LIMIT`: the directory survey exceeded its depth limit.
- `SURVEY_DIRECTORY_LIMIT`: the directory survey exceeded its directory limit.
- `SURVEY_RECORD_LIMIT`: the directory survey exceeded its record limit.

### SYSTEM.CNF and BOOT path

- `SYSTEM_CNF_NOT_FOUND`: no root entry matches `SYSTEM.CNF`.
- `SYSTEM_CNF_AMBIGUOUS`: multiple root entries match `SYSTEM.CNF`.
- `SYSTEM_CNF_IS_DIRECTORY`: `SYSTEM.CNF` is a directory.
- `BOOT_CONFIG_MISSING`: no non-empty `BOOT2` or `BOOT` entry exists.
- `BOOT_PATH_EMPTY`: the BOOT value has no path components.
- `BOOT_PATH_DEPTH_LIMIT`: the BOOT path exceeds the component limit.
- `UNSAFE_BOOT_PATH`: the BOOT path contains `.` or `..`.
- `BOOT_EXECUTABLE_NOT_FOUND`: a BOOT path component was not found.
- `AMBIGUOUS_PATH`: multiple entries match a BOOT path component.
- `BOOT_PATH_NOT_DIRECTORY`: an intermediate BOOT component is not a directory.
- `BOOT_TARGET_IS_DIRECTORY`: the BOOT target is a directory.
- `FILE_SIZE_LIMIT`: a file read exceeds its safety limit (`SYSTEM.CNF` has a 1 MiB cap; whole-file reads default to 4 MiB).

### ELF

- `BOOT_ELF_HEADER_TRUNCATED`: the boot file is smaller than an ELF32 header.
- `BOOT_EXECUTABLE_NOT_ELF`: the boot file lacks ELF magic.
- `UNSUPPORTED_ELF_CLASS`: the file is not ELF32.
- `UNSUPPORTED_ELF_ENDIANNESS`: the file is not little-endian.
- `ELF_VERSION_INVALID`: the ELF version is unsupported.
- `ELF_HEADER_SIZE_INVALID`: the ELF header size is invalid.
- `ELF_PROGRAM_HEADER_LIMIT`: the program-header count exceeds the limit.
- `ELF_PROGRAM_HEADERS_OUT_OF_BOUNDS`: the program-header table is invalid or outside the file.
- `ELF_LOAD_SEGMENT_OUT_OF_BOUNDS`: a PT_LOAD segment extends beyond the executable.
- `ELF_LOAD_SEGMENT_SIZE_INVALID`: a PT_LOAD segment has `p_filesz > p_memsz`.
- `ELF_LOAD_SEGMENT_ALIGNMENT_INVALID`: a PT_LOAD segment has invalid alignment.

## Warnings

Warnings are non-fatal and change the top-level status to `INSPECTED_WITH_WARNINGS`:

- BOOT path has no device prefix, or the device is not `cdrom0`.
- ELF machine is not EM_MIPS (8).
- ELF type is not ET_EXEC (2).
- ELF has no PT_LOAD segment.
- ELF entry point is outside every PT_LOAD segment.

A warning does not mean the image is safe to boot or compatible with RPTP.

## Current limitations

- Only ISO 9660 primary volume descriptors with 2048-byte logical blocks and a single volume are supported.
- Joliet, Rock Ridge, multi-extent files/directories, interleaved files/directories, 2352-byte raw sectors and other disc-image variants are not supported.
- Multi-extent and interleaved entries are rejected explicitly rather than merged or decoded.
- ELF validation is intentionally limited to the header, program-header table and PT_LOAD file bounds; it does not validate every loader convention or PS2-specific memory layout.
- The inspector does not prove that the executable is a valid PS2 game, does not emulate or recompile it, and does not prove compatibility.
- Gate 2 is a read-only milestone under [ADR-0004](DECISIONS/ADR-0004-gate2-read-only-scope.md); extraction, output-directory writes and materialization are not implemented and require a separate future decision and threat model.
- Tests use synthetic images generated in memory and in temporary directories. Do not upload commercial ISO images or extracted copyrighted game files to the repository.
- The current owner-authorized retail sample has been inspected read-only; broader retail layouts and compatibility remain unverified.

## Retail validation

The owner-authorized local sample was surveyed read-only on 2026-10-22 with inspector `d51f0e7`. Five earlier records were inspected at `25b4ab8`; the three new records were also inspected read-only and all eight images were re-surveyed at `d51f0e7`. The runtime folder path is intentionally omitted; per-title metadata and whole-file SHA-256 values are in the [game records](games/README.md).

- All sampled images are 2048-byte aligned, expose a 2048-byte logical block size and completed as `INSPECTED` with no warnings.
- Seven images report PVD volume space equal to the file sector count. `God of War II (USA)` declares 2,083,888 blocks (4,267,802,624 bytes) in an 8,533,671,936-byte image. Its 15 reported files lie inside the declared volume; the highest extent ends 32,768 bytes before the volume end. The remaining 2,082,944 sectors are outside the inspected volume, and their purpose or dual-layer status is **Dugaan**, not verified.
- Directory surveys found no multi-extent or interleaved records and no skipped unsupported directories in the sample. The field positions themselves were checked later against ECMA-119, 5th edition (December 2024), Table 8 and §§10.1.8–10.1.9; targeted synthetic tests reject each field independently. Interleaved layouts remain unsupported.
- Boot executable sizes range from 1,691,684 to 5,684,592 bytes. Four images (`Need for Speed - Most Wanted`, `Bully`, and both owner-described San Andreas samples) have boot executables above the 4 MiB default materialization cap; their read-only inspections still completed and the cap was not changed.
- The two San Andreas images are separate owner-provided samples: an original USA sample and an Indonesian-language mod. They share boot and `SYSTEM.CNF` hashes but have different whole-image hashes and PVD identifiers. Shared boot metadata does not establish file equality or identify which files were modified; the owner-provided mod description is recorded in the game records.
- Surveying is metadata-only. The existing inspection pass still hashes `SYSTEM.CNF` and boot data and reads ELF metadata; no game files were extracted, executed or modified.
- The sample is not evidence of broad retail-layout support, boot support or game compatibility.

## Verification status

- Verified locally on 2026-10-21 with Visual Studio 2026 Build Tools 18.11.1, MSVC 19.51.36260.0, Python 3.13.16, CMake 4.1.0 and Ninja 1.13.2.
- The full Python suite passes; the ISO-inspector tests cover valid metadata, malformed inputs, multi-volume/multi-extent/interleaved rejection (including each interleave byte independently), ELF PT_LOAD validation, deterministic in-memory and file-based mutation checks, survey-specific malformed-record and boundary-limit checks, root multi-extent rejection, and CLI JSON success/error paths, alongside the existing Gate 0/doctor/license/game-record checks. Results are recorded in [docs/VERIFICATION_LOG.md](VERIFICATION_LOG.md).
- The Windows MSVC CMake preset passes its CTest targets; results are recorded in the verification log.
- The current owner-authorized retail sample is `INSPECTED` with no warnings; the records are indexed at `docs/games/README.md`. The directory survey and test-first evidence are recorded in [docs/VERIFICATION_LOG.md](VERIFICATION_LOG.md).
- CI runs `39594267744`, `39594147110`, `39594304857`, `39664774001`, `39838955979`, `39852791294`, `39860776782`, `39908025708`, `39920189021`, `39994586188`, `39999387250`, `40003992195`, `40007604212`, `40233124920` (#43), `40470003967` (#44) and `40470558441` (#45) passed Windows x64/MSVC and Linux/GCC. Latest tested instruction tip is `25267b6`; its SLTI/SLTIU additions do not change the ISO inspector. Gate 2 remains open; these runs are not game-boot or broad ISO-compatibility evidence.
- Not verified: retail ISO layouts beyond the current sample, interleaved-layout support, multi-extent support, other ISO 9660 variants, data beyond a PVD-declared volume, game boot and broad PS2 disc compatibility. Interleave field positions are spec-checked, but decoding interleaved file data is not implemented.
