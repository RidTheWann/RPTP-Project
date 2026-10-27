# ADR-0005 — Concept-level references and independent implementation

- **Date:** 2026-10-27
- **Status:** Proposed
- **Decision owner:** Human project owner
- **Related:** ADR-0001, ADR-0003, `docs/REFERENCES.md`, `docs/CLEAN_ROOM_AUDIT.md`, `docs/PROVENANCE_PLAN.md`

## Context

The owner clarified that RPTP may take inspiration from ideas found in other projects, while RPTP itself must be built independently. A useful high-level feature idea and an implementation recipe are not the same thing. RPTP needs a documented boundary so that product inspiration does not quietly become code, test, or architecture reuse.

On 2026-10-27, a web search accidentally surfaced a search-result snippet from a GitHub issue associated with `cout970/mips-emulator`. The page was not opened or clicked. The exposure is recorded in `docs/REFERENCES.md`; it was not used as a technical authority or implementation input. This ADR does not retrospectively reclassify that snippet as a permitted reference.

## Proposed decision

1. **Conceptual references may inform ideas.** Once this ADR is accepted by the owner, agents may consult public, high-level material from related projects—such as feature summaries, public-facing README sections, user documentation, screenshots, user workflows, release announcements, and broad problem statements—to understand goals, capability gaps, user expectations, or possible features. This is inspiration and comparison only.

2. **Log every intentional conceptual reference.** Record the source, access date, specific high-level idea considered, intended RPTP use, and limitations in `docs/REFERENCES.md`. Clearly label it as a *conceptual reference*, not a technical source. Do not imply that a project’s feature list proves correctness, compatibility, or performance.

3. **Implementation material remains excluded.** Do not consult or use source code, code snippets, patches, tests, test fixtures, build configuration, scripts, internal APIs, implementation-focused design documents, disassembly, or technical issue/PR discussions that reveal how a related project implements a feature. Do not copy, adapt, translate, paraphrase into code, or line-by-line recreate another project's implementation. Changing names, formatting, or syntax is not independent authorship.

4. **Implement independently from requirements and neutral technical evidence.** Convert the selected idea into an RPTP-owned requirement and test plan. Write tests and expected values independently. For ISA, file-format, platform, and runtime behavior, use neutral authoritative specifications and reproducible experiments as technical references. Choose RPTP-specific structures, APIs, control flow, and diagnostics based on the project’s own constraints. When the behavior is not specified by an authoritative source, state the uncertainty and test the RPTP-defined contract instead of claiming hardware accuracy.

5. **Handle accidental exposure.** If implementation-level material appears unexpectedly, stop work in the affected area, do not use the material, record what was seen and how far it was accessed in `docs/REFERENCES.md`, identify potentially affected files, and wait for owner review before proceeding. If affected work cannot demonstrate independent provenance, quarantine and re-derive it or obtain a documented independent review. Do not fetch the page again merely to investigate the exposure.

6. **Preserve all other boundaries.** This amendment does not change the GPL-3.0-or-later license, synthetic-fixture-only rule, banned commercial assets, evidence requirements, technical Gate dispositions, Gate 2 read-only policy, or the requirement for independent provenance review. It does not create a legal guarantee or certify any existing file as clean-room.

## Relationship to ADR-0003

ADR-0003 remains accepted and operative until the owner changes this ADR's status to **Accepted**. If accepted, this ADR supersedes only the blanket prohibition on *high-level conceptual reference* use. All exclusions on implementation material and all existing exposure records, review requirements, and technical scope limits remain in force. No clean-room certification follows from accepting this ADR.

## Consequences

- RPTP may learn from broad product goals and feature ideas without treating another project's implementation as a template.
- High-level inspiration and technical correctness are documented separately, with independent tests as the implementation contract.
- Provenance records will be more explicit, not less. Similar user-visible behavior does not establish copying, and superficial code differences do not establish independent authorship.
- The policy remains an engineering process boundary, not legal advice. Obtain legal review when a publication or rights question requires it.

## Re-evaluation criteria

Revisit this ADR if a contributor needs implementation-level material to proceed, if independent implementation cannot be demonstrated, if a dependency is proposed, or if legal review requires a different provenance model.
