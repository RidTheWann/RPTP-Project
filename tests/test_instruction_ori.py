# SPDX-License-Identifier: GPL-3.0-or-later
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


spike = load_module("rptp_gate0_spike_ori", "tools/rptp_gate0_spike.py")


class OriInstructionTests(unittest.TestCase):
    def test_decode_ori_zero_extends_immediate(self):
        word = spike.encode_i(0x0D, spike.ZERO, spike.T0, 0x8001)
        instruction = spike.decode_instruction(spike.BASE, word)

        self.assertEqual(instruction["op"], "ori")
        self.assertEqual(instruction["rs"], spike.ZERO)
        self.assertEqual(instruction["rt"], spike.T0)
        self.assertEqual(instruction["imm"], 0x8001)

    def test_oracle_ori_zero_extends_and_ignores_zero_register_write(self):
        data = spike.build_ori_fixture_elf()
        entry, words, info = spike.parse_elf(data)
        state = spike.normalize_state(spike.execute_oracle(entry, words))
        regs = state["registers"]

        self.assertEqual(info["instruction_count"], 6)
        self.assertEqual(regs[spike.ZERO], 0)
        self.assertEqual(regs[spike.T0], 0x0000000000008001)
        self.assertEqual(regs[spike.T1], 0x000000000000C001)
        self.assertEqual(regs[spike.V0], 42)
        self.assertEqual(state["memory"], [])
        self.assertEqual(state["pc"], spike.RETURN_SENTINEL)
        self.assertTrue(state["halted"])
        self.assertEqual(len(state["trace"]), 6)

    def test_ori_native_matches_oracle(self):
        candidate = "cl" if os.name == "nt" and shutil.which("cl") else (os.environ.get("CXX") or "c++")
        if shutil.which(candidate) is None:
            self.skipTest(f"No C++ compiler available for native ORI differential ({candidate})")

        data = spike.build_ori_fixture_elf()
        entry, words, _ = spike.parse_elf(data)
        decoded = spike.decode_program(words)
        oracle = spike.normalize_state(spike.execute_oracle(entry, words))
        source_text = spike.emit_cpp(decoded, entry)

        with tempfile.TemporaryDirectory() as temp:
            out_dir = Path(temp)
            source = out_dir / "generated.cpp"
            source.write_text(source_text, encoding="utf-8", newline="\n")
            exe = out_dir / ("rptp-ori-spike.exe" if os.name == "nt" else "rptp-ori-spike")
            command = spike.compile_generated(source, exe, "auto")
            proc = subprocess.run([str(exe)], cwd=out_dir, text=True, capture_output=True, check=False)

            self.assertEqual(proc.returncode, 0, msg=f"{command}\n{proc.stdout}\n{proc.stderr}")
            native = json.loads(proc.stdout)

        self.assertEqual(native, oracle)
        regs = native["registers"]
        self.assertEqual(regs[spike.ZERO], 0)
        self.assertEqual(regs[spike.T0], 0x0000000000008001)
        self.assertEqual(regs[spike.T1], 0x000000000000C001)
        self.assertEqual(regs[spike.V0], 42)
        self.assertEqual(native["memory"], [])
        self.assertEqual(native["pc"], spike.RETURN_SENTINEL)
        self.assertTrue(native["halted"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
