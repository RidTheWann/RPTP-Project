# SPDX-License-Identifier: GPL-3.0-or-later
"""Synthetic-only contract and differential tests for IR-to-C++ lowering.

The fixture is assembled at test time from the existing encoder helpers in
``tools/rptp_gate0_spike.py``. No binary fixture is written or committed.
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


spike = load_module("rptp_gate0_spike_lowering", "tools/rptp_gate0_spike.py")
ir = load_module("rptp_ir_lowering", "tools/rptp_ir.py")
lower = load_module("rptp_lower_under_test", "tools/rptp_lower.py")

BASE = spike.BASE
ZERO = spike.ZERO
V0 = spike.V0
A0 = spike.A0
A1 = spike.A1
T0 = spike.T0
T1 = spike.T1
T2 = spike.T2
T3 = spike.T3
T4 = spike.T4
T5 = 13
T6 = 14
S0 = spike.S0
S1 = spike.S1
S2 = spike.S2
S3 = spike.S3
S4 = spike.S4
S5 = 21
S6 = 22
S7 = spike.S7
RA = spike.RA

MEMORY_ADDRESS = 0x2000
MEMORY_BASE = 0x4000


def nop_word() -> int:
    return spike.encode_r(ZERO, ZERO, ZERO, 0, 0x00)


def jr_ra_word() -> int:
    return spike.encode_r(RA, ZERO, ZERO, 0, 0x08)


def lowering_fixture_rows() -> list[tuple[int, str, int]]:
    rows = [
        ("save_caller_ra", spike.encode_r(RA, ZERO, S7, 0, 0x21)),
        ("set_t0_negative", spike.encode_i(0x09, ZERO, T0, -1)),
        ("set_t1_ori", spike.encode_i(0x0D, ZERO, T1, 0x8001)),
        ("zero_ori_write", spike.encode_i(0x0D, ZERO, ZERO, 0xFFFF)),
        ("zero_addiu_write", spike.encode_i(0x09, ZERO, ZERO, 1)),
        ("add_t2_wraps", spike.encode_r(T0, T1, T2, 0, 0x21)),
        ("set_t3", spike.encode_i(0x0D, ZERO, T3, MEMORY_BASE)),
        ("set_s0", spike.encode_i(0x09, ZERO, S0, 9)),
        ("store_t0", spike.encode_i(0x2B, T3, T0, -MEMORY_ADDRESS)),
        ("load_t4", spike.encode_i(0x23, T3, T4, -MEMORY_ADDRESS)),
        ("beq_taken", spike.encode_i(0x04, T0, T4, 2)),
        ("beq_delay", spike.encode_i(0x09, ZERO, S1, 7)),
        ("beq_skipped", spike.encode_i(0x09, ZERO, S2, 99)),
        ("bne_not_taken", spike.encode_i(0x05, T0, T4, 2)),
        ("bne_delay", spike.encode_i(0x09, ZERO, S5, 11)),
        ("bne_fallthrough", spike.encode_i(0x09, ZERO, S6, 88)),
        ("jump_to_call", spike.encode_j(0x02, BASE + 0x4C)),
        ("jump_delay", spike.encode_i(0x09, ZERO, A0, 13)),
        ("jump_skipped", spike.encode_i(0x09, ZERO, S3, 33)),
        ("jal_to_callee", spike.encode_j(0x03, BASE + 0x64)),
        ("jal_delay", spike.encode_i(0x09, ZERO, A1, 17)),
        ("set_t5", spike.encode_i(0x09, ZERO, T5, 19)),
        ("restore_caller_ra", spike.encode_i(0x09, S7, RA, 0)),
        ("return_from_main", jr_ra_word()),
        ("main_return_delay", spike.encode_i(0x09, ZERO, S4, 23)),
        ("callee", spike.encode_i(0x09, ZERO, V0, 30)),
        ("callee_return", jr_ra_word()),
        ("callee_delay", spike.encode_i(0x09, ZERO, S2, 21)),
        ("unreachable_nop", nop_word()),
    ]
    return [(BASE + index * 4, name, word) for index, (name, word) in enumerate(rows)]


def lowering_result():
    data = spike.build_elf_from_rows(lowering_fixture_rows())
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


class LoweringSourceTests(unittest.TestCase):
    def test_lowering_is_deterministic_and_ignores_raw_words(self):
        _, result = lowering_result()
        first = lower.lower_to_cpp(result)
        second = lower.lower_to_cpp(result)
        changed_words = replace(
            result,
            instructions=tuple(replace(instruction, word=0) for instruction in result.instructions),
        )

        self.assertEqual(first, second)
        self.assertEqual(first, lower.lower_to_cpp(changed_words))
        self.assertTrue(first.endswith("\n"))
        self.assertNotIn("\r", first)

    def test_generated_source_has_no_local_paths_or_timestamps(self):
        _, result = lowering_result()
        source = lower.lower_to_cpp(result)

        self.assertNotIn(str(ROOT), source)
        self.assertNotIn("D:\\", source)
        self.assertNotIn("C:\\", source)
        self.assertNotIn("Generated at", source)
        self.assertNotIn("timestamp", source.lower())


class LoweringNativeTests(unittest.TestCase):
    def test_generated_native_state_matches_oracle(self):
        candidate = compiler_available()
        if candidate is None:
            self.skipTest("No C++ compiler available for native IR-lowering differential")

        data, result = lowering_result()
        entry, words, _ = spike.parse_elf(data)
        source_text = lower.lower_to_cpp(result)
        oracle = spike.normalize_state(spike.execute_oracle(entry, words))

        with tempfile.TemporaryDirectory() as temp:
            out_dir = Path(temp)
            source = out_dir / "generated.cpp"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            exe = out_dir / ("rptp-lowering.exe" if os.name == "nt" else "rptp-lowering")
            command = spike.compile_generated(source, exe, "auto")
            proc = subprocess.run([str(exe)], cwd=out_dir, text=True, capture_output=True, check=False)

            self.assertEqual(proc.returncode, 0, msg=f"{command}\n{proc.stdout}\n{proc.stderr}")
            native = json.loads(proc.stdout)

        self.assertEqual(native, oracle)
        registers = native["registers"]
        self.assertEqual(
            native["trace"],
            [
                BASE + 0x00,
                BASE + 0x04,
                BASE + 0x08,
                BASE + 0x0C,
                BASE + 0x10,
                BASE + 0x14,
                BASE + 0x18,
                BASE + 0x1C,
                BASE + 0x20,
                BASE + 0x24,
                BASE + 0x28,
                BASE + 0x2C,
                BASE + 0x34,
                BASE + 0x38,
                BASE + 0x3C,
                BASE + 0x40,
                BASE + 0x44,
                BASE + 0x4C,
                BASE + 0x50,
                BASE + 0x64,
                BASE + 0x68,
                BASE + 0x6C,
                BASE + 0x54,
                BASE + 0x58,
                BASE + 0x5C,
                BASE + 0x60,
            ],
        )
        self.assertEqual(registers[ZERO], 0)
        self.assertEqual(registers[T0], 0xFFFFFFFFFFFFFFFF)
        self.assertEqual(registers[T1], 0x0000000000008001)
        self.assertEqual(registers[T2], 0x0000000000008000)
        self.assertEqual(registers[T3], MEMORY_BASE)
        self.assertEqual(registers[T4], 0xFFFFFFFFFFFFFFFF)
        self.assertEqual(registers[T5], 19)
        self.assertEqual(registers[S0], 9)
        self.assertEqual(registers[S1], 7)
        self.assertEqual(registers[S2], 21)
        self.assertEqual(registers[S3], 0)
        self.assertEqual(registers[S4], 23)
        self.assertEqual(registers[S5], 11)
        self.assertEqual(registers[S6], 88)
        self.assertEqual(registers[S7], spike.RETURN_SENTINEL)
        self.assertEqual(registers[A0], 13)
        self.assertEqual(registers[A1], 17)
        self.assertEqual(registers[V0], 30)
        self.assertEqual(registers[RA], spike.RETURN_SENTINEL)
        self.assertEqual(native["memory"], [[MEMORY_ADDRESS, 0xFFFFFFFF]])
        self.assertEqual(native["pc"], spike.RETURN_SENTINEL)
        self.assertTrue(native["halted"])

    def test_indirect_jump_uses_the_runtime_register_target(self):
        candidate = compiler_available()
        if candidate is None:
            self.skipTest("No C++ compiler available for native indirect-jump test")

        rows = [
            ("save_caller_ra", spike.encode_r(RA, ZERO, S7, 0, 0x21)),
            ("call_helper", spike.encode_j(0x03, BASE + 0x20)),
            ("call_delay", nop_word()),
            ("copy_return_address", spike.encode_r(RA, ZERO, T0, 0, 0x21)),
            ("add_target_offset", spike.encode_i(0x09, T0, T0, 0x1C)),
            ("restore_caller_ra", spike.encode_i(0x09, S7, RA, 0)),
            ("indirect_jump", spike.encode_r(T0, ZERO, ZERO, 0, 0x08)),
            ("jump_delay", nop_word()),
            ("helper_return", jr_ra_word()),
            ("helper_delay", nop_word()),
            ("jump_target", spike.encode_i(0x09, ZERO, V0, 42)),
            ("return_from_main", jr_ra_word()),
            ("return_delay", spike.encode_i(0x09, ZERO, S1, 9)),
        ]
        data = spike.build_elf_from_rows([(BASE + index * 4, name, word) for index, (name, word) in enumerate(rows)])
        entry, words, _ = spike.parse_elf(data)
        result = ir.analyze_elf(data)
        oracle = spike.normalize_state(spike.execute_oracle(entry, words))
        source_text = lower.lower_to_cpp(result)

        with tempfile.TemporaryDirectory() as temp:
            out_dir = Path(temp)
            source = out_dir / "generated.cpp"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            exe = out_dir / ("rptp-lowering-jr.exe" if os.name == "nt" else "rptp-lowering-jr")
            command = spike.compile_generated(source, exe, "auto")
            proc = subprocess.run([str(exe)], cwd=out_dir, text=True, capture_output=True, check=False)

        self.assertEqual(proc.returncode, 0, msg=f"{command}\n{proc.stdout}\n{proc.stderr}")
        native = json.loads(proc.stdout)
        self.assertEqual(native, oracle)
        self.assertEqual(
            native["trace"],
            [
                BASE + 0x00,
                BASE + 0x04,
                BASE + 0x08,
                BASE + 0x20,
                BASE + 0x24,
                BASE + 0x0C,
                BASE + 0x10,
                BASE + 0x14,
                BASE + 0x18,
                BASE + 0x1C,
                BASE + 0x28,
                BASE + 0x2C,
                BASE + 0x30,
            ],
        )
        self.assertEqual(native["registers"][V0], 42)
        self.assertEqual(native["registers"][S1], 9)
        self.assertEqual(native["registers"][RA], spike.RETURN_SENTINEL)
        self.assertEqual(native["pc"], spike.RETURN_SENTINEL)
        self.assertTrue(native["halted"])

    def test_uninitialized_load_fails_loudly_at_runtime(self):
        candidate = compiler_available()
        if candidate is None:
            self.skipTest("No C++ compiler available for native IR-lowering failure test")

        result = ir.analyze_words(BASE, {BASE: spike.encode_i(0x23, ZERO, T0, 0)})
        source_text = lower.lower_to_cpp(result)

        with tempfile.TemporaryDirectory() as temp:
            out_dir = Path(temp)
            source = out_dir / "generated.cpp"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            exe = out_dir / ("rptp-lowering-failure.exe" if os.name == "nt" else "rptp-lowering-failure")
            command = spike.compile_generated(source, exe, "auto")
            proc = subprocess.run([str(exe)], cwd=out_dir, text=True, capture_output=True, check=False)

        self.assertEqual(proc.returncode, 2, msg=f"{command}\n{proc.stdout}\n{proc.stderr}")
        self.assertEqual(proc.stdout, "")
        self.assertEqual(proc.stderr, "LOWER_RUNTIME_ERROR: read from uninitialized guest memory\n")


class LoweringFailureTests(unittest.TestCase):
    def assert_lowering_error(self, code: str, result) -> None:
        with self.assertRaises(lower.LoweringError) as caught:
            lower.lower_to_cpp(result)
        self.assertEqual(caught.exception.code, code)
        self.assertIn(code, str(caught.exception))

    def test_unsupported_operation_is_rejected(self):
        _, result = lowering_result()
        self.assert_lowering_error(
            lower.LOWER_UNSUPPORTED_OP,
            replace_instruction(result, BASE + 0x04, op="dadd"),
        )

    def test_malformed_immediate_is_rejected(self):
        _, result = lowering_result()
        self.assert_lowering_error(
            lower.LOWER_MALFORMED_INSTRUCTION,
            replace_instruction(result, BASE + 0x04, immediate=None),
        )

    def test_extraneous_operand_is_rejected(self):
        _, result = lowering_result()
        self.assert_lowering_error(
            lower.LOWER_MALFORMED_INSTRUCTION,
            replace_instruction(result, BASE + 0x70, rs=T0),
        )

    def test_invalid_direct_target_is_rejected(self):
        _, result = lowering_result()
        self.assert_lowering_error(
            lower.LOWER_INVALID_TARGET,
            replace_instruction(result, BASE + 0x28, target=BASE + 0x35),
        )

    def test_invalid_delay_slot_ownership_is_rejected(self):
        _, result = lowering_result()
        self.assert_lowering_error(
            lower.LOWER_INVALID_DELAY_SLOT,
            replace_instruction(result, BASE + 0x2C, delay_slot_for=None),
        )

    def test_missing_blocks_are_rejected(self):
        _, result = lowering_result()
        self.assert_lowering_error(lower.LOWER_INVALID_BLOCK, replace(result, blocks=()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
