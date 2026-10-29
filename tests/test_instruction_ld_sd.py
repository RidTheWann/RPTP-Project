# SPDX-License-Identifier: GPL-3.0-or-later
"""Synthetic LD/SD tests for 64-bit little-endian doubleword transfers.

Model cross-checked with RPTP-REF-015 (MIPS64 Vol II-A Rev 5.04): LD p. 207,
SD p. 327, opcodes 0x37 and 0x3F, signed 16-bit offset, naturally aligned
doubleword accesses. The 32-bit effective-address truncation, the fail-closed
alignment rejection and the word-pair memory model are RPTP test definitions.
"""
from __future__ import annotations

from dataclasses import replace
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


spike = load_module("rptp_gate0_spike_ld_sd", "tools/rptp_gate0_spike.py")
ir = load_module("rptp_ir_ld_sd", "tools/rptp_ir.py")
lower = load_module("rptp_lower_ld_sd", "tools/rptp_lower.py")

BASE = spike.BASE
ZERO, V0 = spike.ZERO, spike.V0
T0, T1, T2, T3, T4, T5, T6 = 8, 9, 10, 11, 12, 13, 14
S0, S1, S2, S3 = 16, 17, 18, 19
RA = spike.RA
LD = 0x37
SD = 0x3F
LDC2 = 0x36
SDC2 = 0x3E
UINT64_MAX = 0xFFFFFFFFFFFFFFFF
DATA = 0x2000
LD_PC = BASE + 16
SD_PC = BASE + 12


def nop_word() -> int:
    return spike.encode_r(ZERO, ZERO, ZERO, 0, 0)


def jr_ra_word() -> int:
    return spike.encode_r(RA, ZERO, ZERO, 0, 0x08)


def ld_sd_fixture_rows() -> list[tuple[int, str, int]]:
    rows = [
        # LUI 0x8000 sign-extends to 0xFFFFFFFF80000000; DADDIU makes it
        # 0xFFFFFFFF80000001 so both the low and the high word are non-trivial.
        ("set_t0_high_bit", spike.encode_i(0x0F, ZERO, T0, 0x8000)),
        ("set_t0_low_bit", spike.encode_i(0x19, T0, T0, 1)),
        ("set_base", spike.encode_i(0x09, ZERO, T1, DATA)),
        ("store_doubleword", spike.encode_i(SD, T1, T0, 0)),
        ("load_doubleword", spike.encode_i(LD, T1, T2, 0)),
        ("load_low_word", spike.encode_i(0x23, T1, T3, 0)),
        ("load_high_word", spike.encode_i(0x23, T1, T4, 4)),
        ("load_into_zero", spike.encode_i(LD, T1, ZERO, 0)),
        ("second_base", spike.encode_i(0x09, T1, T5, 8)),
        ("store_negative_offset", spike.encode_i(SD, T5, T0, -8)),
        ("load_negative_offset", spike.encode_i(LD, T5, T6, -8)),
        # 0x40000000 + 0x40000000 = 0x0000000080000000: a positive doubleword
        # with a zero high word, unlike the sign-extended first value.
        ("set_positive_word", spike.encode_i(0x0F, ZERO, S0, 0x4000)),
        ("double_positive_word", spike.encode_r(S0, S0, S1, 0, 0x2D)),
        ("store_positive_doubleword", spike.encode_i(SD, T1, S1, 8)),
        ("load_positive_doubleword", spike.encode_i(LD, T1, S2, 8)),
        # SD with $zero as the source stores eight zero bytes.
        ("store_zero_source", spike.encode_i(SD, T1, ZERO, 16)),
        ("load_zero_source", spike.encode_i(LD, T1, S3, 16)),
        ("return_value", spike.encode_i(0x09, ZERO, V0, 42)),
        ("return_from_main", jr_ra_word()),
        ("return_delay_slot", nop_word()),
    ]
    return [(BASE + index * 4, name, word) for index, (name, word) in enumerate(rows)]


