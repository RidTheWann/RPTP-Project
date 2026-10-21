# Clean-room provenance audit

- **Audit date:** 2026-10-21
- **Policy:** [ADR-0003](DECISIONS/ADR-0003-sealed-source-clean-room-policy.md)
- **Exposure record:** [docs/REFERENCES.md](REFERENCES.md)

This audit tracks what can be said about existing work. It does not certify a file as clean-room, and it cannot prove that prior exposure had no subconscious influence. A component is only as strong as its recorded reference and test evidence.

## Status terms

- `Provisional independent`: authored against recorded neutral references and independent tests; no sealed implementation source is recorded. An independent provenance review is still required.
- `Review required`: functional overlap with previously viewed sealed material exists; do not claim clean-room certification until an independent review or re-derivation is recorded.
- `Blocked`: work may not proceed under ADR-0003 until the named prerequisite is met.
- `Recorded`: documentation or fixture metadata exists; this is not an implementation certification.
- `Sealed`: no further access is permitted.

## Component status

| Component | Exposure relevance | Current evidence | Status | Next action |
|---|---|---|---|---|
| Gate 0 synthetic fixture generator, ELF parser, oracle interpreter and C++ generator | Prior exposure included issue/release prose but no sealed `.cpp` implementation file. Generic MIPS/ELF references are recorded. | Gate 0 tests and differential trace, fixture and generated-source hashes, `docs/REFERENCES.md` | `Provisional independent` | Independent provenance review before Gate 3. Keep tests and hashes reproducible. |
| ISO inspector | Uses ELF and ISO 9660 structures. No sealed source recorded. | ISO inspector tests and full suite pass; CTest results recorded in `docs/VERIFICATION_LOG.md`; ELF reference and ECMA-119 reference | `Provisional independent` | Independent provenance review before Gate 2 closure. |
| CMake presets, CI workflows, doctor and build wrappers | Prior exposure included PS2 Web Recomp `CMakeLists.txt`, `scripts/port.sh` and `scripts/windows.py`. Functional overlap exists. | Independently authored claim only; no recorded template diff or independent review | `Review required` | A reviewer must confirm independent structure and expression, or the layer must be re-derived from current CMake/toolchain documentation and tests. B1b must not be described as clean-room certified meanwhile. |
| Runtime and recompiler expansion | Prior issue/release text included implementation-level descriptions. | None beyond the isolated synthetic spike | `Blocked` | Do not start until the formal Gate 0 disposition and a provenance plan for the affected area are recorded. |
| Documentation and exposure record | Records prior access; not an implementation source. | `docs/REFERENCES.md`, ADR-0001, ADR-0003 | `Recorded` | Update whenever exposure changes; never use a sealed project as a reference. |
| Synthetic binary fixtures | No game data. | `tests/fixtures/MANIFEST`, hashes, artifact guard | `Recorded` | Keep synthetic, manifest-registered and hash-checked. |
| Third-party dependencies | No implementation dependency currently vendored or linked. | `docs/LICENSES.md`; dependency inventory | `Recorded` | Audit license, provenance and notices before adding any dependency. |

## Rules for changing a status

1. `Review required` may become `Provisional independent` only after an independent reviewer records what was checked and why the file is not derived from sealed material.
2. `Provisional independent` must not be presented as a legal conclusion or a guarantee. It is an engineering provenance status.
3. Any accidental access to sealed material stops work. Record the access, identify affected files, quarantine them, and re-derive or review before continuing.
4. A status change requires an update to this audit and, when the policy boundary changes, a superseding ADR.

## Current conclusion

No existing file is certified clean-room. The Gate 0 and ISO inspector code have recorded neutral-reference and test evidence; the build/CI/doctor layer requires independent review. The owner's sealed-source policy is in force, and no new PS2 Web Recomp material was accessed during this audit.
