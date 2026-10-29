# SPDX-License-Identifier: GPL-3.0-or-later
"""Deterministic directed fuzz tests for the RPTP reference oracle.

The generators use only ``random.Random(fixed_seed)``; no wall-clock time,
environment entropy or global random state is consulted.  Every case is a
synthetic ELF assembled in memory, ends in ``jr $ra`` and is executed twice so
that non-determinism is caught directly.
"""
from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.rptp.cfg import discover_program
from tools.rptp.elf import parse_elf_bytes
from tools.rptp.fixtures import (
    CODE_BASE,
    DATA_BASE,
    RA,
    ZERO,
    Assembler,
    build_elf,
    encode_i,
    encode_r,
)
from tools.rptp.oracle import ExecutionError, RETURN_SENTINEL, run_oracle

MASK64 = 0xFFFFFFFFFFFFFFFF
RAM_SIZE = 0x02000000
BASE_REG = 27  # $k1 is reserved as a store base and is never a destination.
DEST_POOL = list(range(1, 27)) + [28, 29]
ALL_REGS = list(range(0, 31))  # $ra (31) is never read or written here.

STRAIGHT_CASES = 200
BRANCH_CASES = 100

S32_OPS = {
    "addiu", "addu", "subu", "slt", "sltu", "slti", "sltiu", "lui",
    "sll", "srl", "sra", "sllv", "srlv", "srav",
}
S64_OPS = {
    "daddiu", "daddu", "dsubu", "and", "or", "xor", "nor",
    "dsll", "dsrl", "dsra", "dsll32", "dsrl32", "dsra32",
    "dsllv", "dsrlv", "dsrav",
}
LOGICAL_IMM_OPS = {"andi", "ori", "xori"}

STRAIGHT_OPS = (
    ["addiu"] * 4 + ["daddiu"] * 2
    + ["addu"] * 3 + ["subu"] * 2 + ["daddu"] * 3 + ["dsubu"] * 2
    + ["and", "or", "xor", "nor"]
    + ["slt", "sltu", "slti", "sltiu"]
    + ["lui"]
    + ["andi", "ori", "xori"] * 2
    + ["sll", "srl", "sra"] * 2 + ["sllv", "srlv", "srav"]
    + ["dsll", "dsrl", "dsra"] * 2
    + ["dsll32", "dsrl32", "dsra32"]
    + ["dsllv", "dsrlv", "dsrav"]
)

BRANCH_FILL_OPS = [
    "addiu", "addu", "subu", "daddu", "dsubu", "and", "or", "xor", "nor",
    "sll", "srl", "sra", "dsll", "dsrl", "dsra", "dsll32", "lui",
]

STORE_OPCODE = {"sb": 0x28, "sh": 0x29, "sw": 0x2B, "sd": 0x3F, "sq": 0x1F}
STORE_ALIGN = {"sb": 1, "sh": 2, "sw": 4, "sd": 8, "sq": 16}

REGISTER_FUNCTS = {"and": 0x24, "or": 0x25, "xor": 0x26, "nor": 0x27,
                   "slt": 0x2A, "sltu": 0x2B}
SHIFT_FUNCTS = {"sll": 0x00, "srl": 0x02, "sra": 0x03,
                "sllv": 0x04, "srlv": 0x06, "srav": 0x07,
                "dsllv": 0x14, "dsrlv": 0x16, "dsrav": 0x17,
                "dsll": 0x38, "dsrl": 0x3A, "dsra": 0x3B,
                "dsll32": 0x3C, "dsrl32": 0x3E, "dsra32": 0x3F}
VARIABLE_SHIFTS = {"sllv", "srlv", "srav", "dsllv", "dsrlv", "dsrav"}


def emit_safe_alu(asm: Assembler, op: str, dest: int, rng: random.Random,
                  *, rs: int | None = None, rt: int | None = None) -> dict:
    """Emit one branch-free arithmetic/logical/shift instruction."""
    rs = rng.randrange(0, 31) if rs is None else rs
    rt = rng.randrange(0, 31) if rt is None else rt
    sa = rng.randrange(0, 32)
    if op in {"addiu", "daddiu", "slti", "sltiu"}:
        imm = rng.randrange(-0x8000, 0x8000)
    else:
        imm = rng.randrange(0, 1 << 16)

    if op == "addiu":
        asm.addiu(dest, rs, imm)
    elif op == "daddiu":
        asm.emit(encode_i(0x19, dest, rs, imm))
    elif op == "addu":
        asm.addu(dest, rs, rt)
    elif op == "subu":
        asm.emit(encode_r(0x23, dest, rs, rt))
    elif op == "daddu":
        asm.daddu(dest, rs, rt)
    elif op == "dsubu":
        asm.dsubu(dest, rs, rt)
    elif op in REGISTER_FUNCTS:
        asm.emit(encode_r(REGISTER_FUNCTS[op], dest, rs, rt))
    elif op == "slti":
        asm.emit(encode_i(0x0A, dest, rs, imm))
    elif op == "sltiu":
        asm.emit(encode_i(0x0B, dest, rs, imm))
    elif op == "lui":
        asm.lui(dest, imm)
    elif op == "andi":
        asm.andi(dest, rs, imm)
    elif op == "ori":
        asm.ori(dest, rs, imm)
    elif op == "xori":
        asm.emit(encode_i(0x0E, dest, rs, imm))
    elif op in VARIABLE_SHIFTS:
        asm.emit(encode_r(SHIFT_FUNCTS[op], dest, rs, rt))
    elif op in SHIFT_FUNCTS:
        asm.emit(encode_r(SHIFT_FUNCTS[op], dest, ZERO, rt, sa))
    else:  # pragma: no cover - generator bug
        raise AssertionError(f"unhandled fuzz op {op}")
    return {"op": op, "dest": dest, "rs": rs, "rt": rt, "imm": imm & 0xFFFF}