def ld_sd_fixture():
    data = spike.build_elf_from_rows(ld_sd_fixture_rows())
    return data, ir.analyze_elf(data)


def replace_instruction(result, pc: int, **fields):
    instructions = tuple(
        replace(instruction, **fields) if instruction.pc == pc else instruction
        for instruction in result.instructions
    )
    return replace(result, instructions=instructions)


def compiler_available() -> str | None:
    candidate = "cl" if os.name == "nt" and shutil.which("cl") else (os.environ.get("CXX") or "c++")
    return candidate if shutil.which(candidate) is not None else None


class LdSdDecodeTests(unittest.TestCase):
    def test_decode_ld_uses_opcode_0x37(self):
        instruction = spike.decode_instruction(BASE, spike.encode_i(LD, T0, T1, 0))
        self.assertEqual(instruction["op"], "ld")
        self.assertEqual((instruction["rs"], instruction["rt"], instruction["imm"]), (T0, T1, 0))

    def test_decode_sd_uses_opcode_0x3f(self):
        instruction = spike.decode_instruction(BASE, spike.encode_i(SD, T0, T1, 0))
        self.assertEqual(instruction["op"], "sd")
        self.assertEqual((instruction["rs"], instruction["rt"], instruction["imm"]), (T0, T1, 0))

    def test_offset_is_sign_extended(self):
        instruction = spike.decode_instruction(BASE, spike.encode_i(LD, T0, T1, 0xFFFF))
        self.assertEqual(instruction["imm"], -1)

    def test_neighbouring_coprocessor_loads_and_stores_remain_unsupported(self):
        for opcode in (LDC2, SDC2):
            with self.subTest(opcode=opcode):
                with self.assertRaisesRegex(ValueError, "Unsupported opcode"):
                    spike.decode_instruction(BASE, spike.encode_i(opcode, T0, T1, 0))


class LdSdIrTests(unittest.TestCase):
    def test_ir_records_register_operands_and_rt_destination(self):
        result = ir.analyze_words(BASE, {BASE: spike.encode_i(LD, T0, T1, -4)})
        instruction = result.instructions[0]
        self.assertEqual(instruction.op, "ld")
        self.assertEqual((instruction.rs, instruction.rt), (T0, T1))
        self.assertEqual(instruction.immediate, -4)
        self.assertEqual(instruction.immediate_kind, ir.SIGNED16)
        self.assertEqual(instruction.destination_register, T1)
        self.assertEqual(instruction.control, ir.FALLTHROUGH)

    def test_ir_records_no_destination_for_store_and_zero_target(self):
        store = ir.analyze_words(BASE, {BASE: spike.encode_i(SD, T0, T1, 8)}).instructions[0]
        self.assertEqual(store.op, "sd")
        self.assertIsNone(store.destination_register)
        self.assertEqual(store.immediate_kind, ir.SIGNED16)
        load = ir.analyze_words(BASE, {BASE: spike.encode_i(LD, T0, ZERO, 0)}).instructions[0]
        self.assertIsNone(load.destination_register)

    def test_ir_rejects_neighbouring_coprocessor_encodings_fail_closed(self):
        for opcode in (LDC2, SDC2):
            with self.subTest(opcode=opcode):
                with self.assertRaises(ir.AnalysisError) as caught:
                    ir.analyze_words(BASE, {BASE: spike.encode_i(opcode, T0, T1, 0)})
                self.assertEqual(caught.exception.code, ir.IR_UNSUPPORTED_INSTRUCTION)


