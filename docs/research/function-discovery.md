# Function discovery for PS2 EE executables

- **Status:** research/design note for the Gate 3 analyzer. No production code changes.
- **Input:** one ELF32/EM_MIPS boot executable produced by a separate, gated extraction step. The analyzer is read-only and never writes to the input.
- **Policy:** ADR-0003. This note is derived only from the neutral references at the end; no sealed emulator/recompiler source was accessed.

## 1. Platform facts the analyzer must encode

| Fact | Value / consequence |
|---|---|
| Container | ELF32, little-endian, `ET_EXEC` (2), `EM_MIPS` (8), `e_version` 1, `e_ehsize` 52. Static image, no dynamic loader. |
| Sections/symbols | Retail boot ELFs are commonly stripped (`e_shoff = 0`, no `.symtab`). When present, `STT_FUNC` symbols are ground truth for validation, not a requirement. |
| Load segments | One or more `PT_LOAD`. `p_vaddr` is the load address; `p_paddr` is normally equal but record a mismatch. `p_filesz <= p_memsz`; the tail is zero-filled (`.bss`). `p_align` is usually `0x1000`; require `p_offset % p_align == p_vaddr % p_align` when `p_align > 1`. If no segment sets `PF_X`, warn and treat all `PT_LOAD` as candidate code (some PS2 linkers omit flags). |
| Entry | Inside an executable `PT_LOAD`, 4-byte aligned. Recorded example: Downhill Domination USA entry `0x0010A008`, one `PT_LOAD` (`docs/games/downhill-domination/STATUS.md`). |
| EE RAM | 32 MiB physical at `0x00000000`; first 1 MiB is kernel-reserved, so retail executables link at/above `0x00100000` [1]. |
| Aliases | The same bytes appear as `0x00xxxxxx` (KUSEG), `0x80xxxxxx` (KSEG0 cached), `0xA0xxxxxx` (KSEG1 uncached), `0x20xxxxxx` (uncached) and `0x30100000+` (uncached accelerated, physical `0x00100000`) [1]. All comparisons must use one canonical address. |
| Vectors | Reset `0xBFC00000`; TLB refill `0x80000000`; performance `0x80000080`; debug `0x80000100`; general/syscall `0x80000180`; interrupt `0x80000200` [1]. For a retail ELF these lie outside `PT_LOAD`; they are not seeds. Runtime handlers are registered through function pointers in data. |
| CPU | R5900 is MIPS III plus MMI, COP1 and COP2. Fixed 4-byte instructions, architectural delay slots, and branch-likely forms (`BEQL`, `BNEL`, `BLEZL`, `BGTZL`, REGIMM likely forms). A not-taken likely branch nullifies its delay slot. COP1 branches (`BC1F`/`BC1T`) are conditional branches; COP2 has no EE program-counter branches. |
| ABI | O32: `$ra=31`, `$sp=29`, `$gp=28`, `$t9=9` for PIC calls, `$s0-$s7` callee-saved, 16-byte caller argument home area; stack frames keep `$sp` 8-byte aligned (commonly 16) [2]. |

Canonicalization (physical/ELF-image address space):

```python
RAM_WINDOWS = [  # (virtual_lo, virtual_hi, physical_base)
    (0x00000000, 0x02000000, 0x00000000),  # KUSEG identity
    (0x20000000, 0x22000000, 0x00000000),  # uncached
    (0x30100000, 0x32000000, 0x00100000),  # accelerated uncached
    (0x80000000, 0x82000000, 0x00000000),  # KSEG0 cached
    (0xA0000000, 0xA2000000, 0x00000000),  # KSEG1 uncached
]
def canon(addr):
    for lo, hi, base in RAM_WINDOWS:
        if lo <= addr < hi:
            return base + (addr - lo)
    return None  # I/O, scratchpad, BIOS: outside the ELF image
```

`e_flags` is advisory: recognize architecture nibble `0x2` (`EF_MIPS_ARCH_3 = 0x20000000`), `EF_MIPS_ABI_O32` (`0x1000`) and `E_MIPS_MACH_5900` (`0x00920000`) when present, but never reject solely on flags [3]. Retail `p_vaddr` values use the KUSEG identity window (for example `0x00100000`); code may reference the same bytes through KSEG0 (`0x80100000`). Index everything by canonical physical address and keep the original ELF address for reporting.

