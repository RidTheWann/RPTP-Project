# Disc assets research plan — read-only inventory and deferred materialization

- **Status:** research/design note for Gate 2-adjacent, read-only work. This note changes no code, test, inspector contract, ADR or game record.
- **Date:** 2026-10-30
- **Scope:** what the current inspector can and cannot say about disc layout and files; how asset/container families could be identified without extracting content; what a future extraction ADR must decide.
- **Not:** a Gate 2 disposition, an extraction authorization, a compatibility claim, an asset-decoding result or a legal opinion.
- **Inputs read:** `AGENTS.md`; `docs/ISO_INSPECTOR.md`; `docs/ISO_INSPECTOR_REVIEW.md`; `docs/GATE2_EVIDENCE.md`; `docs/DECISIONS/ADR-0004-gate2-read-only-scope.md`; `docs/RISKS.md` (R-016, R-018, R-019, R-020, R-029); `docs/COMPATIBILITY.md`; `docs/games/README.md` and the eight per-game `STATUS.md` records; `tools/rptp_inspect.py` as source.
- **No disc access:** no image was opened, sampled, hashed or extracted for this note. All retail values below are copied from the existing game records and are **Belum diverifikasi** in this session.
- **Evidence labels:** **Terverifikasi** means observed in this session by reading the current source/contract or running a command; **Belum diverifikasi** means recorded or specified but not executed or checked here; **Dugaan** means inference or candidate. This note did not execute the inspector against any image.

## 0. Position

Gate 2 is open and **not passed**. ADR-0004 makes it a read-only milestone and defers extraction, an output directory and any write path to a separate ADR and threat model. The reviewed inspector envelope is the primary ISO 9660 namespace with 2048-byte logical blocks and a single volume. Alternate namespaces, multi-extent/interleaved layouts and raw-sector images are rejected or counted, never interpreted.

This plan therefore separates five things that are easy to conflate:

1. more **metadata** from records the inspector already reads;
2. **bounded read-only sampling** of file headers, with an evidence-backed signature registry;
3. **retail variant support** (Joliet, Rock Ridge, multi-extent, interleaved, raw sectors, layers, audio tracks, partitions);
4. **extraction/materialization**, which needs a write path and a separate ADR;
5. **format decoding**, which materializes content and needs its own authorization, references and tests.

Stages 1 and 2 can be planned without violating Gate 2. Stages 3–5 cannot be treated as approved by this note.

## 1. Current capability matrix

### 1.1 What the inspector validates or reports

The following behavior is **Terverifikasi** by reading the current source and the contract in `docs/ISO_INSPECTOR.md`; the inspector was not executed against an image for this note.

| Area | Current behavior | Consequence |
|---|---|---|
| Image form | File size must be a multiple of 2048 bytes and at least 18 blocks; a 17-block image fails `IMAGE_TOO_SMALL` before descriptor scanning. | Raw 2352-byte, 2336-byte or mixed-mode images have no accepted path. |
| Descriptor scan | Scans from logical block 16, bounded at 256 descriptors; requires `CD001`, recognized type/version and a terminator; accepts identical repeated PVD copies and rejects conflicting ones; reports the actual PVD block. | A displaced PVD and a malformed descriptor set are reported explicitly. |
| Descriptor types | Type 0 boot record, type 2 supplementary/enhanced volume descriptor and type 3 partition descriptor are recorded as headers with warnings, never followed; type 1 is interpreted; type 255 terminates; reserved types and unsupported versions are errors. | Auxiliary namespaces and partitions are invisible to inspection even when their headers are present. |
| PVD fields | File-structure version 1, 2048-byte logical block, single-volume set, volume sequence 1, dual-endian volume space and root record; root must be a non-empty, single-extent directory. | Multi-volume, non-2048 and non-v1 primary descriptors are rejected. |
| Volume boundary | The image must be at least as large as the PVD-declared volume; directory and file extents must lie inside that volume; a larger image file is accepted and data beyond the declared volume is not inspected (ECMA-119 §9.4.9). | A PVD-smaller-than-file image can be inspected, but the extra bytes are unclassified. |
| Directory tree | Reads the root and reachable subdirectories; positive data length (not necessarily a 2048-byte multiple, per ECMA-119 §7.4.5); even record lengths; `.` and `..` as the first two records; records cannot cross a logical block; nonzero sector tails are rejected; record and byte budgets apply. | The primary hierarchy is checked structurally, not reconstructed into files. |
| Directory records | Primary identifiers must be printable ASCII; padding and reserved flags are checked; volume sequence must be 1; associated-file and record-format flags are rejected; the extended-attribute-record length is applied as an extent offset, but its contents are not parsed. | XA/system-use bytes are opaque; no alternate-name or link resolution. |
| `SYSTEM.CNF` and BOOT | Root-level `SYSTEM.CNF` must be a regular, single-extent file within 1 MiB; ASCII with terminal NUL padding only; duplicate keys and embedded NUL/non-ASCII are rejected; `BOOT2` takes precedence over a distinct `BOOT`; path components are validated; missing/ambiguous/unsafe targets fail. | The boot configuration contract is narrow and fail-closed. |
| Boot ELF | ELF32, little-endian, version 1, exact 52-byte header and 32-byte program-header entries; `PT_LOAD` file bounds, `p_filesz <= p_memsz`, power-of-two alignment and congruence, nondecreasing virtual addresses, ELF32 address-space bounds; reports file-backed/zero-fill ranges, entry mappings and overlap warnings. | ELF metadata is reported; loading precedence, relocations, physical addresses and PS2 conventions are not evaluated. |
| Hashes and reads | SHA-256 for `SYSTEM.CNF` and the boot executable; bounded streaming reads with a 4 MiB default materialization cap and a separate 1 MiB `SYSTEM.CNF` cap. | Large boot files can be hashed and parsed without whole-file materialization. |
| Write behavior | No extraction, output-directory option, write API or source mutation path. | Gate 2 is read-only by construction, not only by policy. |

