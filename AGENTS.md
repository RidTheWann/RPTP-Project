# AGENTS.md — RPTP agent rules

Applies to every coding agent working in this repository. Read it fully at the start of each session.

**Language.** Talk to the owner in Indonesian. Write code, comments, commit messages, docs, and all CLI/log/error text in English.

**Priority when rules conflict:** (1) legal, license and the currently Accepted ADRs → (2) honesty and evidence (section 4) → (3) fixed project decisions (section 1) → (4) the owner's session instructions → (5) style. A session instruction does not silently amend an Accepted ADR; record a policy change in an ADR and have the owner accept it before treating that change as operative.

## 0. Session start (mandatory)

1. Read `docs/STATE.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`, `docs/CLEAN_ROOM_AUDIT.md`, `docs/DECISIONS/ADR-0001-*.md`, `docs/DECISIONS/ADR-0003-*.md`, `docs/DECISIONS/ADR-0004-*.md`, and `docs/DECISIONS/ADR-0005-*.md`. Do not read docs/VERIFICATION_LOG.md here: it is an append-only evidence log. Open it only when a task needs older evidence.
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

## 2. Provenance and reference boundaries (ADR-0003; proposed amendment ADR-0005)

- **Current rule:** ADR-0003 remains the operative policy until the owner changes ADR-0005 to `Accepted`. The proposed amendment is not permission to access or use additional material before acceptance.
- **If ADR-0005 is Accepted:** public, high-level product references may be consulted for concept inspiration only: feature summaries, user-facing documentation, public UI/workflow descriptions, screenshots, release announcements and broad problem statements. Record source, access date, the concept considered, intended RPTP use and limitations in `docs/REFERENCES.md`.
- **Never use as an implementation source:** source code, patches, code snippets, build configuration, scripts, tests, internal APIs, implementation-focused design docs, disassembly, internal algorithm descriptions, or issue/PR discussions that reveal implementation details. Do not consult material in those categories for RPTP implementation. Do not use exact code, tests, naming, structures, control flow, test values, or a line-by-line translation from another implementation.
- A conceptual source describes *what might be useful*, not technical correctness. Derive ISA, file-format, platform and runtime behavior from neutral authoritative specifications and independent experiments/tests. Write RPTP tests independently; a superficial rewrite or changed identifiers do not establish independent implementation.
- Every non-trivial behavior claim cites a permitted technical reference or an independent test in `docs/REFERENCES.md`. Unsupported claims remain unsupported. Do not write hardware facts from memory; cite them or mark them unverified.
- Components marked `Review required` in `docs/CLEAN_ROOM_AUDIT.md` must never be called clean-room certified. Do not "fix" provenance by consulting implementation material. Re-derivation and status changes require recorded evidence and owner review.
- Runtime/recompiler scope and Gate limitations remain unchanged. The conceptual-reference proposal does not change technical Gate dispositions, licensing requirements, synthetic-fixture restrictions, or independent provenance-review requirements.
- If implementation-level material is encountered accidentally: stop work in the affected area, do not use it, disclose the exposure in `docs/REFERENCES.md`, identify possibly affected files, and wait for owner review before continuing. A high-level reference intentionally consulted under an Accepted ADR must also be logged, but is not treated as a technical authority.

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

- `main` is the integration/release branch. Create one feature branch per feature or coherent change batch from the latest `main`; use names such as `feat/<short-name>`, `fix/<short-name>`, `test/<short-name>`, `docs/<short-name>`, or `policy/<short-name>`. Use small Conventional Commits, one logical change per commit. Push changes to the branch and open/update a PR; do not push commits directly to `main`. Keep PRs focused and independently reviewable. Merge to `main` only when the changes form a meaningful update batch, required CI is green on the latest PR head, conflicts are resolved, and there is no owner-requested hold. The owner has authorized agents in this conversation to create branches, push feature branches, open PRs, and merge completed batches. Never force-push or rewrite published history.
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

Update `docs/STATE.md` and `docs/HANDOFF.md` on the working branch, commit, open/update the PR, then report in Indonesian. Merge to `main` only under section 5:

1. Goal and result (done / partial / failed)
2. Changes (files, commits)
3. Evidence (commands and output summaries, labeled per section 4)
4. Decisions and ADRs
5. Problems, blockers, new risks
6. Gate status and at most three next steps
7. Items that need an owner decision
