# Synthetic generated-C++ performance baseline

- **Date:** 2026-10-30 (second pass; the untracked draft was dated 2026-10-30).
- **Status:** Research note. Synthetic microbenchmarks only. Not a Gate disposition, not a compatibility statement, not a boot claim and not a product-runtime measurement.
- **Scope:** the named differential fixtures, the C++ emitted by `tools/rptp/codegen.py` for them, a compile-time/source-size/scaling study on synthetic programs, and a source reading of the generated harness. No retail code, ISO, BIOS, extracted asset or game-derived material was used.
- **Review status:** this pass re-ran a representative subset of the draft, corrected its factual errors and re-labelled every number. It is not an independent review and has not been certified by the owner.
- **Related:** [RUNTIME.md](../RUNTIME.md), [IR_CFG.md](../IR_CFG.md), [INSTRUCTION_CATALOG.md](../INSTRUCTION_CATALOG.md), `docs/RISKS.md` R-010, `tools/rptp/codegen.py`, `tools/rptp/native.py`, `tools/rptp/oracle.py`, `tools/rptp/fixtures.py`.

Evidence labels follow `AGENTS.md` §4. In this note they mean:

- **Terverifikasi** — re-run or re-measured in the second pass and reported below with its value and repetition count.
- **Belum diverifikasi** — a draft value that was **not** re-run in this pass, or a claim that needs a measurement that does not exist yet. It is retained only as a comparison point.
- **Dugaan** — inference from the evidence above it, not a measured fact.

Every timing is a single-machine, single-session wall-clock observation. Frequencies, cache state, background load and on-access scanning are uncontrolled. Values in the same table were not always taken under the same load, so differences below roughly 1 ms, and differences between the two sessions, are not resolvable by this method.

There is no bootable game and no product runtime. The only executable evidence is synthetic fixtures and the C++ that `tools/rptp/codegen.py` emits for them. Nothing in this note describes how a game would perform.

## 1. What this pass actually did

The draft was treated as a set of claims to check, not as truth. The second pass:

1. re-ran the named-fixture source-size, compile-time, launch-time, stdout-size and step-count measurements;
2. re-ran the Python-stage and oracle timings for both named fixtures;
3. re-ran four points of the single-block compile-time series and three split-block points;
4. re-ran the trace/no-trace slope experiment with a corrected loop counter;
5. re-ran the 32 MiB startup-floor experiment in three independent series;
6. inspected the generated C++ and `tools/rptp/codegen.py` for the qualitative claims;
7. ran the instruction-lowering, native-differential, documentation and artifact-guard checks listed in §8.

It did **not** re-run the draft's 12-million-step trace-free point, the draft's memory-isolation experiment, or the draft's cold-launch series. Those rows are marked **Belum diverifikasi** where they appear.

No compiler flag, warning level, sanitizer, build configuration or production source file was changed. No optimization was implemented.

## 2. Environment

| Item | Value | Label |
|---|---|---|
| OS | Windows 11, build 10.0.26300 (x64) | Terverifikasi |
| CPU | AMD Ryzen 5 5600G with Radeon Graphics, 12 logical processors | Terverifikasi |
| RAM | 17,043,472,384 bytes reported (~15.9 GiB; 16 GiB nominal) | Terverifikasi |
| Python | CPython 3.13.16, 64-bit, MSC v.1944 build | Terverifikasi |
| Compiler | MSVC 14.51.36231, x64 host/target, found by `tools/rptp/native.py:find_msvc()` | Terverifikasi |
| Compile flags | `/nologo /std:c++20 /EHsc /W4 /WX /permissive- /utf-8 /O2` (`native.CL_FLAGS`); no `/GL`, `/LTCG` or link flags | Terverifikasi |
| CRT linkage | Command-line default; `dumpbin /dependents` listed only `KERNEL32.dll`, with no MSVC runtime DLL, so this build statically links the CRT (`/MT`). The exact default switch was not read from vendor documentation in this pass. | Terverifikasi |
| Harness limits | `COMPILE_TIMEOUT_SECONDS = 180`, `RUN_TIMEOUT_SECONDS = 30`, default step budget `100_000` | Terverifikasi |

The draft said the link mode was the "MSVC default (dynamic CRT)". That is wrong for this command line: the measured dependency list contains only `KERNEL32.dll`. The correction matters because it explains part of the executable size and the fixed start-up floor.

