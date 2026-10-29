# GS backend and VU0/VU1 boundary — design and decision brief

- **Status date:** 2026-10-30
- **Status:** Research and design proposal. Not an ADR, not a Gate disposition, not an implementation plan approved by the owner.
- **Subject:** First native Windows x64 graphics backend and the VU0/VU1 execution boundary for Gate 4b/Gate 5.
- **Decision owner:** Human project owner. This document recommends; it decides nothing.
- **Related:** [ADR-0002](../DECISIONS/ADR-0002-renderer-spike-plan.md), [ADR-0003](../DECISIONS/ADR-0003-sealed-source-clean-room-policy.md), [ROADMAP.md](../ROADMAP.md) Gate 4b/5, [RUNTIME.md](../RUNTIME.md), [IR_CFG.md](../IR_CFG.md), [REFERENCES.md](../REFERENCES.md), [RISKS.md](../RISKS.md) `R-007`, [isa-evidence.md](isa-evidence.md).

## 1. Purpose

Gate 4b asks for "first correct reference frame from an independently implemented native GS path", and Gate 5 expands runtime services after that. Neither gate has started. ADR-0002 is still a plan: it lists candidate renderers, defines a decision-quality spike, and states that no candidate is selected. This document narrows that open decision into an implementation-ready brief without writing renderer, GS or VU code.

It answers four questions:

1. Which graphics API should the first Windows x64 backend target, and on what documented facts is that proposal based?
2. What is the smallest synthetic rendering milestone that produces real evidence, and what exactly would that evidence prove?
3. Where do VU state and VU execution live in the runtime, and how does recompiled EE code reach them without importing unverified hardware semantics?
4. What is the staged path from a synthetic triangle to a first game frame, and what blocks each stage?

## 2. Scope, non-scope and gate position

### 2.1 In scope

- A renderer comparison and a **proposal** for the first backend.
- A minimal synthetic rendering milestone (clear, triangle, then texture/blend/depth) with a concrete evidence plan.
- A software boundary for VU0/VU1: state ownership, service interface, EE interaction, deferred semantics.
- A staged path with explicit dependencies and blockers.
- A risk and owner-decision list.

### 2.2 Out of scope

- Any GS, VU, DMA, VIF, GIF, IOP or SPU2 behavior claim. This document contains no register layouts, packet formats, opcodes, timings or memory sizes for those units.
- Renderer, shader, GS or VU code, build changes, dependencies or fixtures.
- Performance measurement or prediction. No frame time, throughput or memory figure is claimed.
- Gate dispositions, ADR acceptance, reference approval, clean-room certification or compatibility claims.
- Revising or superseding ADR-0002; this brief is input to that future owner decision.
- Game-specific work, title selection or extracted assets.

### 2.3 Gate and decision position (Terverifikasi, repository read)

- Gate 0 is a narrow synthetic technical pass only; Gate 2 is open; Gate 3 is not passed; Gate 4b/5 have not started ([STATE.md](../STATE.md), [ROADMAP.md](../ROADMAP.md)).
- ADR-0002 is `Plan only; renderer not selected and no renderer prototype run yet`.
- Only `RPTP-REF-001`–`017` are approved. Sony EE/VU manual use is postponed, and the R5900 catalog's `"verified": true` flag is not evidence ([REFERENCES.md](../REFERENCES.md), [isa-evidence.md](isa-evidence.md) §1, §7).
- Runtime and recompiler expansion requires the per-increment procedure in [PROVENANCE_PLAN.md](../PROVENANCE_PLAN.md): behavior statement, permitted reference, an independent failing-first test, fail-closed diagnostics, audit update, evidence record and a traceable commit body.

### 2.4 Evidence labels

Labels follow AGENTS.md §4, with one addition for API documentation:

- **Terverifikasi** — executed or read in this session; the command or file is named in §8.
- **Belum diverifikasi** — not established against an approved RPTP reference. This includes API facts quoted from official vendor documentation: the pages were fetched on 2026-10-30 and the quoted wording is recorded in §3.2, but no `RPTP-REF-*` row is approved, so the fact is not an approved reference and is not used as PS2 hardware or performance evidence.
- **Dugaan** — inference from the above, explicitly not a measurement.

**No renderer was built, linked or executed for this document.** No GPU API call was made, and no frame was captured. Section 8 states this again.

## 3. First backend: Direct3D 12 versus Vulkan

### 3.1 Evaluation frame

The comparison uses only documented API facts and the project's fixed constraints: Windows 11 x64, C++20, MSVC, CMake + Ninja, deterministic output, fail loudly, from scratch, GPL-3.0-or-later, no sealed implementation material. It scores the candidates on:

