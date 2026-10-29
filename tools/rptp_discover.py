#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Conservative, read-only direct-evidence function discovery for RPTP.

The analysis scans the file-backed executable PT_LOAD words of a validated
ELF32/EM_MIPS image with the current synthetic decoder.  It reports only
evidence that is directly present in the bytes: the ELF entry point, direct
branch/jump/call targets, a syntactic basic-block partition, JR/JALR sites
whose target is unresolved, unsupported encodings, and candidate entry points
derived solely from the ELF entry and in-code direct JAL targets.

It does not execute, extract, rewrite or recompile code, does not guess an
indirect target, and makes no function-extent, dead-code, runtime-reachability,
boot or compatibility claim.  An ISO input is inspected and read in memory;
no game file is created, modified or extracted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import BinaryIO, Callable

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import rptp_inspect as inspector
from rptp import isa

MODEL = "conservative_direct_evidence_v1"
MAX_INPUT_BYTES = 16 * 1024 * 1024
MAX_INSTRUCTIONS = 4 * 1024 * 1024
MAX_DIAGNOSTICS = 1_000_000

LIMITATIONS = (
    "Scans every aligned 32-bit word in file-backed executable PT_LOAD bytes; those bytes may contain data, padding, tables or non-code content.",
    "A basic block is a syntactic partition at observed boundaries; it is not a function boundary, a reachability result or an extent claim.",
    "Candidate entries are only the ELF entry point and in-code direct JAL targets; each is candidate-only and carries no name, extent, return-path or completeness claim.",
    "JR and JALR targets are never guessed. Unsupported encodings are reported and never interpreted as a known instruction or followed.",
    "No code is executed, extracted, rewritten or recompiled; no boot, runtime, dead-code or game-compatibility claim is made.",
    "Static analysis only: PS2 kernel, COP, VU, exception, TLB, cache and timing behavior are not modeled.",
)


class DiscoverError(inspector.InspectError):
    """Stable fail-closed discovery diagnostic."""


class _BlobReader:
    """Minimal inspector reader adapter for an in-memory ELF image."""

    def __init__(self, data: bytes):
        self.data = data
        self.size = len(data)

    def extent(self, entry: dict[str, object]) -> tuple[int, int]:
        return 0, self.size

    def read_at(self, offset: int, size: int) -> bytes:
        if offset < 0 or size < 0 or offset > self.size or size > self.size - offset:
            raise inspector.InspectError("IMAGE_BOUNDS", "ELF byte range is outside the input.")
        return self.data[offset:offset + size]


@dataclass(frozen=True)
class _CodeSegment:
    program_header_index: int
    file_offset: int
    virtual_address: int
    file_size: int
    word_count: int

    @property
    def end(self) -> int:
        return self.virtual_address + self.word_count * 4

    @property
    def trailing_bytes(self) -> int:
        return self.file_size - self.word_count * 4


class _DiagnosticSink:
    """Bounded diagnostics that fail closed instead of truncating evidence."""

    def __init__(self, limit: int):
        self.limit = limit
        self.items: list[dict[str, object]] = []

    def add(self, code: str, address: int, **fields: object) -> None:
        if len(self.items) >= self.limit:
            raise DiscoverError(
                "DISCOVER_DIAGNOSTIC_LIMIT",
                f"Discovery exceeds the {self.limit}-diagnostic safety limit.",
            )
        item: dict[str, object] = {"code": code, "address": address}
        item.update(fields)
        self.items.append(item)


def _safe_name(name: str) -> str:
    if name.startswith("<") and name.endswith(">"):
        return name
    return Path(name).name


def _encoding_label(word: int) -> str:
    opcode = (word >> 26) & 0x3F
    if opcode == 0:
        return f"special_0x{word & 0x3F:02x}"
    if opcode == 1:
        return f"regimm_0x{(word >> 16) & 0x1F:02x}"
    if opcode == 0x1C:
        return f"mmi_0x{word & 0x7FF:03x}"
    return f"opcode_0x{opcode:02x}"


