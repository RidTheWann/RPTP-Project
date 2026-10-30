# Runtime and HLE boundary — design note for the first vertical slice

- **Date:** 2026-10-30
- **Status:** design/research note. No implementation, no Gate disposition, no ADR disposition.
- **Scope:** the boundary between the read-only ISO inspector and a product runtime, the smallest safe Gate 4a (boot) HLE increments, and the deferred extraction threat model.
- **Policy:** [ADR-0003](../DECISIONS/ADR-0003-sealed-source-clean-room-policy.md), [ADR-0004](../DECISIONS/ADR-0004-gate2-read-only-scope.md), [PROVENANCE_PLAN.md](../PROVENANCE_PLAN.md).
- **Gate position:** Gate 2 is read-only and not passed. Gate 3 is in progress and not passed. Gate 4 has not started. This note cannot be cited as Gate 4 evidence.

## 1. Method, evidence labels and hard limits

This note is written from the repository only: the runtime sources and tests under `runtime/`, the inspector sources and tests, and the documents listed above. Only `RPTP-REF-001`–`017` are approved references. No Sony EE/VU/BIOS manual, no emulator or recompiler implementation, and no sealed material were consulted. Where a platform-specific value would be needed, this note states that it is **undefined** and does not supply a number.

Labels used below follow [AGENTS.md](../../AGENTS.md) §4:

| Label | Meaning here |
|---|---|
| **Terverifikasi (T)** | Executed in this session and the result is recorded in §10. |
| **Source-read (R)** | Read in the named file this session; not exercised by an independent probe unless a named test was executed. |
| **Belum diverifikasi (U)** | Stated by a repository contract or recorded evidence, but not exercised against that input in this session. |
| **Dugaan (D)** | Inference or planning estimate, not a measured fact. |
| **RPTP policy (P)** | A project choice. It is not a PS2 hardware fact and must not be described as one. |

Two consequences follow and constrain everything below:

1. **No approved reference currently defines PS2 platform behavior.** `REFERENCES.md` permits generic MIPS/ELF/ISO 9660 material, tool documentation and RPTP tests. It contains no approved memory map, exception/interrupt model, kernel service interface, BIOS service semantics, CDVD command interface, IOP RPC contract, controller protocol or audio protocol. Any such fact in a future increment needs a new recorded reference or an independent measurement, and the owner decides whether it is permitted.
2. **A design can be complete while the implementation remains blocked.** The structure below is actionable now; the platform-specific content of Gate 4a is not.

### 1.1 What must not be built yet

Per the fixed decisions and Gate boundaries, the following are out of scope until their own evidence and owner disposition exist, and none is implemented or proposed for implementation by this note:

- EE kernel, syscall services, exception/interrupt delivery, COP0 state, TLB or timers.
- BIOS HLE service implementations, or reading/using a real BIOS image.
- IOP CPU, IOP modules (IRX), RPC, DMA, VU, GS, SPU2.
- CDVD commands beyond the boundary described in §4.5; controller and audio behavior (Gate 4c).
- ISO extraction, a write path, an output directory, or materialization to host files.
- A JIT, a dynamic loader, or generated code loaded from guest memory.
- Memory-map constants, vector addresses, register addresses or service numbers.
- Any boot, compatibility, timing or hardware-fidelity claim.

## 2. Current-capability matrix of `runtime/`

All rows are **T** for file and test existence; behavioral descriptions are **R** from the named sources, and the focused suites were executed as recorded in §10.