## 2. Analysis model

```python
@dataclass
class Insn:      pc:int; word:int; cls:str; rs:int; rt:int; rd:int; target:int|None
@dataclass
class Edge:      site:int; src_func:int; dst:int|None; kind:str; resolved:bool; via:str
@dataclass
class Block:     start:int; end:int; insns:list[int]; succ:list[Edge]; terminator:str
@dataclass
class Function:  start:int; end:int; source:str; confidence:str; blocks:dict[int,Block]
                 insns:dict[int,Insn]; flags:set[str]; callers:list[Edge]; callees:list[Edge]
@dataclass
class Indirect:  site:int; func_start:int; op:str; reg:int; state:str; candidates:list[int]
                 reason:str; trace:list[int]          # last <=8 defining instructions
@dataclass
class Diagnostic: code:str; severity:str; address:int|None; func_start:int|None; detail:str
```

`Insn.cls` is only the control-flow classification needed for discovery: `alu`, `load`, `store`, `cond`, `jump`, `call`, `indirect`, `return`, `trap`, `opaque`. Instruction length is always 4, so unknown MMI/COP encodings are `opaque` and do not stop discovery; the later code generator rejects them explicitly.

## 3. Discovery pipeline

### 3.1 Seeds (deterministic, priority-ordered)

**Tier A - trusted.** (1) `e_entry`; (2) `STT_FUNC` symbols and `SHF_EXECINSTR` section ranges as candidate bounds, if sections exist; (3) `JAL`/resolved `JALR` targets found while traversing code (these are code-proven calls); (4) aligned words in load segments that canonicalize into an executable segment **and** are corroborated: target is not the interior of a known function, and either a call site references it or its prologue score is >= 4.

**Tier B - speculative, off by default (`--aggressive`).** (5) a blind linear scan for `JAL` encodings whose target is aligned, inside an executable segment and outside known functions; (6) a prologue scan on the 4-byte grid; (7) vector-table entries only for kernel/BIOS images that actually map `0x80000000`-`0x80000200` or `0xBFC00000`-`0xBFC00400`. Tier B functions are marked `confidence=speculative` and are never codegen-eligible in the MVP.

Prologue masks (word is little-endian-decoded; `N` is any 16-bit frame size):

```text
word >> 16 == 0x27BD              addiu  $sp,$sp,-N
word >> 16 == 0x67BD              daddiu $sp,$sp,-N
word & 0xFFFF0000 == 0xFFBF0000   sd     $ra,off($sp)
word & 0xFFFF0000 == 0xAFBF0000   sw     $ra,off($sp)
word & 0xFFFF0000 == 0x7BBF0000   sq     $ra,off($sp)
word & 0xFFFF0000 == 0x3C1C0000   lui    $gp,hi
word & 0xFFFF0000 == 0x279C0000   addiu  $gp,$gp,lo
0x03E00008                        jr     $ra
```

Score: stack adjustment +2, `ra` save within the next six instructions +2, `$gp` setup +2, a reachable `jr $ra` within 4096 bytes +1; require a terminator and score >= 4. A lone `jr $ra` leaf is deliberately too weak to seed.

### 3.2 Recursive traversal

```python
def traverse(fn, start):
    work = [start]
    while work:
        pc = min(work); work.remove(pc)          # deterministic order
        while True:
            if pc in fn.insns: break             # loop back-edge
            if not in_exec(pc) or pc & 3:
                diag("BRANCH_TARGET_OUTSIDE_IMAGE" if not in_exec(pc) else "BRANCH_TARGET_UNALIGNED"); break
            owner = claim(pc, fn)
            if owner == CONFLICT: diag("OVERLAPPING_FUNCTIONS"); break
            insn = decode(pc); fn.insns[pc] = insn
            if insn.is_control:
                ds = pc + 4
                if not in_exec(ds) or ds & 3: diag("DELAY_SLOT_OUTSIDE_IMAGE"); break
                if claim(ds, fn) == CONFLICT: diag("OVERLAPPING_FUNCTIONS"); break
                fn.insns[ds] = decode(ds)
                if fn.insns[ds].is_control: diag("DELAY_SLOT_CONTROL_TRANSFER"); break
            for target, kind in successors(insn, pc):
                if kind in ("call", "tail"): enqueue_function(target, kind, insn, fn)
                elif kind == "next": work.append(target)
            if insn.terminates: break
            pc = pc + (8 if insn.is_control else 4)   # skip the delay slot
    fn.end = max(fn.insns) + 4
```

