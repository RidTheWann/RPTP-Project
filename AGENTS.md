# AGENTS.md — RPTP agent rules

Applies to every coding agent working in this repository. Read it fully at the start of each session.

**Language.** Talk to the owner in Indonesian. Write code, comments, commit messages, docs, and all CLI/log/error text in English.

**Priority when rules conflict:** (1) legal, license and clean-room rules (sections 2–3) → (2) honesty and evidence (section 4) → (3) fixed decisions (section 1) → (4) the owner's session instructions → (5) style. A session instruction may not loosen items 1–3. If one tries, explain the conflict and stop.

## 0. Session start (mandatory)

1. Read `docs/STATE.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`, `docs/CLEAN_ROOM_AUDIT.md`, `docs/DECISIONS/ADR-0001-*.md`, `docs/DECISIONS/ADR-0003-*.md`. Do not read docs/VERIFICATION_LOG.md here: it is an append-only evidence log. Open it only when a task needs older evidence.
2. Run `git status` and `git log --oneline -10`.
3. Summarize the project position in at most 10 lines.
4. Pick ONE task. Write a short plan (goal, files, tests, done criteria) before changing code.

## 1. Mission and fixed decisions

- RPTP turns a user-owned PS2 ISO into a native Windows x64 build: ISO → inspect → ELF → analyze → recompile Emotion Engine (R5900) code to C++ → MSVC build → native runtime. From scratch; no browser/WASM; never "run the game through an emulator".
- The interpreter in `tools/` is a **test oracle only**, not the product path.
- Target stack: Windows 11 x64, C++20, MSVC, CMake + Ninja. Current tooling is Python (`tools/`). Whether inspector/analyzer stages stay Python or move to C++ is an **open decision**: do not migrate without an owner-approved ADR.
- License: GPL-3.0-or-later. Every project source/build/workflow file (`.py`, `.ps1`, `CMakeLists.txt`, `.yml`) carries `SPDX-License-Identifier: GPL-3.0-or-later` (enforced by `tests/test_license_headers.py`). Never change `LICENSE`.
- Output is deterministic: same input, same bytes. No timestamps or absolute paths in generated output.
- Unsupported instructions, syscalls or features must **fail loudly and explicitly**. Never skip them silently or produce a build that looks valid.
- ISOs are opened read-only and never modified. Build outputs stay local.

## 2. Clean-room rules (ADR-0003: sealed-source policy)

- **Sealed:** PS2Recomp, PS2 Web Recomp, PCSX2, Play!, and any other emulator or recompiler implementation. Do NOT open, clone, browse, search for, fetch, or summarize their source, build files, scripts, tests, issues, PRs, release notes, or implementation docs. This includes web search, MCP tools, and "just checking".
- **Permitted references:** neutral public specs (MIPS ISA, ELF, ECMA-119/ISO 9660), official docs of tools (CMake, MSVC, GitHub Actions), and independent experiments and tests.
- Every non-trivial behavior claim cites a permitted reference or an independent test in `docs/REFERENCES.md`. An unsupported claim is not a supported feature. Do not write hardware facts from memory; cite or mark them unverified.
- Components marked `Review required` in `docs/CLEAN_ROOM_AUDIT.md` (CMake/CI/doctor layer) must never be called clean-room certified. Do not "fix" provenance by consulting sealed material. Re-derivation happens only when the owner approves it.
- **Runtime and recompiler expansion is `Blocked`** until the owner records the formal Gate 0 disposition and a provenance plan. Do not add R5900 semantics, kernel, IOP, DMA, VU, GS, SPU2 or similar work before that.
- If you encounter sealed material by accident: stop, do not use it, disclose it in your report, propose an entry for the exposure record in `docs/REFERENCES.md`, and wait for the owner.

## 3. Repository hygiene

- Never commit ISOs, BIOS, game executables, extracted assets, sealed-project artifacts, or personal absolute paths.
- Binary fixtures must be synthetic and registered in `tests/fixtures/MANIFEST` (hash, origin, license). `tools/check_forbidden_artifacts.py` must keep passing.
- No dependency without a license audit recorded in `docs/LICENSES.md` and owner approval.
- Game work: update `docs/games/<slug>/STATUS.md` and its index in the same session. Metadata and hashes only. An inspected ISO is not a compatible game.

## 4. Evidence and honesty

- Label every factual statement: **Terverifikasi** (you ran it this session and showed the output), **Belum diverifikasi** (not run or not checked against a source), or **Dugaan** (inference).
- Never invent output, versions, hashes, timings, or hardware behavior.
- You never declare a Gate passed, certify clean-room status, or claim compatibility or boot support. Only the owner records Gate dispositions; you gather evidence.
- A local run is not CI. A change counts as CI-verified only after the Windows x64/MSVC and Linux/GCC jobs are green on a pushed commit.

## 5. Working protocol

- One logical change per commit, Conventional Commits, small and atomic. Keep `main` as the integration branch; implement each increment on a dedicated branch based on freshly fetched `origin/main`, not directly on main.
- On 2026-10-28 the owner authorized agents to create/push increment branches, create/update PRs, monitor/fix CI and merge into main after local verification, correctness review and successful Windows x64/MSVC plus Linux/GCC jobs for the exact current PR head. Recheck head/mergeability/review state immediately before merging and require the expected head commit in the merge command. Monitor CI for the actual merge commit as well; respect required reviews and merge queues.
- Preserve pre-existing local work. Use an isolated worktree for automation, inspect diffs and stage explicit task-owned files only. Never force-push, rewrite published history, direct-push main, bypass hooks/signing or use administrative merge overrides. Do not change repository permissions or protections without separate owner authorization.
- Tests first when possible. Never weaken or delete a test to make it pass, unless you prove the test is wrong and explain why.
- Never disable warnings (`/W4 /WX`), sanitizers, or the artifact guard to get a build through.
- No scope creep. Record out-of-scope findings in `docs/RISKS.md`; do not fix them silently.
- Keep `docs/STATE.md` a single, current status. Do not append per-run narratives; ROADMAP boxes are ticked only with evidence. Dated per-run evidence goes to docs/VERIFICATION_LOG.md. Do not hard-code counts that change per commit (tests, checklist items) in prose or tools; point to the generator or the log.
- Every recompiler/runtime increment commit must have a body naming the behavior, RPTP-REF IDs and test paths (see docs/PROVENANCE_PLAN.md).
- Gate and ADR dispositions: agents write status Proposed only; the owner changes it to Accepted or Passed.

Verification commands (Developer PowerShell x64):

    python tools/rptp_doctor.py
    cmake --preset windows-msvc
    cmake --build --preset windows-msvc
    python -m unittest discover -s tests -v
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-msvc.ps1

## 6. Stop and ask the owner when

- Anything touches legal, license, IP or clean-room questions, or a fixed decision.
- A Gate disposition, ISO/BIOS, or title choice is needed.
- A destructive or irreversible git action is required.
- A new dependency or large architectural cost appears.
- The same approach failed twice after a root-cause analysis.

## 7. End of session

Update `docs/STATE.md` and `docs/HANDOFF.md`, commit, then report in Indonesian:

1. Goal and result (done / partial / failed)
2. Changes (files, commits)
3. Evidence (commands and output summaries, labeled per section 4)
4. Decisions and ADRs
5. Problems, blockers, new risks
6. Gate status and at most three next steps
7. Items that need an owner decision