### 1.2 Explicitly rejected or unsupported variants

"Rejected" means a stable error; "inventoried" means a header is counted with a warning but never interpreted; "opaque" means bytes are present but ignored; "no path" means no implementation exists.

| Variant | Current policy | Observed status or error | What real support would require |
|---|---|---|---|
| Joliet (supplementary volume descriptor, type 2/version 1) | Inventoried, not followed; primary names only. | Warning; if no PVD exists, `PRIMARY_VOLUME_DESCRIPTOR_MISSING`. | Escape-sequence parsing, a second directory tree, alternate-name policy, collision/traversal tests. |
| Rock Ridge / SUSP alternate names | System Use bytes are opaque; no `NM`, `CL`, `PL`, `RE` or continuation-area handling. | No warning; primary names are used. | A SUSP/Rock Ridge parser, continuation-area rules, link policy and traversal safety, with public references. |
| Multi-extent files or directories | Rejected in every directory inspection reads; survey counts records but does not assemble chains or traverse multi-extent directories. | `MULTI_EXTENT_UNSUPPORTED`; survey counters. | Chain ordering/overlap validation, file reconstruction, and materialization policy. |
| Interleaved files or directories | Rejected when either file-unit or interleave-gap byte is nonzero; survey counts records without de-interleaving. | `INTERLEAVED_UNSUPPORTED`; survey counters. | An ECMA-119 interleave model, physical coverage calculation and a de-interleaving reader. |
| Raw 2352-byte sectors | No sector conversion; typical raw images fail alignment or the block-16 signature. | `IMAGE_ALIGNMENT_INVALID` or `VOLUME_DESCRIPTOR_SIGNATURE`; synthetic coverage is partial. | Sector-format detection, conversion, track/session handling and new evidence. |
| Dual-layer media | No layer model or layer-break reading; only the PVD-declared volume is inspected. | Extra image data is outside scope without a layer warning (not an error). | Layer-descriptor/break handling and a policy for the second layer. Not claimed today. |
| Audio tracks / mixed-mode discs | No track or session parser; the accepted form is a 2048-byte data image. | BIN/CUE or 2352-byte containers are not accepted. | A track/session container parser and a data-track selection policy. |
| Partitions | Type 3 partition descriptor is inventoried with a warning and never followed. | Warning; no partition contents. | Partition descriptor semantics and a separate namespace policy. |
| Multi-volume sets | Rejected. | `UNSUPPORTED_VOLUME_SET`; record volume sequence other than 1 gives `UNSUPPORTED_VOLUME_SEQUENCE`. | A volume-set model and cross-volume path resolution. |
| Non-2048 logical blocks | Rejected. | `UNSUPPORTED_LOGICAL_BLOCK_SIZE`. | A block-size abstraction throughout descriptors, records and extents. |
| Associated or record-formatted files | Rejected in inspection; survey counts records without interpreting contents. | `ASSOCIATED_FILE_UNSUPPORTED`, `RECORD_FORMAT_UNSUPPORTED`. | A file-format model and separate content policy. |
| UDF or non-ISO filesystems | No parser; a primary ISO 9660 descriptor is required. | `PRIMARY_VOLUME_DESCRIPTOR_MISSING` or earlier image/descriptor error. | A separate filesystem parser and scope decision. |
| Boot record (type 0) as executable | Header only; boot data is never executed. | Warning; no boot. | Out of scope; this project does not boot through emulation. |

A clean `INSPECTED` result therefore means "the primary namespace passed the reviewed checks". It does **not** mean Joliet/Rock Ridge names were resolved or partition contents were understood, and it does not mean the disc is fully described.

## 2. Retail variation matrix from recorded metadata

Source: the eight `docs/games/<slug>/STATUS.md` records. These values are **Belum diverifikasi** in this session; no disc was reopened. Links point to the records rather than repeating every hash.

### 2.1 Descriptor and volume metadata

| Title | Product code (source) | PVD volume ID | ISO bytes | Sectors | PVD volume blocks | Relation | Publisher / preparer | Volume-set ID |
|---|---|---:|---:|---:|---:|---|---|---|
| [Black](../games/black/STATUS.md) | `SLUS_213.76` (boot name) | empty | 3,919,609,856 | 1,913,872 | 1,913,872 | equal | not recorded | not recorded |
| [Bully](../games/bully/STATUS.md) | `SLUS_212.69` (boot name) | `BULLY` | 4,636,835,840 | 2,264,080 | 2,264,080 | equal | not recorded | not recorded |
| [Downhill Domination](../games/downhill-domination/STATUS.md) | `SCUS_971.77` (serial `SCUS-97177`) | empty | 2,530,869,248 | 1,235,776 | 1,235,776 | equal | not recorded | not recorded |
| [God of War II](../games/god-of-war-ii/STATUS.md) | `SCUS_974.81` (boot name) | `GODOFWAR2` | 8,533,671,936 | 4,166,832 | 2,083,888 | smaller by 2,082,944 sectors | `SCEA INC` / `PHILW` | `GODOFWAR2` |
| [San Andreas — original](../games/grand-theft-auto-san-andreas-usa-v300/STATUS.md) | `SLUS_209.46` (boot name) | `SAN_ANDREAS` | 4,517,036,032 | 2,205,584 | 2,205,584 | equal | `ROCKSTAR GAMES` / `ROCKSTAR NORTH` | `SAN_ANDREAS` |
| [San Andreas — Indonesian mod](../games/grand-theft-auto-san-andreas-indonesian-v6/STATUS.md) | `SLUS_209.46` (boot name) | `GTASA_PS2_ID_KHN` | 3,866,394,624 | 1,887,888 | 1,887,888 | equal | `KH4N` / `ROCKSTAR` | empty |
| [Need for Speed — Most Wanted](../games/need-for-speed-most-wanted/STATUS.md) | `SLUS_212.67` (boot name) | empty | 3,702,456,320 | 1,807,840 | 1,807,840 | equal | not recorded | not recorded |
| [Resident Evil 4](../games/resident-evil-4/STATUS.md) | `SLUS_211.34` (boot name) | empty | 4,435,836,928 | 2,165,936 | 2,165,936 | equal | not recorded | not recorded |

