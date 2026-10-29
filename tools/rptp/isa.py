# SPDX-License-Identifier: GPL-3.0-or-later
"""R5900 instruction catalog and decoder.

Encodings are derived from neutral public documentation: the Sony/Toshiba
EE Core Instruction Set Manual, the MIPS III architecture manual and ps2tek
(https://psi-rockin.github.io/ps2tek/).  No emulator or recompiler
implementation source was used.  Entries carry an explicit verification
label; ``provisional`` entries are implemented from documented pseudocode
but still need an independent review against the hardware manual before
they may be treated as verified.

The decoder never guesses an instruction: an unrecognised word becomes an
``unknown`` instruction that static analysis and code generation must treat
as unsupported rather than silently lowering it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

MASK32 = 0xFFFFFFFF
MASK64 = 0xFFFFFFFFFFFFFFFF
MASK128 = (1 << 128) - 1

# Verification labels used in the catalog and generated documentation.
GENERIC = "generic-mips-cross-checked"
MANUAL = "manual-cross-checked"
PROVISIONAL = "provisional"
UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class OpSpec:
    mnemonic: str
    fmt: str
    cls: str
    supported: bool = True
    delay_slot: bool = False
    writes_hi_lo: bool = False
    verification: str = PROVISIONAL
    citation: str = ""
    note: str = ""


def _op(mnemonic: str, fmt: str, cls: str, **kwargs: Any) -> OpSpec:
    return OpSpec(mnemonic=mnemonic, fmt=fmt, cls=cls, **kwargs)


# ---------------------------------------------------------------------------
# Core tables (ps2tek encoding tables; MIPS III cross-check).
# ---------------------------------------------------------------------------

SPECIAL: dict[int, OpSpec] = {
    0x00: _op("sll", "rd,rt,sa", "special", verification=GENERIC),
    0x02: _op("srl", "rd,rt,sa", "special", verification=GENERIC),
    0x03: _op("sra", "rd,rt,sa", "special", verification=GENERIC),
    0x04: _op("sllv", "rd,rt,rs", "special", verification=GENERIC),
    0x06: _op("srlv", "rd,rt,rs", "special", verification=GENERIC),
    0x07: _op("srav", "rd,rt,rs", "special", verification=GENERIC),
    0x08: _op("jr", "rs", "special", delay_slot=True, verification=GENERIC),
    0x09: _op("jalr", "rd,rs", "special", delay_slot=True, verification=GENERIC),
    0x0A: _op("movz", "rd,rs,rt", "special", verification=GENERIC),
    0x0B: _op("movn", "rd,rs,rt", "special", verification=GENERIC),
    0x0C: _op("syscall", "code", "special", supported=False, verification=MANUAL,
              note="Requires PS2 kernel/SYSCALL dispatch; decoded for diagnostics only."),
    0x0D: _op("break", "code", "special", supported=False, verification=MANUAL,
              note="Requires exception handling; decoded for diagnostics only."),
    0x0F: _op("sync", "stype", "special", verification=GENERIC,
              note="No architecturally visible effect in a single-core functional model."),
    0x10: _op("mfhi", "rd", "special", verification=PROVISIONAL),
    0x11: _op("mthi", "rs", "special", verification=PROVISIONAL),
    0x12: _op("mflo", "rd", "special", verification=PROVISIONAL),
    0x13: _op("mtlo", "rs", "special", verification=PROVISIONAL),
    0x14: _op("dsllv", "rd,rt,rs", "special", verification=GENERIC),
    0x16: _op("dsrlv", "rd,rt,rs", "special", verification=GENERIC),
    0x17: _op("dsrav", "rd,rt,rs", "special", verification=GENERIC),
    0x18: _op("mult", "rs,rt", "special", writes_hi_lo=True, verification=PROVISIONAL),
    0x19: _op("multu", "rs,rt", "special", writes_hi_lo=True, verification=PROVISIONAL),
    0x1A: _op("div", "rs,rt", "special", writes_hi_lo=True, verification=PROVISIONAL),
    0x1B: _op("divu", "rs,rt", "special", writes_hi_lo=True, verification=PROVISIONAL),
    0x20: _op("add", "rd,rs,rt", "special", verification=GENERIC,
              note="Signed-overflow trap; trap delivery is not implemented yet."),
    0x21: _op("addu", "rd,rs,rt", "special", verification=GENERIC),
    0x22: _op("sub", "rd,rs,rt", "special", verification=GENERIC,
              note="Signed-overflow trap; trap delivery is not implemented yet."),
    0x23: _op("subu", "rd,rs,rt", "special", verification=GENERIC),
    0x24: _op("and", "rd,rs,rt", "special", verification=GENERIC),
    0x25: _op("or", "rd,rs,rt", "special", verification=GENERIC),
    0x26: _op("xor", "rd,rs,rt", "special", verification=GENERIC),
    0x27: _op("nor", "rd,rs,rt", "special", verification=GENERIC),
    0x28: _op("mfsa", "rd", "special", supported=False, verification=MANUAL),
    0x29: _op("mtsa", "rs", "special", supported=False, verification=MANUAL),
    0x2A: _op("slt", "rd,rs,rt", "special", verification=GENERIC),
    0x2B: _op("sltu", "rd,rs,rt", "special", verification=GENERIC),
    0x2C: _op("dadd", "rd,rs,rt", "special", verification=GENERIC,
              note="Signed-overflow trap; trap delivery is not implemented yet."),
    0x2D: _op("daddu", "rd,rs,rt", "special", verification=GENERIC),
    0x2E: _op("dsub", "rd,rs,rt", "special", verification=GENERIC,
              note="Signed-overflow trap; trap delivery is not implemented yet."),
    0x2F: _op("dsubu", "rd,rs,rt", "special", verification=GENERIC),
    0x30: _op("tge", "rs,rt", "special", supported=False, verification=GENERIC),
    0x31: _op("tgeu", "rs,rt", "special", supported=False, verification=GENERIC),
    0x32: _op("tlt", "rs,rt", "special", supported=False, verification=GENERIC),
    0x33: _op("tltu", "rs,rt", "special", supported=False, verification=GENERIC),
    0x34: _op("teq", "rs,rt", "special", supported=False, verification=GENERIC),
    0x36: _op("tne", "rs,rt", "special", supported=False, verification=GENERIC),
    0x38: _op("dsll", "rd,rt,sa", "special", verification=GENERIC),
    0x3A: _op("dsrl", "rd,rt,sa", "special", verification=GENERIC),
    0x3B: _op("dsra", "rd,rt,sa", "special", verification=GENERIC),
    0x3C: _op("dsll32", "rd,rt,sa", "special", verification=GENERIC),
    0x3E: _op("dsrl32", "rd,rt,sa", "special", verification=GENERIC),
    0x3F: _op("dsra32", "rd,rt,sa", "special", verification=GENERIC),
}

REGIMM: dict[int, OpSpec] = {
    0x00: _op("bltz", "rs,offset", "regimm", delay_slot=True, verification=GENERIC),
    0x01: _op("bgez", "rs,offset", "regimm", delay_slot=True, verification=GENERIC),
    0x02: _op("bltzl", "rs,offset", "regimm", supported=False, delay_slot=True, verification=MANUAL,
              note="Branch-likely delay-slot nullification is not implemented yet."),
    0x03: _op("bgezl", "rs,offset", "regimm", supported=False, delay_slot=True, verification=MANUAL,
              note="Branch-likely delay-slot nullification is not implemented yet."),
    0x08: _op("tgei", "rs,imm", "regimm", supported=False, verification=GENERIC),
    0x09: _op("tgeiu", "rs,imm", "regimm", supported=False, verification=GENERIC),
    0x0A: _op("tlti", "rs,imm", "regimm", supported=False, verification=GENERIC),
    0x0B: _op("tltiu", "rs,imm", "regimm", supported=False, verification=GENERIC),
    0x0C: _op("teqi", "rs,imm", "regimm", supported=False, verification=GENERIC),
    0x0E: _op("tnei", "rs,imm", "regimm", supported=False, verification=GENERIC),
    0x10: _op("bltzal", "rs,offset", "regimm", delay_slot=True, verification=GENERIC,
              note="Writes GPR 31 unconditionally."),
    0x11: _op("bgezal", "rs,offset", "regimm", delay_slot=True, verification=GENERIC,
              note="Writes GPR 31 unconditionally."),
    0x12: _op("bltzall", "rs,offset", "regimm", supported=False, delay_slot=True, verification=MANUAL,
              note="Branch-likely delay-slot nullification is not implemented yet."),
    0x13: _op("bgezall", "rs,offset", "regimm", supported=False, delay_slot=True, verification=MANUAL,
              note="Branch-likely delay-slot nullification is not implemented yet."),
    0x18: _op("mtsab", "rs,imm", "regimm", supported=False, verification=MANUAL),
    0x19: _op("mtsah", "rs,imm", "regimm", supported=False, verification=MANUAL),
}

PRIMARY: dict[int, OpSpec] = {
    0x02: _op("j", "target", "jump", delay_slot=True, verification=GENERIC),
    0x03: _op("jal", "target", "jump", delay_slot=True, verification=GENERIC),
    0x04: _op("beq", "rs,rt,offset", "branch", delay_slot=True, verification=GENERIC),
    0x05: _op("bne", "rs,rt,offset", "branch", delay_slot=True, verification=GENERIC),
    0x06: _op("blez", "rs,offset", "branch", delay_slot=True, verification=GENERIC),
    0x07: _op("bgtz", "rs,offset", "branch", delay_slot=True, verification=GENERIC),
    0x08: _op("addi", "rt,rs,imm", "immediate", verification=GENERIC,
              note="Signed-overflow trap; trap delivery is not implemented yet."),
    0x09: _op("addiu", "rt,rs,imm", "immediate", verification=GENERIC),
    0x0A: _op("slti", "rt,rs,imm", "immediate", verification=GENERIC),
    0x0B: _op("sltiu", "rt,rs,imm", "immediate", verification=GENERIC),
    0x0C: _op("andi", "rt,rs,imm", "immediate", verification=GENERIC),
    0x0D: _op("ori", "rt,rs,imm", "immediate", verification=GENERIC),
    0x0E: _op("xori", "rt,rs,imm", "immediate", verification=GENERIC),
    0x0F: _op("lui", "rt,imm", "immediate", verification=GENERIC),
    0x10: _op("cop0", "cop0", "cop0", supported=False, verification=MANUAL,
              note="COP0 state, exceptions and ERET are not implemented yet."),
    0x11: _op("cop1", "cop1", "cop1", supported=False, verification=MANUAL,
              note="R5900 COP1 floating point is not implemented yet."),
    0x12: _op("cop2", "cop2", "cop2", supported=False, verification=MANUAL,
              note="VU0 macro-mode COP2 is not implemented yet."),
    0x14: _op("beql", "rs,rt,offset", "branch", supported=False, delay_slot=True, verification=MANUAL,
              note="Branch-likely delay-slot nullification is not implemented yet."),
    0x15: _op("bnel", "rs,rt,offset", "branch", supported=False, delay_slot=True, verification=MANUAL,
              note="Branch-likely delay-slot nullification is not implemented yet."),
    0x16: _op("blezl", "rs,offset", "branch", supported=False, delay_slot=True, verification=MANUAL,
              note="Branch-likely delay-slot nullification is not implemented yet."),
    0x17: _op("bgtzl", "rs,offset", "branch", supported=False, delay_slot=True, verification=MANUAL,
              note="Branch-likely delay-slot nullification is not implemented yet."),
    0x18: _op("daddi", "rt,rs,imm", "immediate", verification=GENERIC,
              note="Signed-overflow trap; trap delivery is not implemented yet."),
    0x19: _op("daddiu", "rt,rs,imm", "immediate", verification=GENERIC),
    0x1A: _op("ldl", "rt,offset(base)", "load", supported=False, verification=MANUAL),
    0x1B: _op("ldr", "rt,offset(base)", "load", supported=False, verification=MANUAL),
    0x1C: _op("mmi", "mmi", "mmi", verification=MANUAL),
    0x1E: _op("lq", "rt,offset(base)", "load", verification=MANUAL),
    0x1F: _op("sq", "rt,offset(base)", "store", verification=MANUAL),
    0x20: _op("lb", "rt,offset(base)", "load", verification=GENERIC),
    0x21: _op("lh", "rt,offset(base)", "load", verification=GENERIC),
    0x22: _op("lwl", "rt,offset(base)", "load", supported=False, verification=MANUAL),
    0x23: _op("lw", "rt,offset(base)", "load", verification=GENERIC),
    0x24: _op("lbu", "rt,offset(base)", "load", verification=GENERIC),
    0x25: _op("lhu", "rt,offset(base)", "load", verification=GENERIC),
    0x26: _op("lwr", "rt,offset(base)", "load", supported=False, verification=MANUAL),
    0x27: _op("lwu", "rt,offset(base)", "load", verification=GENERIC),
    0x28: _op("sb", "rt,offset(base)", "store", verification=GENERIC),
    0x29: _op("sh", "rt,offset(base)", "store", verification=GENERIC),
    0x2A: _op("swl", "rt,offset(base)", "store", supported=False, verification=MANUAL),
    0x2B: _op("sw", "rt,offset(base)", "store", verification=GENERIC),
    0x2C: _op("sdl", "rt,offset(base)", "store", supported=False, verification=MANUAL),
    0x2D: _op("sdr", "rt,offset(base)", "store", supported=False, verification=MANUAL),
    0x2E: _op("swr", "rt,offset(base)", "store", supported=False, verification=MANUAL),
    0x2F: _op("cache", "op,offset(base)", "cache", verification=MANUAL,
              note="Functional model treats cache maintenance as a no-op."),
    0x31: _op("lwc1", "rt,offset(base)", "load", supported=False, verification=MANUAL),
    0x33: _op("pref", "op,offset(base)", "cache", verification=MANUAL,
              note="Functional model treats prefetch as a no-op."),
    0x36: _op("lqc2", "rt,offset(base)", "load", supported=False, verification=MANUAL),
    0x37: _op("ld", "rt,offset(base)", "load", verification=GENERIC),
    0x39: _op("swc1", "rt,offset(base)", "store", supported=False, verification=MANUAL),
    0x3E: _op("sqc2", "rt,offset(base)", "store", supported=False, verification=MANUAL),
    0x3F: _op("sd", "rt,offset(base)", "store", verification=GENERIC),
}

# MMI encoding (primary opcode 0x1C).  Function values 0x08, 0x09, 0x28 and
# 0x29 select the MMI0/MMI2/MMI1/MMI3 subtables; the sub-opcode is bits 10:6.
# Everything else is a standalone MMI instruction keyed by the full 11-bit
# function field (bits 10:0), which is how PMFHL selectors are encoded.
MMI_SUBTABLE_SELECT = {0x08: 0, 0x09: 2, 0x28: 1, 0x29: 3}

MMI_GROUPS: dict[int, dict[int, OpSpec]] = {
    0: {
        0x00: _op("paddw", "rd,rs,rt", "mmi", verification=MANUAL),
        0x01: _op("psubw", "rd,rs,rt", "mmi", verification=MANUAL),
        0x02: _op("pcgtw", "rd,rs,rt", "mmi", verification=MANUAL),
        0x03: _op("pmaxw", "rd,rs,rt", "mmi", verification=MANUAL),
        0x04: _op("paddh", "rd,rs,rt", "mmi", verification=MANUAL),
        0x05: _op("psubh", "rd,rs,rt", "mmi", verification=MANUAL),
        0x06: _op("pcgth", "rd,rs,rt", "mmi", verification=MANUAL),
        0x07: _op("pmaxh", "rd,rs,rt", "mmi", verification=MANUAL),
        0x08: _op("paddb", "rd,rs,rt", "mmi", verification=MANUAL),
        0x09: _op("psubb", "rd,rs,rt", "mmi", verification=MANUAL),
        0x0A: _op("pcgtb", "rd,rs,rt", "mmi", verification=MANUAL),
        0x0C: _op("paddsw", "rd,rs,rt", "mmi", verification=MANUAL),
        0x0D: _op("psubsw", "rd,rs,rt", "mmi", verification=MANUAL),
        0x0E: _op("pextlw", "rd,rs,rt", "mmi", verification=MANUAL),
        0x0F: _op("ppacw", "rd,rs,rt", "mmi", verification=MANUAL),
        0x10: _op("paddsh", "rd,rs,rt", "mmi", verification=MANUAL),
        0x11: _op("psubsh", "rd,rs,rt", "mmi", verification=MANUAL),
        0x12: _op("pextlh", "rd,rs,rt", "mmi", verification=MANUAL),
        0x13: _op("ppach", "rd,rs,rt", "mmi", verification=MANUAL),
        0x14: _op("paddsb", "rd,rs,rt", "mmi", verification=MANUAL),
        0x15: _op("psubsb", "rd,rs,rt", "mmi", verification=MANUAL),
        0x16: _op("pextlb", "rd,rs,rt", "mmi", verification=MANUAL),
        0x17: _op("ppacb", "rd,rs,rt", "mmi", verification=MANUAL),
        0x1A: _op("pext5", "rd,rt", "mmi", verification=MANUAL),
        0x1B: _op("ppac5", "rd,rt", "mmi", verification=MANUAL),
    },
    1: {
        0x01: _op("pabsw", "rd,rt", "mmi", verification=MANUAL),
        0x02: _op("pceqw", "rd,rs,rt", "mmi", verification=MANUAL),
        0x03: _op("pminw", "rd,rs,rt", "mmi", verification=MANUAL),
        0x04: _op("padsbh", "rd,rs,rt", "mmi", verification=MANUAL),
        0x05: _op("pabsh", "rd,rt", "mmi", verification=MANUAL),
        0x06: _op("pceqh", "rd,rs,rt", "mmi", verification=MANUAL),
        0x07: _op("pminh", "rd,rs,rt", "mmi", verification=MANUAL),
        0x0A: _op("pceqb", "rd,rs,rt", "mmi", verification=MANUAL),
        0x0C: _op("padduw", "rd,rs,rt", "mmi", verification=MANUAL),
        0x0D: _op("psubuw", "rd,rs,rt", "mmi", verification=MANUAL),
        0x0E: _op("pextuw", "rd,rs,rt", "mmi", verification=MANUAL),
        0x10: _op("padduh", "rd,rs,rt", "mmi", verification=MANUAL),
        0x11: _op("psubuh", "rd,rs,rt", "mmi", verification=MANUAL),
        0x12: _op("pextuh", "rd,rs,rt", "mmi", verification=MANUAL),
        0x14: _op("paddub", "rd,rs,rt", "mmi", verification=MANUAL),
        0x15: _op("psubub", "rd,rs,rt", "mmi", verification=MANUAL),
        0x16: _op("pextub", "rd,rs,rt", "mmi", verification=MANUAL),
        0x17: _op("qfsrv", "rd,rs,rt", "mmi", verification=MANUAL),
    },
    2: {
        0x00: _op("pmaddw", "rd,rs,rt", "mmi", writes_hi_lo=True, verification=MANUAL),
        0x02: _op("psllvw", "rd,rt,rs", "mmi", verification=MANUAL),
        0x03: _op("psrlvw", "rd,rt,rs", "mmi", verification=MANUAL),
        0x04: _op("pmsubw", "rd,rs,rt", "mmi", writes_hi_lo=True, verification=MANUAL),
        0x08: _op("pmfhi", "rd", "mmi", verification=MANUAL),
        0x09: _op("pmflo", "rd", "mmi", verification=MANUAL),
        0x0A: _op("pinth", "rd,rs,rt", "mmi", verification=MANUAL),
        0x0C: _op("pmultw", "rd,rs,rt", "mmi", writes_hi_lo=True, verification=MANUAL),
        0x0D: _op("pdivw", "rs,rt", "mmi", writes_hi_lo=True, verification=MANUAL),
        0x0E: _op("pcpyld", "rd,rs,rt", "mmi", verification=MANUAL),
        0x10: _op("pmaddh", "rd,rs,rt", "mmi", writes_hi_lo=True, verification=MANUAL),
        0x11: _op("phmadh", "rd,rs,rt", "mmi", writes_hi_lo=True, verification=MANUAL),
        0x12: _op("pand", "rd,rs,rt", "mmi", verification=MANUAL),
        0x13: _op("pxor", "rd,rs,rt", "mmi", verification=MANUAL),
        0x14: _op("pmsubh", "rd,rs,rt", "mmi", writes_hi_lo=True, verification=MANUAL),
        0x15: _op("phmsbh", "rd,rs,rt", "mmi", writes_hi_lo=True, verification=MANUAL),
        0x1A: _op("pexeh", "rd,rt", "mmi", verification=MANUAL),
        0x1B: _op("prevh", "rd,rt", "mmi", verification=MANUAL),
        0x1C: _op("pmulth", "rd,rs,rt", "mmi", writes_hi_lo=True, verification=MANUAL),
        0x1D: _op("pdivbw", "rs,rt", "mmi", writes_hi_lo=True, verification=MANUAL),
        0x1E: _op("pexew", "rd,rt", "mmi", verification=MANUAL),
        0x1F: _op("prot3w", "rd,rt", "mmi", verification=MANUAL),
    },
    3: {
        0x00: _op("pmadduw", "rd,rs,rt", "mmi", writes_hi_lo=True, verification=MANUAL),
        0x03: _op("psravw", "rd,rt,rs", "mmi", verification=MANUAL),
        0x08: _op("pmthi", "rs", "mmi", writes_hi_lo=True, verification=MANUAL),
        0x09: _op("pmtlo", "rs", "mmi", writes_hi_lo=True, verification=MANUAL),
        0x0A: _op("pinteh", "rd,rs,rt", "mmi", verification=MANUAL),
        0x0C: _op("pmultuw", "rd,rs,rt", "mmi", writes_hi_lo=True, verification=MANUAL),
        0x0D: _op("pdivuw", "rs,rt", "mmi", writes_hi_lo=True, verification=MANUAL),
        0x0E: _op("pcpyud", "rd,rs,rt", "mmi", verification=MANUAL),
        0x12: _op("por", "rd,rs,rt", "mmi", verification=MANUAL),
        0x13: _op("pnor", "rd,rs,rt", "mmi", verification=MANUAL),
        0x1A: _op("pexch", "rd,rt", "mmi", verification=MANUAL),
        0x1B: _op("pcpyh", "rd,rt", "mmi", verification=MANUAL),
        0x1E: _op("pexcw", "rd,rt", "mmi", verification=MANUAL),
    },
}

# Standalone MMI instructions keyed by the full 11-bit function field.
MMI_STANDALONE: dict[int, OpSpec] = {
    0x000: _op("madd", "rd,rs,rt", "mmi", writes_hi_lo=True, verification=MANUAL),
    0x001: _op("maddu", "rd,rs,rt", "mmi", writes_hi_lo=True, verification=MANUAL),
    0x004: _op("plzcw", "rd,rs", "mmi", verification=MANUAL),
    0x010: _op("mfhi1", "rd", "mmi", verification=MANUAL),
    0x011: _op("mthi1", "rs", "mmi", writes_hi_lo=True, verification=MANUAL),
    0x012: _op("mflo1", "rd", "mmi", verification=MANUAL),
    0x013: _op("mtlo1", "rs", "mmi", writes_hi_lo=True, verification=MANUAL),
    0x018: _op("mult1", "rs,rt", "mmi", writes_hi_lo=True, verification=MANUAL),
    0x019: _op("multu1", "rs,rt", "mmi", writes_hi_lo=True, verification=MANUAL),
    0x01A: _op("div1", "rs,rt", "mmi", writes_hi_lo=True, verification=MANUAL),
    0x01B: _op("divu1", "rs,rt", "mmi", writes_hi_lo=True, verification=MANUAL),
    0x020: _op("madd1", "rd,rs,rt", "mmi", writes_hi_lo=True, verification=MANUAL),
    0x021: _op("maddu1", "rd,rs,rt", "mmi", writes_hi_lo=True, verification=MANUAL),
    0x030: _op("pmfhl.lw", "rd", "mmi", verification=MANUAL),
    0x070: _op("pmfhl.uw", "rd", "mmi", verification=MANUAL),
    0x0B0: _op("pmfhl.slw", "rd", "mmi", verification=MANUAL),
    0x0F0: _op("pmfhl.lh", "rd", "mmi", verification=MANUAL),
    0x130: _op("pmfhl.sh", "rd", "mmi", verification=MANUAL),
    0x031: _op("pmthl.lw", "rs", "mmi", writes_hi_lo=True, verification=MANUAL),
    0x034: _op("psllh", "rd,rt,sa", "mmi", verification=MANUAL),
    0x036: _op("psrlh", "rd,rt,sa", "mmi", verification=MANUAL),
    0x037: _op("psrah", "rd,rt,sa", "mmi", verification=MANUAL),
    0x03C: _op("psllw", "rd,rt,sa", "mmi", verification=MANUAL),
    0x03E: _op("psrlw", "rd,rt,sa", "mmi", verification=MANUAL),
    0x03F: _op("psraw", "rd,rt,sa", "mmi", verification=MANUAL),
}

# Instructions implemented by the oracle and the C++ emitter.  Everything
# else decodes for analysis but must fail explicitly in lowering.
SUPPORTED_MNEMONICS = {
    "nop",
    "sll", "srl", "sra", "sllv", "srlv", "srav",
    "dsll", "dsrl", "dsra", "dsll32", "dsrl32", "dsra32",
    "dsllv", "dsrlv", "dsrav",
    "jr", "jalr", "movz", "movn", "sync",
    "addiu", "daddiu", "addu", "daddu", "subu", "dsubu",
    "and", "or", "xor", "nor",
    "slt", "sltu", "slti", "sltiu",
    "lui", "andi", "ori", "xori",
    "lb", "lbu", "lh", "lhu", "lw", "lwu", "ld", "lq",
    "sb", "sh", "sw", "sd", "sq",
    "beq", "bne", "blez", "bgtz", "bltz", "bgez", "bltzal", "bgezal",
    "j", "jal",
    "cache", "pref",
    # HI/LO operations (32-bit operands, 64-bit HI/LO; HI1/LO1 for the *1 forms).
    "mult", "multu", "div", "divu", "mfhi", "mflo", "mthi", "mtlo",
    "madd", "maddu", "mult1", "multu1", "div1", "divu1",
    "mfhi1", "mflo1", "mthi1", "mtlo1", "madd1", "maddu1",
    # Signed-overflow/trap forms lower to an explicit checked trap halt.
    "add", "dadd", "sub", "dsub",
    # MMI lane operations with simple, independently testable semantics.
    "paddw", "psubw", "pcgtw", "pmaxw", "paddh", "psubh", "pcgth", "pmaxh",
    "paddb", "psubb", "pcgtb",
    "paddsw", "psubsw", "paddsh", "psubsh", "paddsb", "psubsb",
    "padduw", "psubuw", "padduh", "psubuh", "paddub", "psubub",
    "pceqw", "pceqh", "pceqb", "pminw", "pminh",
    "pabsw", "pabsh", "pand", "por", "pxor", "pnor",
    "pextlw", "pextlh", "pextlb", "pextuw", "pextuh", "pextub",
    "psllh", "psrlh", "psrah", "psllw", "psrlw", "psraw",
}

CONTROL_MNEMONICS = {
    "beq", "bne", "blez", "bgtz", "bltz", "bgez", "bltzal", "bgezal",
    "beql", "bnel", "blezl", "bgtzl", "bltzl", "bgezl", "bltzall", "bgezall",
    "j", "jal", "jr", "jalr", "eret",
}
BRANCH_MNEMONICS = {
    "beq", "bne", "blez", "bgtz", "bltz", "bgez", "bltzal", "bgezal",
    "beql", "bnel", "blezl", "bgtzl", "bltzl", "bgezl", "bltzall", "bgezall",
}
JUMP_MNEMONICS = {"j", "jal"}
INDIRECT_MNEMONICS = {"jr", "jalr"}
HALT_MNEMONICS = {"syscall", "break", "eret"}
DELAY_SLOT_MNEMONICS = CONTROL_MNEMONICS - {"eret"}


def sign_extend(value: int, bits: int) -> int:
    value &= (1 << bits) - 1
    sign = 1 << (bits - 1)
    return (value ^ sign) - sign


def _target_for_branch(pc: int, simm: int) -> int:
    return (pc + 4 + (simm << 2)) & MASK32


def _target_for_jump(pc: int, word: int) -> int:
    return ((pc + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)


@dataclass(frozen=True)
class Instruction:
    pc: int
    word: int
    mnemonic: str
    cls: str
    fmt: str = ""
    rs: int | None = None
    rt: int | None = None
    rd: int | None = None
    shamt: int | None = None
    imm: int | None = None
    simm: int | None = None
    target: int | None = None
    delay_slot: bool = False
    writes_hi_lo: bool = False
    supported: bool = False
    valid: bool = True
    verification: str = UNSUPPORTED
    note: str = ""

    @property
    def is_control(self) -> bool:
        return self.mnemonic in CONTROL_MNEMONICS

    @property
    def is_branch(self) -> bool:
        return self.mnemonic in BRANCH_MNEMONICS

    @property
    def is_jump(self) -> bool:
        return self.mnemonic in JUMP_MNEMONICS

    @property
    def is_indirect(self) -> bool:
        return self.mnemonic in INDIRECT_MNEMONICS

    @property
    def is_halt(self) -> bool:
        return self.mnemonic in HALT_MNEMONICS or self.mnemonic.startswith("unknown")

    def text(self) -> str:
        def reg(index: int | None) -> str:
            names = [
                "zero", "at", "v0", "v1", "a0", "a1", "a2", "a3",
                "t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7",
                "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7",
                "t8", "t9", "k0", "k1", "gp", "sp", "fp", "ra",
            ]
            return names[index] if index is not None and 0 <= index < 32 else f"r{index}"

        if self.mnemonic == "nop":
            return "nop"
        if self.mnemonic in {"syscall", "break"}:
            code = (self.word >> 6) & 0xFFFFF
            return self.mnemonic + (f" 0x{code:05X}" if code else "")
        if self.mnemonic == "sync":
            return "sync"
        op = self.mnemonic
        fmt = self.fmt
        if fmt == "target":
            return f"{op} 0x{(self.target or 0):08X}"
        if fmt == "rs":
            return f"{op} ${reg(self.rs)}"
        if fmt == "rd":
            return f"{op} ${reg(self.rd)}"
        if fmt == "rd,rs":
            return f"{op} ${reg(self.rd)}, ${reg(self.rs)}"
        if fmt == "rd,rs,rt":
            return f"{op} ${reg(self.rd)}, ${reg(self.rs)}, ${reg(self.rt)}"
        if fmt == "rd,rt":
            return f"{op} ${reg(self.rd)}, ${reg(self.rt)}"
        if fmt == "rd,rt,rs":
            return f"{op} ${reg(self.rd)}, ${reg(self.rt)}, ${reg(self.rs)}"
        if fmt == "rd,rt,sa":
            return f"{op} ${reg(self.rd)}, ${reg(self.rt)}, {self.shamt}"
        if fmt == "rs,rt":
            return f"{op} ${reg(self.rs)}, ${reg(self.rt)}"
        if fmt == "rs,rt,offset":
            return f"{op} ${reg(self.rs)}, ${reg(self.rt)}, 0x{(self.target or 0):08X}"
        if fmt == "rs,offset":
            return f"{op} ${reg(self.rs)}, 0x{(self.target or 0):08X}"
        if fmt == "rt,rs,imm":
            return f"{op} ${reg(self.rt)}, ${reg(self.rs)}, {self.simm}"
        if fmt == "rs,imm":
            return f"{op} ${reg(self.rs)}, {self.simm}"
        if fmt == "rt,imm":
            return f"{op} ${reg(self.rt)}, 0x{(self.imm or 0):04X}"
        if fmt == "rt,offset(base)":
            return f"{op} ${reg(self.rt)}, {self.simm}(${reg(self.rs)})"
        if fmt == "op,offset(base)":
            return f"{op} 0x{(self.imm or 0):02X}, {self.simm}(${reg(self.rs)})"
        if fmt == "code":
            return op
        return op


def _unknown(pc: int, word: int, note: str = "") -> Instruction:
    op = (word >> 26) & 0x3F
    return Instruction(
        pc=pc,
        word=word,
        mnemonic=f"unknown_0x{word:08X}",
        cls="unknown",
        supported=False,
        valid=False,
        verification=UNSUPPORTED,
        note=note or f"Unsupported primary opcode 0x{op:02X}.",
    )


def _make(pc: int, word: int, spec: OpSpec, *, rs: int | None = None,
          rt: int | None = None, rd: int | None = None, shamt: int | None = None,
          imm: int | None = None, simm: int | None = None,
          target: int | None = None, valid: bool = True,
          note_override: str | None = None) -> Instruction:
    supported = spec.supported and spec.mnemonic in SUPPORTED_MNEMONICS and valid
    return Instruction(
        pc=pc,
        word=word,
        mnemonic=spec.mnemonic,
        cls=spec.cls,
        fmt=spec.fmt,
        rs=rs,
        rt=rt,
        rd=rd,
        shamt=shamt,
        imm=imm,
        simm=simm,
        target=target,
        delay_slot=spec.delay_slot,
        writes_hi_lo=spec.writes_hi_lo,
        supported=supported,
        valid=valid,
        verification=spec.verification,
        note=note_override if note_override is not None else spec.note,
    )


def decode_instruction(word: int, pc: int = 0, *, strict: bool = False) -> Instruction:
    """Decode one 32-bit little-endian R5900 instruction word.

    ``strict`` raises on unrecognised encodings; the default returns an
    ``unknown`` instruction so static analysis can report and continue.
    """
    word &= MASK32
    op = (word >> 26) & 0x3F
    rs = (word >> 21) & 0x1F
    rt = (word >> 16) & 0x1F
    rd = (word >> 11) & 0x1F
    shamt = (word >> 6) & 0x1F
    funct = word & 0x3F
    imm = word & 0xFFFF
    simm = sign_extend(imm, 16)

    if word == 0:
        return Instruction(pc=pc, word=0, mnemonic="nop", cls="special",
                           supported=True, verification=GENERIC,
                           note="SLL $zero, $zero, 0")

    if op == 0x00:
        spec = SPECIAL.get(funct)
        if spec is None:
            if strict:
                raise ValueError(f"Unsupported SPECIAL funct 0x{funct:02X} at 0x{pc:08X}")
            return _unknown(pc, word, f"Unsupported SPECIAL funct 0x{funct:02X}.")
        valid = True
        note = spec.note
        if spec.mnemonic == "jr":
            valid = rt == 0 and rd == 0 and shamt == 0
        elif spec.mnemonic == "jalr":
            valid = rt == 0 and shamt == 0
        elif spec.mnemonic in {"mfhi", "mflo", "mfsa"}:
            valid = rs == 0 and rt == 0 and shamt == 0
        elif spec.mnemonic in {"mthi", "mtlo", "mtsa"}:
            valid = rt == 0 and rd == 0 and shamt == 0
        elif funct in {0x00, 0x02, 0x03, 0x38, 0x3A, 0x3B, 0x3C, 0x3E, 0x3F}:
            valid = rs == 0
        if not valid:
            note = (note + " ").strip() + " Reserved encoding fields are non-zero."
        return _make(pc, word, spec, rs=rs, rt=rt, rd=rd, shamt=shamt,
                     imm=imm, simm=simm, valid=valid, note_override=note)

    if op == 0x01:
        spec = REGIMM.get(rt)
        if spec is None:
            if strict:
                raise ValueError(f"Unsupported REGIMM rt 0x{rt:02X} at 0x{pc:08X}")
            return _unknown(pc, word, f"Unsupported REGIMM rt 0x{rt:02X}.")
        return _make(pc, word, spec, rs=rs, rt=rt,
                     imm=imm, simm=simm,
                     target=_target_for_branch(pc, simm))

    if op == 0x1C:
        funct11 = word & 0x7FF
        group = MMI_SUBTABLE_SELECT.get(funct11 & 0x3F)
        if group is None:
            spec = MMI_STANDALONE.get(funct11)
            if spec is None:
                # Standalone shift ops carry their sa field in bits 10:6.  The
                # same fallback must not guess a PMFHL variant, whose high bits
                # are a selector: only 0..4 are defined encodings.
                fallback = MMI_STANDALONE.get(funct11 & 0x3F)
                if fallback is not None and not fallback.mnemonic.startswith("pmfhl"):
                    spec = fallback
            if spec is None:
                if strict:
                    raise ValueError(f"Unsupported MMI function 0x{funct11:03X} at 0x{pc:08X}")
                return _unknown(pc, word, f"Unsupported MMI function 0x{funct11:03X}.")
            if spec.fmt == "rd,rt,sa":
                return _make(pc, word, spec, rd=rd, rt=rt, shamt=shamt)
            valid = (funct11 >> 6) == 0 or spec.mnemonic.startswith("pmfhl")
            note = spec.note
            if not valid:
                note = (note + " Reserved MMI selector bits are non-zero.").strip()
            return _make(pc, word, spec, rs=rs, rt=rt, rd=rd, valid=valid,
                         note_override=note)
        subfunct = (funct11 >> 6) & 0x1F
        spec = MMI_GROUPS[group].get(subfunct)
        if spec is None:
            if strict:
                raise ValueError(
                    f"Unsupported MMI{group} sub-opcode 0x{subfunct:02X} at 0x{pc:08X}")
            return _unknown(pc, word, f"Unsupported MMI{group} sub-opcode 0x{subfunct:02X}.")
        return _make(pc, word, spec, rs=rs, rt=rt, rd=rd)

    if op in PRIMARY:
        spec = PRIMARY[op]
        if spec.mnemonic in {"j", "jal"}:
            return _make(pc, word, spec, target=_target_for_jump(pc, word), imm=imm)
        if spec.cls == "branch":
            return _make(pc, word, spec, rs=rs, rt=rt,
                         target=_target_for_branch(pc, simm), simm=simm, imm=imm)
        if spec.cls in {"load", "store", "cache"}:
            return _make(pc, word, spec, rs=rs, rt=rt, simm=simm, imm=imm)
        if spec.cls == "immediate":
            return _make(pc, word, spec, rs=rs, rt=rt, imm=imm, simm=simm)
        return _make(pc, word, spec, rs=rs, rt=rt, rd=rd, shamt=shamt, imm=imm, simm=simm)

    if strict:
        raise ValueError(f"Unsupported opcode 0x{op:02X} at 0x{pc:08X}")
    return _unknown(pc, word)


def catalog_rows() -> list[dict[str, Any]]:
    """Flatten the catalog into deterministic rows for reports and docs."""
    rows: list[dict[str, Any]] = []

    def add(spec: OpSpec, table: str, encoding: str, ordinal: int | None = None) -> None:
        rows.append({
            "mnemonic": spec.mnemonic,
            "table": table,
            "encoding": encoding,
            "ordinal": ordinal,
            "format": spec.fmt,
            "supported": spec.mnemonic in SUPPORTED_MNEMONICS and spec.supported,
            "delay_slot": spec.delay_slot,
            "writes_hi_lo": spec.writes_hi_lo,
            "verification": spec.verification,
            "note": spec.note,
        })

    add(_op("nop", "", "special", verification=GENERIC), "special", "0x00000000", 0)
    for funct, spec in sorted(SPECIAL.items()):
        add(spec, "special", f"0x00/0x{funct:02X}", funct)
    for rt, spec in sorted(REGIMM.items()):
        add(spec, "regimm", f"0x01/rt=0x{rt:02X}", rt)
    for op, spec in sorted(PRIMARY.items()):
        if spec.mnemonic == "mmi":
            continue
        add(spec, "primary", f"0x{op:02X}", op)
    for funct, spec in sorted(MMI_STANDALONE.items()):
        add(spec, "mmi-standalone", f"0x1C/0x{funct:03X}", funct)
    for group, table in sorted(MMI_GROUPS.items()):
        primary_funct = {0: 0x08, 1: 0x28, 2: 0x09, 3: 0x29}[group]
        for subfunct, spec in sorted(table.items()):
            add(spec, f"mmi{group}", f"0x1C/0x{primary_funct:02X}/sub=0x{subfunct:02X}", subfunct)
    return rows