`successors` rules:

- Conditional branch (`BEQ`..`BGTZ`, REGIMM, COP1 branch, likely variants): `(target, next)` and `(pc+8, next)`. Condition values are irrelevant to reachability; both paths are explored and the edge records `likely=true` so later stages can nullify the delay slot on the not-taken path.
- `J`: resolved by the boundary rule in 3.3 (intra-function branch or tail call). `JAL`: `(target, call)` and a call edge; the link value `pc+8` needs no tracking.
- `JR $ra`: `(none, return)` and terminate. `JR r`: resolve `r` (3.4); constant target becomes a `jump`, otherwise `indirect` and terminate.
- `JALR rd, rs`: `rd==31` is an indirect call, `rd==0` an indirect jump; resolve the register.
- `SYSCALL`: resumes at `pc+4` after the handler returns and has no delay slot (classify as non-control, normal fallthrough). `BREAK`/`ERET`: terminate. `NOP`, `opaque`, loads/stores/ALU: fall through.

Branch/jump target formulas: `J/JAL = ((pc+4) & 0xF0000000) | (imm26 << 2)`; conditional `= pc + 4 + (simm16 << 2)`. Canonicalize both before lookup.

### 3.3 Boundaries, tail calls, thunks, shared epilogues

- A function ends at `max(owned pc) + 4`; holes inside `[start, end)` are interior data, not instructions.
- `J` resolution order: (1) target already owned by this function, or backward and inside it: intra-function branch; (2) target equals a discovered function start, or has a strong prologue and is not reachable by local fallthrough: **tail call** (add a `tail` edge, seed the target, terminate the block); (3) otherwise (forward target with no prologue): traverse it inside the current function and emit `AMBIGUOUS_FORWARD_JUMP`. If that address is later claimed by another function, the caller becomes ambiguous; never silently merge or split.
- A conditional branch to another function's start is `CROSS_FUNCTION_BRANCH` (fatal/ambiguous); it cannot be a tail call because execution may continue locally.
- A thunk is a body of at most four instructions ending in `J target` or `JR $t9` after `lui/addiu`; record `thunk_of=target`, keep it as a function and do not inline it in the MVP.
- A block reached by `J` from two or more distinct functions is a **shared epilogue** (`SHARED_BLOCK`). Emit it once, assign it to no function, and terminate each caller with a tail edge. Duplicating it into both functions would create overlapping code.
- The one-owner-per-instruction invariant is mandatory. Same start: merge. Different starts, one containing the other: both functions become `ambiguous` and codegen-ineligible. Never silently pick a winner.

### 3.4 Indirect jumps and register resolution

For each `JR`/`JALR`, run a bounded backward slice (<= 16 instructions, single-predecessor blocks; stop at a merge, call, or unknown definition). Lattice: `UNKNOWN`, `CONST(v)`, `SYM(base, off)`, `TABLE(base, count, stride, kind)`, `TOP` (conflicting merge).

| Pattern ending at the transfer | Classification |
|---|---|
| `jr $ra` | return (regardless of how `$ra` was restored) |
| `lui r,hi` + `addiu/ori r,r,lo` (+ optional `addu r,r,$zero`); `jr r` | direct jump to constant |
| same, `jalr r` (`rd=31`) | direct call to constant; not indirect |
| `lw r,off(base)` with `base=CONST`, address mapped | load image word; if it canonicalizes into exec, direct jump/call; else `INDIRECT_TARGET_NOT_CODE` |
| `lw r,off($gp)` with `$gp=CONST` | resolve image word as above; otherwise `GP_UNKNOWN` |
| `sll idx,2; addu t,base,idx; lw t,0(t); jr t` with a dominating `sltiu $at,idx,N` | jump table: read `N` words, stride 4 |
| same but entries are `base + offset` after an extra `addu` | relative jump table |
| table with alternating target/gp words | stride 8 table |
| `jr $t9` in a thunk | tail jump to the thunk target |
| anything else (e.g. `lw r,0(a0); jr r`, two unknowns added) | `UNRESOLVED_INDIRECT_*` with the last-definition trace |