| Component | Implemented behavior | Limits that constrain HLE | Tests |
|---|---|---|---|
| `GuestMemory` (`runtime/include/rptp/runtime/guest_memory.hpp`, `runtime/src/guest_memory.cpp`) | Sparse `std::map<uint32_t, std::vector<uint8_t>>` regions. Maps a region with initial bytes and zero fill; read/write/view must fit inside **one** region; overlap, zero-size mapping, 32-bit overflow and the byte budget are rejected. 32-bit index space and 64 MiB default budget are RPTP policies. | No permissions (R/W/X) in memory itself; no MMIO hooks; no aliases; no unmap/clear; no dirty tracking; no page granularity; no snapshot. `map` copies, so guest memory is host-owned. | `runtime/tests/runtime_tests.cpp:test_guest_memory_direct`, `test_valid_two_segment_load`, `test_limits_and_zero_size_segment` |
| ELF loader (`runtime/include/rptp/runtime/elf_loader.hpp`, `runtime/src/elf_loader.cpp`) | Accepts only ELF32 little-endian `ET_EXEC`/`EM_MIPS`, `EV_CURRENT`, `e_ehsize >= 52`, `e_phentsize >= 32`; loads only `PT_LOAD`; checks file bounds, `p_filesz <= p_memsz`, alignment power-of-two and address/offset congruence, `p_vaddr + p_memsz <= 2^32`, ascending order, non-overlap; copies file bytes and zero-fills; requires the entry to be inside a memory range, in its file-backed prefix and in a `PF_X` segment. Errors are stable `LOAD_*`; failure returns an empty report and empty memory. | Overlap rejection is RPTP policy, not a derived requirement. Ignores `p_paddr`, section headers, `e_flags`, dynamic tags and relocations. Does not enforce entry 4-byte alignment (the harness does). Does not distinguish segment permissions in memory. Whole image is read into host memory by the CLI. | `runtime/tests/runtime_tests.cpp:test_header_errors`, `test_segment_errors`, `test_limits_and_zero_size_segment`; `tests/test_runtime_loader.py` (7 CLI tests) |
| Execution harness (`runtime/include/rptp/runtime/execution.hpp`, `runtime/src/execution.cpp`) | Sequential execution of the documented synthetic subset (`ADDIU`, `ADDU`, `SUBU`, `DADDU`, `SLL`, `SLT`, `SLTU`, `SLTI`, `SLTIU`, `DADDIU`, `AND`, `OR`, `XOR`, `NOR`, `ANDI`, `ORI`, `XORI`, `LUI`, `LW`, `SW`, `LD`, `SD`, `BEQ`, `BNE`, `J`, `JAL`, `JR`, `NOP`) plus one delay-slot instruction. `$zero` suppressed; 32-bit PC; step budget; optional trace; sorted memory-write report. Halts successfully only when the next PC leaves every loaded segment. | Test vehicle only. No trap/interrupt, COP0, HI/LO, FPU/MMI, TLB, timing or device model. Instruction fetch checks the segment executable flag, but loads/stores check only `GuestMemory` mapping, so a store into an RX segment is accepted (self-modifying code is not detected). Halting on an unmapped PC is an RPTP convention, not a hardware fact. | `runtime/tests/runtime_tests.cpp:test_execution_*`; `tests/test_runtime_execution.py` (16 CLI tests, oracle differential) |
| CLIs (`runtime/tools/rptp_load.cpp`, `runtime/tools/rptp_run.cpp`) | `rptp-load` and `rptp-run` take an ELF file path. Deterministic versioned JSON (`rptp.runtime.load.v1`, `rptp.runtime.run.v1`); exit `0` success, `2` load/execution error, `1` usage/read failure. No timestamps, host paths or unordered data. | Both read the whole file into host memory. Neither accepts an ISO, a disc handle or a memory stream. | `tests/test_runtime_loader.py`, `tests/test_runtime_execution.py`; CTest `runtime_loader_tests`, `runtime_loader_cli`, `runtime_execution_cli` |
| Build wiring (`CMakeLists.txt`) | `rptp_runtime` static library, `rptp-load`, `rptp-run`, `rptp-runtime-tests`, strict warnings (`/W4 /WX`, `-Wall -Wextra -Wpedantic -Werror`), CTest registration, `rptp-ci` target. | Build/CI/doctor layer remains `Review required` in `CLEAN_ROOM_AUDIT.md`. | CTest |

### 2.1 Recorded limits that matter for HLE

- **U** The largest recorded retail boot executable in the owner-authorized sample is 5,684,592 bytes, and four of eight exceed the inspector's 4 MiB default materialization cap (`ISO_INSPECTOR.md`, retail validation, recorded earlier; not re-measured in this session). The runtime's default image budget is 16 MiB, so the current sample would fit, but the CLI still materializes the whole file. That is a planning observation, not a compatibility claim.
- **T** The harness rejects the registered Gate 0 fixture with `EXEC_MEMORY_FAULT` because its store lies outside the single RX segment; differential tests use two-segment images.
- **R** The loader does not check entry alignment; `EXEC_ENTRY_UNALIGNED` is raised by the harness after a successful load.
- **R** The loader's guest budget (64 MiB default) is an RPTP safety limit. It is not the platform's RAM size, and no approved reference states that size.

