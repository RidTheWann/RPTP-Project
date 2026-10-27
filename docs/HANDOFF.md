# Handoff — RPTP after the Gate 0 technical disposition

## Current position

- Public repository: RidTheWann/RPTP-Project; `main` is the only branch for work. Publication and CI state: `git log origin/main..main`, `git log origin/main`, and the GitHub Actions tab.
- 2026-10-23 Gate 0 disposition: **technical pass for the narrow synthetic differential-spike scope** by explicit owner delegation, recorded in [GATE0_REVIEW.md](GATE0_REVIEW.md). Not a clean-room certification, independent review or Gate 2 disposition.
- Gate 3 is **not passed**. The published synthetic instruction catalog now includes `SLTI` and `SLTIU` (`RPTP-REF-014`), with separate literal-oracle and native C++ differential suites. CI runs [#44](https://github.com/RidTheWann/RPTP-Project/actions/runs/40470003967) and [#45](https://github.com/RidTheWann/RPTP-Project/actions/runs/40470558441) passed both Windows x64/MSVC and Linux/GCC. See [INSTRUCTION_CATALOG.md](INSTRUCTION_CATALOG.md), [IR_CFG.md](IR_CFG.md), [INCREMENT_LEDGER.md](INCREMENT_LEDGER.md) and the append-only [VERIFICATION_LOG.md](VERIFICATION_LOG.md). No product recompiler, function discovery, runtime or game-boot evidence exists.
- Gate 2 is **open, read-only and not passed** under [ADR-0004](DECISIONS/ADR-0004-gate2-read-only-scope.md); extraction is deferred and needs a separate ADR and threat model. Evidence gaps: [GATE2_EVIDENCE.md](GATE2_EVIDENCE.md).
- ISO inspector: single-volume ISO 9660, root `SYSTEM.CNF`/BOOT validation, PVD/root/boot metadata, SHA-256, ELF PT_LOAD checks, explicit error taxonomy, 4 MiB read cap, metadata-only survey, deterministic malformed-input tests. Details: [ISO_INSPECTOR.md](ISO_INSPECTOR.md); retail sample summary: [COMPATIBILITY.md](COMPATIBILITY.md).
- Provenance: Gate 0 spike and ISO inspector are `Provisional independent`; the build/CI/doctor layer is `Review required`. Nothing is clean-room certified. Historical PS2Recomp / PS2 Web Recomp exposure remains documented and is not erased by the license decision. Policy: ADR-0003; component status: [CLEAN_ROOM_AUDIT.md](CLEAN_ROOM_AUDIT.md); procedure: [PROVENANCE_PLAN.md](PROVENANCE_PLAN.md).
- Toolchain baseline: CMake presets, `rptp doctor`, CTest targets and Windows/MSVC + Linux/GCC CI are present. A plain shell has no MSVC `cl.exe`; run MSVC checks through `VsDevCmd.bat -arch=x64 -host_arch=x64` or the wrapper. Contracts: [BUILD_PROVENANCE.md](BUILD_PROVENANCE.md) and `tests/test_build_contract.py`.
- Owner decisions still open: independent provenance reviews of the Gate 0 spike, the ISO inspector and the build/CI/doctor layer, and the Gate 2 disposition.
- Current documents are bounded by `tests/test_doc_budget.py` (STATE/HANDOFF: at most 8192 UTF-8 bytes and 900 characters per line). Keep detail in the canonical documents, not here.

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

Useful paths: `tools/rptp_doctor.py`, `tools/check_forbidden_artifacts.py`, `tools/rptp_gate0_spike.py`, `tools/rptp_ir.py`, `tools/rptp_lower.py`, `tools/rptp_inspect.py`, `tools/rptp_progress.py`, `scripts/run-msvc.ps1`, `docs/VERIFICATION_LOG.md` (append-only), `docs/games/<slug>/STATUS.md` plus its index in `docs/games/README.md`.

If a CI job fails, record the exact runner, command and error in `docs/VERIFICATION_LOG.md` before updating `docs/STATE.md`.

## Next actionable step

1. Apply the per-increment procedure in [PROVENANCE_PLAN.md](PROVENANCE_PLAN.md) to the next smallest Gate 3 behavior: behavior statement, permitted `RPTP-REF-*`, a test that fails first, fail-closed diagnostics, then an informative commit body. Do not expand into kernel, IOP, DMA, VU, GS, SPU2, extraction or compatibility claims.
2. Start the independent ISO inspector provenance review; Gate 2 cannot close without it.
3. Keep `docs/games/` records current and validate the inspector only against owner-authorized discs; never commit game images.
4. Treat [IR_CFG.md](IR_CFG.md) as the IR, CFG, reachability and lowering contract; keep every extension fail-closed and never infer function extents, runtime reachability or dead code from candidate lists or generated artifacts.
