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

- `iso9660`: volume identifier, volume-set size and sequence, system/volume-set/publisher/preparer/application identifiers, volume-space blocks, logical block size, actual primary-volume-descriptor LBA, file-structure version, ordered `volume_descriptors` headers (`lba`, `type`, `version`), and root-directory extent metadata.
- `system_cnf`: path, size, SHA-256, selected `BOOT2` or `BOOT` key, boot value, device, parsed fields, and extent metadata.
- `boot_executable`: resolved path components, device, size, SHA-256, extent metadata, and ELF metadata.
- `boot_executable.elf`: ELF32 class/endianness/type, machine, entry point, program-header-table metadata, PT_LOAD count and segment metadata. Each load segment includes its original `program_header_index`, exclusive `virtual_file_end`/`virtual_memory_end` and `zero_fill_size`.
- `boot_executable.elf.entry_point_mappings`: all memory-containing load headers, in table order, with their original index, `executable`/`file_backed` flags and boot-ELF-relative `file_offset` (null for zero-fill bytes). Empty ranges contain no entry; no mapping is selected when multiple segments contain it. `load_segments_overlap` reports whether any non-empty memory ranges intersect.
- `warnings`: non-fatal observations such as device/machine/type differences, absent loads, overlapping memory, absent or ambiguous entry mappings and entry bytes that are not both file-backed and executable.
- `limitations`: a short reminder of the intentionally narrow scope.

JSON output is sorted by key and the report is deterministic for the same input bytes. Expected failures are deterministic too: the same input produces the same error code and message.

## Directory survey

`--survey` performs a metadata-only directory walk and reports image/sector counts, PVD volume-space relation, directory and file counts, maximum depth, multi-extent and interleaved record counts, the highest file-extent end and the largest file size. It reads directory records, not regular-file data: it does not extract, hash or parse file contents and does not require `SYSTEM.CNF` or an ELF.

- `.` and `..` entries are excluded from report counts but included in raw-record safety limits.
- Directory counts include the root and count unique `(start, size)` extents; depth 0 is the root. Extents are deduplicated and budgeted before queueing, including aliases and cycles. `max_depth` describes the deterministic traversal, not validation of every alias path or the full ISO hierarchy.
- Multi-extent and interleaved records are counted but their directories are not traversed. Main inspection rejects any such record encountered in a directory it reads, including unrelated files; it does not recursively validate unvisited directories. The PVD root itself must be supported.
- `file_count` counts non-directory records, not reconstructed files. `largest_file_size_bytes` is the largest recorded section length; `highest_file_extent_end_bytes` is the maximum recorded start plus section length. Neither validates a multi-extent chain or computes physical interleaved coverage.
- Auxiliary descriptor headers and explicit primary-only warnings are included; status is `SURVEYED_WITH_WARNINGS` when a descriptor is not interpreted, otherwise `SURVEYED`.
- Safety limits are defined in `tools/rptp_inspect.py`: directory bytes include padding; survey budgets count all parsed records and bytes of unique traversed directories. Nonzero sector tails are rejected instead of skipped. No regular-file data is read.

## Checks performed