The draft's environment values match this machine. That does not prove the draft ran in this identical session: the draft's absolute timings differ from this pass in several places (§7).

## 3. Method

### 3.1 Pipeline measured

The measurement driver called the same public functions the differential tests use:

1. `elf.parse_elf_bytes(data, path=...)`
2. `cfg.discover_program(image)`
3. `ir.lower_program(program)`
4. `codegen.generate(program, result)`
5. `native.build_native(generated, workdir)` — writes `rptp_native.cpp` and `rptp_image.bin`, then runs `vcvars64.bat` and `cl` through a batch file
6. `native.run_native(exe, max_steps, blob)`-equivalent invocation: `rptp_native.exe <max_steps> <blob>`

Oracle timing used `oracle.run_oracle(program, max_steps=100_000)`. The driver itself lived under the git-ignored `build/` tree and is not part of the repository. Section 8 gives the exact public calls needed to reproduce the numbers; no host path is part of this note.

### 3.2 Fixtures

| Fixture | Origin | ELF bytes | Blocks | Guest instructions | Executed steps |
|---|---|---|---|---|---|
| `differential` | `fixtures.differential_fixture()` | 8,224 | 7 | 56 | 54 |
| `broad` | `fixtures.broad_fixture()` | 8,224 | 19 | 170 | 166 |
| `halt` | measurement-only: `JR $ra; NOP` | 4,104 | 2 | 2 | 2 |
| `loop-N` | measurement-only counted loop: `LUI`, `ORI`, `ADDIU`, `BNE`, `NOP`, `JR $ra`, `NOP` | 4,124 | 3 | 7 | 3 × N + 4 |
| `straight-N` | measurement-only `ADDIU` chain plus `JR $ra; NOP` | 4,616–12,296 | 1 | N + 2 | N + 2 |
| `split-N/M` | measurement-only: N data instructions in M block functions | 8,448–14,336 | 32–256 | 1,088–2,560 | not executed |

All measurement-only programs were built at run time with `fixtures.Assembler` and `fixtures.build_elf`. They were never written to `tests/fixtures/`, never registered in the manifest and are not part of the test suite. They are synthetic RPTP programs, not game code.

### 3.3 Repetitions

- Compile time: three independent builds for the two named fixtures; two for the 130- and 514-instruction points; **one** for the 1,026-, 2,050- and split-block points. Every build used a fresh directory and a cold `cl` process. Total `cl` wall includes the `vcvars64.bat` bootstrap, measured separately at 1.378 s median of three.
- Launch time: the first launch of a freshly written executable was recorded and then discarded; warm medians come from 4, 6, 8 or 10 launches, as stated per table.
- Oracle and Python-stage costs: three in-process repetitions, medians reported.
- All wall times use `time.perf_counter()` around the process launch from Python, so they include process creation and the parent-side wait.

### 3.4 Measurement caveats

1. **Cold first launch is not stable.** Cold launches in this pass ranged from 0.46 s to 1.81 s for the same kind of freshly written executable. The draft's 0.57–0.67 s range was not reproduced. A plausible cause is on-access scanning of a new binary (**Dugaan**); the cause was not established. Any benchmark that launches a just-built binary once measures the scanner as much as the program.
2. **The fixed start-up floor is large and variable.** A two-instruction program with the modelled 32 MiB RAM allocation took 10.2–16.6 ms warm across three series; the same program with the allocation removed took 6.2–7.8 ms. Differences between programs below a few milliseconds are not resolvable here.
3. **Optimizer collapse.** A tight counted loop whose only observable effect is a register reaching a constant can be reduced to a closed form by `/O2`. "Steps executed" and "work done" can diverge. This is the largest methodological hazard in the runtime numbers.
4. **Single machine, single session.** Run-to-run spread reached several milliseconds on warm launches and several seconds on the largest compile. Absolute values must not be compared across machines or treated as stable constants.
5. **Static CRT.** The command-line default statically links the C++ runtime, so executable size and process start-up include CRT code that a dynamic-runtime build would load from DLLs. This is a property of this harness build, not of a product runtime.

## 4. Measurements

### 4.1 Named fixtures — source, build and execution