## 3. The missing boundary: inspector to product runtime

The inspector and the runtime are two independent programs with different contracts. Today there is no product pipeline, only two test vehicles. Eight things are undefined; each is a design decision, not a coding task.

### 3.1 Handoff, custody and the "no extraction" rule

**Current state (R):** `tools/rptp_inspect.py` exposes `inspect_stream`, `inspect_bytes`, `inspect_path` and `survey_path`. They return metadata dictionaries, including boot ELF metadata and SHA-256, and read the image read-only. There is no API that returns boot-executable bytes, and the runtime accepts only a host ELF path. Gate 2 is read-only under ADR-0004 and no extraction command exists.

**Missing:** a defined custody chain for the boot image: who reads it, in what address space it lives, which hash is binding, and how the loader proves it received the same bytes the inspector validated.

**Design constraint (P):** the runtime must never trust inspector metadata as sufficient. It must re-validate the materialized image itself, then compare `{SHA-256, byte length, entry point, segment table}` with the inspector preflight report; any mismatch is fatal. This keeps one authority (the loader) for materialization and keeps the inspector read-only.

**ADR required.** Two viable shapes, and only the owner can choose: (a) an in-process, read-only stream from the ISO reader into the loader, so no host file is written; or (b) a future extraction step, which ADR-0004 defers to a separate ADR and threat model (§5). Shape (a) still changes Gate boundaries: reading boot bytes at runtime is product behavior, not Gate 2 inspection, so it needs its own disposition even though it writes nothing.

### 3.2 Entry validation and preflight trust

**Current state (R):** the loader validates the ELF entry (mapped, file-backed, executable) but not 4-byte alignment; the harness validates alignment. The inspector reports all entry mappings, warns on ambiguity/overlap/unsuitable entry bytes, and never selects a mapping.

**Missing:** a single entry contract that spans inspector, loader, analyzer and generated code. Minimum content: entry must be 4-byte aligned; must map uniquely into file-backed executable bytes; must be the address the analyzer used as its root; and must have a recorded generated-code target. Any disagreement is fatal before guest execution.

**Validator divergence (R, read from source):**

| Property | ISO inspector | Native loader | Consequence |
|---|---|---|---|
| ELF header size | Exactly 52 | `>= 52` and inside the image | Loader accepts images the inspector rejects; preflight is not a superset. |
| Program-header entry size | Exactly 32 | `>= 32` | Same direction of divergence. |
| `PT_LOAD` overlap | Warning, metadata only | Hard `LOAD_SEGMENT_OVERLAP` | A disc can be `INSPECTED_WITH_WARNINGS` and still be refused by the runtime. |
| Non-`EM_MIPS` / non-`ET_EXEC` | Warning | Hard `LOAD_MACHINE_INVALID` / `LOAD_TYPE_INVALID` | Status mapping must be documented. |
| Entry 4-byte alignment | Not checked | Not checked | A loaded image can fail only at execution (`EXEC_ENTRY_UNALIGNED`). |
| Boot image budget | Streams; 4 MiB default materialization cap | 16 MiB whole-image cap | The two stages can disagree on acceptable size. |

**Design decision (P):** the product pipeline treats inspector warnings that the loader escalates as a preflight failure, not as a warning. The mapping table above becomes part of the handoff contract. This needs no ADR by itself, but it must be written into the runtime contract before a product CLI exists.

### 3.3 Guest memory map

**Current state (R):** guest memory is exactly the `PT_LOAD` ranges from one ELF. There is no stack region, heap, reserved range, device window or alias. Every 32-bit address not mapped is a fault, and two addresses that alias the same physical byte would be two independent regions.

**Missing:** a region model with explicit kinds and permissions, and a policy for aliases. The platform-specific numbers (RAM size, reserved windows, scratchpad, MMIO ranges, vector addresses) are **not defined by any approved reference** and must not be filled in from memory. What can be defined now is RPTP policy:

- Region kinds: `image-read-execute`, `image-read-write`, `stack`, `heap`, `reserved`, `device`.
- Permissions derive from kind; a fetch from a non-executable kind and a store to a read-only kind are explicit faults.
- Guest accesses never leave a region; cross-region access fails rather than splitting.
- Numeric addresses are supplied by the title's load map and a future approved platform reference, not hard-coded.
- Whether the runtime canonicalizes aliases or models them as distinct device windows is an owner decision; until then, alias semantics are undefined and any alias access faults.