class LdSdOracleTests(unittest.TestCase):
    def test_oracle_matches_literal_doubleword_values_and_little_endian_words(self):
        data, _ = ld_sd_fixture()
        entry, words, info = spike.parse_elf(data)
        state = spike.normalize_state(spike.execute_oracle(entry, words))
        regs = state["registers"]
        self.assertEqual(info["instruction_count"], 20)
        self.assertEqual(regs[ZERO], 0)
        self.assertEqual(regs[T0], 0xFFFFFFFF80000001)
        self.assertEqual(regs[T2], 0xFFFFFFFF80000001)
        self.assertEqual(regs[T3], 0xFFFFFFFF80000001)
        self.assertEqual(regs[T4], UINT64_MAX)
        self.assertEqual(regs[T6], 0xFFFFFFFF80000001)
        self.assertEqual(regs[S1], 0x0000000080000000)
        self.assertEqual(regs[S2], 0x0000000080000000)
        self.assertEqual(regs[S3], 0)
        self.assertEqual(regs[V0], 42)
        self.assertEqual(
            state["memory"],
            [
                [DATA, 0x80000001],
                [DATA + 4, 0xFFFFFFFF],
                [DATA + 8, 0x80000000],
                [DATA + 12, 0],
                [DATA + 16, 0],
                [DATA + 20, 0],
            ],
        )
        self.assertEqual(state["pc"], spike.RETURN_SENTINEL)
        self.assertEqual(state["trace"], [BASE + index * 4 for index in range(20)])

    def _oracle_error(self, rows: list[int]) -> str:
        words = {BASE + index * 4: word for index, word in enumerate(rows)}
        with self.assertRaises(ValueError) as caught:
            spike.execute_oracle(BASE, words)
        return str(caught.exception)

    def test_unaligned_load_is_rejected_before_memory_access(self):
        message = self._oracle_error(
            [spike.encode_i(0x09, ZERO, T1, DATA + 4), spike.encode_i(LD, T1, T2, 0)]
        )
        self.assertIn("unaligned doubleword load", message)

    def test_unaligned_store_is_rejected(self):
        message = self._oracle_error(
            [spike.encode_i(0x09, ZERO, T1, DATA + 2), spike.encode_i(SD, T1, T0, 0)]
        )
        self.assertIn("unaligned doubleword store", message)

    def test_load_from_uninitialized_memory_is_rejected(self):
        message = self._oracle_error(
            [spike.encode_i(0x09, ZERO, T1, DATA), spike.encode_i(LD, T1, T2, 0)]
        )
        self.assertIn("uninitialized memory", message)

    def test_load_requires_both_words_of_the_doubleword(self):
        message = self._oracle_error(
            [
                spike.encode_i(0x09, ZERO, T0, 5),
                spike.encode_i(0x09, ZERO, T1, DATA),
                spike.encode_i(0x2B, T1, T0, 0),
                spike.encode_i(LD, T1, T2, 0),
            ]
        )
        self.assertIn("uninitialized memory 0x00002004", message)

    def test_load_into_zero_still_performs_the_alignment_check(self):
        message = self._oracle_error(
            [spike.encode_i(0x09, ZERO, T1, DATA + 4), spike.encode_i(LD, T1, ZERO, 0)]
        )
        self.assertIn("unaligned doubleword load", message)