1. platform fit and portability consequences;
2. installation and dependency surface;
3. validation and debugging support;
4. shader toolchain;
5. headless and software-adapter options for automated tests;
6. explicit-state burden for a from-scratch engine;
7. license and version-pinning work before use.

Performance is not compared. ADR-0002's original candidate list also contains `wgpu-native` and a CPU reference rasterizer. The CPU reference rasterizer is treated here as a **test oracle**, not a product backend, consistent with ADR-0002. `wgpu-native` is outside this comparison because it adds a third-party abstraction layer whose license, version and backend configuration would need their own audit; nothing in this document depends on it.

### 3.2 Documented API facts (Belum diverifikasi as RPTP references)

The following statements were read from official vendor or standards-body pages on 2026-10-30. They are recorded as raw research input. They are **not** approved `RPTP-REF-*` rows, they support no PS2 claim, and they must be re-checked if the owner approves reference rows.

| ID | Fact | Source (fetched 2026-10-30) |
|---|---|---|
| API-D1 | "The Direct3D 12 headers and libraries are part of the Windows 10 SDK. There is no separate download or installation required to use Direct3D 12." `D3d12.dll` is in `%WINDIR%\System32`. | Microsoft Learn, *Direct3D 12 programming environment setup* |
| API-D2 | "C++ is the only supported language for Direct3D 12 development". | Same page |
| API-D3 | The debug layer "provides extensive additional parameter and consistency validation (such as validating shader linkage and resource binding, validating parameter consistency, and reporting error descriptions)". A device that supports it requires the **Graphics Tools** optional feature; the layer lives in `D3D12SDKLayers.dll`. | Same page; `ID3D12Debug::EnableDebugLayer` reference |
| API-D4 | WARP is "a high speed, fully conformant software rasterizer"; since Windows 10 version 1709 it supports Direct3D 12 feature levels 12_0 and 12_1. A Direct3D 12 WARP device is created from the adapter returned by `IDXGIFactory4::EnumWarpAdapter`. The optional WARP NuGet binaries are documented as not redistributable, so they must not be vendored. | Microsoft Learn, *Windows Advanced Rasterization Platform (WARP) Guide* |
| API-D5 | "The WARP device for Direct3D 12 is available only on systems with the Graphics Tools optional feature enabled." | Microsoft Learn, *Porting from Direct3D 11 to Direct3D 12* |
| API-D6 | WARP "can help provide a more deterministic or debuggable result in some cases" where the API allows undefined behavior; hardware-versus-WARP images "appear almost identical" but "small differences sometimes occur" within Direct3D tolerances. | Microsoft Learn, *WARP Guide* |
| API-D7 | Direct3D 12 makes CPU/GPU synchronization and resource state the app's responsibility, using fences and resource barriers; pipeline state is a single object attached before a draw. | Microsoft Learn, *Porting from Direct3D 11 to Direct3D 12*; *Using Resource Barriers to Synchronize Resource States* |
| API-D8 | For DirectX 12, "Shader Model 5.1, the D3DCompile API, and FXC are all deprecated. Use Shader Model 6 via DXIL instead." | Microsoft Learn, *D3DCOMPILE Constants* |
| API-V1 | Vulkan is a "cross-platform industry standard" that supports Windows, Linux, Android, macOS, iOS, Nintendo Switch and HarmonyOS. | vulkan.org |
| API-V2 | Vulkan "requires both a Vulkan Loader and a Vulkan Driver"; the loader is "responsible for mapping an application to Vulkan layers and Vulkan installable client drivers (ICD)". On Windows the loader is supplied by the Vulkan SDK. | docs.vulkan.org, *Loader*, *Checking For Vulkan Support* |
| API-V3 | "Since Vulkan doesn't do any error checking, it is very important, when developing, to enable the Validation Layers right away to help catch invalid behavior." Validation checks parameter values against the specification and tracks object creation/destruction. | docs.vulkan.org, *Vulkan Validation Overview*; *Validation layers* tutorial |
| API-V4 | A Vulkan shader module's code "must be in the SPIR-V format". | docs.vulkan.org, *VkShaderModule* reference; *Shaders* chapter |
| API-V5 | No OS-provided Vulkan software implementation is documented on the pages checked; without a driver/ICD, the loader cannot expose an implementation. | docs.vulkan.org, *Checking For Vulkan Support* |

### 3.3 Comparison

