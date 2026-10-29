# RPTP documentation map

This map lists every tracked document in the repository. `tests/test_doc_freshness.py` fails when a document is missing from this map, when a mapped path does not exist, or when the current-status pointers in `docs/STATE.md` / `docs/HANDOFF.md` lag behind the append-only evidence log.

Every increment must review and update every document affected by its change before merge; see [AGENTS.md](../AGENTS.md). A historical record such as a decision or a dated log entry is not rewritten, but no document may keep a superseded date, PR/run pointer, count or status claim.

## Start here

- `README.md` — project overview, public status, build entry points and links.
- `AGENTS.md` — mandatory agent rules, documentation-freshness rule and verification commands.
- `docs/STATE.md` — single current status, blockers and next steps.
- `docs/HANDOFF.md` — operational handoff, expected commands and next actionable step.
- `docs/ROADMAP.md` — phases, pass criteria and current status per phase.
- `docs/VERIFICATION_LOG.md` — append-only dated evidence record; never rewrite earlier entries.
- `docs/README.md` — this map.

## Status and evidence

- `docs/COMPATIBILITY.md` — platform and sample results; explicitly not a game-compatibility list.
- `docs/BOOT_CENSUS.md` — read-only boot-code census contract, the dated eight-image pre-`SUBU` table and the measured one-image post-`SUBU` refresh (`R-029`).
- `docs/EXECUTION_CONTEXT.md` — compact context snapshot for a new session.
- `docs/RISKS.md` — risk register, mitigations and revisit triggers.
- `docs/GATE0_REVIEW.md` — recorded narrow Gate 0 technical disposition and limits.
- `docs/GATE2_EVIDENCE.md` — Gate 2 criterion-to-evidence dossier; not a disposition.
- `docs/CLEAN_ROOM_AUDIT.md` — component provenance status.
- `docs/PROVENANCE_PLAN.md` — per-increment procedure and independent-review gates.
- `docs/REFERENCES.md` — permitted references, provenance contracts and exposure record.
- `docs/LICENSES.md` — project license, SPDX policy and third-party notices.
- `docs/INCREMENT_LEDGER.md` — reconstructed behavior, reference and test trail per increment.

## Contracts

- `docs/INSTRUCTION_CATALOG.md` — supported synthetic instruction subset and verification level.
- `docs/IR_CFG.md` — IR, CFG, known-edge reachability and lowering contract.
- `docs/FUNCTION_DISCOVERY.md` — conservative read-only direct-evidence discovery contract, error taxonomy and non-claims.
- `docs/RUNTIME.md` — native loader and synthetic execution-harness contract.
- `docs/ISO_INSPECTOR.md` — read-only ISO 9660 inspection contract and format envelope.
- `docs/ISO_INSPECTOR_REVIEW.md` — independent inspector review findings against `4c0df86`; not a Gate disposition.
- `docs/BUILD_PROVENANCE.md` — build/CI/doctor reference basis and current contracts.
- `docs/BUILDING_WINDOWS.md` — Windows x64 build and verification instructions.

## Decisions

- `docs/DECISIONS/ADR-0001-foundation-and-clean-room.md` — foundation, license and clean-room decision.
- `docs/DECISIONS/ADR-0002-renderer-spike-plan.md` — renderer spike plan; selection remains open.
- `docs/DECISIONS/ADR-0003-sealed-source-clean-room-policy.md` — accepted sealed-source policy.
- `docs/DECISIONS/ADR-0004-gate2-read-only-scope.md` — read-only Gate 2 scope; extraction deferred.

## Research notes

- `docs/research/gs-vu-backend-plan.md` — GS backend and VU0/VU1 boundary design brief: renderer proposal, synthetic rendering milestone, VU service boundary and staged path; no implementation, reference approval or Gate disposition.
- `docs/research/performance-baseline.md` — synthetic generated-C++ performance baseline: environment, method, re-measured numbers, corrections to the 2026-10-30 draft and a deferred optimization backlog.
- `docs/research/function-discovery.md` — trusted-seed function discovery, code/data ambiguity and the open jump-table gap.
- `docs/research/runtime-hle-boundary.md` — inspector-to-runtime handoff, staged Gate 4a HLE increments, deferred extraction threat model and owner decisions.
- `docs/research/r5900-isa.json` — R5900/MMI encoding catalog with per-entry page citations; provenance is pending owner review, so the catalog is not an approved reference and its claims are not verified semantics — see [isa-evidence.md](research/isa-evidence.md).
- `docs/research/isa-evidence.md` — evidence levels for the R5900 ISA catalog: decoder cross-check, test-defined subset with approved references, and pending/unverified citations.
- `docs/research/instruction-semantics-matrix.md` — per-instruction semantic evidence matrix across decoder, oracle, CFG, IR/emitter, native runtime and approved references; path asymmetries and a planning recommendation.

## Game records

- `docs/games/README.md` — game work index, rules and status ladder.
- `docs/games/black/STATUS.md` — Black (USA) read-only record.
- `docs/games/bully/STATUS.md` — Bully (USA) read-only record.
- `docs/games/downhill-domination/STATUS.md` — Downhill Domination (USA) read-only record.
- `docs/games/god-of-war-ii/STATUS.md` — God of War II (USA) read-only record.
- `docs/games/grand-theft-auto-san-andreas-indonesian-v6/STATUS.md` — owner-described Indonesian-language mod record.
- `docs/games/grand-theft-auto-san-andreas-usa-v300/STATUS.md` — owner-described original USA sample record.
- `docs/games/need-for-speed-most-wanted/STATUS.md` — Need for Speed - Most Wanted (USA) (v2.00) record.
- `docs/games/resident-evil-4/STATUS.md` — Resident Evil 4 (USA) record.

## External

- `third_party/README.md` — third-party material boundary; not mapped as RPTP documentation.
