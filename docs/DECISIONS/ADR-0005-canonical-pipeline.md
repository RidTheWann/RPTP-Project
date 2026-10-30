# ADR-0005 — Canonical analysis and product path

- **Date:** 2026-10-30
- **Status:** Proposed — agent recommendation; only the owner may change it to Accepted or Rejected
- **Decision owner:** Human project owner
- **Recorded by:** Agent, under the standing 2026-10-28 branch/PR automation authorization
- **Related:** `R-031`, Gate 3, [IR_CFG.md](../IR_CFG.md), [RUNTIME.md](../RUNTIME.md), [instruction-semantics-matrix.md](../research/instruction-semantics-matrix.md), [PROVENANCE_PLAN.md](../PROVENANCE_PLAN.md)

## Context

RPTP must eventually recompile Emotion Engine code to C++ and execute the result on a native runtime. The repository currently contains four instruction-modelling paths that were built at different times and for different evidence purposes:

| Path | Files | Current role | Model and limits |
|---|---|---|---|
| Gate 0 spike | `tools/rptp_gate0_spike.py` | Accepted evidence for the narrow Gate 0 disposition | Ten-op acceptance scope over a 28-operation decoder, 64-bit registers, initialized-word map, no `LW`/`SW` alignment check |
| Legacy analysis/lowering | `tools/rptp_ir.py`, `tools/rptp_lower.py` | Host-side IR, CFG and deterministic lowering | 28 operations, 64-bit registers, initialized-word map, no `LW`/`SW` alignment check, no ordinary or likely branch forms |
| `tools/rptp` pipeline | `tools/rptp/isa.py`, `cfg.py`, `ir.py`, `oracle.py`, `codegen.py`, `native.py` | Decoder, CFG, IR, oracle and C++20 emitter | 142 decoder mnemonics, 42 Level B semantics, 128-bit register oracle, 32 MiB default-zero RAM, alignment checks, six ordinary and eight likely branch forms |
| Native runtime | `runtime/` (`rptp-load`, `rptp-run`) | Test vehicle for loading and synthetic execution | 42 Level B operations, 64-bit registers, mapped ELF segments only, alignment checks; no kernel, syscall, ISO ingestion or boot |

The path split is recorded as `R-031` in [RISKS.md](../RISKS.md). [instruction-semantics-matrix.md](../research/instruction-semantics-matrix.md) §5 documents the asymmetries: the legacy pipeline rejects the fourteen branch forms that `tools/rptp` and the runtime execute; the legacy paths do not check `LW`/`SW` alignment; the oracle and emitter model 128-bit registers and default-zero RAM while the runtime harness models 64-bit registers and mapped regions; and the Gate 0 spike and the legacy pipeline share the same 28-operation decoder set, although the accepted Gate 0 disposition scope is only ten operations.

`tests/test_cross_path_equivalence.py` runs one synthetic program through the `tools/rptp` oracle, the generated C++ and `rptp-run` and compares normalized final state. In the legacy path, `tests/test_ir_lowering.py` compares the generated C++ for the legacy lowering with the Gate 0 spike oracle, while `tests/test_ir_cfg.py` and `tests/test_cfg_reachability.py` are structural tests over the same IR and CFG. The new `tests/test_pipeline_path_contract.py` pins the capability split between the legacy lowering set and the fourteen forms only the newer path accepts.

No canonical path is declared today. An instruction tested on one path is not automatically supported, identically modelled or identically diagnosed on another. The absence of that decision is the remaining open part of `R-031`.

## Problem

Without a canonical path, every new instruction or runtime behavior creates three questions that the repository cannot answer consistently:

1. Which implementation is the semantic reference when the paths disagree?
2. May a new behavior be added to only one path, and what evidence does that path then need?
3. Which path must a future product recompiler and runtime be built from?

Multiple peer paths are useful while they are independent differentials. They become a liability when they silently grow different semantics, because a green test on one path can then be mistaken for support on another. The runtime is also a test vehicle today; calling it a product path without a decision would overstate its status.

## Options considered

1. **Declare `tools/rptp` plus `runtime/` canonical; freeze the legacy paths (recommended).** The newer package has the broader tested subset, the only cross-path differential to the native harness, alignment checks and the branch forms. The legacy pipeline and Gate 0 spike stay in place as frozen regression and provenance evidence.
2. **Keep all paths as peers (status quo).** Preserves existing evidence but leaves `R-031` open and requires every new behavior to be implemented and tested in up to four models.
3. **Make the legacy pipeline canonical.** It has the narrower 28-operation subset, no 4-byte `LW`/`SW` alignment check and no ordinary or likely branch forms; choosing it would discard the newer runtime coverage and cross-path evidence.
4. **Write one new unified path and delete the others.** Attractive long-term, but it is a large rewrite with no measured defect forcing it, and it would discard the independent differentials before their replacement is proven.

