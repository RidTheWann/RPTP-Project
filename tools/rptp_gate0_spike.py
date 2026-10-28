#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Small, self-contained RPTP Gate 0 recompilation spike.

This is a synthetic ELF32/EM_MIPS fixture and an intentionally limited MIPS
subset. It is not a PS2 game loader or a complete R5900 implementation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_REL = Path("tests/fixtures/gate0-r5900-subset.elf")
BASE = 0x00100000
RETURN_SENTINEL = 0x7FFF0000
MEMORY_ADDRESS = 0x2000
MAX_STEPS = 128

# Register aliases used only to make the fixture program easy to audit.
ZERO, V0, V1 = 0, 2, 3
A0, A1 = 4, 5
T0, T1, T2, T3, T4 = 8, 9, 10, 11, 12
S0, S1, S2, S3, S4, S7 = 16, 17, 18, 19, 20, 23
RA = 31


def encode_i(op: int, rs: int, rt: int, imm: int) -> int:
    if not -32768 <= imm <= 65535:
        raise ValueError(f"Immediate out of 16-bit encoding range: {imm}")
    return ((op & 0x3F) << 26) | ((rs & 0x1F) << 21) | ((rt & 0x1F) << 16) | (imm & 0xFFFF)


def encode_r(rs: int, rt: int, rd: int, shamt: int, funct: int) -> int:
    return ((rs & 0x1F) << 21) | ((rt & 0x1F) << 16) | ((rd & 0x1F) << 11) | ((shamt & 0x1F) << 6) | (funct & 0x3F)


def encode_j(op: int, target: int) -> int:
    if target & 3:
        raise ValueError("Jump target must be 4-byte aligned")
    return ((op & 0x3F) << 26) | ((target >> 2) & 0x03FFFFFF)


def fixture_words() -> list[tuple[int, str, int]]:
    """Return (guest PC, label, encoded word) rows for our synthetic fixture."""
    addr = lambda off: BASE + off
    labels = [
        ("save_caller_ra", encode_r(RA, ZERO, S7, 0, 0x21)),
        ("set_t0", encode_i(0x09, ZERO, T0, 7)),
        ("set_t1", encode_i(0x09, ZERO, T1, 5)),
        ("add_t2", encode_r(T0, T1, T2, 0, 0x21)),
        ("set_mem_address", encode_i(0x09, ZERO, T3, MEMORY_ADDRESS)),
        ("store_t2", encode_i(0x2B, T3, T2, 0)),
        ("load_t4", encode_i(0x23, T3, T4, 0)),
        ("bne_to_failure_if_memory_differs", encode_i(0x05, T2, T4, 14)),
        ("bne_delay_slot", encode_i(0x09, ZERO, S4, 23)),
        ("set_a0", encode_i(0x09, ZERO, A0, 9)),
        ("call_sum_function", encode_j(0x03, addr(0x64))),
        ("jal_delay_slot", encode_i(0x09, ZERO, A1, 33)),
        ("expected_sum", encode_i(0x09, ZERO, V1, 42)),
        ("beq_success", encode_i(0x04, V0, V1, 4)),
        ("beq_delay_slot", encode_i(0x09, ZERO, S0, 17)),
        ("failure_flag", encode_i(0x09, ZERO, S1, 0)),
        ("jump_to_failure_restore", encode_j(0x02, addr(0x58))),
        ("jump_delay_nop", encode_r(ZERO, ZERO, ZERO, 0, 0x00)),
        ("success_flag", encode_i(0x09, ZERO, S1, 1)),
        ("restore_caller_ra", encode_i(0x09, S7, RA, 0)),
        ("return_from_main", encode_r(RA, ZERO, ZERO, 0, 0x08)),
        ("main_return_delay_slot", encode_i(0x09, ZERO, S2, 99)),
        ("failure_restore_ra", encode_i(0x09, S7, RA, 0)),
        ("failure_return", encode_r(RA, ZERO, ZERO, 0, 0x08)),
        ("failure_return_delay_slot", encode_i(0x09, ZERO, S2, 88)),
        ("sum_function", encode_r(A0, A1, V0, 0, 0x21)),
        ("sum_function_return", encode_r(RA, ZERO, ZERO, 0, 0x08)),
        ("sum_function_delay_slot", encode_i(0x09, ZERO, S3, 55)),
    ]
    return [(addr(i * 4), name, word) for i, (name, word) in enumerate(labels)]