| Metric | `differential` | `broad` | Label |
|---|---|---|---|
| Generated C++ bytes | 21,918 | 37,109 | Terverifikasi |
| Generated C++ lines | 494 | 812 | Terverifikasi |
| Fixed prelude, formatted with empty dispatch and blocks | 13,909 B / 347 lines | 13,909 B / 347 lines | Terverifikasi |
| Prelude share of generated source | 63.5% | 37.5% | Terverifikasi |
| Bytes of C++ per guest instruction, excluding the prelude | 143.0 | 136.5 | Terverifikasi |
| Block-body lines per guest instruction | 2.55 | 2.64 | Terverifikasi |
| Memory blob bytes | 600 | 1,540 | Terverifikasi |
| `cl` wall time, median of 3 builds | 2.888 s (2.910, 2.836, 2.888) | 3.399 s (3.249, 3.399, 4.922) | Terverifikasi |
| `vcvars64.bat` bootstrap alone, median of 3 | 1.378 s | 1.378 s | Terverifikasi |
| `cl` wall time net of the bootstrap | 1.510 s | 2.021 s | Terverifikasi |
| Executable size | 293,888 B | 301,056 B | Terverifikasi |
| Cold first launch | 0.718 s | 1.657 s | Terverifikasi |
| Warm launch, first series (4 runs) | 10.76 ms | 15.65 ms | Terverifikasi |
| Warm launch, second series (10 runs) | 16.72 ms | 17.75 ms | Terverifikasi |
| Steps executed at budget 100,000 | 54 | 166 | Terverifikasi |
| Halt reason / final PC | `pc_outside_code` / `0x7FFF0000` | `pc_outside_code` / `0x7FFF0000` | Terverifikasi |
| Standard output bytes | 1,382 | 2,431 | Terverifikasi |
| Oracle wall time, median of 3 | 242.4 µs | 393.5 µs | Terverifikasi |
| Oracle steps | 54 | 166 | Terverifikasi |

Both fixtures halt after a few dozen steps, so warm launch is essentially the start-up floor, not execution. The two warm-launch series disagree by up to 6 ms for the same binary; that is the measurement noise, not a program difference. The "net of bootstrap" row is the difference of two medians from different runs, so it is approximate.

At this size, compile cost is dominated by the fixed prelude and the MSVC/iostream header set, not by the emitted instructions. A two-instruction `halt` program compiled in 2.514 s median of three (net of bootstrap: 1.136 s); the 56-instruction fixture compiled in 2.888 s (net: 1.510 s). The 2-instruction build is still 284,672 B. **Terverifikasi.**

### 4.2 Python-side stage costs

Medians of three in-process repetitions. Each repetition ran a fresh parse, discovery, lowering and generation.

| Stage | `differential` (56 instr) | `broad` (170 instr) | Share of `broad` | Label |
|---|---|---|---|---|
| `parse_elf_bytes` | 36.4 µs | 49.4 µs | 1.8% | Terverifikasi |
| `discover_program` | 1,003.3 µs | 1,690.6 µs | 62.6% | Terverifikasi |
| `lower_program` | 224.8 µs | 390.7 µs | 14.5% | Terverifikasi |
| `generate` | 333.3 µs | 783.0 µs | 29.0% | Terverifikasi |
| Total analysis | 1,707.6 µs | 2,699.1 µs | 100% | Terverifikasi |

The `broad` total is about 15.9 µs per guest instruction. `discover_program` is the largest share (59–63%). The draft's total for `broad` (2.77 ms) is reproduced; its per-stage split is not (it reported 1,633 µs discovery, 559 µs lowering and 553 µs generation). The `differential` total (1.71 ms) is higher than the draft's 1.23 ms. The differences are within Python/timing variability and were not investigated further.

The fixtures are too small to separate fixed cost from per-instruction cost, so the per-instruction figure is a ratio, not a fitted slope. Extrapolating 15.9 µs/instruction to the 413,500 aligned code-range words recorded for the authorized Downhill Domination sample implies roughly 6.6 s of analysis for that count. **Dugaan**; it must be measured on a real ELF before any budget is set, and discovery cost need not be linear at title scale.

### 4.3 Compile-time scaling

All single-block programs are one straight-line block: one C++ function and one `switch` case. Split programs are M block functions, each ending in `J`/`JR` plus `NOP`. Total `cl` wall includes the ~1.38 s `vcvars64.bat` bootstrap.

