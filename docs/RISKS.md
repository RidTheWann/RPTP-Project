# RPTP risks — baseline after Gate 0 spike

| ID | Risk | Likelihood / impact | Current mitigation | Trigger to revisit |
|---|---|---|---|---|
| R-001 | Writing the recompiler and runtime from scratch exceeds available engineering capacity. | High / Critical | Vertical slices; estimate in person-weeks; Gate Review required. | Three sessions without measurable progress or estimate range exceeded. |
| R-002 | The subset spike passes but does not generalize to R5900 quirks. | High / Critical | Explicitly label this as generic MIPS subset; use R5900-specific allowed references and tests before claiming support. | First PS2-specific instruction family is added. |
| R-003 | Generated C++ and oracle share the same bug or the oracle is inaccurate. | Medium / High | Add independent test vectors and permitted reference checks; do not rely on a self-comparison alone. | Any hardware-semantic instruction is promoted to supported. |
| R-004 | ELF parsing mishandles retail PS2 ELF variants or malicious input. | Medium / High | Validate lengths/offsets; fuzz parser in Gate 2; keep synthetic fixtures small and manifest-listed. | ISO Inspector is exposed to arbitrary user input. |
| R-005 | MSVC/Windows build differs from the local GCC host build. | High / High | Gate cannot pass until MSVC produces and executes the generated program. | Current Gate 0 review. |
| R-006 | Missing EE syscalls, IOP services, DMA behavior or timing blocks the first game. | High / Critical | Runtime diagnostics for missing services; implement based on measured first-game requirements. | Gate 4a vertical slice. |
| R-007 | VU/GS semantics, especially microprograms and pixel operations, consume most of the schedule. | High / Critical | Keep a renderer spike ADR; use pixel/state oracle tests; profile before optimizing. | Gate 4b and first VU workload. |
| R-008 | Unclear exposure history compromises the intended clean-room policy. | Medium / High | Preserve the explicit historical source exposure record; do not use prior implementation artifacts as design inputs. | Any newly discovered source or license exposure. |
| R-009 | License is not approved while repository is public. | Medium / High | Keep RPTP repository empty; do not push code or add `LICENSE` until the human approves the ADR. | Before Gate 1 / B1b. |
| R-010 | Generated C++ compilation time or code size becomes impractical. | Medium / High | The current spike records deterministic source hash only; measure translation-unit sizing and compile time after the Program Model exists. | Gate 3 produces more than fixture-sized output. |

## Gate 3 and Gate 4 effort ranges (initial, low confidence)

Assumptions: one experienced systems engineer working full time; no reuse of emulator/recompiler implementation code; only permitted public documentation and independently generated test inputs; first test title selected for measured simplicity; ranges express engineering effort, not calendar promises.

- **Gate 3 — recompiler MVP:** 20–60 person-weeks. Includes enough R5900 decode/semantics, reference interpreter, C++ code generation, analyzer, differential tests and failure diagnostics to satisfy the master prompt's scope. Confidence is low because the current spike covers only 10 instruction mnemonics.
- **Gate 4 — first gameplay vertical slice after Gate 3:** 40–120 additional person-weeks. Includes a selected title's boot path, minimum kernel/IOP/CDVD path, the necessary DMA/VU/GS behavior, input/audio/save support and cold-boot/gameplay verification. Confidence is very low because title complexity is not yet measured.

These are deliberately wide initial ranges. The current 28-instruction synthetic spike is not evidence that the full work will fit within the lower bound. After `rptp inspect` and title selection exist, replace the assumption with a workload-specific estimate.
