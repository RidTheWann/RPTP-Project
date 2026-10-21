# References and provenance

Access date for the public technical references below: 2026-10-21.

| Ref | Public source | Permitted use in the Gate 0 spike | Limits |
|---|---|---|---|
| RPTP-REF-001 | University of Waterloo, [MIPS Encoding Reference](https://student.cs.uwaterloo.ca/~isg/res/mips/opcodes) | Field encodings and generic opcodes for common MIPS instructions used by the synthetic fixture: ADDIU, ADDU, BEQ/BNE, J/JAL/JR, LW/SW. | Educational generic MIPS reference; does not verify all R5900-specific behavior. |
| RPTP-REF-002 | UNSW, [MIPS Instruction Set guide](https://web.cse.unsw.edu.au/~cs1521/26T2/resources/mips-guide.html) | Cross-check common instruction naming and register conventions used in the educational fixture. | The page describes a MIPS32 subset used by educational emulators. It is not treated as an R5900 hardware specification. |
| RPTP-REF-003 | Linux man-pages project, [elf(5)](https://man7.org/linux/man-pages/man5/elf.5.html) | ELF header/program-header organization and ELF32 program-segment field definitions for the synthetic fixture parser. | Generic ELF format only; this spike does not claim full support for retail PS2 ELF variants. |
| RPTP-REF-004 | PS2DEV project, [PS2SDK documentation README](https://github.com/ps2dev/ps2sdk) | High-level confirmation that PS2 development distinguishes Emotion Engine and I/O Processor contexts; no PS2SDK source code is copied or linked. | Not used as an implementation template. The Gate 0 spike is a synthetic instruction test and does not implement PS2 system calls. |
| RPTP-REF-005 | [MIPS architecture overview](https://en.wikipedia.org/wiki/MIPS_architecture), as a secondary cross-check | Background statement that classic MIPS control-flow instructions use a branch delay slot. | Secondary source; not authoritative for R5900-specific or PS2-specific behavior. The spike tests only its own narrow model; R5900 confirmation remains open. |

## Verification labels

- **Verified by local test:** the synthetic fixture is reproducible; its parser accepts it and rejects selected malformed inputs; generated C++ matches the reference interpreter for the supported fixture path. The recorded runs include Linux/GCC, Linux/Clang and Windows x64/MSVC.
- **Document-cross-checked:** common MIPS instruction encodings and generic ELF fields referenced above.
- **Not verified:** complete R5900 semantics, delay-slot details beyond the fixture model, EE-specific floating-point/MMI behavior, VU behavior, GS pixel behavior, IOP services, DMA ordering, hardware timing, ISO inspection/boot and commercial-game compatibility.

## Clean-room source exposure record

This table records prior exposure from the conversation, not sources used to build the spike.

| Project/source | Previously accessed material | What is known | Boundary applied here |
|---|---|---|---|
| ran-j/PS2Recomp | README technical descriptions; top-level LICENSE stating GPL-3.0; repository tree/metadata; release notes for v0.3/v0.4; issue/PR text around #370/#371. | No .cpp file contents were fetched or inspected in the tool outputs shown in the conversation. Some non-source issue/release text included implementation-level descriptions. | Recorded as prior exposure. No source code from this project is included or used by the spike. Keep this exposure explicit in future sessions. |
| snuri00/ps2-web-recomp | README technical descriptions; repository tree; top-level CMakeLists.txt; scripts/port.sh; scripts/windows.py; top-level LICENSE. | This goes beyond README-only exposure: the previous session displayed build configuration and two Python/Bash source scripts. The project LICENSE was read as MIT. No runtime/src implementation file contents were fetched in those tool outputs. | Treat this as a recorded prior exposure, not a clean slate. Do not use those implementation details as design inputs or copy their code. The present spike is independently authored from documented generic encodings and its own generated fixture. |
| PS2SDK | Public README/documentation page only. | Public SDK documentation separates EE and IOP toolchain contexts and states project licensing information. | Used for high-level context only; no SDK source code included. |

A historical exposure cannot be undone. The goal is to disclose its scope accurately and prevent it from silently becoming an implementation source. If the human owner interprets any item above as disqualifying under the clean-room policy, stop and amend ADR-0001 before proceeding beyond the isolated spike. The CMake/CI/doctor baseline is new project infrastructure and does not resolve the owner's pending review of prior technical exposure.
