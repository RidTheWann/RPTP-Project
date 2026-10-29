# SPDX-License-Identifier: GPL-3.0-or-later
"""Deterministic C++20 generation from lowered RPTP IR.

The generated program is a self-contained native model of the guest program's
memory, registers and instruction stream.  It deliberately does not call back
into Python: the oracle and the generated C++ are independent implementations
that are compared by the differential test harness.

Every IR block becomes one C++ function.  A dispatch loop matches the guest PC
against block entry addresses.  Branch conditions, indirect targets and link
registers are captured before the delay slot executes, mirroring the IR phase
ordering and the MIPS delay-slot contract.
"""
from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass
from pathlib import Path

from .cfg import Program
from .elf import ElfImage
from .ir import BlockIR, Control, IROp, LoweringResult
from .isa import MASK32

RAM_SIZE = 0x02000000
RETURN_SENTINEL = 0x7FFF0000
DEFAULT_MAX_STEPS = 100_000
MEMORY_BLOB_NAME = "rptp_image.bin"
MEMORY_BLOB_MAGIC = b"RPTPIMG1"


class CodegenError(RuntimeError):
    """Raised when the program cannot be lowered to native code."""


@dataclass(frozen=True)
class GeneratedProgram:
    source: str
    memory_blob: bytes
    block_count: int
    instruction_count: int

    @property
    def source_sha256(self) -> str:
        return hashlib.sha256(self.source.encode("utf-8")).hexdigest()

    @property
    def blob_sha256(self) -> str:
        return hashlib.sha256(self.memory_blob).hexdigest()


def _u32(value: int) -> str:
    return f"0x{value & MASK32:08X}u"


def memory_blob(image: ElfImage) -> bytes:
    """Serialize loaded guest bytes as sparse (address, length, data) runs."""
    initial, _ranges = image.initial_memory()
    runs: list[tuple[int, bytearray]] = []
    for address in sorted(initial):
        if runs and address == runs[-1][0] + len(runs[-1][1]):
            runs[-1][1].append(initial[address])
        else:
            runs.append((address, bytearray([initial[address]])))
    payload = bytearray(MEMORY_BLOB_MAGIC)
    payload += struct.pack("<I", len(runs))
    for address, data in runs:
        payload += struct.pack("<II", address, len(data))
        payload += data
    return bytes(payload)


_MMI_BINARY_HELPERS = {
    "paddw": ("32", "x + y"),
    "psubw": ("32", "x - y"),
    "paddh": ("16", "x + y"),
    "psubh": ("16", "x - y"),
    "paddb": ("8", "x + y"),
    "psubb": ("8", "x - y"),
    "pcgtw": ("32", "cmp_signed(x, y, 32) > 0 ? mask_for(32) : 0"),
    "pcgth": ("16", "cmp_signed(x, y, 16) > 0 ? mask_for(16) : 0"),
    "pcgtb": ("8", "cmp_signed(x, y, 8) > 0 ? mask_for(8) : 0"),
    "pmaxw": ("32", "cmp_signed(x, y, 32) >= 0 ? x : y"),
    "pmaxh": ("16", "cmp_signed(x, y, 16) >= 0 ? x : y"),
    "pminw": ("32", "cmp_signed(x, y, 32) <= 0 ? x : y"),
    "pminh": ("16", "cmp_signed(x, y, 16) <= 0 ? x : y"),
    "pceqw": ("32", "x == y ? mask_for(32) : 0"),
    "pceqh": ("16", "x == y ? mask_for(16) : 0"),
    "pceqb": ("8", "x == y ? mask_for(8) : 0"),
    "paddsw": ("32", "sat_signed(cmp_signed(x, 0, 32) + cmp_signed(y, 0, 32), 32)"),
    "paddsh": ("16", "sat_signed(cmp_signed(x, 0, 16) + cmp_signed(y, 0, 16), 16)"),
    "paddsb": ("8", "sat_signed(cmp_signed(x, 0, 8) + cmp_signed(y, 0, 8), 8)"),
    "psubsw": ("32", "sat_signed(cmp_signed(x, 0, 32) - cmp_signed(y, 0, 32), 32)"),
    "psubsh": ("16", "sat_signed(cmp_signed(x, 0, 16) - cmp_signed(y, 0, 16), 16)"),
    "psubsb": ("8", "sat_signed(cmp_signed(x, 0, 8) - cmp_signed(y, 0, 8), 8)"),
    "padduw": ("32", "sat_unsigned((std::int64_t)x + (std::int64_t)y, 32)"),
    "padduh": ("16", "sat_unsigned((std::int64_t)x + (std::int64_t)y, 16)"),
    "paddub": ("8", "sat_unsigned((std::int64_t)x + (std::int64_t)y, 8)"),
    "psubuw": ("32", "sat_unsigned((std::int64_t)x - (std::int64_t)y, 32)"),
    "psubuh": ("16", "sat_unsigned((std::int64_t)x - (std::int64_t)y, 16)"),
    "psubub": ("8", "sat_unsigned((std::int64_t)x - (std::int64_t)y, 8)"),
}

