#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only ISO 9660 inspector for RPTP. No external dependencies."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

BLOCK = 2048
PVD_LBA = 16
MAX_DESCRIPTORS = 256
MAX_SYSTEM_CNF = 1024 * 1024
MAX_DIRECTORY_ENTRIES = 100_000
MAX_BOOT_COMPONENTS = 32
MAX_PROGRAM_HEADERS = 4096
CHUNK_SIZE = 1024 * 1024
MAX_READ_BYTES = 4 * 1024 * 1024
MAX_SURVEY_DEPTH = 64
MAX_SURVEY_DIRECTORIES = 100_000
MAX_SURVEY_RECORDS = 1_000_000
ELF_HEADER_SIZE = 52
ELF_PROGRAM_HEADER_SIZE = 32
PT_LOAD = 1


class InspectError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _u733(data: bytes, off: int, name: str) -> int:
    if off < 0 or off + 8 > len(data):
        raise InspectError("TRUNCATED_FIELD", f"{name} is truncated.")
    le = int.from_bytes(data[off:off + 4], "little")
    be = int.from_bytes(data[off + 4:off + 8], "big")
    if le != be:
        raise InspectError("BOTH_ENDIAN_MISMATCH", f"{name} has conflicting little- and big-endian values.")
    return le


def _u723(data: bytes, off: int, name: str) -> int:
    if off < 0 or off + 4 > len(data):
        raise InspectError("TRUNCATED_FIELD", f"{name} is truncated.")
    le = int.from_bytes(data[off:off + 2], "little")
    be = int.from_bytes(data[off + 2:off + 4], "big")
    if le != be:
        raise InspectError("BOTH_ENDIAN_MISMATCH", f"{name} has conflicting little- and big-endian values.")
    return le


def _name(raw: bytes) -> str:
    if raw == b"\x00":
        return "."
    if raw == b"\x01":
        return ".."
    return raw.decode("ascii", errors="replace").rstrip("\x00")


def _text(raw: bytes) -> str:
    return raw.decode("ascii", errors="replace").replace("\x00", "").strip()


def _key(raw: bytes | str) -> str:
    value = _name(raw) if isinstance(raw, bytes) else raw
    return value.split(";", 1)[0].rstrip(".").casefold()


def _entry_metadata(entry: dict[str, object]) -> dict[str, object]:
    return {
        "extent_lba": entry["lba"],
        "extent_bytes": entry["size"],
        "xa_length": entry["xa_len"],
        "flags": entry["flags"],
        "volume_sequence": entry["volume_sequence"],
    }


