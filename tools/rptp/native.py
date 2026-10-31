# SPDX-License-Identifier: GPL-3.0-or-later
"""Build and run RPTP-generated C++20 programs with MSVC.

This module is the native side of the differential harness: it discovers a
usable MSVC toolchain, compiles :class:`tools.rptp.codegen.GeneratedProgram`
sources with warnings-as-errors, and runs the resulting executable with a
strict JSON result check.  It only depends on the Python standard library and
never reaches outside this repository's ``build/`` directory for artifacts.

Compilation failures keep their temporary directory and embed the full
compiler output and that path in :class:`HarnessError`.  Successful builds are
removed by the caller (see :func:`run_differential`) so no stale binaries can
be reused by a later test.
"""
from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Any, Iterator

from . import cfg, codegen, elf, ir

BUILD_ROOT = Path(__file__).resolve().parents[2] / "build"
NATIVE_TEST_ROOT = BUILD_ROOT / "native-tests"

CL_FLAGS = ("/nologo /std:c++20 /EHsc /W4 /WX /permissive- /utf-8 /O2")
COMPILE_TIMEOUT_SECONDS = 180.0
RUN_TIMEOUT_SECONDS = 30.0
EXECUTABLE_NAME = "rptp_native.exe"

EXPECTED_KEYS = frozenset({
    "halted", "pc", "reason", "steps", "registers",
    "hi", "lo", "hi1", "lo1", "fpr", "memory", "trace",
})

# The environment variable used by the generated batch files so that paths
# containing spaces or non-ASCII characters never have to be embedded in a
# batch file body (cmd.exe reads those using the legacy OEM code page).
_VCVARS_ENV = "RPTP_HARNESS_VCVARS"

_COUNTER = 0
_CACHED_TOOLCHAIN: MsvcToolchain | None = None


class HarnessError(RuntimeError):
    """Raised when the native toolchain, build or run cannot complete."""


@dataclass(frozen=True)
class MsvcToolchain:
    """A discovered ``cl.exe`` plus the ``vcvars64.bat`` that configures it."""

    cl: Path
    vcvars: Path
    version: str = ""

    @property
    def description(self) -> str:
        label = f"MSVC {self.version}" if self.version else "MSVC"
        return f"{label} ({self.cl})"


def _version_key(version: str) -> tuple[int, ...]:
    numbers: list[int] = []
    for chunk in version.replace("_", ".").replace("-", ".").split("."):
        if chunk.isdigit():
            numbers.append(int(chunk))
    return tuple(numbers)


def _msvc_version_of(cl: Path) -> str:
    # .../VC/Tools/MSVC/<version>/bin/Hostx64/x64/cl.exe
    for parent in cl.parents:
        if parent.parent.name == "MSVC" and parent.name:
            return parent.name
    return ""


def _vcvars_for_cl(cl: Path) -> Path | None:
    for parent in cl.parents:
        for relative in ("Auxiliary/Build/vcvars64.bat", "VC/Auxiliary/Build/vcvars64.bat"):
            candidate = parent / relative
            if candidate.is_file():
                return candidate.resolve()
    return None


def _toolchain_from_install(install: Path) -> MsvcToolchain | None:
    install = Path(install)
    vcvars = install / "VC/Auxiliary/Build/vcvars64.bat"
    if not vcvars.is_file():
        return None
    candidates = list((install / "VC/Tools/MSVC").glob("*/bin/Hostx64/x64/cl.exe"))
    if not candidates:
        return None
    cl = max(candidates, key=lambda path: _version_key(path.parents[3].name)).resolve()
    return MsvcToolchain(cl=cl, vcvars=vcvars.resolve(), version=_msvc_version_of(cl))


def _vswhere_installations() -> list[Path]:
    program_files = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
    vswhere = program_files / "Microsoft Visual Studio/Installer/vswhere.exe"
    if not vswhere.is_file():
        located = shutil.which("vswhere")
        if located is None:
            return []
        vswhere = Path(located)
    command = [
        str(vswhere), "-latest", "-products", "*",
        "-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
        "-property", "installationPath",
    ]
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, errors="replace", timeout=60.0,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if completed.returncode != 0:
        return []
    return [Path(line.strip()) for line in completed.stdout.splitlines() if line.strip()]