def ori_fixture_words() -> list[tuple[int, str, int]]:
    """Return (guest PC, label, encoded word) rows for the separate ORI program."""
    addr = lambda off: BASE + off
    labels = [
        ("zero_register_stays_zero", encode_i(0x0D, ZERO, ZERO, 0xFFFF)),
        ("zero_extend_high_bit", encode_i(0x0D, ZERO, T0, 0x8001)),
        ("combine_zero_extended_value", encode_i(0x0D, T0, T1, 0x4000)),
        ("return_value", encode_i(0x0D, ZERO, V0, 42)),
        ("return_from_main", encode_r(RA, ZERO, ZERO, 0, 0x08)),
        ("main_return_delay_slot", encode_r(ZERO, ZERO, ZERO, 0, 0x00)),
    ]
    return [(addr(i * 4), name, word) for i, (name, word) in enumerate(labels)]


def build_elf_from_rows(rows: list[tuple[int, str, int]]) -> bytes:
    """Create an ELF32 little-endian EM_MIPS executable from explicit test words."""
    code = b"".join(struct.pack("<I", word) for _, _, word in rows)
    ident = b"\x7fELF" + bytes([1, 1, 1, 0, 0]) + bytes(7)
    # ELF32 header: ET_EXEC, EM_MIPS, EV_CURRENT, one PT_LOAD, no section table.
    ehdr = struct.pack(
        "<16sHHIIIIIHHHHHH",
        ident,
        2,       # ET_EXEC
        8,       # EM_MIPS
        1,       # EV_CURRENT
        BASE,    # e_entry
        52,      # e_phoff
        0,       # e_shoff
        0,       # e_flags (no ABI-specific flags required by this fixture)
        52,      # e_ehsize
        32,      # e_phentsize
        1,       # e_phnum
        40,      # e_shentsize
        0,       # e_shnum
        0,       # e_shstrndx
    )
    phdr = struct.pack(
        "<IIIIIIII",
        1,              # PT_LOAD
        0x1000,         # p_offset
        BASE,           # p_vaddr
        BASE,           # p_paddr
        len(code),      # p_filesz
        len(code),      # p_memsz
        5,              # PF_R | PF_X
        0x1000,         # p_align; offsets and addresses are congruent
    )
    if len(ehdr) != 52 or len(phdr) != 32:
        raise AssertionError("ELF structure size mismatch")
    return ehdr + phdr + bytes(0x1000 - len(ehdr) - len(phdr)) + code


def build_fixture_elf() -> bytes:
    """Create the registered Gate 0 synthetic fixture without changing its bytes."""
    return build_elf_from_rows(fixture_words())


def build_ori_fixture_elf() -> bytes:
    """Create the separate synthetic ORI differential fixture."""
    return build_elf_from_rows(ori_fixture_words())


def sign_extend_16(value: int) -> int:
    value &= 0xFFFF
    return value - 0x10000 if value & 0x8000 else value


def sign_extend_32(value: int) -> int:
    value &= 0xFFFFFFFF
    return value - 0x100000000 if value & 0x80000000 else value


def sign_extend_64(value: int) -> int:
    value &= 0xFFFFFFFFFFFFFFFF
    return value - 0x10000000000000000 if value & 0x8000000000000000 else value


def slt64(lhs: int, rhs: int) -> int:
    return 1 if sign_extend_64(lhs) < sign_extend_64(rhs) else 0


def sltu64(lhs: int, rhs: int) -> int:
    return 1 if (lhs & 0xFFFFFFFFFFFFFFFF) < (rhs & 0xFFFFFFFFFFFFFFFF) else 0