| Dimension | Direct3D 12 | Vulkan | Consequence for RPTP |
|---|---|---|---|
| Platform fit | Windows graphics API; the Windows SDK path is the one documented here. | Cross-platform (API-V1). | The fixed target is Windows 11 x64. Vulkan's portability is optional future value, not a current requirement. |
| Build/dependency surface | Headers and import library ship in the Windows SDK already required by the MSVC toolchain; no separate runtime download (API-D1, API-D2). | Needs a loader, a driver/ICD and, for development, the SDK-supplied validation layers (API-V2, API-V3). | D3D12 has the smaller first-step dependency surface (Dugaan, from API-D1 vs API-V2). Any Vulkan SDK use needs a license and version audit before it enters the repo. |
| Validation and debugging | Debug layer with parameter/consistency validation and named-object leak reporting; requires the Graphics Tools optional feature (API-D3). | Validation layers catch invalid API use but are opt-in; the API itself performs no error checking (API-V3). | Both are adequate. D3D12's layer is tied to a Windows optional feature, which matters for CI images (Dugaan). |
| Shader toolchain | Shader Model 6 via DXIL; FXC/D3DCompile deprecated for DX12 (API-D8). | SPIR-V modules (API-V4). | Both require an offline shader compile step and a deterministic, checked-in shader source plus a recorded compiler version. Neither is free. |
| Headless / software adapter | WARP is an OS component and supports D3D12 feature levels 12_0/12_1, but only with Graphics Tools enabled (API-D4, API-D5). | Requires an installed driver/ICD; a Windows machine without a Vulkan driver exposes no implementation (API-V2, API-V5). | D3D12 has a documented OS software path for headless tests; Vulkan has no documented equivalent on the checked pages. Neither is guaranteed on a CI runner today (Belum diverifikasi; needs the spike). |
| Explicit state | App owns barriers, fences, descriptors and PSOs (API-D7). | App owns synchronization and pipeline state; validation layers exist because the API does not check (API-V3). | Comparable conceptual cost. The from-scratch engine must own this state either way; the choice does not remove the work. |
| Portability consequence | Windows-only for this project's purposes. | Broad, including Linux and mobile. | Choosing D3D12 first narrows future platforms unless a second backend is written (Dugaan). Choosing Vulkan first pays a loader/driver dependency now for portability that is not required. |
| From-scratch constraint | A platform API, not an emulator or recompiler. | Same. | Using either API does not violate the from-scratch rule. The GS semantics, packet decoding, state translation and frame verification remain RPTP-authored work. WARP is a software GPU implementation, not a PS2 emulator. |
| Samples and copied code | Vendor samples exist. | Vendor/Khronos samples exist. | Do not vendor or adapt sample code. Author the minimal path from documented contracts and test it; record any copied snippet as third-party material. |

### 3.4 Recommendation (proposal, not a decision)

**Proposal:** implement the first backend against **Direct3D 12**, behind a narrow internal `gfx` interface, with the CPU reference rasterizer as the permanent test oracle and WARP as the first automated adapter. Keep Vulkan as a second backend option if cross-platform support later becomes an owner requirement.

Reasons, stated as reasoning rather than fact:

1. The product target is fixed to Windows 11 x64, so Vulkan's main advantage does not pay for its loader/ICD/validation-layer surface in the first increment (Dugaan from API-V1/V2 and the fixed decisions).
2. D3D12 is already part of the Windows SDK the MSVC build needs, which minimizes new dependency and license-audit work for the first milestone (Dugaan from API-D1).
3. The documented debug layer and WARP give a plausible path to a headless, CI-checkable clear/triangle test without a physical GPU (Dugaan from API-D3/D4/D5; the availability on the actual CI image is Belum diverifikasi).
4. A narrow `gfx` interface keeps a later Vulkan backend possible without committing to an abstraction framework now.

What would overturn the proposal: the owner decides cross-platform support is a near-term requirement; the WARP/Graphics Tools path proves unavailable on the CI image and no other software adapter is acceptable; or D3D12 license/SDK terms fail the dependency audit.

### 3.5 What the comparison does not establish

- It does not select a renderer; ADR-0002 remains open until the owner accepts or replaces it.
- It does not prove that either API is available on a GitHub-hosted Windows runner, that WARP output is stable across runner images, or that a headless device can be created there.
- It does not compare performance, driver quality, vendor bugs or long-term maintenance cost.
- It does not approve any Microsoft, Khronos or LunarG document as an RPTP reference. Proposed rows are in §7.3 and require the owner.

## 4. Minimal synthetic rendering milestone (M0)

### 4.1 Definition

M0 is a headless, deterministic, asset-free rendering test built from compile-time constants. It has three sub-milestones, each independently testable:

