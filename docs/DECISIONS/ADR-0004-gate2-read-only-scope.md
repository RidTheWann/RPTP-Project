# ADR-0004 — Gate 2 is a read-only inspection milestone

- **Date:** 2026-10-22
- **Status:** Accepted — owner-delegated scope decision
- **Decision owner:** Human project owner
- **Recorded by:** Agent, under the owner's 2026-10-22 continuation instruction
- **Related:** Gate 2, `docs/GATE2_EVIDENCE.md`, `docs/ISO_INSPECTOR.md`, `docs/RISKS.md`, ADR-0003

## Context

The earlier Gate 2 plan included safe extraction boundaries. The Gate 2 evidence dossier therefore treated a missing extraction design as an open gate criterion. The owner selected a narrower read-only Gate 2 milestone and delegated the recording of that engineering scope decision to this session.

Extraction would add a write path, a destination policy, overwrite and traversal protection, disk-exhaustion handling, and decisions about extracted proprietary content. None of those controls exists, and none is required to prove that the current inspector reads an image deterministically, rejects unsupported layouts and leaves the input unchanged.

## Decision

1. Gate 2 is a **read-only inspection milestone**. Its scope is parsing, validation, metadata reporting, hashing and synthetic/retail inspection evidence.
2. Gate 2 does not include extraction, materialization to a destination directory, a write API, an output-directory option, or writing to the inspected image or host filesystem.
3. "No writes outside a requested output directory" is replaced by the stronger read-only criterion: **no write path to the input or host during Gate 2**. The inspected image is opened read-only.
4. Extraction is future work, not a Gate 2 prerequisite. It requires a separate ADR and threat model before implementation, covering at minimum path traversal, overwrite policy, link/reparse behavior, destination boundaries, disk exhaustion, extracted-content handling and output provenance.
5. The 4 MiB materialization cap remains an inspection limit. It is not a Gate 2 blocker and does not authorize an extraction path.
6. This decision does not claim that any future extraction implementation would be safe, and it does not relax the fail-closed rules for unsupported ISO layouts.

## Consequences

- Gate 2 can be reviewed without an extraction design; extraction no longer blocks the read-only milestone.
- The repository must not expose an extraction command or output directory as if this decision approved one.
- A future extraction proposal must return for an explicit architecture and provenance decision; it cannot rely on this ADR as authorization.
- Documentation, the roadmap and the risk register must describe extraction as deferred future work.

## Re-evaluation criteria

Revisit this ADR if the owner broadens Gate 2, requests an extraction prototype, or adds a write-capable inspection mode. Only the owner may change the scope. Any extraction work requires a superseding ADR and a threat model before code is added.
