#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only boot-code word census for RPTP.

The census counts aligned 32-bit words in the file-backed PT_LOAD ranges of a
validated ELF32 little-endian image and reports how many are accepted by the
current synthetic IR decoder. It is static metadata: it does not execute,
extract, rewrite or recompile code, and it does not classify bytes as code or
data. An ISO input is inspected and read in memory only.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import BinaryIO, Callable

MAX_BOOT_BYTES = 16 * 1024 * 1024
MAX_WORDS = 4 * 1024 * 1024
MODEL = "pt_load_word_census_v1"
DECODER_MODULE = "tools/rptp/isa.py"


def _load_module(name: str, filename: str):
    path = Path(__file__).parent / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module {path}")
    module = importlib.util.module_from_spec(spec)
    # Register before execution so dataclasses can resolve postponed annotations.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


inspector = _load_module("rptp_census_inspector", "rptp_inspect.py")
isa = _load_module("rptp_census_isa", "rptp/isa.py")

LIMITATIONS = (
    "Counts every aligned 4-byte word in file-backed PT_LOAD bytes; those bytes may include data, padding or non-code content.",
    "A supported word is accepted by the current R5900 decoder and its supported-mnemonic set only; this does not prove semantics, reachability or runtime safety.",
    "Unsupported labels are raw encoding identifiers (opcode or opcode/funct), not semantic instruction names.",
    "No code was executed, extracted, rewritten or recompiled; no function discovery, CFG or compatibility claim is made.",
    "Census results are static metadata and do not imply that an image can boot or run.",
)


class CensusError(inspector.InspectError):
    """Stable fail-closed census diagnostic."""


class _BlobReader:
    """Minimal inspector reader adapter for an in-memory ELF image."""

    def __init__(self, data: bytes):
        self.data = data
        self.size = len(data)

    def extent(self, entry: dict[str, object]) -> tuple[int, int]:
        return 0, self.size

    def read_at(self, offset: int, size: int) -> bytes:
        if offset < 0 or size < 0 or offset > self.size or size > self.size - offset:
            raise inspector.InspectError("IMAGE_BOUNDS", "ELF byte range is outside the input.")
        return self.data[offset:offset + size]


def _supported_op(word: int) -> str | None:
    instruction = isa.decode_instruction(word, 0)
    return instruction.mnemonic if instruction.supported else None


def _decoder_identity() -> dict[str, object]:
    """Deterministic identity for the decoder set used by this census."""
    mnemonics = sorted(isa.SUPPORTED_MNEMONICS)
    digest = hashlib.sha256("\n".join(mnemonics).encode("ascii")).hexdigest()
    return {
        "module": DECODER_MODULE,
        "supported_mnemonic_count": len(mnemonics),
        "supported_mnemonic_set_sha256": digest,
    }


def _encoding_label(word: int) -> str:
    opcode = (word >> 26) & 0x3F
    if opcode == 0:
        return f"special_0x{word & 0x3F:02x}"
    if opcode == 1:
        return f"regimm_0x{(word >> 16) & 0x1F:02x}"
    return f"opcode_0x{opcode:02x}"


def _elf_warnings(elf: dict[str, object]) -> list[str]:
    warnings: list[str] = []
    if elf["machine_id"] != 8:
        warnings.append(f"ELF machine id is {elf['machine_id']}; EM_MIPS (8) is expected for PS2.")
    if elf["type"] != 2:
        warnings.append(f"ELF type is {elf['type']}; ET_EXEC (2) is expected for a PS2 executable.")
    if elf["load_segments_overlap"]:
        warnings.append("ELF PT_LOAD memory ranges overlap; loading precedence is not evaluated.")
    if elf["load_segment_count"] == 0:
        warnings.append("ELF has no PT_LOAD segment.")
    else:
        mappings = elf["entry_point_mappings"]
        if not mappings:
            warnings.append("ELF entry point is outside all PT_LOAD segments.")
        elif not any(mapping["file_backed"] and mapping["executable"] for mapping in mappings):
            warnings.append("ELF entry point is not in file-backed executable PT_LOAD bytes.")
        if len(mappings) > 1:
            warnings.append("ELF entry point maps to multiple PT_LOAD segments.")
    return warnings