| Sub-milestone | Content | Fixed parameters |
|---|---|---|
| M0-A `clear` | Create a device and an offscreen color target; clear it; read back. | 64×64 `RGBA8_UNORM`, one fixed clear color, no swapchain required. |
| M0-B `triangle` | Draw one triangle with a solid color; read back. | Fixed NDC vertices in source, fixed viewport/scissor, no depth, no blend, no texture, culling disabled or fixed. |
| M0-C `state` | Draw two triangles with a procedural 2×2 texture, alpha blend and a depth test; read back color and depth. | Fixed blend factors/equation, fixed depth comparison, fixed texture contents generated in code, nearest sampling. |

M0-C is the smallest workload that exercises the ADR-0002 concerns (texture upload, alpha, depth, readback) without game data. Nothing is loaded from disk; the texture and vertices are literals. No binary fixture is added, so `tests/fixtures/MANIFEST` does not change.

The CLI shape is a proposal for a future increment, not an existing command:

    rptp-gfx-selftest --frame=m0a|m0b|m0c --adapter=warp|hardware --json

Output must be deterministic: no timestamps, no host paths, fixed key order, adapter name and driver version recorded as metadata but excluded from pass/fail unless the owner decides otherwise.

### 4.2 Determinism contract

"Deterministic" here means: **the same binary, adapter, driver and OS produce byte-identical readback for the same frame**, and the test reports every input that could change the result. It does not mean that different GPUs or drivers agree. API-D6 documents that even WARP and hardware can differ within Direct3D tolerances.

The contract therefore has three levels:

1. **Exact** — repeated runs on the same adapter/driver/OS must match bit-for-bit. This is the pass/fail gate for the local and CI run.
2. **Oracle-bounded** — GPU output versus the CPU reference rasterizer must match on coverage (with an explicit edge-pixel rule) and on color within a documented per-channel tolerance.
3. **Cross-adapter informational** — hardware versus WARP is reported as a delta histogram and maximum channel delta; it is not a hard equality gate until the owner sets a policy.

### 4.3 Evidence that would prove M0

A future M0 increment is proven only when all of the following are recorded:

1. **Build and run** — the backend target builds with the existing MSVC preset under `/W4 /WX`, and the self-test runs headless (no window or swapchain) on a machine with the required adapter, capturing the target by readback.
2. **Raw readback hash** — SHA-256 of the raw `RGBA8` buffer, plus the full buffer written only on mismatch. The frame is compared to the CPU-oracle output, not to a committed golden image.
3. **Repeatability** — at least 10 consecutive runs in one process and 3 process restarts produce one hash; any variance is a failure, not a warning.
4. **CPU oracle** — an independently written CPU rasterizer (test-only) produces the same coverage mask and color within the agreed tolerance. The oracle is authored from the same fixed specification, not from the GPU path.
5. **Validation-clean assertion** — the D3D12 debug layer (or the Vulkan validation layers, if Vulkan is chosen) is enabled in debug builds, and the test fails if any error is emitted. A deliberate negative control (for example a missing barrier or an unbound resource) must make the same harness fail, proving the gate is live.
6. **State trace** — a deterministic record of pipeline state (pipeline-state descriptor hash, viewport, scissor, blend state, depth state, draw count, resource transitions) is compared to an expected trace. This catches a frame that is correct by accident.
7. **Adapter honesty** — the JSON records the adapter name and driver version. A run on an unexpected or software adapter is not silently treated as a hardware pass.
8. **Artifact guard** — `tools/check_forbidden_artifacts.py` remains green; no game data, screenshot or generated image is committed.

### 4.4 What M0 does not prove

- No GS semantics: no GS register model, packet decoding, pixel format, swizzle, CLUT, alpha test, dithering, mipmap, texture cache or coordinate convention.
- No VU behavior and no EE code path. M0 is driven by host code, not recompiled guest code.
- No windowing, resize, swapchain, device-loss, multi-frame or presentation behavior.
- No performance claim. M0 is a correctness harness.
- No cross-vendor pixel equality. A hardware-versus-WARP difference is expected to be reported, not hidden.
- No compatibility, boot or game claim.

### 4.5 Cost and dependency notes

- D3D12 adds no vendored library if the Windows SDK is already part of the toolchain (API-D1); the Windows SDK terms still need a recorded dependency note under [LICENSES.md](../LICENSES.md).
- The debug layer and WARP depend on the Graphics Tools optional feature (API-D3, API-D5). The CI image must be checked; if the feature is absent, the test must skip loudly with an explicit reason, never pass silently.
- A Vulkan backend would add the Vulkan SDK/loader/validation-layer surface and its license audit before the first line of backend code (API-V2, API-V3).
- Shader compilation adds a toolchain step (DXIL/DXC or SPIR-V/glslang); the compiler version and shader source hash must be recorded for reproducibility.

## 5. VU0/VU1 execution boundary

### 5.1 Why this section contains no VU semantics