def build_straight_case(seed: int) -> tuple:
    rng = random.Random(seed)
    asm = Assembler()
    dests = DEST_POOL[:]
    rng.shuffle(dests)
    initial = {register: rng.getrandbits(64) for register in range(1, 31)
               if register != BASE_REG}
    initial[BASE_REG] = DATA_BASE

    checks = []
    op_log = []
    for _ in range(rng.randint(8, 18)):
        if rng.random() < 0.20:
            kind = rng.choice(tuple(STORE_OPCODE))
            alignment = STORE_ALIGN[kind]
            offset = alignment * rng.randrange(0, 4)
            rt = rng.choice(ALL_REGS)
            asm.emit(encode_i(STORE_OPCODE[kind], rt, BASE_REG, offset))
            op_log.append((kind, rt, offset))
            continue
        op = rng.choice(STRAIGHT_OPS)
        dest = dests.pop()
        if op in LOGICAL_IMM_OPS:
            record = emit_safe_alu(asm, op, dest, rng, rs=BASE_REG)
        else:
            record = emit_safe_alu(asm, op, dest, rng)
        checks.append(record)
        op_log.append((record["op"], record["dest"], record["rs"],
                       record["rt"], record["imm"]))

    asm.jr(RA)
    asm.nop()
    words = asm.resolve()
    program = discover_program(parse_elf_bytes(build_elf(words)))
    return program, initial, checks, words, op_log


def build_branch_case(seed: int) -> tuple:
    rng = random.Random(seed)
    slot_count = rng.randint(14, 26)
    candidate_slots = list(range(0, slot_count - 3, 2))
    branch_count = rng.randint(2, min(4, len(candidate_slots)))
    branch_slots = sorted(rng.sample(candidate_slots, branch_count))
    reserved = set()
    for index in branch_slots:
        reserved.update((index, index + 1))

    plan = {}
    for index in branch_slots:
        targets = [slot for slot in range(index + 2, slot_count - 1)
                   if slot not in reserved]
        if not targets:  # pragma: no cover - generator invariant
            raise AssertionError("no forward branch target available")
        plan[index] = (rng.choice(["beq", "bne", "blez", "bltz"]),
                       rng.choice(targets))

    initial = {}
    special = [0, 1, MASK64, 1 << 63, MASK64 - 1, (1 << 63) - 1]
    for register in range(1, 31):
        initial[register] = (rng.choice(special) if rng.random() < 0.5
                             else rng.getrandbits(64))

    asm = Assembler()
    for slot in range(slot_count):
        asm.label(f"slot{slot}")
        if slot == slot_count - 2:
            asm.jr(RA)
        elif slot == slot_count - 1:
            asm.nop()
        elif slot in plan:
            kind, target = plan[slot]
            rs = rng.choice(ALL_REGS)
            rt = rng.choice(ALL_REGS)
            if kind == "beq":
                asm.beq(rs, rt, f"slot{target}")
            elif kind == "bne":
                asm.bne(rs, rt, f"slot{target}")
            elif kind == "blez":
                asm.blez(rs, f"slot{target}")
            else:
                asm.bltz(rs, f"slot{target}")
        else:
            op = rng.choice(BRANCH_FILL_OPS)
            emit_safe_alu(asm, op, rng.randrange(1, 31), rng)

    words = asm.resolve()
    program = discover_program(parse_elf_bytes(build_elf(words)))
    return program, initial, plan, slot_count, words


