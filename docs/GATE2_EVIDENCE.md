# Gate 2 evidence dossier

- **Status: NOT PASSED — evidence only.** Only the human owner records a Gate disposition.
- **Base commit:** `6499b05d710837f3cae4b3f7e06fa5ab0cb9e55a`; CI run `39838955979` passed Windows x64/MSVC and Linux/GCC.
- **Historical CI:** runs #44/#45 cover SLTI/SLTIU; the existing log records DADDIU/correction run #50 on Windows x64/MSVC and Linux/GCC. These are historical records, not CI for this inspection increment.
- **Technical review date:** 2026-10-28. The primary-only ISO envelope and ELF32 load-map checks use `RPTP-REF-006`/`003` and named synthetic tests in [ISO_INSPECTOR.md](ISO_INSPECTOR.md); the eight-image sample was revalidated read-only. This increment publishes the hardened inspector; hosted exact-head CI results are recorded in [VERIFICATION_LOG.md](VERIFICATION_LOG.md) when observed.
- **Gate 2 status:** remains **NOT PASSED**. The independent inspector provenance review, hosted exact-head CI of this increment and owner disposition remain open. No extraction, boot or runtime feature is added.
- **Scope:** read-only ISO inspection and synthetic test evidence, per [ADR-0004](DECISIONS/ADR-0004-gate2-read-only-scope.md). No boot, extraction, recompilation or compatibility claim.

## Owner prerequisites

- Gate 0 disposition: **narrow technical pass recorded 2026-10-23 by explicit owner delegation**; it does not close Gate 2. See [GATE0_REVIEW.md](GATE0_REVIEW.md).
- Independent provenance review of the ISO inspector: **not recorded**; the component remains `Provisional independent` in [CLEAN_ROOM_AUDIT.md](CLEAN_ROOM_AUDIT.md).
- Independent review of the build/CI/doctor layer: **not recorded**; that layer remains `Review required`.

## Criterion-to-evidence map

| Gate 2 criterion | Evidence | Current state |
|---|---|---|
| Deterministic inspection on synthetic fixtures | `tests/test_iso_inspector.py`: `test_inspects_synthetic_iso_and_elf`, `test_report_is_deterministic`, `test_error_is_deterministic`; JSON output is sorted by key. | Evidenced for the tested synthetic subset. |
| Robust rejection of malformed input | Explicit error taxonomy in [ISO_INSPECTOR.md](ISO_INSPECTOR.md); 250-case inspection and survey mutation smoke tests assert only `InspectError`; malformed survey records, unsafe extents and boundary limits have named tests; file-based mutation and CLI survey tests assert input bytes are unchanged. | Evidenced for the selected mutation set, not exhaustive fuzzing. |
| No write path to the input or host | `test_file_mutations_preserve_input_bytes`; interleave cases check the input SHA-256 after rejection; the inspector has no write or extraction path. | Evidenced for the read-only scope. |
| Clear unsupported-feature reporting | Named tests reject reserved descriptor types, invalid versions, conflicting PVD copies, multi-extent chains before ambiguous lookup, interleave bytes, associated/record-formatted data and malformed record padding/flags. Auxiliary namespaces are inventoried but never followed, with explicit primary-only warnings. | Evidenced for the reviewed primary-only envelope, not support for rejected layouts. |
| Single-volume ISO 9660 PVD and root `SYSTEM.CNF` | Synthetic success/error tests plus eight read-only retail image records in [VERIFICATION_LOG.md](VERIFICATION_LOG.md) and [games/README.md](games/README.md). | Evidenced for the supported subset; not proof of broad retail-layout support. |
| PVD volume-space boundary | ECMA-119 §9.4.9 (p. 26) defines Volume Space Size as the declared number of logical blocks. `parse_pvd` rejects an image smaller than the declaration; `extent` keeps directory and file reads inside it. Tests cover truncation, out-of-volume extents and a file larger than its PVD volume. | Evidenced for the declared-volume boundary. Data outside the volume is outside Gate 2 scope. |
| BOOT path resolution and ELF metadata | Synthetic path/warning/ELF tests plus duplicate-key, embedded-NUL/non-ASCII and quote rejection; exact explicit-version lookup, coexisting-version hashes and versionless ambiguity; neutral PT_LOAD alignment, address-width and ordering checks; half-open load/zero-fill and entry mappings with overlap/permission warnings; bounded streaming above the materialization cap. | Evidenced by named `ElfLoadMapTests` and existing path/resource tests for the documented subset, not a native ELF loader; unresolved loading-policy risk remains R-027. |
| Directory survey and resource bounds | Raw-record limits include special entries; directory/survey byte budgets include padding. Tests cover exact/+1 limits, nonzero sector tails, invalid primary identifiers, early fan-out rejection, alias/cycle deduplication, input preservation, descriptor warnings and record-level unsupported-layout counts. | Metadata-only; no assembled-file, physical interleave-coverage, full hierarchy or unvisited-directory validation claim. |
| Extraction boundary | No extraction or output-directory feature exists; ADR-0004 records read-only scope and defers extraction. | Not a Gate 2 criterion. Future extraction needs a separate ADR and threat model. |
| Multi-extent and ISO-variant technical review | The format matrix in [ISO_INSPECTOR.md](ISO_INSPECTOR.md) maps descriptor coexistence, primary-only names, opaque extensions, multi-extent chains, raw/non-2048 and multi-volume cases to named synthetic acceptance/rejection tests. | **Technical review complete for the primary-only envelope.** Extension decoding/file assembly remains unsupported, not a claim of broad disc compatibility. |
| Interleave field provenance | ECMA-119 5th edition (December 2024), Table 8 (p. 37) and §§10.1.8–10.1.9 (p. 40); independent field tests. | Evidenced. Interleaved file data remains unsupported. |
| CI on the current evidence | The inspection increment is published for exact-head CI; observed results are appended to [VERIFICATION_LOG.md](VERIFICATION_LOG.md). | **Open:** green Windows x64/MSVC plus Linux/GCC jobs for the exact head are required before merge. |