**ADR required** before any product memory map is fixed.

### 3.4 Relocation policy

**Current state (R):** only `ET_EXEC` is accepted; no relocation is applied; section headers, dynamic tags and `p_paddr` are ignored.

**Design decision (P):** the first vertical slice keeps static images only. `ET_DYN`, `PT_DYNAMIC`, relocation sections, overlays and runtime-loaded EE modules fail closed with an explicit code. There is no loader that patches guest memory at runtime. This is already the loader's behavior except that unsupported types are rejected as "type invalid"; the error taxonomy should later distinguish "static-only policy" from "malformed image". No ADR is needed to keep the current restriction; an ADR is needed to relax it.

### 3.5 Generated-code loading

**Current state (R):** the product path is ahead-of-time C++ compiled by MSVC. The harness executes guest words directly, which is an oracle, not the product. Nothing loads generated code today.

**Missing:** the contract between generated C++ and the runtime. Proposed shape (P, ADR required):

- Generated code is native code statically linked with `rptp_runtime`; it is never read from or written to guest memory, so guest data cannot become executable.
- Guest PC becomes a dispatch index into a validated table emitted at compile time (or a switch with the same guarantee). A target absent from the table is a fatal trap carrying the target value; there is no fallback interpreter and no JIT.
- Generated code calls a narrow runtime ABI for memory, traps and services. That ABI is versioned and checked at build time.
- Self-modifying code, computed jumps outside the table and unsupported instructions fail closed; the analyzer's unresolved indirect transfers stay non-compilable.

**ADR required** for the ABI and state ownership before the first generated program runs.

### 3.6 Host/guest state separation

**Current state (R):** `ExecResult` carries registers, PC, step count, trace and a sorted memory-write list; `GuestMemory` owns guest bytes. Nothing host-specific appears in the JSON.

**Missing:** an explicit product state object and a rule for what is guest-visible. Proposed contract (P):

- Guest state: GPRs, PC, HI/LO, COP0 and FPU/MMI state when and only when their references are approved; guest memory; device-visible registers.
- Host state: threads, wall clock, files, allocator addresses, logging handles. None of it is readable by guest code and none appears in deterministic output.
- Devices are reached only through the runtime boundary, never by mapping host objects into guest memory.

No ADR is required merely to keep the separation; one is required if guest-visible timing or asynchronous events are introduced.

### 3.7 Deterministic output and telemetry

**Current state (R):** the CLIs emit fixed-order JSON with no timestamps or host paths; the harness records sorted writes; the trace is opt-in.

**Missing:** a product rule. Proposed (P): deterministic artifacts (load report, run report, service-call log, generated-code manifest) contain no timestamps, no absolute paths, no unordered containers and no host timing; any diagnostic that needs wall-clock or duration goes to a separate, non-contractual log. Step budgets and trace caps are mandatory so output size is bounded. This is an ADR-level choice because it constrains future debugging features.

### 3.8 Error taxonomy and the fail-closed gate

**Current state (R):** stable `LOAD_*` and `EXEC_*` codes; exit `0`/`2`/`1`; one error per outcome and no partial success.

**Missing:** a product-level taxonomy that keeps those prefixes and adds:

- `RUNTIME_*` for product state and boundary violations (for example an unsupported region kind or a dispatch miss).
- `HLE_*` for unimplemented or rejected services, with the service identifier in the message.
- A rule that every unsupported instruction, syscall, device access or malformed input produces one code and no fallback. "Not implemented" is a hard failure, never a silent zero return.

The gate is the error path itself: a build that reaches an unimplemented service must terminate with a diagnostic, not continue with plausible state. This does not need an ADR, but it must be in the runtime contract before code.

### 3.9 Boundary decisions and their owners

| # | Decision | Kind | Owner action |
|---|---|---|---|
| B1 | Boot-image custody: read-only in-process stream vs future extraction | ADR | Owner |
| B2 | Memory-map contract (region kinds, permissions, alias policy) | ADR | Owner |
| B3 | Generated-code ABI, dispatch table and state ownership | ADR | Owner |
| B4 | HLE service surface and BIOS policy | ADR | Owner |
| B5 | Determinism and telemetry contract | ADR | Owner |
| B6 | Inspector-to-loader warning escalation mapping | Contract | Agent drafts, owner reviews |
| B7 | Static-only relocation policy | Contract | Agent drafts, owner reviews |
| B8 | Entry contract across inspector/analyzer/codegen | Contract | Agent drafts, owner reviews |