No approved reference describes VU behavior. The Sony VU User's Manual is not approved and its use is postponed; only `RPTP-REF-001`–`017` are permitted; the R5900 catalog's COP2 entries are Level C and the decoder exposes opcode `0x12` as an opaque, unsupported `cop2` placeholder ([REFERENCES.md](../REFERENCES.md), [isa-evidence.md](isa-evidence.md) §5, `tools/rptp/isa.py`). The oracle explicitly excludes COP2/VU/GS behavior (`tools/rptp/oracle.py`).

Therefore this section defines **software seams only**: who owns state, which calls cross the boundary, and what fails closed. It deliberately contains no vector register layout, instruction behavior, memory size, packet format or timing rule. Any such detail must arrive later with an approved reference and an independent test.

The VU0/VU1 topology used below (VU0 coupled to EE execution; VU1 fed from the DMA/VIF side and producing GS-bound data) is the **project's planning assumption**, marked **Belum diverifikasi**, not a hardware description. The design keeps both units behind one interface so that a correction to this assumption changes wiring, not generated EE code.

### 5.2 State ownership

| State | Owner | Access rule |
|---|---|---|
| EE general registers and guest memory | Existing runtime (`GuestMemory`, recompiled code) | Unchanged. No VU state is placed in EE-visible memory by this design. |
| VU instruction store and data store | `VuUnit` service | Opaque. No host pointer, reference or array index is exposed to generated code. |
| VU vector/flag/status state | `VuUnit` service | Opaque; readable only through a status call that returns a copy. |
| GS register/state model | Future CPU-side `GsState` | Not owned by the VU or the backend; written by the future packet layer. |
| GPU resources, PSOs, barriers, readback buffers | `gfx` backend | Private to the backend; never visible to EE or VU code. |
| Frame target | `gfx` backend | Readback only in tests. |

Two independent `VuUnit` instances (`vu0`, `vu1`) are proposed. They share an interface, not state. There is no global vector register file. Each unit's state must be serializable so a failing test can be replayed from a recorded state hash.

### 5.3 Proposed service interface (names only, no code)

| Call | Purpose | Failure mode |
|---|---|---|
| `reset()` | Return the unit to its defined initial state. | Internal error only. |
| `load_instruction_store(bytes, origin)` | Copy a bounded microprogram image from guest memory. | `VU_IMAGE_INVALID`, `VU_LIMIT_EXCEEDED`. |
| `read_data_word(address)` / `write_data_word(address, value)` | Bounded data-store access for tests and future DMA plumbing. | `VU_ADDRESS_INVALID`, `VU_UNSUPPORTED`. |
| `run(step_budget)` | Execute until halt, a defined event, or the budget. | `VU_STEP_LIMIT`, `VU_UNSUPPORTED`. |
| `status()` | Return a copy of PC, run state and error state. | None. |
| `take_events()` | Drain a bounded event queue (for example a GS-bound data chunk). | `VU_EVENT_OVERFLOW`. |

All calls are synchronous on the runtime thread, deterministic, and bounded. No host threads, wall-clock time or asynchronous callbacks are allowed in the boundary, because the project requires reproducible output.

The first implementation of every call except `reset`/`status` is a **fail-closed stub** returning `VU_UNSUPPORTED`. That is an honest implementation of "not implemented", not a semantic guess.

### 5.4 How recompiled EE code interacts with the VU

1. **No inline vector state.** The recompiler must never emit a vector register array or inline COP2 operation into generated EE code. EE-side vector access becomes a call to the `VuUnit` service with an explicit status check.
2. **Fail closed now.** Any EE instruction whose semantics touch COP2 is currently unsupported. The decoder already treats opcode `0x12` as an opaque `cop2` placeholder; the oracle and lowerer must continue to reject it explicitly (`LOWER_UNSUPPORTED_OP` / `EXEC_UNSUPPORTED_INSTRUCTION` style diagnostics) rather than skipping it. When an approved reference exists, the lowering emits a service call and a deterministic error path.
3. **Microprogram upload is a service call.** A future EE path copies a bounded image from guest memory into `VuUnit`; the unit validates size and origin against RPTP limits, not guessed hardware limits.
4. **Kicks are explicit records.** Running a microprogram is a service call with a step budget. The unit returns events; it never calls the renderer directly.
5. **Test doubles are interface-level only.** A `MockVuUnit` implementing the same interface with scripted responses can test the EE-side plumbing (call emission, error propagation, trace ordering) without any VU semantics. It is the only VU-adjacent work that could be proposed before a reference is approved, and it still needs owner authorization because it expands the runtime surface.
6. **Wrong topology is cheap to fix.** If the planning assumption about VU0/VU1 wiring is corrected, only the service wiring and test double change; generated EE code still calls the same interface.