class OracleFuzzCase(unittest.TestCase):
    def assert_register_zero(self, state, context: str) -> None:
        self.assertEqual(state["registers"][0], [0, 0],
                         f"$zero was modified\n{context}")

    def assert_sign_extension(self, value: list[int], kind: str,
                              context: str) -> None:
        lo, hi = value
        if kind == "s32":
            negative = (lo >> 31) & 1
            self.assertEqual(hi, MASK64 if negative else 0,
                             f"32-bit result is not sign-extended to bit 127\n{context}")
            self.assertEqual(lo >> 32, 0xFFFFFFFF if negative else 0,
                             f"32-bit result bits 63..32 do not match bit 31\n{context}")
        else:
            negative = (lo >> 63) & 1
            self.assertEqual(hi, MASK64 if negative else 0,
                             f"64-bit result is not sign-extended to bit 127\n{context}")

    def assert_memory_bytes(self, state, context: str) -> None:
        for address, value in state["memory"]:
            self.assertGreaterEqual(address, 0, context)
            self.assertLess(address, RAM_SIZE, context)
            self.assertGreaterEqual(value, 0,
                                    f"memory write value {value} is not a byte\n{context}")
            self.assertLessEqual(value, 0xFF,
                                 f"memory write value {value} is not a byte\n{context}")

    def run_twice(self, program, initial, context: str):
        try:
            first = run_oracle(program, initial_registers=initial)
            second = run_oracle(program, initial_registers=initial)
        except ExecutionError as exc:
            self.fail(f"oracle raised ExecutionError: {exc}\n{context}")
        except Exception as exc:  # noqa: BLE001 - a crash is a fuzz failure
            self.fail(f"oracle crashed with {type(exc).__name__}: {exc}\n{context}")
        self.assertEqual(first, second,
                         f"two runs of the same fixture differ\n{context}")
        return first

    def test_straight_line_fuzz(self):
        for index in range(STRAIGHT_CASES):
            seed = 0xA1CE0000 + index
            program, initial, checks, words, op_log = build_straight_case(seed)
            context = (f"seed=0x{seed:08X}\n"
                       f"words={[f'0x{word:08X}' for word in words]}\n"
                       f"ops={op_log}")
            state = self.run_twice(program, initial, context)

            self.assertTrue(state["halted"], context)
            self.assertEqual(state["reason"], "pc_outside_code", context)
            self.assertEqual(state["pc"], RETURN_SENTINEL, context)
            self.assert_register_zero(state, context)
            self.assert_memory_bytes(state, context)

            for check in checks:
                value = state["registers"][check["dest"]]
                op = check["op"]
                if op in LOGICAL_IMM_OPS:
                    expected = {
                        "andi": DATA_BASE & check["imm"],
                        "ori": DATA_BASE | check["imm"],
                        "xori": DATA_BASE ^ check["imm"],
                    }[op]
                    self.assertEqual(
                        value, [expected, 0],
                        f"{op} with zero-extended immediate 0x{check['imm']:04X} "
                        f"must not set bits above 63\n{context}")
                elif op in S32_OPS:
                    self.assert_sign_extension(value, "s32", context)
                elif op in S64_OPS:
                    self.assert_sign_extension(value, "s64", context)
                else:  # pragma: no cover - generator bug
                    self.fail(f"unclassified fuzz op {op}\n{context}")

    def test_forward_branch_fuzz(self):
        for index in range(BRANCH_CASES):
            seed = 0xB0000000 + index
            program, initial, plan, slot_count, words = build_branch_case(seed)
            max_steps = slot_count + 4
            context = (f"seed=0x{seed:08X}\n"
                       f"slots={slot_count} branches={plan}\n"
                       f"words={[f'0x{word:08X}' for word in words]}")
            try:
                first = run_oracle(program, max_steps=max_steps,
                                   initial_registers=initial)
                second = run_oracle(program, max_steps=max_steps,
                                    initial_registers=initial)
            except ExecutionError as exc:
                self.fail(f"oracle raised ExecutionError: {exc}\n{context}")
            except Exception as exc:  # noqa: BLE001
                self.fail(f"oracle crashed with {type(exc).__name__}: {exc}\n{context}")
            self.assertEqual(first, second,
                             f"two runs of the same fixture differ\n{context}")

            self.assertTrue(first["halted"], context)
            self.assertEqual(first["reason"], "pc_outside_code", context)
            self.assertEqual(first["pc"], RETURN_SENTINEL, context)
            self.assertLessEqual(first["steps"], max_steps, context)
            self.assertLessEqual(first["steps"], slot_count, context)
            self.assertEqual(len(first["trace"]), first["steps"], context)
            self.assert_register_zero(first, context)

            trace = first["trace"]
            code_end = CODE_BASE + 4 * slot_count
            for address in trace:
                self.assertTrue(CODE_BASE <= address < code_end,
                                f"trace address 0x{address:08X} is outside "
                                f"0x{CODE_BASE:08X}..0x{code_end:08X}\n{context}")
            self.assertEqual(trace, sorted(trace),
                             f"forward-only trace must be increasing\n{context}")
            self.assertEqual(len(trace), len(set(trace)),
                             f"forward-only trace must not repeat PCs\n{context}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