def _census(
    elf: dict[str, object],
    read_segment: Callable[[dict[str, object]], bytes],
    source: dict[str, object],
) -> dict[str, object]:
    counts: dict[str, list[int | bool]] = {}
    segments: list[dict[str, object]] = []
    word_count = 0
    zero_words = 0
    unique_words: set[int] = set()
    trailing_bytes = 0
    supported_words = 0
    for segment in elf["load_segments"]:
        data = read_segment(segment)
        file_size = int(segment["file_size"])
        words = file_size // 4
        trailing = file_size % 4
        segment_zero_words = 0
        segment_supported = 0
        for offset in range(0, words * 4, 4):
            word = int.from_bytes(data[offset:offset + 4], "little")
            unique_words.add(word)
            word_count += 1
            if word == 0:
                zero_words += 1
                segment_zero_words += 1
            label = _supported_op(word)
            if label is None:
                label = _encoding_label(word)
                supported = False
            else:
                supported = True
                supported_words += 1
                segment_supported += 1
            entry = counts.setdefault(label, [0, supported])
            entry[0] = int(entry[0]) + 1
        trailing_bytes += trailing
        segments.append({
            "program_header_index": segment["program_header_index"],
            "file_offset": segment["file_offset"],
            "virtual_address": segment["virtual_address"],
            "file_size": file_size,
            "memory_size": segment["memory_size"],
            "word_count": words,
            "trailing_bytes": trailing,
            "zero_word_count": segment_zero_words,
            "supported_word_count": segment_supported,
        })
    if word_count > MAX_WORDS:
        raise CensusError("CENSUS_WORD_LIMIT", f"Boot image exceeds the {MAX_WORDS}-word census limit.")
    opcodes = [
        {"label": label, "count": int(count), "supported": bool(supported)}
        for label, (count, supported) in counts.items()
    ]
    opcodes.sort(key=lambda item: (-item["count"], item["label"]))
    unsupported = [item for item in opcodes if not item["supported"]]
    warnings = _elf_warnings(elf)
    if trailing_bytes:
        warnings.append(f"{trailing_bytes} trailing byte(s) at the end of PT_LOAD file data were not counted.")
    return {
        "status": "CENSUSED_WITH_WARNINGS" if warnings else "CENSUSED",
        "model": MODEL,
        "decoder": _decoder_identity(),
        "source": source,
        "elf": {
            "entry_point": elf["entry_point"],
            "machine_id": elf["machine_id"],
            "type": elf["type"],
            "load_segment_count": elf["load_segment_count"],
            "load_segments_overlap": elf["load_segments_overlap"],
            "load_segments": elf["load_segments"],
            "entry_point_mappings": elf["entry_point_mappings"],
        },
        "census": {
            "word_count": word_count,
            "zero_word_count": zero_words,
            "nonzero_word_count": word_count - zero_words,
            "unique_word_count": len(unique_words),
            "supported_word_count": supported_words,
            "unsupported_word_count": word_count - supported_words,
            "supported_ratio": round(supported_words / word_count, 6) if word_count else 0.0,
            "trailing_bytes": trailing_bytes,
            "segments": segments,
        },
        "opcodes": opcodes,
        "unsupported_encodings": unsupported,
        "warnings": warnings,
        "limitations": list(LIMITATIONS),
    }