def _search_installations() -> list[Path]:
    roots: list[Path] = []
    vs_install = os.environ.get("VSINSTALLDIR")
    if vs_install:
        roots.append(Path(vs_install))
    vc_install = os.environ.get("VCINSTALLDIR")
    if vc_install:
        vc_path = Path(vc_install)
        # VCINSTALLDIR is the ...\VC directory; the VC Tools live next to it.
        roots.append(vc_path.parent if vc_path.name.lower() == "vc" else vc_path)
    for variable in ("ProgramFiles(x86)", "ProgramFiles", "ProgramW6432"):
        base = os.environ.get(variable)
        if not base:
            continue
        for pattern in ("Microsoft Visual Studio/*/*", "Microsoft Visual Studio/*"):
            roots.extend(sorted(Path(base).glob(pattern)))
    installations = _vswhere_installations() + roots
    unique: list[Path] = []
    seen: set[str] = set()
    for installation in installations:
        key = str(installation).lower()
        if key not in seen:
            seen.add(key)
            unique.append(installation)
    return unique


def _first_toolchain() -> MsvcToolchain | None:
    for installation in _search_installations():
        toolchain = _toolchain_from_install(installation)
        if toolchain is not None:
            return toolchain
    return None


def _toolchain_from_cl(candidate: str) -> MsvcToolchain | None:
    cl_path: Path | None = None
    raw = Path(candidate)
    if raw.is_dir():
        if (raw / "cl.exe").is_file():
            cl_path = raw / "cl.exe"
        else:
            matches = sorted(
                raw.glob("VC/Tools/MSVC/*/bin/Hostx64/x64/cl.exe"),
                key=lambda path: _version_key(path.parents[3].name),
            )
            if matches:
                cl_path = matches[-1]
    elif raw.is_file():
        cl_path = raw
    else:
        located = shutil.which(candidate)
        if located:
            cl_path = Path(located)
    if cl_path is None:
        return None
    cl_path = cl_path.resolve()

    override = os.environ.get("RPTP_VCVARS")
    if override:
        vcvars = Path(override).resolve()
        if not vcvars.is_file():
            return None
    else:
        vcvars = _vcvars_for_cl(cl_path)
        if vcvars is None:
            fallback = _first_toolchain()
            if fallback is None:
                return None
            vcvars = fallback.vcvars
    return MsvcToolchain(cl=cl_path, vcvars=vcvars, version=_msvc_version_of(cl_path))


def find_msvc() -> MsvcToolchain:
    """Return the first usable MSVC toolchain, caching discovery in-process.

    ``RPTP_CL`` may point at ``cl.exe`` (or a Visual Studio installation
    directory); otherwise vswhere and the standard Program Files layouts are
    searched.  A clear :class:`HarnessError` is raised when no compiler and
    matching ``vcvars64.bat`` pair can be found.
    """
    global _CACHED_TOOLCHAIN
    if _CACHED_TOOLCHAIN is not None:
        return _CACHED_TOOLCHAIN

    explicit = os.environ.get("RPTP_CL")
    if explicit:
        toolchain = _toolchain_from_cl(explicit)
        if toolchain is None:
            raise HarnessError(
                "RPTP_CL is set but does not resolve to a usable MSVC compiler: "
                f"{explicit!r}. Point RPTP_CL at ...\\VC\\Tools\\MSVC\\<version>"
                "\\bin\\Hostx64\\x64\\cl.exe (or the Visual Studio installation "
                "directory) and optionally set RPTP_VCVARS to vcvars64.bat.")
        _CACHED_TOOLCHAIN = toolchain
        return toolchain

    toolchain = _first_toolchain()
    if toolchain is None:
        located = shutil.which("cl")
        if located:
            toolchain = _toolchain_from_cl(located)
    if toolchain is None:
        raise HarnessError(
            "MSVC is unavailable: no cl.exe plus vcvars64.bat pair was found.\n"
            "Install Visual Studio Build Tools with the 'Desktop development with "
            "C++' workload, run this test from a Developer Command Prompt, or set "
            "RPTP_CL to the full path of cl.exe (and RPTP_VCVARS to vcvars64.bat).\n"
            "Searched vswhere, Program Files Visual Studio installations and PATH.")
    _CACHED_TOOLCHAIN = toolchain
    return toolchain


def _new_workdir() -> Path:
    global _COUNTER
    NATIVE_TEST_ROOT.mkdir(parents=True, exist_ok=True)
    _COUNTER += 1
    prefix = f"{os.getpid()}-{_COUNTER}-"
    return Path(tempfile.mkdtemp(prefix=prefix, dir=NATIVE_TEST_ROOT)).resolve()


