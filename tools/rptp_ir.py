#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Minimal synthetic-only IR and fail-closed control-flow analysis for RPTP.

This module reuses the narrow Gate 0 decoder. It does not execute code, emit
native code, recover complete functions, or claim complete R5900 behavior.
"""
import importlib.util
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping, Sequence

MAX_INSTRUCTIONS = 4096

FALLTHROUGH = "fallthrough"
CONDITIONAL_BRANCH = "conditional_branch"
DIRECT_JUMP = "direct_jump"
DIRECT_CALL = "direct_call"
INDIRECT_JUMP = "indirect_jump"
RETURN_CANDIDATE = "return_candidate"

SIGNED16 = "signed16"
ZERO16 = "zero16"
SHIFTED16 = "shifted16"

ORIGIN_ELF_ENTRY = "elf_entry"
ORIGIN_JAL_TARGET = "jal_target"
CANDIDATE_CONFIDENCE = "candidate"
CANDIDATE_LIMITATIONS = "Entry point or direct JAL target only; not a function extent, symbol, reachability or return-path claim."

IR_ELF_INVALID = "IR_ELF_INVALID"
IR_EMPTY_CODE = "IR_EMPTY_CODE"
IR_LIMIT_EXCEEDED = "IR_LIMIT_EXCEEDED"
IR_INVALID_PC = "IR_INVALID_PC"
IR_PC_OUT_OF_RANGE = "IR_PC_OUT_OF_RANGE"
IR_UNALIGNED_PC = "IR_UNALIGNED_PC"
IR_UNALIGNED_ENTRY = "IR_UNALIGNED_ENTRY"
IR_ENTRY_OUT_OF_RANGE = "IR_ENTRY_OUT_OF_RANGE"
IR_ENTRY_IN_DELAY_SLOT = "IR_ENTRY_IN_DELAY_SLOT"
IR_INVALID_WORD = "IR_INVALID_WORD"
IR_NON_CONTIGUOUS_CODE = "IR_NON_CONTIGUOUS_CODE"
IR_UNSUPPORTED_INSTRUCTION = "IR_UNSUPPORTED_INSTRUCTION"
IR_INVALID_CONTROL = "IR_INVALID_CONTROL"
IR_MISSING_DELAY_SLOT = "IR_MISSING_DELAY_SLOT"
IR_CONTROL_IN_DELAY_SLOT = "IR_CONTROL_IN_DELAY_SLOT"
IR_DELAY_SLOT_MISMATCH = "IR_DELAY_SLOT_MISMATCH"
IR_ORPHAN_DELAY_SLOT = "IR_ORPHAN_DELAY_SLOT"
IR_MISSING_TARGET = "IR_MISSING_TARGET"
IR_TARGET_UNALIGNED = "IR_TARGET_UNALIGNED"
IR_TARGET_OUT_OF_RANGE = "IR_TARGET_OUT_OF_RANGE"
IR_TARGET_IN_DELAY_SLOT = "IR_TARGET_IN_DELAY_SLOT"
IR_FALLTHROUGH_OUT_OF_RANGE = "IR_FALLTHROUGH_OUT_OF_RANGE"
IR_FALLTHROUGH_IN_DELAY_SLOT = "IR_FALLTHROUGH_IN_DELAY_SLOT"
IR_BLOCK_START_IN_DELAY_SLOT = "IR_BLOCK_START_IN_DELAY_SLOT"
IR_BLOCK_BOUNDARY = "IR_BLOCK_BOUNDARY"
IR_OVERLAPPING_BLOCK = "IR_OVERLAPPING_BLOCK"
IR_UNCOVERED_INSTRUCTION = "IR_UNCOVERED_INSTRUCTION"

_CONTROL_KINDS = {
    FALLTHROUGH,
    CONDITIONAL_BRANCH,
    DIRECT_JUMP,
    DIRECT_CALL,
    INDIRECT_JUMP,
    RETURN_CANDIDATE,
}
_DIRECT_TARGET_CONTROLS = {CONDITIONAL_BRANCH, DIRECT_JUMP, DIRECT_CALL}


def _load_spike():
    path = Path(__file__).with_name("rptp_gate0_spike.py")
    spec = importlib.util.spec_from_file_location("rptp_ir_spike_decoder", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load decoder module {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


spike = _load_spike()


class AnalysisError(ValueError):
    """Stable, fail-closed IR/CFG diagnostic."""

    def __init__(self, code: str, detail: str, *, pc: int | None = None) -> None:
        self.code = code
        self.pc = pc
        location = f" at 0x{pc:08X}" if pc is not None else ""
        super().__init__(f"{code}: {detail}{location}")


@dataclass(frozen=True)
class IRInstruction:
    pc: int
    word: int
    op: str
    control: str
    rs: int | None = None
    rt: int | None = None
    rd: int | None = None
    immediate: int | None = None
    immediate_kind: str | None = None
    target: int | None = None
    destination_register: int | None = None
    delay_slot_for: int | None = None

    @property
    def is_control_transfer(self) -> bool:
        return self.control != FALLTHROUGH


@dataclass(frozen=True)
class BasicBlock:
    start_pc: int
    end_pc: int
    instructions: tuple[IRInstruction, ...]
    successors: tuple[int, ...]

    @property
    def terminator(self) -> IRInstruction | None:
        for instruction in self.instructions:
            if instruction.is_control_transfer:
                return instruction
        return None


@dataclass(frozen=True)
class FunctionEntryCandidate:
    address: int
    origins: tuple[str, ...]
    call_sites: tuple[int, ...]
    confidence: str
    limitations: str


@dataclass(frozen=True)
class AnalysisResult:
    entry: int
    code_start: int
    code_end: int
    instructions: tuple[IRInstruction, ...]
    blocks: tuple[BasicBlock, ...]
    function_entries: tuple[FunctionEntryCandidate, ...]

    def to_dict(self) -> dict[str, Any]:
        instructions = []
        for instruction in self.instructions:
            instructions.append(
                {
                    "pc": instruction.pc,
                    "pc_hex": f"0x{instruction.pc:08X}",
                    "word": instruction.word,
                    "word_hex": f"0x{instruction.word:08X}",
                    "op": instruction.op,
                    "control": instruction.control,
                    "rs": instruction.rs,
                    "rt": instruction.rt,
                    "rd": instruction.rd,
                    "immediate": instruction.immediate,
                    "immediate_kind": instruction.immediate_kind,
                    "target": instruction.target,
                    "destination_register": instruction.destination_register,
                    "delay_slot_for": instruction.delay_slot_for,
                }
            )
        blocks = []
        for block in self.blocks:
            terminator = block.terminator
            blocks.append(
                {
                    "start_pc": block.start_pc,
                    "start_pc_hex": f"0x{block.start_pc:08X}",
                    "end_pc": block.end_pc,
                    "instruction_pcs": [instruction.pc for instruction in block.instructions],
                    "terminator_pc": None if terminator is None else terminator.pc,
                    "successors": list(block.successors),
                }
            )
        candidates = []
        for candidate in self.function_entries:
            candidates.append(
                {
                    "address": candidate.address,
                    "address_hex": f"0x{candidate.address:08X}",
                    "origins": list(candidate.origins),
                    "call_sites": list(candidate.call_sites),
                    "confidence": candidate.confidence,
                    "limitations": candidate.limitations,
                }
            )
        return {
            "schema_version": 1,
            "entry": self.entry,
            "code_start": self.code_start,
            "code_end": self.code_end,
            "instructions": instructions,
            "blocks": blocks,
            "function_entry_candidates": candidates,
        }


def _decode_word(pc: int, word: int) -> IRInstruction:
    try:
        decoded = spike.decode_instruction(pc, word)
    except ValueError as exc:
        raise AnalysisError(IR_UNSUPPORTED_INSTRUCTION, str(exc), pc=pc) from exc

    op = decoded["op"]
    immediate = None
    immediate_kind = None
    destination_register = None
    target = None

    if op in {"beq", "bne"}:
        control = CONDITIONAL_BRANCH
        target = decoded["target"]
    elif op == "j":
        control = DIRECT_JUMP
        target = decoded["target"]
    elif op == "jal":
        control = DIRECT_CALL
        target = decoded["target"]
        destination_register = spike.RA
    elif op == "jr":
        control = RETURN_CANDIDATE if decoded["rs"] == spike.RA else INDIRECT_JUMP
    elif op in {"nop", "addu", "addiu", "andi", "ori", "xori", "lui", "lw", "sw"}:
        control = FALLTHROUGH
    else:
        raise AnalysisError(IR_UNSUPPORTED_INSTRUCTION, f"Unsupported decoded operation {op}", pc=pc)

    if op == "lui" and decoded["rs"] != spike.ZERO:
        raise AnalysisError(IR_UNSUPPORTED_INSTRUCTION, "LUI requires rs=0", pc=pc)

    if op in {"addiu", "lw", "sw", "beq", "bne"}:
        immediate = decoded["imm"]
        immediate_kind = SIGNED16
    elif op in {"andi", "ori", "xori"}:
        immediate = decoded["imm"]
        immediate_kind = ZERO16
    elif op == "lui":
        immediate = decoded["imm"]
        immediate_kind = SHIFTED16

    if op in {"addiu", "andi", "ori", "xori", "lui", "lw"}:
        rt = decoded["rt"]
        destination_register = rt if rt != spike.ZERO else None
    elif op == "addu":
        rd = decoded["rd"]
        destination_register = rd if rd != spike.ZERO else None

    return IRInstruction(
        pc=pc,
        word=word,
        op=op,
        control=control,
        rs=decoded.get("rs"),
        rt=decoded.get("rt"),
        rd=decoded.get("rd"),
        immediate=immediate,
        immediate_kind=immediate_kind,
        target=target,
        destination_register=destination_register,
    )


def build_ir(entry: int, words: Mapping[int, int], *, max_instructions: int = MAX_INSTRUCTIONS) -> tuple[IRInstruction, ...]:
    """Build the minimal IR over a contiguous synthetic instruction range."""
    if not isinstance(entry, int) or isinstance(entry, bool):
        raise AnalysisError(IR_INVALID_PC, "Entry point must be an integer")
    if entry & 3:
        raise AnalysisError(IR_UNALIGNED_ENTRY, "Entry point is not 4-byte aligned", pc=entry)
    if not 0 <= entry <= 0xFFFFFFFC:
        raise AnalysisError(IR_ENTRY_OUT_OF_RANGE, "Entry point is outside the 32-bit address space", pc=entry)
    if not isinstance(max_instructions, int) or isinstance(max_instructions, bool) or max_instructions < 1:
        raise AnalysisError(IR_LIMIT_EXCEEDED, "Instruction limit must be a positive integer")
    if not words:
        raise AnalysisError(IR_EMPTY_CODE, "Code range is empty")
    if len(words) > max_instructions:
        raise AnalysisError(IR_LIMIT_EXCEEDED, f"Code range exceeds the {max_instructions}-instruction limit")

    items: list[tuple[int, int]] = []
    for pc, word in words.items():
        if not isinstance(pc, int) or isinstance(pc, bool):
            raise AnalysisError(IR_INVALID_PC, "Instruction address must be an integer")
        if not 0 <= pc <= 0xFFFFFFFC:
            raise AnalysisError(IR_PC_OUT_OF_RANGE, "Instruction address is outside the 32-bit address space", pc=pc)
        if pc & 3:
            raise AnalysisError(IR_UNALIGNED_PC, "Instruction address is not 4-byte aligned", pc=pc)
        if not isinstance(word, int) or isinstance(word, bool) or not 0 <= word <= 0xFFFFFFFF:
            raise AnalysisError(IR_INVALID_WORD, "Instruction word is not a 32-bit unsigned integer", pc=pc)
        items.append((pc, word))
    items.sort()
    pcs = [pc for pc, _ in items]

    for previous, current in zip(pcs, pcs[1:]):
        if current != previous + 4:
            raise AnalysisError(
                IR_NON_CONTIGUOUS_CODE,
                f"Code range is not contiguous between 0x{previous:08X} and 0x{current:08X}",
                pc=current,
            )

    pc_set = set(pcs)
    if entry not in pc_set:
        raise AnalysisError(IR_ENTRY_OUT_OF_RANGE, "Entry point is outside the analysed code range", pc=entry)

    by_pc = {pc: _decode_word(pc, word) for pc, word in items}
    delay_owner: dict[int, int] = {}
    for instruction in tuple(by_pc.values()):
        if not instruction.is_control_transfer:
            continue
        slot_pc = instruction.pc + 4
        if slot_pc not in by_pc:
            raise AnalysisError(IR_MISSING_DELAY_SLOT, "Control transfer has no instruction in its delay slot", pc=instruction.pc)
        slot = by_pc[slot_pc]
        if slot.is_control_transfer:
            raise AnalysisError(IR_CONTROL_IN_DELAY_SLOT, "Control transfer appears in a delay slot", pc=slot_pc)
        if slot_pc in delay_owner:
            raise AnalysisError(IR_CONTROL_IN_DELAY_SLOT, "Delay slot is claimed by more than one transfer", pc=slot_pc)
        delay_owner[slot_pc] = instruction.pc

    for slot_pc, owner_pc in delay_owner.items():
        by_pc[slot_pc] = replace(by_pc[slot_pc], delay_slot_for=owner_pc)

    instructions = tuple(by_pc[pc] for pc in pcs)
    delay_slots = set(delay_owner)
    for instruction in instructions:
        if instruction.control in _DIRECT_TARGET_CONTROLS:
            if instruction.target is None:
                raise AnalysisError(IR_MISSING_TARGET, "Direct control transfer has no target", pc=instruction.pc)
            if instruction.target & 3:
                raise AnalysisError(IR_TARGET_UNALIGNED, "Control-flow target is not 4-byte aligned", pc=instruction.target)
            if instruction.target not in pc_set:
                raise AnalysisError(IR_TARGET_OUT_OF_RANGE, "Control-flow target is outside the analysed code range", pc=instruction.target)
            if instruction.target in delay_slots:
                raise AnalysisError(IR_TARGET_IN_DELAY_SLOT, "Control-flow target points into a delay slot", pc=instruction.target)
        if instruction.control == CONDITIONAL_BRANCH:
            fallthrough = (instruction.pc + 8) & 0xFFFFFFFF
            if fallthrough not in pc_set:
                raise AnalysisError(IR_FALLTHROUGH_OUT_OF_RANGE, "Conditional fallthrough is outside the analysed code range", pc=instruction.pc)
            if fallthrough in delay_slots:
                raise AnalysisError(IR_FALLTHROUGH_IN_DELAY_SLOT, "Conditional fallthrough points into a delay slot", pc=instruction.pc)

    return instructions


def discover_blocks(instructions: Sequence[IRInstruction], entry: int) -> tuple[BasicBlock, ...]:
    """Partition validated IR into deterministic blocks without claiming reachability."""
    ordered = tuple(instructions)
    if not ordered:
        raise AnalysisError(IR_EMPTY_CODE, "Code range is empty")
    if not isinstance(entry, int) or isinstance(entry, bool):
        raise AnalysisError(IR_INVALID_PC, "Entry point must be an integer")
    if entry & 3:
        raise AnalysisError(IR_UNALIGNED_ENTRY, "Entry point is not 4-byte aligned", pc=entry)

    by_pc: dict[int, IRInstruction] = {}
    for instruction in ordered:
        if not isinstance(instruction.pc, int) or isinstance(instruction.pc, bool):
            raise AnalysisError(IR_INVALID_PC, "Instruction address must be an integer")
        if not 0 <= instruction.pc <= 0xFFFFFFFC:
            raise AnalysisError(IR_PC_OUT_OF_RANGE, "Instruction address is outside the 32-bit address space", pc=instruction.pc)
        if instruction.pc & 3:
            raise AnalysisError(IR_UNALIGNED_PC, "Instruction address is not 4-byte aligned", pc=instruction.pc)
        if instruction.control not in _CONTROL_KINDS:
            raise AnalysisError(IR_INVALID_CONTROL, "Instruction has an unknown control-flow classification", pc=instruction.pc)
        if instruction.pc in by_pc:
            raise AnalysisError(IR_OVERLAPPING_BLOCK, "Instruction address appears more than once", pc=instruction.pc)
        by_pc[instruction.pc] = instruction

    pcs = sorted(by_pc)
    for previous, current in zip(pcs, pcs[1:]):
        if current != previous + 4:
            raise AnalysisError(
                IR_NON_CONTIGUOUS_CODE,
                f"Code range is not contiguous between 0x{previous:08X} and 0x{current:08X}",
                pc=current,
            )
    if entry not in by_pc:
        raise AnalysisError(IR_ENTRY_OUT_OF_RANGE, "Entry point is outside the analysed code range", pc=entry)

    delay_slots: dict[int, int] = {}
    for instruction in ordered:
        if instruction.delay_slot_for is None:
            continue
        owner_pc = instruction.delay_slot_for
        if owner_pc != instruction.pc - 4 or owner_pc not in by_pc:
            raise AnalysisError(IR_ORPHAN_DELAY_SLOT, "Delay-slot owner is missing or not adjacent", pc=instruction.pc)
        owner = by_pc[owner_pc]
        if not owner.is_control_transfer:
            raise AnalysisError(IR_DELAY_SLOT_MISMATCH, "Delay-slot owner is not a control transfer", pc=instruction.pc)
        delay_slots[instruction.pc] = owner_pc

    transfers = tuple(instruction for instruction in ordered if instruction.is_control_transfer)
    for transfer in transfers:
        slot_pc = transfer.pc + 4
        if slot_pc not in by_pc:
            raise AnalysisError(IR_MISSING_DELAY_SLOT, "Control transfer has no instruction in its delay slot", pc=transfer.pc)
        slot = by_pc[slot_pc]
        if slot.is_control_transfer:
            raise AnalysisError(IR_CONTROL_IN_DELAY_SLOT, "Control transfer appears in a delay slot", pc=slot_pc)
        if slot.delay_slot_for != transfer.pc:
            raise AnalysisError(IR_DELAY_SLOT_MISMATCH, "Delay slot does not identify its transfer", pc=slot_pc)

    if entry in delay_slots:
        raise AnalysisError(IR_ENTRY_IN_DELAY_SLOT, "Entry point points into a delay slot", pc=entry)

    for transfer in transfers:
        if transfer.control in _DIRECT_TARGET_CONTROLS:
            if transfer.target is None:
                raise AnalysisError(IR_MISSING_TARGET, "Direct control transfer has no target", pc=transfer.pc)
            if transfer.target & 3:
                raise AnalysisError(IR_TARGET_UNALIGNED, "Control-flow target is not 4-byte aligned", pc=transfer.target)
            if transfer.target not in by_pc:
                raise AnalysisError(IR_TARGET_OUT_OF_RANGE, "Control-flow target is outside the analysed code range", pc=transfer.target)
            if transfer.target in delay_slots:
                raise AnalysisError(IR_TARGET_IN_DELAY_SLOT, "Control-flow target points into a delay slot", pc=transfer.target)
        if transfer.control == CONDITIONAL_BRANCH:
            fallthrough = (transfer.pc + 8) & 0xFFFFFFFF
            if fallthrough not in by_pc:
                raise AnalysisError(IR_FALLTHROUGH_OUT_OF_RANGE, "Conditional fallthrough is outside the analysed code range", pc=transfer.pc)
            if fallthrough in delay_slots:
                raise AnalysisError(IR_FALLTHROUGH_IN_DELAY_SLOT, "Conditional fallthrough points into a delay slot", pc=transfer.pc)

    code_start = pcs[0]
    code_end = pcs[-1] + 4
    starts = {code_start, entry}
    for transfer in transfers:
        if transfer.target is not None:
            starts.add(transfer.target)
        if transfer.control == CONDITIONAL_BRANCH:
            starts.add((transfer.pc + 8) & 0xFFFFFFFF)
        post_delay = (transfer.pc + 8) & 0xFFFFFFFF
        if post_delay in by_pc:
            starts.add(post_delay)

    for start in starts:
        if start not in by_pc:
            raise AnalysisError(IR_BLOCK_BOUNDARY, "Block start is outside the analysed code range", pc=start)
        if start & 3:
            raise AnalysisError(IR_TARGET_UNALIGNED, "Block start is not 4-byte aligned", pc=start)
        if start in delay_slots:
            raise AnalysisError(IR_BLOCK_START_IN_DELAY_SLOT, "Block start points into a delay slot", pc=start)

    start_list = sorted(starts)
    blocks: list[BasicBlock] = []
    for index, start in enumerate(start_list):
        end = start_list[index + 1] if index + 1 < len(start_list) else code_end
        block_instructions = tuple(by_pc[pc] for pc in range(start, end, 4))
        if not block_instructions:
            raise AnalysisError(IR_BLOCK_BOUNDARY, "Block contains no instructions", pc=start)
        terminators = [instruction for instruction in block_instructions if instruction.is_control_transfer]
        if len(terminators) > 1:
            raise AnalysisError(IR_OVERLAPPING_BLOCK, "Block contains more than one control transfer", pc=start)
        successor_candidates: tuple[int, ...]
        if terminators:
            terminator = terminators[0]
            if end != terminator.pc + 8:
                raise AnalysisError(IR_BLOCK_BOUNDARY, "Control-transfer block does not end after its delay slot", pc=terminator.pc)
            if len(block_instructions) < 2 or block_instructions[-2] != terminator:
                raise AnalysisError(IR_BLOCK_BOUNDARY, "Control transfer is not followed only by its delay slot", pc=terminator.pc)
            if block_instructions[-1].delay_slot_for != terminator.pc:
                raise AnalysisError(IR_DELAY_SLOT_MISMATCH, "Block delay slot does not identify its transfer", pc=block_instructions[-1].pc)
            if terminator.control == CONDITIONAL_BRANCH:
                fallthrough = (terminator.pc + 8) & 0xFFFFFFFF
                if terminator.target not in starts or fallthrough not in starts:
                    raise AnalysisError(IR_BLOCK_BOUNDARY, "Conditional successor is not a block start", pc=terminator.pc)
                successor_candidates = (terminator.target, fallthrough)
            elif terminator.control in {DIRECT_JUMP, DIRECT_CALL}:
                if terminator.target not in starts:
                    raise AnalysisError(IR_BLOCK_BOUNDARY, "Direct successor is not a block start", pc=terminator.pc)
                successor_candidates = (terminator.target,)
            else:
                successor_candidates = ()
        else:
            successor_candidates = (end,) if end < code_end else ()
        successors = tuple(dict.fromkeys(successor_candidates))
        blocks.append(
            BasicBlock(
                start_pc=start,
                end_pc=end,
                instructions=block_instructions,
                successors=successors,
            )
        )

    covered = tuple(instruction.pc for block in blocks for instruction in block.instructions)
    if covered != tuple(pcs):
        raise AnalysisError(IR_UNCOVERED_INSTRUCTION, "Block partition does not cover every instruction exactly once")
    return tuple(blocks)


def _discover_function_entries(instructions: Sequence[IRInstruction], entry: int) -> tuple[FunctionEntryCandidate, ...]:
    origins: dict[int, set[str]] = {entry: {ORIGIN_ELF_ENTRY}}
    call_sites: dict[int, list[int]] = {entry: []}
    for instruction in instructions:
        if instruction.control != DIRECT_CALL or instruction.target is None:
            continue
        origins.setdefault(instruction.target, set()).add(ORIGIN_JAL_TARGET)
        call_sites.setdefault(instruction.target, []).append(instruction.pc)

    candidates = []
    for address in sorted(origins):
        candidates.append(
            FunctionEntryCandidate(
                address=address,
                origins=tuple(sorted(origins[address])),
                call_sites=tuple(sorted(call_sites.get(address, []))),
                confidence=CANDIDATE_CONFIDENCE,
                limitations=CANDIDATE_LIMITATIONS,
            )
        )
    return tuple(candidates)


def analyze_words(entry: int, words: Mapping[int, int], *, max_instructions: int = MAX_INSTRUCTIONS) -> AnalysisResult:
    instructions = build_ir(entry, words, max_instructions=max_instructions)
    blocks = discover_blocks(instructions, entry)
    return AnalysisResult(
        entry=entry,
        code_start=instructions[0].pc,
        code_end=instructions[-1].pc + 4,
        instructions=instructions,
        blocks=blocks,
        function_entries=_discover_function_entries(instructions, entry),
    )


def analyze_elf(data: bytes, *, max_instructions: int = MAX_INSTRUCTIONS) -> AnalysisResult:
    try:
        entry, words, _info = spike.parse_elf(data)
    except ValueError as exc:
        raise AnalysisError(IR_ELF_INVALID, str(exc)) from exc
    return analyze_words(entry, words, max_instructions=max_instructions)
