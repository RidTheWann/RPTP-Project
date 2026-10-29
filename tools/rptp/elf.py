# SPDX-License-Identifier: GPL-3.0-or-later
"""Minimal, defensive ELF32/EM_MIPS loader for static analysis.

The loader reads program headers, an optional section table, an optional
symbol table and the file-backed bytes of every PT_LOAD segment.  It never
executes or extracts files and it rejects malformed inputs explicitly.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
import struct

MASK32 = 0xFFFFFFFF

PT_LOAD = 1
PF_X = 1
PF_W = 2
PF_R = 4

SHT_SYMTAB = 2
SHT_STRTAB = 3
STT_FUNC = 2
STT_OBJECT = 1


class ElfError(ValueError):
    """Raised when an input is not a supported, well-formed ELF32 MIPS file."""


@dataclass(frozen=True)
class LoadSegment:
    index: int
    offset: int
    vaddr: int
    filesz: int
    memsz: int
    flags: int
    align: int
    file_data: bytes

    @property
    def executable(self) -> bool:
        return bool(self.flags & PF_X)

    @property
    def writable(self) -> bool:
        return bool(self.flags & PF_W)

    @property
    def end_vaddr(self) -> int:
        return self.vaddr + self.memsz


@dataclass(frozen=True)
class Section:
    index: int
    name: str
    sh_type: int
    flags: int
    addr: int
    offset: int
    size: int
    link: int
    entsize: int


@dataclass(frozen=True)
class Symbol:
    name: str
    value: int
    size: int
    info: int
    shndx: int

    @property
    def binding(self) -> int:
        return (self.info >> 4) & 0xF

    @property
    def stype(self) -> int:
        return self.info & 0xF

    @property
    def is_function(self) -> bool:
        return self.stype == STT_FUNC and self.value != 0

    @property
    def is_object(self) -> bool:
        return self.stype == STT_OBJECT and self.value != 0


@dataclass
class ElfImage:
    path: str
    entry: int
    segments: list[LoadSegment]
    sections: list[Section]
    symbols: list[Symbol]
    sha256: str
    size: int
    flags: int
    file_bytes: bytes = field(repr=False, default=b"")

    @property
    def executable_segments(self) -> list[LoadSegment]:
        return [segment for segment in self.segments if segment.executable]

    @property
    def code_ranges(self) -> list[tuple[int, int]]:
        return sorted((segment.vaddr, segment.end_vaddr) for segment in self.executable_segments)

    @property
    def function_symbols(self) -> list[Symbol]:
        return sorted((symbol for symbol in self.symbols if symbol.is_function),
                      key=lambda symbol: (symbol.value, symbol.name))

    def is_code_address(self, address: int) -> bool:
        return any(start <= address < end for start, end in self.code_ranges)

    def read_byte(self, address: int) -> int:
        for segment in self.segments:
            if segment.vaddr <= address < segment.vaddr + segment.filesz:
                return segment.file_data[address - segment.vaddr]
            if segment.vaddr + segment.filesz <= address < segment.end_vaddr:
                return 0
        raise ElfError(f"Address 0x{address:08X} is not backed by a PT_LOAD segment")

    def read_bytes(self, address: int, length: int) -> bytes:
        if length < 0:
            raise ElfError("Negative read length")
        return bytes(self.read_byte(address + offset) for offset in range(length))

    def contains(self, address: int) -> bool:
        for segment in self.segments:
            if segment.vaddr <= address < segment.end_vaddr:
                return True
        return False

    def segment_for(self, address: int) -> LoadSegment | None:
        for segment in self.segments:
            if segment.vaddr <= address < segment.end_vaddr:
                return segment
        return None

    def initial_memory(self) -> tuple[dict[int, int], list[tuple[int, int]]]:
        """Return non-zero initial bytes and the valid address ranges."""
        data: dict[int, int] = {}
        ranges: list[tuple[int, int]] = []
        for segment in self.segments:
            ranges.append((segment.vaddr, segment.end_vaddr))
            for offset, value in enumerate(segment.file_data):
                if value:
                    data[segment.vaddr + offset] = value
        ranges.sort()
        return data, ranges

    def code_words(self, diagnostics: list[str] | None = None) -> dict[int, int]:
        words: dict[int, int] = {}
        for segment in self.executable_segments:
            if segment.filesz % 4:
                if diagnostics is not None:
                    diagnostics.append(
                        f"Executable segment {segment.index} size 0x{segment.filesz:X} "
                        "is not a multiple of 4; trailing bytes ignored.")
            for offset in range(0, segment.filesz - (segment.filesz % 4), 4):
                address = segment.vaddr + offset
                words[address] = struct.unpack_from("<I", segment.file_data, offset)[0]
        return words


def _cstring(table: bytes, offset: int) -> str:
    if offset < 0 or offset >= len(table):
        return ""
    end = table.find(b"\x00", offset)
    if end < 0:
        end = len(table)
    return table[offset:end].decode("utf-8", "replace")


def parse_elf_bytes(data: bytes, *, path: str = "<memory>") -> ElfImage:
    if len(data) < 52:
        raise ElfError("ELF header is truncated")
    ident = data[:16]
    if ident[:4] != b"\x7fELF":
        raise ElfError("Invalid ELF magic")
    if ident[4] != 1:
        raise ElfError("Only ELF32 is supported")
    if ident[5] != 1:
        raise ElfError("Only little-endian ELF is supported")
    if ident[6] != 1:
        raise ElfError("Unsupported ELF identification version")

    (e_type, e_machine, e_version, e_entry, e_phoff, e_shoff, e_flags,
     e_ehsize, e_phentsize, e_phnum, e_shentsize, e_shnum, e_shstrndx) = struct.unpack_from(
        "<HHIIIIIHHHHHH", data, 16)
    if e_type != 2:
        raise ElfError(f"Expected ET_EXEC (2), got {e_type}")
    if e_machine != 8:
        raise ElfError(f"Expected EM_MIPS (8), got {e_machine}")
    if e_version != 1 or e_ehsize != 52:
        raise ElfError("Unsupported ELF version or header size")
    if e_phnum == 0:
        raise ElfError("ELF has no program headers")
    if e_phentsize != 32:
        raise ElfError(f"Unsupported program-header entry size {e_phentsize}")
    if e_phoff > len(data) or e_phnum > (len(data) - e_phoff) // 32:
        raise ElfError("Program header table extends beyond input")
    if e_entry > MASK32:
        raise ElfError("Entry point exceeds the ELF32 address space")

    segments: list[LoadSegment] = []
    for index in range(e_phnum):
        offset = e_phoff + index * 32
        p_type, p_offset, p_vaddr, _p_paddr, p_filesz, p_memsz, p_flags, p_align = struct.unpack_from(
            "<IIIIIIII", data, offset)
        if p_type != PT_LOAD:
            continue
        if p_filesz > p_memsz:
            raise ElfError(f"Segment {index}: p_filesz exceeds p_memsz")
        if p_vaddr + p_memsz > 0x100000000:
            raise ElfError(f"Segment {index}: virtual address range overflows ELF32")
        if p_offset > len(data) or p_filesz > len(data) - p_offset:
            raise ElfError(f"Segment {index}: file-backed range extends beyond input")
        if p_align not in (0, 1):
            if p_align & (p_align - 1):
                raise ElfError(f"Segment {index}: alignment is not a power of two")
            if (p_offset % p_align) != (p_vaddr % p_align):
                raise ElfError(f"Segment {index}: file and virtual alignment disagree")
        segments.append(LoadSegment(
            index=index,
            offset=p_offset,
            vaddr=p_vaddr,
            filesz=p_filesz,
            memsz=p_memsz,
            flags=p_flags,
            align=p_align,
            file_data=data[p_offset:p_offset + p_filesz],
        ))
    if not segments:
        raise ElfError("ELF has no PT_LOAD segments")
    segments.sort(key=lambda segment: (segment.vaddr, segment.index))
    for previous, current in zip(segments, segments[1:]):
        if current.vaddr < previous.end_vaddr:
            raise ElfError(
                f"PT_LOAD segments overlap: 0x{previous.vaddr:08X}-0x{previous.end_vaddr:08X} "
                f"and 0x{current.vaddr:08X}-0x{current.end_vaddr:08X}")
    if not any(segment.executable and segment.vaddr <= e_entry < segment.end_vaddr for segment in segments):
        raise ElfError("ELF entry point is outside an executable PT_LOAD segment")

    sections: list[Section] = []
    symbols: list[Symbol] = []
    if e_shoff and e_shnum:
        if e_shentsize != 40:
            raise ElfError(f"Unsupported section-header entry size {e_shentsize}")
        if e_shoff > len(data) or e_shnum > (len(data) - e_shoff) // 40:
            raise ElfError("Section header table extends beyond input")
        raw_sections = [struct.unpack_from("<IIIIIIIIII", data, e_shoff + index * 40)
                        for index in range(e_shnum)]
        names: list[str] = []
        if e_shstrndx < len(raw_sections):
            shstr = raw_sections[e_shstrndx]
            shstr_offset, shstr_size = shstr[4], shstr[5]
            if shstr_offset > len(data) or shstr_size > len(data) - shstr_offset:
                raise ElfError("Section-name string table extends beyond input")
            names = [""] * len(raw_sections)
            table = data[shstr_offset:shstr_offset + shstr_size]
            for index, sh in enumerate(raw_sections):
                names[index] = _cstring(table, sh[0])
        for index, (sh_name, sh_type, sh_flags, sh_addr, sh_offset, sh_size,
                    sh_link, _sh_info, _sh_addralign, sh_entsize) in enumerate(raw_sections):
            sections.append(Section(
                index=index,
                name=names[index] if index < len(names) else "",
                sh_type=sh_type,
                flags=sh_flags,
                addr=sh_addr,
                offset=sh_offset,
                size=sh_size,
                link=sh_link,
                entsize=sh_entsize,
            ))
        for section in sections:
            if section.sh_type != SHT_SYMTAB:
                continue
            if section.link >= len(sections):
                raise ElfError("Symbol table has an invalid string-table link")
            strtab = sections[section.link]
            if strtab.sh_type != SHT_STRTAB:
                raise ElfError("Symbol table does not link to a string table")
            if section.offset > len(data) or section.size > len(data) - section.offset:
                raise ElfError("Symbol table extends beyond input")
            if strtab.offset > len(data) or strtab.size > len(data) - strtab.offset:
                raise ElfError("Symbol string table extends beyond input")
            strings = data[strtab.offset:strtab.offset + strtab.size]
            entsize = section.entsize or 16
            if entsize != 16:
                raise ElfError(f"Unsupported ELF32 symbol entry size {entsize}")
            if section.size % entsize:
                raise ElfError("Symbol table size is not a multiple of the entry size")
            for sym_offset in range(0, section.size, entsize):
                st_name, st_value, st_size, st_info, _st_other, st_shndx = struct.unpack_from(
                    "<IIIBBH", data, section.offset + sym_offset)
                symbols.append(Symbol(
                    name=_cstring(strings, st_name),
                    value=st_value,
                    size=st_size,
                    info=st_info,
                    shndx=st_shndx,
                ))
    symbols.sort(key=lambda symbol: (symbol.value, symbol.info, symbol.name))

    return ElfImage(
        path=path,
        entry=e_entry,
        segments=segments,
        sections=sections,
        symbols=symbols,
        sha256=hashlib.sha256(data).hexdigest(),
        size=len(data),
        flags=e_flags,
        file_bytes=data,
    )


def load_elf(path: str | Path) -> ElfImage:
    file_path = Path(path)
    data = file_path.read_bytes()
    return parse_elf_bytes(data, path=str(file_path))
