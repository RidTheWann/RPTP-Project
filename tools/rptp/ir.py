# SPDX-License-Identifier: GPL-3.0-or-later
"""Low-level RPTP IR and deterministic lowering from decoded R5900 code.

The IR makes the MIPS delay-slot contract explicit:

* ``ops`` execute in program order before the control transfer;
* ``control`` captures the branch condition, indirect target and link-register
  write using the register state *before* the delay slot;
* ``delay_ops`` execute after that capture;
* the next PC is selected only after ``delay_ops``.

For a branch-likely instruction the condition also controls ``delay_ops``:
they execute only when the branch is taken.  When it is not taken the model
nullifies them and continues at ``fallthrough``.  CFG successors are unchanged:
both the direct target and the fallthrough remain recorded.

Splitting these phases is what prevents the classic recompiler bug where the
delay slot overwrites a register that the branch was supposed to compare.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from .cfg import BasicBlock, Program
from .isa import Instruction, MASK64


class LoweringError(ValueError):
    """Raised when a decoded instruction has no IR lowering."""


@dataclass(frozen=True)
class IROp:
    kind: str
    pc: int
    mnemonic: str = ""
    dst: int | None = None
    a: int | None = None
    b: int | None = None
    imm: int | None = None
    width: int = 0
    signed: bool = False
    size: int = 0
    note: str = ""


@dataclass(frozen=True)
class Control:
    kind: str  # branch | jump | call | return | indirect | indirect_call | halt | unsupported
    pc: int
    mnemonic: str = ""
    cond: str = ""
    rs: int | None = None
    rt: int | None = None
    target: int | None = None
    fallthrough: int | None = None
    link_reg: int | None = None
    target_reg: int | None = None
    reason: str = ""
    likely: bool = False


@dataclass
class BlockIR:
    start: int
    ops: list[IROp]
    control: Control
    delay_ops: list[IROp]
    instructions: list[Instruction]
    delay_slot_pc: int | None = None


class LoweringResult:
    def __init__(self, blocks: dict[int, BlockIR], errors: list[str]) -> None:
        self.blocks = blocks
        self.errors = errors

    def reachable_unsupported(self, entry: int) -> list[str]:
        problems: list[str] = []
        seen: set[int] = set()
        stack = [entry]
        while stack:
            pc = stack.pop()
            if pc in seen:
                continue
            seen.add(pc)
            if pc not in self.blocks:
                problems.append(f"reachable address 0x{pc:08X} has no IR block")
                continue
            block = self.blocks[pc]
            if block.control.kind in {"halt", "unsupported"}:
                problems.append(f"block 0x{pc:08X}: {block.control.reason or block.control.kind}")
            for successor in block.control_successors():
                stack.append(successor)
        return problems


def _control_successors(self: BlockIR) -> list[int]:
    successors: list[int] = []
    if self.control.kind == "branch":
        if self.control.target is not None:
            successors.append(self.control.target)
        if self.control.fallthrough is not None:
            successors.append(self.control.fallthrough)
    elif self.control.kind in {"jump", "call"}:
        if self.control.target is not None:
            successors.append(self.control.target)
        if self.control.kind == "call" and self.control.fallthrough is not None:
            successors.append(self.control.fallthrough)
    elif self.control.kind == "indirect_call" and self.control.fallthrough is not None:
        successors.append(self.control.fallthrough)
    return successors


BlockIR.control_successors = _control_successors  # type: ignore[attr-defined]


def _lower_instruction(instruction: Instruction) -> IROp:
    mnemonic = instruction.mnemonic
    pc = instruction.pc
    cls = instruction.cls
    if mnemonic in {"nop", "sync", "cache", "pref"}:
        return IROp("nop", pc, mnemonic=mnemonic)
    if mnemonic == "lui":
        return IROp("lui", pc, mnemonic="lui", dst=instruction.rt, imm=instruction.imm)
    if mnemonic in {"addiu", "daddiu", "slti", "sltiu", "andi", "ori", "xori"}:
        width = 64 if mnemonic == "daddiu" else 32
        return IROp("imm_op", pc, mnemonic=mnemonic, dst=instruction.rt,
                    a=instruction.rs, imm=instruction.simm if mnemonic not in
                    {"andi", "ori", "xori"} else instruction.imm, width=width,
                    signed=mnemonic in {"slti", "sltiu"})
    if mnemonic in {"addu", "daddu", "subu", "dsubu", "and", "or", "xor", "nor",
                    "slt", "sltu", "movz", "movn"}:
        width = 64 if mnemonic.startswith("d") else 32
        return IROp("reg_op", pc, mnemonic=mnemonic, dst=instruction.rd,
                    a=instruction.rs, b=instruction.rt, width=width,
                    signed=mnemonic in {"slt", "sltu"})
    if mnemonic in {"add", "dadd", "sub", "dsub"}:
        width = 64 if mnemonic.startswith("d") else 32
        return IROp("checked_arith", pc, mnemonic=mnemonic, dst=instruction.rd,
                    a=instruction.rs, b=instruction.rt, width=width)
    if mnemonic in {"sll", "srl", "sra"}:
        return IROp("shift", pc, mnemonic=mnemonic, dst=instruction.rd,
                    a=instruction.rt, imm=instruction.shamt, width=32)
    if mnemonic in {"dsll", "dsrl", "dsra"}:
        return IROp("shift", pc, mnemonic=mnemonic, dst=instruction.rd,
                    a=instruction.rt, imm=instruction.shamt, width=64)
    if mnemonic in {"dsll32", "dsrl32", "dsra32"}:
        return IROp("shift", pc, mnemonic=mnemonic, dst=instruction.rd,
                    a=instruction.rt, imm=(instruction.shamt or 0) + 32, width=64)
    if mnemonic in {"sllv", "srlv", "srav"}:
        return IROp("shift_var", pc, mnemonic=mnemonic, dst=instruction.rd,
                    a=instruction.rt, b=instruction.rs, width=32)
    if mnemonic in {"dsllv", "dsrlv", "dsrav"}:
        return IROp("shift_var", pc, mnemonic=mnemonic, dst=instruction.rd,
                    a=instruction.rt, b=instruction.rs, width=64)
    if mnemonic in {"mfhi", "mflo", "mfhi1", "mflo1"}:
        return IROp("read_hi_lo", pc, mnemonic=mnemonic, dst=instruction.rd)
    if mnemonic in {"mthi", "mtlo", "mthi1", "mtlo1"}:
        return IROp("write_hi_lo", pc, mnemonic=mnemonic, a=instruction.rs)
    if mnemonic in {"mult", "multu", "div", "divu", "madd", "maddu",
                    "mult1", "multu1", "div1", "divu1", "madd1", "maddu1"}:
        return IROp("muldiv", pc, mnemonic=mnemonic, dst=instruction.rd,
                    a=instruction.rs, b=instruction.rt)
    if mnemonic == "mfc1":
        return IROp("fpr_read", pc, mnemonic=mnemonic, dst=instruction.rt,
                    a=instruction.rd)
    if mnemonic == "mtc1":
        return IROp("fpr_write", pc, mnemonic=mnemonic, dst=instruction.rd,
                    a=instruction.rt)
    if mnemonic == "lwc1":
        return IROp("cop1_load", pc, mnemonic=mnemonic, dst=instruction.rt,
                    a=instruction.rs, imm=instruction.simm, size=4)
    if mnemonic == "swc1":
        return IROp("cop1_store", pc, mnemonic=mnemonic, a=instruction.rs,
                    b=instruction.rt, imm=instruction.simm, size=4)
    if cls == "load":
        size = {"lb": 1, "lbu": 1, "lh": 2, "lhu": 2, "lw": 4, "lwu": 4,
                "ld": 8, "lq": 16}.get(mnemonic)
        if size is None:
            raise LoweringError(f"No load width for {mnemonic} at 0x{pc:08X}")
        return IROp("load", pc, mnemonic=mnemonic, dst=instruction.rt, a=instruction.rs,
                    imm=instruction.simm, size=size,
                    signed=mnemonic in {"lb", "lh", "lw", "ld"})
    if cls == "store":
        size = {"sb": 1, "sh": 2, "sw": 4, "sd": 8, "sq": 16}.get(mnemonic)
        if size is None:
            raise LoweringError(f"No store width for {mnemonic} at 0x{pc:08X}")
        return IROp("store", pc, mnemonic=mnemonic, a=instruction.rs, b=instruction.rt,
                    imm=instruction.simm, size=size)
    if cls == "mmi":
        if mnemonic in {"psllh", "psrlh", "psrah", "psllw", "psrlw", "psraw"}:
            width = 16 if mnemonic.endswith("h") else 32
            return IROp("mmi_shift", pc, mnemonic=mnemonic, dst=instruction.rd,
                        a=instruction.rt, imm=instruction.shamt, width=width)
        return IROp("mmi", pc, mnemonic=mnemonic, dst=instruction.rd,
                    a=instruction.rs, b=instruction.rt)
    raise LoweringError(
        f"No IR lowering for {instruction.text()} ({mnemonic}) at 0x{pc:08X}")


def _branch_condition(instruction: Instruction) -> str:
    return {
        "beq": "eq", "bne": "ne",
        "blez": "le", "bgtz": "gt",
        "bltz": "lt", "bgez": "ge",
        "bltzal": "lt", "bgezal": "ge",
        "beql": "eq", "bnel": "ne",
        "blezl": "le", "bgtzl": "gt",
        "bltzl": "lt", "bgezl": "ge",
        "bltzall": "lt", "bgezall": "ge",
    }[instruction.mnemonic]


def lower_block(block: BasicBlock) -> BlockIR:
    if block.kind == "unsupported":
        raise LoweringError(f"Block 0x{block.start:08X} is unsupported: {block.problem}")
    if block.kind == "halt":
        ops: list[IROp] = []
        halt_pc = block.start
        for instruction in block.instructions:
            if instruction.is_halt:
                halt_pc = instruction.pc
                break
            ops.append(_lower_instruction(instruction))
        reason = block.problem or (block.terminator.mnemonic if block.terminator else "halt")
        return BlockIR(block.start, ops, Control("halt", halt_pc, reason=reason),
                       [], list(block.instructions), block.delay_slot_pc)
    if block.kind == "fallthrough":
        ops = [_lower_instruction(instruction) for instruction in block.instructions]
        target = block.successors[0] if block.successors else None
        return BlockIR(block.start, ops, Control("jump", block.start, target=target),
                       [], list(block.instructions), block.delay_slot_pc)

    control_index = None
    for index, instruction in enumerate(block.instructions):
        if instruction.is_control:
            control_index = index
            break
    if control_index is None:
        raise LoweringError(f"Block 0x{block.start:08X} has no control transfer")
    control_instruction = block.instructions[control_index]
    delay_instruction = None
    if control_index + 1 < len(block.instructions):
        if control_index + 2 != len(block.instructions):
            raise LoweringError(f"Block 0x{block.start:08X} has extra instructions after its delay slot")
        delay_instruction = block.instructions[control_index + 1]
    pre_instructions = block.instructions[:control_index]
    ops = [_lower_instruction(instruction) for instruction in pre_instructions]
    delay_ops = [_lower_instruction(delay_instruction)] if delay_instruction is not None else []

    mnemonic = control_instruction.mnemonic
    next_pc = (control_instruction.pc + 8) & 0xFFFFFFFF
    link_reg: int | None = None
    if mnemonic in {"bltzal", "bgezal", "bltzall", "bgezall"}:
        link_reg = 31
    control = Control(
        kind="unsupported",
        pc=control_instruction.pc,
        mnemonic=mnemonic,
        target=control_instruction.target,
        fallthrough=next_pc,
        link_reg=link_reg,
    )
    if mnemonic in {"beq", "bne", "blez", "bgtz", "bltz", "bgez", "bltzal", "bgezal",
                    "beql", "bnel", "blezl", "bgtzl", "bltzl", "bgezl",
                    "bltzall", "bgezall"}:
        control = Control(
            kind="branch", pc=control_instruction.pc, mnemonic=mnemonic,
            cond=_branch_condition(control_instruction),
            rs=control_instruction.rs, rt=control_instruction.rt,
            target=(control_instruction.target
                    if control_instruction.target is not None else next_pc),
            fallthrough=next_pc,
            link_reg=link_reg,
            likely=control_instruction.is_likely,
        )
    elif mnemonic == "j":
        control = Control("jump", control_instruction.pc, mnemonic=mnemonic,
                          target=control_instruction.target)
    elif mnemonic == "jal":
        control = Control("call", control_instruction.pc, mnemonic=mnemonic,
                          target=control_instruction.target, fallthrough=next_pc,
                          link_reg=31)
    elif mnemonic == "jr":
        if control_instruction.rs == 31:
            control = Control("return", control_instruction.pc, mnemonic=mnemonic,
                              target_reg=31)
        else:
            control = Control("indirect", control_instruction.pc, mnemonic=mnemonic,
                              target_reg=control_instruction.rs)
    elif mnemonic == "jalr":
        rd = control_instruction.rd or 0
        kind = "indirect_call" if rd == 31 and control_instruction.rs != 31 else "indirect"
        control = Control(kind, control_instruction.pc, mnemonic=mnemonic,
                          target_reg=control_instruction.rs, fallthrough=next_pc,
                          link_reg=rd if rd else None)
    else:
        raise LoweringError(f"No control lowering for {control_instruction.text()} at 0x{control_instruction.pc:08X}")

    return BlockIR(block.start, ops, control, delay_ops,
                   list(block.instructions), block.delay_slot_pc)


def lower_program(program: Program, block_starts: Iterable[int] | None = None) -> LoweringResult:
    errors: list[str] = []
    blocks: dict[int, BlockIR] = {}
    selected = sorted(program.blocks) if block_starts is None else sorted(set(block_starts))
    for start in selected:
        if start not in program.blocks:
            errors.append(f"No CFG block at 0x{start:08X}")
            continue
        try:
            blocks[start] = lower_block(program.blocks[start])
        except LoweringError as exc:
            errors.append(str(exc))
    return LoweringResult(blocks, errors)