- Image size is a multiple of 2048 bytes and large enough for a volume-descriptor set.
- Volume descriptors are scanned from sector 16 within the fixed scan bound and, once known, the declared volume boundary. Headers must carry `CD001`, a recognized type/version, and a terminator. The actual PVD LBA is reported; identical PVD copies are allowed and conflicting copies are rejected.
- The primary volume descriptor is present with file-structure version 1 and a 34-byte root record; its volume-space, logical-block, volume-set and volume-sequence fields are validated in their ISO 9660 dual-endian forms.
- ECMA-119 §9.4.9 (p. 26) defines the volume-space field as the declared number of logical blocks. An image smaller than that declaration is rejected; an image larger than it is accepted, and only the declared volume is inspected. Data beyond that boundary is not treated as ISO 9660 content.
- Only single-volume sets with 2048-byte logical blocks are accepted.
- The root directory record is non-empty, is a directory, lies within the declared volume, and is single-extent.
- Directory records have valid lengths, non-empty printable-ASCII primary identifiers, zero identifier/sector padding, valid reserved/directory flags and volume sequence 1, do not cross a logical-block boundary, and stay within raw-record and byte limits. Single-byte identifiers 0/1 require the directory flag. This is not complete ISO identifier-grammar validation. ECMA-119 zero-based bytes 26/27 are the file-unit/interleave-gap fields; either non-zero value is rejected in main inspection.
- Root `SYSTEM.CNF` must be a regular, single-extent file within the size limit. The RPTP configuration contract accepts ASCII with terminal NUL padding only; embedded NUL/non-ASCII bytes and duplicate case-normalized keys are rejected rather than silently repaired. `BOOT2` takes precedence over a distinct legacy `BOOT`.
- BOOT path resolution accepts `\` or `/` and balanced outer quotes, rejects malformed quotes and `.`/`..` components, bounds path depth, and rejects missing, ambiguous, intermediate-file and directory targets. An explicit `;version` matches the full recorded component case-insensitively; an omitted version must identify a unique base name. It never substitutes another version for an explicit request.
- The boot file must be ELF32, little-endian, version 1, with a valid header and program-header table.
- Every PT_LOAD segment must fit inside the executable, cannot have `p_filesz > p_memsz`, and must use 0, 1 or a power-of-two alignment. For alignment above 1, `p_vaddr` and `p_offset` must be congruent modulo `p_align` (`RPTP-REF-003`).
- PT_LOAD headers must appear in nondecreasing `p_vaddr` order, ignoring non-load headers; the table is never silently sorted. Half-open memory ranges must end at or below `2^32`; an exclusive end exactly at that boundary is accepted, including the final address byte. Empty ranges contain no bytes.
- File-backed ranges precede zero-fill bytes as defined by `RPTP-REF-003`; their bounds are reported without reading payloads or allocating segment memory. Overlaps, entry permissions/backing and multiple mappings are reported with warnings, not loading decisions. This remains selected metadata validation, not a native loader.
- SHA-256 is calculated for both `SYSTEM.CNF` and the boot executable; both files are streamed in bounded chunks.
- Whole-file materialization is streamed in configurable chunks and capped by `max_read_bytes` (default 4 MiB); `SYSTEM.CNF` keeps its separate 1 MiB cap. The Python entry points accept both `max_read_bytes` and `chunk_size` (default 1 MiB).
- No file content is extracted and no write is performed.

## Reviewed format envelope

The 2026-10-28 technical review uses ECMA-119 (`RPTP-REF-006`) and independent synthetic tests; it is not the independent provenance review or a Gate disposition.

| Layout or record | Inspection policy and test evidence |
|---|---|
| Type 1/version 1 PVD, single volume, 2048-byte blocks | Parse primary namespace; `test_reports_actual_primary_descriptor_lba_after_boot_record` verifies displaced PVD metadata. |
| Repeated PVD recordings | Identical bytes accepted; conflicts rejected by `test_rejects_conflicting_primary_descriptor_copies`. |
| Type 0 boot record, type 2 supplementary/version 1 or enhanced/version 2, type 3 partition descriptor | Record headers with warnings, never execute boot data or follow auxiliary roots; `test_auxiliary_namespaces_are_reported_but_never_followed` uses deliberately unusable auxiliary roots. This is not namespace/partition validation. |
| Reserved descriptor types or unsupported versions/file-structure versions | Explicit errors; named type/version tests and exact scan/volume-boundary tests. |
| Multi-extent file sections, including SYSTEM.CNF/boot chains and unrelated assets | Reject before ambiguous lookup; `test_multi_extent_chains_are_rejected_before_ambiguous_lookup`. Survey reports records only, without assembling or validating chains. |
| Associated or record-formatted files | Reject as unsupported in inspection; survey does not interpret file contents. Reserved directory flags and invalid padding are rejected in both modes. |
| Opaque directory system-use and extended attributes | Only the recorded primary name and XA offset are used. `test_opaque_system_use_bytes_do_not_replace_primary_names` checks opaque bytes; this is not Rock Ridge recognition or alternate-name/link resolution. |
| Multi-volume, non-2048 logical blocks, raw-sector/non-ISO images | Existing volume/block/alignment/signature errors reject synthetic cases. No raw-sector conversion or secondary-volume selection exists; raw-sector variants are not exhaustively tested. |
| Sector tails and primary identifiers | Both modes reject nonzero tails, non-printable identifiers and special file identifiers; `IsoReviewRegressionTests` also accepts zero padding before a subsequent sector. |
| Explicit and omitted BOOT versions | Missing explicit versions fail; coexisting versions select the requested hash; versionless ambiguity fails. Named explicit/coexisting-version tests cover both paths. |
| Directory fan-out, aliases and cycles | `test_survey_directory_budget_is_enforced_while_scheduling` proves early rejection; `test_survey_deduplicates_aliases_and_cycles` verifies unique traversal counts. |
| ELF PT_LOAD alignment | Positive 0/1/4/4096 cases and an incongruent 4096-byte negative case use the neutral `p_align` definition, not a PS2 loader model. |
| ELF32 load map and entry | `ElfLoadMapTests` rejects virtual overflow/decreasing load order, accepts the exact address-space end and empty/adjacent ranges, reports zero-fill/offset mappings, and warns on overlap or unsuitable entry bytes. Nested/empty overlap and cross-mapping permission cases are tested without choosing loader policy. |
| Large boot executable | Stream metadata/hash without whole-file materialization; `test_large_boot_executable_is_streamed_without_materialization` preserves the existing materialization cap. |

Tests are in `tests/test_iso_inspector.py`; commands and red/green evidence are in [VERIFICATION_LOG.md](VERIFICATION_LOG.md). Rejection of an unsupported layout is not support for that layout, and accepting its primary namespace is not validation of its extensions.

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
- `PRIMARY_VOLUME_DESCRIPTOR_CONFLICT`: repeated PVD copies disagree.
- `VOLUME_DESCRIPTOR_OUT_OF_BOUNDS`: the descriptor set lies outside its declared volume.
- `UNSUPPORTED_VOLUME_DESCRIPTOR_TYPE`: a reserved descriptor type was encountered.
- `UNSUPPORTED_FILE_STRUCTURE_VERSION`: the primary file-structure version is not 1.
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
- `DIRECTORY_IDENTIFIER_INVALID`: a primary identifier contains non-printable bytes, or a special identifier lacks the directory flag.
- `DIRECTORY_RECORD_CROSSES_BLOCK`: a directory record crosses a logical-block boundary.
- `DIRECTORY_ENTRY_LIMIT`: a directory exceeds the raw-record safety limit, including special entries.
- `DIRECTORY_SIZE_LIMIT`: declared directory bytes exceed the safety budget, including padding.
- `DIRECTORY_PADDING_INVALID`: identifier padding or the unused directory-sector tail is not zero.
- `DIRECTORY_FLAGS_INVALID`: reserved bits or invalid directory-associated/record-format flags are set.
- `ASSOCIATED_FILE_UNSUPPORTED`: inspection encountered associated-file data.
- `RECORD_FORMAT_UNSUPPORTED`: inspection encountered record-formatted file data.
- `EXTENT_OUT_OF_BOUNDS`: an extent lies outside the image or declared volume.
- `UNSUPPORTED_VOLUME_SEQUENCE`: a directory record references another volume sequence.
- `NOT_A_DIRECTORY`: a directory operation was requested on a file.
- `MULTI_EXTENT_UNSUPPORTED`: inspection encountered a non-final file section or multi-extent directory in a directory it reads; survey also rejects an unsupported root.
- `INTERLEAVED_UNSUPPORTED`: a directory record declares a non-zero file-unit or interleave-gap value; interleaved layouts are not supported.
- `SURVEY_DEPTH_LIMIT`: the directory survey exceeded its depth limit.
- `SURVEY_DIRECTORY_LIMIT`: the directory survey exceeded its directory limit.
- `SURVEY_RECORD_LIMIT`: the directory survey exceeded its raw-record limit, including special entries.
- `SURVEY_BYTE_LIMIT`: the directory survey exceeded its cumulative unique-directory byte budget.

### SYSTEM.CNF and BOOT path

- `SYSTEM_CNF_NOT_FOUND`: no root entry matches `SYSTEM.CNF`.
- `SYSTEM_CNF_AMBIGUOUS`: multiple root entries match `SYSTEM.CNF`.
- `SYSTEM_CNF_IS_DIRECTORY`: `SYSTEM.CNF` is a directory.
- `BOOT_CONFIG_MISSING`: no non-empty `BOOT2` or `BOOT` entry exists.
- `SYSTEM_CNF_ENCODING_INVALID`: embedded NUL or non-ASCII bytes prevent configuration parsing.
- `SYSTEM_CNF_DUPLICATE_KEY`: a normalized configuration key appears more than once.
- `BOOT_PATH_INVALID`: quotes in the BOOT value are unbalanced or embedded.
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
- `ELF_LOAD_SEGMENT_ADDRESS_INVALID`: a PT_LOAD memory range extends beyond the ELF32 address space.
- `ELF_LOAD_SEGMENT_ORDER_INVALID`: PT_LOAD headers have decreasing virtual addresses.

## Warnings

Warnings are non-fatal and change the top-level status to `INSPECTED_WITH_WARNINGS`:

- An auxiliary descriptor is recorded but not interpreted; only primary-namespace inspection is performed. Survey exposes the same warnings.
- BOOT path has no device prefix, or the device is not `cdrom0`.
- ELF machine is not EM_MIPS (8).
- ELF type is not ET_EXEC (2).
- ELF has no PT_LOAD segment.
- ELF entry point is outside every PT_LOAD segment.
- PT_LOAD memory ranges overlap; loading precedence is not evaluated.
- Entry bytes are not both file-backed and executable within the same mapping.
- Entry maps to multiple PT_LOAD memory segments; no mapping is selected.

A warning does not mean the image is safe to boot or compatible with RPTP, nor does an overlap warning alone establish that the disc is malformed.

## Current limitations

- Only ISO 9660 primary volume descriptors with 2048-byte logical blocks and a single volume are supported.
- Joliet/Rock Ridge alternate namespaces, partition contents, multi-extent file assembly, interleaved data, 2352-byte raw sectors and other disc-image variants are not supported. Auxiliary headers can coexist with an inspected PVD but are explicitly not interpreted.
- Main inspection rejects unsupported multi-extent/interleaved/associated/record-formatted records in visited directories rather than interpreting them as contiguous regular files. Survey counts records and skips unsupported directories; it is not a validator of those file layouts.
- ELF validation covers selected header/table, file/size/alignment/order and ELF32 virtual-range constraints. The load map is metadata only; overlap precedence, physical-address mapping, relocations and PS2 memory conventions remain undefined. Zero-fill sizes must not be summed into a validated memory footprint when ranges overlap.
- The inspector does not prove that the executable is a valid PS2 game, does not emulate or recompile it, and does not prove compatibility.
- Gate 2 is a read-only milestone under [ADR-0004](DECISIONS/ADR-0004-gate2-read-only-scope.md); extraction, output-directory writes and materialization are not implemented and require a separate future decision and threat model.
- Tests use synthetic images generated in memory and in temporary directories. Do not upload commercial ISO images or extracted copyrighted game files to the repository.
- The current owner-authorized retail sample has been inspected read-only; broader retail layouts and compatibility remain unverified.

## Retail validation

Historical 2026-10-22 passes at `25b4ab8`/`d51f0e7` remain in the verification log. On 2026-10-28 all eight authorized images were inspected and surveyed twice with the hardened inspector now included in this increment. CLI output was identical across repeats; whole-image hashes matched both prior records and before/after values, with unchanged size/mtime. Independent sparse reads of ELF/program headers cross-checked all load entries, entry offsets and overlap reports without copying payloads. Per-title evidence is in the [game records](games/README.md); no personal absolute path is recorded.

- All sampled images are 2048-byte aligned and expose a 2048-byte logical block size. Five inspections completed as `INSPECTED`; Bully and both San Andreas samples now report `INSPECTED_WITH_WARNINGS` for overlapping PT_LOAD zero-fill memory ranges. All surveys completed as `SURVEYED` without warnings. Each entry maps uniquely into file-backed PF_X bytes; this is metadata, not loader readiness. The newly visible overlaps do not alone establish malformed discs; precedence and PS2 loading conventions remain undefined.
- Seven images report PVD volume space equal to the file sector count. `God of War II (USA)` declares 2,083,888 blocks (4,267,802,624 bytes) in an 8,533,671,936-byte image. Its 15 reported files lie inside the declared volume; the highest extent ends 32,768 bytes before the volume end. The remaining 2,082,944 sectors are outside the inspected volume, and their purpose or dual-layer status is **Dugaan**, not verified.
- Directory surveys found no multi-extent or interleaved records and no skipped unsupported directories in the sample. The field positions themselves were checked later against ECMA-119, 5th edition (December 2024), Table 8 and §§10.1.8–10.1.9; targeted synthetic tests reject each field independently. Interleaved layouts remain unsupported.
- Boot executable sizes range from 1,691,684 to 5,684,592 bytes. Four images (`Need for Speed - Most Wanted`, `Bully`, and both owner-described San Andreas samples) have boot executables above the 4 MiB default materialization cap; their read-only inspections still completed and the cap was not changed.
- The two San Andreas images are separate owner-provided samples: an original USA sample and an Indonesian-language mod. They share boot and `SYSTEM.CNF` hashes but have different whole-image hashes and PVD identifiers. Shared boot metadata does not establish file equality or identify which files were modified; the owner-provided mod description is recorded in the game records.
- Surveying is metadata-only. The existing inspection pass still hashes `SYSTEM.CNF` and boot data and reads ELF metadata; no game files were extracted, executed or modified.
- The sample is not evidence of broad retail-layout support, boot support or game compatibility.

## Verification status

- Local 2026-10-29 inspection and ELF load-map hardening in this increment passed the focused inspector suite and the full Windows/MSVC suite, doctor, artifact guard, compileall, CMake/CTest and the wrapper. Test-first failures, review regressions and eight-disc read-only revalidation are recorded in [VERIFICATION_LOG.md](VERIFICATION_LOG.md). The primary-only technical envelope is reviewed; the increment is published for exact-head CI and is not independently provenance-reviewed.
- Verified locally on 2026-10-21 with Visual Studio 2026 Build Tools 18.11.1, MSVC 19.51.36260.0, Python 3.13.16, CMake 4.1.0 and Ninja 1.13.2.
- The full Python suite passes; the ISO-inspector tests cover valid metadata, malformed inputs, multi-volume/multi-extent/interleaved rejection (including each interleave byte independently), ELF PT_LOAD validation, deterministic in-memory and file-based mutation checks, survey-specific malformed-record and boundary-limit checks, root multi-extent rejection, and CLI JSON success/error paths, alongside the existing Gate 0/doctor/license/game-record checks. Results are recorded in [docs/VERIFICATION_LOG.md](VERIFICATION_LOG.md).
- The Windows MSVC CMake preset passes its CTest targets; results are recorded in the verification log.
- The current eight-image sample completed repeated inspection/survey with unchanged whole-image hashes. Bully and both San Andreas samples are `INSPECTED_WITH_WARNINGS` for load-memory overlap; the other five are `INSPECTED`, and all surveys are `SURVEYED`. Records: `docs/games/README.md`; evidence: [VERIFICATION_LOG.md](VERIFICATION_LOG.md). No game was executed.
- Historical CI runs `39594267744`, `39594147110`, `39594304857`, `39664774001`, `39838955979`, `39852791294`, `39860776782`, `39908025708`, `39920189021`, `39994586188`, `39999387250`, `40003992195`, `40007604212`, `40233124920` (#43), `40470003967` (#44), `40470558441` (#45) and `40474315598` (#50) passed Windows x64/MSVC and Linux/GCC as recorded in the log. They do not verify this increment; its exact-head runs are recorded in the log when observed. Gate 2 remains open; these runs are not game-boot or broad ISO-compatibility evidence.
- Not verified: retail layouts beyond the revalidated eight-image sample, interleaved/multi-extent decoding, alternate ISO namespaces, complete hierarchy/identifier grammar or native ELF loading, data structure beyond a PVD-declared volume, game boot and broad PS2 disc compatibility. The primary-only technical rejection envelope is reviewed; rejected or opaque formats are not supported.
