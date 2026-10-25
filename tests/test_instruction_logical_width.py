# SPDX-License-Identifier: GPL-3.0-or-later
"""Independent regression tests for 64-bit register width semantics of ORI, XORI, and ANDI."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module {relative_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


spike = load_module("rptp_gate0_spike_logical_width", "tools/rptp_gate0_spike.py")
ir = load_module("rptp_ir_logical_width", "tools/rptp_ir.py")
lower = load_module("rptp_lower_logical_width", "tools/rptp_lower.py")

BASE = spike.BASE
ZERO = spike.ZERO
V0 = spike.V0
T0 = spike.T0
T1 = spike.T1
T2 = spike.T2
T3 = spike.T3
RA = spike.RA

ANDI = 0x0C
ORI = 0x0D
XORI = 0x0E
LUI = 0x0F
ADDIU = 0x09
XOR_FUNCT = 0x26
SLTU_FUNCT = 0x2B


def nop_word() -> int:
    return spike.encode_r(ZERO, ZERO, ZERO, 0, 0x00)


def jr_ra_word() -> int:
    return spike.encode_r(RA, ZERO, ZERO, 0, 0x08)


def reproducer_fixture_rows() -> list[tuple[int, str, int]]:
    """Reproducer sequence reported in audit finding F1."""
    rows = [
        ("set_lui", spike.encode_i(LUI, ZERO, T0, 0xFFFF)),
        ("ori_full", spike.encode_i(ORI, T0, T0, 0xFFFF)),
        ("set_all_ones", spike.encode_i(ADDIU, ZERO, T1, -1)),
        ("xor_test", spike.encode_r(T0, T1, T2, 0, XOR_FUNCT)),
        ("sltu_test", spike.encode_r(T0, T1, T3, 0, SLTU_FUNCT)),
        ("return_from_main", jr_ra_word()),
        ("main_return_delay_slot", nop_word()),
    ]
    return [(BASE + index * 4, name, word) for index, (name, word) in enumerate(rows)]


def reproducer_fixture():
    data = spike.build_elf_from_rows(reproducer_fixture_rows())
    return data, ir.analyze_elf(data)


def execute_oracle_with_registers(words: dict[int, int], initial_regs: dict[int, int]) -> dict[str, Any]:
    old_initial_state = spike.initial_state

    def patched_initial_state(entry_pc: int):
        state = old_initial_state(entry_pc)
        for r, v in initial_regs.items():
            state["registers"][r] = v
        return state

    spike.initial_state = patched_initial_state
    try:
        return spike.execute_oracle(BASE, words)
    finally:
        spike.initial_state = old_initial_state


def compiler_available() -> str | None:
    candidate = "cl" if os.name == "nt" and shutil.which("cl") else (os.environ.get("CXX") or "c++")
    return candidate if shutil.which(candidate) is not None else None


class LogicalWidthReproducerTests(unittest.TestCase):
    def test_reproducer_oracle_preserves_64_bit_width(self):
        data, _ = reproducer_fixture()
        entry, words, _ = spike.parse_elf(data)
        state = spike.normalize_state(spike.execute_oracle(entry, words))
        regs = state["registers"]

        # lui t0, 0xFFFF -> (0xFFFF << 16) sign-extended to 64-bit = 0xFFFFFFFFFFFF0000
        # ori t0, t0, 0xFFFF -> 0xFFFFFFFFFFFF0000 | 0x000000000000FFFF = 0xFFFFFFFFFFFFFFFF
        self.assertEqual(regs[T0], 0xFFFFFFFFFFFFFFFF)
        # addiu t1, zero, -1 -> -1 sign-extended to 64-bit = 0xFFFFFFFFFFFFFFFF
        self.assertEqual(regs[T1], 0xFFFFFFFFFFFFFFFF)
        # xor t2, t0, t1 -> 0xFFFFFFFFFFFFFFFF ^ 0xFFFFFFFFFFFFFFFF = 0x0000000000000000
        self.assertEqual(regs[T2], 0x0000000000000000)
        # sltu t3, t0, t1 -> (0xFFFFFFFFFFFFFFFF < 0xFFFFFFFFFFFFFFFF) unsigned = 0
        self.assertEqual(regs[T3], 0x0000000000000000)

    def test_reproducer_native_matches_literal_constants(self):
        candidate = compiler_available()
        if candidate is None:
            self.skipTest("No C++ compiler available for the logical-width reproducer differential")

        data, result = reproducer_fixture()
        source_text = lower.lower_to_cpp(result)

        with tempfile.TemporaryDirectory() as temp:
            out_dir = Path(temp)
            source = out_dir / "generated.cpp"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            exe = out_dir / ("rptp-reproducer.exe" if os.name == "nt" else "rptp-reproducer")
            command = spike.compile_generated(source, exe, "auto")
            proc = subprocess.run([str(exe)], cwd=out_dir, text=True, capture_output=True, check=False)

        self.assertEqual(proc.returncode, 0, msg=f"{command}\n{proc.stdout}\n{proc.stderr}")
        native = json.loads(proc.stdout)
        regs = native["registers"]

        # lui t0, 0xFFFF -> 0xFFFFFFFFFFFF0000
        # ori t0, t0, 0xFFFF -> 0xFFFFFFFFFFFF0000 | 0x000000000000FFFF = 0xFFFFFFFFFFFFFFFF
        self.assertEqual(regs[T0], 0xFFFFFFFFFFFFFFFF)
        # addiu t1, zero, -1 -> 0xFFFFFFFFFFFFFFFF
        self.assertEqual(regs[T1], 0xFFFFFFFFFFFFFFFF)
        # xor t2, t0, t1 -> 0xFFFFFFFFFFFFFFFF ^ 0xFFFFFFFFFFFFFFFF = 0
        self.assertEqual(regs[T2], 0x0000000000000000)
        # sltu t3, t0, t1 -> (0xFFFFFFFFFFFFFFFF < 0xFFFFFFFFFFFFFFFF) unsigned = 0
        self.assertEqual(regs[T3], 0x0000000000000000)


class LogicalWidthExplicitOracleTests(unittest.TestCase):
    def test_oracle_ori_preserves_upper_bits(self):
        cases = (
            # rs=0x8000000080000000, imm16=0xFFFF -> 0x8000000080000000 | 0x000000000000FFFF = 0x800000008000FFFF
            (0x8000000080000000, 0xFFFF, 0x800000008000FFFF),
            # rs=0xFFFFFFFF00000000, imm16=0x1234 -> 0xFFFFFFFF00000000 | 0x0000000000001234 = 0xFFFFFFFF00001234
            (0xFFFFFFFF00000000, 0x1234, 0xFFFFFFFF00001234),
            # rs=0x0000000100000000, imm16=0x0001 -> 0x0000000100000000 | 0x0000000000000001 = 0x0000000100000001
            (0x0000000100000000, 0x0001, 0x0000000100000001),
        )
        for rs_val, imm, expected in cases:
            with self.subTest(rs_val=hex(rs_val), imm=hex(imm)):
                words = {
                    BASE: spike.encode_i(ORI, T0, T1, imm),
                    BASE + 4: jr_ra_word(),
                    BASE + 8: nop_word(),
                }
                state = execute_oracle_with_registers(words, {T0: rs_val})
                self.assertEqual(state["registers"][T1], expected)

    def test_oracle_xori_preserves_upper_bits(self):
        cases = (
            # rs=0x8000000080000000, imm16=0xFFFF -> 0x8000000080000000 ^ 0x000000000000FFFF = 0x800000008000FFFF
            (0x8000000080000000, 0xFFFF, 0x800000008000FFFF),
            # rs=0xFFFFFFFF0000F0F0, imm16=0x00FF -> 0xFFFFFFFF0000F0F0 ^ 0x00000000000000FF = 0xFFFFFFFF0000F00F
            (0xFFFFFFFF0000F0F0, 0x00FF, 0xFFFFFFFF0000F00F),
            # rs=0x0000000100000000, imm16=0x0001 -> 0x0000000100000000 ^ 0x0000000000000001 = 0x0000000100000001
            (0x0000000100000000, 0x0001, 0x0000000100000001),
        )
        for rs_val, imm, expected in cases:
            with self.subTest(rs_val=hex(rs_val), imm=hex(imm)):
                words = {
                    BASE: spike.encode_i(XORI, T0, T1, imm),
                    BASE + 4: jr_ra_word(),
                    BASE + 8: nop_word(),
                }
                state = execute_oracle_with_registers(words, {T0: rs_val})
                self.assertEqual(state["registers"][T1], expected)

    def test_oracle_andi_zeroes_upper_bits(self):
        cases = (
            # rs=0xFFFFFFFF12345678, imm16=0x00FF -> 0xFFFFFFFF12345678 & 0x00000000000000FF = 0x0000000000000078
            (0xFFFFFFFF12345678, 0x00FF, 0x0000000000000078),
            # rs=0xFFFFFFFF0000FF00, imm16=0x0F0F -> 0xFFFFFFFF0000FF00 & 0x0000000000000F0F = 0x0000000000000F00
            (0xFFFFFFFF0000FF00, 0x0F0F, 0x0000000000000F00),
        )
        for rs_val, imm, expected in cases:
            with self.subTest(rs_val=hex(rs_val), imm=hex(imm)):
                words = {
                    BASE: spike.encode_i(ANDI, T0, T1, imm),
                    BASE + 4: jr_ra_word(),
                    BASE + 8: nop_word(),
                }
                state = execute_oracle_with_registers(words, {T0: rs_val})
                self.assertEqual(state["registers"][T1], expected)

    def test_oracle_logical_immediates_ignore_zero_register_write(self):
        for op in (ORI, XORI, ANDI):
            with self.subTest(op=op):
                words = {
                    BASE: spike.encode_i(op, T0, ZERO, 0xFFFF),
                    BASE + 4: jr_ra_word(),
                    BASE + 8: nop_word(),
                }
                state = execute_oracle_with_registers(words, {T0: 0xFFFFFFFFFFFFFFFF})
                self.assertEqual(state["registers"][ZERO], 0)


class LogicalWidthNativeBoundaryTests(unittest.TestCase):
    def test_native_helpers_preserve_or_zero_upper_bits(self):
        candidate = compiler_available()
        if candidate is None:
            self.skipTest("No C++ compiler available for native boundary checks")

        words = {
            BASE: spike.encode_i(ORI, T0, T1, 0xFFFF),
            BASE + 4: spike.encode_i(XORI, T0, T2, 0xFFFF),
            BASE + 8: spike.encode_i(ANDI, T0, T3, 0x00FF),
            BASE + 12: jr_ra_word(),
            BASE + 16: nop_word(),
        }
        result = ir.analyze_words(BASE, words)
        source_text = lower.lower_to_cpp(result)

        harness_text = f'''#define main rptp_generated_entry
#include "generated.cpp"
#undef main
#include <cassert>
#include <iostream>

int main() {{
    // ORI case 1: 0x8000000080000000 | 0xFFFF = 0x800000008000FFFF
    {{
        State s;
        s.pc = 0x{BASE:08X}u;
        s.registers[{T0}] = 0x8000000080000000ull;
        run_generated(s);
        if (s.registers[{T1}] != 0x800000008000FFFFull) {{
            std::cerr << "ORI fail: got 0x" << std::hex << s.registers[{T1}] << std::endl;
            return 1;
        }}
    }}
    // XORI case 1: 0x8000000080000000 ^ 0xFFFF = 0x800000008000FFFF
    {{
        State s;
        s.pc = 0x{BASE + 4:08X}u;
        s.registers[{T0}] = 0x8000000080000000ull;
        run_generated(s);
        if (s.registers[{T2}] != 0x800000008000FFFFull) {{
            std::cerr << "XORI fail: got 0x" << std::hex << s.registers[{T2}] << std::endl;
            return 2;
        }}
    }}
    // ANDI case 1: 0xFFFFFFFF12345678 & 0x00FF = 0x0000000000000078
    {{
        State s;
        s.pc = 0x{BASE + 8:08X}u;
        s.registers[{T0}] = 0xFFFFFFFF12345678ull;
        run_generated(s);
        if (s.registers[{T3}] != 0x0000000000000078ull) {{
            std::cerr << "ANDI fail: got 0x" << std::hex << s.registers[{T3}] << std::endl;
            return 3;
        }}
    }}
    return 0;
}}
'''
        with tempfile.TemporaryDirectory() as temp:
            out_dir = Path(temp)
            source = out_dir / "generated.cpp"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            harness = out_dir / "harness.cpp"
            harness.write_text(harness_text, encoding="utf-8", newline="\n")
            exe = out_dir / ("rptp-boundary.exe" if os.name == "nt" else "rptp-boundary")
            command = spike.compile_generated(harness, exe, "auto")
            proc = subprocess.run([str(exe)], cwd=out_dir, text=True, capture_output=True, check=False)

        self.assertEqual(proc.returncode, 0, msg=f"{command}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
