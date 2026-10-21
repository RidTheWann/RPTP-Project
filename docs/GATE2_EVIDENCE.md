# Gate 2 evidence dossier

- **Status: NOT PASSED — evidence only.** Only the human owner records a Gate disposition.
- **Base commit:** `d334139d11526e2abc4fad7d4ad09eced3b7da4a`; CI run `39664774001` passed Windows x64/MSVC and Linux/GCC.
- **Local follow-up:** `6ae4a3a` and `33d8392`; local-only and not CI-verified.
- **Scope:** read-only ISO inspection and synthetic test evidence. No boot, extraction, recompilation or compatibility claim.

## Owner prerequisites

- Formal Gate 0 disposition: **pending human review**.
- Independent provenance review of the ISO inspector: **not recorded**; the component remains `Provisional independent` in [CLEAN_ROOM_AUDIT.md](CLEAN_ROOM_AUDIT.md).
- Independent review of the build/CI/doctor layer: **not recorded**; that layer remains `Review required`.

## Criterion-to-evidence map

| Gate 2 criterion | Evidence | Current state |
|---|---|---|
| Deterministic inspection on synthetic fixtures | `tests/test_iso_inspector.py`: `test_inspects_synthetic_iso_and_elf`, `test_report_is_deterministic`, `test_error_is_deterministic`; JSON output is sorted by key. | Evidenced for the tested synthetic subset. |
| Robust rejection of malformed input | Explicit error taxonomy in [ISO_INSPECTOR.md](ISO_INSPECTOR.md); 250-case mutation smoke test asserts only `InspectError`; file-based mutation tests assert input bytes are unchanged. | Evidenced for the selected mutation set, not exhaustive fuzzing. |
| Read-only behavior | `test_file_mutations_preserve_input_bytes`; interleave cases check the input SHA-256 after rejection; the inspector has no write path. | Evidenced. |
| Clear unsupported-feature reporting | Stable codes including `MULTI_EXTENT_UNSUPPORTED` and `INTERLEAVED_UNSUPPORTED`; tests cover each interleave byte independently. | Evidenced for implemented rejection paths. |
| No writes outside a requested output directory | No extraction or output-directory feature exists; inspection writes nothing. | Partially applicable; extraction boundaries are not designed or implemented. |
| Single-volume ISO 9660 PVD and root `SYSTEM.CNF` | Synthetic success/error tests plus five read-only retail inspections recorded in [VERIFICATION_LOG.md](VERIFICATION_LOG.md) and [games/README.md](games/README.md). | Evidenced for the supported subset; not proof of broad retail-layout support. |
| BOOT path resolution and ELF metadata | Synthetic path, warning, ELF header and PT_LOAD tests; `SYSTEM.CNF` and boot hashes are reported. | Evidenced for the documented subset. |
| Directory survey | `IsoReader.survey` tests cover counts, depth, limits, multi-extent skip and interleaved counting; retail surveys recorded. | Evidenced as metadata-only; it does not read file data. |
| Safe extraction boundaries | No implementation or design record yet. | **Open.** |
| Multi-extent and ISO-variant support | Multi-extent layouts are rejected, not supported; Joliet, Rock Ridge and raw-sector variants are unsupported. | **Open by design; fail-closed.** |
| Interleave field provenance | ECMA-119 5th edition (December 2024), Table 8 (p. 37) and §§10.1.8–10.1.9 (p. 40); independent field tests. | Evidenced. Interleaved file data remains unsupported. |
| CI on the current evidence | `d334139` is green; `6ae4a3a` and `33d8392` are local-only. | **Open for the new commits.** |

## Retail sample limits

Five owner-authorized images completed read-only inspection. That sample is not Gate 2 evidence for broad compatibility:

- All five reported no interleaved or multi-extent records, so they do not exercise those layouts.
- `God of War II` has a PVD volume space smaller than the file; second-layer coverage is **Dugaan**.
- `Need for Speed - Most Wanted` has a boot executable above the 4 MiB materialization cap; the cap is unchanged.
- No image was extracted, booted or recompiled.

## What would close Gate 2

1. Owner records the formal Gate 0 disposition and an independent review of the ISO inspector's provenance.
2. A documented safe-extraction boundary (or an explicit decision that Gate 2 excludes extraction).
3. Review of the documented ISO variants and multi-extent handling, with synthetic tests for every accepted or rejected case.
4. Owner publication of the final evidence commit followed by green Windows x64/MSVC and Linux/GCC CI.
5. Owner records the Gate 2 disposition; this dossier must not be treated as that disposition.