class LdSdLoweringTests(unittest.TestCase):
    def test_native_lowering_matches_oracle_and_literals(self):
        if compiler_available() is None:
            self.skipTest("No C++ compiler available for the LD/SD native differential")
        data, result = ld_sd_fixture()
        entry, words, _ = spike.parse_elf(data)
        oracle = spike.normalize_state(spike.execute_oracle(entry, words))
        source_text = lower.lower_to_cpp(result)
        with tempfile.TemporaryDirectory() as temp:
            out_dir = Path(temp)
            source = out_dir / "generated.cpp"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            exe = out_dir / ("rptp-ld-sd.exe" if os.name == "nt" else "rptp-ld-sd")
            command = spike.compile_generated(source, exe, "auto")
            proc = subprocess.run([str(exe)], cwd=out_dir, text=True, capture_output=True, check=False)
        self.assertEqual(proc.returncode, 0, msg=f"{command}\n{proc.stdout}\n{proc.stderr}")
        self.assertEqual(proc.stderr, "")
        native = json.loads(proc.stdout)
        self.assertEqual(native, oracle)
        self.assertEqual(native["registers"][T2], 0xFFFFFFFF80000001)
        self.assertEqual(native["registers"][T4], UINT64_MAX)
        self.assertEqual(native["registers"][S2], 0x0000000080000000)
        self.assertEqual(native["registers"][S3], 0)
        self.assertEqual(native["registers"][ZERO], 0)

    def test_load_helper_combines_words_and_rejects_bad_addresses(self):
        if compiler_available() is None:
            self.skipTest("No C++ compiler available for the LD boundary differential")
        result = ir.analyze_words(BASE, {BASE: spike.encode_i(LD, T0, T1, 0)})
        source_text = lower.lower_to_cpp(result)
        harness_text = f'''#define main rptp_generated_entry
#include "generated.cpp"
#undef main

int main() {{
    const auto load = [](std::uint32_t base, std::uint32_t low, std::uint32_t high, bool with_high) {{
        State state;
        state.pc = 0x{BASE:08X}u;
        state.registers[{T0}] = base;
        state.memory[0x{DATA:08X}u] = low;
        if (with_high) state.memory[0x{DATA + 4:08X}u] = high;
        try {{
            run_generated(state);
            std::cout << 'v' << std::hex << state.registers[{T1}] << ' ';
        }} catch (const std::runtime_error& error) {{
            const std::string message = error.what();
            std::cout << (message.find("unaligned") != std::string::npos ? "unaligned" : "uninitialized") << ' ';
        }}
    }};
    load(0x{DATA:08X}u, 0x89ABCDEFu, 0x01234567u, true);
    load(0x{DATA:08X}u, 0xFFFFFFFFu, 0xFFFFFFFFu, true);
    load(0x{DATA + 4:08X}u, 0x11111111u, 0x22222222u, true);
    load(0x{DATA:08X}u, 0x33333333u, 0x44444444u, false);
    std::cout << '\\n';
    return 0;
}}
'''
        with tempfile.TemporaryDirectory() as temp:
            out_dir = Path(temp)
            source = out_dir / "generated.cpp"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            harness = out_dir / "harness.cpp"
            harness.write_text(harness_text, encoding="utf-8", newline="\n")
            exe = out_dir / ("rptp-ld-boundary.exe" if os.name == "nt" else "rptp-ld-boundary")
            command = spike.compile_generated(harness, exe, "auto")
            proc = subprocess.run([str(exe)], cwd=out_dir, text=True, capture_output=True, check=False)
        self.assertEqual(proc.returncode, 0, msg=f"{command}\n{proc.stdout}\n{proc.stderr}")
        self.assertEqual(proc.stderr, "")
        self.assertEqual(
            proc.stdout.split(),
            ["v123456789abcdef", "vffffffffffffffff", "unaligned", "uninitialized"],
        )

    def test_store_helper_splits_words_and_rejects_unaligned_address(self):
        if compiler_available() is None:
            self.skipTest("No C++ compiler available for the SD boundary differential")
        result = ir.analyze_words(BASE, {BASE: spike.encode_i(SD, T0, T1, 0)})
        source_text = lower.lower_to_cpp(result)
        harness_text = f'''#define main rptp_generated_entry
#include "generated.cpp"
#undef main

int main() {{
    const auto store = [](std::uint32_t base, std::uint64_t value) {{
        State state;
        state.pc = 0x{BASE:08X}u;
        state.registers[{T0}] = base;
        state.registers[{T1}] = value;
        try {{
            run_generated(state);
            std::cout << 'v' << std::hex << state.memory[0x{DATA:08X}u] << ','
                      << state.memory[0x{DATA + 4:08X}u] << ' ';
        }} catch (const std::runtime_error& error) {{
            std::cout << "unaligned" << ' ';
        }}
    }};
    store(0x{DATA:08X}u, 0xFEDCBA9876543210ull);
    store(0x{DATA:08X}u, 0ull);
    store(0x{DATA + 2:08X}u, 0xFFFFFFFFFFFFFFFFull);
    std::cout << '\\n';
    return 0;
}}
'''
        with tempfile.TemporaryDirectory() as temp:
            out_dir = Path(temp)
            source = out_dir / "generated.cpp"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            harness = out_dir / "harness.cpp"
            harness.write_text(harness_text, encoding="utf-8", newline="\n")
            exe = out_dir / ("rptp-sd-boundary.exe" if os.name == "nt" else "rptp-sd-boundary")
            command = spike.compile_generated(harness, exe, "auto")
            proc = subprocess.run([str(exe)], cwd=out_dir, text=True, capture_output=True, check=False)
        self.assertEqual(proc.returncode, 0, msg=f"{command}\n{proc.stdout}\n{proc.stderr}")
        self.assertEqual(proc.stderr, "")
        self.assertEqual(proc.stdout.split(), ["v76543210,fedcba98", "v0,0", "unaligned"])

    def test_lowering_is_deterministic_and_ignores_raw_words(self):
        _, result = ld_sd_fixture()
        source = lower.lower_to_cpp(result)
        mutated = replace(
            result,
            instructions=tuple(replace(item, word=0) for item in result.instructions),
        )
        self.assertEqual(source, lower.lower_to_cpp(mutated))
        self.assertIn("load_doubleword(", source)
        self.assertIn("store_doubleword(", source)
        self.assertNotIn("\r", source)
        self.assertTrue(source.endswith("\n"))

    def test_doubleword_helpers_are_absent_without_ld_or_sd(self):
        word_load = ir.analyze_words(BASE, {BASE: spike.encode_i(0x23, T0, T1, 0)})
        source = lower.lower_to_cpp(word_load)
        self.assertNotIn("load_doubleword(", source)
        self.assertNotIn("store_doubleword(", source)

    def test_lowering_rejects_malformed_ld_metadata(self):
        _, result = ld_sd_fixture()
        cases = {
            "missing_rs": ({"rs": None}, lower.LOWER_MALFORMED_INSTRUCTION),
            "missing_rt": ({"rt": None}, lower.LOWER_MALFORMED_INSTRUCTION),
            "missing_immediate": ({"immediate": None}, lower.LOWER_MALFORMED_INSTRUCTION),
            "wrong_immediate_kind": ({"immediate_kind": ir.ZERO16}, lower.LOWER_MALFORMED_INSTRUCTION),
            "wrong_destination": ({"destination_register": None}, lower.LOWER_MALFORMED_INSTRUCTION),
            "wrong_control": ({"control": lower.DIRECT_JUMP}, lower.LOWER_INVALID_CONTROL),
            "unexpected_target": ({"target": BASE}, lower.LOWER_MALFORMED_INSTRUCTION),
            "unexpected_rd": ({"rd": T0}, lower.LOWER_MALFORMED_INSTRUCTION),
        }
        for name, (fields, code) in cases.items():
            with self.subTest(name=name):
                malformed = replace_instruction(result, LD_PC, **fields)
                with self.assertRaises(lower.LoweringError) as caught:
                    lower.lower_to_cpp(malformed)
                self.assertEqual(caught.exception.code, code)

    def test_lowering_rejects_malformed_sd_metadata(self):
        _, result = ld_sd_fixture()
        cases = {
            "store_destination": ({"destination_register": T1}, lower.LOWER_MALFORMED_INSTRUCTION),
            "missing_rs": ({"rs": None}, lower.LOWER_MALFORMED_INSTRUCTION),
            "missing_rt": ({"rt": None}, lower.LOWER_MALFORMED_INSTRUCTION),
            "missing_immediate": ({"immediate": None}, lower.LOWER_MALFORMED_INSTRUCTION),
            "wrong_control": ({"control": lower.DIRECT_JUMP}, lower.LOWER_INVALID_CONTROL),
            "unexpected_target": ({"target": BASE}, lower.LOWER_MALFORMED_INSTRUCTION),
        }
        for name, (fields, code) in cases.items():
            with self.subTest(name=name):
                malformed = replace_instruction(result, SD_PC, **fields)
                with self.assertRaises(lower.LoweringError) as caught:
                    lower.lower_to_cpp(malformed)
                self.assertEqual(caught.exception.code, code)


if __name__ == "__main__":
    unittest.main(verbosity=2)
