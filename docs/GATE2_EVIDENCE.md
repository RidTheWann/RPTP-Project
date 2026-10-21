# Gate 2 evidence dossier

- **Status: NOT PASSED — evidence only.** Only the human owner records a Gate disposition.
- **Base commit:** `d334139d11526e2abc4fad7d4ad09eced3b7da4a`; CI run `39664774001` passed Windows x64/MSVC and Linux/GCC.
- **Local follow-up:** commits after `d334139`; run `git log origin/main..main` for the current list. They are local-only and not CI-verified. See `docs/STATE.md` for status.
- **Scope:** read-only ISO inspection and synthetic test evidence, per [ADR-0004](DECISIONS/ADR-0004-gate2-read-only-scope.md). No boot, extraction, recompilation or compatibility claim.

## Owner prerequisites

- Formal Gate 0 disposition: **pending human review**.
- Independent provenance review of the ISO inspector: **not recorded**; the component remains `Provisional independent` in [CLEAN_ROOM_AUDIT.md](CLEAN_ROOM_AUDIT.md).
- Independent review of the build/CI/doctor layer: **not recorded**; that layer remains `Review required`.

## Criterion-to-evidence map

| Gate 2 criterion | Evidence | Current state |
|---|---|---|
| Deterministic inspection on synthetic fixtures | `tests/test_iso_inspector.py`: `test_inspects_synthetic_iso_and_elf`, `test_report_is_deterministic`, `test_error_is_deterministic`; JSON output is sorted by key. | Evidenced for the tested synthetic subset. |
| Robust rejection of malformed input | Explicit error taxonomy in [ISO_INSPECTOR.md](ISO_INSPECTOR.md); 250-case inspection and survey mutation smoke tests assert only `InspectError`; malformed survey records, unsafe extents and boundary limits have named tests; file-based mutation and CLI survey tests assert input bytes are unchanged. | Evidenced for the selected mutation set, not exhaustive fuzzing. |
| No write path to the input or host | `test_file_mutations_preserve_input_bytes`; interleave cases check the input SHA-256 after rejection; the inspector has no write or extraction path. | Evidenced for the read-only scope. |
| Clear unsupported-feature reporting | Stable codes including `MULTI_EXTENT_UNSUPPORTED` and `INTERLEAVED_UNSUPPORTED`; tests cover each interleave byte independently. | Evidenced for implemented rejection paths. |
| Single-volume ISO 9660 PVD and root `SYSTEM.CNF` | Synthetic success/error tests plus eight read-only retail image records in [VERIFICATION_LOG.md](VERIFICATION_LOG.md) and [games/README.md](games/README.md). | Evidenced for the supported subset; not proof of broad retail-layout support. |
| BOOT path resolution and ELF metadata | Synthetic path, warning, ELF header and PT_LOAD tests; `SYSTEM.CNF` and boot hashes are reported. | Evidenced for the documented subset. |
| Directory survey | `IsoReader.survey` tests cover counts, depth, exact boundary limits, malformed records, multi-extent/interleaved counting and skip behavior, root multi-extent rejection and file-based input preservation; retail surveys recorded. | Evidenced as metadata-only; it does not read file data. |
| Extraction boundary | No extraction or output-directory feature exists; ADR-0004 records read-only scope and defers extraction. | Not a Gate 2 criterion. Future extraction needs a separate ADR and threat model. |
| Multi-extent and ISO-variant support | Multi-extent layouts are rejected, not supported; Joliet, Rock Ridge and raw-sector variants are unsupported. | **Open by design; fail-closed.** |
| Interleave field provenance | ECMA-119 5th edition (December 2024), Table 8 (p. 37) and §§10.1.8–10.1.9 (p. 40); independent field tests. | Evidenced. Interleaved file data remains unsupported. |
| CI on the current evidence | `d334139` is green; later local commits are not CI-verified. | **Open for the new commits.** |

## Retail sample limits

Eight owner-authorized images have read-only inspection records. Five earlier records were produced at `25b4ab8`; all eight were re-surveyed at `d51f0e7`, and the three new images were also inspected read-only at `d51f0e7`. That sample is not Gate 2 evidence for broad compatibility:

- All eight reported no interleaved or multi-extent records, so they do not exercise those layouts.
- `God of War II` has a PVD volume space smaller than the file; second-layer coverage is **Dugaan**.
- Four images (`Need for Speed - Most Wanted`, `Bully`, and both San Andreas variants) have boot executables above the 4 MiB materialization cap; the cap is unchanged and inspection still completed.
- The two San Andreas images share boot and `SYSTEM.CNF` hashes but have different whole-image hashes and PVD identifiers; the filename variant labels do not establish revision identity.
- No image was extracted, booted or recompiled.

## What would close Gate 2

1. Owner records the formal Gate 0 disposition and an independent review of the ISO inspector's provenance.
2. Confirm the read-only Gate 2 scope in ADR-0004; extraction is deferred and requires a separate threat model.
3. Review the documented ISO variants and multi-extent handling, with synthetic tests for every accepted or rejected case.
4. Owner publication of the final evidence commit followed by green Windows x64/MSVC and Linux/GCC CI.
5. Owner records the Gate 2 disposition; this dossier must not be treated as that disposition.