### 5.5 VU1 to GS boundary

The VU unit must not know about the renderer. The proposed path is:

    VuUnit(vu1) -> bounded event stream -> future GS packet decoder -> future GsState -> gfx backend

The event stream is an RPTP-defined byte/word chunk with a length bound. Its contents are **not** a GS packet format claim; the format is deferred until an approved GS reference exists. This separation means:

- the backend can be tested with hand-built `GsState` records before any VU exists;
- the VU can be tested against a mock sink before any GS decoder exists;
- a wrong packet assumption cannot leak into the renderer interface.

### 5.6 Deferred parts and their prerequisites

| Deferred part | Prerequisite |
|---|---|
| VU instruction decode and execution | Approved VU reference; Gate 4b/5 disposition; failing-first synthetic tests |
| Vector register file, flags, MAC pipeline, clipping/status semantics | Same |
| Instruction/data store sizes, mapping, alignment and bank rules | Same, plus an explicit RPTP limit policy |
| Microprogram upload/kick protocol and entry rules | Same |
| EE COP2 transfer and interlock semantics | Same; the eight catalog COP2 entries are Level C today |
| VU1 control, VIF/DMA handshake and kick timing | Approved VU and DMA/VIF references; Gate 4a/4b |
| VU1-to-GIF packet production | Approved GS/GIF reference and a synthetic packet corpus |
| Timing, stalls, dual-issue, branch and exception behavior | Approved reference plus a measurement method |
| Performance | Only after correctness evidence; no target before that |

### 5.7 Why no VU semantics before an approved reference and Gate disposition

1. **No reference.** The approved list contains no VU or GS document. Implementing from memory would violate the reference rule in AGENTS.md §2 and the per-increment procedure.
2. **Unverifiable tests.** A test written from the same guessed model as the implementation would only compare RPTP with RPTP; [isa-evidence.md](isa-evidence.md) §2 explicitly says that is not evidence.
3. **Fail-closed rule.** Unsupported features must fail loudly. A half-guessed VU is worse than an explicit `VU_UNSUPPORTED`, because it produces plausible but unverifiable results.
4. **Provenance.** Any semantics derived from sealed emulator/recompiler material would have to be quarantined under ADR-0003. The owner must approve the neutral reference before work starts.
5. **Gate authority.** Gate 4b/5 have not started, and only the owner records Gate dispositions. An agent cannot open that scope by writing code.

## 6. Staged path from M0 to a first game frame

### 6.1 Stages

| Stage | Deliverable | Depends on | Evidence | Status |
|---|---|---|---|---|
| S0 | This design brief | — | Document review | Current increment |
| S1 | `gfx` interface + D3D12 device/adapter selection + M0-A clear + readback | Owner accepts renderer proposal; SDK/license note; CI adapter check | Exact readback hash, repeat runs, validation-clean, state trace | Blocked on owner decision |
| S2 | M0-B triangle + M0-C texture/blend/depth + CPU oracle | S1 | Oracle comparison, tolerance report, negative validation control | Blocked on S1 |
| S3 | CPU-side `GsState` model and one packet-family decoder | Approved GS reference; synthetic packet corpus | Synthetic packet tests, fail-closed unknown packets | Blocked on reference approval |
| S4 | `GsState` → backend translation for one primitive path | S2, S3 | Frame comparison against CPU GS model | Blocked on S2/S3 |
| S5 | `VuUnit` interface + fail-closed stubs + mock sink | Owner authorization for the runtime surface; no hardware reference needed for stubs | Interface tests, explicit `VU_UNSUPPORTED` diagnostics | Not authorized; no semantics |
| S6 | VU0 execution and EE COP2 service path | Approved VU reference; Gate disposition; S5 | Synthetic microprogram tests, fail-closed limits | Blocked |
| S7 | VU1 execution + event stream + VU1→GS plumbing | S6; approved VU/VIF/DMA references | Synthetic microprogram to synthetic sink | Blocked |
| S8 | DMA/VIF/GIF transport and EE↔VU1 kick path | Approved DMA/VIF references; Gate 4a; S7 | Synthetic DMA transfer traces | Blocked |
| S9 | Kernel/syscall/CDVD boot path for one title | Gate 4a evidence; title selection | Boot log, deterministic service trace | Blocked |
| S10 | First game frame | S1–S9; reference-frame method agreed | Owner-accepted comparison record | Blocked |

The ordering is not a schedule. It exists to show which stage each missing reference unlocks and to prevent renderer work from silently absorbing kernel, DMA or VU scope.

### 6.2 Explicit blockers