## 4. Gate 4a staged HLE plan

The plan below is a sequence of **smallest safe increments**. It is conditional: Gate 4a does not start until Gate 3 has an exit and the owner records a Gate 4a disposition and a title choice. Every increment must follow the per-increment procedure in `PROVENANCE_PLAN.md` and must fail closed.

**Stage 0 is a prerequisite, not an increment:** an approved reference set for the platform facts the slice needs. Today that set does not exist (R: `REFERENCES.md`). Without it, stages H1–H6 can define RPTP structure but cannot supply real addresses, service numbers or device semantics.

### 4.1 H0 — Contracts and synthetic fixtures only

- **Goal:** write the runtime/HLE contract (state object, region kinds, trap identifiers, error codes, determinism rule) and build synthetic fixtures before any service exists.
- **Preconditions:** owner accepts B2, B3 and B5 as ADRs or records them as proposed contracts; no retail material.
- **Reference needs:** none beyond ELF/MIPS material already approved for the instruction model.
- **Test oracle:** an independent Python oracle that records the same events the runtime will emit (trap site, code, register snapshot) and byte-identical JSON across two runs.
- **Fail-closed:** every unimplemented trap or service has a code; no default return value.
- **Must not claim:** boot, kernel behavior, memory-map fidelity, compatibility.

### 4.2 H1 — Guest memory layout and permissions

- **Goal:** region kinds, permission enforcement on fetch/load/store, an explicit stack region for generated code, and a loader that reports the layout it created. Addresses come from the image and a future approved reference; no constants.
- **Preconditions:** B2 decision; H0 contract; synthetic two- and three-region images.
- **Reference needs:** an approved source for any platform range that is not simply a `PT_LOAD` range. None exists today, so the stage can only exercise RPTP-defined addresses chosen by the test.
- **Test oracle:** oracle runs the same program against an equivalent region table; tests cover fetch from data, store to RX, cross-region access, stack growth past its bound and unmapped access.
- **Fail-closed:** permission violation and unmapped access are distinct `RUNTIME_*`/`EXEC_*` faults; no silent remap.
- **Must not claim:** that the layout matches any real console; that the synthetic addresses are hardware addresses.

### 4.3 H2 — Trap boundary (synchronous only)

- **Goal:** decode the trap instruction into an explicit trap event `{pc, code, registers}`, dispatch through a registered handler table, and return to the instruction after the trap only when the handler says so. No asynchronous interrupts in the first increment.
- **Preconditions:** H1; an approved reference for the trap encoding and return convention. The current permitted-use lists do not cover `SYSCALL`, `BREAK` or `ERET`, so a reference entry is required first.
- **Reference needs:** generic ISA text for the encoding and the architectural effect; the platform's service numbering is **not** approved and must not be guessed.
- **Test oracle:** the Python oracle records the trap event and the post-return state; a handler that returns a value, a handler that fails, and an unknown code are separate cases.
- **Fail-closed:** unknown trap code or missing handler aborts with `HLE_UNSUPPORTED_TRAP`; a trap inside a delay slot or a handler that re-enters incorrectly is rejected.
- **Must not claim:** exception vectors, COP0 cause/status behavior, interrupt latency or kernel entry semantics.

### 4.4 H3 — BIOS HLE stub policy

- **Goal:** a registry of RPTP-authored host stubs with stable identifiers, names, argument/return contracts and an explicit `UNIMPLEMENTED` default. No BIOS image is read, required or emulated.
- **Preconditions:** H2; B4 decision; an approved source for any service semantics the slice needs. None exists today.
- **Reference needs:** service numbers and semantics require a permitted neutral reference or an owner-approved independent measurement. Without one, only RPTP-defined synthetic service IDs may be used, and they cannot boot retail software.
- **Test oracle:** synthetic guests call known and unknown IDs; the oracle records the call sequence and return values; the stub log is deterministic and bounded.
- **Fail-closed:** unknown ID, wrong argument count/type, unsupported return or a stub that would need a real BIOS aborts with `HLE_UNSUPPORTED_SERVICE`.
- **Must not claim:** BIOS equivalence, kernel fidelity, real service numbering or retail boot.