## Proposed decision

If the owner accepts this ADR:

1. **Canonical semantic reference:** `tools/rptp` (decoder, CFG, IR, oracle and codegen) is the reference implementation for synthetic instruction semantics. The oracle is the expected-state side of a differential, not a hardware model.
2. **Canonical product path:** the analysis and emission pipeline is `tools/rptp`; the designated product execution path is `runtime/`. The current runtime is a test vehicle and may not be described as a product runtime, kernel or boot path until it has separate evidence and a Gate disposition.
3. **Frozen legacy paths:** `tools/rptp_ir.py`, `tools/rptp_lower.py` and `tools/rptp_gate0_spike.py` receive no new instruction support or semantic changes. They remain available for regression and provenance evidence. Removing or retiring them requires a later owner-approved change.
4. **New behavior lands in the canonical path first:** a permitted `RPTP-REF-*` entry, an independent test that fails before the change, fail-closed diagnostics and cross-path coverage are required before the behavior is called supported.
5. **No silent divergence:** a path that does not implement a behavior must reject the relevant encoding or program with its stable diagnostic. It may not approximate, skip or silently lower the behavior.
6. **Model boundaries are explicit:** the canonical oracle and emitter currently use 128-bit registers and default-zero RAM; the runtime harness uses 64-bit registers and mapped regions. Those differences must be documented and tested at the boundary. Converging the runtime model is future work, not a claim made by this ADR.
7. **No status promotion:** this ADR changes no Gate, clean-room, provenance or compatibility status. Gate 3 remains not passed and Gate 2 remains open and read-only.

## Equivalence criteria

A behavior may be called cross-path verified only when all applicable criteria hold:

1. The canonical oracle, generated C++ and `rptp-run` observe the same normalized final GPR values, data bytes, stop PC, step count, executed-PC trace and halt reason for a synthetic program that exercises the behavior.
2. The test uses literal or independently derived expectations, not two copies of the same implementation.
3. A path outside the canonical set either agrees on its documented subset or rejects the behavior explicitly; the difference is recorded in the matrix and in a test.
4. Unsupported encodings and malformed inputs fail closed with stable diagnostics on every path that accepts the input.
5. Deterministic output is preserved: no timestamps, host paths or unordered data in generated sources or JSON.
6. The result is labelled synthetic evidence. Agreement between RPTP models is not hardware validation, a Gate 3 pass or a compatibility claim.

The existing `tests/test_cross_path_equivalence.py` satisfies criterion 1 for one shared program. `tests/test_pipeline_path_contract.py` records the current legacy capability boundary. Neither is an independent clean-room review.

## Migration stages

- **Stage 0 (this proposal):** record the decision package and the capability-contract test. No behavior changes, no path is declared canonical before owner acceptance.
- **Stage 1 (after owner acceptance):** update the contracts and status documents to name the canonical path; freeze new legacy semantics; route new instruction work through the canonical pipeline and its tests.
- **Stage 2:** add a legacy-versus-canonical differential for the 28-operation shared subset, or record and test the model-boundary exceptions explicitly. Do not claim equivalence beyond what the test observes.
- **Stage 3:** converge the runtime model with the canonical model, or document a deliberate product-model decision. This requires its own evidence and does not follow automatically from this ADR.
- **Stage 4:** retire or redirect a legacy path only with an owner-approved change and after its remaining evidence role is preserved.

## Non-goals and limits

- No new instruction, runtime service, kernel, syscall, IOP, DMA, VU, GS, SPU2, ISO extraction or game-compatibility behavior.
- No deletion of legacy code, tests or Gate 0 evidence.
- No claim that the current runtime is a product runtime or that the canonical path is complete.
- No clean-room certification, independent provenance disposition or Gate disposition.
- No claim that 128-bit register modelling is verified R5900 behavior; it is the current synthetic model choice.

## Consequences

- New work stops duplicating semantics across four paths and has one reference side for differentials.
- The legacy pipeline and Gate 0 spike remain available as frozen evidence, so the accepted Gate 0 record is not disturbed.
- `R-031` moves from "no proposal" to "proposal recorded; owner decision pending"; it remains open until the owner accepts or rejects this ADR and the migration stages complete.
- The 64-bit runtime harness versus 128-bit oracle remains an explicit, tested boundary rather than an implied equivalence.
- Documentation, tests and future increments must name which path they extend.

## Re-evaluation criteria

Revisit this ADR if the owner rejects the proposed canonical path, if a new analysis or execution path is introduced, if an instruction is added to a non-canonical path, if the runtime register model changes, or before the first vertical slice is declared. Only the owner may change the status; agents may update the evidence and record the outcome.