- **B1 — GS/VU reference vacuum.** No approved reference describes GS state, packet formats, pixel formats or VU execution. This blocks S3, S4, S6–S8.
- **B2 — Gate disposition.** Gate 4b/5 are unstarted; the owner must record the disposition that authorizes GS/VU scope.
- **B3 — Kernel/DMA/IOP evidence.** No approved reference or test covers the boot services path. This blocks S8–S9.
- **B4 — Title selection.** Gate 4 explicitly says the first title is chosen after measured metadata, not popularity. No title is selected for graphics work.
- **B5 — CI adapter unknown.** WARP/D3D12 requires the Graphics Tools optional feature (API-D5); its presence on the CI image is Belum diverifikasi. A test that silently passes without an adapter would violate the fail-closed rule.
- **B6 — Reference-frame truth undefined.** See §6.3.
- **B7 — Dependency/license audit.** Any SDK or runtime beyond the existing MSVC toolchain needs a [LICENSES.md](../LICENSES.md) entry before use.

### 6.3 What "first game frame" means and why it is hard

Gate 4b asks for a "first correct reference frame". Correctness needs an external truth. The project cannot use an emulator as an oracle (ADR-0003 seals them), and a game frame is game-derived material that must not be committed.

The only defensible options are:

1. **Owner visual acceptance** of a locally captured frame from a user-owned title, with the image kept local and only metadata (hash, date, method, title) recorded in the repository.
2. **A CPU GS reference model** written inside RPTP from approved references, compared to the GPU backend; the model is an independent implementation but still not proof of hardware equivalence.
3. **A hardware capture** supplied by the owner, kept local, with the same metadata-only recording.

Whichever is chosen, the repository must never contain the frame or the capture. The owner must also decide what tolerance and what human sign-off constitute "correct". This is decision OD-7 in §7.1.

## 7. Risks and owner decisions

### 7.1 Decisions needed from the owner

| ID | Decision | Options | Recommendation |
|---|---|---|---|
| OD-1 | First renderer | Direct3D 12 / Vulkan / wgpu-native / CPU-only first | Direct3D 12 first, behind a narrow `gfx` interface (§3.4). Proposal only. |
| OD-2 | API reference rows | Approve new rows for Microsoft D3D12/WARP and Khronos Vulkan docs; or keep API facts unapproved | Approve narrow API-only rows (§7.3); they support backend facts, never PS2 behavior. |
| OD-3 | GS/VU hardware reference | Approve limited Sony manual use; commission independent experiments; keep blocked | Keep VU/GS semantics blocked until a neutral reference with recorded limits exists. |
| OD-4 | Determinism policy | Exact hash only / exact + oracle tolerance / cross-adapter tolerance | Exact on one adapter; oracle-bounded; cross-adapter informational until measured. |
| OD-5 | CI strategy when no adapter exists | Fail / skip with explicit reason / soft gate | Skip with explicit reason in the test output and a separate required local run; never a silent pass. |
| OD-6 | M0 scope | Clear only / triangle / triangle+texture+blend+depth | M0-A, M0-B, M0-C as separate increments (§4.1). |
| OD-7 | Reference frame for Gate 4b | Owner visual / CPU GS model / hardware capture | Owner visual plus CPU GS model; metadata only in the repo (§6.3). |
| OD-8 | Backend abstraction depth | Direct calls / narrow internal interface / plugin framework | Narrow internal interface; no plugin framework before a second backend exists. |
| OD-9 | WARP/Vulkan SDK dependency terms | Record in LICENSES.md / reject | Record before first use; WARP's NuGet binaries are documented as non-redistributable, so do not vendor them. |

### 7.2 Risks

| ID | Risk | Likelihood / impact | Mitigation | Trigger to revisit |
|---|---|---|---|---|
| G-01 | GPU output differs across adapters or driver versions, so a golden pixel hash is brittle. | High / High | CPU oracle + tolerance, exact hash only within one adapter/driver/OS; report deltas. | First cross-adapter run. |
| G-02 | The CI image lacks the Graphics Tools feature or a GPU, so the backend test cannot run. | Medium / High | Adapter detection, explicit skip with reason, separate required local run; spike before promising CI. | First S1 CI attempt. |
| G-03 | API documentation is used without approved reference rows, creating an unverifiable behavior claim. | Medium / Medium | API facts marked Belum diverifikasi; owner approves rows before code cites them. | OD-2 decision. |
| G-04 | GS/VU work starts from memory or from sealed material. | Medium / Critical | No semantics before approved reference; fail-closed stubs; quarantine rule. | Any VU/GS code proposal. |
| G-05 | The backend abstraction becomes a framework and absorbs schedule. | Medium / Medium | Narrow interface, one backend, no plugin system. | Second backend proposal. |
| G-06 | A "correct" frame is accepted without a defensible oracle. | Medium / High | OD-7 method, metadata-only recording, explicit non-equivalence statement. | Gate 4b evidence review. |
| G-07 | D3D12 locks the project to Windows and a later port redoes the backend. | Medium / Medium | Accept for the fixed target; keep `gfx` interface; Vulkan remains an option. | Cross-platform requirement. |
| G-08 | Performance work begins before correctness. | Medium / High | No performance claims or targets until M0/S4 pass; profile only with recorded methodology. | First performance question. |

