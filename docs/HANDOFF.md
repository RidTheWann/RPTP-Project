# Handoff — RPTP after the Gate 0 technical disposition

## Current position

- Public repository: RidTheWann/RPTP-Project. On 2026-10-28 the owner authorized isolated increment branches, PRs, CI diagnosis/fixes and merges after local verification/review and both exact-head compiler jobs pass. Follow [AGENTS.md](../AGENTS.md), pin the merge head and monitor actual merge-commit CI; no direct main push, force-push, history rewrite or administrative override.
- PRs #10–#28 merged inspection, `SLL`, census, native loader, documentation evidence, the synthetic execution harness, its extended subset, `DADDU`, `SUBU` and an evidence-derived progress page with cache-busted README images; `SUBU` is PR #22 (`21fdffc`, run `40849490715`), the cache-busting is PR #26 `b2ddedf` plus PR #27 `f8c2c52`, and latest PR #28 is `f967448` (run `40856000777`), with both jobs passing on each merge commit. The original checkout remains preserved. User-profile `/rptp-develop` is manual and not vendored; GitHub CLI authentication/write access is verified. Query current PR/run metadata before claiming hosted CI or merge, and use the append-only [VERIFICATION_LOG.md](VERIFICATION_LOG.md) for observed results.
- PR #7 (reference policy) and PR #8 (older `SUBU` work) are closed; `SUBU` was re-implemented as PR #22 on current `origin/main`, and neither closed branch was reused or modified. Accepted ADR-0003 is unchanged.
- 2026-10-23 Gate 0 disposition: **technical pass for the narrow synthetic differential-spike scope** by explicit owner delegation, recorded in [GATE0_REVIEW.md](GATE0_REVIEW.md). Not a clean-room certification, independent review or Gate 2 disposition.
- Gate 3 is **not passed**. The synthetic instruction catalog includes `SLTI`, `SLTIU`, `DADDIU`, `DADDU`, `SUBU` and `SLL` (`RPTP-REF-014`/`015`/`002`), with separate literal-oracle and native C++ differential suites. CI run [#50](https://github.com/RidTheWann/RPTP-Project/actions/runs/40474315598) passed both jobs for DADDIU; `DADDU` passed PR #19 run `40836707828` and `SUBU` PR #22 run `40849490715`. See [INSTRUCTION_CATALOG.md](INSTRUCTION_CATALOG.md), [IR_CFG.md](IR_CFG.md), [INCREMENT_LEDGER.md](INCREMENT_LEDGER.md) and the append-only [VERIFICATION_LOG.md](VERIFICATION_LOG.md). No product recompiler, function discovery, runtime or game-boot evidence exists.
- Gate 2 is **open, read-only and not passed** under [ADR-0004](DECISIONS/ADR-0004-gate2-read-only-scope.md); extraction is deferred and needs a separate ADR and threat model. Evidence gaps: [GATE2_EVIDENCE.md](GATE2_EVIDENCE.md).
- ISO inspector: single-volume ISO 9660, strict descriptor/record/config validation, root `SYSTEM.CNF`/BOOT validation, PVD/root/boot metadata, SHA-256, ELF PT_LOAD bounds/alignment/order/zero-fill plus entry load-map and overlap reporting, explicit error taxonomy, read and survey byte budgets, metadata-only survey, deterministic malformed-input tests. Details: [ISO_INSPECTOR.md](ISO_INSPECTOR.md); retail sample summary: [COMPATIBILITY.md](COMPATIBILITY.md).
- Boot-code census: `tools/rptp_census.py` counts aligned file-backed PT_LOAD words and current-decoder acceptance for a local ELF or an ISO boot executable read in memory. All eight authorized images were refreshed read-only with the decoder after `SLL` and `DADDU`; these figures predate `SUBU` (`R-029`). Acceptance is 58.3–69.2%, and counts include data/padding. Details and limits: [BOOT_CENSUS.md](BOOT_CENSUS.md). No extraction, execution or compatibility is implied.
- Native runtime foundation: C++20 `rptp_runtime` provides sparse `GuestMemory` and a fail-closed ELF32 little-endian `ET_EXEC`/`EM_MIPS` `PT_LOAD` loader; `rptp-load` emits deterministic `rptp.runtime.load.v1` JSON and exits `0`/`2`/`1`. CTest `runtime_loader_tests` and `runtime_loader_cli` cover direct C++ checks and an independent Python-built image differential. Contract: [RUNTIME.md](RUNTIME.md).
- Synthetic execution harness: `rptp_runtime::execute_loaded` runs the documented synthetic subset (Gate 0 instructions plus SLL, SLT, SLTU, SLTI, SLTIU, DADDIU, DADDU, SUBU, AND, OR, XOR, NOR, ANDI, ORI, XORI, LUI) with one delay slot over a loaded image; `rptp-run` emits deterministic `rptp.runtime.run.v1` JSON, `EXEC_*` errors, a step budget and an optional trace. Direct C++ checks plus an independent Python oracle differential in `tests/test_runtime_execution.py` cover arithmetic, memory, logic, shifts, comparisons, branches, calls, delay slots, failures and determinism. It is a test vehicle, not a product runtime; the Gate 0 fixture halts with `EXEC_MEMORY_FAULT` because its store falls outside the single RX segment. No kernel, syscall, ISO ingestion, boot or compatibility behavior.
- Provenance: Gate 0 spike and ISO inspector are `Provisional independent`; the build/CI/doctor layer is `Review required`. Nothing is clean-room certified. Historical PS2Recomp / PS2 Web Recomp exposure remains documented and is not erased by the license decision. Policy: ADR-0003; component status: [CLEAN_ROOM_AUDIT.md](CLEAN_ROOM_AUDIT.md); procedure: [PROVENANCE_PLAN.md](PROVENANCE_PLAN.md).
- Toolchain baseline: CMake presets, `rptp doctor`, CTest targets and Windows/MSVC + Linux/GCC CI are present. A plain shell has no MSVC `cl.exe`; run MSVC checks through `VsDevCmd.bat -arch=x64 -host_arch=x64` or the wrapper. Contracts: [BUILD_PROVENANCE.md](BUILD_PROVENANCE.md) and `tests/test_build_contract.py`.
- Owner decisions still open: independent provenance reviews of the Gate 0 spike, the ISO inspector and the build/CI/doctor layer, and the Gate 2 disposition.
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

Useful paths: `tools/rptp_doctor.py`, `tools/check_forbidden_artifacts.py`, `tools/rptp_gate0_spike.py`, `tools/rptp_ir.py`, `tools/rptp_lower.py`, `tools/rptp_inspect.py`, `tools/rptp_census.py`, `tools/rptp_progress.py`, `scripts/run-msvc.ps1`, `docs/VERIFICATION_LOG.md` (append-only), `docs/games/<slug>/STATUS.md` plus its index in `docs/games/README.md`.

If a CI job fails, record the exact runner, command and error in `docs/VERIFICATION_LOG.md` before updating `docs/STATE.md`.

## Next actionable step

1. Extend the synthetic runtime harness only inside the documented model, or apply the per-increment procedure in [PROVENANCE_PLAN.md](PROVENANCE_PLAN.md) to the next smallest Gate 3 behavior using [BOOT_CENSUS.md](BOOT_CENSUS.md) frequency evidence. Either way: behavior statement, permitted `RPTP-REF-*`, a test that fails first, fail-closed diagnostics, then an informative commit body. Do not expand into kernel, IOP, DMA, VU, GS, SPU2, extraction or compatibility claims.
2. Start the independent ISO inspector provenance review and add the native runtime layer to the independent review scope; Gate 2 cannot close without the inspector review.
3. Keep `docs/games/` records current and validate the inspector only against owner-authorized discs; never commit game images.
4. Treat [IR_CFG.md](IR_CFG.md) and [RUNTIME.md](RUNTIME.md) as the analysis and runtime loader/harness contracts; keep every extension fail-closed and never infer function extents, runtime reachability or game compatibility from candidate lists, loaded images or generated artifacts.
