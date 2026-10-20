# ADR-0002 — Native renderer feasibility spike plan

- **Date:** 2026-10-21
- **Status:** Plan only; renderer not selected and no renderer prototype run yet
- **Related:** Gate 0; Gate 4b

## Context

RPTP targets Windows x64 and ultimately has to present graphics produced by PS2 GS semantics. A renderer choice based on modern 3D game performance alone would be insufficient. The spike needs to test native Windows integration, pixel-format handling, texture uploads, alpha/depth operations and readback behavior relevant to the planned runtime.

## Candidates

1. **Direct3D 12:** Windows-native option. Evaluate toolchain integration, shader pipeline setup, resource barriers, texture readback and exact integer/format behavior.
2. **Vulkan:** explicit cross-vendor GPU option. Evaluate Windows setup, driver availability, resource synchronization and format/readback behavior.
3. **wgpu-native:** abstraction option named in the project blueprint. Verify its current license, supported backend configuration, readback path and overhead from its own official project documentation before a prototype is considered.
4. **CPU reference rasterizer:** test oracle only, not the intended product renderer. It supplies deterministic reference pixels for small test cases and is not expected to reach gameplay performance.

No candidate is selected by this ADR.

## Test workload

Implement the same minimal workload for each GPU candidate, using only original test patterns:

- Create a native window and render target.
- Upload a small RGBA texture and render a textured quad/triangle.
- Exercise a minimal alpha blend and depth comparison.
- Read back a small target region and compare specified pixels against the CPU oracle.
- Record shader compile failures, pixel deltas, CPU submission time, GPU time where measured, readback latency, initialization complexity, device loss/resize handling and memory behavior.

The workload is not intended to emulate the entire GS. It is a decision-quality spike for integration and exactness, not a compatibility claim.

## Evaluation criteria

Score each candidate using the same Windows machine and workload:

- Windows 11 x64 build reliability and SDK installation burden.
- Shader/pixel-format flexibility, alpha/depth behavior and texture readback support.
- Pixel correctness versus the CPU reference.
- Render and readback latency, recorded with methodology.
- Debugging and validation support.
- Dependency license, redistribution terms and version-pinning requirements.
- Maintenance and portability consequences.

## Gate

Do not merge a renderer dependency into the project until the spike artifacts, test source, environment and measurements are recorded; the license is verified; and the human owner approves the ADR. Do not use prior PS2 Web Recomp implementation files as the implementation template for this spike.