## Retail sample limits

Eight owner-authorized images have read-only inspection records. Historical passes at `25b4ab8`/`d51f0e7` are retained in the log. All eight were inspected and surveyed twice on 2026-10-28 with the hardened inspector now included in this increment; output was deterministic, whole-image hashes matched prior records and before/after values, and size/mtime remained unchanged. Independent sparse ELF-header reads cross-checked load entries, entry offsets and overlap reports. Bully and both San Andreas samples now carry memory-overlap warnings; the other inspections and all surveys have no warnings. No loading precedence is inferred. That sample is not Gate 2 evidence for broad compatibility:

- All eight reported no interleaved or multi-extent records, so they do not exercise those layouts.
- `God of War II` has a PVD volume space of 2,083,888 blocks (4,267,802,624 bytes) in an 8,533,671,936-byte image; 2,082,944 sectors lie beyond the declared volume and were not inspected. All 15 reported files lie inside the volume, with the highest extent ending 32,768 bytes before the volume end. The purpose of the extra data and second-layer coverage are **Dugaan**, not verified. No parser defect was reproduced.
- Four images (`Need for Speed - Most Wanted`, `Bully`, and both owner-described San Andreas samples) have boot executables above the 4 MiB materialization cap; the cap is unchanged and inspection still completed.
- The two San Andreas images are separate owner-provided samples: an original USA sample and an Indonesian-language mod. They share boot and `SYSTEM.CNF` hashes but have different whole-image hashes and PVD identifiers. Shared boot metadata does not establish file equality or identify which files were modified.
- No image was extracted, booted or recompiled.

## What would close Gate 2

1. Record an independent review of the ISO inspector's provenance; the narrow Gate 0 technical disposition is already recorded but does not substitute for it.
2. Confirm the read-only Gate 2 scope in ADR-0004; extraction is deferred and requires a separate threat model.
3. Review the completed primary-only format matrix and its named synthetic tests; any request for extension decoding, extraction or broader disc support needs additional scope and evidence.
4. Owner publication of the final evidence commit followed by green Windows x64/MSVC and Linux/GCC CI.
5. Owner records the Gate 2 disposition; this dossier must not be treated as that disposition.
