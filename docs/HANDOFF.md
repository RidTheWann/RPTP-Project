# Handoff — RPTP after the branch-likely and ISA-evidence increments

## Current position

- Public repository: RidTheWann/RPTP-Project. On 2026-10-28 the owner authorized isolated increment branches, PRs, CI diagnosis/fixes and merges after local verification/review and both exact-head compiler jobs pass. Follow [AGENTS.md](../AGENTS.md), pin the merge head and monitor actual merge-commit CI; no direct main push, force-push, history rewrite or administrative override.
- PRs #10–#39 merged inspection, `SLL`, census, native loader, harness, `DADDU`, `SUBU`, tooling, ISO hardening, `LD`/`SD`, the `tools/rptp` analysis pipeline, branch-likely, the ISA evidence levels and the current-status synchronization. Latest merges: PR #39 `b5858d9` (run `40949915999`), PR #38 `fcae099` (run `40945454160`) and PR #37 `0944c84` (run `40946144443`); all green on Windows x64/MSVC and Linux/GCC. The original checkout remains preserved. User-profile `/rptp-develop` is manual and not vendored; GitHub CLI write access is verified. Query current PR/run metadata before claiming hosted CI or merge, and use the append-only [VERIFICATION_LOG.md](VERIFICATION_LOG.md) for observed results.
- PR #7 (reference policy) and PR #8 (older `SUBU` work) are closed; neither closed branch was reused or modified.
- 2026-10-23 Gate 0 disposition: **technical pass for the narrow synthetic differential-spike scope** by explicit owner delegation, recorded in [GATE0_REVIEW.md](GATE0_REVIEW.md). Not a clean-room certification, independent review or Gate 2 disposition.
- Gate 3 is **not passed**. The `tools/rptp` pipeline (PR #35, `93bbc9c`) adds an R5900/MMI decoder, low-level IR, trusted-seed CFG, deterministic C++20 generation, a Python oracle and dual-model differentials. The subset includes aligned `LD`/`SD` (PR #33, `36572b8`) and eight branch-likely forms (PR #38, `fcae099`, `RPTP-REF-015`); [research/isa-evidence.md](research/isa-evidence.md) (PR #37, `0944c84`) records 36 Level B instructions, 216/224 decoder-crosschecked and 189 unverified claims. The C++ harness lacks branch-likely and the oracle's unaligned `LW`/`SW` rejection. No product recompiler, function discovery or game-boot evidence exists.
- Gate 2 is **open, read-only and not passed** under [ADR-0004](DECISIONS/ADR-0004-gate2-read-only-scope.md); extraction is deferred and needs a separate ADR and threat model. PR #34 (`49cbbe5`) recorded a separate inspector review pass and hardening fixes in [ISO_INSPECTOR_REVIEW.md](ISO_INSPECTOR_REVIEW.md); PR #36 (`9029fd9`) accepted positive non-block-aligned directory data lengths after an ECMA-119 re-check. The owner's disposition is open; evidence gaps: [GATE2_EVIDENCE.md](GATE2_EVIDENCE.md).
- ISO inspector: single-volume ISO 9660, strict descriptor/record/config validation, root `SYSTEM.CNF`/BOOT validation, PVD/root/boot metadata, SHA-256, ELF PT_LOAD bounds/alignment/order/zero-fill plus entry load-map and overlap reporting, explicit error taxonomy, read and survey byte budgets, metadata-only survey, deterministic malformed-input tests. Details: [ISO_INSPECTOR.md](ISO_INSPECTOR.md); retail sample summary: [COMPATIBILITY.md](COMPATIBILITY.md).
- Boot-code census: `tools/rptp_census.py` counts aligned file-backed PT_LOAD words and current-decoder acceptance for a local ELF or an ISO boot executable read in memory. Seven of the eight image rows remain pre-`SUBU`; the one locally available image, Downhill Domination (USA), measured 260,641/413,500 accepted words (63.03%) post-`SUBU`, which still predates branch-likely. Counts include data/padding. Details and limits: [BOOT_CENSUS.md](BOOT_CENSUS.md). No extraction, execution or compatibility is implied.
- Native runtime foundation: C++20 `rptp_runtime` provides sparse `GuestMemory`, a fail-closed ELF32 little-endian `ET_EXEC`/`EM_MIPS` `PT_LOAD` loader (`rptp-load`, `rptp.runtime.load.v1`, stable `LOAD_*` errors) and a synthetic execution harness (`rptp-run`, `rptp.runtime.run.v1`) for the documented subset plus one delay slot, with `EXEC_*` errors and a step budget. `LD`/`SD` reached the host IR and harness in PR #33. It is a test vehicle: no kernel, syscall, ISO ingestion, boot or compatibility. Contract: [RUNTIME.md](RUNTIME.md).
- Provenance: Gate 0 spike and ISO inspector are `Provisional independent`; the build/CI/doctor layer is `Review required`; the branch-likely and `tools/rptp` increments are `Recorded` expansion work. Nothing is certified clean-room. Policy: ADR-0003; component status: [CLEAN_ROOM_AUDIT.md](CLEAN_ROOM_AUDIT.md); procedure: [PROVENANCE_PLAN.md](PROVENANCE_PLAN.md).
- Toolchain baseline: CMake presets, `rptp doctor`, CTest targets and Windows/MSVC + Linux/GCC CI are present. A plain shell has no MSVC `cl.exe`; run MSVC checks through `VsDevCmd.bat -arch=x64 -host_arch=x64` or the wrapper. Contracts: [BUILD_PROVENANCE.md](BUILD_PROVENANCE.md) and `tests/test_build_contract.py`.
- Owner decisions still open: independent provenance reviews of the Gate 0 spike, the ISO inspector and the build/CI/doctor layer; the owner's decision on the recorded ISO review record; the Gate 2 disposition.
- Current documents are bounded by `tests/test_doc_budget.py` (STATE/HANDOFF: at most 8192 UTF-8 bytes and 900 characters per line) and kept current by `tests/test_doc_freshness.py` plus [docs/README.md](README.md): no document may keep a superseded date, pointer, count or status. Keep detail in the canonical documents, not here.

## Expected local commands

From Visual Studio Developer PowerShell (x64) or the x64 Native Tools prompt, in the repository root:

    python tools/rptp_doctor.py
    python tools/check_forbidden_artifacts.py --root .
    cmake --preset windows-msvc
    cmake --build --preset windows-msvc
    python -m compileall -q tools tests
    python -m unittest discover -s tests -v
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-msvc.ps1

Focused runs: `python -m unittest discover -s tests -p test_doc_budget.py -v`, and `python -m unittest tests.test_ir_cfg -v` for the IR/CFG suite. Host preset: `cmake --preset host` then `cmake --build --preset host`.

Useful paths: `tools/rptp_doctor.py`, `tools/check_forbidden_artifacts.py`, `tools/rptp_gate0_spike.py`, `tools/rptp_ir.py`, `tools/rptp_lower.py`, `tools/rptp_inspect.py`, `tools/rptp_census.py`, `tools/rptp_progress.py`, `tools/rptp/` (decoder/IR/CFG/oracle/codegen), `scripts/run-msvc.ps1`, `docs/VERIFICATION_LOG.md` (append-only), `docs/games/<slug>/STATUS.md` plus its index in `docs/games/README.md`.

If a CI job fails, record the exact runner, command and error in `docs/VERIFICATION_LOG.md` before updating `docs/STATE.md`.

## Next actionable step

1. Consolidate the synthetic paths inside the documented model: add branch-likely and a single unaligned-`LW`/`SW` policy to the native harness, or record why a path intentionally differs, with cross-path differentials. Then apply the per-increment procedure in [PROVENANCE_PLAN.md](PROVENANCE_PLAN.md) to the next behavior using [BOOT_CENSUS.md](BOOT_CENSUS.md) frequency evidence. Do not expand into kernel, IOP, DMA, VU, GS, SPU2, extraction or compatibility claims.
2. Build the per-instruction semantics matrix from [research/isa-evidence.md](research/isa-evidence.md) so decodable, implemented, tested and evidence-backed are never conflated.
3. Refresh the eight-image census read-only with the current decoder when the images are reachable; use the updated distribution to choose the next instruction family.
4. The owner must decide whether the recorded ISO inspector review satisfies the Gate 2 prerequisite; the Gate 0, runtime and build/CI/doctor independent reviews remain product-release prerequisites. Never claim clean-room certification first.
5. Keep `docs/games/` records current and validate the inspector only against owner-authorized discs; never commit game images.
6. Treat [IR_CFG.md](IR_CFG.md) and [RUNTIME.md](RUNTIME.md) as the analysis and runtime contracts; keep every extension fail-closed and never infer function extents, runtime reachability or game compatibility from candidate lists, loaded images or generated artifacts.