_MMI_PEXT = {
    "pextlw": ("32", "false"),
    "pextuw": ("32", "true"),
    "pextlh": ("16", "false"),
    "pextuh": ("16", "true"),
    "pextlb": ("8", "false"),
    "pextub": ("8", "true"),
}

_MMI_SHIFTS = {
    "psllh": (16, "x << shift"),
    "psrlh": (16, "x >> shift"),
    "psrah": (16, "(std::uint64_t)(cmp_signed(x, 0, 16) >> shift)"),
    "psllw": (32, "x << shift"),
    "psrlw": (32, "x >> shift"),
    "psraw": (32, "(std::uint64_t)(cmp_signed(x, 0, 32) >> shift)"),
}


def _mmi_expression(op: IROp, left: str, right: str) -> str:
    mnemonic = op.mnemonic
    if mnemonic in {"pand", "por", "pxor", "pnor"}:
        operator = {"pand": "&", "por": "|", "pxor": "^"}.get(mnemonic)
        if operator:
            return f"rptp::u128({left}.lo {operator} {right}.lo, {left}.hi {operator} {right}.hi)"
        return f"rptp::u128(~({left}.lo | {right}.lo), ~({left}.hi | {right}.hi))"
    if mnemonic in {"pabsw", "pabsh"}:
        width = 32 if mnemonic == "pabsw" else 16
        return (f"rptp::lanes_unary({right}, {width}, "
                f"[](std::uint64_t x) -> std::uint64_t {{ return abs_lane(x, {width}); }})")
    if mnemonic in _MMI_PEXT:
        width, upper = _MMI_PEXT[mnemonic]
        return f"rptp::pext({left}, {right}, {width}, {upper})"
    helper = _MMI_BINARY_HELPERS.get(mnemonic)
    if helper is None:
        raise CodegenError(f"No native MMI lowering for {mnemonic}")
    width, expression = helper
    return (f"rptp::lanes_binary({left}, {right}, {width}, "
            f"[](std::uint64_t x, std::uint64_t y) -> std::uint64_t {{ return {expression}; }})")


def _mmi_shift_expression(op: IROp, value: str) -> str:
    helper = _MMI_SHIFTS.get(op.mnemonic)
    if helper is None:
        raise CodegenError(f"No native MMI shift lowering for {op.mnemonic}")
    width, expression = helper
    shift = (op.imm or 0) & (0xF if width == 16 else 0x1F)
    return (f"rptp::lanes_unary({value}, {width}, "
            f"[shift = {shift}u](std::uint64_t x) -> std::uint64_t {{ return {expression}; }})")


def _reg(index: int | None) -> str:
    if index is None:
        raise CodegenError("IR operation is missing a register index")
    return f"s.r[{index}u]"


def _memory_expression(op: IROp) -> str:
    mnemonic = op.mnemonic
    if mnemonic in {"lq", "sq"}:
        raise CodegenError(f"{mnemonic} must use the 128-bit memory path")
    size = op.size
    if size not in (1, 2, 4, 8):
        raise CodegenError(f"Unsupported access width {size} for {mnemonic}")
    alignment = {1: 0, 2: 1, 4: 3, 8: 7}[size]
    lines = [f"{{ const std::uint32_t ea = rptp::effective_address(s, {op.a}u, {op.imm});"]
    if alignment and op.kind == "load":
        lines.append(f"  if ((ea & {alignment}u) != 0u) throw std::runtime_error(\"unaligned {mnemonic.upper()}\");")
    if alignment and op.kind == "store":
        lines.append(f"  if ((ea & {alignment}u) != 0u) throw std::runtime_error(\"unaligned {mnemonic.upper()}\");")
    if op.kind == "load":
        raw = f"rptp::read_le(s, ea, {size}u)"
        if mnemonic in {"lb", "lh", "lw"}:
            value = f"rptp::sext{size * 8}({raw})"
        elif mnemonic in {"lbu", "lhu", "lwu"}:
            value = f"rptp::zext64({raw})"
        else:
            value = f"rptp::sext64({raw})"
        lines.append(f"  rptp::write_reg(s, {op.dst}u, {value});")
    else:
        lines.append(f"  rptp::write_le(s, ea, {size}u, s.r[{op.b}u].lo);")
    lines.append("}")
    return "\n".join(lines)