| Program | Guest instructions | C++ bytes | `cl` wall (median) | Repetitions | Executable bytes | Label |
|---|---|---|---|---|---|---|
| `halt` | 2 | 14,166 | 2.514 s | 3 | 284,672 | Terverifikasi |
| `straight-130` | 130 | 28,648 | 3.627 s | 2 | 292,864 | Terverifikasi |
| `straight-514` | 514 | 72,424 | 7.663 s | 2 | 307,712 | Terverifikasi |
| `straight-1026` | 1,026 | 130,816 | 13.778 s | 1 | 340,480 | Terverifikasi |
| `straight-2050` | 2,050 | 248,576 | 4.582 s | 1 | 593,920 | Terverifikasi |
| `split-1024/32` | 1,088 | 137,109 | 3.146 s | 1 | 379,392 | Terverifikasi |
| `split-2048/32` | 2,176 | 261,365 | 3.923 s | 1 | 473,600 | Terverifikasi |
| `split-2048/8` | 2,560 | 300,341 | 3.528 s | 1 | 526,336 | Terverifikasi |

The shape is reproducible but the draft's description is not precise:

- From 130 to 1,026 instructions, compile time grows roughly in proportion to source size (3.6 s → 7.7 s → 13.8 s), not "far faster than source size". The draft's own table already showed a 1,026→1,538 decline (21.47 s → 17.77 s).
- At 2,050 instructions in one function the optimizer behaviour changes: compile time falls to 4.582 s while the executable grows to 593,920 B (from 340,480 B at 1,026). A plausible explanation is that the optimizer stops fully optimizing a very large function, which both cuts compile time and inflates the binary. **Dugaan**; the mechanism was not confirmed against compiler documentation or any vendor implementation.
- The split series removes the growth: 2,176 instructions in 64 block functions compile in 3.923 s, while 1,026 instructions in one function take 13.778 s. In this pass that is 2.1× the code in about 28% of the time (roughly 3.5× faster), not the draft's "six times the code, one sixth the compile time". The direction and the several-fold magnitude are **Terverifikasi**; the exact ratio is session-dependent.

This is `docs/RISKS.md` R-010 evidence for the synthetic pipeline. The CFG allows blocks up to `MAX_BLOCK_INSTRUCTIONS = 4096` (`tools/rptp/cfg.py`), and a long straight-line run is the shape that fills a block. Whether retail code contains such runs is **Dugaan**; the generator behaviour is **Terverifikasi**.

### 4.4 Per-step cost and the trace artefact

The generated `run()` loop appends every executed PC to `std::vector<std::uint32_t> trace` and prints the whole vector as JSON at exit (`tools/rptp/codegen.py`, `push_trace` and `print_state`). The loop program was re-run with a corrected counter: `LUI`+`ORI` set the iteration count, so the executed step counts are 3N+4 as intended.

| Build variant | Steps measured | Warm medians | ns per executed step | Label |
|---|---|---|---|---|
| As generated (trace recorded and printed) | 30,004 / 120,004 | 17.768 ms / 36.021 ms | 203 | Terverifikasi |
| Trace recorded, not printed (measurement-only rewrite) | 30,004 / 120,004 | 9.738 ms / 10.935 ms | 13.3 | Terverifikasi |
| Trace neither recorded nor printed (measurement-only rewrite) | 30,004 / 120,004 | 9.945 ms / 11.520 ms | 17.5 | Terverifikasi |

The rewrite variants were counterfactual builds of the same generated source, produced only under `build/` for measurement; no repository file was touched. Warm medians are from 8–10 launches per point.

1. **Trace emission dominates the current executable.** The as-generated slope is about 203 ns per executed step, reproducing the draft's 221 ns. With printing suppressed the slope falls to 13–18 ns per step. That is an order-of-magnitude difference, not a resolved execution cost.
2. **The execution-only cost is not resolved by this method.** Both counterfactual endpoints sit within 1–2 ms of the ~10 ms start-up floor, and the floor itself varied by several milliseconds. The 13.3 and 17.5 ns slopes are therefore upper bounds contaminated by the floor, not measurements of guest work. The draft's 2.2 and 9.5 ns figures were not reproduced. The draft's 0.42 ns/step point at 12 million steps was not re-run (**Belum diverifikasi**); a three-instruction counted loop whose only observable effect is a register reaching a constant is a prime candidate for closed-form reduction by `/O2`, which is exactly why such a figure cannot be treated as throughput.

What is safe to say: the current generated harness is not a runtime, and its measured wall clock per guest step is dominated by a debugging trace that a product runtime would not emit. Any performance statement taken from `rptp_native.exe` today measures the harness, not the recompiled code.

