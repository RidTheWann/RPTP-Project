# SPDX-License-Identifier: GPL-3.0-or-later
"""Original synthetic ELF/assembly fixtures for differential testing.

Fixtures are assembled in memory and written to temporary directories by the
tests.  No retail game code or proprietary data is involved; the encodings are
derived from the permitted public references listed in docs/REFERENCES.md.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field

CODE_BASE = 0x00100000
DATA_BASE = 0x00200000

ZERO, AT, V0, V1, A0, A1, A2, A3 = 0, 1, 2, 3, 4, 5, 6, 7
T0, T1, T2, T3, T4, T5, T6, T7 = 8, 9, 10, 11, 12, 13, 14, 15
S0, S1, S2, S3, S4, S5, S6, S7 = 16, 17, 18, 19, 20, 21, 22, 23
T8, T9, K0, K1, GP, SP, FP, RA = 24, 25, 26, 27, 28, 29, 30, 31


def encode_i(op: int, rt: int, rs: int, imm: int) -> int:
    return ((op & 0x3F) << 26) | ((rs & 0x1F) << 21) | ((rt & 0x1F) << 16) | (imm & 0xFFFF)


def encode_r(funct: int, rd: int, rs: int, rt: int, sa: int = 0) -> int:
    return ((rs & 0x1F) << 21) | ((rt & 0x1F) << 16) | ((rd & 0x1F) << 11) | ((sa & 0x1F) << 6) | (funct & 0x3F)


def encode_j(op: int, target: int) -> int:
    return ((op & 0x3F) << 26) | ((target >> 2) & 0x03FFFFFF)


def encode_mmi(funct11: int, rd: int, rs: int, rt: int) -> int:
    return (0x1C << 26) | ((rs & 0x1F) << 21) | ((rt & 0x1F) << 16) | ((rd & 0x1F) << 11) | (funct11 & 0x7FF)


@dataclass
class _Fixup:
    index: int
    kind: str
    target: str
    pc: int


@dataclass
class Assembler:
    base: int = CODE_BASE
    words: list[int] = field(default_factory=list)
    labels: dict[str, int] = field(default_factory=dict)
    fixups: list[_Fixup] = field(default_factory=list)

    @property
    def pc(self) -> int:
        return self.base + 4 * len(self.words)

    def label(self, name: str) -> None:
        if name in self.labels:
            raise ValueError(f"Duplicate label {name}")
        self.labels[name] = self.pc

    def emit(self, word: int) -> None:
        self.words.append(word & 0xFFFFFFFF)

    def nop(self) -> None:
        self.emit(0)

    def addiu(self, rt: int, rs: int, imm: int) -> None:
        self.emit(encode_i(0x09, rt, rs, imm))

    def lui(self, rt: int, imm: int) -> None:
        self.emit(encode_i(0x0F, rt, ZERO, imm))

    def ori(self, rt: int, rs: int, imm: int) -> None:
        self.emit(encode_i(0x0D, rt, rs, imm))

    def andi(self, rt: int, rs: int, imm: int) -> None:
        self.emit(encode_i(0x0C, rt, rs, imm))

    def dsll(self, rd: int, rt: int, sa: int) -> None:
        self.emit(encode_r(0x38, rd, ZERO, rt, sa))

    def dsll32(self, rd: int, rt: int, sa: int) -> None:
        self.emit(encode_r(0x3C, rd, ZERO, rt, sa))

    def daddu(self, rd: int, rs: int, rt: int) -> None:
        self.emit(encode_r(0x2D, rd, rs, rt))

    def dsubu(self, rd: int, rs: int, rt: int) -> None:
        self.emit(encode_r(0x2F, rd, rs, rt))

    def addu(self, rd: int, rs: int, rt: int) -> None:
        self.emit(encode_r(0x21, rd, rs, rt))

    def add(self, rd: int, rs: int, rt: int) -> None:
        self.emit(encode_r(0x20, rd, rs, rt))

    def dadd(self, rd: int, rs: int, rt: int) -> None:
        self.emit(encode_r(0x2C, rd, rs, rt))

    def sub(self, rd: int, rs: int, rt: int) -> None:
        self.emit(encode_r(0x22, rd, rs, rt))

    def dsub(self, rd: int, rs: int, rt: int) -> None:
        self.emit(encode_r(0x2E, rd, rs, rt))

    def or_(self, rd: int, rs: int, rt: int) -> None:
        self.emit(encode_r(0x25, rd, rs, rt))

    def and_(self, rd: int, rs: int, rt: int) -> None:
        self.emit(encode_r(0x24, rd, rs, rt))

    def xor(self, rd: int, rs: int, rt: int) -> None:
        self.emit(encode_r(0x26, rd, rs, rt))

    def nor(self, rd: int, rs: int, rt: int) -> None:
        self.emit(encode_r(0x27, rd, rs, rt))

    def xori(self, rt: int, rs: int, imm: int) -> None:
        self.emit(encode_i(0x0E, rt, rs, imm))

    def slt(self, rd: int, rs: int, rt: int) -> None:
        self.emit(encode_r(0x2A, rd, rs, rt))

    def sltu(self, rd: int, rs: int, rt: int) -> None:
        self.emit(encode_r(0x2B, rd, rs, rt))

    def slti(self, rt: int, rs: int, imm: int) -> None:
        self.emit(encode_i(0x0A, rt, rs, imm))

    def sltiu(self, rt: int, rs: int, imm: int) -> None:
        self.emit(encode_i(0x0B, rt, rs, imm))

    def sll(self, rd: int, rt: int, sa: int) -> None:
        self.emit(encode_r(0x00, rd, ZERO, rt, sa))

    def srl(self, rd: int, rt: int, sa: int) -> None:
        self.emit(encode_r(0x02, rd, ZERO, rt, sa))

    def sra(self, rd: int, rt: int, sa: int) -> None:
        self.emit(encode_r(0x03, rd, ZERO, rt, sa))

    def dsrl(self, rd: int, rt: int, sa: int) -> None:
        self.emit(encode_r(0x3A, rd, ZERO, rt, sa))

    def dsra(self, rd: int, rt: int, sa: int) -> None:
        self.emit(encode_r(0x3B, rd, ZERO, rt, sa))

    def dsrl32(self, rd: int, rt: int, sa: int) -> None:
        self.emit(encode_r(0x3E, rd, ZERO, rt, sa))

    def dsra32(self, rd: int, rt: int, sa: int) -> None:
        self.emit(encode_r(0x3F, rd, ZERO, rt, sa))

    def sllv(self, rd: int, rt: int, rs: int) -> None:
        self.emit(encode_r(0x04, rd, rs, rt))

    def srlv(self, rd: int, rt: int, rs: int) -> None:
        self.emit(encode_r(0x06, rd, rs, rt))

    def srav(self, rd: int, rt: int, rs: int) -> None:
        self.emit(encode_r(0x07, rd, rs, rt))

    def dsllv(self, rd: int, rt: int, rs: int) -> None:
        self.emit(encode_r(0x14, rd, rs, rt))

    def dsrlv(self, rd: int, rt: int, rs: int) -> None:
        self.emit(encode_r(0x16, rd, rs, rt))

    def dsrav(self, rd: int, rt: int, rs: int) -> None:
        self.emit(encode_r(0x17, rd, rs, rt))

    def movz(self, rd: int, rs: int, rt: int) -> None:
        self.emit(encode_r(0x0A, rd, rs, rt))

    def movn(self, rd: int, rs: int, rt: int) -> None:
        self.emit(encode_r(0x0B, rd, rs, rt))

    def mult(self, rs: int, rt: int, rd: int = 0) -> None:
        self.emit(encode_r(0x18, rd, rs, rt))

    def multu(self, rs: int, rt: int, rd: int = 0) -> None:
        self.emit(encode_r(0x19, rd, rs, rt))

    def div(self, rs: int, rt: int) -> None:
        self.emit(encode_r(0x1A, 0, rs, rt))

    def divu(self, rs: int, rt: int) -> None:
        self.emit(encode_r(0x1B, 0, rs, rt))

    def mfhi(self, rd: int) -> None:
        self.emit(encode_r(0x10, rd, 0, 0))

    def mflo(self, rd: int) -> None:
        self.emit(encode_r(0x12, rd, 0, 0))

    def mthi(self, rs: int) -> None:
        self.emit(encode_r(0x11, 0, rs, 0))

    def mtlo(self, rs: int) -> None:
        self.emit(encode_r(0x13, 0, rs, 0))

    def madd(self, rs: int, rt: int, rd: int = 0) -> None:
        self.mmi("madd", rd, rs, rt)

    def maddu(self, rs: int, rt: int, rd: int = 0) -> None:
        self.mmi("maddu", rd, rs, rt)

    def mfhi1(self, rd: int) -> None:
        self.mmi("mfhi1", rd)

    def mflo1(self, rd: int) -> None:
        self.mmi("mflo1", rd)

    def mthi1(self, rs: int) -> None:
        self.mmi("mthi1", 0, rs)

    def mtlo1(self, rs: int) -> None:
        self.mmi("mtlo1", 0, rs)

    def lb(self, rt: int, offset: int, base: int) -> None:
        self.emit(encode_i(0x20, rt, base, offset))

    def lbu(self, rt: int, offset: int, base: int) -> None:
        self.emit(encode_i(0x24, rt, base, offset))

    def lh(self, rt: int, offset: int, base: int) -> None:
        self.emit(encode_i(0x21, rt, base, offset))

    def lhu(self, rt: int, offset: int, base: int) -> None:
        self.emit(encode_i(0x25, rt, base, offset))

    def lw(self, rt: int, offset: int, base: int) -> None:
        self.emit(encode_i(0x23, rt, base, offset))

    def lwu(self, rt: int, offset: int, base: int) -> None:
        self.emit(encode_i(0x27, rt, base, offset))

    def ld(self, rt: int, offset: int, base: int) -> None:
        self.emit(encode_i(0x37, rt, base, offset))

    def sb(self, rt: int, offset: int, base: int) -> None:
        self.emit(encode_i(0x28, rt, base, offset))

    def sh(self, rt: int, offset: int, base: int) -> None:
        self.emit(encode_i(0x29, rt, base, offset))

    def sw(self, rt: int, offset: int, base: int) -> None:
        self.emit(encode_i(0x2B, rt, base, offset))

    def sd(self, rt: int, offset: int, base: int) -> None:
        self.emit(encode_i(0x3F, rt, base, offset))

    def lq(self, rt: int, offset: int, base: int) -> None:
        self.emit(encode_i(0x1E, rt, base, offset))

    def sq(self, rt: int, offset: int, base: int) -> None:
        self.emit(encode_i(0x1F, rt, base, offset))

    def lwc1(self, ft: int, offset: int, base: int) -> None:
        self.emit(encode_i(0x31, ft, base, offset))

    def swc1(self, ft: int, offset: int, base: int) -> None:
        self.emit(encode_i(0x39, ft, base, offset))

    def mfc1(self, rt: int, fs: int) -> None:
        self.emit((0x11 << 26) | (rt << 16) | (fs << 11))

    def mtc1(self, rt: int, fs: int) -> None:
        self.emit((0x11 << 26) | (0x04 << 21) | (rt << 16) | (fs << 11))

    def cfc1(self, rt: int, fs: int = 0) -> None:
        self.emit((0x11 << 26) | (0x02 << 21) | (rt << 16) | (fs << 11))

    def ctc1(self, rt: int, fs: int = 0) -> None:
        self.emit((0x11 << 26) | (0x06 << 21) | (rt << 16) | (fs << 11))

    def beq(self, rs: int, rt: int, label: str) -> None:
        self._branch(0x04, rs, rt, label)

    def bne(self, rs: int, rt: int, label: str) -> None:
        self._branch(0x05, rs, rt, label)

    def blez(self, rs: int, label: str) -> None:
        self._branch(0x06, rs, ZERO, label)

    def bgtz(self, rs: int, label: str) -> None:
        self._branch(0x07, rs, ZERO, label)

    def bltz(self, rs: int, label: str) -> None:
        self._regimm_branch(0x00, rs, label)

    def bgez(self, rs: int, label: str) -> None:
        self._regimm_branch(0x01, rs, label)

    def bltzal(self, rs: int, label: str) -> None:
        self._regimm_branch(0x10, rs, label)

    def bgezal(self, rs: int, label: str) -> None:
        self._regimm_branch(0x11, rs, label)

    def beql(self, rs: int, rt: int, label: str) -> None:
        self._branch(0x14, rs, rt, label)

    def bnel(self, rs: int, rt: int, label: str) -> None:
        self._branch(0x15, rs, rt, label)

    def blezl(self, rs: int, label: str) -> None:
        self._branch(0x16, rs, ZERO, label)

    def bgtzl(self, rs: int, label: str) -> None:
        self._branch(0x17, rs, ZERO, label)

    def bltzl(self, rs: int, label: str) -> None:
        self._regimm_branch(0x02, rs, label)

    def bgezl(self, rs: int, label: str) -> None:
        self._regimm_branch(0x03, rs, label)

    def bltzall(self, rs: int, label: str) -> None:
        self._regimm_branch(0x12, rs, label)

    def bgezall(self, rs: int, label: str) -> None:
        self._regimm_branch(0x13, rs, label)

    def _branch(self, op: int, rs: int, rt: int, label: str) -> None:
        self.fixups.append(_Fixup(len(self.words), "branch", label, self.pc))
        self.emit(encode_i(op, rt, rs, 0))

    def _regimm_branch(self, rt: int, rs: int, label: str) -> None:
        self.fixups.append(_Fixup(len(self.words), "branch", label, self.pc))
        self.emit(encode_i(0x01, rt, rs, 0))

    def j(self, label: str) -> None:
        self.fixups.append(_Fixup(len(self.words), "jump", label, self.pc))
        self.emit(0)

    def jal(self, label: str) -> None:
        self.fixups.append(_Fixup(len(self.words), "jump", label, self.pc))
        self.emit(0x03 << 26)

    def jr(self, rs: int) -> None:
        self.emit(encode_r(0x08, 0, rs, 0))

    def jalr(self, rd: int, rs: int) -> None:
        self.emit(encode_r(0x09, rd, rs, 0))

    def mmi(self, mnemonic: str, rd: int = 0, rs: int = 0, rt: int = 0) -> None:
        table = {
            "paddw": 0x008, "psubw": 0x048, "pcgtw": 0x088, "pmaxw": 0x0C8,
            "paddh": 0x108, "psubh": 0x148, "pcgth": 0x188, "pmaxh": 0x1C8,
            "paddb": 0x208, "psubb": 0x248, "pcgtb": 0x288,
            "paddsw": 0x308, "psubsw": 0x348,
            "pextlw": 0x388, "pextuw": 0x3A8,
            "pextlh": 0x488, "pextuh": 0x4A8,
            "pextlb": 0x588, "pextub": 0x5A8,
            "paddsh": 0x408, "psubsh": 0x448,
            "paddsb": 0x508, "psubsb": 0x548,
            "pceqw": 0x0A8, "pminw": 0x0E8, "pceqh": 0x1A8, "pminh": 0x1E8,
            "pceqb": 0x2A8, "padduw": 0x328, "psubuw": 0x368,
            "padduh": 0x428, "psubuh": 0x468, "paddub": 0x528, "psubub": 0x568,
            "pand": 0x489, "pxor": 0x4C9, "por": 0x4A9, "pnor": 0x4E9,
            "pabsw": 0x068, "pabsh": 0x168,
            "madd": 0x000, "maddu": 0x001,
            "mfhi1": 0x010, "mthi1": 0x011, "mflo1": 0x012, "mtlo1": 0x013,
            "mult1": 0x018, "multu1": 0x019, "div1": 0x01A, "divu1": 0x01B,
            "madd1": 0x020, "maddu1": 0x021,
        }
        if mnemonic not in table:
            raise ValueError(f"Unsupported fixture MMI mnemonic {mnemonic}")
        self.emit(encode_mmi(table[mnemonic], rd, rs, rt))

    def mmi_shift(self, mnemonic: str, rd: int, rt: int, sa: int) -> None:
        table = {"psllh": 0x034, "psrlh": 0x036, "psrah": 0x037,
                 "psllw": 0x03C, "psrlw": 0x03E, "psraw": 0x03F}
        if mnemonic not in table:
            raise ValueError(f"Unsupported fixture MMI shift {mnemonic}")
        self.emit(encode_mmi(table[mnemonic] | ((sa & 0x1F) << 6), rd, 0, rt))

    def resolve(self) -> list[int]:
        words = list(self.words)
        for fixup in self.fixups:
            if fixup.target not in self.labels:
                raise ValueError(f"Undefined label {fixup.target}")
            target = self.labels[fixup.target]
            if fixup.kind == "jump":
                words[fixup.index] = encode_j(0x03 if (words[fixup.index] >> 26) == 3 else 0x02, target)
            else:
                offset = (target - (fixup.pc + 4)) >> 2
                if not -32768 <= offset <= 32767:
                    raise ValueError(f"Branch to {fixup.target} is out of range")
                words[fixup.index] = (words[fixup.index] & 0xFFFF0000) | (offset & 0xFFFF)
        return words


def build_elf(words: list[int], data: bytes = b"", *, base: int = CODE_BASE,
              data_base: int = DATA_BASE, entry: int | None = None) -> bytes:
    code = b"".join(struct.pack("<I", word & 0xFFFFFFFF) for word in words)
    ident = b"\x7fELF" + bytes([1, 1, 1, 0, 0]) + bytes(7)
    e_entry = base if entry is None else entry
    phnum = 2 if data else 1
    ehdr = struct.pack(
        "<16sHHIIIIIHHHHHH", ident, 2, 8, 1, e_entry, 52, 0, 0, 52, 32, phnum, 40, 0, 0)
    code_offset = 0x1000
    data_offset = 0x2000
    phdrs = [struct.pack("<IIIIIIII", 1, code_offset, base, base, len(code), len(code), 5, 0x1000)]
    if data:
        phdrs.append(struct.pack("<IIIIIIII", 1, data_offset, data_base, data_base,
                                 len(data), len(data), 6, 0x1000))
    header = ehdr + b"".join(phdrs)
    image = bytearray(header)
    image.extend(b"\0" * (code_offset - len(image)))
    image.extend(code)
    if data:
        image.extend(b"\0" * (data_offset - len(image)))
        image.extend(data)
    return bytes(image)


def differential_fixture() -> bytes:
    """A mixed program exercising branches, delay slots, calls, memory and MMI."""
    asm = Assembler()
    asm.addiu(T0, ZERO, 1)
    asm.addiu(T1, ZERO, 1)
    asm.beq(T0, T1, "taken")
    asm.addiu(T0, ZERO, 99)       # delay slot overwrites the compared register
    asm.addiu(S0, ZERO, 7)        # skipped when the branch is taken
    asm.label("taken")
    asm.addiu(S1, T0, 0)          # observes the delay-slot value
    asm.addu(AT, ZERO, RA)        # save the link register like a real prologue
    asm.addiu(A0, ZERO, 9)
    asm.jal("sum")
    asm.addiu(A1, ZERO, 33)       # call delay slot
    asm.addiu(V1, ZERO, 42)
    asm.beq(V0, V1, "call_ok")
    asm.addiu(S2, ZERO, 5)        # delay slot always executes
    asm.addiu(S3, ZERO, 77)
    asm.label("call_ok")
    asm.lui(T2, DATA_BASE >> 16)
    asm.addiu(T3, ZERO, 12)
    asm.sw(T3, 0, T2)
    asm.lw(T4, 0, T2)
    asm.lq(T5, 0, T2)
    asm.sq(T5, 16, T2)
    asm.addiu(T6, ZERO, -1)
    asm.dsll32(T7, T6, 0)
    asm.daddu(S4, T7, T6)
    asm.dsubu(S5, ZERO, T7)
    asm.addiu(A2, ZERO, 7)
    asm.addiu(A3, ZERO, -3)
    asm.mult(A2, A3)
    asm.mflo(K0)
    asm.mfhi(K1)
    asm.div(A2, A3)
    asm.mflo(GP)
    asm.mfhi(SP)
    asm.divu(A2, ZERO)
    asm.mflo(T8)
    asm.mfhi(T9)
    asm.addiu(T0, ZERO, 1)
    asm.dsll32(T0, T0, 0)
    asm.ori(T0, T0, 2)
    asm.addiu(T1, ZERO, 3)
    asm.dsll32(T1, T1, 0)
    asm.ori(T1, T1, 4)
    asm.mmi("paddw", S6, T0, T1)
    asm.mmi("psubw", S7, T0, T1)
    asm.mmi("pand", K0, T0, T1)
    asm.mmi("pcgtw", K1, T1, T0)
    asm.mmi("pceqw", GP, T0, T0)
    asm.mmi("paddsw", SP, T0, T0)
    asm.mmi_shift("psllh", FP, T0, 1)
    asm.mmi_shift("psrah", V1, T0, 1)
    asm.mmi("pabsw", S0, 0, T1)
    asm.addu(RA, ZERO, AT)        # restore the caller link register
    asm.jr(RA)
    asm.nop()
    asm.label("sum")
    asm.addu(V0, A0, A1)
    asm.jr(RA)
    asm.addiu(S3, ZERO, 55)
    data = bytes(range(0x10, 0x30))
    return build_elf(asm.resolve(), data)


def broad_fixture() -> bytes:
    """Scalar, memory, branch and HI/LO coverage beyond the mixed smoke fixture."""
    asm = Assembler()

    asm.lui(T0, 0x1234)
    asm.ori(T0, T0, 0x5678)
    asm.lui(T1, 0x00FF)
    asm.ori(T1, T1, 0xF0F0)
    asm.and_(S0, T0, T1)
    asm.or_(S1, T0, T1)
    asm.xor(S2, T0, T1)
    asm.nor(S3, T0, T1)
    asm.xori(S4, T0, 0x00FF)
    asm.andi(S5, T0, 0xFF00)

    asm.addiu(T2, ZERO, -1)
    asm.slt(S6, T2, ZERO)
    asm.sltu(K0, T2, ZERO)
    asm.slti(K1, T2, 1)
    asm.sltiu(GP, ZERO, -1)

    asm.addiu(T0, ZERO, 0x00F0)
    asm.sll(V0, T0, 4)
    asm.srl(V1, T0, 2)
    asm.addiu(T1, ZERO, -16)
    asm.sra(A0, T1, 2)
    asm.addiu(T2, ZERO, 3)
    asm.sllv(A1, T0, T2)
    asm.srlv(A2, T0, T2)
    asm.srav(A3, T1, T2)
    asm.addiu(T3, ZERO, 1)
    asm.dsll32(T4, T3, 1)
    asm.dsrl32(T5, T4, 1)
    asm.dsra32(T6, T4, 1)
    asm.addiu(T7, ZERO, -1)
    asm.dsll32(T8, T7, 0)
    asm.dsra(T9, T8, 4)
    asm.dsrl(K0, T8, 4)
    asm.addiu(T5, ZERO, 5)
    asm.dsllv(K1, T3, T5)
    asm.dsrlv(GP, T8, T5)
    asm.dsrav(S6, T7, T5)

    asm.addiu(T0, ZERO, 11)
    asm.addiu(T1, ZERO, 22)
    asm.addiu(T2, ZERO, 0)
    asm.movz(T0, T1, T2)
    asm.addiu(T3, ZERO, 1)
    asm.movn(T0, T3, T3)
    asm.addiu(T4, ZERO, 33)
    asm.movz(T4, T1, T3)
    asm.addiu(T5, ZERO, 44)
    asm.movn(T5, T1, T2)

    asm.addiu(A0, ZERO, 7)
    asm.addiu(A1, ZERO, -3)
    asm.mult(A0, A1, V0)
    asm.multu(A0, A1, V1)
    asm.mfhi(T0)
    asm.mflo(T1)
    asm.addiu(T2, ZERO, 5)
    asm.mtlo(T2)
    asm.mthi(ZERO)
    asm.madd(A0, A1, S0)
    asm.mfhi(T3)
    asm.mflo(T4)
    asm.mtlo(T2)
    asm.mthi(ZERO)
    asm.maddu(A0, A1, S1)
    asm.mfhi(T5)
    asm.mflo(T6)
    asm.addiu(T7, ZERO, 9)
    asm.mtlo1(T7)
    asm.mthi1(ZERO)
    asm.mmi("mult1", 0, A0, A1)
    asm.mfhi1(T8)
    asm.mflo1(T9)
    asm.mmi("madd1", S2, A0, A1)
    asm.mfhi1(K0)
    asm.mflo1(K1)

    asm.div(A0, A1)
    asm.mflo(T0)
    asm.mfhi(T1)
    asm.divu(A0, A1)
    asm.mflo(T2)
    asm.mfhi(T3)
    asm.div(A0, ZERO)
    asm.mflo(T4)
    asm.mfhi(T5)
    asm.lui(T6, 0x8000)
    asm.addiu(T7, ZERO, -1)
    asm.div(T6, T7)
    asm.mflo(T8)
    asm.mfhi(T9)

    asm.lui(T2, DATA_BASE >> 16)
    asm.lb(T3, 0, T2)
    asm.lbu(T4, 0, T2)
    asm.lh(T5, 2, T2)
    asm.lhu(T6, 2, T2)
    asm.lw(T7, 4, T2)
    asm.lwu(T8, 4, T2)
    asm.ld(T9, 8, T2)
    asm.addiu(K0, ZERO, -1)
    asm.sb(K0, 0x20, T2)
    asm.lb(K1, 0x20, T2)
    asm.lbu(GP, 0x20, T2)
    asm.lui(T3, 0x1234)
    asm.ori(T3, T3, 0x5678)
    asm.sh(T3, 0x22, T2)
    asm.lh(T4, 0x22, T2)
    asm.lhu(T5, 0x22, T2)
    asm.lui(T6, 0xFEDC)
    asm.ori(T6, T6, 0xBA98)
    asm.dsll32(T6, T6, 0)
    asm.lui(T7, 0x7654)
    asm.ori(T7, T7, 0x3210)
    asm.or_(T8, T6, T7)
    asm.sd(T8, 0x28, T2)
    asm.ld(T9, 0x28, T2)
    asm.lq(T3, 5, T2)
    asm.sq(T3, 0x33, T2)
    asm.lq(T4, 0x30, T2)
    asm.lui(T5, 0x8020)
    asm.lw(T6, 4, T5)
    asm.sb(K0, 0x21, T5)

    asm.addiu(T0, ZERO, 5)
    asm.addiu(T1, ZERO, 6)
    asm.beq(T0, T1, "wrong_beq")
    asm.addiu(S0, ZERO, 111)
    asm.addiu(S1, ZERO, 222)
    asm.j("beq_done")
    asm.nop()
    asm.label("wrong_beq")
    asm.addiu(S2, ZERO, 999)
    asm.label("beq_done")

    asm.addiu(T2, ZERO, -5)
    asm.bltz(T2, "bltz_ok")
    asm.addiu(S2, ZERO, 123)
    asm.addiu(S3, ZERO, 999)
    asm.label("bltz_ok")
    asm.addiu(S3, ZERO, 456)

    asm.addiu(T3, ZERO, 7)
    asm.blez(T2, "blez_ok")
    asm.addiu(S4, ZERO, 10)
    asm.addiu(S5, ZERO, 999)
    asm.label("blez_ok")
    asm.addiu(S5, ZERO, 20)

    asm.bgtz(T3, "bgtz_ok")
    asm.addiu(S0, ZERO, 30)
    asm.addiu(S1, ZERO, 999)
    asm.label("bgtz_ok")
    asm.addiu(S1, ZERO, 40)

    asm.bgez(T3, "bgez_ok")
    asm.addiu(V0, ZERO, 50)
    asm.addiu(V1, ZERO, 999)
    asm.label("bgez_ok")
    asm.addiu(V1, ZERO, 60)

    asm.addu(S7, RA, ZERO)
    asm.bltzal(T2, "bltzal_ok")
    asm.nop()
    asm.addiu(S6, ZERO, 999)
    asm.label("bltzal_ok")
    asm.addu(S6, RA, ZERO)
    asm.addu(RA, S7, ZERO)
    asm.bgezal(T3, "bgezal_ok")
    asm.nop()
    asm.addiu(K0, ZERO, 999)
    asm.label("bgezal_ok")
    asm.addu(K0, RA, ZERO)
    asm.addu(RA, S7, ZERO)

    asm.addiu(A0, ZERO, 10)
    asm.addiu(A1, ZERO, 5)
    asm.jal("jalr_func")
    asm.addiu(A2, ZERO, 1)
    asm.addiu(A2, ZERO, 2)
    asm.lui(T0, DATA_BASE >> 16)
    asm.lw(T1, 0x10, T0)
    asm.addu(AT, S7, ZERO)        # S7 still holds the caller sentinel
    asm.jalr(RA, T1)
    asm.addiu(A0, ZERO, 21)
    asm.addu(RA, AT, ZERO)
    asm.jr(RA)
    asm.nop()

    asm.label("jalr_func")
    asm.addu(V0, A0, A1)
    asm.jr(RA)
    asm.nop()

    data = bytearray(range(0x40, 0x60))
    struct.pack_into("<I", data, 0x10, asm.labels["jalr_func"])
    return build_elf(asm.resolve(), bytes(data))


def overflow_fixture(mnemonic: str = "add") -> bytes:
    """A program that traps on signed overflow of the requested operation."""
    asm = Assembler()
    if mnemonic == "add":
        asm.lui(T0, 0x7FFF)
        asm.ori(T0, T0, 0xFFFF)
        asm.addiu(T1, ZERO, 1)
        asm.add(T2, T0, T1)
    elif mnemonic == "sub":
        asm.lui(T0, 0x8000)
        asm.addiu(T1, ZERO, 1)
        asm.sub(T2, T0, T1)
    elif mnemonic == "dadd":
        asm.addiu(T0, ZERO, -1)
        asm.dsrl(T0, T0, 1)
        asm.addiu(T1, ZERO, 1)
        asm.dadd(T2, T0, T1)
    elif mnemonic == "dsub":
        asm.addiu(T0, ZERO, -1)
        asm.dsll32(T0, T0, 31)
        asm.addiu(T1, ZERO, 1)
        asm.dsub(T2, T0, T1)
    else:
        raise ValueError(f"Unsupported overflow fixture {mnemonic}")
    asm.jr(RA)
    asm.nop()
    return build_elf(asm.resolve())