### 4.5 H4 — CDVD / disc-read boundary

- **Goal:** a read-only sector interface over the validated ISO reader: request by logical block, bounds checked against the declared volume, deterministic caching, no host writes. The inspector already enforces a 2048-byte logical block and a primary-only ISO 9660 envelope (`RPTP-REF-006`).
- **Preconditions:** B1 custody decision; H1; owner decision that runtime disc reads are within the authorized scope (Gate 2 is read-only inspection, not a product disc service).
- **Reference needs:** the ISO 9660 structures are approved; any platform command protocol is not. The first increment can expose only a generic block-read interface and must not pretend to implement a command set.
- **Test oracle:** a synthetic in-memory ISO with known sectors; reads return exact bytes; out-of-volume, multi-extent, interleaved and unsupported-layout requests fail with codes from the inspector taxonomy.
- **Fail-closed:** no extraction, no writes, no implicit file reconstruction, no silent zero-fill for unreadable sectors.
- **Must not claim:** that a game's disc access works, or that the interface resembles the console's command interface.

### 4.6 H5 — IOP boundary

- **Goal:** a fail-closed stub only. Any IOP or RPC-shaped call returns `HLE_UNSUPPORTED_SUBSYSTEM` with the request identifier. No IOP CPU, no module loading, no shared-memory aliasing.
- **Preconditions:** H1; owner Gate 4a disposition; a future design for RPC. No implementation in the first slice.
- **Reference needs:** none can be satisfied today; IOP behavior is deliberately outside the approved set.
- **Test oracle:** synthetic guest issues a request; runtime records the rejected request deterministically and aborts the run.
- **Fail-closed:** every request is rejected; no retry, no fallback, no partial response.
- **Must not claim:** IOP emulation, RPC support, module loading or boot progress.

### 4.7 H6 — Controller and audio boundaries (interface only)

- **Goal:** define host-side interfaces with deterministic test doubles: a scripted input event source and a silent or recording audio sink. No device protocol, no timing model, no mixing.
- **Preconditions:** H1; Gate 4c scope (input/audio are 4c, not 4a); B5 determinism decision.
- **Reference needs:** none approved for protocols; only the interface shape is defined now.
- **Test oracle:** a scripted event list produces a deterministic guest-visible sequence; the sink records buffers with sequence numbers only.
- **Fail-closed:** an unimplemented device request aborts; an out-of-sequence event is rejected.
- **Must not claim:** controller compatibility, audio correctness, latency or real-time behavior.

### 4.8 Sequence and stop conditions

1. Stage 0 reference/ADR gate, then H0.
2. H1 → H2 → H3, each with its own failing-first test and recorded evidence.
3. H4 or H5 only after the owner decides that disc access or an IOP stub belongs in 4a; otherwise both stay stubs.
4. H6 interface work may be designed in 4a but implemented in 4c.

Stop and return to the owner if a stage needs a platform fact that no approved reference supplies, if a test would need retail material, or if the only way forward is to weaken a fail-closed check.

## 5. Threat model for a future write path or extraction

**This section is deferred design, not authorization.** Gate 2 is read-only under ADR-0004. No extraction API, output directory or write path exists (R: source and ADR-0004). Any implementation requires a separate owner-approved ADR and threat model **under the ADR-0004 re-evaluation rule**, and this note does not satisfy that requirement. The table records what such an ADR must cover.