class _Emitter:
    def __init__(self, program: Program, result: LoweringResult, entry: int) -> None:
        self.program = program
        self.result = result
        self.entry = entry
        self.lines: list[str] = []

    def emit(self, text: str = "", indent: int = 1) -> None:
        prefix = "    " * indent
        for line in text.splitlines():
            self.lines.append(prefix + line if line else "")

    def op(self, op: IROp) -> None:
        self.emit(f"rptp::push_trace(s, {_u32(op.pc)});")
        mnemonic = op.mnemonic
        kind = op.kind
        if kind == "nop":
            return
        if kind == "lui":
            self.emit(f"rptp::write_reg(s, {op.dst}u, rptp::sext32((std::uint32_t){op.imm}u << 16));")
        elif kind == "imm_op":
            self._imm_op(op)
        elif kind == "reg_op":
            self._reg_op(op)
        elif kind == "checked_arith":
            self._checked_arith(op)
        elif kind == "shift":
            self._shift(op)
        elif kind == "shift_var":
            self._shift_var(op)
        elif kind == "read_hi_lo":
            field = "hi1" if mnemonic == "mfhi1" else ("lo1" if mnemonic == "mflo1" else
                                                          ("hi" if mnemonic == "mfhi" else "lo"))
            self.emit(f"rptp::write_reg(s, {op.dst}u, rptp::sext64(s.{field}));")
        elif kind == "write_hi_lo":
            field = {"mthi": "hi", "mtlo": "lo", "mthi1": "hi1", "mtlo1": "lo1"}[mnemonic]
            self.emit(f"s.{field} = s.r[{op.a}u].lo;")
        elif kind == "muldiv":
            self._muldiv(op)
        elif kind in {"load", "store"}:
            if mnemonic in {"lq", "sq"}:
                self._quad_memory(op)
            else:
                self.emit(_memory_expression(op))
        elif kind == "mmi":
            left = _reg(op.a)
            right = _reg(op.b)
            expression = _mmi_expression(op, left, right)
            self.emit(f"rptp::write_reg(s, {op.dst}u, {expression});")
        elif kind == "mmi_shift":
            self.emit(f"rptp::write_reg(s, {op.dst}u, {_mmi_shift_expression(op, _reg(op.a))});")
        else:
            raise CodegenError(f"No native lowering for IR kind {kind} ({mnemonic})")

    def _imm_op(self, op: IROp) -> None:
        m = op.mnemonic
        dest = f"{op.dst}u"
        source = _reg(op.a)
        if m in {"addiu", "daddiu"}:
            write = "sext32" if m == "addiu" else "sext64"
            operand = f"(std::uint32_t){source}.lo" if m == "addiu" else f"{source}.lo"
            cast = f"(std::uint64_t)(std::int64_t){op.imm}" if op.imm < 0 else f"{op.imm}u"
            self.emit(f"rptp::write_reg(s, {dest}, rptp::{write}({operand} + {cast}));")
        elif m == "slti":
            self.emit(f"rptp::write_reg(s, {dest}, rptp::sext64(cmp_signed({source}.lo, {op.imm}, 64) < 0 ? 1u : 0u));")
        elif m == "sltiu":
            imm = op.imm & 0xFFFFFFFFFFFFFFFF
            self.emit(f"rptp::write_reg(s, {dest}, rptp::sext64({source}.lo < 0x{imm:016X}ull ? 1u : 0u));")
        elif m in {"andi", "ori", "xori"}:
            operator = {"andi": "&", "ori": "|", "xori": "^"}[m]
            self.emit(f"rptp::write_reg(s, {dest}, rptp::sext64({source}.lo {operator} 0x{op.imm:04X}ull));")
        else:
            raise CodegenError(f"No native immediate lowering for {m}")

    def _reg_op(self, op: IROp) -> None:
        m = op.mnemonic
        left = _reg(op.a)
        right = _reg(op.b)
        dest = f"{op.dst}u"
        width = op.width
        if m in {"addu", "subu"}:
            operator = "+" if m == "addu" else "-"
            self.emit(f"rptp::write_reg(s, {dest}, rptp::sext32((std::uint32_t)((std::uint32_t){left}.lo {operator} (std::uint32_t){right}.lo)));")
        elif m in {"daddu", "dsubu"}:
            operator = "+" if m == "daddu" else "-"
            self.emit(f"rptp::write_reg(s, {dest}, rptp::sext64({left}.lo {operator} {right}.lo));")
        elif m in {"and", "or", "xor", "nor"}:
            operator = {"and": "&", "or": "|", "xor": "^"}[m] if m != "nor" else None
            if operator:
                self.emit(f"rptp::write_reg(s, {dest}, rptp::sext64({left}.lo {operator} {right}.lo));")
            else:
                self.emit(f"rptp::write_reg(s, {dest}, rptp::sext64(~({left}.lo | {right}.lo)));")
        elif m in {"slt", "sltu"}:
            comparison = (f"cmp_signed({left}.lo, {right}.lo, 64) < 0"
                          if m == "slt" else f"{left}.lo < {right}.lo")
            self.emit(f"rptp::write_reg(s, {dest}, rptp::sext64({comparison} ? 1u : 0u));")
        elif m in {"movz", "movn"}:
            condition = f"{right}.lo == 0u" if m == "movz" else f"{right}.lo != 0u"
            self.emit(f"if ({condition}) rptp::write_reg(s, {dest}, {left});")
        else:
            raise CodegenError(f"No native register lowering for {m}")

    def _checked_arith(self, op: IROp) -> None:
        m = op.mnemonic
        left = _reg(op.a)
        right = _reg(op.b)
        dest = f"{op.dst}u"
        if op.width == 32:
            self.emit(f"{{ const std::int64_t result = (std::int64_t)(std::int32_t){left}.lo "
                      f"{'+' if m in {'add', 'dadd'} else '-'} (std::int64_t)(std::int32_t){right}.lo;")
            self.emit("  if (result < INT32_MIN || result > INT32_MAX) { rptp::trap(s, "
                      f"{_u32(op.pc)}, \"trap:integer_overflow\"); return; }}")
            self.emit(f"rptp::write_reg(s, {dest}, rptp::sext32((std::uint32_t)result)); }}")
        else:
            operation = "add" if m in {"add", "dadd"} else "sub"
            self.emit(f"{{ std::uint64_t result; if (rptp::{operation}_overflow64({left}.lo, {right}.lo, result)) "
                      f"{{ rptp::trap(s, {_u32(op.pc)}, \"trap:integer_overflow\"); return; }}")
            self.emit(f"  rptp::write_reg(s, {dest}, rptp::sext64(result)); }}")

    def _shift(self, op: IROp) -> None:
        m = op.mnemonic
        source = _reg(op.a)
        dest = f"{op.dst}u"
        shift = op.imm or 0
        base = m[:-2] if m.endswith("32") and m.startswith("ds") else m
        if op.width == 32:
            if base == "sll":
                expression = f"(std::uint32_t){source}.lo << {shift}u"
            elif base == "srl":
                expression = f"(std::uint32_t){source}.lo >> {shift}u"
            else:
                expression = f"cmp_signed({source}.lo, 0, 32) >> {shift}u"
            self.emit(f"rptp::write_reg(s, {dest}, rptp::sext32((std::uint32_t)({expression})));")
        else:
            if base == "dsll":
                expression = f"{source}.lo << {shift}u"
            elif base == "dsrl":
                expression = f"{source}.lo >> {shift}u"
            else:
                expression = f"cmp_signed({source}.lo, 0, 64) >> {shift}u"
            self.emit(f"rptp::write_reg(s, {dest}, rptp::sext64((std::uint64_t)({expression})));")

    def _shift_var(self, op: IROp) -> None:
        m = op.mnemonic
        value = _reg(op.a)
        amount = _reg(op.b)
        dest = f"{op.dst}u"
        if op.width == 32:
            shift = f"((std::uint32_t){amount}.lo & 31u)"
            base = m[1:] if m.startswith("d") else m
            if base == "sllv":
                expression = f"(std::uint32_t){value}.lo << {shift}"
            elif base == "srlv":
                expression = f"(std::uint32_t){value}.lo >> {shift}"
            else:
                expression = f"cmp_signed({value}.lo, 0, 32) >> {shift}"
            self.emit(f"rptp::write_reg(s, {dest}, rptp::sext32((std::uint32_t)({expression})));")
        else:
            shift = f"({amount}.lo & 63u)"
            base = m[1:] if m.startswith("d") else m
            if base == "sllv":
                expression = f"{value}.lo << {shift}"
            elif base == "srlv":
                expression = f"{value}.lo >> {shift}"
            else:
                expression = f"cmp_signed({value}.lo, 0, 64) >> {shift}"
            self.emit(f"rptp::write_reg(s, {dest}, rptp::sext64((std::uint64_t)({expression})));")

    def _muldiv(self, op: IROp) -> None:
        m = op.mnemonic
        secondary = "true" if m.endswith("1") else "false"
        rd = f"{op.dst}u" if op.dst else "0u"
        if m.startswith("div"):
            signed = "true" if m in {"div", "div1"} else "false"
            self.emit(f"rptp::exec_div(s, {op.a}u, {op.b}u, {signed}, {secondary});")
        else:
            signed = "true" if m in {"mult", "mult1", "madd", "madd1"} else "false"
            function = "exec_madd" if m.startswith("madd") else "exec_mult"
            self.emit(f"rptp::{function}(s, {op.a}u, {op.b}u, {signed}, {secondary}, {rd});")

    def _quad_memory(self, op: IROp) -> None:
        lines = [f"{{ const std::uint32_t ea = rptp::effective_address(s, {op.a}u, {op.imm}) & ~0xFu;"]
        if op.kind == "load":
            lines.append(f"  rptp::write_reg(s, {op.dst}u, rptp::read128(s, ea));")
        else:
            lines.append(f"  rptp::write128(s, ea, s.r[{op.b}u]);")
        lines.append("}")
        self.emit("\n".join(lines))

    def control(self, block: BlockIR) -> None:
        control = block.control
        kind = control.kind
        if kind == "halt":
            self.emit(f"rptp::push_trace(s, {_u32(control.pc)});")
            self.emit(f"rptp::trap(s, {_u32(control.pc)}, \"{control.reason or 'halt'}\");")
            return
        if kind == "unsupported":
            raise CodegenError(f"Block 0x{block.start:08X} is unsupported: {control.reason}")
        if kind == "branch":
            if control.mnemonic not in {"beq", "bne", "blez", "bgtz", "bltz", "bgez",
                                        "bltzal", "bgezal"}:
                raise CodegenError(f"No native branch lowering for {control.mnemonic}")
            self.emit(f"rptp::push_trace(s, {_u32(control.pc)});")
            left = _reg(control.rs)
            right = _reg(control.rt) if control.rt is not None and control.mnemonic in {"beq", "bne"} else None
            if control.cond == "eq":
                condition = f"{left}.lo == {right}.lo"
            elif control.cond == "ne":
                condition = f"{left}.lo != {right}.lo"
            elif control.cond == "le":
                condition = f"rptp::cmp_signed({left}.lo, 0, 64) <= 0"
            elif control.cond == "gt":
                condition = f"rptp::cmp_signed({left}.lo, 0, 64) > 0"
            elif control.cond == "lt":
                condition = f"rptp::cmp_signed({left}.lo, 0, 64) < 0"
            else:
                condition = f"rptp::cmp_signed({left}.lo, 0, 64) >= 0"
            self.emit(f"const bool taken = {condition};")
            if control.link_reg is not None:
                self.emit(f"rptp::write_reg(s, {control.link_reg}u, rptp::u128({_u32(control.pc + 8)}));")
            for op in block.delay_ops:
                self.op(op)
            target = control.target if control.target is not None else control.fallthrough
            self.emit(f"s.pc = taken ? {_u32(target)} : {_u32(control.fallthrough)};")
            return
        if kind in {"jump", "call"}:
            if not control.mnemonic:
                target = control.target
                if target is None:
                    target = block.start + 4 * len(block.instructions)
                for op in block.delay_ops:
                    self.op(op)
                self.emit(f"s.pc = {_u32(target)};")
                return
            self.emit(f"rptp::push_trace(s, {_u32(control.pc)});")
            if kind == "call":
                self.emit(f"rptp::write_reg(s, 31u, rptp::u128({_u32(control.pc + 8)}));")
            for op in block.delay_ops:
                self.op(op)
            self.emit(f"s.pc = {_u32(control.target)};")
            return
        if kind in {"return", "indirect", "indirect_call"}:
            self.emit(f"rptp::push_trace(s, {_u32(control.pc)});")
            target_reg = control.target_reg if control.target_reg is not None else 31
            self.emit(f"const std::uint32_t target = (std::uint32_t)s.r[{target_reg}u].lo;")
            if control.link_reg is not None:
                self.emit(f"rptp::write_reg(s, {control.link_reg}u, rptp::u128({_u32(control.pc + 8)}));")
            for op in block.delay_ops:
                self.op(op)
            self.emit("s.pc = target;")
            return
        raise CodegenError(f"No native lowering for control kind {kind}")

    def block(self, block: BlockIR) -> None:
        name = f"block_{block.start:08X}"
        self.emit(f"static void {name}(rptp::State& s) {{", indent=0)
        for op in block.ops:
            self.op(op)
        self.control(block)
        self.emit("}", indent=0)
        self.emit("", indent=0)
        return name

    def program_source(self) -> tuple[str, int]:
        blocks = sorted(self.result.blocks)
        if not blocks:
            raise CodegenError("No IR blocks to generate")
        name_by_start: dict[int, str] = {}
        for start in blocks:
            name_by_start[start] = self.block(self.result.blocks[start])
        dispatch = "\n".join(
            f"            case {_u32(start)}: {name_by_start[start]}(s); break;"
            for start in blocks)
        instruction_count = sum(len(block.instructions) for block in self.result.blocks.values())
        source = _PRELUDE.format(
            entry=_u32(self.entry),
            sentinel=_u32(RETURN_SENTINEL),
            dispatch=dispatch,
            blocks="\n".join(self.lines),
        )
        return source, instruction_count


