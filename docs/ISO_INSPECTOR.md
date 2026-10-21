# ISO Inspector prototype

## Purpose

`tools/rptp_inspect.py` is a read-only first step in RPTP's ISO-to-native pipeline. It reports ISO metadata and resolves the boot executable referenced by `SYSTEM.CNF`; it does not extract files, write to the image, emulate code, recompile code, or launch a game.

## Usage

From the repository root:

```powershell
python tools/rptp_inspect.py "D:\Games\your-owned-game.iso"
python tools/rptp_inspect.py "D:\Games\your-owned-game.iso" --json
```

Exit code is `0` for an inspected image and `2` for an expected inspection error. Error output includes a stable machine-readable `error_code` in JSON mode.

## Checks performed

- ISO image size alignment to 2048-byte logical sectors.
- Volume descriptor signature/version and bounded descriptor scan ending at a terminator.
- Primary volume descriptor fields encoded in ISO 9660 dual-endian format.
- Declared volume bounds and root directory record.
- Root `SYSTEM.CNF`, with `BOOT2` preferred and legacy `BOOT` accepted.
- Safe path-component resolution without `.` or `..` traversal.
- Extent and directory-record bounds, with explicit rejection of multi-extent boot files/directories.
- ELF32 little-endian identification, basic header fields and program-header table bounds.
- SHA-256 of the resolved boot file, streamed in bounded chunks.

## Current limitations

- This prototype only supports ISO 9660 primary volume descriptors with 2048-byte sectors.
- Multi-extent files/directories, non-ISO9660 layouts, and some real-world disc variants are not supported.
- ELF validation is intentionally limited; it does not validate every segment or PS2-specific loader convention.
- The inspector does not prove that the executable is a valid PS2 game, does not emulate or recompile it, and does not prove compatibility.
- Tests generate a tiny synthetic ISO entirely in memory. Do not upload commercial ISO images or extracted copyrighted game files to the repository.

## Verification status

The source and unit tests have been added, but this document should be considered pending verification until the repository's Windows/MSVC and Linux/GCC CI jobs complete successfully.