class IsoReader:
    def __init__(
        self,
        stream: BinaryIO,
        size: int,
        name: str,
        *,
        max_read_bytes: int = MAX_READ_BYTES,
        chunk_size: int = CHUNK_SIZE,
    ):
        if max_read_bytes <= 0:
            raise ValueError("max_read_bytes must be positive.")
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive.")
        self.stream = stream
        self.size = size
        self.name = name
        self.max_read_bytes = max_read_bytes
        self.chunk_size = chunk_size
        self.volume_blocks = 0
        self.root: dict[str, object] | None = None

    def read_at(self, offset: int, size: int) -> bytes:
        if offset < 0 or size < 0 or offset > self.size or size > self.size - offset:
            raise InspectError(
                "IMAGE_BOUNDS",
                f"Byte range at offset {offset} of {size} bytes is outside the image.",
            )
        self.stream.seek(offset)
        data = self.stream.read(size)
        if len(data) != size:
            raise InspectError("IMAGE_TRUNCATED", f"Could not read {size} bytes at offset {offset}.")
        return data

    def extent(self, entry: dict[str, object]) -> tuple[int, int]:
        first_lba = int(entry["lba"]) + int(entry["xa_len"])
        length = int(entry["size"])
        limit = self.volume_blocks * BLOCK
        if first_lba < 0 or length < 0 or first_lba > self.volume_blocks:
            raise InspectError("EXTENT_OUT_OF_BOUNDS", f"Extent is outside the image or declared volume: {entry['name']}.")
        start = first_lba * BLOCK
        if start > limit or length > limit - start or start > self.size or length > self.size - start:
            raise InspectError("EXTENT_OUT_OF_BOUNDS", f"Extent is outside the image or declared volume: {entry['name']}.")
        return start, length

    def parse_record(self, rec: bytes, *, allow_unsupported: bool = False) -> dict[str, object]:
        if len(rec) < 34 or rec[0] < 34 or rec[0] > len(rec):
            raise InspectError("DIRECTORY_RECORD_LENGTH_INVALID", "Invalid or truncated ISO 9660 directory record.")
        rec = rec[:rec[0]]
        name_len = rec[32]
        if name_len == 0:
            raise InspectError("DIRECTORY_IDENTIFIER_EMPTY", "Directory record has an empty identifier.")
        name_end = 33 + name_len
        pad = 1 if name_len % 2 == 0 else 0
        if name_end + pad > len(rec):
            raise InspectError("DIRECTORY_IDENTIFIER_TRUNCATED", "Directory identifier extends beyond its record.")
        volume_sequence = _u723(rec, 28, "volume sequence number")
        if volume_sequence != 1:
            raise InspectError(
                "UNSUPPORTED_VOLUME_SEQUENCE",
                f"Directory record volume sequence {volume_sequence} is not supported; only single-volume sets are accepted.",
            )
        file_unit_size = rec[26]
        interleave_gap = rec[27]
        if not allow_unsupported and (file_unit_size != 0 or interleave_gap != 0):
            raise InspectError(
                "INTERLEAVED_UNSUPPORTED",
                f"Interleaved directory record is unsupported: {_name(rec[33:name_end])}.",
            )
        entry = {
            "name": _name(rec[33:name_end]),
            "id": rec[33:name_end],
            "xa_len": rec[1],
            "lba": _u733(rec, 2, "extent location"),
            "size": _u733(rec, 10, "data length"),
            "flags": rec[25],
            "directory": bool(rec[25] & 0x02),
            "multi_extent": bool(rec[25] & 0x80),
            "record_length": rec[0],
            "volume_sequence": volume_sequence,
        }
        self.extent(entry)
        return entry

    def scan_pvd(self) -> bytes:
        pvd = None
        terminated = False
        end = min(self.size // BLOCK, PVD_LBA + MAX_DESCRIPTORS)
        for lba in range(PVD_LBA, end):
            desc = self.read_at(lba * BLOCK, BLOCK)
            if desc[1:6] != b"CD001":
                raise InspectError("VOLUME_DESCRIPTOR_SIGNATURE", f"Descriptor at block {lba} has no CD001 signature.")
            if desc[6] != 1:
                raise InspectError("VOLUME_DESCRIPTOR_VERSION", f"Descriptor at block {lba} has unsupported version {desc[6]}.")
            if desc[0] == 1 and pvd is None:
                pvd = desc
            if desc[0] == 255:
                terminated = True
                break
        if not terminated:
            raise InspectError("VOLUME_DESCRIPTOR_TERMINATOR_MISSING", "No volume descriptor terminator was found within the scan limit.")
        if pvd is None:
            raise InspectError("PRIMARY_VOLUME_DESCRIPTOR_MISSING", "No primary volume descriptor was found.")
        return pvd

    def parse_pvd(self, pvd: bytes) -> dict[str, object]:
        self.volume_blocks = _u733(pvd, 80, "volume space size")
        block_size = _u723(pvd, 128, "logical block size")
        volume_set_size = _u723(pvd, 120, "volume set size")
        volume_sequence = _u723(pvd, 124, "volume sequence number")
        if block_size != BLOCK:
            raise InspectError("UNSUPPORTED_LOGICAL_BLOCK_SIZE", f"Only {BLOCK}-byte logical blocks are supported; found {block_size}.")
        if volume_set_size != 1 or volume_sequence != 1:
            raise InspectError(
                "UNSUPPORTED_VOLUME_SET",
                f"Only single-volume ISO sets are supported; found size {volume_set_size}, sequence {volume_sequence}.",
            )
        if self.volume_blocks <= PVD_LBA:
            raise InspectError("INVALID_VOLUME_SIZE", "Declared volume is too small.")
        if self.volume_blocks * BLOCK > self.size:
            raise InspectError("IMAGE_TRUNCATED", "Image is smaller than the volume space size in the PVD.")
        root_len = pvd[156]
        if root_len < 34 or 156 + root_len > BLOCK:
            raise InspectError("ROOT_RECORD_INVALID", "Root directory record is invalid.")
        root = self.parse_record(pvd[156:156 + root_len])
        if not root["directory"] or root["id"] != b"\x00" or root["size"] == 0:
            raise InspectError("ROOT_RECORD_INVALID", "PVD root record is not a valid non-empty root directory.")
        if root["multi_extent"]:
            raise InspectError("MULTI_EXTENT_UNSUPPORTED", "Multi-extent root directory is unsupported.")
        self.root = root
        return {
            "volume_id": _text(pvd[40:72]),
            "volume_set_size": volume_set_size,
            "volume_sequence_number": volume_sequence,
            "system_identifier": _text(pvd[8:40]),
            "volume_set_identifier": _text(pvd[190:318]),
            "publisher_identifier": _text(pvd[318:446]),
            "data_preparer_identifier": _text(pvd[446:574]),
            "application_identifier": _text(pvd[574:702]),
            "copyright_file_identifier": _text(pvd[702:739]),
            "abstract_file_identifier": _text(pvd[739:776]),
            "bibliographic_file_identifier": _text(pvd[776:813]),
            "volume_space_blocks": self.volume_blocks,
            "logical_block_size": block_size,
            "primary_volume_descriptor_lba": PVD_LBA,
            "root_directory": {
                "extent_lba": root["lba"],
                "size_bytes": root["size"],
                "xa_length": root["xa_len"],
            },
        }

    def list_dir(self, entry: dict[str, object]) -> list[dict[str, object]]:
        if not entry["directory"]:
            raise InspectError("NOT_A_DIRECTORY", f"{entry['name']} is not a directory.")
        if entry["multi_extent"]:
            raise InspectError("MULTI_EXTENT_UNSUPPORTED", f"Multi-extent directory is unsupported: {entry['name']}.")
        start, size = self.extent(entry)
        position = 0
        items: list[dict[str, object]] = []
        while position < size:
            block_left = BLOCK - (position % BLOCK)
            segment = min(block_left, size - position)
            rec_len = self.read_at(start + position, 1)[0]
            if rec_len == 0:
                position += segment
                continue
            if rec_len < 34:
                raise InspectError("DIRECTORY_RECORD_LENGTH_INVALID", f"Invalid record length {rec_len} at directory offset {position}.")
            if rec_len > segment:
                raise InspectError("DIRECTORY_RECORD_CROSSES_BLOCK", f"Directory record crosses a logical block at offset {position}.")
            rec = self.read_at(start + position, rec_len)
            child = self.parse_record(rec)
            if child["multi_extent"] and child["directory"]:
                raise InspectError("MULTI_EXTENT_UNSUPPORTED", f"Multi-extent directory is unsupported: {child['name']}.")
            if child["id"] not in (b"\x00", b"\x01"):
                items.append(child)
                if len(items) > MAX_DIRECTORY_ENTRIES:
                    raise InspectError("DIRECTORY_ENTRY_LIMIT", "Directory entry limit exceeded.")
            position += rec_len
        return items

    def survey(self) -> dict[str, object]:
        if self.size < (PVD_LBA + 1) * BLOCK:
            raise InspectError("IMAGE_TOO_SMALL", "Image is too small to contain an ISO 9660 volume descriptor.")
        if self.size % BLOCK:
            raise InspectError("IMAGE_ALIGNMENT_INVALID", f"Image size is not a multiple of {BLOCK} bytes.")
        self.parse_pvd(self.scan_pvd())
        assert self.root is not None
        directory_count = 0
        directory_record_count = 0
        file_count = 0
        record_count = 0
        max_depth = 0
        multi_extent_records = 0
        interleaved_records = 0
        skipped_unsupported_directories = 0
        highest_file_extent_end = 0
        largest_file_size = 0
        seen: set[tuple[int, int]] = set()
        stack: list[tuple[dict[str, object], int]] = [(self.root, 0)]
        while stack:
            directory, depth = stack.pop()
            start, size = self.extent(directory)
            key = (start, size)
            if key in seen:
                continue
            seen.add(key)
            if depth > MAX_SURVEY_DEPTH:
                raise InspectError("SURVEY_DEPTH_LIMIT", f"Directory depth exceeds {MAX_SURVEY_DEPTH}.")
            if len(seen) > MAX_SURVEY_DIRECTORIES:
                raise InspectError("SURVEY_DIRECTORY_LIMIT", f"Directory count exceeds {MAX_SURVEY_DIRECTORIES}.")
            directory_count += 1
            max_depth = max(max_depth, depth)
            position = 0
            while position < size:
                block_left = BLOCK - (position % BLOCK)
                segment = min(block_left, size - position)
                rec_len = self.read_at(start + position, 1)[0]
                if rec_len == 0:
                    position += segment
                    continue
                if rec_len < 34:
                    raise InspectError("DIRECTORY_RECORD_LENGTH_INVALID", f"Invalid record length {rec_len} at directory offset {position}.")
                if rec_len > segment:
                    raise InspectError("DIRECTORY_RECORD_CROSSES_BLOCK", f"Directory record crosses a logical block at offset {position}.")
                rec = self.read_at(start + position, rec_len)
                child = self.parse_record(rec, allow_unsupported=True)
                position += rec_len
                if child["id"] in (b"\x00", b"\x01"):
                    continue
                record_count += 1
                if record_count > MAX_SURVEY_RECORDS:
                    raise InspectError("SURVEY_RECORD_LIMIT", f"Record count exceeds {MAX_SURVEY_RECORDS}.")
                if rec[26] != 0 or rec[27] != 0:
                    interleaved_records += 1
                if child["multi_extent"]:
                    multi_extent_records += 1
                if child["directory"]:
                    directory_record_count += 1
                    if child["multi_extent"] or rec[26] != 0 or rec[27] != 0:
                        skipped_unsupported_directories += 1
                        continue
                    stack.append((child, depth + 1))
                else:
                    file_count += 1
                    file_start, file_size = self.extent(child)
                    highest_file_extent_end = max(highest_file_extent_end, file_start + file_size)
                    largest_file_size = max(largest_file_size, file_size)
        sector_count = self.size // BLOCK
        volume_bytes = self.volume_blocks * BLOCK
        if self.volume_blocks == sector_count:
            volume_relation = "equal"
        elif self.volume_blocks < sector_count:
            volume_relation = "smaller"
        else:
            volume_relation = "larger"
        return {
            "status": "SURVEYED",
            "image_size_bytes": self.size,
            "sector_count": sector_count,
            "logical_block_size": BLOCK,
            "volume_space_blocks": self.volume_blocks,
            "volume_space_bytes": volume_bytes,
            "volume_space_relation": volume_relation,
            "volume_space_delta_bytes": volume_bytes - self.size,
            "directory_count": directory_count,
            "directory_record_count": directory_record_count,
            "file_count": file_count,
            "record_count": record_count,
            "max_depth": max_depth,
            "multi_extent_records": multi_extent_records,
            "interleaved_records": interleaved_records,
            "skipped_unsupported_directories": skipped_unsupported_directories,
            "highest_file_extent_end_bytes": highest_file_extent_end,
            "largest_file_size_bytes": largest_file_size,
        }

    def find_child(self, parent: dict[str, object], component: str) -> dict[str, object]:
        wanted = _key(component)
        matches = [entry for entry in self.list_dir(parent) if _key(entry["id"]) == wanted]
        if not matches:
            raise InspectError("BOOT_EXECUTABLE_NOT_FOUND", f"BOOT path component was not found: {component}.")
        if len(matches) > 1:
            raise InspectError("AMBIGUOUS_PATH", f"Multiple entries match BOOT path component: {component}.")
        return matches[0]

    def resolve_boot(self, value: str) -> tuple[dict[str, object], str | None, list[str]]:
        value = value.strip().strip('"').strip("'")
        device = None
        if ":" in value:
            device, value = value.split(":", 1)
            device = device.strip().casefold() or None
        components = [part for part in re.split(r"[\\/]+", value) if part]
        if not components:
            raise InspectError("BOOT_PATH_EMPTY", "BOOT path is empty.")
        if len(components) > MAX_BOOT_COMPONENTS:
            raise InspectError("BOOT_PATH_DEPTH_LIMIT", f"BOOT path exceeds {MAX_BOOT_COMPONENTS} components.")
        if any(part in (".", "..") for part in components):
            raise InspectError("UNSAFE_BOOT_PATH", "BOOT path contains a dot or parent-directory component.")
        assert self.root is not None
        entry = self.root
        resolved_path: list[str] = []
        for index, component in enumerate(components):
            entry = self.find_child(entry, component)
            resolved_path.append(str(entry["name"]))
            if index < len(components) - 1 and not entry["directory"]:
                raise InspectError("BOOT_PATH_NOT_DIRECTORY", f"Intermediate BOOT path component is not a directory: {component}.")
        if entry["directory"]:
            raise InspectError("BOOT_TARGET_IS_DIRECTORY", "BOOT path identifies a directory.")
        if entry["multi_extent"]:
            raise InspectError("MULTI_EXTENT_UNSUPPORTED", "Multi-extent BOOT executable is not supported.")
        return entry, device, resolved_path

    def read_range(self, start: int, size: int) -> bytes:
        if size > self.max_read_bytes:
            raise InspectError("FILE_SIZE_LIMIT", f"Read size {size} exceeds the {self.max_read_bytes}-byte safety limit.")
        chunks: list[bytes] = []
        offset = 0
        while offset < size:
            count = min(self.chunk_size, size - offset)
            chunks.append(self.read_at(start + offset, count))
            offset += count
        return b"".join(chunks)

    def read_entry(self, entry: dict[str, object], max_size: int) -> bytes:
        start, size = self.extent(entry)
        limit = min(max_size, self.max_read_bytes)
        if size > limit:
            raise InspectError("FILE_SIZE_LIMIT", f"{entry['name']} exceeds the {limit}-byte safety limit.")
        return self.read_range(start, size)

    def hash_entry(self, entry: dict[str, object]) -> str:
        start, size = self.extent(entry)
        digest = hashlib.sha256()
        offset = 0
        while offset < size:
            count = min(self.chunk_size, size - offset)
            digest.update(self.read_at(start + offset, count))
            offset += count
        return digest.hexdigest()

    def parse_elf(self, entry: dict[str, object]) -> dict[str, object]:
        start, size = self.extent(entry)
        if size < ELF_HEADER_SIZE:
            raise InspectError("BOOT_ELF_HEADER_TRUNCATED", "BOOT executable is smaller than an ELF32 header.")
        h = self.read_at(start, min(size, 64))
        if h[:4] != b"\x7fELF":
            raise InspectError("BOOT_EXECUTABLE_NOT_ELF", "BOOT executable does not start with ELF magic.")
        if h[4] != 1:
            raise InspectError("UNSUPPORTED_ELF_CLASS", f"Expected ELF32, got class {h[4]}.")
        if h[5] != 1:
            raise InspectError("UNSUPPORTED_ELF_ENDIANNESS", f"Expected little-endian ELF, got data encoding {h[5]}.")
        if h[6] != 1 or int.from_bytes(h[20:24], "little") != 1:
            raise InspectError("ELF_VERSION_INVALID", "Unsupported ELF version.")
        elf_type = int.from_bytes(h[16:18], "little")
        machine = int.from_bytes(h[18:20], "little")
        entry_point = int.from_bytes(h[24:28], "little")
        phoff = int.from_bytes(h[28:32], "little")
        ehsize = int.from_bytes(h[40:42], "little")
        phentsize = int.from_bytes(h[42:44], "little")
        phnum = int.from_bytes(h[44:46], "little")
        if ehsize < ELF_HEADER_SIZE or ehsize > size:
            raise InspectError("ELF_HEADER_SIZE_INVALID", "ELF32 header size is invalid.")
        if phnum > MAX_PROGRAM_HEADERS:
            raise InspectError("ELF_PROGRAM_HEADER_LIMIT", f"Program header count exceeds {MAX_PROGRAM_HEADERS}.")
        if phnum:
            if phentsize < ELF_PROGRAM_HEADER_SIZE or phoff < ehsize or phoff + phentsize * phnum > size:
                raise InspectError("ELF_PROGRAM_HEADERS_OUT_OF_BOUNDS", "ELF program header table is invalid or out of bounds.")
        load_segments: list[dict[str, object]] = []
        for index in range(phnum):
            ph = self.read_at(start + phoff + index * phentsize, ELF_PROGRAM_HEADER_SIZE)
            segment_type = int.from_bytes(ph[0:4], "little")
            file_offset = int.from_bytes(ph[4:8], "little")
            virtual_address = int.from_bytes(ph[8:12], "little")
            physical_address = int.from_bytes(ph[12:16], "little")
            file_size = int.from_bytes(ph[16:20], "little")
            memory_size = int.from_bytes(ph[20:24], "little")
            flags = int.from_bytes(ph[24:28], "little")
            alignment = int.from_bytes(ph[28:32], "little")
            if segment_type != PT_LOAD:
                continue
            if file_offset + file_size > size:
                raise InspectError(
                    "ELF_LOAD_SEGMENT_OUT_OF_BOUNDS",
                    f"ELF PT_LOAD segment {index} extends beyond the executable.",
                )
            if file_size > memory_size:
                raise InspectError(
                    "ELF_LOAD_SEGMENT_SIZE_INVALID",
                    f"ELF PT_LOAD segment {index} has file size {file_size} greater than memory size {memory_size}.",
                )
            if alignment not in (0, 1) and alignment & (alignment - 1):
                raise InspectError(
                    "ELF_LOAD_SEGMENT_ALIGNMENT_INVALID",
                    f"ELF PT_LOAD segment {index} has non-power-of-two alignment {alignment}.",
                )
            load_segments.append({
                "type": segment_type,
                "file_offset": file_offset,
                "virtual_address": virtual_address,
                "physical_address": physical_address,
                "file_size": file_size,
                "memory_size": memory_size,
                "flags": flags,
                "alignment": alignment,
            })
        return {
            "class": "ELF32",
            "endianness": "little",
            "type": elf_type,
            "machine_id": machine,
            "machine": "MIPS" if machine == 8 else "other",
            "entry_point": entry_point,
            "program_header_offset": phoff,
            "program_header_entry_size": phentsize,
            "program_header_count": phnum,
            "load_segment_count": len(load_segments),
            "load_segments": load_segments,
        }

    def inspect(self) -> dict[str, object]:
        if self.size < (PVD_LBA + 1) * BLOCK:
            raise InspectError("IMAGE_TOO_SMALL", "Image is too small to contain an ISO 9660 volume descriptor.")
        if self.size % BLOCK:
            raise InspectError("IMAGE_ALIGNMENT_INVALID", f"Image size is not a multiple of {BLOCK} bytes.")
        iso = self.parse_pvd(self.scan_pvd())
        assert self.root is not None
        system_matches = [e for e in self.list_dir(self.root) if _key(e["id"]) == "system.cnf"]
        if not system_matches:
            raise InspectError("SYSTEM_CNF_NOT_FOUND", "SYSTEM.CNF was not found in the ISO root directory.")
        if len(system_matches) != 1:
            raise InspectError("SYSTEM_CNF_AMBIGUOUS", "Multiple root entries match SYSTEM.CNF.")
        system = system_matches[0]
        if system["directory"]:
            raise InspectError("SYSTEM_CNF_IS_DIRECTORY", "SYSTEM.CNF is a directory, not a regular file.")
        if system["multi_extent"]:
            raise InspectError("MULTI_EXTENT_UNSUPPORTED", "Multi-extent SYSTEM.CNF is not supported.")
        raw_config = self.read_entry(system, MAX_SYSTEM_CNF).decode("ascii", errors="replace").replace("\x00", "")
        config: dict[str, str] = {}
        for line in raw_config.splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                if key.strip():
                    config[key.strip().upper()] = value.strip()
        boot_key = "BOOT2" if config.get("BOOT2") else ("BOOT" if config.get("BOOT") else None)
        if boot_key is None:
            raise InspectError("BOOT_CONFIG_MISSING", "SYSTEM.CNF has no non-empty BOOT2 or BOOT entry.")
        executable, device, resolved_path = self.resolve_boot(config[boot_key])
        elf = self.parse_elf(executable)
        warnings: list[str] = []
        if device is None:
            warnings.append("BOOT path has no device prefix; cdrom0 is expected for a typical PS2 disc.")
        elif device != "cdrom0":
            warnings.append(f"BOOT device is {device!r}; cdrom0 is expected for a typical PS2 disc.")
        if elf["machine_id"] != 8:
            warnings.append(f"BOOT ELF machine id is {elf['machine_id']}; EM_MIPS (8) is expected for PS2.")
        if elf["type"] != 2:
            warnings.append(f"BOOT ELF type is {elf['type']}; ET_EXEC (2) is expected for a PS2 executable.")
        if elf["load_segment_count"] == 0:
            warnings.append("BOOT ELF has no PT_LOAD segment.")
        else:
            entry_point = int(elf["entry_point"])
            entry_in_segment = any(
                int(segment["virtual_address"]) <= entry_point < int(segment["virtual_address"]) + int(segment["memory_size"])
                for segment in elf["load_segments"]
            )
            if not entry_in_segment:
                warnings.append("BOOT ELF entry point is outside all PT_LOAD segments.")
        return {
            "status": "INSPECTED_WITH_WARNINGS" if warnings else "INSPECTED",
            "input_name": self.name,
            "image_size_bytes": self.size,
            "iso9660": iso,
            "system_cnf": {
                "path": system["name"],
                "size_bytes": system["size"],
                "sha256": self.hash_entry(system),
                "boot_key": boot_key,
                "boot_value": config[boot_key],
                "device": device,
                "fields": config,
                "extent": _entry_metadata(system),
            },
            "boot_executable": {
                "path": executable["name"],
                "resolved_path": resolved_path,
                "device": device,
                "size_bytes": executable["size"],
                "sha256": self.hash_entry(executable),
                "extent": _entry_metadata(executable),
                "elf": elf,
            },
            "warnings": warnings,
            "limitations": [
                "Read-only ISO 9660 primary-volume-descriptor inspector; files are not extracted or modified.",
                "Supports single-volume ISO 9660 images with 2048-byte logical blocks; multi-extent entries are rejected.",
                "ELF inspection validates the header, program-header table and PT_LOAD file bounds; it does not recompile or launch the game.",
                "No retail/commercial ISO is included in tests; broader PS2 disc compatibility is unverified.",
            ],
        }


def inspect_stream(
    stream: BinaryIO,
    size: int,
    name: str = "<stream>",
    *,
    max_read_bytes: int = MAX_READ_BYTES,
    chunk_size: int = CHUNK_SIZE,
) -> dict[str, object]:
    return IsoReader(
        stream,
        size,
        name,
        max_read_bytes=max_read_bytes,
        chunk_size=chunk_size,
    ).inspect()


def inspect_bytes(
    data: bytes,
    name: str = "<memory>",
    *,
    max_read_bytes: int = MAX_READ_BYTES,
    chunk_size: int = CHUNK_SIZE,
) -> dict[str, object]:
    return inspect_stream(
        BytesIO(data),
        len(data),
        name,
        max_read_bytes=max_read_bytes,
        chunk_size=chunk_size,
    )


def inspect_path(
    path: Path,
    *,
    max_read_bytes: int = MAX_READ_BYTES,
    chunk_size: int = CHUNK_SIZE,
) -> dict[str, object]:
    try:
        if not path.exists():
            raise InspectError("INPUT_NOT_FOUND", f"Input file does not exist: {path}")
        if not path.is_file():
            raise InspectError("INPUT_NOT_FILE", f"Input path is not a regular file: {path}")
        with path.open("rb") as stream:
            return inspect_stream(
                stream,
                path.stat().st_size,
                str(path),
                max_read_bytes=max_read_bytes,
                chunk_size=chunk_size,
            )
    except InspectError:
        raise
    except OSError as exc:
        raise InspectError("INPUT_UNREADABLE", f"Cannot read {path}: {exc}") from exc


def survey_path(
    path: Path,
    *,
    max_read_bytes: int = MAX_READ_BYTES,
    chunk_size: int = CHUNK_SIZE,
) -> dict[str, object]:
    try:
        if not path.exists():
            raise InspectError("INPUT_NOT_FOUND", f"Input file does not exist: {path}")
        if not path.is_file():
            raise InspectError("INPUT_NOT_FILE", f"Input path is not a regular file: {path}")
        with path.open("rb") as stream:
            return IsoReader(
                stream,
                path.stat().st_size,
                str(path),
                max_read_bytes=max_read_bytes,
                chunk_size=chunk_size,
            ).survey()
    except InspectError:
        raise
    except OSError as exc:
        raise InspectError("INPUT_UNREADABLE", f"Cannot read {path}: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, help="User-owned 2048-byte-sector ISO image, opened read-only")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    parser.add_argument("--survey", action="store_true", help="Emit a read-only directory survey instead of boot inspection")
    args = parser.parse_args()
    try:
        if args.survey:
            report = survey_path(args.image)
        else:
            report = inspect_path(args.image)
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        elif args.survey:
            print(f"RPTP ISO directory survey: {report['status']}")
            print(f"Image size: {report['image_size_bytes']} bytes; sectors: {report['sector_count']}")
            if report["volume_space_relation"] == "equal":
                print(f"Volume space: {report['volume_space_blocks']} blocks; equal to the file size")
            else:
                print(
                    f"Volume space: {report['volume_space_blocks']} blocks; "
                    f"{report['volume_space_relation']} than the file by "
                    f"{abs(report['volume_space_delta_bytes'])} bytes"
                )
            print(
                f"Directories: {report['directory_count']}; files: {report['file_count']}; "
                f"max depth: {report['max_depth']}"
            )
            print(
                f"Multi-extent records: {report['multi_extent_records']}; "
                f"interleaved records: {report['interleaved_records']}"
            )
            print(
                f"Highest file extent end: {report['highest_file_extent_end_bytes']} bytes; "
                f"largest file: {report['largest_file_size_bytes']} bytes"
            )
            print("No file data was extracted or executed.")
        else:
            iso, cfg, boot = report["iso9660"], report["system_cnf"], report["boot_executable"]
            print(f"RPTP ISO inspection: {report['status']}")
            print(f"Input: {report['input_name']}")
            print(f"Volume: {iso['volume_id'] or '(no volume identifier)'}")
            print(f"Block size: {iso['logical_block_size']}; volume blocks: {iso['volume_space_blocks']}")
            print(f"SYSTEM.CNF: {cfg['path']} ({cfg['size_bytes']} bytes)")
            print(f"SYSTEM.CNF SHA-256: {cfg['sha256']}")
            print(f"{cfg['boot_key']}: {cfg['boot_value']}")
            print(f"BOOT executable: {'/'.join(boot['resolved_path'])} ({boot['size_bytes']} bytes)")
            print(f"SHA-256: {boot['sha256']}")
            elf = boot["elf"]
            print(
                f"ELF: {elf['class']} {elf['endianness']}-endian, machine={elf['machine_id']}, "
                f"entry=0x{elf['entry_point']:08X}, load_segments={elf['load_segment_count']}"
            )
            for warning in report["warnings"]:
                print(f"WARNING: {warning}")
            print("No files were extracted or modified.")
        return 0
    except InspectError as exc:
        output = {"status": "ERROR", "error_code": exc.code, "message": exc.message}
        if args.json:
            print(json.dumps(output, indent=2, sort_keys=True))
        else:
            print(f"RPTP inspect failed [{exc.code}]: {exc.message}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
