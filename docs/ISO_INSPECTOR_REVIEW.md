# ISO Inspector independent review

- **Status: review recorded; fixes local to this increment.** This is a technical review record, not a Gate disposition or a clean-room certification. Only the project owner records Gate dispositions.
- **Reviewed commit:** `4c0df86` (`Merge pull request #30`), the tree that first contained the hardened inspector. Findings below are stated against that commit.
- **Review date:** 2026-10-29.
- **Reviewer:** a separate review pass by an agent that did not author the inspector. It read `tools/rptp_inspect.py`, [ISO_INSPECTOR.md](ISO_INSPECTOR.md), and `tests/test_iso_inspector.py`, and built synthetic probes from the documented contract only. No external implementation was consulted.
- **Scope:** read-only inspection and survey of the primary ISO 9660 namespace, per [ADR-0004](DECISIONS/ADR-0004-gate2-read-only-scope.md). Extraction, boot, native loading and game compatibility are out of scope.

## Method

1. Read the parser and the documented contract; enumerate every stable `InspectError` code and every documented structural rule.
2. Construct synthetic images that violate one rule at a time and observe inspection and survey behavior, without reading any file payload.
3. Compare the observations with ECMA-119 (`RPTP-REF-006`) and the contract; classify gaps by severity.
4. After fixes, re-run the probes as named regression tests in `IsoHardeningTests`.

The review is independent in the sense that the reviewer did not write the code and derived the probes from the contract. It is not a provenance certification: exposure history in [REFERENCES.md](REFERENCES.md) is unchanged, [CLEAN_ROOM_AUDIT.md](CLEAN_ROOM_AUDIT.md) retains its statuses, and the owner decides whether this record satisfies the independent-review prerequisite in [GATE2_EVIDENCE.md](GATE2_EVIDENCE.md).

## Findings

No High-severity finding was recorded. Four findings were recorded.

| ID | Severity | Finding at `4c0df86` | Resolution in this increment |
|---|---|---|---|
| G2-R-01 | Medium | Directory structure was not enforced. A root directory declared with 92 bytes and two 46-byte file records but no `.`/`..` was accepted; a boot subdirectory with a 46-byte data length was accepted; a subdirectory with data length 0 passed survey; a `SYSTEM.CNF` record of 47 bytes passed inspection although ECMA-119 §9.1.13 requires an even length. | Both modes require a positive directory data length, even record lengths, and `.` then `..` as the first two records (`DIRECTORY_DOT_ENTRY_INVALID`). The dot check follows record order, so a legal `.` record with System Use bytes may move `..` past offset 34. The original response over-constrained the length to a 2048-byte multiple; ECMA-119 §7.4.5 permits a file section shorter than its data space, and a 2026-10-30 read-only re-probe found all 15 Downhill Domination (USA) directories non-aligned (216 to 44,464 bytes; root 990 bytes). The 46-byte subdirectory now fails because its required records do not fit the declared length (`DIRECTORY_RECORD_CROSSES_BLOCK`), and the 92-byte dotless root fails the dot check. `test_accepts_non_block_aligned_directory_data_lengths` covers 114- and 990-byte directories. |
| G2-R-02 | Low | A 17-block image with a PVD at block 16 reported `VOLUME_DESCRIPTOR_TERMINATOR_MISSING` instead of the documented size failure; only a 10-block image was tested. | `MIN_IMAGE_BLOCKS = 18` is enforced before descriptor scanning in both modes; `test_image_size_gate_requires_descriptor_and_terminator_blocks` covers 17 blocks, and an 18-block descriptor set is accepted. |
| G2-R-03 | Low | ELF32 metadata accepted `e_ehsize = 53` and `e_phentsize = 33`, although ELF32 fixes them at 52 and 32 bytes; docs claimed a valid header. | Exact `e_ehsize == 52` and `e_phentsize == 32` are required (`ELF_HEADER_SIZE_INVALID`). Residual: `e_phoff` need not be 52 and is surfaced as a warning, not an error. |
| G2-R-04 | Low | Several documented fail-closed codes and exact limits were unreachable by tests: `SYSTEM_CNF_AMBIGUOUS`, `BOOT_PATH_EMPTY`, `BOOT_PATH_NOT_DIRECTORY`, `BOOT_TARGET_IS_DIRECTORY`, `NOT_A_DIRECTORY`, `BOOT_ELF_HEADER_TRUNCATED`, `UNSUPPORTED_ELF_CLASS`, `UNSUPPORTED_ELF_ENDIANNESS`, `ELF_VERSION_INVALID`, `ELF_HEADER_SIZE_INVALID`, `ELF_PROGRAM_HEADER_LIMIT`; the 32/33 boot-component, 4096/4097 program-header and 1 MiB `SYSTEM.CNF` boundaries were untested. | `test_documented_fail_closed_codes_are_reachable` and boundary tests now exercise each listed code and limit at N and N+1 where meaningful. A table in `IsoHardeningTests` records the code-to-probe mapping. |

## Residual risk

- G2-R-03's `e_phoff` slack remains deliberate: the reader reports program-header placement as a warning and never loads segments. Tightening it would reject images the current contract can still inspect.
- Directory and survey limits are tested at their exact boundaries, not proven sufficient for adversarial runtime complexity; the existing budgets remain the enforcement mechanism.
- This review did not fuzz the parser continuously and did not read retail file payloads. Retail observations remain read-only metadata records in [GATE2_EVIDENCE.md](GATE2_EVIDENCE.md).
- Gate 2 remains **NOT PASSED**. The owner prerequisites in [GATE2_EVIDENCE.md](GATE2_EVIDENCE.md) are unchanged.

## Evidence

- Probes are encoded in `IsoHardeningTests` in `tests/test_iso_inspector.py`; the full inspector suite passed locally before the pull request, and hosted CI is recorded in [VERIFICATION_LOG.md](VERIFICATION_LOG.md) once the increment merges.
- The contract changes are described in [ISO_INSPECTOR.md](ISO_INSPECTOR.md); risk tracking is R-028 in [RISKS.md](RISKS.md).
