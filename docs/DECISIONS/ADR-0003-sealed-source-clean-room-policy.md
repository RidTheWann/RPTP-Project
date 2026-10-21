# ADR-0003 — Sealed-source clean-room policy

- **Date:** 2026-10-21
- **Status:** Accepted
- **Decision owner:** Human project owner
- **Related:** ADR-0001, `docs/REFERENCES.md`, `docs/RISKS.md`, `docs/EXECUTION_CONTEXT.md`

## Context

ADR-0001 records prior source exposure involving PS2Recomp and PS2 Web Recomp. The exposure includes README material, repository metadata, build configuration and two build scripts. No recorded tool output fetched the PS2 Web Recomp runtime implementation, but this is not a clean slate.

The owner had to decide how to handle the exposure before expanding the recompiler or runtime. On 2026-10-21 the owner selected the strict option: **keep competitor/reference projects sealed and rebuild affected work from neutral specifications and independent tests**, re-deriving anything that cannot demonstrate provenance.

A historical exposure cannot be erased. This ADR defines how future work is kept separate from the previously viewed material. It records a process decision; it is not a legal opinion and cannot guarantee a particular legal outcome.

## Decision

1. **Sealed projects.** PS2Recomp, PS2 Web Recomp, PCSX2, Play! and any other emulator or recompiler implementation are sealed. Do not open, clone, browse, search, fetch, or ask an agent to inspect their source code, build files, scripts, tests, issues, release notes or implementation documentation.
2. **No new access.** The sealed list is not exhaustive. Treat any implementation-level emulator/recompiler material as sealed unless the owner explicitly approves a neutral specification as a reference.
3. **No implementation use.** Do not copy, adapt, translate, paraphrase into code, or use as a design template any material from a sealed project. Previously viewed build configuration and scripts must not shape RPTP build files, directory layout or helper code.
4. **Independent derivation.** New behavior must be derived from permitted neutral specifications and independent experiments. Generic public MIPS, ELF and ISO 9660 documentation is permitted when recorded in `docs/REFERENCES.md`; hardware- or game-specific claims require their own evidence.
5. **Quarantine rule.** If any existing or future file cannot demonstrate independent provenance, stop work on that area, record the concern, quarantine the file or area, and re-derive it. Do not silently clean up or rewrite a contaminated area without recording the event.
6. **Provenance ledger.** Every non-trivial behavior claim must identify the permitted reference or independent test that supports it in `docs/REFERENCES.md`. An unsupported claim is not a supported feature.
7. **Synthetic inputs only.** Keep binary fixtures synthetic, manifest-registered and hash-checked. Never add commercial ISOs, BIOS files, game executables, extracted assets or sealed-project artifacts.
8. **Review before expansion.** Before adding a recompiler or runtime subsystem, check the sealed-source boundary and provenance record. Any accidental access to sealed material must be disclosed and evaluated before that work continues.
9. **No legal guarantee.** This policy is intended to create a defensible, auditable clean-room record. It does not replace legal review, and it does not erase the historical exposure disclosed in `docs/REFERENCES.md`.

## Permitted neutral sources

The following categories are permitted when they are not implementation source from a sealed project:

- Public ISA, ELF and ISO 9660 format specifications.
- Publicly documented platform behavior that is not copied from an emulator/recompiler implementation.
- Independently authored tests, fixtures and measurements.
- Original RPTP code and documentation.

A specification hosted by a sealed project is not automatically approved; use a neutral copy or request owner review first.

## Procedure for new work

1. State the behavior or format being implemented.
2. Identify the permitted neutral reference and record it in `docs/REFERENCES.md`.
3. Write an independent test or measurement that would fail if the behavior is wrong.
4. Implement without consulting sealed material, and keep the test with the implementation.
5. Record the verification result and any remaining uncertainty.
6. If sealed material is encountered accidentally, stop, disclose it in the exposure record, quarantine affected work and ask the owner to review before continuing.

## Existing work assessment

This policy sets a provenance bar for existing work; it does not certify that work automatically.

- The Gate 0 synthetic fixture, ELF parser, interpreter and generator are recorded as independently authored from neutral MIPS/ELF references. No sealed implementation file is recorded as copied.
- The ISO inspector is recorded as independently authored from ELF and ISO 9660 structures. It needs a recorded ECMA-119 reference and an independent provenance review.
- The CMake presets, CI workflows, doctor and build wrappers are functionally similar to material seen in PS2 Web Recomp. They are flagged `Review required`; do not describe B1b as clean-room certified until an independent provenance review or re-derivation is recorded.
- Documentation that records exposure is evidence, not an implementation source.
- No existing file is certified merely by this ADR. Component-level status is tracked in `docs/CLEAN_ROOM_AUDIT.md`.

## Consequences

- Some work will take longer because it must be re-derived and tested independently.
- Existing Gate 0 and ISO inspector work remains usable only if its provenance is traceable to permitted references and tests.
- The project cannot claim that the previously viewed material was never seen. It can claim that the material is disclosed, sealed and not used as an implementation source.
- A future decision to use a sealed project would require a superseding ADR and an explicit quarantine/re-derivation plan.

## Re-evaluation criteria

Only the human owner may change this policy. Revisit it if:

- A legal or publication question requires a different exposure model.
- A contributor cannot demonstrate independent provenance for affected work.
- A sealed project is proposed as a dependency or reference.
- New evidence shows that previously viewed material has entered the implementation.