Jump-table acceptance is strict: the bounds guard must dominate the load, the table must lie wholly inside one load segment, every one of the `N` entries must be 4-byte aligned and canonicalize into an executable segment, and a table entry may equal the default target. If any entry fails, emit `JUMP_TABLE_INVALID_ENTRY` (fatal) and create no edges from the table; do not clip the table to the valid prefix. If the bound is unknown, emit `JUMP_TABLE_BOUNDS_UNKNOWN` and leave the transfer unresolved.

`JALR` semantics come from the encoding: `rd` is the link register, so `jalr $t9` assembles as `rd=31`; `jalr $s0` with `rd=0` is a jump. Do not infer from register names alone.

### 3.5 Code-versus-data policy

1. Only bytes reachable by a control-flow path from a Tier-A seed, or a corroborated Tier-B seed, are code.
2. All code addresses are 4-byte aligned. Unaligned targets are fatal, not rounded.
3. Unreachable words inside an executable segment, including literal pools and inline data between functions, are `DATA`/`INTERIOR_DATA`; they are never decoded as code merely because they decode.
4. Non-executable segments are data. GPU/DMA/VIF/GIF packets and VU microcode images are data; VU microcode executes on a different processor and is out of scope.
5. Overlap is ambiguity. A function containing another function's start, or two functions owning the same instruction, is excluded from codegen with a diagnostic.
6. Any branch into bytes already classified as data is fatal for the containing function (`BRANCH_INTO_DATA`).
7. A jump table is data whose entries are only read under the proof in 3.4; it is never discovered by scanning.
8. Analysis completion and codegen eligibility are separate. The report may classify the whole image while marking specific functions ineligible.

## 4. Validation and deterministic report

If `STT_FUNC` symbols exist, compute: exact start matches, recalled symbols (`discovered / symbols`), extra functions, size mismatches (`fn.end` vs `st_value + st_size`, allowing alignment padding up to the next symbol), and call-edge precision/recall against symbol-resolved `JAL` targets. On stripped binaries, use self-consistency: every function has a terminator on every path, no instruction has two owners, every edge endpoint is classified, and coverage partitions all executable bytes.

Report (sorted by numeric address at every level, no timestamps, input SHA-256 included):

```json
{
  "schema": "rptp.function-discovery/1",
  "status": "COMPLETE | COMPLETE_WITH_WARNINGS | INCOMPLETE",
  "input": {"sha256": "...", "entry": "0x0010A008", "machine": 8, "type": 2},
  "segments": [{"vaddr": "0x00100000", "filesz": 1691684, "memsz": 1691684, "flags": "R-X"}],
  "functions": [{"start": "0x00100000", "end": "0x00100120", "name": null,
                 "source": ["entry"], "confidence": "trusted", "codegen_eligible": true,
                 "callees": [{"site": "0x00100040", "dst": "0x00100200", "kind": "call"}]}],
  "indirect": [{"site": "0x00100110", "function": "0x00100000", "op": "jr", "reg": 8,
                "state": "UNRESOLVED", "reason": "INDEXED_LOAD_UNBOUNDED", "trace": ["0x0010010C"]}],
  "diagnostics": [{"code": "UNRESOLVED_INDIRECT_JUMP", "severity": "fatal",
                   "address": "0x00100110", "detail": "..."}],
  "metrics": {"exec_bytes": 0, "code_bytes": 0, "data_bytes": 0, "unknown_bytes": 0,
              "functions": 0, "blocks": 0, "call_edges": 0, "tail_edges": 0,
              "unresolved_indirect": 0, "symbol_recall": null}
}
```

Exit codes mirror `rptp_inspect.py`: `0` for complete/with-warnings, `2` for analysis errors or `INCOMPLETE`. A fatal diagnostic means "this function/image is not compilable", not "the analyzer crashed"; the report is still written.