All eight records report a 2048-byte logical block, a successful `INSPECTED`/`INSPECTED_WITH_WARNINGS` result and a successful `SURVEYED` result. Seven PVD volumes equal the file sector count; God of War II is the only recorded image whose PVD volume is smaller than the file.

### 2.2 Boot metadata

| Title | `SYSTEM.CNF` bytes | BOOT2 target | Boot file bytes | Boot SHA-256 recorded | PT_LOAD | Warnings |
|---|---:|---|---:|---|---:|---|
| Black | 57 | `SLUS_213.76;1` | 3,371,868 | no | 1 | none |
| Bully | 57 | `SLUS_212.69;1` | 5,132,120 | yes | 19 | PT_LOAD memory overlap |
| Downhill Domination | 54 | `SCUS_971.77;1` | 1,691,684 | yes | 1 | none |
| God of War II | 57 | `SCUS_974.81;1` | 2,125,688 | yes | 1 | none |
| San Andreas — original | 57 | `SLUS_209.46;1` | 5,684,592 | yes | 10 | PT_LOAD memory overlap |
| San Andreas — Indonesian mod | 57 | `SLUS_209.46;1` | 5,684,592 | yes | 10 | PT_LOAD memory overlap |
| Need for Speed — Most Wanted | 57 | `SLUS_212.67;1` | 4,918,740 | no | 1 | none |
| Resident Evil 4 | 57 | `SLUS_211.34;1` | 3,096,892 | no | 1 | none |

Boot sizes range from 1,691,684 to 5,684,592 bytes. Four images (Bully, both San Andreas samples and Need for Speed) exceed the 4 MiB default materialization cap; their inspections still completed because hashing is streamed and only ELF metadata is read.

### 2.3 Directory survey metadata

| Title | Directories (incl. root) | File records | Max depth | Multi-extent records | Interleaved records | Highest extent end | Largest section |
|---|---:|---:|---:|---:|---:|---:|---:|
| Black | 41 | 585 | 3 | 0 | 0 | 3,898,607,616 | 117,669,888 |
| Bully | 36 | 248 | 2 | 0 | 0 | 4,636,833,792 | 818,270,208 |
| Downhill Domination | 15 | 2,338 | 1 | 0 | 0 | 2,530,839,544 | 109,658,116 |
| God of War II | 1 | 15 | 0 | 0 | 0 | 4,267,769,856 | 4,264,382,464 |
| San Andreas — original | 29 | 299 | 3 | 0 | 0 | 4,496,060,416 | 478,615,552 |
| San Andreas — Indonesian mod | 29 | 299 | 3 | 0 | 0 | 3,866,388,699 | 478,615,552 |
| Need for Speed — Most Wanted | 5 | 21 | 2 | 0 | 0 | 3,681,464,000 | 1,010,616,320 |
| Resident Evil 4 | 2 | 8 | 1 | 0 | 0 | 4,414,846,976 | 1,963,034,624 |

All eight surveys report zero skipped unsupported directories. `file records` counts directory records, not reconstructed files; `largest section` is the largest recorded section length, not a container size.

### 2.4 Sample-level observations

- **Volume relation.** Seven images have a PVD volume equal to the file sector count. God of War II declares 2,083,888 blocks (4,267,802,624 bytes) in an 8,533,671,936-byte file. The 2,082,944 sectors (4,265,869,312 bytes) after the declared volume are outside inspection; all 15 reported files lie inside the volume and the highest extent ends 32,768 bytes before the volume end. The purpose of the extra data and any layer status remain **Dugaan**; R-018 is open.
- **Boot names and sizes.** All boot targets use the `SLUS_nnn.nn` or `SCUS_nnn.nn` pattern. Boot sizes vary by almost 4 MB across the sample, and ELF `PT_LOAD` counts vary from 1 to 19. The four boot files above the 4 MiB cap are a measured reason not to reuse the inspection cap as an extraction cap (R-016).
- **Load-map overlap.** Bully and both San Andreas samples report overlapping `PT_LOAD` memory ranges. This is metadata, not evidence of a malformed disc, and no loading precedence is selected. The other five have no overlap warning.
- **San Andreas pair.** The original and the owner-described Indonesian mod record the same boot executable SHA-256 and the same `SYSTEM.CNF` SHA-256, but different whole-image SHA-256 values and different PVD identifiers (`SAN_ANDREAS` vs `GTASA_PS2_ID_KHN`). The records prove the images are not byte-identical; they do not identify changed files, translation scope or method (R-020).
- **Directory shape.** The sample ranges from a root-only directory with 15 file records (God of War II) to 41 directories (Black); file-record counts range from 8 (Resident Evil 4) to 2,338 (Downhill Domination). This is useful variation for inventory output, but it is not a statistical sample of retail discs.
- **Container-looking names.** God of War II records a largest file named `PART1.PAK;1` at 4,264,382,464 bytes. The name and size are metadata; neither proves a format, compression, encryption or a particular container layout.
- **Absence of unsupported records.** Every survey reports zero multi-extent and zero interleaved records and zero skipped unsupported directories. The sample therefore does not exercise those rejection paths; the synthetic tests do.
- **Descriptor coverage.** Every survey reports no descriptor warnings, so no type 0/2/3 descriptor was recorded in this sample. Joliet, boot-record and partition descriptor handling are not exercised by the records. Rock Ridge cannot be ruled out from the absence of warnings because System Use bytes are opaque; its presence is simply unknown.
- **No asset content observation.** No extraction, file-level content comparison, execution or compatibility test was performed for any record. The separate read-only boot-code census records word counts in the boot executable; those counts are not asset/container evidence and are not used in this plan.