| Threat | Vector | Required control (design only) | Residual risk |
|---|---|---|---|
| Path traversal | Crafted ISO identifier such as `..` or embedded separators | Canonical destination root; reject `.`/`..`, absolute paths, drive letters, UNC prefixes and separators inside a component; map names to a safe allowlist | Unicode/case-folding ambiguities |
| Link/reparse escape | Pre-existing symlink or junction inside the destination | Do not follow links; open with no-follow semantics; verify the resolved path stays under the root; refuse reparse points | Platform-specific filesystem behavior |
| Overwrite / clobber | Existing file or symlink at the target name | Exclusive create by default; explicit opt-in for overwrite; atomic temp-file + rename inside the destination | User-forced overwrite |
| TOCTOU | Path changes between check and write | Create handles first, validate the handle, write through it; never re-resolve by path | Local attacker with handle access |
| Disk exhaustion | Large or many extents | Per-file and total byte budgets, free-space check, abort and clean partial output | Shared-volume pressure |
| Large/expanding extent chains | Multi-extent or interleaved chains, huge declared sizes | Reject unsupported layouts; bound declared and actual bytes; never trust metadata alone | Future format support |
| Proprietary content leakage | Extracted game assets committed or redistributed | Default no-extraction; explicit user destination; manifest with hashes; artifact guard; documentation that output is user-local | User redistribution |
| Input mutation | Write accidentally targeting the image | Open the image read-only and refuse any handle with write access; verify the image hash before and after | None if enforced |
| Log leakage | Absolute host paths, user names, timestamps | Deterministic logs without host paths; separate non-contractual diagnostics | Operator-added verbosity |
| Partial/ambiguous output | Crash mid-extraction | Atomic per-file commit; on failure remove partial files or mark the run failed; never present a partial tree as complete | Power loss |
| Concurrency | Two runs writing the same destination | Lock or exclusive-create the destination; deterministic conflict error | Stale locks |
| Executing extracted content | Running a game executable or script from the output tree | Never execute extracted content; the runtime consumes validated data only | User action outside RPTP |

Entry criteria for the future ADR: a named use case, a provenance review of the write code, a tested destination policy, a fail-closed cleanup path and owner sign-off. Until then, the correct behavior is to refuse the feature.

## 6. Verification matrix

Legend: **S** = synthetic fixture can test it now; **I** = needs an owner-authorized image; **G** = needs a Gate/owner disposition; **N** = not implemented.

| Capability | S | I | G | Evidence today |
|---|---|---|---|---|
| ELF32/`EM_MIPS` load, segment bounds, zero fill | Yes | No | No | CTest `runtime_loader_tests`, 7 CLI tests (T) |
| Entry mapped/file-backed/executable | Yes | No | No | Loader tests (T) |
| Entry 4-byte alignment | Yes | No | No | Harness `EXEC_ENTRY_UNALIGNED` (T) |
| Guest memory bounds and single-region access | Yes | No | No | `test_guest_memory_direct`, `EXEC_MEMORY_FAULT` tests (T) |
| Deterministic load/run JSON | Yes | No | No | CTest CLI suites (T) |
| Step budget and trace bound | Yes | No | No | `test_step_limit_fails_closed` (T) |
| Instruction-permission enforcement | Design only | No | ADR B2 | Not implemented (N) |
| Trap dispatch (synchronous) | Yes, once H2 exists | No | Reference + Gate 4a | Not implemented (N) |
| HLE unknown-service failure | Yes, once H3 exists | No | ADR B4 | Not implemented (N) |
| CDVD-style block read over validated ISO | Yes, with synthetic ISO | Yes for retail layout | B1 + Gate 4a | Not implemented (N) |
| IOP request rejection | Yes | No | Gate 4a | Not implemented (N) |
| Loader on a retail boot executable | No | Yes | Gate 4a + reference approval | Loader has only run on synthetic images (U) |
| Boot to first guest instruction on retail | No | Yes | Gate 4a disposition | Not implemented (N) |
| Generated-code dispatch and ABI | Synthetic programs | No | ADR B3 + Gate 3 exit | Harness only (N) |
| First correct frame | No | Yes | Gate 4b | Not implemented (N) |
| Input/audio/save behavior | Scripted doubles | Yes | Gate 4c | Not implemented (N) |

Rules for reading this matrix:

- A synthetic pass proves only the tested synthetic behavior. It is not boot or compatibility evidence.
- Any row marked **I** requires an owner-authorized image, metadata/hash records only, and no committed game data.
- Any row marked **G** requires an owner disposition or ADR; an agent may gather evidence but may not record a pass.
- A local run is not CI. CI-green claims require both supported jobs on the exact pushed commit.

## 7. Owner decisions needed (questions only)