### 4.5 Start-up floor and the 32 MiB RAM model

| Series | Two-step program as generated | Same program with `state.ram.assign(RAM_SIZE, 0)` removed | Difference | Label |
|---|---|---|---|---|
| 6 warm launches | 15.463 ms | 7.839 ms | 7.62 ms | Terverifikasi |
| 10 warm launches | 16.574 ms | 6.220 ms | 10.35 ms | Terverifikasi |
| 10 warm launches | 10.207 ms | 6.372 ms | 3.84 ms | Terverifikasi |

Every run of the generated program allocates and zeroes the full 32 MiB guest RAM before executing one instruction (`State::ram.assign` in the prelude). The direction is reproducible: the allocation is a multi-millisecond fixed cost, and at fixture sizes it is comparable to or larger than execution. The exact cost is not stable across series (3.8–10.4 ms), so the draft's single 4.8 ms value should be read as one observation in that range, not as a constant. The 32 MiB size is the RPTP memory model (`codegen.RAM_SIZE`, `oracle.RAM_SIZE`), not a datasheet claim.

## 5. Static reading of the generated code

This section is a reading of `tools/rptp/codegen.py` and of the emitted source, not a profile. Code-shape claims are **Terverifikasi against the source**; the performance consequence attached to each is **Dugaan** unless a measurement above covers it.

### 5.1 Helper calls versus inline expressions

Counts are textual call expressions inside the generated block bodies only (the region from the first `static void block_` to `void run`), so prelude definitions and helper-internal calls are excluded. Every row therefore has one basis. The draft mixed whole-source and block-body counts; several of its rows are corrected here.

| Construct | `differential` (56 instr) | `broad` (170 instr) | Notes |
|---|---|---|---|
| `push_trace(s, pc)` | 56 | 170 | exactly one per emitted instruction |
| `write_reg(s, idx, U128)` | 46 | 136 | one per architectural write; guards `index != 0` |
| `sext32` / `sext64` | 22 / 13 | 71 / 46 | wraps narrowing or widening writes |
| `effective_address` | 4 | 21 | one per scalar or quad memory instruction |
| `read_le` / `write_le` | 1 / 1 | 14 / 4 | byte loop plus bounds check |
| `read128` / `write128` | 1 / 1 | 2 / 1 | `LQ`/`SQ`; these call `read_le`/`write_le` internally in the prelude |
| `exec_div` / `exec_mult` / `exec_madd` | 2 / 1 / 0 | 4 / 3 / 3 | out-of-line helper per multiply/divide |
| `lanes_binary` / `lanes_unary` | 5 / 3 | 0 / 0 | MMI lane loops with per-lane `lane_of`/`set_lane` |

Arithmetic itself is not a helper call: `ADDIU`, `ADDU`, `SUBU`, `AND`, `OR`, `SLT`, `SLL` and friends are emitted as inline expressions over `s.r[n].lo`. The overhead is in the wrappers (`write_reg`, the sign-extension helpers) rather than in the operation. `write_reg` takes `U128` by value and is small, so an optimizing compiler will normally inline it; the emitted shape is nevertheless one call expression, one `!= 0` test and one 16-byte store per guest write. **Dugaan** for the inlining outcome; **Terverifikasi** for the emitted shape.

### 5.2 Guest-memory bounds checks and address translation

Every load and store costs, in this order:

1. `effective_address(s, base, offset)` — a 64-bit add, `physical()` with two 32-bit range comparisons (`0x8000_0000–0x9FFF_FFFF` and `0xA000_0000–0xBFFF_FFFF`) and a subtract;
2. an alignment test where the access width demands one (1/2/4/8 bytes), which on failure throws `std::runtime_error`;
3. `check_ram(address, size)` — a 64-bit compare against `RAM_SIZE = 0x0200_0000`;
4. a **byte-at-a-time** loop over `size` elements: 4 iterations for `LW`/`SW`, 8 for `LD`/`SD`, 16 for `LQ`/`SQ`.

Instruction fetch has no runtime cost: each block is straight-line C++, so decoding happens at generation time and there is no per-instruction fetch, decoder or bounds check. **Terverifikasi.**

