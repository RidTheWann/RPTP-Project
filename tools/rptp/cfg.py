# SPDX-License-Identifier: GPL-3.0-or-later
"""Control-flow graph, function discovery and indirect-target analysis.

The pass is deliberately conservative.  It decodes only from trusted seeds
(entry point, function symbols, call targets, user seeds and statically
resolved indirect targets), splits blocks at newly discovered branch
targets, and reports code/data ambiguity instead of scanning arbitrary
bytes as code.  No emulator source was used; the algorithm follows the
documented ELF/MIPS ABI and generic static-analysis practice.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from heapq import heappop, heappush
from typing import Iterable

from .elf import ElfImage, ElfError, Symbol
from .isa import (
    Instruction,
    MASK32,
    MASK64,
    decode_instruction,
    HALT_MNEMONICS,
    sign_extend,
)

MAX_BLOCK_INSTRUCTIONS = 4096
RA_REGISTER = 31


@dataclass(frozen=True)
class Diagnostic:
    severity: str
    code: str
    address: int
    message: str


@dataclass
class BasicBlock:
    start: int
    instructions: list[Instruction]
    kind: str
    successors: tuple[int, ...] = ()
    resolved_targets: tuple[int, ...] = ()
    call_target: int | None = None
    problem: str = ""
    delay_slot_pc: int | None = None

    @property
    def end(self) -> int:
        return self.instructions[-1].pc + 4 if self.instructions else self.start

    @property
    def instruction_addresses(self) -> list[int]:
        return [instruction.pc for instruction in self.instructions]

    @property
    def terminator(self) -> Instruction | None:
        return self.instructions[-1] if self.instructions else None

    @property
    def supported(self) -> bool:
        return self.kind != "unsupported" and all(instruction.supported for instruction in self.instructions)


@dataclass(frozen=True)
class CallEdge:
    caller: int
    call_pc: int
    callee: int | None
    kind: str


@dataclass(frozen=True)
class IndirectSite:
    pc: int
    function_entry: int
    mnemonic: str
    register: int
    resolved_target: int | None
    likely_jump_table: bool
    note: str


@dataclass
class Function:
    entry: int
    name: str
    source: str
    blocks: list[int] = field(default_factory=list)
    calls: list[CallEdge] = field(default_factory=list)
    has_return: bool = False
    has_unresolved_indirect: bool = False
    shared_blocks: list[int] = field(default_factory=list)


@dataclass
class Program:
    image: ElfImage
    entry: int
    blocks: dict[int, BasicBlock]
    functions: list[Function]
    call_edges: list[CallEdge]
    indirect_sites: list[IndirectSite]
    diagnostics: list[Diagnostic]
    code_words: dict[int, int]
    roots: dict[int, str]
    stats: dict[str, int]

    def function_at(self, address: int) -> Function | None:
        for function in self.functions:
            if function.entry == address:
                return function
        return None

    def reachable_blocks(self, start: int | None = None) -> set[int]:
        seed = self.entry if start is None else start
        seen: set[int] = set()
        worklist = [seed]
        while worklist:
            pc = worklist.pop()
            if pc in seen or pc not in self.blocks:
                continue
            seen.add(pc)
            worklist.extend(self.blocks[pc].successors)
            worklist.extend(self.blocks[pc].resolved_targets)
        return seen

    def unsupported_blocks(self, block_set: Iterable[int] | None = None) -> list[BasicBlock]:
        selected = self.blocks.values() if block_set is None else (
            self.blocks[pc] for pc in block_set if pc in self.blocks)
        return sorted((block for block in selected if not block.supported), key=lambda block: block.start)


class Discovery:
    """Mutable worklist used while building the global CFG."""

    def __init__(self, image: ElfImage, extra_seeds: Iterable[int] = ()) -> None:
        self.image = image
        self.words: dict[int, int] = image.code_words()
        self.blocks: dict[int, BasicBlock] = {}
        self.address_owner: dict[int, int] = {}
        self.diagnostics: list[Diagnostic] = []
        self.worklist: list[int] = []
        self.queued: set[int] = set()
        self.call_targets: set[int] = set()
        self.resolved_targets: set[int] = set()
        self.indirect_sites: list[IndirectSite] = []
        self.extra_seeds = sorted(set(extra_seeds))

    def diagnostic(self, severity: str, code: str, address: int, message: str) -> None:
        self.diagnostics.append(Diagnostic(severity, code, address, message))

    def queue(self, pc: int) -> None:
        pc &= MASK32
        if pc in self.queued or pc in self.blocks:
            return
        self.queued.add(pc)
        heappush(self.worklist, pc)

    def run(self) -> None:
        # Trusted seeds only.  Do not blindly scan executable bytes.
        self.queue(self.image.entry)
        for symbol in self.image.function_symbols:
            if self.image.is_code_address(symbol.value):
                self.queue(symbol.value)
        for seed in self.extra_seeds:
            if self.image.is_code_address(seed):
                self.queue(seed)
            else:
                self.diagnostic("warning", "seed.outside_code", seed,
                                f"User seed 0x{seed:08X} is outside executable segments.")
        while self.worklist:
            pc = heappop(self.worklist)
            if pc in self.blocks:
                continue
            if pc in self.address_owner and pc not in self.blocks:
                if not self.split_at(pc):
                    continue
                continue
            block = self.decode_block(pc)
            if block is not None:
                self.add_block(block)

    # -- block construction -------------------------------------------------
    def decode_block(self, start: int) -> BasicBlock | None:
        if start not in self.words:
            self.diagnostic("warning", "block.outside_code", start,
                            f"Address 0x{start:08X} is not a file-backed executable instruction.")
            return None
        instructions: list[Instruction] = []
        pc = start
        for _ in range(MAX_BLOCK_INSTRUCTIONS):
            word = self.words.get(pc)
            if word is None:
                self.diagnostic("error", "block.fell_off_segment", pc,
                                f"Fall-through from 0x{pc - 4:08X} leaves the executable segment.")
                return self._make_block(start, instructions, "unsupported",
                                        problem="fall-through leaves executable segment")
            instruction = decode_instruction(word, pc)
            instructions.append(instruction)
            if instruction.is_control:
                return self._finish_control_block(start, instructions, instruction)
            if instruction.is_halt:
                return self._make_block(start, instructions, "halt",
                                        problem=instruction.note or instruction.mnemonic)
            if not instruction.supported:
                self.diagnostic("warning", "block.unsupported_instruction", pc,
                                f"{instruction.text()} ({instruction.verification}) is not supported: "
                                f"{instruction.note or 'no lowering'}")
                return self._make_block(start, instructions, "unsupported",
                                        problem=instruction.note or instruction.mnemonic)
            pc += 4
        self.diagnostic("error", "block.too_large", start,
                        f"Block at 0x{start:08X} exceeded {MAX_BLOCK_INSTRUCTIONS} instructions; "
                        "the seed probably points at data.")
        return self._make_block(start, instructions, "unsupported", problem="block too large")

    def _finish_control_block(self, start: int, instructions: list[Instruction],
                              control: Instruction) -> BasicBlock:
        if control.delay_slot:
            delay_pc = control.pc + 4
            delay_word = self.words.get(delay_pc)
            if delay_word is None:
                self.diagnostic("error", "block.missing_delay_slot", control.pc,
                                f"Control transfer at 0x{control.pc:08X} has no file-backed delay slot.")
                return self._make_block(start, instructions, "unsupported",
                                        problem="missing delay slot")
            delay = decode_instruction(delay_word, delay_pc)
            instructions.append(delay)
            if delay.is_control:
                self.diagnostic("error", "block.control_in_delay_slot", delay_pc,
                                f"Control transfer in the delay slot of 0x{control.pc:08X}; "
                                "R5900 behaviour is unpredictable for this sequence.")
                return self._make_block(start, instructions, "unsupported",
                                        problem="control transfer in delay slot",
                                        delay_slot_pc=delay_pc)
            if not delay.supported:
                self.diagnostic("warning", "block.unsupported_delay_slot", delay_pc,
                                f"Delay-slot instruction {delay.text()} is not supported: "
                                f"{delay.note or 'no lowering'}")
                return self._make_block(start, instructions, "unsupported",
                                        problem="unsupported delay-slot instruction",
                                        delay_slot_pc=delay_pc)
            next_pc = (control.pc + 8) & MASK32
        else:
            delay = None
            next_pc = (control.pc + 4) & MASK32

        if not control.supported:
            self.diagnostic("warning", "block.unsupported_control", control.pc,
                            f"{control.text()} is decoded but not supported: {control.note or 'no lowering'}")
            return self._make_block(start, instructions, "unsupported",
                                    problem=control.note or control.mnemonic,
                                    delay_slot_pc=delay.pc if delay else None)

        mnemonic = control.mnemonic
        successors: list[int] = []
        kind = "unsupported"
        call_target: int | None = None
        if mnemonic in {"beq", "bne", "blez", "bgtz", "bltz", "bgez", "bltzal", "bgezal",
                        "beql", "bnel", "blezl", "bgtzl", "bltzl", "bgezl",
                        "bltzall", "bgezall"}:
            kind = "branch"
            target = control.target or 0
            if target in self.words:
                successors.append(target)
            else:
                self.diagnostic("warning", "branch.target_outside_code", control.pc,
                                f"Branch target 0x{target:08X} is outside file-backed executable code.")
            if next_pc in self.words:
                successors.append(next_pc)
            else:
                self.diagnostic("debug", "branch.fallthrough_outside_code", control.pc,
                                f"Fall-through 0x{next_pc:08X} is outside file-backed executable code.")
        elif mnemonic == "j":
            kind = "jump"
            target = control.target or 0
            if target in self.words:
                successors.append(target)
            else:
                self.diagnostic("warning", "jump.target_outside_code", control.pc,
                                f"Jump target 0x{target:08X} is outside file-backed executable code.")
        elif mnemonic == "jal":
            kind = "call"
            call_target = control.target or 0
            if call_target in self.words:
                successors.append(call_target)
                self.call_targets.add(call_target)
            else:
                self.diagnostic("error", "call.target_outside_code", control.pc,
                                f"JAL target 0x{call_target:08X} is outside file-backed executable code.")
            if next_pc in self.words:
                successors.append(next_pc)
            else:
                self.diagnostic("debug", "call.return_site_outside_code", control.pc,
                                f"JAL return site 0x{next_pc:08X} is outside file-backed executable code.")
        elif mnemonic == "jr":
            if control.rs == RA_REGISTER:
                kind = "return"
            else:
                kind = "indirect"
        elif mnemonic == "jalr":
            if control.rd == RA_REGISTER and control.rs != RA_REGISTER:
                kind = "indirect_call"
                if next_pc in self.words:
                    successors.append(next_pc)
                else:
                    self.diagnostic("debug", "call.return_site_outside_code", control.pc,
                                    f"JALR return site 0x{next_pc:08X} is outside file-backed executable code.")
            else:
                kind = "indirect"
        else:
            self.diagnostic("warning", "block.unknown_control", control.pc,
                            f"Unhandled control mnemonic {mnemonic}.")
            return self._make_block(start, instructions, "unsupported",
                                    problem=f"unhandled control {mnemonic}",
                                    delay_slot_pc=delay.pc if delay else None)

        block = self._make_block(start, instructions, kind,
                                 successors=tuple(dict.fromkeys(successors)),
                                 call_target=call_target,
                                 delay_slot_pc=delay.pc if delay else None)
        if kind in {"indirect", "indirect_call"}:
            resolved, likely_table, note = self.resolve_indirect(block, control)
            if resolved is not None:
                block.resolved_targets = (resolved,)
                self.resolved_targets.add(resolved)
                self.queue(resolved)
                if kind == "indirect_call":
                    self.call_targets.add(resolved)
                self.diagnostic("info", "indirect.resolved", control.pc,
                                f"Resolved {control.text()} target to 0x{resolved:08X}.")
            else:
                self.diagnostic("warning", "indirect.unresolved", control.pc,
                                f"Unresolved {control.text()}: {note}")
            self.indirect_sites.append(IndirectSite(
                pc=control.pc,
                function_entry=0,  # filled after function discovery
                mnemonic=control.mnemonic,
                register=control.rs or 0,
                resolved_target=resolved,
                likely_jump_table=likely_table,
                note=note,
            ))
        return block

    def _make_block(self, start: int, instructions: list[Instruction], kind: str,
                    successors: tuple[int, ...] = (), call_target: int | None = None,
                    problem: str = "", delay_slot_pc: int | None = None) -> BasicBlock:
        return BasicBlock(
            start=start,
            instructions=instructions,
            kind=kind,
            successors=successors,
            call_target=call_target,
            problem=problem,
            delay_slot_pc=delay_slot_pc,
        )

    def add_block(self, block: BasicBlock) -> None:
        if block.start in self.blocks:
            return
        self.blocks[block.start] = block
        for instruction in block.instructions:
            previous = self.address_owner.get(instruction.pc)
            if previous is not None and previous != block.start:
                self.diagnostic("error", "block.overlap", instruction.pc,
                                f"Instruction 0x{instruction.pc:08X} is claimed by blocks "
                                f"0x{previous:08X} and 0x{block.start:08X}.")
            self.address_owner[instruction.pc] = block.start
        for successor in block.successors:
            self.queue(successor)
        for target in block.resolved_targets:
            self.queue(target)

    def split_at(self, pc: int) -> bool:
        owner_start = self.address_owner.get(pc)
        if owner_start is None or pc in self.blocks:
            return False
        owner = self.blocks.get(owner_start)
        if owner is None:
            return False
        try:
            index = owner.instruction_addresses.index(pc)
        except ValueError:
            return False
        if index == 0:
            return False
        head_instructions = owner.instructions[:index]
        tail_instructions = owner.instructions[index:]
        if not head_instructions:
            return False
        last_head = head_instructions[-1]
        if last_head.is_control:
            self.diagnostic("error", "block.split_delay_slot", pc,
                            f"Seed 0x{pc:08X} points into the delay slot of control transfer "
                            f"0x{last_head.pc:08X}; refusing to split.")
            return False
        # Rebuild the head as a plain fall-through block.
        head = BasicBlock(
            start=owner_start,
            instructions=head_instructions,
            kind="fallthrough",
            successors=(pc,),
        )
        tail = BasicBlock(
            start=pc,
            instructions=tail_instructions,
            kind=owner.kind,
            successors=owner.successors,
            resolved_targets=owner.resolved_targets,
            call_target=owner.call_target,
            problem=owner.problem,
            delay_slot_pc=owner.delay_slot_pc,
        )
        del self.blocks[owner_start]
        self.blocks[head.start] = head
        self.blocks[tail.start] = tail
        for instruction in head.instructions:
            self.address_owner[instruction.pc] = head.start
        for instruction in tail.instructions:
            self.address_owner[instruction.pc] = tail.start
        self.diagnostic("info", "block.split", pc,
                        f"Split block 0x{owner_start:08X} at newly discovered target 0x{pc:08X}.")
        for successor in tail.successors:
            self.queue(successor)
        for target in tail.resolved_targets:
            self.queue(target)
        return True

    # -- indirect target resolution ----------------------------------------
    def resolve_indirect(self, block: BasicBlock, control: Instruction) -> tuple[int | None, bool, str]:
        target_reg = control.rs
        if target_reg is None:
            return None, False, "instruction has no source register"
        control_index = block.instructions.index(control)
        value, reason = self._resolve_register(block, control_index - 1, target_reg, 0)
        likely_table = self._looks_like_jump_table(block, control_index)
        if value is None:
            return None, likely_table, reason
        value &= MASK32
        if value in self.words:
            return value, likely_table, f"constant target 0x{value:08X}"
        return None, likely_table, f"computed target 0x{value:08X} is outside executable code"

    def _resolve_register(self, block: BasicBlock, before_index: int, register: int,
                          depth: int) -> tuple[int | None, str]:
        if depth > 8:
            return None, "resolution depth exceeded"
        for index in range(before_index, -1, -1):
            instruction = block.instructions[index]
            if not _writes_register(instruction, register):
                continue
            mnemonic = instruction.mnemonic
            if mnemonic == "lui":
                return ((instruction.imm or 0) << 16) & MASK32, "lui"
            if mnemonic in {"addiu", "daddiu"}:
                if instruction.rs == 0:
                    return (instruction.simm or 0) & MASK32, mnemonic
                base, reason = self._resolve_register(block, index - 1, instruction.rs or 0, depth + 1)
                if base is not None:
                    return (base + (instruction.simm or 0)) & MASK32, mnemonic
                return None, f"base register $r{instruction.rs} of {mnemonic} is not constant"
            if mnemonic in {"ori", "xori", "andi"}:
                base, _ = self._resolve_register(block, index - 1, instruction.rs or 0, depth + 1)
                immediate = instruction.imm or 0
                if base is None:
                    base = 0 if instruction.rs == 0 else None
                if base is not None:
                    if mnemonic == "ori":
                        return (base | immediate) & MASK32, mnemonic
                    if mnemonic == "xori":
                        return (base ^ immediate) & MASK32, mnemonic
                    return (base & immediate) & MASK32, mnemonic
                return None, f"base register of {mnemonic} is not constant"
            if mnemonic in {"addu", "daddu", "or", "xor", "and"}:
                left, _ = self._resolve_register(block, index - 1, instruction.rs or 0, depth + 1)
                right, _ = self._resolve_register(block, index - 1, instruction.rt or 0, depth + 1)
                if left is not None and right is not None:
                    if mnemonic in {"addu", "daddu"}:
                        return (left + right) & MASK32, mnemonic
                    if mnemonic == "or":
                        return (left | right) & MASK32, mnemonic
                    if mnemonic == "xor":
                        return (left ^ right) & MASK32, mnemonic
                    return (left & right) & MASK32, mnemonic
                return None, f"operand of {mnemonic} is not constant"
            if mnemonic in {"sll", "srl", "sra"} and instruction.shamt is not None:
                source, _ = self._resolve_register(block, index - 1, instruction.rt or 0, depth + 1)
                if source is not None:
                    shift = instruction.shamt & 0x1F
                    if mnemonic == "sll":
                        return (source << shift) & MASK32, mnemonic
                    if mnemonic == "srl":
                        return (source >> shift) & MASK32, mnemonic
                    return ((sign_extend(source, 32) >> shift) & MASK32), mnemonic
                return None, f"source of {mnemonic} is not constant"
            if mnemonic in {"lw", "lwu", "ld"}:
                base, _ = self._resolve_register(block, index - 1, instruction.rs or 0, depth + 1)
                if base is None:
                    return None, f"load base of {mnemonic} is not constant"
                address = (base + (instruction.simm or 0)) & MASK32
                try:
                    if mnemonic == "lw":
                        data = self.image.read_bytes(address, 4)
                        return int.from_bytes(data, "little", signed=False) & MASK32, "lw constant"
                    if mnemonic == "ld":
                        data = self.image.read_bytes(address, 8)
                        return int.from_bytes(data, "little", signed=False) & MASK32, "ld constant"
                    data = self.image.read_bytes(address, 4)
                    return int.from_bytes(data, "little", signed=False) & MASK32, "lwu constant"
                except ElfError:
                    return None, f"load address 0x{address:08X} is not backed by initial data"
            return None, f"last write to $r{register} is {mnemonic}"
        return None, f"$r{register} has no constant definition in this block"

    @staticmethod
    def _looks_like_jump_table(block: BasicBlock, control_index: int) -> bool:
        window = block.instructions[max(0, control_index - 12):control_index]
        has_bound = any(instruction.mnemonic in {"sltiu", "slti", "sltu", "slt"}
                        for instruction in window)
        has_indexed_load = any(instruction.mnemonic in {"lw", "lwu", "ld"} for instruction in window)
        return has_bound and has_indexed_load


def _writes_register(instruction: Instruction, register: int) -> bool:
    if instruction.mnemonic in {"beq", "bne", "blez", "bgtz", "bltz", "bgez",
                                "bltzal", "bgezal", "beql", "bnel", "blezl",
                                "bgtzl", "bltzl", "bgezl", "bltzall", "bgezall",
                                "j", "jal", "jr", "jalr",
                                "sw", "sh", "sb", "sd", "sq", "cache", "pref",
                                "syscall", "break", "sync", "nop"}:
        return False
    if instruction.mnemonic in {"lb", "lbu", "lh", "lhu", "lw", "lwu", "ld", "lq",
                                "addiu", "daddiu", "slti", "sltiu", "andi", "ori",
                                "xori", "lui"}:
        return instruction.rt == register
    if instruction.mnemonic in {"mfhi", "mflo", "mfhi1", "mflo1"}:
        return instruction.rd == register
    if instruction.mnemonic in {"mthi", "mtlo", "mthi1", "mtlo1",
                                "div", "divu", "div1", "divu1",
                                "mult1", "multu1"}:
        return False
    if instruction.mnemonic in {"mult", "multu"}:
        return instruction.rd == register
    if instruction.cls == "mmi":
        if instruction.mnemonic in {"madd", "maddu", "madd1", "maddu1"}:
            return instruction.rd == register
        if instruction.writes_hi_lo or instruction.mnemonic in {
                "pmthi", "pmtlo", "pmfhi", "pmflo"}:
            return False
        return instruction.rd == register
    return instruction.rd == register


def _function_name(address: int, symbols: list[Symbol]) -> tuple[str, str]:
    candidates = [symbol for symbol in symbols
                  if symbol.is_function and symbol.value == address and symbol.name]
    if candidates:
        candidates.sort(key=lambda symbol: (symbol.binding != 1, len(symbol.name), symbol.name))
        return candidates[0].name, "symbol"
    return f"sub_{address:08X}", "address"


def discover_program(image: ElfImage, extra_seeds: Iterable[int] = ()) -> Program:
    discovery = Discovery(image, extra_seeds)
    discovery.run()

    # Fill indirect-site function ownership later.
    roots: dict[int, str] = {}
    roots[image.entry] = "entry"
    symbol_functions = [symbol for symbol in image.function_symbols if image.is_code_address(symbol.value)]
    for symbol in symbol_functions:
        roots.setdefault(symbol.value, "symbol")
    for target in sorted(discovery.call_targets):
        if image.is_code_address(target):
            roots.setdefault(target, "jal")
    for seed in discovery.extra_seeds:
        roots.setdefault(seed, "user")
    for target in sorted(discovery.resolved_targets):
        roots.setdefault(target, "resolved_indirect")

    owner: dict[int, int] = {}
    functions: list[Function] = []
    call_edges: set[CallEdge] = set()
    for root in roots:
        if root not in discovery.blocks:
            discovery.diagnostic("warning", "function.root_without_block", root,
                                 f"Function root 0x{root:08X} has no decodable block.")
            continue
        name, source = _function_name(root, image.symbols)
        function = Function(entry=root, name=name, source=roots[root] if roots[root] != "symbol" else source)
        stack = [root]
        seen: set[int] = set()
        while stack:
            pc = stack.pop()
            if pc in seen:
                continue
            block = discovery.blocks.get(pc)
            if block is None:
                continue
            if pc in owner and owner[pc] != root:
                function.shared_blocks.append(pc)
                discovery.diagnostic("warning", "function.shared_block", pc,
                                     f"Block 0x{pc:08X} is shared by functions 0x{owner[pc]:08X} "
                                     f"and 0x{root:08X}; traversal stops here.")
                continue
            owner[pc] = root
            seen.add(pc)
            function.blocks.append(pc)
            if block.kind == "call":
                target = block.call_target
                if target is not None:
                    edge = CallEdge(root, block.start, target, "jal")
                    if edge not in call_edges:
                        call_edges.add(edge)
                        function.calls.append(edge)
                continue
            if block.kind == "indirect_call":
                function.has_unresolved_indirect = True
                if block.resolved_targets:
                    for target in block.resolved_targets:
                        edge = CallEdge(root, block.start, target, "jalr_resolved")
                        if edge not in call_edges:
                            call_edges.add(edge)
                            function.calls.append(edge)
                continue
            if block.kind == "return":
                function.has_return = True
                continue
            if block.kind in {"indirect", "halt", "unsupported"}:
                if block.kind == "indirect":
                    function.has_unresolved_indirect = True
                continue
            if block.kind == "jump":
                for successor in block.successors:
                    if successor in roots and successor != root:
                        edge = CallEdge(root, block.start, successor, "tail")
                        if edge not in call_edges:
                            call_edges.add(edge)
                            function.calls.append(edge)
                        continue
                    stack.append(successor)
                continue
            # branch, fallthrough
            for successor in block.successors:
                stack.append(successor)
        function.blocks.sort()
        function.calls.sort(key=lambda edge: (edge.call_pc, edge.callee or 0, edge.kind))
        functions.append(function)

    functions.sort(key=lambda function: function.entry)
    block_function: dict[int, int] = {}
    for function in functions:
        for pc in function.blocks:
            block_function.setdefault(pc, function.entry)
    indirect_sites = [
        IndirectSite(
            pc=site.pc,
            function_entry=block_function.get(discovery.address_owner.get(site.pc, 0), 0),
            mnemonic=site.mnemonic,
            register=site.register,
            resolved_target=site.resolved_target,
            likely_jump_table=site.likely_jump_table,
            note=site.note,
        )
        for site in discovery.indirect_sites
    ]
    indirect_sites.sort(key=lambda site: site.pc)

    diagnostics = sorted(discovery.diagnostics,
                         key=lambda item: (item.address, item.code, item.message))
    code_words = discovery.words
    discovered_addresses = set(discovery.address_owner)
    executable_bytes = sum(segment.filesz for segment in image.executable_segments)
    unsupported_count = sum(1 for address in discovered_addresses
                            if (address in code_words and
                                not decode_instruction(code_words[address], address).supported))
    stats = {
        "executable_bytes": executable_bytes,
        "decoded_instruction_bytes": len(discovered_addresses) * 4,
        "decoded_instructions": len(discovered_addresses),
        "blocks": len(discovery.blocks),
        "functions": len(functions),
        "call_edges": len(call_edges),
        "indirect_sites": len(indirect_sites),
        "unresolved_indirect": sum(1 for site in indirect_sites if site.resolved_target is None),
        "unsupported_instructions": unsupported_count,
        "diagnostics": len(diagnostics),
    }
    return Program(
        image=image,
        entry=image.entry,
        blocks=discovery.blocks,
        functions=functions,
        call_edges=sorted(call_edges, key=lambda edge: (edge.caller, edge.call_pc, edge.callee or 0, edge.kind)),
        indirect_sites=indirect_sites,
        diagnostics=diagnostics,
        code_words=code_words,
        roots=roots,
        stats=stats,
    )
