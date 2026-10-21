# RPTP risks — baseline after Gate 0 spike

| ID | Risk | Likelihood / impact | Current mitigation | Trigger to revisit |
|---|---|---|---|---|
| R-001 | Writing the recompiler and runtime from scratch exceeds available engineering capacity. | High / Critical | Vertical slices; estimate in person-weeks; Gate Review required. | Three sessions without measurable progress or estimate range exceeded. |
| R-002 | The subset spike passes but does not generalize to R5900 quirks. | High / Critical | Explicitly label this as a generic MIPS subset; use permitted R5900-specific references and independent tests before claiming support. | First PS2-specific instruction family is added. |
| R-003 | Generated C++ and oracle share the same bug or the oracle is inaccurate. | Medium / High | Add independent test vectors and permitted reference checks; do not rely on self-comparison alone. | Any hardware-semantic instruction is promoted to supported. |
| R-004 | ELF parsing mishandles retail PS2 ELF variants or malicious input. | Medium / High | Validate lengths/offsets; fuzz parser in ISO Inspector; keep synthetic fixtures small and manifest-listed. | ISO Inspector is exposed to arbitrary user input. |
| R-005 | MSVC/Windows behavior differs from host toolchains. | Medium / High | The narrow generated-source differential spike has passed on MSVC; add CI so it stays reproducible and visible. Do not infer full project or game compatibility. | CI fails or new instruction behavior is added. |
| R-006 | Missing EE syscalls, IOP services, DMA behavior or timing blocks the first game. | High / Critical | Runtime diagnostics for missing services; implement based on measured first-game requirements. | First-game boot vertical slice. |
| R-007 | VU/GS semantics, especially microprograms and pixel operations, consume most of the schedule. | High / Critical | Keep a renderer spike ADR; use pixel/state oracle tests; profile before optimizing. | Renderer/GPU prototype begins. |
| R-008 | Historical source exposure compromises the intended clean-room policy. | Medium / High | Preserve the explicit exposure record; do not use previously viewed project artifacts as templates; require owner disposition before extending affected implementation areas. | Before expanding recompiler/runtime implementation beyond the isolated spike. |
| R-009 | License, dependency compatibility or publication policy is unclear. | Medium / High | GPL-3.0-or-later is the selected project license and is published. Audit every third-party dependency and keep prior-source exposure review separate. | Before adding/vendoring a dependency or redistributable asset. |
| R-010 | Generated C++ compilation time or code size becomes impractical. | Medium / High | Current evidence records deterministic source hash only; measure translation-unit sizing and compile time after the program model exists. | Gate 3 produces more than fixture-sized output. |
| R-011 | CI workflow/toolchain drift creates false confidence or false failures. | Medium / Medium | Test Windows/MSVC and Linux/host separately; record runner/toolchain versions; do not equate CI green with game compatibility. | First CI run or runner image/toolchain change. |

## Gate 3 and Gate 4 effort ranges (initial, low confidence)

Assumptions: one experienced systems engineer working full time; no reuse of emulator/recompiler implementation code; only permitted public documentation and independently generated test inputs; first test title selected for measured simplicity; ranges express engineering effort, not calendar promises.

- **Gate 3 — recompiler MVP:** 20–60 person-weeks. Includes enough R5900 decode/semantics, reference interpreter, C++ code generation, analyzer, differential tests and failure diagnostics to satisfy the agreed project scope. Confidence is low because the current spike covers only 10 instruction mnemonics.
- **Gate 4 — first gameplay vertical slice after Gate 3:** 40–120 additional person-weeks. Includes a selected title's boot path, minimum kernel/IOP/CDVD path, necessary DMA/VU/GS behavior, input/audio/save support and cold-boot/gameplay verification. Confidence is very low because title complexity is not yet measured.

These are deliberately wide initial ranges. The current 28-instruction synthetic spike is not evidence that the full work will fit within the lower bound. After ISO inspection and title selection exist, replace the assumptions with a workload-specific estimate.