Stores additionally write every byte into `std::map<std::uint32_t, std::uint8_t> writes` so the harness can print the final memory image. A single `SW` therefore performs four tree lookups/insertions on top of the four RAM stores; `SD` eight; `SQ` sixteen. **Terverifikasi** in the prelude. This is the biggest structural difference between the test harness and any future product runtime, and a plausible reason a memory-heavy loop would be much slower than the ALU loop measured in §4.4. **Dugaan.** The draft's attempt to isolate load/store cost produced deltas inside the noise; it was not re-run (**Belum diverifikasi**) and is not used to rank anything.

### 5.3 Trap and overflow checks

- `ADD`/`SUB`/`DADD`/`DSUB` emit an explicit overflow test and call `rptp::trap(...)`; the 64-bit forms call `add_overflow64`/`sub_overflow64`. Only these four mnemonics pay it. **Terverifikasi.**
- `ADDU`/`SUBU`/`DADDU`/`DSUBU`/`ADDIU`/`DADDIU` do not trap, so they emit no check. **Terverifikasi.**
- Memory faults and unaligned accesses use C++ exceptions. The happy path pays only the comparison; the throw path is irrelevant to throughput but allocates and unwinds if a guest really faults. **Terverifikasi** for the shape; **Dugaan** that it matters only on the failure path.
- Nothing traps on unmapped instruction fetches: a PC that reaches no case falls to `default:` and sets `pc_outside_code`. **Terverifikasi.**

### 5.4 Dispatch and block structure

- One C++ function per block (`static void block_XXXXXXXX(rptp::State&)`), plus a `switch (s.pc)` with one `case` per block in `run()`.
- Dispatch is paid **per block**, not per instruction: a block writes `s.pc` once at its end and returns to the loop. Mean block length in the named fixtures is 8.0 and 8.9 instructions. Whether retail code amortises dispatch better or worse is **Dugaan**.
- The loop also re-tests `s.halted` and `s.steps >= s.max_steps` once per block. **Terverifikasi.**
- All state lives in one `State` struct (32 × `U128` registers = 512 bytes, HI/LO pairs, PC, counters, memory, trace, writes map). Nothing is kept in host registers across blocks, so every block entry reloads from memory. **Terverifikasi** structurally; the cost is **Dugaan**.
- Branch delay slots are emitted inline inside the terminating block, so a taken branch does not cost an extra dispatch. **Terverifikasi.**

### 5.5 Register array

`s.r` is `std::array<U128, 32>`; each register carries `lo` and `hi`, and every write stores 16 bytes even when the instruction only defines 32 bits. Reads usually touch only `.lo`. `$zero` is enforced by the `write_reg` guard rather than by a dedicated zero register. **Terverifikasi.** Consequence: half of the register file's store traffic is the sign-extension shadow, and a guest register rename would not be expressible without changing `State`. **Dugaan.**

### 5.6 Code-size growth

| Quantity | Value | Label |
|---|---|---|
| Fixed prelude per translation unit | 13,909 B / 347 lines when formatted with empty dispatch and blocks | Terverifikasi |
| C++ bytes per guest instruction, straight-line series | 111.9–114.5 | Terverifikasi |
| C++ bytes per guest instruction, named fixtures | 136.5–143.0 | Terverifikasi |
| Block-body source lines per guest instruction | 2.0–2.1 straight-line; 2.55–2.64 named fixtures | Terverifikasi |
| Executable floor, two-step program | 284,672 B | Terverifikasi |
| Executable growth, 130 → 1,026 instructions | 292,864 B → 340,480 B (+53.1 B, about 0.052 KiB, per instruction) | Terverifikasi |
| Executable size at 2,050 instructions, post-collapse | 593,920 B | Terverifikasi |

At 113 B/instruction, a 400,000-instruction title would emit roughly 45 MB of C++ in one translation unit if nothing changed. That is a planning figure for R-010, not a measurement. **Dugaan** for the extrapolation; the per-instruction constant is **Terverifikasi**.

The draft's "2.3 source lines per guest instruction" is not what this pass measures: the straight-line series is 2.0–2.1 and the named fixtures are 2.55–2.64. The draft's "~330 prelude lines" is also low; the formatted prelude is 347 lines.

### 5.7 Python-side analysis

Analysis is pure Python and single-threaded. Measured cost is about 15.9 µs per instruction end to end at fixture scale (§4.2), with `discover_program` the largest share (59–63%). The generator is 4.6 µs per instruction in the `broad` fixture and produces a string that is written once per build. There is no caching between runs: `native.run_differential` re-discovers, re-lowers and re-generates on every call. **Terverifikasi** in `tools/rptp/native.py`. Whether this matters at title scale is **Belum diverifikasi**; it should be measured on a real owner-authorized, read-only ELF before any decision to rewrite the analyzer in C++, which would need an owner-approved ADR per `AGENTS.md` §1.