## 5. Error taxonomy

| Code | Severity | Meaning |
|---|---|---|
| `ELF_NOT_EXEC`, `ELF_NOT_MIPS`, `ELF_BAD_CLASS`, `ELF_BAD_ENDIAN` | fatal | Not an analyzable PS2 EE executable. |
| `ELF_SEGMENT_BOUNDS`, `ELF_SEGMENT_OVERLAP`, `ELF_BAD_ALIGNMENT` | fatal | Loader cannot build an unambiguous address space. |
| `ENTRY_OUTSIDE_EXEC`, `ENTRY_UNALIGNED` | fatal | Entry cannot seed traversal. |
| `PADDR_MISMATCH`, `SEGMENT_BELOW_USER_BASE` | warning | Suspicious but analyzable. |
| `BRANCH_TARGET_OUTSIDE_IMAGE`, `BRANCH_TARGET_UNALIGNED`, `BRANCH_INTO_DATA` | fatal | Control flow leaves the proven image. |
| `DELAY_SLOT_OUTSIDE_IMAGE`, `DELAY_SLOT_CONTROL_TRANSFER` | fatal | Invalid/unmodeled delay-slot control flow. |
| `OVERLAPPING_FUNCTIONS`, `CROSS_FUNCTION_BRANCH` | fatal/ambiguous | Ownership conflict; both functions excluded. |
| `AMBIGUOUS_FORWARD_JUMP` | warning | A forward `J` was treated as intra-function without proof. |
| `FUNCTION_FALLTHROUGH`, `FUNCTION_LIMIT`, `INSTRUCTION_LIMIT` | fatal | No terminator, or resource bound exceeded. |
| `INTERIOR_DATA`, `SHARED_BLOCK`, `DATA_SEED_REJECTED` | info | Classification facts, not failures. |
| `UNKNOWN_INSTRUCTION` | warning (fatal for codegen) | Opaque 4-byte instruction. |
| `UNRESOLVED_INDIRECT_JUMP`, `UNRESOLVED_INDIRECT_CALL` | fatal | Register value not provable. |
| `UNRESOLVED_JUMP_TABLE`, `JUMP_TABLE_INVALID_ENTRY`, `JUMP_TABLE_BOUNDS_UNKNOWN` | fatal | Table not safely consumable. |
| `GP_UNKNOWN`, `INDIRECT_TARGET_NOT_CODE` | warning/fatal | Global-pointer or pointer target unproven. |
| `SYMBOL_FUNCTION_NOT_DISCOVERED`, `SYMBOL_RANGE_MISMATCH` | warning | Validation discrepancy. |
| `SELF_MODIFYING_CODE` | warning now, fatal for codegen | A store targets an executable range. |

## 6. MVP versus later

**MVP:** ELF32 LE `EM_MIPS` `ET_EXEC`; all `PT_LOAD`; canonical address space; seeds from entry, `STT_FUNC`, traversal-resolved `JAL`, and corroborated pointers; recursive traversal with delay slots, branch-likely, direct branches, `J`/`JAL`, `JR $ra`, tail calls, thunks, shared epilogues; constant/backward-slice resolution for `lui/addiu/addu/ori/move/lw` plus the bounded jump-table pattern; symbol validation; deterministic JSON; explicit `INCOMPLETE`. No code generation.

**Later:** forward dataflow across blocks and calls; `$gp` small-data model; compare-chain switches; pointer/type inference in `.rodata`; function fingerprints; overlay manifests (runtime-loaded EE modules); IOP/IRX analysis (different CPU, 2 MiB at `0x1C000000`); self-modifying-code handling; VU microcode separation; incremental caching.

## 7. Synthetic testing strategy

Use the existing generator style (`tools/rptp_gate0_spike.py`) to build small ELFs programmatically; register every fixture in `tests/fixtures/MANIFEST` with SHA-256. Author expected JSON by hand, never by running the analyzer.