1. **Boot-image custody:** for Gate 4a, may the product read boot bytes in-process from the ISO through a read-only stream (no host write), or must the project wait for a separately approved extraction ADR?
2. **Memory map:** will you approve an ADR that defines region kinds and permissions while leaving all platform addresses undefined until an approved reference exists? Which neutral source, if any, may define those addresses?
3. **Generated-code boundary:** do you approve the AOT-only design — native code statically linked, guest PC as a validated dispatch index, no JIT and no guest memory becoming executable?
4. **BIOS policy:** do you confirm that RPTP will never read, require or emulate a real BIOS image, and that HLE stubs are RPTP-authored host functions with an explicit unimplemented default? Which reference, if any, may define service semantics?
5. **Trap/interrupt scope:** is a synchronous trap-only first increment acceptable, with asynchronous interrupts deferred until a separate design?
6. **Disc access scope:** are runtime block reads from the ISO within the read-only Gate 2 scope, or does any product disc service require a new ADR and disposition?
7. **Determinism contract:** which artifacts are contractual (load report, run report, service log, generated-code manifest), and may host timing exist only in a non-contractual diagnostic log?
8. **Error contract:** do you accept stable `RUNTIME_*` and `HLE_*` codes with exit `0`/`2`/`1`, and a hard failure for every unimplemented service?
9. **Warning escalation:** do you accept that inspector warnings which the loader treats as errors become preflight failures for the product pipeline?
10. **Review ownership:** who will perform the independent provenance review of the runtime and HLE layer before any Gate 4 evidence is claimed?

## 8. References and traceability

- `RPTP-REF-003` — ELF32 header/program-header fields, `PT_LOAD` zero fill, ascending order and entry metadata; used by the existing loader and cited by this note only for already-recorded meanings.
- `RPTP-REF-006` — ECMA-119 primary-volume, directory and 2048-byte logical-block envelope; basis for the disc-read boundary.
- `RPTP-REF-001`, `RPTP-REF-002`, `RPTP-REF-014`, `RPTP-REF-015` — the instruction encodings and the synthetic model already implemented by the harness; no new instruction semantics are introduced here.
- `RPTP-REF-017` — CMake target and test wiring behavior.
- Repository contracts: `docs/RUNTIME.md`, `docs/ISO_INSPECTOR.md`, `docs/IR_CFG.md`, `docs/PROVENANCE_PLAN.md`, `docs/CLEAN_ROOM_AUDIT.md`, ADR-0003 and ADR-0004.

**Reference gaps (no approved source exists in this repository):** platform memory map and alias windows; exception/interrupt model; kernel service interface; BIOS service numbering and semantics; CDVD command protocol; IOP CPU/RPC; controller protocol; audio protocol; timing model. These gaps, not coding effort, are what currently block Gate 4a.

**Provenance:** this note is a design record derived from the repository and the approved generic references. It adds no reference row, accesses no sealed material, and makes no clean-room, Gate or compatibility claim. Proposed ADR identifiers in this note (if any are later opened) would start at ADR-0006 and must be created with status Proposed; only the owner may accept them.

## 9. Non-goals of this note

- It does not authorize Gate 4, extraction, a write path, a product runtime or any retail execution.
- It does not define hardware behavior, service numbers, addresses or timing.
- It does not modify `docs/STATE.md`, `docs/HANDOFF.md` or `docs/CLEAN_ROOM_AUDIT.md`; integration owns those.
- It does not replace the independent provenance reviews in `PROVENANCE_PLAN.md`.

## 10. Verification record for this note

Commands run in this session from the increment worktree, with the MSVC developer environment activated through `Launch-VsDevShell.ps1` (T):

```text
cmake --preset windows-msvc
cmake --build build/cmake-msvc --target rptp-runtime-tests rptp-load rptp-run
ctest --test-dir build/cmake-msvc -R "runtime_" --output-on-failure
```

Observed (T): configure found MSVC 19.51.36260.0 and Python 3.13.16; the build linked `rptp-load.exe`, `rptp-run.exe` and `rptp-runtime-tests.exe`; CTest reported 3/3 passed (`runtime_loader_tests` 0.51 s, `runtime_loader_cli` 0.73 s, `runtime_execution_cli` 0.86 s; total 2.10 s).

Additional direct runs (T):

```text
RPTP_LOAD_BINARY=build/cmake-msvc/rptp-load.exe python -m unittest tests.test_runtime_loader
RPTP_RUN_BINARY=build/cmake-msvc/rptp-run.exe python -m unittest tests.test_runtime_execution
build/cmake-msvc/rptp-runtime-tests.exe
```

Observed (T): 7 loader CLI tests OK, 16 execution CLI tests OK, and the C++ binary printed `runtime loader and execution checks passed`. These are local MSVC runs, not hosted CI, and they exercise synthetic images only. No test was modified.
