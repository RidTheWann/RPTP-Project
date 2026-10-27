#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Deterministic IR-to-C++ lowering for the synthetic RPTP instruction subset.

The input is a validated ``tools/rptp_ir.py`` analysis result. The generated
program is a testable C++20 state machine for the existing synthetic execution
model; it is not a complete R5900 recompiler or runtime.
"""
from __future__ import annotations

from typing import Any

DEFAULT_RETURN_SENTINEL = 0x7FFF0000
DEFAULT_MAX_STEPS = 128
MAX_LOWER_INSTRUCTIONS = 4096

LOWER_INVALID_RESULT = "LOWER_INVALID_RESULT"
LOWER_UNSUPPORTED_OP = "LOWER_UNSUPPORTED_OP"
LOWER_MALFORMED_INSTRUCTION = "LOWER_MALFORMED_INSTRUCTION"
LOWER_INVALID_CONTROL = "LOWER_INVALID_CONTROL"
LOWER_INVALID_TARGET = "LOWER_INVALID_TARGET"
LOWER_INVALID_DELAY_SLOT = "LOWER_INVALID_DELAY_SLOT"
LOWER_INVALID_BLOCK = "LOWER_INVALID_BLOCK"
LOWER_LIMIT_EXCEEDED = "LOWER_LIMIT_EXCEEDED"
LOWER_INVALID_OPTION = "LOWER_INVALID_OPTION"

FALLTHROUGH = "fallthrough"
CONDITIONAL_BRANCH = "conditional_branch"
DIRECT_JUMP = "direct_jump"
DIRECT_CALL = "direct_call"
INDIRECT_JUMP = "indirect_jump"
RETURN_CANDIDATE = "return_candidate"

SIGNED16 = "signed16"
ZERO16 = "zero16"
SHIFTED16 = "shifted16"

RA = 31

_CONTROLS = {
    FALLTHROUGH,
    CONDITIONAL_BRANCH,
    DIRECT_JUMP,
    DIRECT_CALL,
    INDIRECT_JUMP,
    RETURN_CANDIDATE,
}
_DIRECT_CONTROLS = {CONDITIONAL_BRANCH, DIRECT_JUMP, DIRECT_CALL}
_REGISTER_DEST_OPS = {"addu", "and", "or", "xor", "nor", "slt", "sltu"}
_SUPPORTED_OPS = {"nop", "addu", "and", "or", "xor", "nor", "slt", "sltu", "addiu", "slti", "andi", "ori", "xori", "lui", "lw", "sw", "beq", "bne", "j", "jal", "jr"}
_FIXED_CONTROLS = {
    "nop": FALLTHROUGH,
    "addu": FALLTHROUGH,
    "and": FALLTHROUGH,
    "or": FALLTHROUGH,
    "xor": FALLTHROUGH,
    "nor": FALLTHROUGH,
    "slt": FALLTHROUGH,
    "sltu": FALLTHROUGH,
    "addiu": FALLTHROUGH,
    "slti": FALLTHROUGH,
    "andi": FALLTHROUGH,
    "ori": FALLTHROUGH,
    "xori": FALLTHROUGH,
    "lui": FALLTHROUGH,
    "lw": FALLTHROUGH,
    "sw": FALLTHROUGH,
    "beq": CONDITIONAL_BRANCH,
    "bne": CONDITIONAL_BRANCH,
    "j": DIRECT_JUMP,
    "jal": DIRECT_CALL,
}
_MISSING = object()


class LoweringError(ValueError):
    """Stable, fail-closed lowering diagnostic."""

    def __init__(self, code: str, detail: str, *, pc: int | None = None) -> None:
        self.code = code
        self.pc = pc
        location = f" at 0x{pc:08X}" if pc is not None else ""
        super().__init__(f"{code}: {detail}{location}")


def _read(obj: Any, name: str, code: str, *, pc: int | None = None) -> Any:
    value = getattr(obj, name, _MISSING)
    if value is _MISSING:
        raise LoweringError(code, f"Missing required field {name}", pc=pc)
    return value


def _integer(
    value: Any,
    what: str,
    *,
    code: str,
    pc: int | None = None,
    minimum: int = 0,
    maximum: int = 0xFFFFFFFF,
) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise LoweringError(code, f"{what} must be an integer", pc=pc)
    if not minimum <= value <= maximum:
        raise LoweringError(code, f"{what} is outside the supported range", pc=pc)
    return value


def _optional_integer(
    value: Any,
    what: str,
    *,
    code: str,
    pc: int | None = None,
    minimum: int = 0,
    maximum: int = 0xFFFFFFFF,
) -> int | None:
    if value is None:
        return None
    return _integer(value, what, code=code, pc=pc, minimum=minimum, maximum=maximum)


def _register(instruction: Any, name: str, *, required: bool) -> int | None:
    value = _read(instruction, name, LOWER_MALFORMED_INSTRUCTION, pc=instruction.pc)
    if value is None:
        if required:
            raise LoweringError(LOWER_MALFORMED_INSTRUCTION, f"Missing {name} register", pc=instruction.pc)
        return None
    return _integer(value, f"{name} register", code=LOWER_MALFORMED_INSTRUCTION, pc=instruction.pc, maximum=31)


def _expect_none(instruction: Any, name: str) -> None:
    value = _read(instruction, name, LOWER_MALFORMED_INSTRUCTION, pc=instruction.pc)
    if value is not None:
        raise LoweringError(LOWER_MALFORMED_INSTRUCTION, f"{name} must be absent for this operation", pc=instruction.pc)


def _prepare_options(return_sentinel: Any, max_steps: Any) -> tuple[int, int]:
    sentinel = _integer(
        return_sentinel,
        "Return sentinel",
        code=LOWER_INVALID_OPTION,
    )
    steps = _integer(
        max_steps,
        "Step limit",
        code=LOWER_INVALID_OPTION,
        minimum=1,
        maximum=1_000_000_000,
    )
    return sentinel, steps


def _validate_result_shape(result: Any) -> tuple[int, int, int, tuple[Any, ...], tuple[Any, ...]]:
    if result is None:
        raise LoweringError(LOWER_INVALID_RESULT, "Analysis result must not be None")
    entry = _integer(_read(result, "entry", LOWER_INVALID_RESULT), "Entry point", code=LOWER_INVALID_RESULT)
    code_start = _integer(_read(result, "code_start", LOWER_INVALID_RESULT), "Code start", code=LOWER_INVALID_RESULT)
    code_end = _integer(
        _read(result, "code_end", LOWER_INVALID_RESULT),
        "Code end",
        code=LOWER_INVALID_RESULT,
        maximum=0x100000000,
    )
    if entry & 3 or code_start & 3 or code_end & 3:
        raise LoweringError(LOWER_INVALID_RESULT, "Entry and code bounds must be 4-byte aligned")
    if code_start >= code_end:
        raise LoweringError(LOWER_INVALID_RESULT, "Code range must be non-empty")
    if code_end > 0x100000000:
        raise LoweringError(LOWER_INVALID_RESULT, "Code range exceeds the 32-bit address space")
    if (code_end - code_start) % 4:
        raise LoweringError(LOWER_INVALID_RESULT, "Code range is not a multiple of one instruction")
    instruction_count = (code_end - code_start) // 4
    if instruction_count > MAX_LOWER_INSTRUCTIONS:
        raise LoweringError(LOWER_LIMIT_EXCEEDED, f"Code range exceeds the {MAX_LOWER_INSTRUCTIONS}-instruction limit")

    raw_instructions = _read(result, "instructions", LOWER_INVALID_RESULT)
    if not isinstance(raw_instructions, (tuple, list)):
        raise LoweringError(LOWER_INVALID_RESULT, "Instructions must be a tuple or list")
    instructions = tuple(raw_instructions)
    if len(instructions) != instruction_count:
        raise LoweringError(LOWER_INVALID_RESULT, "Instruction count does not match the code range")

    raw_blocks = _read(result, "blocks", LOWER_INVALID_RESULT)
    if not isinstance(raw_blocks, (tuple, list)):
        raise LoweringError(LOWER_INVALID_RESULT, "Blocks must be a tuple or list")
    blocks = tuple(raw_blocks)
    if not blocks:
        raise LoweringError(LOWER_INVALID_BLOCK, "Analysis result must contain at least one block")

    if not code_start <= entry < code_end:
        raise LoweringError(LOWER_INVALID_RESULT, "Entry point is outside the code range")
    return entry, code_start, code_end, instructions, blocks


def _validate_instruction(instruction: Any, expected_pc: int) -> tuple[str, str, int | None, int | None]:
    pc = _integer(
        _read(instruction, "pc", LOWER_MALFORMED_INSTRUCTION),
        "Instruction address",
        code=LOWER_MALFORMED_INSTRUCTION,
    )
    if pc != expected_pc:
        raise LoweringError(LOWER_MALFORMED_INSTRUCTION, "Instruction addresses are not contiguous and ordered", pc=pc)
    _integer(_read(instruction, "word", LOWER_MALFORMED_INSTRUCTION, pc=pc), "Raw word", code=LOWER_MALFORMED_INSTRUCTION, pc=pc)
    op = _read(instruction, "op", LOWER_MALFORMED_INSTRUCTION, pc=pc)
    if not isinstance(op, str) or op not in _SUPPORTED_OPS:
        raise LoweringError(LOWER_UNSUPPORTED_OP, f"Unsupported operation {op!r}", pc=pc)
    control = _read(instruction, "control", LOWER_MALFORMED_INSTRUCTION, pc=pc)
    if not isinstance(control, str) or control not in _CONTROLS:
        raise LoweringError(LOWER_INVALID_CONTROL, "Unknown control-flow classification", pc=pc)

    if op in {"addu", "and", "or", "xor", "nor", "slt", "sltu", "addiu", "slti", "andi", "ori", "xori", "lui", "lw", "sw", "beq", "bne", "jr"}:
        rs = _register(instruction, "rs", required=True)
    else:
        _expect_none(instruction, "rs")
        rs = None
    if op in {"addu", "and", "or", "xor", "nor", "slt", "sltu", "addiu", "slti", "andi", "ori", "xori", "lui", "lw", "sw", "beq", "bne"}:
        rt = _register(instruction, "rt", required=True)
    else:
        _expect_none(instruction, "rt")
        rt = None
    if op == "lui" and rs != 0:
        raise LoweringError(LOWER_MALFORMED_INSTRUCTION, "LUI requires rs=0", pc=pc)
    if op in _REGISTER_DEST_OPS:
        rd = _register(instruction, "rd", required=True)
    else:
        _expect_none(instruction, "rd")
        rd = None

    if op == "jr":
        expected_control = RETURN_CANDIDATE if rs == RA else INDIRECT_JUMP
    else:
        expected_control = _FIXED_CONTROLS[op]
    if control != expected_control:
        raise LoweringError(LOWER_INVALID_CONTROL, "Control-flow classification does not match the operation", pc=pc)

    if op in {"addiu", "slti", "lw", "sw", "beq", "bne"}:
        immediate_kind = SIGNED16
        minimum, maximum = -0x8000, 0x7FFF
    elif op in {"andi", "ori", "xori"}:
        immediate_kind = ZERO16
        minimum, maximum = 0, 0xFFFF
    elif op == "lui":
        immediate_kind = SHIFTED16
        minimum, maximum = 0, 0xFFFF
    else:
        immediate_kind = None
        minimum = maximum = 0

    immediate = _read(instruction, "immediate", LOWER_MALFORMED_INSTRUCTION, pc=pc)
    actual_kind = _read(instruction, "immediate_kind", LOWER_MALFORMED_INSTRUCTION, pc=pc)
    if immediate_kind is None:
        if immediate is not None or actual_kind is not None:
            raise LoweringError(LOWER_MALFORMED_INSTRUCTION, "Immediate fields must be absent for this operation", pc=pc)
    else:
        if actual_kind != immediate_kind:
            raise LoweringError(LOWER_MALFORMED_INSTRUCTION, "Immediate kind does not match the operation", pc=pc)
        immediate = _integer(
            immediate,
            "Immediate",
            code=LOWER_MALFORMED_INSTRUCTION,
            pc=pc,
            minimum=minimum,
            maximum=maximum,
        )

    if op in {"addiu", "slti", "andi", "ori", "xori", "lui", "lw"}:
        expected_destination = None if rt == 0 else rt
    elif op in _REGISTER_DEST_OPS:
        expected_destination = None if rd == 0 else rd
    elif op == "jal":
        expected_destination = RA
    else:
        expected_destination = None
    destination = _optional_integer(
        _read(instruction, "destination_register", LOWER_MALFORMED_INSTRUCTION, pc=pc),
        "Destination register",
        code=LOWER_MALFORMED_INSTRUCTION,
        pc=pc,
        maximum=31,
    )
    if destination != expected_destination:
        raise LoweringError(LOWER_MALFORMED_INSTRUCTION, "Destination register does not match the operation", pc=pc)

    target = _optional_integer(
        _read(instruction, "target", LOWER_MALFORMED_INSTRUCTION, pc=pc),
        "Control-flow target",
        code=LOWER_MALFORMED_INSTRUCTION,
        pc=pc,
    )
    if control in _DIRECT_CONTROLS:
        if target is None:
            raise LoweringError(LOWER_INVALID_TARGET, "Direct control transfer has no target", pc=pc)
    elif target is not None:
        raise LoweringError(LOWER_MALFORMED_INSTRUCTION, "A non-direct transfer must not have a static target", pc=pc)

    _optional_integer(
        _read(instruction, "delay_slot_for", LOWER_MALFORMED_INSTRUCTION, pc=pc),
        "Delay-slot owner",
        code=LOWER_INVALID_DELAY_SLOT,
        pc=pc,
    )
    return op, control, immediate, target


def _validate_delay_slots(instructions: tuple[Any, ...]) -> tuple[dict[int, int], tuple[Any, ...]]:
    by_pc = {instruction.pc: instruction for instruction in instructions}
    transfers = tuple(instruction for instruction in instructions if instruction.control != FALLTHROUGH)
    delay_slots: dict[int, int] = {}
    for transfer in transfers:
        slot_pc = transfer.pc + 4
        slot = by_pc.get(slot_pc)
        if slot is None:
            raise LoweringError(LOWER_INVALID_DELAY_SLOT, "Control transfer has no instruction in its delay slot", pc=transfer.pc)
        if slot.control != FALLTHROUGH:
            raise LoweringError(LOWER_INVALID_DELAY_SLOT, "Control transfer appears in a delay slot", pc=slot_pc)
        if slot.delay_slot_for != transfer.pc:
            raise LoweringError(LOWER_INVALID_DELAY_SLOT, "Delay slot does not identify its transfer", pc=slot_pc)
        delay_slots[slot_pc] = transfer.pc

    for instruction in instructions:
        if instruction.pc in delay_slots:
            continue
        if instruction.delay_slot_for is not None:
            raise LoweringError(LOWER_INVALID_DELAY_SLOT, "Instruction claims a delay slot without an owning transfer", pc=instruction.pc)
    return delay_slots, transfers


def _validate_targets(
    code_start: int,
    code_end: int,
    by_pc: dict[int, Any],
    delay_slots: dict[int, int],
    transfers: tuple[Any, ...],
) -> None:
    for transfer in transfers:
        if transfer.control in _DIRECT_CONTROLS:
            target = transfer.target
            if target is None:
                raise LoweringError(LOWER_INVALID_TARGET, "Direct control transfer has no target", pc=transfer.pc)
            if target & 3:
                raise LoweringError(LOWER_INVALID_TARGET, "Control-flow target is not 4-byte aligned", pc=target)
            if not code_start <= target < code_end or target not in by_pc:
                raise LoweringError(LOWER_INVALID_TARGET, "Control-flow target is outside the code range", pc=target)
            if target in delay_slots:
                raise LoweringError(LOWER_INVALID_TARGET, "Control-flow target points into a delay slot", pc=target)
        if transfer.control == CONDITIONAL_BRANCH:
            fallthrough = (transfer.pc + 8) & 0xFFFFFFFF
            if fallthrough not in by_pc:
                raise LoweringError(LOWER_INVALID_TARGET, "Conditional fallthrough is outside the code range", pc=transfer.pc)
            if fallthrough in delay_slots:
                raise LoweringError(LOWER_INVALID_TARGET, "Conditional fallthrough points into a delay slot", pc=transfer.pc)


def _validate_blocks(
    entry: int,
    code_start: int,
    code_end: int,
    instructions: tuple[Any, ...],
    blocks: tuple[Any, ...],
    by_pc: dict[int, Any],
    delay_slots: dict[int, int],
    transfers: tuple[Any, ...],
) -> None:
    expected_starts = {code_start, entry}
    for transfer in transfers:
        if transfer.target is not None:
            expected_starts.add(transfer.target)
        if transfer.control == CONDITIONAL_BRANCH:
            expected_starts.add((transfer.pc + 8) & 0xFFFFFFFF)
        post_delay = (transfer.pc + 8) & 0xFFFFFFFF
        if post_delay in by_pc:
            expected_starts.add(post_delay)
    for start in expected_starts:
        if start not in by_pc:
            raise LoweringError(LOWER_INVALID_BLOCK, "Block start is outside the code range", pc=start)
        if start in delay_slots:
            raise LoweringError(LOWER_INVALID_BLOCK, "Block start points into a delay slot", pc=start)

    starts: list[int] = []
    previous_end = None
    for block in blocks:
        start = _integer(
            _read(block, "start_pc", LOWER_INVALID_BLOCK),
            "Block start",
            code=LOWER_INVALID_BLOCK,
        )
        end = _integer(
            _read(block, "end_pc", LOWER_INVALID_BLOCK),
            "Block end",
            code=LOWER_INVALID_BLOCK,
            maximum=0x100000000,
        )
        if start & 3 or end & 3:
            raise LoweringError(LOWER_INVALID_BLOCK, "Block bounds must be 4-byte aligned", pc=start)
        if start >= end or end > code_end:
            raise LoweringError(LOWER_INVALID_BLOCK, "Block range is invalid", pc=start)
        if previous_end is not None and start != previous_end:
            raise LoweringError(LOWER_INVALID_BLOCK, "Blocks are not contiguous and ordered", pc=start)
        previous_end = end
        starts.append(start)

        raw_block_instructions = _read(block, "instructions", LOWER_INVALID_BLOCK)
        if not isinstance(raw_block_instructions, (tuple, list)):
            raise LoweringError(LOWER_INVALID_BLOCK, "Block instructions must be a tuple or list", pc=start)
        block_instructions = tuple(raw_block_instructions)
        block_pcs = tuple(range(start, end, 4))
        if tuple(_read(item, "pc", LOWER_INVALID_BLOCK, pc=start) for item in block_instructions) != block_pcs:
            raise LoweringError(LOWER_INVALID_BLOCK, "Block instructions do not cover the block range", pc=start)
        if any(pc not in by_pc for pc in block_pcs):
            raise LoweringError(LOWER_INVALID_BLOCK, "Block contains an instruction outside the code range", pc=start)

        block_transfers = [by_pc[pc] for pc in block_pcs if by_pc[pc].control != FALLTHROUGH]
        if len(block_transfers) > 1:
            raise LoweringError(LOWER_INVALID_BLOCK, "Block contains more than one control transfer", pc=start)
        successors = _read(block, "successors", LOWER_INVALID_BLOCK)
        if not isinstance(successors, (tuple, list)):
            raise LoweringError(LOWER_INVALID_BLOCK, "Block successors must be a tuple or list", pc=start)
        successor_tuple = tuple(successors)
        if any(not isinstance(item, int) or isinstance(item, bool) for item in successor_tuple):
            raise LoweringError(LOWER_INVALID_BLOCK, "Block successor is not an integer", pc=start)
        if len(set(successor_tuple)) != len(successor_tuple):
            raise LoweringError(LOWER_INVALID_BLOCK, "Block successors contain duplicates", pc=start)

        if block_transfers:
            terminator = block_transfers[0]
            if end != terminator.pc + 8:
                raise LoweringError(LOWER_INVALID_BLOCK, "Control-transfer block does not end after its delay slot", pc=terminator.pc)
            if len(block_pcs) < 2 or block_pcs[-2] != terminator.pc or block_pcs[-1] not in delay_slots:
                raise LoweringError(LOWER_INVALID_BLOCK, "Control transfer is not followed only by its delay slot", pc=terminator.pc)
            if terminator.control == CONDITIONAL_BRANCH:
                fallthrough = (terminator.pc + 8) & 0xFFFFFFFF
                expected_successors = tuple(dict.fromkeys((terminator.target, fallthrough)))
            elif terminator.control in {DIRECT_JUMP, DIRECT_CALL}:
                expected_successors = (terminator.target,)
            else:
                expected_successors = ()
        else:
            expected_successors = (end,) if end < code_end else ()
        if successor_tuple != expected_successors:
            raise LoweringError(LOWER_INVALID_BLOCK, "Block successors do not match the control-flow contract", pc=start)

    if tuple(starts) != tuple(sorted(expected_starts)):
        raise LoweringError(LOWER_INVALID_BLOCK, "Block partition does not match the expected starts")
    if previous_end != code_end:
        raise LoweringError(LOWER_INVALID_BLOCK, "Block partition does not reach the code end")

    covered = tuple(
        pc
        for block in blocks
        for pc in range(
            _read(block, "start_pc", LOWER_INVALID_BLOCK),
            _read(block, "end_pc", LOWER_INVALID_BLOCK),
            4,
        )
    )
    if covered != tuple(instruction.pc for instruction in instructions):
        raise LoweringError(LOWER_INVALID_BLOCK, "Block partition does not cover every instruction exactly once")


def _validate(result: Any) -> tuple[int, int, int, tuple[Any, ...], dict[int, Any]]:
    entry, code_start, code_end, instructions, blocks = _validate_result_shape(result)
    for index, instruction in enumerate(instructions):
        _validate_instruction(instruction, code_start + index * 4)
    by_pc = {instruction.pc: instruction for instruction in instructions}
    delay_slots, transfers = _validate_delay_slots(instructions)
    _validate_targets(code_start, code_end, by_pc, delay_slots, transfers)
    _validate_blocks(entry, code_start, code_end, instructions, blocks, by_pc, delay_slots, transfers)
    return entry, code_start, code_end, instructions, by_pc


def _register_literal(index: int) -> str:
    return f"{index}u"


def _instruction_case(instruction: Any) -> list[str]:
    pc = instruction.pc
    op = instruction.op
    lines = [f"        case 0x{pc:08X}u:", "            s.trace.push_back(current_pc);"]
    if op == "nop":
        lines.append("            break;")
    elif op == "addiu":
        lines.append(
            f"            write_register(s, {_register_literal(instruction.rt)}, "
            f"addiu32(s.registers[{_register_literal(instruction.rs)}], {instruction.immediate}));"
        )
        lines.append("            break;")
    elif op == "addu":
        lines.append(
            f"            write_register(s, {_register_literal(instruction.rd)}, "
            f"addu32(s.registers[{_register_literal(instruction.rs)}], s.registers[{_register_literal(instruction.rt)}]));"
        )
        lines.append("            break;")
    elif op in {"and", "or", "xor"}:
        operator = {"and": "&", "or": "|", "xor": "^"}[op]
        lines.append(
            f"            write_register(s, {_register_literal(instruction.rd)}, "
            f"s.registers[{_register_literal(instruction.rs)}] {operator} s.registers[{_register_literal(instruction.rt)}]);"
        )
        lines.append("            break;")
    elif op == "nor":
        lines.append(
            f"            write_register(s, {_register_literal(instruction.rd)}, "
            f"~(s.registers[{_register_literal(instruction.rs)}] | s.registers[{_register_literal(instruction.rt)}]));"
        )
        lines.append("            break;")
    elif op in {"slt", "sltu"}:
        lines.append(
            f"            write_register(s, {_register_literal(instruction.rd)}, "
            f"{op}64(s.registers[{_register_literal(instruction.rs)}], s.registers[{_register_literal(instruction.rt)}]));"
        )
        lines.append("            break;")
    elif op == "slti":
        lines.append(
            f"            write_register(s, {_register_literal(instruction.rt)}, "
            f"slt64(s.registers[{_register_literal(instruction.rs)}], "
            f"static_cast<std::uint64_t>(static_cast<std::int64_t>({instruction.immediate}))));"
        )
        lines.append("            break;")
    elif op in {"andi", "ori", "xori"}:
        lines.append(
            f"            write_register(s, {_register_literal(instruction.rt)}, "
            f"{op}32(s.registers[{_register_literal(instruction.rs)}], 0x{instruction.immediate:04X}u));"
        )
        lines.append("            break;")
    elif op == "lui":
        lines.append(
            f"            write_register(s, {_register_literal(instruction.rt)}, "
            f"lui32(0x{instruction.immediate:04X}u));"
        )
        lines.append("            break;")
    elif op == "lw":
        lines.append(
            f"            write_register(s, {_register_literal(instruction.rt)}, "
            f"load_word(s, effective_address(s.registers[{_register_literal(instruction.rs)}], {instruction.immediate})));"
        )
        lines.append("            break;")
    elif op == "sw":
        lines.append(
            f"            store_word(s, effective_address(s.registers[{_register_literal(instruction.rs)}], "
            f"{instruction.immediate}), static_cast<std::uint32_t>(s.registers[{_register_literal(instruction.rt)}]));"
        )
        lines.append("            break;")
    elif op in {"beq", "bne"}:
        comparison = "==" if op == "beq" else "!="
        lines.append(
            f"            new_pending = true; new_target = (s.registers[{_register_literal(instruction.rs)}] "
            f"{comparison} s.registers[{_register_literal(instruction.rt)}]) ? 0x{instruction.target:08X}u "
            ": static_cast<std::uint32_t>(current_pc + 8u);"
        )
        lines.append("            break;")
    elif op == "j":
        lines.append(f"            new_pending = true; new_target = 0x{instruction.target:08X}u;")
        lines.append("            break;")
    elif op == "jal":
        lines.append(f"            write_register(s, {_register_literal(RA)}, static_cast<std::uint64_t>(current_pc + 8u));")
        lines.append(f"            new_pending = true; new_target = 0x{instruction.target:08X}u;")
        lines.append("            break;")
    elif op == "jr":
        lines.append(
            f"            new_pending = true; new_target = static_cast<std::uint32_t>(s.registers[{_register_literal(instruction.rs)}]);"
        )
        lines.append("            break;")
    else:
        raise LoweringError(LOWER_UNSUPPORTED_OP, f"Cannot emit unsupported operation {op!r}", pc=pc)
    return lines


def lower_to_cpp(
    result: Any,
    *,
    return_sentinel: int = DEFAULT_RETURN_SENTINEL,
    max_steps: int = DEFAULT_MAX_STEPS,
) -> str:
    """Lower a validated analysis result to deterministic C++20 source."""
    sentinel, step_limit = _prepare_options(return_sentinel, max_steps)
    entry, _code_start, _code_end, instructions, _by_pc = _validate(result)

    cases: list[str] = []
    for instruction in instructions:
        cases.extend(_instruction_case(instruction))
    body = "\n".join(cases)
    logical_helpers = []
    for op_name, operator in (("andi", "&"), ("ori", "|"), ("xori", "^")):
        if any(instruction.op == op_name for instruction in instructions):
            logical_helpers.append(
                f"std::uint64_t {op_name}32(std::uint64_t lhs, std::uint32_t immediate) {{\n"
                f"    return lhs {operator} static_cast<std::uint64_t>(immediate);\n"
                "}\n\n"
            )
    logical_helper = "".join(logical_helpers)
    lui_helper = (
        "std::uint64_t lui32(std::uint32_t immediate) {\n"
        "    return sign_extend_32(static_cast<std::uint32_t>(immediate << 16));\n"
        "}\n\n"
    ) if any(instruction.op == "lui" for instruction in instructions) else ""
    comparison_helpers = []
    if any(instruction.op in {"slt", "slti"} for instruction in instructions):
        comparison_helpers.append(
            "std::uint64_t slt64(std::uint64_t lhs, std::uint64_t rhs) {\n"
            "    const bool lhs_negative = (lhs & 0x8000000000000000ull) != 0ull;\n"
            "    const bool rhs_negative = (rhs & 0x8000000000000000ull) != 0ull;\n"
            "    if (lhs_negative != rhs_negative) return lhs_negative ? 1ull : 0ull;\n"
            "    return lhs < rhs ? 1ull : 0ull;\n"
            "}\n\n"
        )
    if any(instruction.op == "sltu" for instruction in instructions):
        comparison_helpers.append(
            "std::uint64_t sltu64(std::uint64_t lhs, std::uint64_t rhs) {\n"
            "    return lhs < rhs ? 1ull : 0ull;\n"
            "}\n\n"
        )
    comparison_helper = "".join(comparison_helpers)

    return f'''// Generated by tools/rptp_lower.py from validated RPTP IR. Do not edit by hand.
// Synthetic instruction subset only; not a complete R5900 implementation.
#include <array>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <map>
#include <stdexcept>
#include <vector>

struct State {{
    std::array<std::uint64_t, 32> registers{{}};
    std::map<std::uint32_t, std::uint32_t> memory;
    std::vector<std::uint32_t> trace;
    std::uint32_t pc = 0x{entry:08X}u;
    bool halted = false;
}};

std::uint64_t sign_extend_32(std::uint32_t value) {{
    const std::int64_t signed_value = (value & 0x80000000u) != 0u
        ? static_cast<std::int64_t>(value) - 0x100000000ll
        : static_cast<std::int64_t>(value);
    return static_cast<std::uint64_t>(signed_value);
}}

std::uint64_t addiu32(std::uint64_t lhs, std::int32_t immediate) {{
    const auto value = static_cast<std::uint32_t>(lhs) + static_cast<std::uint32_t>(immediate);
    return sign_extend_32(value);
}}

std::uint64_t addu32(std::uint64_t lhs, std::uint64_t rhs) {{
    const auto value = static_cast<std::uint32_t>(lhs) + static_cast<std::uint32_t>(rhs);
    return sign_extend_32(value);
}}

{logical_helper}{lui_helper}{comparison_helper}std::uint32_t effective_address(std::uint64_t base, std::int32_t offset) {{
    return static_cast<std::uint32_t>(static_cast<std::uint32_t>(base) + static_cast<std::uint32_t>(offset));
}}

void write_register(State& state, std::uint32_t index, std::uint64_t value) {{
    if (index != 0u) state.registers[index] = value;
}}

std::uint64_t load_word(const State& state, std::uint32_t address) {{
    const auto it = state.memory.find(address);
    if (it == state.memory.end()) throw std::runtime_error("read from uninitialized guest memory");
    return sign_extend_32(it->second);
}}

void store_word(State& state, std::uint32_t address, std::uint32_t value) {{
    state.memory[address] = value;
}}

void run_generated(State& s) {{
    bool pending = false;
    std::uint32_t pending_target = 0;
    for (std::size_t step = 0; step < {step_limit}u; ++step) {{
        const std::uint32_t current_pc = s.pc;
        const bool was_delay_slot = pending;
        const std::uint32_t delayed_target = pending_target;
        pending = false;
        bool new_pending = false;
        std::uint32_t new_target = 0;
        switch (current_pc) {{
{body}
        default:
            s.halted = true;
            return;
        }}
        s.registers[0] = 0;
        if (was_delay_slot) {{
            s.pc = delayed_target;
        }} else if (new_pending) {{
            s.pc = current_pc + 4u;
            pending = true;
            pending_target = new_target;
        }} else {{
            s.pc = current_pc + 4u;
        }}
    }}
    throw std::runtime_error("generated code exceeded the instruction limit");
}}

int main() {{
    try {{
        State state;
        state.pc = 0x{entry:08X}u;
        state.registers[31] = 0x{sentinel:08X}u;
        run_generated(state);
        std::cout << "{{\\\"halted\\\":" << (state.halted ? "true" : "false")
                  << ",\\\"pc\\\":" << state.pc
                  << ",\\\"registers\\\":[";
        for (std::size_t i = 0; i < state.registers.size(); ++i) {{
            if (i != 0u) std::cout << ',';
            std::cout << state.registers[i];
        }}
        std::cout << "],\\\"memory\\\":[";
        bool first_memory = true;
        for (const auto& item : state.memory) {{
            if (!first_memory) std::cout << ',';
            first_memory = false;
            std::cout << "[" << item.first << ',' << item.second << "]";
        }}
        std::cout << "],\\\"trace\\\":[";
        for (std::size_t i = 0; i < state.trace.size(); ++i) {{
            if (i != 0u) std::cout << ',';
            std::cout << state.trace[i];
        }}
        std::cout << "]}}\\n";
        return 0;
    }} catch (const std::exception& error) {{
        std::cerr << "LOWER_RUNTIME_ERROR: " << error.what() << '\\n';
        return 2;
    }}
}}
'''