### 2.5 What cannot be concluded from this metadata

- **File types and formats — Belum diverifikasi.** Names, suffixes and sizes do not identify a container, texture, audio or compression format. `PART1.PAK` is a name, not a parsed archive.
- **Compression or encryption — Belum diverifikasi.** A large or small section says nothing about whether its bytes are compressed or encrypted.
- **File-level equality — Belum diverifikasi.** File-level hashes exist only for `SYSTEM.CNF` and boot, and only for some records; whole-image hashes prove whole-image equality or inequality, not which files differ.
- **San Andreas modifications — Dugaan at best.** The changed file set, translation coverage and modification method are unaudited.
- **God of War II layer status — Dugaan.** No layer descriptor or layer break was parsed; the extra bytes could be a second layer, padding, another structure or something else.
- **Audio tracks or mixed-mode origin — Belum diverifikasi.** The accepted image form is a 2048-byte data image; the inspector cannot tell whether a source disc also carried audio tracks.
- **Partitions, UDF or other filesystems — Belum diverifikasi.** Only the primary ISO 9660 namespace was read; no partition or alternate filesystem contents were inspected.
- **Provenance of the image — Belum diverifikasi.** Metadata cannot prove that an image is a faithful dump rather than a rebuilt, patched or repackaged image.
- **Completeness of the hierarchy — Belum diverifikasi.** The survey skips unsupported directories, deduplicates aliases and counts records; it does not validate every alias path or the full ISO hierarchy.
- **Boot or compatibility — not tested.** A clean inspection is not a boot, gameplay or compatibility result.
- **Representativeness — no claim.** Eight USA titles, all recorded at 2.53–8.53 GB, do not establish behavior for PAL/Japanese discs, CD-sized images, multi-disc sets, audio-track discs or any unrecorded layout.

## 3. Read-only asset/container identification plan

### 3.1 Design rules

1. **Read-only first.** Directory records come before file payloads. No output directory, no extraction and no source write.
2. **Deterministic output.** Sorted records, no timestamps and no absolute paths. The inspector's `input_name` echoes the supplied path and must be stripped from any committed summary.
3. **Fail closed.** Unknown is a valid, explicit result. A name or a suffix is not a classification.
4. **One layer only.** No recursive archive walking, no decompression and no nested-container discovery in the first stages.
5. **Reference-backed signatures.** A magic value is active only after a permitted public reference and a synthetic positive/negative test are recorded.
6. **No game data in the repository or CI.** Manifests and summaries only; no samples, decoded images/audio or extracted files.

### 3.2 Stage A — deterministic record inventory (recommended first extension)

This is the first safe read-only extension because it reads only directory records that the survey already reads. It does not read regular-file data, does not hash file contents and does not create an output directory.

Proposed behavior:

- Add an `--inventory` mode (or a `--manifest` output for `--survey`) that walks the same validated primary namespace and emits one entry per non-directory record.
- Reuse the existing depth, directory-count, record-count and byte budgets; add manifest-specific entry, name-length and output-size caps.
- Emit to standard output only. Do not add an output-path option; that belongs to the extraction ADR.
- Keep a logical path built from primary identifiers, plus the exact recorded name. Escape characters that are unsafe in a host path; never use a raw ISO name as a host path.
- Keep multi-extent and interleaved records as counted/explicitly unsupported entries; do not assemble chains.

Proposed schema (illustrative, no real game values):

```json
{
  "schema": "rptp.asset-inventory.v1",
  "image": {
    "sha256": null,
    "size_bytes": 0,
    "volume_id": "",
    "volume_space_blocks": 0
  },
  "counts": {
    "directories": 0,
    "files": 0,
    "multi_extent_records": 0,
    "interleaved_records": 0,
    "skipped_unsupported_directories": 0
  },
  "entries": [
    {
      "path": "DIR/FILE.BIN;1",
      "name": "FILE.BIN;1",
      "depth": 1,
      "size_bytes": 0,
      "extent_lba": 0,
      "xa_length": 0,
      "flags": 0,
      "extension": ".bin"
    }
  ]
}
```

`image.sha256` is `null` by default because the whole-image hash would require reading every payload byte; it may be supplied by the caller or copied from the game record. The manifest itself must not contain the inspector's `input_name` value, a timestamp or an absolute path. Entries are sorted by path and then by name.

What this buys: a complete, reviewable list of recorded names, sizes and extents; extension/size histograms; duplicate-size candidates; a basis for selecting which files deserve a bounded header sample. What it does not buy: any type identification, any content hash and any decoding.

### 3.3 Stage B — bounded signature sampling

Only after Stage A and only with owner-approved scope:

- Read a fixed, small prefix from each regular, single-extent file (for example, 64 bytes; the exact cap is an owner decision). Do not read whole files by default.
- Enforce a per-file cap, a total sample budget and a file-count budget. On exhaustion, stop with an explicit error; do not silently skip files.
- Classify only against an explicit signature registry. Record `signature_id`, `sample_length` and `sample_sha256`; do not record the sample bytes.
- Do not decompress, execute, disassemble or recursively walk any container. A recognized archive is a label, not an invitation to parse its members.
- Treat an unmatched prefix as `unknown`. Do not guess from a suffix or an entropy estimate.

A signature registry entry needs:

| Field | Requirement |
|---|---|
| `id` | Stable name, for example `container.zip` or `media.riff_wave`. |
| `family` | Coarse class: executable, archive, texture, audio, image, video, unknown. |
| `magic` and `offset` | Exact bytes and offset, from a permitted public reference. |
| `minimum_header` | Bytes required before the signature is valid. |
| `endianness` | Only where the format defines it. |
| `reference` | `RPTP-REF-*` entry in `docs/REFERENCES.md`. |
| `positive_fixture` | Synthetic sample that must match. |
| `negative_fixture` | Near-miss sample that must not match. |
| `sample_cap` | Maximum bytes the classifier may read. |

Candidate families to investigate, with no signature asserted in this note:

| Candidate | Basis | Status | Allowed next step |
|---|---|---|---|
| ELF32/EM_MIPS | Existing inspector; neutral ELF reference. | **Terverifikasi** for boot metadata (source read). | Reuse the existing parser; no new claim. |
| ISO 9660 | ECMA-119; image-level structure. | **Terverifikasi** for the primary envelope (source read). | No change. |
| ZIP/gzip-style archives | Public container signatures. | **Belum diverifikasi** for this sample. | Add reference, positive/negative fixtures, then sample. |
| RIFF/WAVE, Ogg | Public audio-container documentation. | **Belum diverifikasi** for this sample. | Signature only; no decoding. |
| PNG/JPEG | Public image-format documentation. | **Belum diverifikasi** for this sample. | Signature only; no decoding. |
| `PAK`/`ARC`/`BIN`/`DAT`/`IMG`/`STR` suffixes | Recorded names and common suffix families. | **Dugaan**: suffix is not type evidence. | Inventory and bounded sample; no parsing. |
| Platform texture/audio containers (families commonly referred to as TIM2-like, VAG-like or ADX-like) | Public format documentation must be located and recorded; no signature or layout is asserted here. | **Dugaan**/ **Belum diverifikasi**. | Add a permitted reference and independent tests before naming a format. |
| Unknown | Default when no registry entry matches. | Explicit result. | Stop; do not infer. |

This is the "texture/audio signature" plan: a registry-driven classifier, not a list of remembered magic numbers. The first texture/audio entry should be added only when a public format document is recorded in `docs/REFERENCES.md` and a synthetic test proves the signature, header length and endianness.

### 3.4 Sizes, hashes and duplicate detection

- **Sizes** come from directory records. They are cheap and already available in Stage A.
- **Optional full-file SHA-256** is read-only but reads every byte. If approved, stream it with a total byte cap, record it as `content_sha256`, and label it clearly. If not approved, leave it `null`.
- **Duplicate detection** uses `(size_bytes, content_sha256)` when a full hash exists, otherwise `size_bytes` only as a weak candidate list. A size collision is not a duplicate.
- **Sample hashes** are named `sample_sha256`; they must never be presented as whole-file hashes.
- **Image identity** is the whole-image SHA-256 already recorded for the authorized samples; do not recompute it for this note or present a new hash without running the command.

### 3.5 Provenance-safe recording

Default policy:

- Keep the full per-file manifest local (for example under a local build output), not in the repository.
- Commit only a summary in `docs/games/<slug>/STATUS.md`: schema version, tool revision, image SHA-256, volume ID, counts, aggregate sizes, unknown/signature counts and the manifest's own SHA-256.
- Do not commit sample bytes, hex dumps, decoded images/audio, extracted files, screenshots or format guesses presented as facts.
- Do not commit absolute paths. Strip the inspector's `input_name`; use a basename or a relative logical path.
- Do not put timestamps in the manifest. If an operator log needs local time, keep it local and outside the committed record.
- A per-file metadata manifest (names, sizes, hashes) is metadata under the game-record rules, but it can be large and revealing. Commit it only with explicit owner approval and after a review for personal paths and content.

### 3.6 Why actual decoding and extraction are deferred

- **Gate 2 / ADR-0004.** Extraction, an output directory and any write path are excluded and require a separate ADR and threat model. Decoding in memory is not a filesystem write, but it still materializes copyrighted content and creates a parser attack surface.
- **Authorization.** The project has owner-provided authorization records, not a legal conclusion. Producing decoded assets or extracted files is a different act from reading metadata.
- **Clean-room provenance.** Each format decoder needs permitted public documentation and independent tests. No emulator/recompiler implementation may be consulted (ADR-0003).
- **Security.** Format parsers process untrusted bytes; they need bounds, budgets, fuzzing and a memory-safety review. A read-only header classifier is much smaller than a decoder.
- **Product need.** Gate 3 and Gate 4 are not passed. The native runtime does not yet consume game assets, so building decoders now would be speculative scope.
- **Determinism and auditability.** A decoder needs a versioned output contract and tests before it can produce evidence; otherwise a "decoded" result is not reproducible.

### 3.7 Staging summary

| Stage | Reads file payload? | Writes? | Current status |
|---|---|---|---|
| A. Record inventory | No | No | Recommended first extension; read-only. |
| B. Bounded signature sample | Yes, small prefix | No | Needs owner scope and a reference-backed registry. |
| C. Variant support (Joliet/Rock Ridge/multi-extent/interleaved/raw/layers/audio/partitions) | Depends | No | Separate reviewed increments; not implied by A or B. |
| D. Extraction/materialization | Yes | Yes | Blocked by ADR-0004; needs a separate ADR and threat model. |
| E. Format decoding | Yes | Depends | Separate authorization, references and tests; after D or as an explicitly approved in-memory exception. |