def parse_elf(data: bytes) -> tuple[int, dict[int, int], dict[str, int]]:
    """Parse the small subset of ELF32 used by the spike, with bounds checks."""
    if len(data) < 52:
        raise ValueError("ELF header is truncated")
    fields = struct.unpack_from("<16sHHIIIIIHHHHHH", data, 0)
    ident, e_type, e_machine, e_version, e_entry, e_phoff, _e_shoff, _flags, e_ehsize, e_phentsize, e_phnum, *_ = fields
    if ident[:4] != b"\x7fELF":
        raise ValueError("Invalid ELF magic")
    if ident[4] != 1 or ident[5] != 1 or ident[6] != 1:
        raise ValueError("Expected ELF32 little-endian current-version input")
    if e_type != 2:
        raise ValueError(f"Expected ET_EXEC (2), got {e_type}")
    if e_machine != 8:
        raise ValueError(f"Expected EM_MIPS (8), got {e_machine}")
    if e_version != 1 or e_ehsize != 52:
        raise ValueError("Unsupported ELF version or header size")
    if e_phentsize != 32 or e_phnum == 0:
        raise ValueError("Unsupported or missing ELF program headers")
    if e_phoff > len(data) or e_phnum > (len(data) - e_phoff) // e_phentsize:
        raise ValueError("Program header table extends beyond input")

    executable: tuple[int, int, int] | None = None
    for index in range(e_phnum):
        p_type, p_offset, p_vaddr, _p_paddr, p_filesz, p_memsz, p_flags, p_align = struct.unpack_from("<IIIIIIII", data, e_phoff + index * e_phentsize)
        if p_type != 1 or not (p_flags & 1):  # PT_LOAD and PF_X
            continue
        if p_filesz > p_memsz:
            raise ValueError("Executable segment p_filesz exceeds p_memsz")
        if p_vaddr + p_memsz > 0x100000000:
            raise ValueError("Executable segment virtual address range overflows ELF32")
        if p_offset > len(data) or p_filesz > len(data) - p_offset:
            raise ValueError("Executable segment extends beyond input")
        if p_align not in (0, 1):
            if (p_align & (p_align - 1)) != 0:
                raise ValueError("Executable segment alignment is not a power of two")
            if (p_offset % p_align) != (p_vaddr % p_align):
                raise ValueError("Executable segment alignment is inconsistent")
        if executable is not None:
            raise ValueError("Spike currently expects exactly one executable PT_LOAD segment")
        executable = (p_offset, p_vaddr, p_filesz)
    if executable is None:
        raise ValueError("No executable PT_LOAD segment found")
    p_offset, p_vaddr, p_filesz = executable
    if p_filesz == 0 or p_filesz % 4:
        raise ValueError("Executable segment must contain aligned 32-bit instructions")
    if not (p_vaddr <= e_entry < p_vaddr + p_filesz):
        raise ValueError("ELF entry point is outside the executable segment")
    code_bytes = data[p_offset:p_offset + p_filesz]
    words = {p_vaddr + off: struct.unpack_from("<I", code_bytes, off)[0] for off in range(0, len(code_bytes), 4)}
    return e_entry, words, {"entry": e_entry, "segment_vaddr": p_vaddr, "segment_size": p_filesz, "instruction_count": len(words)}