_PRELUDE = r'''// SPDX-License-Identifier: GPL-3.0-or-later
// Generated by tools/rptp/codegen.py. Do not edit by hand.
// Native R5900 subset model; not a complete PS2 EE reimplementation.
#include <array>
#include <cstdint>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

namespace rptp {{
constexpr std::uint32_t RAM_SIZE = 0x02000000u;

struct U128 {{
    std::uint64_t lo = 0;
    std::uint64_t hi = 0;
}};

inline U128 u128(std::uint64_t lo, std::uint64_t hi = 0) {{ return U128{{lo, hi}}; }}
inline U128 zext64(std::uint64_t value) {{ return U128{{value, 0}}; }}
inline U128 sext64(std::uint64_t value) {{
    return U128{{value, (value & 0x8000000000000000ull) != 0ull ? ~0ull : 0ull}};
}}
inline U128 sext32(std::uint64_t value) {{
    return sext64(static_cast<std::uint64_t>(static_cast<std::int64_t>(
        static_cast<std::int32_t>(static_cast<std::uint32_t>(value)))));
}}
inline U128 sext16(std::uint64_t value) {{
    return sext64(static_cast<std::uint64_t>(static_cast<std::int64_t>(static_cast<std::int16_t>(value))));
}}
inline U128 sext8(std::uint64_t value) {{
    return sext64(static_cast<std::uint64_t>(static_cast<std::int64_t>(static_cast<std::int8_t>(value))));
}}
inline std::int64_t cmp_signed(std::uint64_t value, std::uint64_t, unsigned width) {{
    if (width == 64) return static_cast<std::int64_t>(value);
    if (width == 32) return static_cast<std::int32_t>(value);
    if (width == 16) return static_cast<std::int16_t>(value);
    return static_cast<std::int8_t>(value);
}}
inline std::uint64_t mask_for(unsigned width) {{
    return width == 64 ? ~0ull : ((1ull << width) - 1ull);
}}
inline std::uint64_t sat_signed(std::int64_t value, unsigned width) {{
    if (width == 32) {{
        if (value < -2147483648ll) value = -2147483648ll;
        if (value > 2147483647ll) value = 2147483647ll;
        return static_cast<std::uint32_t>(value);
    }}
    if (width == 16) {{
        if (value < -32768) value = -32768;
        if (value > 32767) value = 32767;
        return static_cast<std::uint16_t>(value);
    }}
    if (value < -128) value = -128;
    if (value > 127) value = 127;
    return static_cast<std::uint8_t>(value);
}}
inline std::uint64_t sat_unsigned(std::int64_t value, unsigned width) {{
    const std::int64_t high = width == 32 ? 4294967295ll : (width == 16 ? 65535ll : 255ll);
    if (value < 0) value = 0;
    if (value > high) value = high;
    return static_cast<std::uint64_t>(value);
}}
inline std::uint64_t abs_lane(std::uint64_t value, unsigned width) {{
    const std::int64_t signed_value = cmp_signed(value, 0, width);
    const std::int64_t low = -(static_cast<std::int64_t>(1) << (width - 1));
    if (signed_value == low) return mask_for(width);
    return static_cast<std::uint64_t>(signed_value < 0 ? -signed_value : signed_value);
}}
inline std::uint64_t lane_of(U128 value, unsigned shift, unsigned width) {{
    std::uint64_t word;
    if (shift < 64u) {{
        word = value.lo >> shift;
        if (shift + width > 64u) word |= value.hi << (64u - shift);
    }} else {{
        word = value.hi >> (shift - 64u);
    }}
    return width == 64u ? word : (word & ((1ull << width) - 1ull));
}}
inline U128 set_lane(U128 value, unsigned shift, unsigned width, std::uint64_t lane) {{
    const std::uint64_t mask = mask_for(width);
    lane &= mask;
    if (shift == 0u && width == 64u) {{
        value.lo = lane;
    }} else if (shift < 64u) {{
        value.lo |= lane << shift;
        if (shift + width > 64u) value.hi |= lane >> (64u - shift);
    }} else {{
        value.hi |= lane << (shift - 64u);
    }}
    return value;
}}
template <typename F>
U128 lanes_binary(U128 left, U128 right, unsigned width, F operation) {{
    U128 result{{}};
    for (unsigned shift = 0; shift < 128u; shift += width) {{
        result = set_lane(result, shift, width,
                          operation(lane_of(left, shift, width), lane_of(right, shift, width)));
    }}
    return result;
}}
template <typename F>
U128 lanes_unary(U128 value, unsigned width, F operation) {{
    U128 result{{}};
    for (unsigned shift = 0; shift < 128u; shift += width) {{
        result = set_lane(result, shift, width, operation(lane_of(value, shift, width)));
    }}
    return result;
}}
inline U128 pext(U128 left, U128 right, unsigned width, bool upper) {{
    const unsigned half = 64u / width;
    const unsigned start = upper ? half : 0u;
    U128 result{{}};
    for (unsigned index = 0; index < half; ++index) {{
        result = set_lane(result, (2u * index) * width, width, lane_of(left, (start + index) * width, width));
        result = set_lane(result, (2u * index + 1u) * width, width, lane_of(right, (start + index) * width, width));
    }}
    return result;
}}

struct State {{
    std::array<U128, 32> r{{}};
    std::uint64_t hi = 0;
    std::uint64_t lo = 0;
    std::uint64_t hi1 = 0;
    std::uint64_t lo1 = 0;
    std::uint32_t pc = 0;
    bool halted = false;
    std::string reason;
    std::uint64_t steps = 0;
    std::uint64_t max_steps = 100000u;
    std::vector<std::uint32_t> trace;
    std::vector<std::uint8_t> ram;
    std::map<std::uint32_t, std::uint8_t> writes;
}};

inline void push_trace(State& state, std::uint32_t pc) {{
    state.trace.push_back(pc);
    ++state.steps;
}}
inline void write_reg(State& state, unsigned index, U128 value) {{
    if (index != 0u) state.r[index] = value;
}}
inline void trap(State& state, std::uint32_t pc, const char* reason) {{
    state.halted = true;
    state.reason = reason;
    state.pc = pc;
}}
inline std::uint32_t physical(std::uint32_t address) {{
    if (address >= 0x80000000u && address < 0xA0000000u) return address - 0x80000000u;
    if (address >= 0xA0000000u && address < 0xC0000000u) return address - 0xA0000000u;
    return address;
}}
inline std::uint32_t effective_address(const State& state, unsigned base, std::int32_t offset) {{
    return physical(static_cast<std::uint32_t>(state.r[base].lo +
        static_cast<std::uint64_t>(static_cast<std::int64_t>(offset))));
}}
inline void check_ram(std::uint32_t address, unsigned size) {{
    if (static_cast<std::uint64_t>(address) + size > RAM_SIZE) {{
        throw std::runtime_error("guest memory access outside modelled RAM");
    }}
}}
inline std::uint64_t read_le(const State& state, std::uint32_t address, unsigned size) {{
    check_ram(address, size);
    std::uint64_t value = 0;
    for (unsigned index = 0; index < size; ++index) {{
        value |= static_cast<std::uint64_t>(state.ram[address + index]) << (8u * index);
    }}
    return value;
}}
inline U128 read128(const State& state, std::uint32_t address) {{
    return U128{{read_le(state, address, 8u), read_le(state, address + 8u, 8u)}};
}}
inline void write_le(State& state, std::uint32_t address, unsigned size, std::uint64_t value) {{
    check_ram(address, size);
    for (unsigned index = 0; index < size; ++index) {{
        const std::uint8_t byte = static_cast<std::uint8_t>(value >> (8u * index));
        state.ram[address + index] = byte;
        state.writes[address + index] = byte;
    }}
}}
inline void write128(State& state, std::uint32_t address, U128 value) {{
    write_le(state, address, 8u, value.lo);
    write_le(state, address + 8u, 8u, value.hi);
}}
inline bool add_overflow64(std::uint64_t left, std::uint64_t right, std::uint64_t& result) {{
    result = left + right;
    return ((~(left ^ right) & (left ^ result)) >> 63) != 0u;
}}
inline bool sub_overflow64(std::uint64_t left, std::uint64_t right, std::uint64_t& result) {{
    result = left - right;
    return (((left ^ right) & (left ^ result)) >> 63) != 0u;
}}

inline void exec_div(State& state, unsigned rs, unsigned rt, bool is_signed, bool secondary) {{
    const std::uint32_t left = static_cast<std::uint32_t>(state.r[rs].lo);
    const std::uint32_t right = static_cast<std::uint32_t>(state.r[rt].lo);
    std::uint32_t quotient = 0;
    std::uint32_t remainder = left;
    if (right != 0u) {{
        if (is_signed) {{
            const std::int64_t a = static_cast<std::int32_t>(left);
            const std::int64_t b = static_cast<std::int32_t>(right);
            const std::int64_t q = a / b;
            quotient = static_cast<std::uint32_t>(q);
            remainder = static_cast<std::uint32_t>(a - q * b);
        }} else {{
            quotient = left / right;
            remainder = left % right;
        }}
    }}
    const std::uint64_t lo_value = static_cast<std::uint64_t>(
        static_cast<std::int64_t>(static_cast<std::int32_t>(quotient)));
    const std::uint64_t hi_value = static_cast<std::uint64_t>(
        static_cast<std::int64_t>(static_cast<std::int32_t>(remainder)));
    if (secondary) {{ state.lo1 = lo_value; state.hi1 = hi_value; }}
    else {{ state.lo = lo_value; state.hi = hi_value; }}
}}

inline void exec_mult(State& state, unsigned rs, unsigned rt, bool is_signed,
                      bool secondary, unsigned rd) {{
    const std::uint32_t left = static_cast<std::uint32_t>(state.r[rs].lo);
    const std::uint32_t right = static_cast<std::uint32_t>(state.r[rt].lo);
    std::uint64_t product;
    if (is_signed) {{
        product = static_cast<std::uint64_t>(
            static_cast<std::int64_t>(static_cast<std::int32_t>(left)) *
            static_cast<std::int64_t>(static_cast<std::int32_t>(right)));
    }} else {{
        product = static_cast<std::uint64_t>(left) * static_cast<std::uint64_t>(right);
    }}
    const std::uint64_t low = static_cast<std::uint64_t>(
        static_cast<std::int64_t>(static_cast<std::int32_t>(static_cast<std::uint32_t>(product))));
    const std::uint64_t high = static_cast<std::uint64_t>(
        static_cast<std::int64_t>(static_cast<std::int32_t>(static_cast<std::uint32_t>(product >> 32))));
    if (secondary) {{ state.lo1 = low; state.hi1 = high; }}
    else {{ state.lo = low; state.hi = high; }}
    if (rd != 0u) write_reg(state, rd, sext32(static_cast<std::uint32_t>(product)));
}}

inline void exec_madd(State& state, unsigned rs, unsigned rt, bool is_signed,
                      bool secondary, unsigned rd) {{
    const std::uint32_t left = static_cast<std::uint32_t>(state.r[rs].lo);
    const std::uint32_t right = static_cast<std::uint32_t>(state.r[rt].lo);
    std::uint64_t product;
    if (is_signed) {{
        product = static_cast<std::uint64_t>(
            static_cast<std::int64_t>(static_cast<std::int32_t>(left)) *
            static_cast<std::int64_t>(static_cast<std::int32_t>(right)));
    }} else {{
        product = static_cast<std::uint64_t>(left) * static_cast<std::uint64_t>(right);
    }}
    std::uint64_t& low = secondary ? state.lo1 : state.lo;
    std::uint64_t& high = secondary ? state.hi1 : state.hi;
    const std::uint64_t new_low = low + product;
    const std::uint64_t carry = (new_low < low) ? 1u : 0u;
    const std::uint64_t extension =
        is_signed ? static_cast<std::uint64_t>(static_cast<std::int64_t>(product) >> 63) : 0ull;
    high += extension + carry;
    low = new_low;
    if (rd != 0u) write_reg(state, rd, sext32(static_cast<std::uint32_t>(new_low)));
}}

inline void load_image(State& state, const char* path) {{
    std::ifstream stream(path, std::ios::binary);
    if (!stream) throw std::runtime_error("cannot open memory image");
    std::array<char, 8> magic{{}};
    stream.read(magic.data(), 8);
    if (std::string(magic.data(), 8) != "RPTPIMG1") throw std::runtime_error("bad memory image magic");
    std::uint32_t count = 0;
    stream.read(reinterpret_cast<char*>(&count), 4);
    for (std::uint32_t index = 0; index < count; ++index) {{
        std::uint32_t address = 0;
        std::uint32_t length = 0;
        stream.read(reinterpret_cast<char*>(&address), 4);
        stream.read(reinterpret_cast<char*>(&length), 4);
        check_ram(address, length);
        stream.read(reinterpret_cast<char*>(state.ram.data() + address), length);
        if (!stream) throw std::runtime_error("truncated memory image");
    }}
}}

inline void print_state(const State& state) {{
    std::cout << "{{\"halted\":" << (state.halted ? "true" : "false")
              << ",\"pc\":" << state.pc
              << ",\"reason\":\"" << state.reason << "\""
              << ",\"steps\":" << state.steps << ",\"registers\":[";
    for (std::size_t index = 0; index < state.r.size(); ++index) {{
        if (index != 0u) std::cout << ',';
        std::cout << '[' << state.r[index].lo << ',' << state.r[index].hi << ']';
    }}
    std::cout << "],\"hi\":" << state.hi << ",\"lo\":" << state.lo
              << ",\"hi1\":" << state.hi1 << ",\"lo1\":" << state.lo1
              << ",\"memory\":[";
    bool first = true;
    for (const auto& item : state.writes) {{
        if (!first) std::cout << ',';
        first = false;
        std::cout << '[' << item.first << ',' << static_cast<unsigned>(item.second) << ']';
    }}
    std::cout << "],\"trace\":[";
    for (std::size_t index = 0; index < state.trace.size(); ++index) {{
        if (index != 0u) std::cout << ',';
        std::cout << state.trace[index];
    }}
    std::cout << "]}}\n";
}}

{blocks}

void run(rptp::State& s) {{
    while (!s.halted) {{
        if (s.steps >= s.max_steps) {{
            s.halted = true;
            s.reason = "step_limit";
            break;
        }}
        switch (s.pc) {{
{dispatch}
            default:
                s.halted = true;
                s.reason = "pc_outside_code";
                break;
        }}
    }}
}}
}}  // namespace rptp

int main(int argc, char** argv) {{
    try {{
        rptp::State state;
        state.ram.assign(rptp::RAM_SIZE, 0);
        state.pc = {entry};
        state.r[31] = rptp::u128({sentinel});
        if (argc > 1) state.max_steps = std::stoull(argv[1]);
        if (argc > 2) rptp::load_image(state, argv[2]);
        rptp::run(state);
        rptp::print_state(state);
        return 0;
    }} catch (const std::exception& error) {{
        std::cerr << "native model error: " << error.what() << "\n";
        return 2;
    }}
}}
'''


def generate(program: Program, result: LoweringResult, entry: int | None = None) -> GeneratedProgram:
    if result.errors:
        raise CodegenError("lowering failed: " + "; ".join(result.errors))
    entry = program.entry if entry is None else entry
    emitter = _Emitter(program, result, entry)
    source, instruction_count = emitter.program_source()
    return GeneratedProgram(
        source=source,
        memory_blob=memory_blob(program.image),
        block_count=len(result.blocks),
        instruction_count=instruction_count,
    )


def write_generated(generated: GeneratedProgram, directory: Path) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    source_path = directory / "rptp_native.cpp"
    blob_path = directory / MEMORY_BLOB_NAME
    source_path.write_text(generated.source, encoding="utf-8")
    blob_path.write_bytes(generated.memory_blob)
    return source_path, blob_path