Existing [RISKS.md](../RISKS.md) entries remain in force: `R-007` (VU/GS schedule), `R-001` (capacity), `R-003` (shared-bug oracle), `R-005` (MSVC/host differences), `R-009` (dependency license). This document does not change their status.

### 7.3 Proposed reference rows (owner approval required)

These rows are **not** in [REFERENCES.md](../REFERENCES.md) and are not approved. They are written here so the owner can accept, amend or reject them in one step.

| Proposed ref | Public source | Proposed permitted use | Proposed limits |
|---|---|---|---|
| RPTP-REF-018 | Microsoft Learn, Direct3D 12 documentation: programming environment setup, debug layer, WARP guide, porting/synchronization and resource-barrier pages, D3DCOMPILE constants | Backend API facts: SDK contents, debug-layer behavior and prerequisites, WARP availability and conformance statements, explicit synchronization/state model, DXIL shader model | Windows API documentation only; no PS2 hardware, GS, VU or performance claim; no vendor sample code copied |
| RPTP-REF-019 | Khronos, vulkan.org and docs.vulkan.org: loader, checking for support, validation overview, validation-layers tutorial, SPIR-V and shader-module references | Backend API facts: platform scope, loader/ICD requirement, validation-layer behavior, SPIR-V shader format | API documentation only; no PS2 hardware, GS, VU or performance claim; Vulkan SDK license audit still required before use |

The exact access date, quoted passages and limits must be re-recorded in [REFERENCES.md](../REFERENCES.md) by the owner or by an increment the owner authorizes. Until then, every API statement in this document stays Belum diverifikasi.

## 8. Verification performed

**Terverifikasi (this session):**

- Read: `AGENTS.md`, `docs/STATE.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`, `docs/CLEAN_ROOM_AUDIT.md`, `docs/RISKS.md`, `docs/DECISIONS/ADR-0001`, `ADR-0002`, `ADR-0003`, `docs/RUNTIME.md`, `docs/IR_CFG.md`, `docs/REFERENCES.md`, `docs/LICENSES.md`, `docs/PROVENANCE_PLAN.md`, `docs/README.md`, `docs/research/isa-evidence.md`.
- Read-only repository checks: `git status`, `git log --oneline -10`, `git rev-parse origin/main`, `git fetch origin main`; the work branch is based on the fetched `origin/main` tip `0944c84`.
- Confirmed the decoder's opaque `cop2` placeholder in `tools/rptp/isa.py` (opcode `0x12`, `supported=False`) and the oracle's exclusion of COP2/VU/GS in `tools/rptp/oracle.py`.
- Documentation tests (run for this increment): `python -m unittest tests.test_doc_freshness tests.test_doc_budget tests.test_license_headers -v` — all pass after this document was added to the `docs/README.md` map.
- Full Python suite: `python -m unittest discover -s tests` — pass; no test was added, changed or skipped by this increment.
- Artifact guard: `python tools/check_forbidden_artifacts.py --root .` — pass.

**Belum diverifikasi:**

- Every API fact in §3.2 as an approved RPTP reference.
- Availability of the D3D12 debug layer and WARP on the GitHub-hosted Windows runner.
- Whether a Vulkan implementation is present on that runner.
- Any behavior of the D3D12 or Vulkan API on this machine; no device was created.

**Not performed at all:**

- No renderer, shader, window, device or readback code was written or executed.
- No GS, VU, DMA, VIF, GIF or SPU2 code or test was written.
- No performance measurement was taken.
- No game image, BIOS, executable or asset was read, extracted or committed.

## 9. Non-claims

- This document does not select a renderer, approve a reference, open Gate 4b/5 or change ADR-0002.
- It does not claim that a synthetic triangle demonstrates GS correctness, that a backend is feasible on CI, or that any title can boot.
- It does not describe VU or GS hardware. The interface names and ownership rules are RPTP software design, not hardware behavior.
- It does not certify any component as clean-room. ADR-0003 remains in force; a future backend must follow the per-increment provenance procedure before its first behavior claim.