## 6. What this does not measure

- **No retail or game performance.** No retail executable was loaded, recompiled or executed. Nothing here predicts frame rate, load time or playability.
- **No boot.** No image boots, in the harness or anywhere else.
- **No compatibility.** An inspected ISO, a loaded synthetic image and a generated differential binary are not evidence of game compatibility.
- **No hardware timing.** The RPTP model has no cycle counts, pipeline, cache, TLB or timing behaviour. "Steps" are retired model instructions, not EE cycles; the 32 MiB figure is the project's memory model, not a datasheet claim.
- **No product-runtime claim.** `rptp_native.exe` is a differential test vehicle. Its per-step wall time is dominated by a trace a product runtime would not emit.
- **No resolved execution cost.** The trace-free slopes are within the start-up floor's noise. No per-guest-instruction execution cost is claimed.
- **No optimizer-internals claim.** The explanation for the 2,050-instruction collapse is a **Dugaan**; no compiler source or vendor implementation was consulted.
- **No transferability claim.** Every timing is from one machine, one compiler build and this session. Absolute values must not be compared across machines or treated as stable constants.
- **No CI performance claim.** No benchmark or timing threshold runs in CI. A local run is not CI.
- **No clean-room or Gate implication.** This note adds no evidence for Gate 3, changes no component status in `docs/CLEAN_ROOM_AUDIT.md`, and passes no Gate.

## 7. Corrections to the draft

| Draft claim | What this pass found | Disposition |
|---|---|---|
| "Every number below is Terverifikasi" | Many numbers were not re-run; several differ materially. | Replaced with per-row labels. |
| Link mode: "MSVC default (dynamic CRT)" | `dumpbin /dependents` listed only `KERNEL32.dll`; the CRT is statically linked. | Corrected. |
| Warm launch: 10.0 / 9.9 ms | 10.8–16.7 ms (`differential`) and 15.6–17.7 ms (`broad`) across two series. | Corrected; noise range given. |
| Cold launch: 0.57–0.67 s | 0.46–1.81 s in this session; cause not established. | Corrected. |
| "Compile time rises far faster than source size" / "superlinearly" | Roughly proportional from 130 to 1,026 instructions, then a collapse at 2,050. The draft's own table already showed a decline at 1,538. | Corrected. |
| "Six times the code, one sixth the compile time" | 2.1× the code compiled about 3.5× faster in this pass (3.923 s vs 13.778 s). | Corrected; direction retained. |
| Helper table (e.g. `write_reg` 48/138, `sext32` 25/17, `read_le` 3/3) | Mixed counting bases; block-body counts are 46/136, 22/71, 1/14. | Corrected with one counting method. |
| "2.3 C++ source lines per guest instruction" | 2.0–2.1 straight-line, 2.55–2.64 named fixtures. | Corrected. |
| "~330 prelude lines" | 347 lines when formatted with empty dispatch and blocks. | Corrected. |
| Trace residual slopes 2.2 and 9.5 ns/step | 13.3 and 17.5 ns/step, both within the start-up-floor noise. | Corrected; no execution-cost claim. |
| 0.42 ns/step at 12M steps | Not re-run. | Marked Belum diverifikasi; treated as a collapse warning, not throughput. |
| ">95% of measured wall time per step is diagnostics" | The as-generated slope is about 10–15× the no-print slope; the exact share is unresolved. | Softened. |
| Per-stage Python timings | `broad` total reproduces; per-stage values do not. | Corrected. |
| "The mechanism was not confirmed ... no compiler source consulted" | Still true. | Retained as Dugaan. |

The draft did not contain absolute host paths. This note also contains none.

## 8. Reproduction

The measurements used only public repository calls. From the repository root, in a Developer PowerShell x64:

    python tools/rptp_doctor.py
    python -m unittest tests.test_ir_lowering tests.test_native_diff -v
    python -m unittest tests.test_doc_freshness tests.test_doc_budget -v
    python tools/check_forbidden_artifacts.py

The named-fixture source size, blob size and step count need no compiler:

```python
from tools.rptp import cfg, codegen, elf, fixtures, ir, oracle

image = elf.parse_elf_bytes(fixtures.differential_fixture(), path="differential.elf")
program = cfg.discover_program(image)
result = ir.lower_program(program)
generated = codegen.generate(program, result)
print(len(generated.source.encode("utf-8")))   # 21918
print(len(generated.source.splitlines()))      # 494
print(len(generated.memory_blob))              # 600
print(oracle.run_oracle(program, max_steps=100_000)["steps"])  # 54
```

A compile/run measurement uses a fresh directory under the git-ignored `build/` tree:

```python
from pathlib import Path
from tools.rptp import cfg, codegen, elf, fixtures, ir, native

image = elf.parse_elf_bytes(fixtures.differential_fixture(), path="differential.elf")
program = cfg.discover_program(image)
generated = codegen.generate(program, ir.lower_program(program))
workdir = Path("build") / "perf-repro"
exe = native.build_native(generated, workdir)
blob = workdir / codegen.MEMORY_BLOB_NAME
print(native.run_native(exe, 100_000, blob)["steps"])  # 54
```

A straight-line scaling point can be built without touching the test suite:

```python
from pathlib import Path
from tools.rptp import cfg, codegen, elf, fixtures, ir, native

asm = fixtures.Assembler()
for index in range(512):
    asm.addiu(fixtures.T0, fixtures.ZERO, index & 0x7FFF)
asm.jr(fixtures.RA)
asm.nop()
image = elf.parse_elf_bytes(fixtures.build_elf(asm.resolve()), path="straight.elf")
program = cfg.discover_program(image)
generated = codegen.generate(program, ir.lower_program(program))
print(len(generated.source.encode("utf-8")))   # about 72 KB for this construction
exe = native.build_native(generated, Path("build") / "perf-repro-straight")
```

Delete `build/perf-repro*` afterwards. Compile and launch times depend on the machine and must be measured, not copied.

## 9. Deferred optimization backlog

Stage 3 optimization and runtime/recompiler expansion remain gated on a booting vertical slice. **No item below is authorized by this note, and none was implemented.** The list is ordered by the strength of the evidence that exists today, not by expected game impact.

1. **Remove or gate the differential trace in any product runtime.** Evidence: trace printing costs about 203 ns per executed step and produced 960,373 bytes of stdout for 120,004 steps, while the no-print slope was 13–18 ns. Status: not guest optimization; the product runtime does not exist. Deferred.
2. **Cap or split large block functions before single-translation-unit compile time dominates.** Evidence: 1,026 instructions in one function took 13.778 s, while 2,176 instructions in 64 functions took 3.923 s; the 2,050-instruction single function fell to 4.582 s while the executable grew to 593,920 B. This is R-010. Deferred: it needs a semantic-preserving block-splitting design, differential evidence for every fixture and its own increment.
3. **Redesign the guest-memory path.** Evidence: source reading shows address translation, alignment checks, a 64-bit bound check, a byte-at-a-time loop and a per-byte `std::map` write record. The cost is **Belum diverifikasi** because the isolation experiment is inconclusive. Deferred: it depends on the product memory model and a non-collapsed benchmark corpus.
4. **Reduce register write traffic and the `U128` shadow.** Evidence: every write stores 16 bytes even for 32-bit results, and `$zero` is a runtime guard. The cost is **Belum diverifikasi**. Deferred: it changes the register model and needs a full semantic review.
5. **Improve block dispatch and host-state layout.** Evidence: one `switch` per block, no host registers carried across blocks, 8–9 instructions per block in the named fixtures. The cost is **Dugaan**. Deferred until a product runtime can attribute time by block.
6. **Measure, then decide about Python analyzer latency.** Evidence: about 15.9 µs per instruction at fixture scale, with discovery 59–63% of the total; title-scale cost is **Belum diverifikasi**. Deferred: a C++ migration would need an owner-approved ADR; caching is a smaller change but still needs a title-scale measurement first.

Measurement prerequisites for ranking the backlog above, none of which this note implements:

- a non-collapsible synthetic corpus with checksums, where time is verified to scale with iteration count;
- a compile-time and source-size budget on a fixed corpus;
- a memory-path isolation experiment that clears the start-up floor by at least an order of magnitude;
- per-block counters and a wall-clock sample in a future runtime.

Regression thresholds should not be gated in CI until a product runtime exists and runner variance is measured. A shared CI runner is the wrong instrument for a 5% timing threshold.

An optimization that cannot be differentially validated is not performed. Gate 3 is not passed, and no performance work should jump ahead of it.