def _validate_limits(max_input_bytes: int, max_instructions: int, max_diagnostics: int) -> None:
    for name, value in (
        ("max_input_bytes", max_input_bytes),
        ("max_instructions", max_instructions),
        ("max_diagnostics", max_diagnostics),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise DiscoverError("DISCOVER_INVALID_LIMIT", f"{name} must be a positive integer.")


def _read_input_path(path: Path, max_input_bytes: int) -> bytes:
    try:
        if not path.exists():
            raise DiscoverError("DISCOVER_INPUT_NOT_FOUND", f"Input file does not exist: {_safe_name(str(path))}.")
        if not path.is_file():
            raise DiscoverError("DISCOVER_INPUT_NOT_FILE", f"Input path is not a regular file: {_safe_name(str(path))}.")
        size = path.stat().st_size
        if size > max_input_bytes:
            raise DiscoverError(
                "DISCOVER_SIZE_LIMIT",
                f"Input exceeds the {max_input_bytes}-byte discovery limit.",
            )
        data = path.read_bytes()
    except DiscoverError:
        raise
    except OSError as exc:
        raise DiscoverError(
            "DISCOVER_INPUT_UNREADABLE",
            f"Cannot read input file: {exc.strerror or 'I/O error'}.",
        ) from exc
    if len(data) > max_input_bytes:
        raise DiscoverError(
            "DISCOVER_SIZE_LIMIT",
            f"Input exceeds the {max_input_bytes}-byte discovery limit.",
        )
    return data


def _code_segments(elf: dict[str, object]) -> list[_CodeSegment]:
    segments: list[_CodeSegment] = []
    for segment in elf["load_segments"]:
        assert isinstance(segment, dict)
        if not int(segment["flags"]) & 1:
            continue
        file_size = int(segment["file_size"])
        if file_size < 4:
            continue
        virtual_address = int(segment["virtual_address"])
        if virtual_address % 4:
            raise DiscoverError(
                "DISCOVER_SEGMENT_UNALIGNED",
                f"Executable PT_LOAD segment {segment['program_header_index']} is not 4-byte aligned.",
            )
        segments.append(
            _CodeSegment(
                program_header_index=int(segment["program_header_index"]),
                file_offset=int(segment["file_offset"]),
                virtual_address=virtual_address,
                file_size=file_size,
                word_count=file_size // 4,
            )
        )
    return segments


def _validate_elf(elf: dict[str, object]) -> tuple[int, list[_CodeSegment], _CodeSegment]:
    if int(elf["machine_id"]) != 8:
        raise DiscoverError(
            "DISCOVER_UNSUPPORTED_MACHINE",
            f"ELF machine id is {elf['machine_id']}; EM_MIPS (8) is required.",
        )
    if int(elf["type"]) != 2:
        raise DiscoverError(
            "DISCOVER_UNSUPPORTED_TYPE",
            f"ELF type is {elf['type']}; ET_EXEC (2) is required.",
        )
    if int(elf["load_segment_count"]) == 0:
        raise DiscoverError("DISCOVER_NO_LOAD_SEGMENTS", "ELF has no PT_LOAD segment.")
    segments = _code_segments(elf)
    if not segments:
        raise DiscoverError(
            "DISCOVER_NO_EXECUTABLE_CODE",
            "ELF has no file-backed executable PT_LOAD segment with a complete 32-bit word.",
        )
    previous_end = -1
    for segment in segments:
        if segment.virtual_address < previous_end:
            raise DiscoverError(
                "DISCOVER_CODE_OVERLAP",
                "File-backed executable PT_LOAD word ranges overlap; the scan would be ambiguous.",
            )
        previous_end = segment.end
    entry_point = int(elf["entry_point"])
    if entry_point % 4:
        raise DiscoverError(
            "DISCOVER_ENTRY_UNALIGNED",
            f"ELF entry point 0x{entry_point:08X} is not 4-byte aligned.",
        )
    matches = [segment for segment in segments if segment.virtual_address <= entry_point < segment.end]
    if len(matches) != 1:
        raise DiscoverError(
            "DISCOVER_ENTRY_NOT_IN_CODE",
            f"ELF entry point 0x{entry_point:08X} is not inside one file-backed executable word range.",
        )
    return entry_point, segments, matches[0]


def _add_boundary(
    boundaries: dict[int, dict[int, set[str]]],
    segment: _CodeSegment,
    address: int,
    reason: str,
) -> None:
    if segment.virtual_address <= address < segment.end and address % 4 == 0:
        boundaries[segment.program_header_index].setdefault(address, set()).add(reason)


def _scan_code_segments(
    segments: list[_CodeSegment],
    read_segment: Callable[[_CodeSegment], bytes],
    sink: _DiagnosticSink,
) -> dict[str, object]:
    boundaries: dict[int, dict[int, set[str]]] = {
        segment.program_header_index: {segment.virtual_address: {"segment_start"}}
        for segment in segments
    }
    branch_sites: list[dict[str, object]] = []
    jump_sites: list[dict[str, object]] = []
    call_sites: list[dict[str, object]] = []
    indirect_sites: list[dict[str, object]] = []
    unsupported_control_sites: list[dict[str, object]] = []
    delay_slot_addresses: set[int] = set()
    unsupported_by_encoding: Counter[str] = Counter()
    mnemonic_counts: Counter[str] = Counter()
    counts = {
        "word_count": 0,
        "supported_word_count": 0,
        "unsupported_word_count": 0,
        "zero_word_count": 0,
        "control_word_count": 0,
    }

    def add_unsupported(instruction: isa.Instruction, in_delay_slot: bool) -> None:
        encoding = _encoding_label(instruction.word)
        unsupported_by_encoding[encoding] += 1
        sink.add(
            "UNSUPPORTED_ENCODING",
            instruction.pc,
            word=instruction.word,
            mnemonic=instruction.mnemonic,
            encoding=encoding,
            instruction_class=instruction.cls,
            valid=instruction.valid,
            delay_slot=in_delay_slot,
            note=instruction.note,
        )

    for segment in segments:
        data = read_segment(segment)
        if len(data) != segment.file_size:
            raise DiscoverError(
                "DISCOVER_SEGMENT_READ",
                f"PT_LOAD segment {segment.program_header_index} did not return its declared file bytes.",
            )
        pending_delay_owner: int | None = None
        for index in range(segment.word_count):
            pc = segment.virtual_address + index * 4
            word = int.from_bytes(data[index * 4:index * 4 + 4], "little")
            instruction = isa.decode_instruction(word, pc)
            counts["word_count"] += 1
            if word == 0:
                counts["zero_word_count"] += 1
            if instruction.supported:
                counts["supported_word_count"] += 1
                mnemonic_counts[instruction.mnemonic] += 1
                if instruction.is_control:
                    counts["control_word_count"] += 1
            else:
                counts["unsupported_word_count"] += 1

            if pending_delay_owner is not None:
                if not instruction.supported:
                    add_unsupported(instruction, True)
                known_control = (
                    instruction.is_control
                    or (instruction.supported and instruction.is_halt)
                    or instruction.mnemonic in {"syscall", "break"}
                )
                if known_control:
                    sink.add(
                        "CONTROL_IN_DELAY_SLOT",
                        pc,
                        mnemonic=instruction.mnemonic,
                        supported=instruction.supported,
                        delay_slot_owner=pending_delay_owner,
                    )
                if index + 1 < segment.word_count:
                    _add_boundary(boundaries, segment, pc + 4, "after_transfer")
                pending_delay_owner = None
                continue

            if not instruction.supported:
                add_unsupported(instruction, False)
                if instruction.mnemonic in {"syscall", "break"}:
                    unsupported_control_sites.append({
                        "site": pc,
                        "mnemonic": instruction.mnemonic,
                        "kind": "unsupported_halt",
                        "word": word,
                        "note": instruction.note,
                    })
                elif instruction.mnemonic == "cop0":
                    unsupported_control_sites.append({
                        "site": pc,
                        "mnemonic": instruction.mnemonic,
                        "kind": "opaque_cop0",
                        "word": word,
                        "note": "COP0 is opaque; a control transfer or ERET cannot be ruled out.",
                    })
                elif instruction.is_control:
                    unsupported_control_sites.append({
                        "site": pc,
                        "mnemonic": instruction.mnemonic,
                        "kind": "unsupported_control",
                        "word": word,
                        "note": instruction.note,
                    })
                _add_boundary(boundaries, segment, pc, "unsupported")
                if index + 1 < segment.word_count:
                    _add_boundary(boundaries, segment, pc + 4, "after_unsupported")
                continue

            if instruction.is_halt:
                # ERET is the only halt form that is not already handled above;
                # the current decoder does not emit it, but the evidence is
                # still reported as unresolved rather than followed.
                unsupported_control_sites.append({
                    "site": pc,
                    "mnemonic": instruction.mnemonic,
                    "kind": "unresolved_halt",
                    "word": word,
                    "note": "Halt or exception-return target is not modeled.",
                })
                _add_boundary(boundaries, segment, pc, "transfer")
                if index + 1 < segment.word_count:
                    _add_boundary(boundaries, segment, pc + 4, "after_transfer")
                continue

            if instruction.is_branch:
                assert instruction.target is not None
                branch_sites.append({
                    "site": pc,
                    "mnemonic": instruction.mnemonic,
                    "target": instruction.target,
                    "likely": instruction.is_likely,
                })
                _add_boundary(boundaries, segment, pc, "transfer")
                if index + 1 < segment.word_count:
                    delay_slot_addresses.add(pc + 4)
                    pending_delay_owner = pc
                else:
                    sink.add("MISSING_DELAY_SLOT", pc, mnemonic=instruction.mnemonic)
                continue

            if instruction.is_jump:
                assert instruction.target is not None
                site = {
                    "site": pc,
                    "mnemonic": instruction.mnemonic,
                    "target": instruction.target,
                }
                if instruction.mnemonic == "jal":
                    call_sites.append(site)
                else:
                    jump_sites.append(site)
                _add_boundary(boundaries, segment, pc, "transfer")
                if index + 1 < segment.word_count:
                    delay_slot_addresses.add(pc + 4)
                    pending_delay_owner = pc
                else:
                    sink.add("MISSING_DELAY_SLOT", pc, mnemonic=instruction.mnemonic)
                continue

            if instruction.is_indirect:
                if instruction.mnemonic == "jr" and instruction.rs == 31:
                    kind = "return_candidate"
                elif instruction.mnemonic == "jalr":
                    kind = "indirect_call"
                else:
                    kind = "indirect_jump"
                indirect_sites.append({
                    "site": pc,
                    "mnemonic": instruction.mnemonic,
                    "rs": instruction.rs,
                    "rd": instruction.rd if instruction.mnemonic == "jalr" else None,
                    "kind": kind,
                    "resolution": "unresolved",
                    "reason": "register target is not known statically",
                })
                _add_boundary(boundaries, segment, pc, "transfer")
                if index + 1 < segment.word_count:
                    delay_slot_addresses.add(pc + 4)
                    pending_delay_owner = pc
                else:
                    sink.add("MISSING_DELAY_SLOT", pc, mnemonic=instruction.mnemonic)
                continue

            if instruction.is_control:
                unsupported_control_sites.append({
                    "site": pc,
                    "mnemonic": instruction.mnemonic,
                    "kind": "unresolved_control",
                    "word": word,
                    "note": instruction.note,
                })
                _add_boundary(boundaries, segment, pc, "transfer")
                if index + 1 < segment.word_count:
                    delay_slot_addresses.add(pc + 4)
                    pending_delay_owner = pc
                else:
                    sink.add("MISSING_DELAY_SLOT", pc, mnemonic=instruction.mnemonic)
                continue

    return {
        "boundaries": boundaries,
        "branch_sites": branch_sites,
        "jump_sites": jump_sites,
        "call_sites": call_sites,
        "indirect_sites": indirect_sites,
        "unsupported_control_sites": unsupported_control_sites,
        "delay_slot_addresses": delay_slot_addresses,
        "unsupported_by_encoding": unsupported_by_encoding,
        "mnemonic_counts": mnemonic_counts,
        "counts": counts,
    }


def _classify_target(
    target: int,
    segments: list[_CodeSegment],
    delay_slot_addresses: set[int],
    load_segments: list[dict[str, object]],
) -> tuple[str, _CodeSegment | None]:
    if target % 4:
        return "unaligned", None
    for segment in segments:
        if segment.virtual_address <= target < segment.end:
            if target in delay_slot_addresses:
                return "delay_slot", segment
            return "in_code", segment
    for segment in load_segments:
        virtual_address = int(segment["virtual_address"])
        file_size = int(segment["file_size"])
        memory_size = int(segment["memory_size"])
        if virtual_address <= target < virtual_address + file_size:
            if int(segment["flags"]) & 1:
                return "executable_trailing_bytes", None
            return "file_backed_non_executable", None
        if virtual_address <= target < virtual_address + memory_size:
            return "zero_fill", None
    return "outside_loaded_segments", None


def _finish_direct_sites(
    *,
    sites: list[dict[str, object]],
    kind: str,
    segments: list[_CodeSegment],
    delay_slot_addresses: set[int],
    load_segments: list[dict[str, object]],
    boundaries: dict[int, dict[int, set[str]]],
    sink: _DiagnosticSink,
) -> tuple[list[dict[str, object]], dict[str, int]]:
    unique: dict[int, dict[str, object]] = {}
    status_counts: Counter[str] = Counter()
    for site in sites:
        target = int(site["target"])
        status, segment = _classify_target(target, segments, delay_slot_addresses, load_segments)
        site["target_status"] = status
        status_counts[status] += 1
        if status == "in_code":
            assert segment is not None
            _add_boundary(boundaries, segment, target, f"{kind}_target")
        elif status == "delay_slot":
            sink.add(
                "TARGET_IN_DELAY_SLOT",
                int(site["site"]),
                target=target,
                transfer_kind=kind,
            )
        item = unique.setdefault(
            target,
            {
                "address": target,
                "site_count": 0,
                "target_status": status,
                "in_code": status == "in_code",
            },
        )
        item["site_count"] = int(item["site_count"]) + 1
    return (
        [unique[address] for address in sorted(unique)],
        dict(sorted(status_counts.items())),
    )


def _build_blocks(
    segments: list[_CodeSegment],
    boundaries: dict[int, dict[int, set[str]]],
) -> list[dict[str, object]]:
    blocks: list[dict[str, object]] = []
    for segment in segments:
        local = boundaries[segment.program_header_index]
        local.setdefault(segment.virtual_address, set()).add("segment_start")
        starts = sorted(local)
        for address in starts:
            if address < segment.virtual_address or address >= segment.end or address % 4:
                raise DiscoverError(
                    "DISCOVER_INTERNAL_BLOCK_BOUNDARY",
                    f"Internal block boundary 0x{address:08X} is outside its executable segment.",
                )
        for index, start in enumerate(starts):
            end = starts[index + 1] if index + 1 < len(starts) else segment.end
            if end <= start:
                raise DiscoverError(
                    "DISCOVER_INTERNAL_BLOCK_BOUNDARY",
                    f"Internal block partition is not strictly increasing at 0x{start:08X}.",
                )
            blocks.append({
                "segment_index": segment.program_header_index,
                "start": start,
                "end": end,
                "instruction_count": (end - start) // 4,
                "start_reasons": sorted(local[start]),
            })
    return blocks


def _discover(
    elf: dict[str, object],
    read_segment: Callable[[_CodeSegment], bytes],
    source: dict[str, object],
    inherited_warnings: list[str],
    *,
    max_instructions: int,
    max_diagnostics: int,
) -> dict[str, object]:
    entry_point, segments, entry_segment = _validate_elf(elf)
    total_words = sum(segment.word_count for segment in segments)
    if total_words > max_instructions:
        raise DiscoverError(
            "DISCOVER_INSTRUCTION_LIMIT",
            f"Scanned executable words ({total_words}) exceed the {max_instructions}-instruction safety limit.",
        )

    warnings = list(inherited_warnings)
    for segment in segments:
        if segment.trailing_bytes:
            warnings.append(
                f"PT_LOAD segment {segment.program_header_index} has {segment.trailing_bytes} trailing "
                "file byte(s) after its last complete 32-bit word; they were not decoded."
            )

    sink = _DiagnosticSink(max_diagnostics)
    scan = _scan_code_segments(segments, read_segment, sink)
    boundaries = scan["boundaries"]  # type: ignore[assignment]
    branch_sites = scan["branch_sites"]  # type: ignore[assignment]
    jump_sites = scan["jump_sites"]  # type: ignore[assignment]
    call_sites = scan["call_sites"]  # type: ignore[assignment]
    indirect_sites = scan["indirect_sites"]  # type: ignore[assignment]
    unsupported_control_sites = scan["unsupported_control_sites"]  # type: ignore[assignment]
    delay_slot_addresses = scan["delay_slot_addresses"]  # type: ignore[assignment]
    unsupported_by_encoding = scan["unsupported_by_encoding"]  # type: ignore[assignment]
    mnemonic_counts = scan["mnemonic_counts"]  # type: ignore[assignment]
    counts = scan["counts"]  # type: ignore[assignment]

    if entry_point in delay_slot_addresses:
        raise DiscoverError(
            "DISCOVER_ENTRY_IN_DELAY_SLOT",
            f"ELF entry point 0x{entry_point:08X} is a delay-slot word; the entry cannot be a transferred instruction.",
        )
    _add_boundary(boundaries, entry_segment, entry_point, "entry")

    branch_targets, branch_target_status = _finish_direct_sites(
        sites=branch_sites,
        kind="branch",
        segments=segments,
        delay_slot_addresses=delay_slot_addresses,
        load_segments=elf["load_segments"],
        boundaries=boundaries,
        sink=sink,
    )
    jump_targets, jump_target_status = _finish_direct_sites(
        sites=jump_sites,
        kind="jump",
        segments=segments,
        delay_slot_addresses=delay_slot_addresses,
        load_segments=elf["load_segments"],
        boundaries=boundaries,
        sink=sink,
    )
    call_targets, call_target_status = _finish_direct_sites(
        sites=call_sites,
        kind="call",
        segments=segments,
        delay_slot_addresses=delay_slot_addresses,
        load_segments=elf["load_segments"],
        boundaries=boundaries,
        sink=sink,
    )

    candidates: dict[int, dict[str, object]] = {}

    def add_candidate(address: int, origin: str, call_site: int | None = None) -> None:
        item = candidates.setdefault(
            address,
            {
                "address": address,
                "origins": set(),
                "call_sites": set(),
                "candidate_only": True,
                "note": "Candidate entry only; no function extent, reachability or completeness claim.",
            },
        )
        origins = item["origins"]
        assert isinstance(origins, set)
        origins.add(origin)
        if call_site is not None:
            sites = item["call_sites"]
            assert isinstance(sites, set)
            sites.add(call_site)

    add_candidate(entry_point, "elf_entry")
    for site in call_sites:
        if site["target_status"] == "in_code":
            add_candidate(int(site["target"]), "jal_target", int(site["site"]))

    candidate_rows: list[dict[str, object]] = []
    for address in sorted(candidates):
        item = candidates[address]
        origins = item["origins"]
        call_site_set = item["call_sites"]
        assert isinstance(origins, set) and isinstance(call_site_set, set)
        candidate_rows.append({
            "address": address,
            "origins": sorted(origins),
            "call_sites": sorted(call_site_set),
            "candidate_only": True,
            "note": item["note"],
        })

    blocks = _build_blocks(segments, boundaries)
    diagnostic_counts = Counter(str(item["code"]) for item in sink.items)
    sink.items.sort(key=lambda item: (int(item["address"]), str(item["code"])))
    unsupported_summary = [
        {"encoding": encoding, "count": count}
        for encoding, count in sorted(
            unsupported_by_encoding.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]
    supported_mnemonics = [
        {"mnemonic": mnemonic, "count": count}
        for mnemonic, count in sorted(mnemonic_counts.items())
    ]
    unsupported_encoding_count = diagnostic_counts.get("UNSUPPORTED_ENCODING", 0)
    if unsupported_encoding_count != int(counts["unsupported_word_count"]):
        raise DiscoverError(
            "DISCOVER_INTERNAL_COUNT_MISMATCH",
            "Internal unsupported-word count does not match the emitted diagnostics.",
        )

    target_status_counts: Counter[str] = Counter()
    for statuses in (branch_target_status, jump_target_status, call_target_status):
        target_status_counts.update(statuses)
    unresolved_target_count = sum(
        count for status, count in target_status_counts.items() if status != "in_code"
    )
    if unresolved_target_count:
        details = ", ".join(
            f"{status}={count}" for status, count in sorted(target_status_counts.items())
            if status != "in_code"
        )
        warnings.append(
            f"{unresolved_target_count} direct target(s) were not followed because they are not "
            f"in-code word addresses ({details}); they remain reported as unresolved evidence."
        )
    if diagnostic_counts.get("MISSING_DELAY_SLOT"):
        warnings.append(
            f"{diagnostic_counts['MISSING_DELAY_SLOT']} control instruction(s) at the end of a "
            "scanned segment have no delay slot in that segment."
        )
    if diagnostic_counts.get("CONTROL_IN_DELAY_SLOT"):
        warnings.append(
            f"{diagnostic_counts['CONTROL_IN_DELAY_SLOT']} transfer or halt encoding(s) were observed "
            "inside a delay slot; they were not followed as independent transfers."
        )

    for site_collection in (branch_sites, jump_sites, call_sites, indirect_sites, unsupported_control_sites):
        site_collection.sort(key=lambda item: int(item["site"]))

    status = "DISCOVERED_WITH_WARNINGS" if warnings else "DISCOVERED"
    return {
        "status": status,
        "model": MODEL,
        "source": source,
        "elf": {
            "entry_point": entry_point,
            "machine_id": elf["machine_id"],
            "machine": elf["machine"],
            "type": elf["type"],
            "program_header_count": elf["program_header_count"],
            "load_segment_count": elf["load_segment_count"],
            "load_segments_overlap": elf["load_segments_overlap"],
            "executable_segment_count": len(segments),
            "entry_segment_index": entry_segment.program_header_index,
        },
        "entry_point": entry_point,
        "candidates": candidate_rows,
        "code": {
            "word_count": counts["word_count"],
            "supported_word_count": counts["supported_word_count"],
            "unsupported_word_count": counts["unsupported_word_count"],
            "zero_word_count": counts["zero_word_count"],
            "control_word_count": counts["control_word_count"],
            "branch_site_count": len(branch_sites),
            "jump_site_count": len(jump_sites),
            "call_site_count": len(call_sites),
            "indirect_site_count": len(indirect_sites),
            "unsupported_control_site_count": len(unsupported_control_sites),
            "direct_target_count": len(branch_sites) + len(jump_sites) + len(call_sites),
            "diagnostic_count": len(sink.items),
            "candidate_count": len(candidate_rows),
            "block_count": len(blocks),
            "segments": [
                {
                    "program_header_index": segment.program_header_index,
                    "file_offset": segment.file_offset,
                    "virtual_address": segment.virtual_address,
                    "file_size": segment.file_size,
                    "word_count": segment.word_count,
                    "trailing_bytes": segment.trailing_bytes,
                    "virtual_word_end": segment.end,
                }
                for segment in segments
            ],
            "supported_mnemonics": supported_mnemonics,
        },
        "direct_targets": {
            "branch": branch_targets,
            "jump": jump_targets,
            "call": call_targets,
            "status_counts": dict(sorted(target_status_counts.items())),
        },
        "branch_sites": branch_sites,
        "jump_sites": jump_sites,
        "call_sites": call_sites,
        "indirect_transfers": indirect_sites,
        "unsupported_control": unsupported_control_sites,
        "unsupported_encodings": unsupported_summary,
        "diagnostic_counts": dict(sorted(diagnostic_counts.items())),
        "diagnostics": sink.items,
        "basic_blocks": blocks,
        "warnings": warnings,
        "limitations": list(LIMITATIONS),
    }


def discover_elf_bytes(
    data: bytes,
    *,
    name: str = "<memory>",
    max_input_bytes: int = MAX_INPUT_BYTES,
    max_instructions: int = MAX_INSTRUCTIONS,
    max_diagnostics: int = MAX_DIAGNOSTICS,
) -> dict[str, object]:
    """Discover direct evidence in an in-memory ELF32 image."""
    _validate_limits(max_input_bytes, max_instructions, max_diagnostics)
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("ELF data must be bytes")
    data = bytes(data)
    if len(data) > max_input_bytes:
        raise DiscoverError(
            "DISCOVER_SIZE_LIMIT",
            f"Input exceeds the {max_input_bytes}-byte discovery limit.",
        )
    elf = inspector.IsoReader.parse_elf(
        _BlobReader(data),
        {"name": _safe_name(name), "size": len(data)},
    )
    source = {
        "kind": "elf",
        "input_name": _safe_name(name),
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    return _discover(
        elf,
        lambda segment: data[segment.file_offset:segment.file_offset + segment.file_size],
        source,
        [],
        max_instructions=max_instructions,
        max_diagnostics=max_diagnostics,
    )


def discover_elf_path(
    path: Path,
    *,
    max_input_bytes: int = MAX_INPUT_BYTES,
    max_instructions: int = MAX_INSTRUCTIONS,
    max_diagnostics: int = MAX_DIAGNOSTICS,
) -> dict[str, object]:
    """Discover direct evidence in an ELF file opened read-only."""
    _validate_limits(max_input_bytes, max_instructions, max_diagnostics)
    path = Path(path)
    data = _read_input_path(path, max_input_bytes)
    return discover_elf_bytes(
        data,
        name=path.name,
        max_input_bytes=max_input_bytes,
        max_instructions=max_instructions,
        max_diagnostics=max_diagnostics,
    )


def discover_iso_path(
    path: Path,
    *,
    max_input_bytes: int = MAX_INPUT_BYTES,
    max_instructions: int = MAX_INSTRUCTIONS,
    max_diagnostics: int = MAX_DIAGNOSTICS,
    chunk_size: int = inspector.CHUNK_SIZE,
) -> dict[str, object]:
    """Discover direct evidence in an ISO boot executable without extraction."""
    _validate_limits(max_input_bytes, max_instructions, max_diagnostics)
    if not isinstance(chunk_size, int) or isinstance(chunk_size, bool) or chunk_size <= 0:
        raise DiscoverError("DISCOVER_INVALID_LIMIT", "chunk_size must be a positive integer.")
    path = Path(path)
    try:
        if not path.exists():
            raise DiscoverError("DISCOVER_INPUT_NOT_FOUND", f"Input file does not exist: {path.name}.")
        if not path.is_file():
            raise DiscoverError("DISCOVER_INPUT_NOT_FILE", f"Input path is not a regular file: {path.name}.")
        with path.open("rb") as stream:
            size = path.stat().st_size
            reader = inspector.IsoReader(
                stream,
                size,
                path.name,
                max_read_bytes=max_input_bytes,
                chunk_size=chunk_size,
            )
            inspection = reader.inspect()
            boot = inspection["boot_executable"]
            assert isinstance(boot, dict)
            boot_size = int(boot["size_bytes"])
            if boot_size > max_input_bytes:
                raise DiscoverError(
                    "DISCOVER_SIZE_LIMIT",
                    f"BOOT executable exceeds the {max_input_bytes}-byte discovery limit.",
                )
            extent = boot["extent"]
            assert isinstance(extent, dict)
            boot_extent = {
                "name": boot["path"],
                "lba": extent["extent_lba"],
                "xa_len": 0,
                "size": boot_size,
            }
            start, _ = reader.extent(boot_extent)
            source = {
                "kind": "iso",
                "input_name": path.name,
                "image_size_bytes": size,
                "boot_path": boot["path"],
                "boot_size_bytes": boot_size,
                "boot_sha256": boot["sha256"],
            }
            return _discover(
                boot["elf"],
                lambda segment: reader.read_range(
                    start + segment.file_offset,
                    segment.file_size,
                ),
                source,
                list(inspection["warnings"]),
                max_instructions=max_instructions,
                max_diagnostics=max_diagnostics,
            )
    except DiscoverError:
        raise
    except inspector.InspectError:
        raise
    except OSError as exc:
        raise DiscoverError(
            "DISCOVER_INPUT_UNREADABLE",
            f"Cannot read input file: {exc.strerror or 'I/O error'}.",
        ) from exc


def _print_human(report: dict[str, object]) -> None:
    code = report["code"]
    source = report["source"]
    assert isinstance(code, dict) and isinstance(source, dict)
    print(f"RPTP conservative function discovery: {report['status']}")
    print(f"Source: {source['input_name']} ({str(source['kind']).upper()})")
    if source["kind"] == "iso":
        print(f"BOOT executable: {source['boot_path']} ({source['boot_size_bytes']} bytes)")
    print(f"Entry point: 0x{int(report['entry_point']):08X}")
    print(
        f"Scanned {code['word_count']} word(s) in {len(code['segments'])} file-backed "
        "executable PT_LOAD segment(s)"
    )
    print(
        f"Supported: {code['supported_word_count']}; unsupported: {code['unsupported_word_count']}; "
        f"zero: {code['zero_word_count']}; control: {code['control_word_count']}"
    )
    candidates = report["candidates"]
    print(f"Candidate entries (candidate-only): {len(candidates)}")
    for candidate in candidates[:10]:  # type: ignore[index]
        assert isinstance(candidate, dict)
        print(
            f"  0x{int(candidate['address']):08X}  "
            f"origins={','.join(candidate['origins'])} "  # type: ignore[arg-type]
            f"call_sites={len(candidate['call_sites'])}"  # type: ignore[arg-type]
        )
    if len(candidates) > 10:
        print(f"  ... {len(candidates) - 10} more candidate(s)")
    print(
        f"Direct transfers: {code['branch_site_count']} branch(es), {code['jump_site_count']} J, "
        f"{code['call_site_count']} JAL; indirect JR/JALR: {code['indirect_site_count']}; "
        f"unsupported control evidence: {code['unsupported_control_site_count']}"
    )
    print(f"Basic blocks: {code['block_count']}; diagnostics: {code['diagnostic_count']}")
    summary = report["unsupported_encodings"]
    if summary:
        print("Unsupported encodings (top):")
        for item in summary[:5]:  # type: ignore[index]
            assert isinstance(item, dict)
            print(f"  {int(item['count']):8d}  {item['encoding']}")
        if len(summary) > 5:
            print(f"  ... {len(summary) - 5} more encoding group(s)")
    for warning in report["warnings"]:  # type: ignore[assignment]
        print(f"WARNING: {warning}")
    print("Static direct-evidence only; no execution, extraction, function-extent or compatibility claim.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--elf", type=Path, metavar="FILE", help="ELF file opened read-only")
    mode.add_argument("--iso", type=Path, metavar="IMAGE", help="ISO image inspected and read in memory")
    parser.add_argument("--json", action="store_true", help="Emit deterministic machine-readable JSON")
    parser.add_argument(
        "--max-input-bytes",
        type=int,
        default=MAX_INPUT_BYTES,
        help=f"Input or BOOT executable size limit (default {MAX_INPUT_BYTES})",
    )
    parser.add_argument(
        "--max-instructions",
        type=int,
        default=MAX_INSTRUCTIONS,
        help=f"Scanned 32-bit word limit (default {MAX_INSTRUCTIONS})",
    )
    parser.add_argument(
        "--max-diagnostics",
        type=int,
        default=MAX_DIAGNOSTICS,
        help=f"Diagnostic limit before fail-closed exit (default {MAX_DIAGNOSTICS})",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=inspector.CHUNK_SIZE,
        help=f"ISO read chunk size in bytes (default {inspector.CHUNK_SIZE})",
    )
    args = parser.parse_args(argv)
    for name in ("max_input_bytes", "max_instructions", "max_diagnostics", "chunk_size"):
        if getattr(args, name) <= 0:
            parser.error(f"--{name.replace('_', '-')} must be positive")
    try:
        common = {
            "max_input_bytes": args.max_input_bytes,
            "max_instructions": args.max_instructions,
            "max_diagnostics": args.max_diagnostics,
        }
        if args.elf is not None:
            report = discover_elf_path(args.elf, **common)
        else:
            report = discover_iso_path(args.iso, chunk_size=args.chunk_size, **common)
    except inspector.InspectError as exc:
        output = {"status": "ERROR", "error_code": exc.code, "message": exc.message}
        if args.json:
            print(json.dumps(output, indent=2, sort_keys=True))
        else:
            print(f"RPTP discovery failed [{exc.code}]: {exc.message}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    _print_human(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
