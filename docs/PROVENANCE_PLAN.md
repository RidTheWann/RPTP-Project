# Provenance execution plan

- **Date:** 2026-10-23
- **Status:** Execution plan, not a certification. Prepared under the owner's explicit 2026-10-23 instruction that delegated recording of the narrow Gate 0 technical pass.
- **Policy:** [ADR-0003](DECISIONS/ADR-0003-sealed-source-clean-room-policy.md)
- **Exposure record:** [REFERENCES.md](REFERENCES.md)
- **Component audit:** [CLEAN_ROOM_AUDIT.md](CLEAN_ROOM_AUDIT.md)
- **Gate 0 disposition:** [GATE0_REVIEW.md](GATE0_REVIEW.md)

## Purpose

This plan makes the provenance obligations concrete enough to execute. It defines what is currently traceable, what still needs independent review or re-derivation, what remains prohibited, and what evidence must exist before RPTP can be described as release-ready.

It does **not** certify any file, erase the historical source exposure, replace legal advice, or authorize access to sealed material. The owner remains responsible for clean-room and release decisions.

## Scope and non-claims

This plan covers the Gate 0 synthetic spike, the read-only ISO inspector, the build/CI/doctor layer, documentation, synthetic fixtures, dependencies, and any future recompiler or runtime increment.

It does not change:

- the Gate 0 disposition, which is a technical pass for the narrow synthetic scope only;
- Gate 2, which remains open, read-only and not passed;
- the `Review required` status of the build/CI/doctor layer;
- the prohibition on extraction, retail execution, boot or compatibility claims; or
- the rule that only the owner records gate and release dispositions.

## Current provenance inventory

| Area | Traceable evidence | Open provenance work | Current status |
|---|---|---|---|
| Gate 0 synthetic fixture, ELF parser, oracle and C++ generator | Neutral references `RPTP-REF-001`–`005`; focused tests; fixture and generated-source SHA-256; manifest entry; recorded compiler runs | Independent reviewer must inspect the implementation, tests, history and exposure record and record a conclusion. No file-level authorship log exists. | `Provisional independent` |
| Read-only ISO inspector | ECMA-119 `RPTP-REF-006`; synthetic and mutation tests; recorded CTest and retail read-only records | Independent reviewer must inspect the implementation and tests before Gate 2 closure. | `Provisional independent` |
| CMake, CI, doctor and build wrappers | Agent-led re-derivation against `RPTP-REF-007`–`012`; contract tests; local runs | Prior exposure included sealed build configuration and scripts. Independent review or further re-derivation is required. | `Review required` |
| Runtime and recompiler expansion | The 26-instruction catalog, IR/CFG, deterministic lowering, boot-code census, native loader and test-only execution harness under `runtime/`, each with named tests | Every new subsystem must follow the per-increment procedure below. The expansion prerequisite is met and increments are recorded; no clean-room claim exists yet. | `Recorded` |
| Documentation and exposure record | Git history; ADR-0001; ADR-0003; the exposure table in `REFERENCES.md` | Update whenever exposure, references or scope changes. | `Recorded` |
| Synthetic fixtures | `tests/fixtures/MANIFEST`; hashes; artifact guard | Any new binary fixture needs origin, license and hash registration. | `Recorded` |
| Third-party dependencies | `docs/LICENSES.md`; no implementation dependency currently vendored or linked | Audit before adding any dependency. | `Recorded` |

The status labels are defined in [CLEAN_ROOM_AUDIT.md](CLEAN_ROOM_AUDIT.md). `Recorded` means documentation or metadata exists; it is not an implementation certification.

## What is traceable now

The following claims can be traced to repository evidence:

- each non-trivial implemented behavior is expected to map to a permitted reference in `REFERENCES.md` and to a named test;
- the synthetic fixture and generated C++ have recorded SHA-256 values, and regeneration is the reproducibility mechanism;
- the component audit records exposure relevance and current status for each area;
- published commits and CI runs provide a timeline for the published baseline; and
- the historical exposure record states what was viewed and when policy changed.

The following cannot be proven from repository evidence alone:

- the subjective design influence of material viewed before ADR-0003;
- that no sealed material was consulted in undocumented work outside the recorded sessions;
- that functional similarity reflects independent design rather than imitation; or
- that the current tests exercise every relevant behavior.

These limits are why the independent reviews below remain mandatory. An agent assertion is not a substitute.

## Prohibited material and actions