def census_elf_bytes(
    data: bytes,
    *,
    name: str = "<memory>",
    max_boot_bytes: int = MAX_BOOT_BYTES,
) -> dict[str, object]:
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("ELF data must be bytes")
    data = bytes(data)
    if len(data) > max_boot_bytes:
        raise CensusError("CENSUS_SIZE_LIMIT", f"ELF exceeds the {max_boot_bytes}-byte census limit.")
    elf = inspector.IsoReader.parse_elf(_BlobReader(data), {"name": name, "size": len(data)})
    source = {
        "kind": "elf",
        "input_name": name,
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    return _census(elf, lambda segment: data[segment["file_offset"]:segment["file_offset"] + segment["file_size"]], source)


def census_elf_path(path: Path, *, max_boot_bytes: int = MAX_BOOT_BYTES) -> dict[str, object]:
    try:
        if not path.exists():
            raise CensusError("INPUT_NOT_FOUND", f"Input file does not exist: {path}")
        if not path.is_file():
            raise CensusError("INPUT_NOT_FILE", f"Input path is not a regular file: {path}")
        size = path.stat().st_size
        if size > max_boot_bytes:
            raise CensusError("CENSUS_SIZE_LIMIT", f"ELF exceeds the {max_boot_bytes}-byte census limit.")
        data = path.read_bytes()
    except CensusError:
        raise
    except OSError as exc:
        raise CensusError("INPUT_UNREADABLE", f"Cannot read {path}: {exc}") from exc
    return census_elf_bytes(data, name=str(path), max_boot_bytes=max_boot_bytes)


def _census_iso_stream(
    stream: BinaryIO,
    size: int,
    name: str,
    *,
    max_boot_bytes: int,
    chunk_size: int,
) -> dict[str, object]:
    reader = inspector.IsoReader(stream, size, name, max_read_bytes=max_boot_bytes, chunk_size=chunk_size)
    report = reader.inspect()
    boot = report["boot_executable"]
    boot_size = int(boot["size_bytes"])
    if boot_size > max_boot_bytes:
        raise CensusError("CENSUS_SIZE_LIMIT", f"Boot executable exceeds the {max_boot_bytes}-byte census limit.")
    extent = boot["extent"]
    entry = {"name": boot["path"], "lba": extent["extent_lba"], "xa_len": 0, "size": boot_size}
    start, _ = reader.extent(entry)
    source = {
        "kind": "iso",
        "input_name": name,
        "image_size_bytes": size,
        "boot_path": boot["path"],
        "boot_size_bytes": boot_size,
        "boot_sha256": boot["sha256"],
    }
    result = _census(
        boot["elf"],
        lambda segment: reader.read_range(start + int(segment["file_offset"]), int(segment["file_size"])),
        source,
    )
    result["warnings"] = list(report["warnings"]) + [warning for warning in result["warnings"] if warning not in report["warnings"]]
    if result["warnings"]:
        result["status"] = "CENSUSED_WITH_WARNINGS"
    return result


def census_iso_path(
    path: Path,
    *,
    max_boot_bytes: int = MAX_BOOT_BYTES,
    chunk_size: int = inspector.CHUNK_SIZE,
) -> dict[str, object]:
    try:
        if not path.exists():
            raise CensusError("INPUT_NOT_FOUND", f"Input file does not exist: {path}")
        if not path.is_file():
            raise CensusError("INPUT_NOT_FILE", f"Input path is not a regular file: {path}")
        with path.open("rb") as stream:
            return _census_iso_stream(
                stream,
                path.stat().st_size,
                str(path),
                max_boot_bytes=max_boot_bytes,
                chunk_size=chunk_size,
            )
    except CensusError:
        raise
    except OSError as exc:
        raise CensusError("INPUT_UNREADABLE", f"Cannot read {path}: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="User-owned ISO image or ELF file, opened read-only")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--iso", action="store_true", help="Inspect an ISO and census its boot executable in memory")
    mode.add_argument("--elf", action="store_true", help="Census an ELF file directly")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    parser.add_argument("--max-boot-bytes", type=int, default=MAX_BOOT_BYTES, help="Input size safety limit")
    args = parser.parse_args()
    if args.max_boot_bytes <= 0:
        parser.error("--max-boot-bytes must be positive")
    try:
        if args.elf:
            report = census_elf_path(args.input, max_boot_bytes=args.max_boot_bytes)
        else:
            report = census_iso_path(args.input, max_boot_bytes=args.max_boot_bytes)
    except inspector.InspectError as exc:
        output = {"status": "ERROR", "error_code": exc.code, "message": exc.message}
        if args.json:
            print(json.dumps(output, indent=2, sort_keys=True))
        else:
            print(f"RPTP census failed [{exc.code}]: {exc.message}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    census = report["census"]
    decoder = report["decoder"]
    print(f"RPTP boot-code census: {report['status']}")
    print(f"Source: {report['source']['input_name']}")
    print(
        f"Decoder: {decoder['module']}; supported mnemonics: {decoder['supported_mnemonic_count']}; "
        f"set SHA-256: {decoder['supported_mnemonic_set_sha256']}"
    )
    if report["source"]["kind"] == "iso":
        print(f"BOOT executable: {report['source']['boot_path']} ({report['source']['boot_size_bytes']} bytes)")
    print(f"Entry point: 0x{report['elf']['entry_point']:08X}")
    print(
        f"Words: {census['word_count']}; unique: {census['unique_word_count']}; zero: {census['zero_word_count']}; "
        f"supported: {census['supported_word_count']} ({census['supported_ratio']:.2%}); "
        f"unsupported: {census['unsupported_word_count']}"
    )
    print("Top encodings:")
    for item in report["opcodes"][:10]:
        marker = "supported" if item["supported"] else "unsupported"
        print(f"  {item['count']:8d}  {item['label']} ({marker})")
    for warning in report["warnings"]:
        print(f"WARNING: {warning}")
    print("Static word census only; bytes may include data; no execution, extraction or compatibility claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
