#!/usr/bin/env python3
"""Reject game/proprietary artifacts and unregistered binary fixtures."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

ALWAYS_FORBIDDEN = {".iso", ".ps2", ".bios", ".rom", ".nvm", ".dump", ".vcd", ".exe", ".dll", ".pdb", ".obj", ".o", ".lib", ".a"}
MANIFEST_PATH = Path("tests/fixtures/MANIFEST")
SKIP_DIRS = {".git", "build", "out", "__pycache__", ".pytest_cache"}


def read_manifest(root: Path) -> tuple[dict[str, str], list[str]]:
    path = root / MANIFEST_PATH
    errors: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {}, [f"Cannot read fixture manifest {MANIFEST_PATH.as_posix()}: {exc}"]
    if data.get("schema_version") != 1 or not isinstance(data.get("fixtures"), list):
        return {}, ["Fixture MANIFEST must have schema_version=1 and a fixtures array"]
    allowed: dict[str, str] = {}
    for item in data["fixtures"]:
        path_text = item.get("path")
        sha = item.get("sha256")
        origin = item.get("origin")
        license_status = item.get("license_status")
        if not all(isinstance(v, str) and v.strip() for v in (path_text, sha, origin, license_status)):
            errors.append(f"Manifest entry missing path/hash/origin/license_status: {item!r}")
            continue
        rel = Path(path_text)
        if rel.is_absolute() or ".." in rel.parts:
            errors.append(f"Unsafe fixture path in MANIFEST: {path_text}")
            continue
        if not path_text.replace("\\", "/").startswith("tests/fixtures/"):
            errors.append(f"Fixture allowlist may only cover tests/fixtures/: {path_text}")
            continue
        if path_text in allowed:
            errors.append(f"Duplicate fixture path in MANIFEST: {path_text}")
            continue
        allowed[path_text.replace("\\", "/")] = sha.lower()
    return allowed, errors


def scan_repository(root: Path) -> list[str]:
    root = root.resolve()
    allowed, errors = read_manifest(root)
    seen_allowed: set[str] = set()
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in SKIP_DIRS or part.startswith("cmake-build-") for part in rel.parts):
            continue
        rel_text = rel.as_posix()
        suffix = path.suffix.lower()
        if path.is_symlink() and (suffix in ALWAYS_FORBIDDEN or suffix in {".elf", ".bin"}):
            errors.append(f"Symlink is not permitted for binary/game artifacts: {rel_text}")
            continue
        if suffix in ALWAYS_FORBIDDEN:
            errors.append(f"Forbidden proprietary/game artifact: {rel_text}")
            continue
        if suffix in {".elf", ".bin"}:
            expected = allowed.get(rel_text)
            if rel_text != rel_text.replace("\\", "/"):
                errors.append(f"Non-canonical fixture path: {rel_text}")
            if expected is None:
                errors.append(f"Unregistered binary fixture: {rel_text}")
                continue
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            seen_allowed.add(rel_text)
            if actual != expected:
                errors.append(f"Fixture hash mismatch: {rel_text}; expected {expected}, got {actual}")
    for rel_text in allowed:
        if not (root / rel_text).is_file():
            errors.append(f"Manifest fixture is missing: {rel_text}")
        elif rel_text not in seen_allowed:
            # Non-binary entries in the manifest are not accepted as fixture registrations.
            errors.append(f"Manifest path is not a scanned .elf/.bin fixture: {rel_text}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    errors = scan_repository(args.root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Artifact guard passed: only manifest-registered synthetic binary fixtures are permitted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