| Fixture | Exercises | Expected result |
|---|---|---|
| `clean-three-fn` | entry, `JAL`/`JR`, delay slots, leaf function | 3 functions, exact starts/ends, 2 call edges. |
| `jump-table-4` | `sltiu` guard + `lw` + `jr`, table in `.rodata` | 4 resolved targets, no unresolved entry. |
| `interleaved-data` | literal pool between functions, not branched to | bytes classified `INTERIOR_DATA`; no function starts there. |
| `prologue-lookalike` | data word matching `addiu sp` + `sd ra` | not discovered by default; Tier B marks it speculative only. |
| `unresolved-indirect` | `lw $t0,0($a0); jr $t0` | one `UNRESOLVED_INDIRECT_JUMP`; function ineligible; status `INCOMPLETE`. |
| `thunk-plt` | `lui/addiu $t9; jalr $t9` and `j target` | direct call edge plus a thunk record. |
| `overlap` | `JAL` into the middle of a known function | `OVERLAPPING_FUNCTIONS`; no silent merge. |
| `shared-epilogue` | two functions `j` to one restore/`jr $ra` block | one shared block, two tail edges. |
| `branch-likely` | taken and not-taken likely branches | delay slot reached only on the taken path. |
| `symtab-vs-stripped` | same code with and without `.symtab` | identical functions; symbol metrics 100%/100% or explained deltas. |
| `malformed/*` | unaligned entry, `JAL` outside segment, segment overlap, truncated file | exact error codes, no crash, report still deterministic. |

Properties: two runs are byte-identical; the input file hash is unchanged; code + data + unknown equals total executable bytes; every function has a terminator; no address has two owners except declared shared blocks. Add a 250-case seeded byte-flip smoke test asserting "no crash, no hang, valid report or exact error". All fixtures are synthetic; no game bytes enter CI.

## 8. Risks and limits

| Risk | Effect | Mitigation |
|---|---|---|
| Data misclassified as code | Wrong function, miscompile | Proof-chain classification; speculative seeds excluded from codegen; overlap fatal; fail closed. |
| Missed functions (computed pointers, hand-written asm without prologue) | Runtime miss | Coverage metrics; runtime trap on executing unclassified addresses; aggressive pass later. |
| Unresolved indirect jumps/tables | Non-compilable function | Explicit diagnostics; never guess; report `INCOMPLETE`. |
| Self-modifying code / runtime patching | Static analysis unsound | Detect stores into executable ranges; mark and exclude. |
| Overlays / runtime-loaded EE modules | Boot ELF is only part of the program | Analyze the disc inventory and loaders in a later phase; report incompleteness. |
| Compressed or encrypted payloads | No discoverable game code | Detect non-ELF/high-entropy input; reject explicitly. |
| IOP modules (`IRX`) | Wrong CPU/memory map | Detect and refuse; separate analyzer with R3000 assumptions. |
| Address aliasing | Duplicate functions | Canonicalize every target and pointer before comparison. |
| Symbol absence | No ground truth | Self-consistency checks and golden synthetic fixtures. |

## References

1. PS2TEK, *PS2 internals* (EE memory map, reset/exception vectors): https://psi-rockin.github.io/ps2tek/
2. System V Application Binary Interface, *MIPS Processor Supplement* (O32 conventions): https://refspecs.linuxfoundation.org/elf/mipsabi.pdf
3. Generic MIPS ELF constants (`EF_MIPS_ARCH`, `EF_MIPS_ABI_O32`, `E_MIPS_MACH_5900`): https://github.com/reswitched/newlib/blob/master/include/elf/mips.h
4. ELF gABI, *ELF Header* and program-header definitions: https://refspecs.linuxfoundation.org/elf/gabi4+/ch4.eheader.html
5. Ghidra discussion, recursive-descent disassembly: https://github.com/NationalSecurityAgency/ghidra/discussions/2994
6. Ghidra advanced course, *Improving Disassembly and Decompilation* (function-start and thunk heuristics): https://ghidra.re/ghidra_docs/GhidraClass/Advanced/improvingDisassemblyAndDecompilation.pdf
7. C. Pang et al., *All You Ever Wanted to Know About x86/x64 Binary Disassembly* (2021): https://oaklandsok.github.io/papers/pang2021.pdf
8. RPTP, Downhill Domination (USA) inspection record: `docs/games/downhill-domination/STATUS.md`