1. Do not open, clone, browse, search, fetch or summarize PS2Recomp, PS2 Web Recomp, PCSX2, Play! or any other emulator/recompiler implementation source, build files, scripts, tests, issues, release notes or implementation documentation.
2. Do not use a sealed project as a design template, code source, test oracle, naming source or directory-layout source.
3. Do not treat a specification hosted by a sealed project as permitted without owner review; use a neutral copy or record the gap.
4. Do not add retail ISOs, BIOS files, game executables, extracted assets, game-derived generated output, personal absolute paths or secrets to the repository.
5. Do not add or update a runtime/recompiler feature without the per-increment provenance record and tests described below.
6. Do not describe any component as clean-room certified, independently reviewed or legally cleared unless the review evidence exists.

## Per-increment procedure for recompiler and runtime work

Before committing a new behavior, the change must record:

1. **Behavior statement:** the exact instruction, format or service behavior being added, and the explicit non-goals.
2. **Permitted reference:** one or more `RPTP-REF-*` entries, or a new entry added to `REFERENCES.md` with access date, permitted use and limits. Hardware claims need a neutral, citable source or an independent measurement.
3. **Independent test:** a test that fails before the implementation and does not simply compare two copies of the same logic. The test path and expected failure mode must be named in the commit body.
4. **Fail-closed behavior:** explicit diagnostics for unsupported encodings, missing services or malformed input. Silent fallback is not acceptable.
5. **Scope check:** confirm the change does not expand beyond the approved behavior or imply compatibility beyond tested inputs.
6. **Audit update:** update the relevant `CLEAN_ROOM_AUDIT.md` row and `REFERENCES.md` when the evidence or status changes.
7. **Evidence record:** after the run, append the commands and results to `VERIFICATION_LOG.md`; do not rewrite earlier entries.
8. **Commit body:** name the behavior, reference IDs and test paths so the change can be audited from history.

If any item cannot be satisfied, stop before committing the feature. Record the gap in `RISKS.md` and, if it affects provenance, in the audit rather than weakening the requirement.

## Independent review gates

The following reviews must be performed by a reviewer who is independent of the implementation work. The reviewer may use the repository, the exposure record, the tests and the published history. Access to sealed material is not authorized by this plan; if a review appears to require it, the owner must decide under legal guidance.

### Before Gate 2 closure

- Review the read-only ISO inspector's implementation, tests and reference basis.
- Record files reviewed, commit hash, reference-to-behavior mapping, test evidence and unresolved concerns.
- Update the audit status only if the evidence supports it.
- Do not expand this into a clean-room certification of unrelated components.

### Before product release

- Review the Gate 0 spike and its later history against the exposure record.
- Review the build/CI/doctor layer, which remains `Review required` because of prior exposure to sealed build files and scripts.
- Review any runtime/recompiler subsystem added after this plan.
- Record a repository-level conclusion covering remaining uncertainty and any area that must be quarantined.
- Complete any legal review the owner considers necessary for distribution.

A release may be blocked by an unresolved review even if all tests pass. Passing tests prove behavior, not provenance.

## Re-derivation and quarantine procedure

If a file or area cannot demonstrate independent provenance:

1. Stop work in that area.
2. Record the concern and the affected paths in `RISKS.md`, the audit and the exposure record as appropriate.
3. Quarantine the area from further expansion and from release claims.
4. Re-derive it from permitted references and tests, or obtain the independent review that resolves the concern.
5. Record the disposition and the evidence before resuming.

An accidental encounter with sealed material follows the same stop rule. Do not use the material, do not copy it into notes, disclose the encounter and wait for the owner.

## Review evidence template

An independent review record must contain at least:

- reviewer identity or role, date and commit hash;
- files and behaviors reviewed;
- permitted references and tests checked;
- exposure-record entries considered;
- an explicit statement of what was **not** reviewed;
- unresolved similarities, uncertainties or gaps;
- the resulting status recommendation; and
- the owner's acceptance or rejection of that recommendation.

Without this record, the maximum honest status is `Provisional independent` for independently authored areas and `Review required` where functional overlap with sealed material exists.

## Execution order and ownership

1. **Owner delegation recorded:** Gate 0 narrow technical pass, 2026-10-23. Evidence and limits are in `GATE0_REVIEW.md`.
2. **Agent:** apply the per-increment procedure to the next smallest recompiler/runtime behavior; keep tests and references with the change.
3. **Agent:** keep Gate 2 read-only and fail-closed; do not implement extraction.
4. **Owner:** commission or perform the independent ISO inspector review before Gate 2 closure.
5. **Owner:** commission or perform the independent Gate 0 and build-layer reviews before product release.
6. **Owner:** record all gate, clean-room and release dispositions. The agent supplies evidence only.

## Non-certification statement

Recording this plan satisfies the owner's prerequisite for a concrete provenance plan. It does not certify RPTP, any component, any commit or any future work as clean-room. The historical exposure remains documented, the build/CI/doctor layer remains `Review required`, and independent review remains a release prerequisite.
