# SPDX-License-Identifier: GPL-3.0-or-later
"""Reference interpreter ("oracle") for differential recompiler testing.

The oracle deliberately shares no code with the C++ emitter: it executes the
decoded instruction stream directly in Python, while the emitter lowers the
same stream through the IR to C++ helpers.  The two implementations are then
compared on registers, HI/LO, memory writes and the executed-PC trace.

Scope: the instruction subset listed in ``isa.SUPPORTED_MNEMONICS``.  PS2
kernel calls, COP0/COP1/COP2, VU, GS, IOP, interrupts and hardware timing are
not modelled.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .cfg import Program
from .elf import ElfImage
from .isa import (
    Instruction,
    MASK32,
    MASK64,
    MASK128,
    sign_extend,
)

RAM_SIZE = 0x02000000
RETURN_SENTINEL = 0x7FFF0000


class ExecutionError(RuntimeError):
    """Raised when the reference model cannot execute a guest instruction."""


def _sext128(value: int, bits: int) -> int:
    value &= (1 << bits) - 1
    if value & (1 << (bits - 1)):
        return value | (MASK128 ^ ((1 << bits) - 1))
    return value


def _physical(address: int) -> int:
    value = address & MASK32
    if 0x80000000 <= value < 0xA0000000:
        value -= 0x80000000
    elif 0xA0000000 <= value < 0xC0000000:
        value -= 0xA0000000
    return value


class GuestMemory:
    """Sparse 32 MiB EE main-RAM model with default-zero reads."""

    def __init__(self, initial: dict[int, int] | None = None) -> None:
        self.bytes: dict[int, int] = dict(initial or {})
        self.writes: dict[int, int] = {}

    def _check(self, address: int, size: int) -> None:
        if address < 0 or size < 0 or address + size > RAM_SIZE:
            raise ExecutionError(
                f"guest memory access 0x{address:08X}+{size} is outside the modelled "
                f"{RAM_SIZE // (1024 * 1024)} MiB main RAM")

    def read(self, address: int, size: int, signed: bool = False) -> int:
        physical = _physical(address)
        self._check(physical, size)
        value = 0
        for offset in range(size):
            value |= self.bytes.get(physical + offset, 0) << (8 * offset)
        if signed:
            return sign_extend(value, size * 8)
        return value

    def write(self, address: int, size: int, value: int) -> None:
        physical = _physical(address)
        self._check(physical, size)
        for offset in range(size):
            byte = (value >> (8 * offset)) & 0xFF
            self.bytes[physical + offset] = byte
            self.writes[physical + offset] = byte

    def snapshot(self) -> list[list[int]]:
        return [[address, value] for address, value in sorted(self.writes.items())]


@dataclass
class State:
    registers: list[int] = field(default_factory=lambda: [0] * 32)
    hi: int = 0
    lo: int = 0
    hi1: int = 0
    lo1: int = 0
    pc: int = 0
    halted: bool = False
    reason: str = ""
    steps: int = 0
    trace: list[int] = field(default_factory=list)
    memory: GuestMemory = field(default_factory=GuestMemory)


def _mask_lane(value: int, width: int) -> int:
    return value & ((1 << width) - 1)


def lanes(value: int, width: int) -> list[int]:
    count = 128 // width
    mask = (1 << width) - 1
    return [(value >> (index * width)) & mask for index in range(count)]


def pack(values: list[int], width: int) -> int:
    mask = (1 << width) - 1
    result = 0
    for index, value in enumerate(values):
        result |= (value & mask) << (index * width)
    return result & MASK128


def _sat_signed(value: int, width: int) -> int:
    low = -(1 << (width - 1))
    high = (1 << (width - 1)) - 1
    return max(low, min(high, value)) & ((1 << width) - 1)


def _sat_unsigned(value: int, width: int) -> int:
    return max(0, min((1 << width) - 1, value))


def _mmi_binary(mnemonic: str, left: int, right: int) -> int:
    if mnemonic in {"pand", "por", "pxor", "pnor"}:
        if mnemonic == "pand":
            return left & right
        if mnemonic == "por":
            return left | right
        if mnemonic == "pxor":
            return (left ^ right) & MASK128
        return (~(left | right)) & MASK128
    if mnemonic in {"paddw", "psubw", "pcgtw", "pmaxw", "pminw", "pceqw"}:
        return _mmi_words(mnemonic, left, right, 32, 4)
    if mnemonic in {"paddh", "psubh", "pcgth", "pmaxh", "pminh", "pceqh"}:
        return _mmi_words(mnemonic.replace("paddh", "paddw").replace("psubh", "psubw")
                          .replace("pcgth", "pcgtw").replace("pmaxh", "pmaxw")
                          .replace("pminh", "pminw").replace("pceqh", "pceqw"),
                          left, right, 16, 8)
    if mnemonic in {"paddb", "psubb", "pcgtb", "pceqb"}:
        base = {"paddb": "paddw", "psubb": "psubw", "pcgtb": "pcgtw", "pceqb": "pceqw"}[mnemonic]
        return _mmi_words(base, left, right, 8, 16)
    if mnemonic in {"paddsw", "psubsw", "paddsh", "psubsh", "paddsb", "psubsb"}:
        width = 32 if mnemonic.endswith("sw") else (16 if mnemonic.endswith("sh") else 8)
        count = 128 // width
        a = lanes(left, width)
        b = lanes(right, width)
        if mnemonic.startswith("padd"):
            return pack([_sat_signed(sign_extend(x, width) + sign_extend(y, width), width)
                         for x, y in zip(a, b)], width)
        return pack([_sat_signed(sign_extend(x, width) - sign_extend(y, width), width)
                     for x, y in zip(a, b)], width)
    if mnemonic in {"padduw", "psubuw", "padduh", "psubuh", "paddub", "psubub"}:
        width = 32 if mnemonic.endswith("uw") else (16 if mnemonic.endswith("uh") else 8)
        a = lanes(left, width)
        b = lanes(right, width)
        if mnemonic.startswith("padd"):
            return pack([_sat_unsigned(x + y, width) for x, y in zip(a, b)], width)
        return pack([_sat_unsigned(x - y, width) for x, y in zip(a, b)], width)
    if mnemonic in {"pextlw", "pextuw", "pextlh", "pextuh", "pextlb", "pextub"}:
        width = 32 if mnemonic.endswith("w") else (16 if mnemonic.endswith("h") else 8)
        half = 64 // width
        all_a = lanes(left, width)
        all_b = lanes(right, width)
        start = 0 if mnemonic[4] == "l" else half
        out: list[int] = []
        for index in range(half):
            out.append(all_a[start + index])
            out.append(all_b[start + index])
        return pack(out, width)
    raise ExecutionError(f"MMI helper has no implementation for {mnemonic}")


def _mmi_words(mnemonic: str, left: int, right: int, width: int, count: int) -> int:
    a = lanes(left, width)
    b = lanes(right, width)
    out: list[int] = []
    mask = (1 << width) - 1
    for x, y in zip(a, b):
        if mnemonic == "paddw":
            out.append((x + y) & mask)
        elif mnemonic == "psubw":
            out.append((x - y) & mask)
        elif mnemonic == "pcgtw":
            out.append(mask if sign_extend(x, width) > sign_extend(y, width) else 0)
        elif mnemonic == "pmaxw":
            out.append(x if sign_extend(x, width) >= sign_extend(y, width) else y)
        elif mnemonic == "pminw":
            out.append(x if sign_extend(x, width) <= sign_extend(y, width) else y)
        elif mnemonic == "pceqw":
            out.append(mask if x == y else 0)
        else:
            raise ExecutionError(f"unknown MMI word op {mnemonic}")
    return pack(out, width)


def _mmi_unary(mnemonic: str, value: int) -> int:
    if mnemonic == "pabsw":
        width = 32
    elif mnemonic == "pabsh":
        width = 16
    else:
        raise ExecutionError(f"unknown MMI unary op {mnemonic}")
    out: list[int] = []
    mask = (1 << width) - 1
    low = -(1 << (width - 1))
    for lane in lanes(value, width):
        signed = sign_extend(lane, width)
        out.append(mask if signed == low else abs(signed))
    return pack(out, width)


def _mmi_shift(mnemonic: str, value: int, sa: int) -> int:
    width = 16 if mnemonic.endswith("h") else 32
    shift = sa & (0xF if width == 16 else 0x1F)
    mask = (1 << width) - 1
    out: list[int] = []
    for lane in lanes(value, width):
        if mnemonic.startswith("psll"):
            result = lane << shift
        elif mnemonic.startswith("psrl"):
            result = lane >> shift
        else:
            result = sign_extend(lane, width) >> shift
        out.append(result & mask)
    return pack(out, width)


def _write_s32(state: State, register: int, value: int) -> None:
    if register:
        state.registers[register] = _sext128(value & MASK32, 32)


def _write_s64(state: State, register: int, value: int) -> None:
    if register:
        state.registers[register] = _sext128(value & MASK64, 64)


def _write_u32(state: State, register: int, value: int) -> None:
    if register:
        state.registers[register] = value & MASK32


def _write_128(state: State, register: int, value: int) -> None:
    if register:
        state.registers[register] = value & MASK128


def _signed64(value: int) -> int:
    return sign_extend(value & MASK64, 64)


def _sext64(value: int) -> int:
    return sign_extend(value & MASK64, 64)


def _trunc_div(left: int, right: int) -> int:
    quotient = abs(left) // abs(right)
    return -quotient if (left < 0) != (right < 0) else quotient


def _signed32(value: int) -> int:
    return sign_extend(value & MASK32, 32)


class Oracle:
    def __init__(self, program: Program, *, max_steps: int = 100_000,
                 initial_registers: dict[int, int] | None = None,
                 return_sentinel: int = RETURN_SENTINEL) -> None:
        self.program = program
        initial, _ranges = program.image.initial_memory()
        self.state = State(memory=GuestMemory(initial))
        self.state.registers[31] = return_sentinel
        if initial_registers:
            for register, value in initial_registers.items():
                if not 0 <= register < 32:
                    raise ValueError(f"Invalid initial register index {register}")
                self.state.registers[register] = value & MASK128
        self.state.registers[0] = 0
        self.state.pc = program.entry
        self.max_steps = max_steps
        self.return_sentinel = return_sentinel

    def run(self) -> State:
        state = self.state
        while not state.halted:
            if state.steps >= self.max_steps:
                state.halted = True
                state.reason = "step_limit"
                break
            block = self.program.blocks.get(state.pc)
            if block is None:
                state.halted = True
                state.reason = "pc_outside_code"
                break
            if not block.supported:
                terminator = block.terminator
                raise ExecutionError(
                    f"Execution reached unsupported block 0x{block.start:08X} "
                    f"({block.problem or (terminator.text() if terminator else 'unknown')})")
            self._execute_block(block)
        return state

    def _execute_block(self, block) -> None:
        state = self.state
        instructions = block.instructions
        # Locate the control instruction (second-to-last only when it has a delay slot).
        control_index = None
        for index, instruction in enumerate(instructions):
            if instruction.is_control:
                control_index = index
                break
        pre = instructions if control_index is None else instructions[:control_index]
        control = None if control_index is None else instructions[control_index]
        delay = None
        if control is not None and control_index + 1 < len(instructions):
            delay = instructions[control_index + 1]

        # The model only executes blocks whose full instruction stream is supported.
        for instruction in pre:
            state.trace.append(instruction.pc)
            state.steps += 1
            if not self._execute_instruction(instruction):
                return

        if control is None:
            # A fall-through/split block: no control instruction.
            state.pc = (block.start + 4 * len(instructions)) & MASK32
            return

        state.trace.append(control.pc)
        state.steps += 1
        mnemonic = control.mnemonic
        if mnemonic in {"syscall", "break", "eret"}:
            state.halted = True
            state.reason = mnemonic
            state.pc = control.pc
            return
        if mnemonic in {"beq", "bne", "blez", "bgtz", "bltz", "bgez", "bltzal", "bgezal"}:
            take = self._branch_taken(control)
            if mnemonic in {"bltzal", "bgezal"} and state.registers:
                _write_u32(state, 31, (control.pc + 8) & MASK32)
            next_pc = (control.target or 0) if take else ((control.pc + 8) & MASK32)
        elif mnemonic == "j":
            next_pc = control.target or 0
        elif mnemonic == "jal":
            _write_u32(state, 31, (control.pc + 8) & MASK32)
            next_pc = control.target or 0
        elif mnemonic == "jr":
            next_pc = state.registers[control.rs or 0] & MASK32
        elif mnemonic == "jalr":
            next_pc = state.registers[control.rs or 0] & MASK32
            if control.rd:
                _write_u32(state, control.rd, (control.pc + 8) & MASK32)
        else:
            raise ExecutionError(f"Oracle has no control lowering for {control.text()}")
        state.registers[0] = 0

        if delay is not None:
            state.trace.append(delay.pc)
            state.steps += 1
            if not self._execute_instruction(delay):
                return
        state.pc = next_pc & MASK32
        state.registers[0] = 0

    def _branch_taken(self, control: Instruction) -> bool:
        regs = self.state.registers
        mnemonic = control.mnemonic
        rs = regs[control.rs or 0] & MASK64
        rt = regs[control.rt or 0] & MASK64
        if mnemonic == "beq":
            return rs == rt
        if mnemonic == "bne":
            return rs != rt
        if mnemonic == "blez":
            return _signed64(rs) <= 0
        if mnemonic == "bgtz":
            return _signed64(rs) > 0
        if mnemonic in {"bltz", "bltzal"}:
            return _signed64(rs) < 0
        if mnemonic in {"bgez", "bgezal"}:
            return _signed64(rs) >= 0
        raise ExecutionError(f"Unknown branch {mnemonic}")

    def _effective_address(self, instruction: Instruction) -> int:
        base = self.state.registers[instruction.rs or 0]
        return _physical((base + (instruction.simm or 0)) & MASK64)

    def _execute_instruction(self, instruction: Instruction) -> bool:
        state = self.state
        regs = state.registers
        m = instruction.mnemonic
        try:
            if m in {"nop", "sync", "cache", "pref"}:
                pass
            elif m == "lui":
                _write_s32(state, instruction.rt or 0, (instruction.imm or 0) << 16)
            elif m == "addiu":
                _write_s32(state, instruction.rt or 0,
                           (regs[instruction.rs or 0] & MASK32) + (instruction.simm or 0))
            elif m == "daddiu":
                _write_s64(state, instruction.rt or 0,
                           (regs[instruction.rs or 0] & MASK64) + (instruction.simm or 0))
            elif m == "slti":
                _write_s64(state, instruction.rt or 0,
                           1 if _signed64(regs[instruction.rs or 0]) < (instruction.simm or 0) else 0)
            elif m == "sltiu":
                _write_s64(state, instruction.rt or 0,
                           1 if (regs[instruction.rs or 0] & MASK64) < ((instruction.simm or 0) & MASK64) else 0)
            elif m == "andi":
                _write_s64(state, instruction.rt or 0,
                           (regs[instruction.rs or 0] & (instruction.imm or 0)) & MASK64)
            elif m == "ori":
                _write_s64(state, instruction.rt or 0,
                           (regs[instruction.rs or 0] | (instruction.imm or 0)) & MASK64)
            elif m == "xori":
                _write_s64(state, instruction.rt or 0,
                           (regs[instruction.rs or 0] ^ (instruction.imm or 0)) & MASK64)
            elif m == "addu":
                _write_s32(state, instruction.rd or 0,
                           (regs[instruction.rs or 0] & MASK32) + (regs[instruction.rt or 0] & MASK32))
            elif m == "daddu":
                _write_s64(state, instruction.rd or 0,
                           (regs[instruction.rs or 0] & MASK64) + (regs[instruction.rt or 0] & MASK64))
            elif m == "subu":
                _write_s32(state, instruction.rd or 0,
                           (regs[instruction.rs or 0] & MASK32) - (regs[instruction.rt or 0] & MASK32))
            elif m == "dsubu":
                _write_s64(state, instruction.rd or 0,
                           (regs[instruction.rs or 0] & MASK64) - (regs[instruction.rt or 0] & MASK64))
            elif m in {"add", "sub", "dadd", "dsub"}:
                width = 64 if m.startswith("d") else 32
                mask = (1 << width) - 1
                left = sign_extend(regs[instruction.rs or 0] & mask, width)
                right = sign_extend(regs[instruction.rt or 0] & mask, width)
                if m in {"add", "dadd"}:
                    result = left + right
                else:
                    result = left - right
                # The check must use the untruncated sum: 0x7FFFFFFF + 1 wraps to
                # INT32_MIN once masked, which a range check on the result misses.
                if not (-(1 << (width - 1)) <= result < (1 << (width - 1))):
                    state.halted = True
                    state.reason = "trap:integer_overflow"
                    state.pc = instruction.pc
                    return False
                if width == 32:
                    _write_s32(state, instruction.rd or 0, result)
                else:
                    _write_s64(state, instruction.rd or 0, result)
            elif m in {"and", "or", "xor", "nor"}:
                left = regs[instruction.rs or 0] & MASK64
                right = regs[instruction.rt or 0] & MASK64
                if m == "and":
                    result = left & right
                elif m == "or":
                    result = left | right
                elif m == "xor":
                    result = left ^ right
                else:
                    result = ~(left | right)
                _write_s64(state, instruction.rd or 0, result)
            elif m in {"slt", "sltu"}:
                left = regs[instruction.rs or 0] & MASK64
                right = regs[instruction.rt or 0] & MASK64
                if m == "slt":
                    result = _signed64(left) < _signed64(right)
                else:
                    result = left < right
                _write_s64(state, instruction.rd or 0, 1 if result else 0)
            elif m in {"movz", "movn"}:
                operand = regs[instruction.rt or 0] & MASK64
                condition = operand == 0 if m == "movz" else operand != 0
                if condition and instruction.rd:
                    regs[instruction.rd] = regs[instruction.rs or 0]
            elif m in {"sll", "srl", "sra"}:
                value = regs[instruction.rt or 0] & MASK32
                shift = instruction.shamt or 0
                if m == "sll":
                    result = value << shift
                elif m == "srl":
                    result = value >> shift
                else:
                    result = sign_extend(value, 32) >> shift
                _write_s32(state, instruction.rd or 0, result)
            elif m in {"dsll", "dsrl", "dsra", "dsll32", "dsrl32", "dsra32"}:
                value = regs[instruction.rt or 0] & MASK64
                shift = (instruction.shamt or 0) + (32 if m.endswith("32") else 0)
                base = m[:-2] if m.endswith("32") else m
                if base == "dsll":
                    result = value << shift
                elif base == "dsrl":
                    result = value >> shift
                else:
                    result = sign_extend(value, 64) >> shift
                _write_s64(state, instruction.rd or 0, result)
            elif m in {"sllv", "srlv", "srav", "dsllv", "dsrlv", "dsrav"}:
                width = 64 if m.startswith("d") else 32
                value = regs[instruction.rt or 0] & ((1 << width) - 1)
                shift = regs[instruction.rs or 0] & (63 if width == 64 else 31)
                base = m[1:] if m.startswith("d") else m
                if base == "sllv":
                    result = value << shift
                elif base == "srlv":
                    result = value >> shift
                else:
                    result = sign_extend(value, width) >> shift
                if width == 32:
                    _write_s32(state, instruction.rd or 0, result)
                else:
                    _write_s64(state, instruction.rd or 0, result)
            elif m in {"mult", "multu", "div", "divu", "madd", "maddu",
                       "mult1", "multu1", "div1", "divu1", "madd1", "maddu1"}:
                if not self._execute_muldiv(instruction):
                    state.pc = instruction.pc
                    return False
            elif m in {"mfhi", "mflo"}:
                _write_s64(state, instruction.rd or 0, state.hi if m == "mfhi" else state.lo)
            elif m in {"mfhi1", "mflo1"}:
                value = state.hi1 if m == "mfhi1" else state.lo1
                _write_s64(state, instruction.rd or 0, value)
            elif m in {"mthi", "mtlo"}:
                if m == "mthi":
                    state.hi = regs[instruction.rs or 0] & MASK64
                else:
                    state.lo = regs[instruction.rs or 0] & MASK64
            elif m in {"mthi1", "mtlo1"}:
                if m == "mthi1":
                    state.hi1 = regs[instruction.rs or 0] & MASK64
                else:
                    state.lo1 = regs[instruction.rs or 0] & MASK64
            elif instruction.cls == "load":
                self._execute_load(instruction)
            elif instruction.cls == "store":
                self._execute_store(instruction)
            elif instruction.cls == "mmi":
                value = self._execute_mmi(instruction)
                if value is not None:
                    _write_128(state, instruction.rd or 0, value)
            else:
                raise ExecutionError(f"Oracle has no implementation for {instruction.text()}")
            regs[0] = 0
            return True
        except ExecutionError:
            raise
        except Exception as exc:  # pragma: no cover - defensive boundary
            raise ExecutionError(f"Oracle failure at 0x{instruction.pc:08X} ({instruction.text()}): {exc}") from exc

    def _execute_muldiv(self, instruction: Instruction) -> bool:
        """Execute signed/unsigned multiply-divide with verified 32-bit operands.

        MULT/DIV operate on the low 32 bits of their operands and write
        64-bit HI/LO (sign-extended 32-bit halves).  The ``*1`` forms use
        HI1/LO1.  Division by zero is architecturally undefined; this model
        chooses quotient 0 and remainder equal to the dividend so that the
        differential tests remain deterministic.
        """
        state = self.state
        regs = state.registers
        m = instruction.mnemonic
        left = regs[instruction.rs or 0] & MASK32
        right = regs[instruction.rt or 0] & MASK32
        signed = m in {"div", "div1", "mult", "mult1", "madd", "madd1"}
        secondary = m.endswith("1")
        if m.startswith("div"):
            if right == 0:
                quotient, remainder = 0, left
            elif signed:
                quotient = _trunc_div(_signed32(left), _signed32(right))
                remainder = _signed32(left) - quotient * _signed32(right)
            else:
                quotient = left // right
                remainder = left % right
            lo = _signed32(quotient) & MASK64
            hi = _signed32(remainder) & MASK64
            if secondary:
                state.lo1, state.hi1 = lo, hi
            else:
                state.lo, state.hi = lo, hi
            return True
        if signed:
            product = _signed32(left) * _signed32(right)
        else:
            product = left * right
        low = _signed32(product) & MASK64
        high = _signed32(product >> 32) & MASK64
        if m.startswith("madd"):
            if secondary:
                accumulator = ((state.hi1 << 64) | state.lo1) + product
                state.hi1 = (accumulator >> 64) & MASK64
                state.lo1 = accumulator & MASK64
            else:
                accumulator = ((state.hi << 64) | state.lo) + product
                state.hi = (accumulator >> 64) & MASK64
                state.lo = accumulator & MASK64
            if instruction.rd:
                _write_s64(state, instruction.rd, _signed32(accumulator & MASK32))
            return True
        if secondary:
            state.hi1, state.lo1 = high, low
        else:
            state.hi, state.lo = high, low
        if instruction.rd:
            _write_s64(state, instruction.rd, _signed32(product & MASK32))
        return True

    def _execute_load(self, instruction: Instruction) -> None:
        state = self.state
        m = instruction.mnemonic
        address = self._effective_address(instruction)
        if m in {"lh", "lhu"}:
            if address & 1:
                raise ExecutionError(f"Unaligned LH at 0x{address:08X}")
            value = state.memory.read(address, 2, signed=False)
            (_write_s64 if m == "lh" else _write_u32)(state, instruction.rt or 0,
                                                       sign_extend(value, 16) if m == "lh" else value)
        elif m == "lw":
            if address & 3:
                raise ExecutionError(f"Unaligned LW at 0x{address:08X}")
            _write_s64(state, instruction.rt or 0, state.memory.read(address, 4, signed=True))
        elif m == "lwu":
            if address & 3:
                raise ExecutionError(f"Unaligned LWU at 0x{address:08X}")
            _write_u32(state, instruction.rt or 0, state.memory.read(address, 4))
        elif m == "ld":
            if address & 7:
                raise ExecutionError(f"Unaligned LD at 0x{address:08X}")
            _write_s64(state, instruction.rt or 0, state.memory.read(address, 8, signed=True))
        elif m == "lq":
            address &= ~0xF
            _write_128(state, instruction.rt or 0, state.memory.read(address, 16))
        elif m in {"lb", "lbu"}:
            value = state.memory.read(address, 1, signed=m == "lb")
            if m == "lb":
                _write_s64(state, instruction.rt or 0, value)
            else:
                _write_u32(state, instruction.rt or 0, value)
        else:
            raise ExecutionError(f"Oracle has no load lowering for {instruction.text()}")

    def _execute_store(self, instruction: Instruction) -> None:
        state = self.state
        m = instruction.mnemonic
        address = self._effective_address(instruction)
        value = state.registers[instruction.rt or 0]
        if m == "sb":
            state.memory.write(address, 1, value)
        elif m == "sh":
            if address & 1:
                raise ExecutionError(f"Unaligned SH at 0x{address:08X}")
            state.memory.write(address, 2, value)
        elif m == "sw":
            if address & 3:
                raise ExecutionError(f"Unaligned SW at 0x{address:08X}")
            state.memory.write(address, 4, value)
        elif m == "sd":
            if address & 7:
                raise ExecutionError(f"Unaligned SD at 0x{address:08X}")
            state.memory.write(address, 8, value)
        elif m == "sq":
            state.memory.write(address & ~0xF, 16, value)
        else:
            raise ExecutionError(f"Oracle has no store lowering for {instruction.text()}")

    def _execute_mmi(self, instruction: Instruction) -> int | None:
        state = self.state
        regs = state.registers
        m = instruction.mnemonic
        if m in {"pabsw", "pabsh"}:
            return _mmi_unary(m, regs[instruction.rt or 0])
        if m in {"psllh", "psrlh", "psrah", "psllw", "psrlw", "psraw"}:
            return _mmi_shift(m, regs[instruction.rt or 0], instruction.shamt or 0)
        left = regs[instruction.rs or 0]
        right = regs[instruction.rt or 0]
        return _mmi_binary(m, left, right)


def normalize_state(state: State) -> dict[str, Any]:
    """Produce the exact JSON shape emitted by generated C++ programs."""
    return {
        "halted": bool(state.halted),
        "pc": int(state.pc),
        "reason": state.reason,
        "steps": int(state.steps),
        "registers": [[int(value) & MASK64, (int(value) >> 64) & MASK64]
                      for value in state.registers],
        "hi": int(state.hi) & MASK64,
        "lo": int(state.lo) & MASK64,
        "hi1": int(state.hi1) & MASK64,
        "lo1": int(state.lo1) & MASK64,
        "memory": [[int(address), int(value)] for address, value in sorted(state.memory.writes.items())],
        "trace": [int(pc) for pc in state.trace],
    }


def run_oracle(program: Program, *, max_steps: int = 100_000,
               initial_registers: dict[int, int] | None = None) -> dict[str, Any]:
    return normalize_state(Oracle(program, max_steps=max_steps,
                                  initial_registers=initial_registers).run())