@contextlib.contextmanager
def temporary_workdir() -> Iterator[Path]:
    """Yield ``build/native-tests/<pid>-<counter>-*`` and clean it on success.

    When the body raises, the directory is deliberately kept so the failure
    report can point at the generated source, binary and compiler logs.
    """
    workdir = _new_workdir()
    try:
        yield workdir
    except BaseException:
        raise
    else:
        shutil.rmtree(workdir, ignore_errors=True)


def _write_batch(directory: Path, name: str, lines: list[str]) -> Path:
    path = directory / name
    body = "@echo off\r\nsetlocal\r\n" + "\r\n".join(lines) + "\r\nexit /b %errorlevel%\r\n"
    path.write_text(body, encoding="ascii", newline="")
    return path


def _run_batch(batch: Path, workdir: Path, timeout: float,
               compiler: MsvcToolchain) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment[_VCVARS_ENV] = str(compiler.vcvars)
    try:
        return subprocess.run(
            ["cmd.exe", "/d", "/c", str(batch)],
            cwd=str(workdir),
            env=environment,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
        )
    except OSError as exc:
        raise HarnessError(
            f"Unable to start cmd.exe for {batch}: {exc}\nArtifacts kept at: {workdir}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise HarnessError(
            f"Command timed out after {timeout:.0f}s: {batch}\n"
            f"Artifacts kept at: {workdir}"
        ) from exc


def _combined_output(completed: subprocess.CompletedProcess[str]) -> str:
    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    if stdout and stderr and not stdout.endswith("\n"):
        stdout += "\n"
    return (stdout + stderr).strip()


def probe_compiler(compiler: MsvcToolchain | None = None) -> str:
    """Run ``cl /?`` through vcvars and return its output.

    Used by tests to prove that the discovered compiler is executable, without
    depending on the generated program compiling.
    """
    compiler = compiler or find_msvc()
    workdir = _new_workdir()
    try:
        batch = _write_batch(workdir, "probe.bat", [
            f'call "%{_VCVARS_ENV}%" >nul',
            "if errorlevel 1 exit /b 1",
            "cl /nologo /?",
        ])
        completed = _run_batch(batch, workdir, COMPILE_TIMEOUT_SECONDS, compiler)
        output = _combined_output(completed)
        if completed.returncode != 0:
            raise HarnessError(
                f"cl.exe failed to run (exit {completed.returncode}).\n"
                f"Toolchain: {compiler.description}\n"
                f"Artifacts kept at: {workdir}\n--- compiler output ---\n"
                f"{output or '<empty>'}")
    except BaseException:
        raise
    else:
        shutil.rmtree(workdir, ignore_errors=True)
        return output


def _compile_command(workdir: Path) -> str:
    source = workdir / "rptp_native.cpp"
    exe = workdir / EXECUTABLE_NAME
    return f'cl {CL_FLAGS} /Fe:"{exe}" "{source}"'


def build_native(generated: codegen.GeneratedProgram, workdir: Path | str) -> Path:
    """Write and compile ``generated`` into ``workdir``; return the executable.

    The compiler output is captured and attached to :class:`HarnessError` on
    failure, together with the artifact directory that was intentionally left
    in place.  The caller owns ``workdir`` and decides when to remove it.
    """
    workdir = Path(workdir).resolve()
    try:
        workdir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise HarnessError(f"Unable to create native build directory {workdir}: {exc}") from exc

    compiler = find_msvc()
    source_path, _blob_path = codegen.write_generated(generated, workdir)
    exe = workdir / EXECUTABLE_NAME
    batch = _write_batch(workdir, "build_native.bat", [
        f'call "%{_VCVARS_ENV}%" >nul',
        "if errorlevel 1 exit /b 1",
        f"cl {CL_FLAGS} /Fe:{EXECUTABLE_NAME} {source_path.name}",
    ])
    completed = _run_batch(batch, workdir, COMPILE_TIMEOUT_SECONDS, compiler)
    output = _combined_output(completed)
    if completed.returncode != 0 or not exe.is_file():
        raise HarnessError(
            f"MSVC compilation failed (exit {completed.returncode}) for {source_path}.\n"
            f"Toolchain: {compiler.description}\n"
            f"Command: {_compile_command(workdir)}\n"
            f"Artifacts kept at: {workdir}\n"
            f"--- compiler output ---\n{output or '<empty>'}")
    return exe