def decode_instruction(pc: int, word: int) -> dict[str, Any]:
    op = (word >> 26) & 0x3F
    rs = (word >> 21) & 0x1F
    rt = (word >> 16) & 0x1F
    rd = (word >> 11) & 0x1F
    shamt = (word >> 6) & 0x1F
    funct = word & 0x3F
    imm = word & 0xFFFF
    simm = sign_extend_16(imm)
    if op == 0x00:
        if funct == 0x21 and shamt == 0:
            return {"pc": pc, "word": word, "op": "addu", "rs": rs, "rt": rt, "rd": rd}
        if funct in (0x24, 0x25, 0x26, 0x27) and shamt == 0:
            name = {0x24: "and", 0x25: "or", 0x26: "xor", 0x27: "nor"}[funct]
            return {"pc": pc, "word": word, "op": name, "rs": rs, "rt": rt, "rd": rd}
        if funct == 0x2A and shamt == 0:
            return {"pc": pc, "word": word, "op": "slt", "rs": rs, "rt": rt, "rd": rd}
        if funct == 0x2B and shamt == 0:
            return {"pc": pc, "word": word, "op": "sltu", "rs": rs, "rt": rt, "rd": rd}
        if funct == 0x08 and rt == 0 and rd == 0 and shamt == 0:
            return {"pc": pc, "word": word, "op": "jr", "rs": rs}
        if funct == 0x00:
            if rs != 0:
                raise ValueError(f"SLL requires rs=0 (word 0x{word:08X}) at 0x{pc:08X}")
            if rt == 0 and rd == 0 and shamt == 0:
                return {"pc": pc, "word": word, "op": "nop"}
            return {"pc": pc, "word": word, "op": "sll", "rs": rs, "rt": rt, "rd": rd, "shamt": shamt}
        raise ValueError(f"Unsupported SPECIAL instruction 0x{word:08X} at 0x{pc:08X}")
    if op == 0x09:
        return {"pc": pc, "word": word, "op": "addiu", "rs": rs, "rt": rt, "imm": simm}
    if op == 0x0A:
        return {"pc": pc, "word": word, "op": "slti", "rs": rs, "rt": rt, "imm": simm}
    if op == 0x0B:
        return {"pc": pc, "word": word, "op": "sltiu", "rs": rs, "rt": rt, "imm": simm}
    if op == 0x19:
        return {"pc": pc, "word": word, "op": "daddiu", "rs": rs, "rt": rt, "imm": simm}
    if op in (0x0C, 0x0D, 0x0E):
        name = {0x0C: "andi", 0x0D: "ori", 0x0E: "xori"}[op]
        return {"pc": pc, "word": word, "op": name, "rs": rs, "rt": rt, "imm": imm}
    if op == 0x0F:
        if rs != 0:
            raise ValueError(f"LUI requires rs=0 (word 0x{word:08X}) at 0x{pc:08X}")
        return {"pc": pc, "word": word, "op": "lui", "rs": rs, "rt": rt, "imm": imm}
    if op == 0x23:
        return {"pc": pc, "word": word, "op": "lw", "rs": rs, "rt": rt, "imm": simm}
    if op == 0x2B:
        return {"pc": pc, "word": word, "op": "sw", "rs": rs, "rt": rt, "imm": simm}
    if op in (0x04, 0x05):
        target = (pc + 4 + (simm << 2)) & 0xFFFFFFFF
        return {"pc": pc, "word": word, "op": "beq" if op == 0x04 else "bne", "rs": rs, "rt": rt, "imm": simm, "target": target}
    if op in (0x02, 0x03):
        target = ((pc + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)
        return {"pc": pc, "word": word, "op": "j" if op == 0x02 else "jal", "target": target}
    raise ValueError(f"Unsupported opcode 0x{op:02X} (word 0x{word:08X}) at 0x{pc:08X}")


def decode_program(words: dict[int, int]) -> dict[int, dict[str, Any]]:
    decoded = {pc: decode_instruction(pc, word) for pc, word in sorted(words.items())}
    control_ops = {"beq", "bne", "j", "jal", "jr"}
    for pc, ins in decoded.items():
        previous = decoded.get(pc - 4)
        if previous and previous["op"] in control_ops and ins["op"] in control_ops:
            raise ValueError(f"Control transfer in delay slot at 0x{pc:08X} is outside this spike's supported subset")
        if ins["op"] in control_ops and (pc + 4) not in decoded:
            raise ValueError(f"Missing delay-slot instruction after control transfer at 0x{pc:08X}")
        if ins["op"] in {"beq", "bne", "j", "jal"} and ins["target"] not in decoded:
            raise ValueError(f"Static control-flow target 0x{ins['target']:08X} is outside this spike's code model")
    return decoded


def initial_state(entry: int) -> dict[str, Any]:
    regs = [0] * 32
    regs[RA] = RETURN_SENTINEL
    return {"pc": entry, "registers": regs, "memory": {}, "trace": [], "halted": False}


def execute_oracle(entry: int, words: dict[int, int]) -> dict[str, Any]:
    """Small reference interpreter used only as a differential-test oracle."""
    decoded = decode_program(words)
    s = initial_state(entry)
    pending_target: int | None = None
    for _ in range(MAX_STEPS):
        pc = s["pc"]
        ins = decoded.get(pc)
        if ins is None:
            s["halted"] = True
            break
        was_delay_slot = pending_target is not None
        delay_target = pending_target
        pending_target = None
        s["trace"].append(pc)
        op = ins["op"]
        r = s["registers"]
        new_target: int | None = None
        if op == "nop":
            pass
        elif op == "addiu":
            value = ((r[ins["rs"]] & 0xFFFFFFFF) + (ins["imm"] & 0xFFFFFFFF)) & 0xFFFFFFFF
            result = sign_extend_32(value)
            if ins["rt"]:
                r[ins["rt"]] = result & 0xFFFFFFFFFFFFFFFF
        elif op == "daddiu":
            value = (r[ins["rs"]] + ins["imm"]) & 0xFFFFFFFFFFFFFFFF
            if ins["rt"]:
                r[ins["rt"]] = value
        elif op == "addu":
            value = ((r[ins["rs"]] & 0xFFFFFFFF) + (r[ins["rt"]] & 0xFFFFFFFF)) & 0xFFFFFFFF
            result = sign_extend_32(value)
            if ins["rd"]:
                r[ins["rd"]] = result & 0xFFFFFFFFFFFFFFFF
        elif op == "sll":
            value = ((r[ins["rt"]] & 0xFFFFFFFF) << ins["shamt"]) & 0xFFFFFFFF
            result = sign_extend_32(value)
            if ins["rd"]:
                r[ins["rd"]] = result & 0xFFFFFFFFFFFFFFFF
        elif op == "and":
            result = r[ins["rs"]] & r[ins["rt"]]
            if ins["rd"]:
                r[ins["rd"]] = result & 0xFFFFFFFFFFFFFFFF
        elif op == "or":
            result = r[ins["rs"]] | r[ins["rt"]]
            if ins["rd"]:
                r[ins["rd"]] = result & 0xFFFFFFFFFFFFFFFF
        elif op == "xor":
            result = r[ins["rs"]] ^ r[ins["rt"]]
            if ins["rd"]:
                r[ins["rd"]] = result & 0xFFFFFFFFFFFFFFFF
        elif op == "nor":
            result = ~(r[ins["rs"]] | r[ins["rt"]])
            if ins["rd"]:
                r[ins["rd"]] = result & 0xFFFFFFFFFFFFFFFF
        elif op == "slt":
            result = slt64(r[ins["rs"]], r[ins["rt"]])
            if ins["rd"]:
                r[ins["rd"]] = result
        elif op == "sltu":
            result = sltu64(r[ins["rs"]], r[ins["rt"]])
            if ins["rd"]:
                r[ins["rd"]] = result
        elif op == "slti":
            result = slt64(r[ins["rs"]], ins["imm"])
            if ins["rt"]:
                r[ins["rt"]] = result
        elif op == "sltiu":
            result = sltu64(r[ins["rs"]], ins["imm"])
            if ins["rt"]:
                r[ins["rt"]] = result
        elif op == "ori":
            value = (r[ins["rs"]] | (ins["imm"] & 0xFFFF)) & 0xFFFFFFFFFFFFFFFF
            if ins["rt"]:
                r[ins["rt"]] = value
        elif op == "andi":
            value = ((r[ins["rs"]] & 0xFFFFFFFF) & ins["imm"]) & 0xFFFFFFFF
            if ins["rt"]:
                r[ins["rt"]] = value
        elif op == "xori":
            value = (r[ins["rs"]] ^ (ins["imm"] & 0xFFFF)) & 0xFFFFFFFFFFFFFFFF
            if ins["rt"]:
                r[ins["rt"]] = value
        elif op == "lui":
            value = (ins["imm"] << 16) & 0xFFFFFFFF
            result = sign_extend_32(value)
            if ins["rt"]:
                r[ins["rt"]] = result & 0xFFFFFFFFFFFFFFFF
        elif op == "lw":
            address = ((r[ins["rs"]] & 0xFFFFFFFF) + ins["imm"]) & 0xFFFFFFFF
            if address not in s["memory"]:
                raise ValueError(f"Oracle read from uninitialized memory 0x{address:08X}")
            result = sign_extend_32(s["memory"][address])
            if ins["rt"]:
                r[ins["rt"]] = result & 0xFFFFFFFFFFFFFFFF
        elif op == "sw":
            address = ((r[ins["rs"]] & 0xFFFFFFFF) + ins["imm"]) & 0xFFFFFFFF
            s["memory"][address] = r[ins["rt"]] & 0xFFFFFFFF
        elif op == "beq":
            new_target = ins["target"] if r[ins["rs"]] == r[ins["rt"]] else (pc + 8) & 0xFFFFFFFF
        elif op == "bne":
            new_target = ins["target"] if r[ins["rs"]] != r[ins["rt"]] else (pc + 8) & 0xFFFFFFFF
        elif op == "j":
            new_target = ins["target"]
        elif op == "jal":
            r[RA] = (pc + 8) & 0xFFFFFFFF
            new_target = ins["target"]
        elif op == "jr":
            new_target = r[ins["rs"]] & 0xFFFFFFFF
        else:
            raise AssertionError(f"Decoder returned unknown operation {op}")
        r[ZERO] = 0
        if was_delay_slot:
            assert delay_target is not None
            s["pc"] = delay_target
        elif new_target is not None:
            s["pc"] = (pc + 4) & 0xFFFFFFFF
            pending_target = new_target
        else:
            s["pc"] = (pc + 4) & 0xFFFFFFFF
    else:
        raise RuntimeError(f"Oracle exceeded {MAX_STEPS} instructions")
    if not s["halted"]:
        raise RuntimeError("Oracle stopped without reaching a non-code guest PC")
    # Normalize JSON object keys and values for exact differential comparison.
    s["memory"] = {str(addr): value for addr, value in sorted(s["memory"].items())}
    return s


def emit_cpp(decoded: dict[int, dict[str, Any]], entry: int) -> str:
    cases: list[str] = []
    for pc, ins in sorted(decoded.items()):
        op = ins["op"]
        lines = [f"        case 0x{pc:08X}u:", "            s.trace.push_back(current_pc);"]
        if op == "nop":
            lines.append("            break;")
        elif op == "addiu":
            lines.append(f"            write_register(s, {ins['rt']}u, addiu32(s.registers[{ins['rs']}u], {ins['imm']}));")
            lines.append("            break;")
        elif op == "addu":
            lines.append(f"            write_register(s, {ins['rd']}u, addu32(s.registers[{ins['rs']}u], s.registers[{ins['rt']}u]));")
            lines.append("            break;")
        elif op == "ori":
            lines.append(f"            write_register(s, {ins['rt']}u, ori32(s.registers[{ins['rs']}u], 0x{ins['imm']:04X}u));")
            lines.append("            break;")
        elif op == "lw":
            lines.append(f"            write_register(s, {ins['rt']}u, load_word(s, effective_address(s.registers[{ins['rs']}u], {ins['imm']})));")
            lines.append("            break;")
        elif op == "sw":
            lines.append(f"            store_word(s, effective_address(s.registers[{ins['rs']}u], {ins['imm']}), static_cast<std::uint32_t>(s.registers[{ins['rt']}u]));")
            lines.append("            break;")
        elif op in ("beq", "bne"):
            comparison = "==" if op == "beq" else "!="
            lines.append(f"            new_pending = true; new_target = (s.registers[{ins['rs']}u] {comparison} s.registers[{ins['rt']}u]) ? 0x{ins['target']:08X}u : static_cast<std::uint32_t>(current_pc + 8u);")
            lines.append("            break;")
        elif op == "j":
            lines.append(f"            new_pending = true; new_target = 0x{ins['target']:08X}u;")
            lines.append("            break;")
        elif op == "jal":
            lines.append("            write_register(s, 31u, static_cast<std::uint64_t>(current_pc + 8u));")
            lines.append(f"            new_pending = true; new_target = 0x{ins['target']:08X}u;")
            lines.append("            break;")
        elif op == "jr":
            lines.append(f"            new_pending = true; new_target = static_cast<std::uint32_t>(s.registers[{ins['rs']}u]);")
            lines.append("            break;")
        else:
            raise ValueError(f"Cannot emit unsupported instruction {op}")
        cases.extend(lines)
    body = "\n".join(cases)
    ori_helper = (
        "std::uint64_t ori32(std::uint64_t lhs, std::uint32_t immediate) {{\n"
        "    return lhs | static_cast<std::uint64_t>(immediate);\n"
        "}}\n\n"
    ) if any(ins["op"] == "ori" for ins in decoded.values()) else ""
    return f'''// Generated by tools/rptp_gate0_spike.py. Do not edit by hand.
// This is a narrow ISA-subset spike, not a complete R5900 implementation.
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

{ori_helper}std::uint32_t effective_address(std::uint64_t base, std::int32_t offset) {{
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
    for (std::size_t step = 0; step < {MAX_STEPS}u; ++step) {{
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
    State state;
    state.pc = 0x{entry:08X}u;
    state.registers[31] = 0x{RETURN_SENTINEL:08X}u;
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
}}
'''


def normalize_state(s: dict[str, Any]) -> dict[str, Any]:
    memory = [[int(address), int(value)] for address, value in sorted(s["memory"].items(), key=lambda kv: int(kv[0]))]
    return {"halted": bool(s["halted"]), "pc": int(s["pc"]), "registers": [int(x) for x in s["registers"]], "memory": memory, "trace": [int(x) for x in s["trace"]]}


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def manifest_entry_hash(root: Path, relative_path: Path) -> str:
    manifest_path = root / "tests/fixtures/MANIFEST"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest.get("fixtures", []):
        if entry.get("path") == relative_path.as_posix():
            return str(entry.get("sha256", ""))
    raise ValueError(f"Fixture is not registered in tests/fixtures/MANIFEST: {relative_path.as_posix()}")


def compile_generated(source: Path, output: Path, compiler: str) -> list[str]:
    selected = compiler
    if selected == "auto":
        selected = "cl" if os.name == "nt" and shutil.which("cl") else (os.environ.get("CXX") or "c++")
    compiler_path = shutil.which(selected)
    if not compiler_path:
        raise RuntimeError(f"Compiler '{selected}' was not found on PATH")
    if Path(compiler_path).name.lower() in ("cl", "cl.exe"):
        command = [compiler_path, "/nologo", "/std:c++20", "/EHsc", "/W4", "/WX", "/permissive-", "/utf-8", str(source), f"/Fe:{output}"]
    else:
        command = [compiler_path, "-std=c++20", "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-O2", str(source), "-o", str(output)]
    proc = subprocess.run(command, cwd=source.parent, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError("Compiler failed.\nCOMMAND: " + " ".join(command) + "\nSTDOUT:\n" + proc.stdout + "\nSTDERR:\n" + proc.stderr)
    return command


def run_spike(out_dir: Path, compiler: str) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    fixture_bytes = build_fixture_elf()
    tracked_fixture = ROOT / FIXTURE_REL
    if not tracked_fixture.exists():
        raise RuntimeError(f"Registered synthetic fixture is missing: {tracked_fixture}")
    tracked_hash = hashlib.sha256(tracked_fixture.read_bytes()).hexdigest()
    expected_hash = manifest_entry_hash(ROOT, FIXTURE_REL)
    generated_hash = hashlib.sha256(fixture_bytes).hexdigest()
    if tracked_hash != expected_hash:
        raise RuntimeError("Registered fixture hash mismatch; inspect the MANIFEST before proceeding")
    if generated_hash != tracked_hash:
        raise RuntimeError("Deterministic fixture generator does not match the registered fixture")

    fixture_copy = out_dir / "gate0-fixture.elf"
    fixture_copy.write_bytes(fixture_bytes)
    entry, words, elf_info = parse_elf(fixture_bytes)
    decoded = decode_program(words)
    oracle = normalize_state(execute_oracle(entry, words))
    source_text_1 = emit_cpp(decoded, entry)
    source_text_2 = emit_cpp(decoded, entry)
    if source_text_1.encode("utf-8") != source_text_2.encode("utf-8"):
        raise RuntimeError("Generated source is not deterministic")
    source = out_dir / "generated.cpp"
    source.write_text(source_text_1, encoding="utf-8", newline="\n")
    exe = out_dir / ("rptp-gate0-spike.exe" if os.name == "nt" else "rptp-gate0-spike")
    command = compile_generated(source, exe, compiler)
    proc = subprocess.run([str(exe)], cwd=out_dir, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError("Generated executable failed.\nSTDOUT:\n" + proc.stdout + "\nSTDERR:\n" + proc.stderr)
    try:
        native = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Generated executable did not emit valid JSON: {proc.stdout!r}") from exc
    if native != oracle:
        diff = {"oracle": oracle, "native": native}
        write_json(out_dir / "differential-mismatch.json", diff)
        raise RuntimeError("Differential mismatch; see differential-mismatch.json")

    assertions = {
        "return_value_v0_is_42": native["registers"][V0] == 42,
        "stored_and_loaded_value_is_12": native["registers"][T2] == 12 and native["registers"][T4] == 12 and native["memory"] == [[MEMORY_ADDRESS, 12]],
        "bne_not_taken_delay_slot_executed": native["registers"][S4] == 23,
        "beq_taken_delay_slot_executed": native["registers"][S0] == 17 and native["registers"][S1] == 1,
        "jal_jr_delay_slots_executed": native["registers"][S3] == 55 and native["registers"][S2] == 99,
        "zero_register_remains_zero": native["registers"][ZERO] == 0,
        "returned_to_sentinel": native["pc"] == RETURN_SENTINEL and native["halted"] is True,
    }
    failed = [name for name, passed in assertions.items() if not passed]
    if failed:
        raise RuntimeError("Gate 0 assertion(s) failed: " + ", ".join(failed))
    write_json(out_dir / "oracle.json", oracle)
    write_json(out_dir / "native.json", native)
    report = {
        "status": "PASS_LOCAL_DIFFERENTIAL_SPIKE",
        "scope": "synthetic ELF32/EM_MIPS; ADDIU, ADDU, LW, SW, BEQ, BNE, J, JAL, JR, NOP; delay slots",
        "elf": elf_info,
        "fixture_sha256": generated_hash,
        "generated_cpp_sha256": hashlib.sha256(source_text_1.encode("utf-8")).hexdigest(),
        "compiler": command[0],
        "compiler_command": command,
        "host_platform": sys.platform,
        "native_matches_oracle": True,
        "assertions": assertions,
        "trace_steps": len(native["trace"]),
        "windows_msvc_verified": bool(os.name == "nt" and Path(command[0]).name.lower() in ("cl", "cl.exe")),
        "note": "The Windows MSVC field is true only when this run actually executes on Windows with cl.exe. A host compiler pass does not prove an MSVC/Windows build.",
    }
    write_json(out_dir / "report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("build/gate0"), help="Output directory (relative to repo root unless absolute)")
    parser.add_argument("--compiler", default="auto", help="C++ compiler executable; use 'cl' in Visual Studio Developer PowerShell")
    parser.add_argument("--print-elf", action="store_true", help="Print synthetic fixture size and SHA-256, without compiling")
    args = parser.parse_args()
    out = args.out if args.out.is_absolute() else ROOT / args.out
    try:
        if args.print_elf:
            data = build_fixture_elf()
            entry, words, info = parse_elf(data)
            print(json.dumps({"sha256": hashlib.sha256(data).hexdigest(), **info}, indent=2, sort_keys=True))
            return 0
        report = run_spike(out, args.compiler)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    except Exception as exc:  # CLI boundary: report a deterministic failure instead of a traceback by default.
        print(f"RPTP Gate 0 spike failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