## 4. Separate-ADR outline for future extraction/materialization

This is an outline only. It does not create an ADR, approve a write path or authorize any implementation. The owner assigns the number; ADR-0005 is used here only as a placeholder.

### 4.1 Decision to be made

Whether a local, user-invoked materialization path may exist; what it may write; under which per-title authorization and controls; and which formats, if any, may be decoded. The default remains "no write path".

### 4.2 Threat model

| Threat | Example | Required control | Test evidence |
|---|---|---|---|
| Path traversal | A recorded name contains `..`, `/`, `\` or an encoded separator. | Build output paths from validated components; reject dot segments, separators, absolute paths and NUL/control bytes; verify the canonical path stays under the output root. | Traversal fixtures for every separator and encoding. |
| Absolute/drive/UNC/ADS paths | `<drive>:\...`, `\\server\share`, `name:stream`. | Reject drive letters, UNC prefixes and alternate data streams; host-specific validation. | Windows path-policy tests. |
| Reserved names and trailing dots/spaces | `CON`, `NUL`, `NAME.`, `NAME `. | Reject or deterministically escape; case-insensitive collision detection. | Name-policy tests. |
| Symlink/junction/reparse escape | A pre-created junction inside the output root. | Do not follow links; check each component; reject reparse points; canonical root prefix check. | Junction/symlink tests. |
| Overwrite | Destination file already exists. | Create-new semantics; no replace by default; explicit replace policy if ever allowed. | Collision tests. |
| Case-only collision | `A.TXT` and `a.txt` on a case-insensitive filesystem. | Casefold collision detection; deterministic disambiguation. | Collision tests. |
| Disk exhaustion | A huge file or a very large file count. | Per-file, total and file-count caps; free-space preflight; streaming; abort and clean up. | Cap and low-space tests. |
| Nested container bomb | An archive containing another archive. | Depth 1 only; no recursion; decompression ratio/size caps if decompression is ever added. | Nested-container tests. |
| Parser exploit | Malformed header triggers excessive allocation or memory corruption. | Bounds checks, budgets, fuzzing, memory-safety review; no code execution. | Malformed-input tests. |
| Source mutation/TOCTOU | The image changes during extraction. | Open read-only; hash before/after; abort on mismatch. | Mutation test. |
| Partial output | Crash leaves a half-written tree. | Temp directory plus atomic rename; cleanup on failure; no success manifest. | Failure-injection tests. |
| Content leakage | Extracted assets are committed or uploaded. | Local-only policy; artifact guard; `.gitignore`; no game images or assets in CI. | Repository checks. |
| Log leakage | Absolute paths or personal data in logs. | Relative paths in the manifest; local-only audit log policy. | Log review. |
| Privilege | The tool requires elevation. | Run as the invoking user; no elevation request. | Manual check. |

### 4.3 Ownership and authorization

- A per-title authorization record must name the title, region, serial (if known), image SHA-256, the authorized scope (inspect / inventory / sample / extract), the date and the owner's statement. It is an authorization record, not a legal conclusion.
- No CI, shared runner, upload or redistribution. Extraction remains local to the owner.
- If the authorization scope is unclear, stop. Do not infer permission from a filename or from "it is on my disk".
- Extracted content must not be committed, packaged in a release or used to train/publish derived assets without a separate owner decision.

### 4.4 Output directory policy

- Require an explicit `--output-root`; no default path.
- Canonicalize the root, reject symlinks/reparse points and require it to be outside the repository, outside the source image's directory and outside any protected system location.
- Prefer a dedicated empty directory; create a per-image subdirectory named by a prefix of the image SHA-256.
- Check free space before writing; enforce per-file and total caps.
- Write to a temporary sibling and rename atomically; remove temporary output on failure.
- Do not write a manifest that claims success unless every requested entry completed.
- Do not add an output option to the inspector until this ADR is accepted.

### 4.5 Path traversal and overwrite defenses

- Use only validated primary identifiers; do not trust Rock Ridge/Joliet alternate names until their parser has its own review.
- Reject `/`, `\`, `:`, NUL, control characters, `.` and `..`, absolute paths, drive/UNC prefixes, trailing dots/spaces and reserved device names.
- Enforce component length, path length and depth limits; use a deterministic escape for characters that are legal in ISO 9660 but unsafe on the host.
- Detect case-insensitive collisions before writing.
- Open with create-new/no-follow semantics; never follow a symlink or reparse point.
- Verify the canonical destination path is under the canonical output root immediately before each write.
- Refuse file/directory conflicts and never overwrite an existing path by default.

### 4.6 Cap policy

- Separate caps for per-file bytes, total bytes, file count, depth, path component length, open handles and elapsed work.
- Preflight the destination free space; stream writes; abort with a stable error rather than truncating.
- Keep the 4 MiB inspection cap separate. R-016 records boot files above it; the largest recorded section in the sample is 4,264,382,464 bytes, so an extraction cap must be an explicit owner decision, not a reused inspection default.
- If a requested file exceeds the cap, fail explicitly and name the file; do not write a partial file that looks valid.
- A dry-run planner that validates names, collisions, caps and free space without writing should be the first implementation step.

### 4.7 Audit logging

- Emit a local append-only JSONL audit log under the output root (or another owner-approved local location): sequence number, schema version, tool revision, image SHA-256, options, relative output path, size, content SHA-256, status and error code.
- Emit a deterministic manifest (sorted, no timestamps, no absolute paths) separately from the audit log.
- Log the final summary and exit code; do not log file contents or sample bytes.
- Do not commit the audit log. If a summary is committed, include only the image hash, tool revision, counts, cap outcomes and manifest hash.

### 4.8 Acceptance criteria before code

- Owner accepts the ADR and the threat model; the agent records only `Proposed`.
- Per-title authorization exists.
- Traversal, overwrite, collision, cap, partial-output and source-mutation tests exist and fail first.
- The parser/decoder has permitted references, synthetic fixtures and a provenance review.
- Output policy and audit schema are documented; no game data is in CI.
- A dry-run mode exists and produces no writes.

## 5. Synthetic test plan for inspector extensions

### 5.1 Harness rules

- Build images in memory or temporary directories; no commercial image and no extracted game file in the repository or CI.
- If a binary fixture must be committed, register hash, origin and license in `tests/fixtures/MANIFEST` and keep it synthetic.
- Write the failing test first; do not weaken or delete an existing test.
- Assert stable error codes, deterministic JSON and unchanged input bytes.
- Keep the existing `tests/test_iso_inspector.py` regressions intact; new tests should extend `IsoHardeningTests` or a new focused suite.

### 5.2 Malformed descriptors

| Case | Expected result |
|---|---|
| 17-block image with a PVD at block 16 | `IMAGE_TOO_SMALL` before scanning. |
| 18-block minimal descriptor set | Accepted. |
| PVD at a displaced block within the scan bound and volume | Reported actual PVD LBA; accepted. |
| Missing terminator / terminator outside the scan bound | `VOLUME_DESCRIPTOR_TERMINATOR_MISSING`. |
| Bad `CD001` signature | `VOLUME_DESCRIPTOR_SIGNATURE`. |
| Reserved descriptor type | `UNSUPPORTED_VOLUME_DESCRIPTOR_TYPE`. |
| Type 1 with version 2 | `VOLUME_DESCRIPTOR_VERSION`. |
| Type 2 version 1/2 or type 3 with a valid PVD | Inventoried, warning, PVD still inspected. |
| Type 0 boot record | Inventoried, warning, boot data not executed. |
| Conflicting repeated PVD copies | `PRIMARY_VOLUME_DESCRIPTOR_CONFLICT`. |
| Identical repeated PVD copies | Accepted. |
| Volume space at or below the PVD block (16 or less) | `INVALID_VOLUME_SIZE`. |
| Volume space 17 in an 18-block image | `VOLUME_DESCRIPTOR_OUT_OF_BOUNDS`: the terminator at block 17 lies outside the declared volume. |
| Volume space larger than the image | `IMAGE_TRUNCATED`. |
| Logical block size 512/1024/4096 | `UNSUPPORTED_LOGICAL_BLOCK_SIZE`. |
| Volume set size 2 or sequence 2 | `UNSUPPORTED_VOLUME_SET`. |
| File-structure version 2 | `UNSUPPORTED_FILE_STRUCTURE_VERSION`. |
| Root record length 33 or 35 | `ROOT_RECORD_INVALID`. |
| Root multi-extent flag | `MULTI_EXTENT_UNSUPPORTED`. |
| Root extent outside the declared volume | `EXTENT_OUT_OF_BOUNDS`. |
| Dual-endian field mismatch | `BOTH_ENDIAN_MISMATCH`. |

### 5.3 Variant directories

- Valid PVD plus a Joliet SVD with a deliberately unusable root: inspection succeeds on the primary namespace, emits a descriptor warning, and never follows the SVD root.
- Only an SVD, no PVD: `PRIMARY_VOLUME_DESCRIPTOR_MISSING`.
- Enhanced volume descriptor (type 2/version 2): inventoried with a warning; no enhanced-namespace traversal.
- Partition descriptor (type 3) with a fake partition root: inventoried with a warning; the fake root is never read.
- Boot record (type 0) with fake boot data: inventoried with a warning; no execution.
- Rock Ridge/SUSP System Use bytes containing alternate names and a continuation area: primary names are used, alternate names are not resolved, and continuation areas are not followed.
- Multiple auxiliary descriptors: one warning per recorded descriptor; the primary namespace remains authoritative.
- Terminator before the PVD: `PRIMARY_VOLUME_DESCRIPTOR_MISSING`.
- Unknown descriptor type: `UNSUPPORTED_VOLUME_DESCRIPTOR_TYPE`.

### 5.4 Multi-extent

- Non-final file section in the root, an unrelated file, a directory, `SYSTEM.CNF` and the boot executable each produce `MULTI_EXTENT_UNSUPPORTED` before an ambiguous lookup.
- Survey counts the record, does not assemble the chain and does not traverse a multi-extent directory.
- A final section whose multi-extent flag is clear and whose predecessor is absent is indistinguishable from a regular file; document the observed behavior as a limitation, not as chain validation.
- Assert the input SHA-256 is unchanged after every rejection.

### 5.5 Interleaved

- File-unit nonzero/gap zero, unit zero/gap nonzero and both nonzero each produce `INTERLEAVED_UNSUPPORTED`; test each byte independently.
- A directory record with interleave fields set is rejected in inspection and counted in survey.
- Survey does not de-interleave or compute physical coverage.
- Input bytes are unchanged after rejection.

### 5.6 Raw-sector and container variants

- A 2352-byte image whose size is not a multiple of 2048 fails `IMAGE_ALIGNMENT_INVALID`.
- A 2352-byte image whose size happens to be a multiple of 2048 (for example 128 sectors) still fails at block 16 with no `CD001`; this proves alignment alone is not raw-sector support.
- 2336-byte and 2448-byte images fail alignment or signature.
- A BIN/CUE pair is not accepted as an image; a text CUE path fails an explicit input/image error, not a silent partial parse.
- Do not add a raw-sector success test until a sector-format model and a permitted reference exist.

### 5.7 Budgets and boundaries

- Exact and exact-plus-one cases for directory entries, directory bytes, survey depth, survey directories, survey records, survey bytes, record length (33/34/35/47), identifier length 0/1, descriptor scan bound, boot components (32/33), program headers (4096/4097), `SYSTEM.CNF` (1 MiB) and whole-file reads (4 MiB).
- Nonzero directory padding and nonzero sector tails fail in both inspection and survey.
- Non-block-aligned directory lengths such as 114, 990 and 44,464 bytes are accepted when their records fit; a 47-byte record is rejected.
- Inventory limits: entry count, name length, logical path length and total manifest size; no payload read.
- Sampling limits: per-file sample, total sample budget, file count and an exhausted-budget error; no silent skip.

### 5.8 Determinism and read-only checks

- Run each new mode twice and compare byte-identical JSON.
- Verify input SHA-256, size and mtime before and after.
- Assert the CLI exits 0 for a valid image, 2 for an expected inspection error and produces stable error JSON.
- Assert an inventory run creates no output file and does not read regular-file payloads (use an instrumented stream or a read-count assertion).
- Strip or basename `input_name` in any fixture that is intended to model a committed summary.

## 6. Non-claims and owner decisions

### 6.1 Explicit non-claims

- **No boot claim.** No image was booted, executed or emulated.
- **No compatibility claim.** Inspection and metadata are not compatibility, gameplay or portability evidence.
- **No asset-decoding claim.** No file, texture, audio, archive or container was decoded or identified in this note. Names and suffixes are not signatures.
- **No legal conclusion.** Owner-provided provenance and authorization are not a legal opinion about ownership, fair use, licensing or redistribution.
- **No Gate 2 disposition.** This note is not a Gate 2 pass and does not close the independent-review or owner-disposition prerequisites.
- **No dual-layer, audio-track or partition claim.** The God of War II extra data is unclassified; the sample does not verify layer, track or partition handling.
- **No San Andreas modification finding.** Shared boot/`SYSTEM.CNF` hashes do not identify changed files.
- **No extraction safety claim.** The ADR outline is not an approved design and no write path exists.
- **No statistical claim.** Eight owner-authorized USA samples are not a representative retail census.

### 6.2 Owner decisions needed

1. **Gate 2 disposition.** Commission/record the independent ISO inspector provenance review and record the Gate 2 disposition. Decide whether the read-only inventory may proceed before that disposition or must wait.
2. **Inspector extension scope.** Approve Stage A (record inventory) and, separately, Stage B (bounded signature sampling), including budgets and the exact evidence to be recorded.
3. **Extraction ADR.** Assign the ADR number, approve the threat model, output-directory policy, path/overwrite defenses, caps and audit schema. No extraction code before the ADR is accepted.
4. **Titles and authorization.** Confirm which of the eight titles are authorized for inventory/sampling/extraction, the scope of each authorization, and that no new image is accessed without a new record.
5. **Commit policy.** Decide whether only aggregate summaries or also per-file name/size/hash manifests may be committed, and where.
6. **Cap policy.** Decide extraction caps separately from the 4 MiB inspection cap, using R-016 and the measured boot/file sizes; decide how over-cap files fail.
7. **Format references.** Decide which public format documentation may be used for texture/audio/container signatures and decoders, and require an `RPTP-REF-*` entry and clean-room review before implementation.
8. **Variant priorities.** Decide whether Joliet, Rock Ridge, multi-extent, interleaved, raw 2352, dual-layer, audio-track or partition support is needed, each as a separate reviewed increment with synthetic tests. Do not treat any as approved by this note.
9. **Product asset needs.** After Gate 3/Gate 4 planning, identify which asset families the native runtime actually needs; do not build speculative decoders first.

### 6.3 Recommended sequence

1. Owner records the Gate 2 disposition and any read-only scope extension.
2. Implement and test Stage A record inventory; update per-game summaries with metadata only.
3. If approved, add the reference-backed signature registry and Stage B bounded sampling.
4. Write and accept the extraction ADR and threat model; implement a dry-run planner first.
5. Add single-file materialization, then directory materialization, with traversal/overwrite/cap tests.
6. Add format decoders one family at a time, each with references, fixtures and provenance review.
7. Treat variant support as separate increments; never bundle it into an "asset support" claim.

## References

- ECMA-119, 5th edition (December 2024), as recorded in `docs/REFERENCES.md` (`RPTP-REF-006`); this note uses the clauses already cited by the inspector contract: §6.8.2 (`.`/`..`), §7.4.5 (directory data length), §9.1.13 (record length), §9.4.9 (volume space) and Table 8/§§10.1.8–10.1.9 (file-unit/interleave-gap).
- ELF32 specification, as used by the inspector under `RPTP-REF-003`; no new ELF claim is made.
- `docs/ISO_INSPECTOR.md` and `docs/ISO_INSPECTOR_REVIEW.md` for the current contract and review envelope.
- `docs/GATE2_EVIDENCE.md` and `docs/DECISIONS/ADR-0004-gate2-read-only-scope.md` for the read-only boundary.
- `docs/RISKS.md` R-016, R-018, R-019, R-020 and R-029.
- `docs/COMPATIBILITY.md`, `docs/games/README.md` and the eight `STATUS.md` records for the recorded retail metadata.
- Public format documentation for any future signature or decoder must be added to `docs/REFERENCES.md` before use. No emulator or recompiler implementation was accessed for this note.