def run_native(exe: Path | str, max_steps: int, blob: Path | str) -> dict[str, Any]:
    """Run the native executable and return its single validated JSON object.

    A non-zero exit, a timeout, invalid JSON, trailing output or a payload whose
    top-level key set differs from :data:`EXPECTED_KEYS` all raise
    :class:`HarnessError` with stderr (and stdout, when present) attached.
    """
    exe = Path(exe).resolve()
    blob = Path(blob).resolve()
    if not exe.is_file():
        raise HarnessError(f"Native executable does not exist: {exe}")
    if not blob.is_file():
        raise HarnessError(f"Memory blob does not exist: {blob}")

    try:
        completed = subprocess.run(
            [str(exe), str(int(max_steps)), str(blob)],
            cwd=str(exe.parent),
            capture_output=True,
            text=True,
            errors="replace",
            timeout=RUN_TIMEOUT_SECONDS,
        )
    except OSError as exc:
        raise HarnessError(f"Unable to start {exe}: {exc}\nArtifacts kept at: {exe.parent}") from exc
    except subprocess.TimeoutExpired as exc:
        raise HarnessError(
            f"Native program timed out after {RUN_TIMEOUT_SECONDS:.0f}s: {exe}\n"
            f"Artifacts kept at: {exe.parent}") from exc

    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    if completed.returncode != 0:
        raise HarnessError(
            f"Native program exited with status {completed.returncode}: {exe}\n"
            f"Artifacts kept at: {exe.parent}\n"
            f"--- stdout ---\n{stdout.strip() or '<empty>'}\n"
            f"--- stderr ---\n{stderr.strip() or '<empty>'}")

    text = stdout.strip()
    try:
        payload, end = json.JSONDecoder().raw_decode(text)
    except json.JSONDecodeError as exc:
        raise HarnessError(
            f"Native program did not emit valid JSON: {exc}\n"
            f"Artifacts kept at: {exe.parent}\n"
            f"--- stdout ---\n{stdout.strip() or '<empty>'}\n"
            f"--- stderr ---\n{stderr.strip() or '<empty>'}") from exc
    trailing = text[end:].strip()
    if trailing:
        raise HarnessError(
            "Native program emitted more than one JSON value; trailing text: "
            f"{trailing[:200]!r}\nArtifacts kept at: {exe.parent}")
    if not isinstance(payload, dict):
        raise HarnessError(
            f"Native program emitted {type(payload).__name__}, expected a JSON object.\n"
            f"Artifacts kept at: {exe.parent}")

    missing = sorted(EXPECTED_KEYS - set(payload))
    unexpected = sorted(set(payload) - EXPECTED_KEYS)
    if missing or unexpected:
        raise HarnessError(
            f"Native JSON key set mismatch (missing={missing}, unexpected={unexpected}).\n"
            f"Artifacts kept at: {exe.parent}")
    registers = payload["registers"]
    if not isinstance(registers, list) or len(registers) != 32:
        raise HarnessError(
            "Native JSON 'registers' must be a list of 32 [lo, hi] pairs; got "
            f"{type(registers).__name__} of length "
            f"{len(registers) if isinstance(registers, list) else '?'}.\n"
            f"Artifacts kept at: {exe.parent}")
    for index, pair in enumerate(registers):
        if (not isinstance(pair, list) or len(pair) != 2
                or not all(isinstance(value, int) and not isinstance(value, bool) for value in pair)):
            raise HarnessError(
                f"Native JSON register {index} is not a [lo, hi] integer pair: {pair!r}\n"
                f"Artifacts kept at: {exe.parent}")
    return payload


def run_differential(image: elf.ElfImage, *, max_steps: int = 100_000) -> dict[str, Any]:
    """Lower, generate, compile and run ``image``; return the native JSON.

    This is intentionally a straight-line pipeline with no caching between
    calls: every invocation gets a fresh temporary directory.  The directory is
    removed on success and retained (with its path in the exception) on failure.
    """
    program = cfg.discover_program(image)
    result = ir.lower_program(program)
    generated = codegen.generate(program, result)

    workdir = _new_workdir()
    try:
        exe = build_native(generated, workdir)
        blob = workdir / codegen.MEMORY_BLOB_NAME
        payload = run_native(exe, max_steps, blob)
    except BaseException:
        raise
    else:
        shutil.rmtree(workdir, ignore_errors=True)
        return payload
