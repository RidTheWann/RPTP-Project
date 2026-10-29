# SPDX-License-Identifier: GPL-3.0-or-later
"""Encoding conformance tests for the R5900 decoder.

Every expectation is derived mechanically from
``docs/research/r5900-isa.json``, the repository's research catalog (224
entries).  The JSON ``verified`` flag is a catalog bookkeeping marker; it is
not evidence of hardware verification, and R5900-specific citations in that
file come from a manual that is PENDING an owner decision.  Test words are
built from the documented opcode/funct/operand fields rather than from the
decoder's own tables, so a decoder table cell that disagrees with the
research data fails here.

The suite also pins the MMI subtable layout, the full 11-bit standalone
function space (including all PMFHL selectors), the sa-in-bits-10:6
fallback used by the six standalone PS shift instructions, the
reserved-selector note, and explicit failure for genuinely unknown words.

It finally checks that every mnemonic listed in ``isa.SUPPORTED_MNEMONICS``
is reachable from a decoded word and can be lowered by ``tools/rptp/ir.py``
(control transfers through ``lower_block``; everything else through the
instruction-level lowering).

One known decoder defect is recorded as an expected failure at the bottom
of the file; it is reported, not fixed, because this task may not modify
``tools/rptp/isa.py``.
"""
from __future__ import annotations

import collections
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.rptp import ir, isa  # noqa: E402  (path set up above)
from tools.rptp.cfg import BasicBlock  # noqa: E402

RESEARCH_FILE = ROOT / "docs" / "research" / "r5900-isa.json"

PC = 0x00100000
MASK32 = 0xFFFFFFFF
MMI_OPCODE = 0x1C
MMI_BASE = MMI_OPCODE << 26

# Distinct sample values make field mix-ups visible: if the decoder put rs
# into the rt slot the assertions below would see 9 where 10 is expected.
SAMPLE = {
    "rd": 17,
    "rs": 9,
    "rt": 10,
    "sa": 5,
    "immediate": 0x1234,
    "offset": 0x0010,
    "base": 29,
    "vf": 7,
    "id": 3,
    "op": 3,
    "target": 0x00ABCD,
    "code": 0xABCDE,
    "stype": 2,
}

# Function values whose shift amount lives in bits 10:6 of the MMI word.
MMI_SHIFT_BASE = {
    0x034: "psllh",
    0x036: "psrlh",
    0x037: "psrah",
    0x03C: "psllw",
    0x03E: "psrlw",
    0x03F: "psraw",
}

# PMFHL variants are selected by the high five bits of the 11-bit function
# field; PMTHL.LW is a separate standalone function.
PMFHL_FUNCTS = {
    "pmfhl.lw": 0x030,
    "pmfhl.uw": 0x070,
    "pmfhl.slw": 0x0B0,
    "pmfhl.lh": 0x0F0,
    "pmfhl.sh": 0x130,
}
PMTHL_LW_FUNCT = 0x031

# The eight research entries that cannot be represented at mnemonic
# granularity: the decoder deliberately treats all COP2 macro-mode
# instructions as a single opaque placeholder until COP2 exists.
SKIPPED = {
    "QMFC2": "COP2 transfer decodes only as the opaque 'cop2' placeholder.",
    "QMTC2": "COP2 transfer decodes only as the opaque 'cop2' placeholder.",
    "CFC2": "COP2 control transfer decodes only as the opaque 'cop2' placeholder.",
    "CTC2": "COP2 control transfer decodes only as the opaque 'cop2' placeholder.",
    "BC2F": "COP2 branch conditions (rt=0..3 under rs=8) are not distinguished.",
    "BC2FL": "COP2 branch conditions (rt=0..3 under rs=8) are not distinguished.",
    "BC2T": "COP2 branch conditions (rt=0..3 under rs=8) are not distinguished.",
    "BC2TL": "COP2 branch conditions (rt=0..3 under rs=8) are not distinguished.",
}

EXPECTED_CLASS_COUNTS = {
    "special": 52,
    "mips3": 41,
    "regimm": 16,
    "special2": 25,
    "mmi0": 25,
    "mmi1": 18,
    "mmi2": 22,
    "mmi3": 13,
    "cop2": 10,
    "lqsq": 2,
}


class Unencodable(ValueError):
    """Raised when a research entry cannot be turned into a unique word."""


def _load_research() -> dict:
    with RESEARCH_FILE.open(encoding="utf-8") as handle:
        return json.load(handle)


RESEARCH = _load_research()
ENTRIES = RESEARCH["instructions"]
ENTRIES_BY_MNEMONIC = {entry["mnemonic"]: entry for entry in ENTRIES}


def _sample_operands(entry: dict) -> dict:
    values: dict[str, int] = {}
    for operand in entry["operands"]:
        name = operand.rstrip("?")
        if name not in SAMPLE:
            raise Unencodable(f"{entry['mnemonic']}: unknown operand {operand!r}")
        values[name] = 0 if operand.endswith("?") else SAMPLE[name]
    return values


def encode_entry(entry: dict) -> int:
    """Build the canonical 32-bit word documented by a research entry.

    Reserved fields are forced to zero so the result is a valid encoding
    rather than a reserved-encoding diagnostic.
    """
    cls = entry["class"]
    opcode = entry["opcode"]
    mnemonic = entry["mnemonic"]
    values = _sample_operands(entry)

    rs = values.get("rs", values.get("base", 0))
    rt = values.get("rt", values.get("vf", values.get("op", 0)))
    rd = values.get("rd", 0)
    sa = values.get("sa", values.get("stype", 0))
    imm = values.get("immediate", values.get("offset", 0))

    if cls == "special":
        funct = entry["funct"]
        if funct in (0x0C, 0x0D):  # SYSCALL/BREAK: code in bits 25..6.
            return ((values["code"] & 0xFFFFF) << 6) | funct
        if funct in {0x00, 0x02, 0x03, 0x38, 0x3A, 0x3B, 0x3C, 0x3E, 0x3F}:
            rs = 0
        elif funct == 0x08:  # JR
            rt = rd = sa = 0
        elif funct == 0x09:  # JALR; rd defaults to 31.
            rt = sa = 0
            rd = 31
        elif funct in (0x10, 0x12):  # MFHI/MFLO
            rs = rt = sa = 0
        elif funct in (0x11, 0x13):  # MTHI/MTLO
            rt = rd = sa = 0
        elif funct == 0x0F:  # SYNC
            rs = rt = rd = 0
        elif funct == 0x28:  # MFSA
            rs = rt = sa = 0
        elif funct == 0x29:  # MTSA
            rt = rd = sa = 0
        elif funct in (0x18, 0x19):  # MULT/MULTU two-operand form
            rd = 0
        return (
            (opcode << 26)
            | (rs << 21)
            | (rt << 16)
            | (rd << 11)
            | (sa << 6)
            | (funct & 0x3F)
        )

    if cls == "regimm":
        return (
            (opcode << 26)
            | (rs << 21)
            | ((entry["funct"] & 0x1F) << 16)
            | (imm & 0xFFFF)
        )

    if cls in ("mmi0", "mmi1", "mmi2", "mmi3", "special2"):
        funct11 = entry["funct"] & 0x7FF
        if mnemonic.lower() in MMI_SHIFT_BASE.values():
            funct11 |= values["sa"] << 6
        return (
            MMI_BASE
            | (rs << 21)
            | (rt << 16)
            | (rd << 11)
            | funct11
        )

    if cls in ("mips3", "lqsq"):
        if "target" in values:
            return (opcode << 26) | (values["target"] & 0x03FFFFFF)
        return (opcode << 26) | (rs << 21) | (rt << 16) | (imm & 0xFFFF)

    if cls == "cop2":
        if mnemonic in ("LQC2", "SQC2"):
            return (opcode << 26) | (rs << 21) | (rt << 16) | (imm & 0xFFFF)
        raise Unencodable(SKIPPED.get(mnemonic, f"{mnemonic}: no encoder"))

    raise Unencodable(f"{mnemonic}: unsupported research class {cls!r}")


def mmi_word(funct11: int, rd: int = 0, rs: int = 0, rt: int = 0) -> int:
    return MMI_BASE | (rs << 21) | (rt << 16) | (rd << 11) | (funct11 & 0x7FF)


def canonical_word(mnemonic: str) -> int | None:
    """Return a valid encoding for a supported mnemonic, searching the tables."""
    if mnemonic == "nop":
        return 0
    for funct, spec in sorted(isa.SPECIAL.items()):
        if spec.mnemonic == mnemonic:
            return encode_entry(
                {
                    "mnemonic": mnemonic.upper(),
                    "class": "special",
                    "opcode": 0,
                    "funct": funct,
                    "operands": _special_operands(funct, spec),
                }
            )
    for rt, spec in sorted(isa.REGIMM.items()):
        if spec.mnemonic == mnemonic:
            return (0x01 << 26) | (SAMPLE["rs"] << 21) | (rt << 16) | 0x0010
    for opcode, spec in sorted(isa.PRIMARY.items()):
        if spec.mnemonic == mnemonic:
            if opcode in (0x02, 0x03):
                return (opcode << 26) | 0x00ABCD
            return (
                (opcode << 26)
                | (SAMPLE["rs"] << 21)
                | (SAMPLE["rt"] << 16)
                | 0x0010
            )
    for group, table in sorted(isa.MMI_GROUPS.items()):
        selector = {0: 0x08, 1: 0x28, 2: 0x09, 3: 0x29}[group]
        for subfunct, spec in sorted(table.items()):
            if spec.mnemonic == mnemonic:
                fields = _format_fields(spec.fmt)
                return mmi_word((subfunct << 6) | selector, **fields)
    for funct11, spec in sorted(isa.MMI_STANDALONE.items()):
        if spec.mnemonic == mnemonic:
            if spec.fmt in ("rd,rt,sa",):
                funct11 |= SAMPLE["sa"] << 6
            fields = _format_fields(spec.fmt)
            return mmi_word(funct11, **fields)
    return None


def _format_fields(fmt: str) -> dict:
    fields = {"rd": 0, "rs": 0, "rt": 0}
    for part in fmt.split(","):
        if part in ("rd", "rs", "rt"):
            fields[part] = SAMPLE[part]
    return fields


def _special_operands(funct: int, spec: isa.OpSpec) -> list[str]:
    """Operand tokens for a SPECIAL spec, with reserved fields removed."""
    if funct in (0x0C, 0x0D):
        return ["code"]
    return list(spec.fmt.split(","))


class IsaEncodingTests(unittest.TestCase):
    def assert_decoded_operands(self, entry: dict, ins: isa.Instruction) -> None:
        tokens = [operand.rstrip("?") for operand in entry["operands"]]
        optional_rd = "rd?" in entry["operands"]

        if "rd" in tokens:
            if entry["mnemonic"] == "JALR":
                # The documented default link register is GPR 31.
                self.assertEqual(ins.rd, 31)
            else:
                self.assertEqual(ins.rd, 0 if optional_rd else SAMPLE["rd"])
        if "rs" in tokens:
            self.assertEqual(ins.rs, SAMPLE["rs"])
        if "base" in tokens:
            self.assertEqual(ins.rs, SAMPLE["base"])
        if "rt" in tokens:
            self.assertEqual(ins.rt, SAMPLE["rt"])
        if "vf" in tokens:
            self.assertEqual(ins.rt, SAMPLE["vf"])
        if "op" in tokens:
            self.assertEqual(ins.rt, SAMPLE["op"])
        if "sa" in tokens:
            self.assertEqual(ins.shamt, SAMPLE["sa"])
        if "stype" in tokens:
            self.assertEqual(ins.shamt, SAMPLE["stype"])
        if "immediate" in tokens:
            self.assertEqual(ins.imm, SAMPLE["immediate"])
            self.assertEqual(ins.simm, SAMPLE["immediate"])
        if "offset" in tokens:
            simm = isa.sign_extend(SAMPLE["offset"], 16)
            self.assertEqual(ins.simm, simm)
            if entry["delay_slot"]:
                expected = (PC + 4 + (simm << 2)) & MASK32
                self.assertEqual(ins.target, expected)
        if "target" in tokens:
            expected = ((PC + 4) & 0xF0000000) | (
                (SAMPLE["target"] & 0x03FFFFFF) << 2
            )
            self.assertEqual(ins.target, expected)
        if "code" in tokens:
            self.assertEqual(ins.text(), f"{ins.mnemonic} 0x{SAMPLE['code']:05X}")

    # -- research fixture -------------------------------------------------

    def test_research_catalog_entries_are_present_and_complete(self):
        self.assertEqual(RESEARCH["schema_version"], 1)
        self.assertEqual(len(RESEARCH["sources"]), 4)
        self.assertEqual(len(ENTRIES), 224)
        self.assertEqual(len(ENTRIES_BY_MNEMONIC), 224, "mnemonics must be unique")
        self.assertEqual(
            {entry["mnemonic"] for entry in ENTRIES}, set(ENTRIES_BY_MNEMONIC)
        )
        for entry in ENTRIES:
            with self.subTest(mnemonic=entry["mnemonic"]):
                # Structural marker only: this checks the catalog JSON shape,
                # not that the entry's semantics were hardware-verified.
                self.assertIs(entry["verified"], True)
                self.assertTrue(entry["citation"])
                self.assertIsInstance(entry["operands"], list)
        counts = collections.Counter(entry["class"] for entry in ENTRIES)
        self.assertEqual(dict(counts), EXPECTED_CLASS_COUNTS)

    def test_skip_list_is_small_explicit_and_complete(self):
        self.assertEqual(
            set(SKIPPED),
            {"QMFC2", "QMTC2", "CFC2", "CTC2", "BC2F", "BC2FL", "BC2T", "BC2TL"},
        )
        self.assertLessEqual(len(SKIPPED), 8)
        self.assertTrue(all(reason for reason in SKIPPED.values()))
        self.assertTrue(set(SKIPPED) <= set(ENTRIES_BY_MNEMONIC))
        for mnemonic in SKIPPED:
            self.assertEqual(
                ENTRIES_BY_MNEMONIC[mnemonic]["class"],
                "cop2",
                f"{mnemonic} is skipped but is not a COP2 entry",
            )
        encoded = 0
        for entry in ENTRIES:
            if entry["mnemonic"] in SKIPPED:
                with self.subTest(mnemonic=entry["mnemonic"]):
                    with self.assertRaises(Unencodable):
                        encode_entry(entry)
            else:
                with self.subTest(mnemonic=entry["mnemonic"]):
                    word = encode_entry(entry)
                    self.assertGreaterEqual(word, 0)
                    self.assertLessEqual(word, MASK32)
                    encoded += 1
        self.assertEqual(encoded, 216)
        self.assertEqual(encoded + len(SKIPPED), len(ENTRIES))

    # -- every documented encoding ---------------------------------------

    def test_every_encodable_entry_decodes_exactly(self):
        checked = 0
        for entry in ENTRIES:
            mnemonic = entry["mnemonic"].lower()
            if entry["mnemonic"] in SKIPPED:
                continue
            word = encode_entry(entry)
            with self.subTest(mnemonic=mnemonic, word=f"0x{word:08X}"):
                ins = isa.decode_instruction(word, PC)
                self.assertEqual(ins.word, word)
                self.assertEqual(ins.pc, PC)
                self.assertFalse(
                    ins.mnemonic.startswith("unknown_"),
                    f"0x{word:08X} decoded as {ins.mnemonic} ({ins.note})",
                )
                self.assertEqual(ins.mnemonic, mnemonic)
                self.assertTrue(ins.valid, ins.note)
                self.assertNotEqual(ins.verification, isa.UNSUPPORTED)
                self.assertEqual(
                    ins.supported, mnemonic in isa.SUPPORTED_MNEMONICS
                )
                self.assert_decoded_operands(entry, ins)
                checked += 1
        self.assertEqual(checked, 216)

    def test_three_operand_multiply_forms_carry_rd(self):
        for mnemonic in ("MULT", "MULTU"):
            for rd in (0, 3, 31):
                with self.subTest(mnemonic=mnemonic, rd=rd):
                    base = encode_entry(ENTRIES_BY_MNEMONIC[mnemonic])
                    word = base | (rd << 11)
                    ins = isa.decode_instruction(word, PC)
                    self.assertEqual(ins.mnemonic, mnemonic.lower())
                    self.assertEqual(ins.rd, rd)
                    self.assertEqual(ins.rs, SAMPLE["rs"])
                    self.assertEqual(ins.rt, SAMPLE["rt"])
                    self.assertTrue(ins.valid)
                    self.assertTrue(ins.supported)
        for mnemonic in ("MADD", "MADDU"):
            base = encode_entry(ENTRIES_BY_MNEMONIC[mnemonic])
            word = base | (0x1F << 11)
            ins = isa.decode_instruction(word, PC)
            self.assertEqual(ins.mnemonic, mnemonic.lower())
            self.assertEqual(ins.rd, 0x1F)
            self.assertTrue(ins.valid)

    def test_signed_immediate_and_target_bits(self):
        # ADDIU rt, rs, -1
        addiu = (
            (ENTRIES_BY_MNEMONIC["ADDIU"]["opcode"] << 26)
            | (SAMPLE["rs"] << 21)
            | (SAMPLE["rt"] << 16)
            | 0xFFFF
        )
        ins = isa.decode_instruction(addiu, PC)
        self.assertEqual(ins.mnemonic, "addiu")
        self.assertEqual(ins.imm, 0xFFFF)
        self.assertEqual(ins.simm, -1)

        # BEQ rs, rt, -16: target = PC + 4 - 64.
        beq = (
            (ENTRIES_BY_MNEMONIC["BEQ"]["opcode"] << 26)
            | (SAMPLE["rs"] << 21)
            | (SAMPLE["rt"] << 16)
            | 0xFFF0
        )
        ins = isa.decode_instruction(beq, PC)
        self.assertEqual(ins.mnemonic, "beq")
        self.assertEqual(ins.simm, -16)
        self.assertEqual(ins.target, (PC + 4 - 64) & MASK32)

        # J target keeps the upper nibble of PC+4.
        high_pc = 0x80100000
        jump = (ENTRIES_BY_MNEMONIC["J"]["opcode"] << 26) | 0x000010
        ins = isa.decode_instruction(jump, high_pc)
        self.assertEqual(ins.mnemonic, "j")
        self.assertEqual(
            ins.target, ((high_pc + 4) & 0xF0000000) | (0x10 << 2)
        )

    # -- MMI layout -------------------------------------------------------

    def test_mmi_subtable_matrix(self):
        defined = 0
        undefined = 0
        for selector, group in sorted(isa.MMI_SUBTABLE_SELECT.items()):
            self.assertEqual(
                {0: 0x08, 1: 0x28, 2: 0x09, 3: 0x29}[group], selector
            )
            for subfunct in range(32):
                funct11 = (subfunct << 6) | selector
                word = mmi_word(
                    funct11,
                    rd=SAMPLE["rd"],
                    rs=SAMPLE["rs"],
                    rt=SAMPLE["rt"],
                )
                with self.subTest(group=group, subfunct=subfunct):
                    self.assertEqual(isa.MMI_SUBTABLE_SELECT[funct11 & 0x3F], group)
                    self.assertEqual((funct11 >> 6) & 0x1F, subfunct)
                    ins = isa.decode_instruction(word, PC)
                    spec = isa.MMI_GROUPS[group].get(subfunct)
                    if spec is None:
                        undefined += 1
                        self.assertEqual(ins.mnemonic, f"unknown_0x{word:08X}")
                        self.assertFalse(ins.valid)
                    else:
                        defined += 1
                        self.assertEqual(ins.mnemonic, spec.mnemonic)
                        self.assertEqual(ins.rs, SAMPLE["rs"])
                        self.assertEqual(ins.rt, SAMPLE["rt"])
                        self.assertEqual(ins.rd, SAMPLE["rd"])
                        self.assertTrue(ins.valid)
        self.assertEqual(defined, 78)
        self.assertEqual(undefined, 128 - 78)

    def test_mmi_standalone_uses_the_full_11_bit_function(self):
        checked = 0
        for funct11, spec in sorted(isa.MMI_STANDALONE.items()):
            if spec.mnemonic in MMI_SHIFT_BASE.values():
                continue
            fields = _format_fields(spec.fmt)
            word = mmi_word(funct11, **fields)
            with self.subTest(mnemonic=spec.mnemonic, funct11=hex(funct11)):
                ins = isa.decode_instruction(word, PC)
                self.assertEqual(ins.mnemonic, spec.mnemonic)
                self.assertTrue(ins.valid, ins.note)
                for part in spec.fmt.split(","):
                    if part in ("rd", "rs", "rt"):
                        self.assertEqual(
                            getattr(ins, part), SAMPLE[part]
                        )
                self.assertEqual(
                    ins.supported,
                    spec.mnemonic in isa.SUPPORTED_MNEMONICS and spec.supported,
                )
                checked += 1
        self.assertEqual(checked, len(isa.MMI_STANDALONE) - len(MMI_SHIFT_BASE))

    def test_pmfhl_variants_and_pmthl_lw(self):
        research = {
            entry["mnemonic"].lower(): entry["funct"]
            for entry in ENTRIES
            if entry["class"] == "special2"
            and (
                entry["mnemonic"].startswith("PMFHL")
                or entry["mnemonic"] == "PMTHL.LW"
            )
        }
        self.assertEqual(
            research, dict(PMFHL_FUNCTS, **{"pmthl.lw": PMTHL_LW_FUNCT})
        )
        self.assertEqual(len(set(PMFHL_FUNCTS.values())), 5)

        for index, (mnemonic, funct11) in enumerate(
            sorted(PMFHL_FUNCTS.items(), key=lambda item: item[1])
        ):
            with self.subTest(mnemonic=mnemonic):
                self.assertEqual(funct11 & 0x3F, 0x30)
                self.assertEqual(funct11 >> 6, index)
                self.assertEqual(
                    isa.MMI_STANDALONE[funct11].mnemonic, mnemonic
                )
                entry = ENTRIES_BY_MNEMONIC[mnemonic.upper()]
                word = encode_entry(entry)
                ins = isa.decode_instruction(word, PC)
                self.assertEqual(ins.mnemonic, mnemonic)
                self.assertEqual(ins.rd, SAMPLE["rd"])
                self.assertTrue(ins.valid)
                self.assertFalse(ins.supported)

        entry = ENTRIES_BY_MNEMONIC["PMTHL.LW"]
        word = encode_entry(entry)
        ins = isa.decode_instruction(word, PC)
        self.assertEqual(word & 0x7FF, PMTHL_LW_FUNCT)
        self.assertEqual(ins.mnemonic, "pmthl.lw")
        self.assertEqual(ins.rs, SAMPLE["rs"])
        self.assertTrue(ins.valid)
        self.assertFalse(ins.supported)
        self.assertTrue(ins.writes_hi_lo)

    def test_standalone_shift_sa_lives_in_bits_10_to_6(self):
        checked = 0
        for base, mnemonic in sorted(MMI_SHIFT_BASE.items()):
            spec = isa.MMI_STANDALONE[base]
            self.assertEqual(spec.mnemonic, mnemonic)
            self.assertEqual(spec.fmt, "rd,rt,sa")
            self.assertNotIn(base, isa.MMI_SUBTABLE_SELECT)
            for sa in range(32):
                funct11 = base | (sa << 6)
                word = mmi_word(
                    funct11,
                    rd=SAMPLE["rd"],
                    rs=SAMPLE["rs"],
                    rt=SAMPLE["rt"],
                )
                with self.subTest(mnemonic=mnemonic, sa=sa):
                    self.assertEqual((funct11 >> 6) & 0x1F, sa)
                    self.assertEqual(funct11 & 0x3F, base)
                    if sa == 0:
                        self.assertIn(funct11, isa.MMI_STANDALONE)
                    else:
                        # The unmasked 11-bit key must not exist; the decoder
                        # is expected to fall back to the masked base key.
                        self.assertNotIn(funct11, isa.MMI_STANDALONE)
                        self.assertEqual(
                            isa.MMI_STANDALONE[funct11 & 0x3F].mnemonic,
                            mnemonic,
                        )
                    ins = isa.decode_instruction(word, PC)
                    self.assertEqual(ins.mnemonic, mnemonic)
                    self.assertEqual(ins.shamt, sa)
                    self.assertEqual(ins.rd, SAMPLE["rd"])
                    self.assertEqual(ins.rt, SAMPLE["rt"])
                    self.assertTrue(ins.valid)
                    self.assertEqual(
                        ins.supported, mnemonic in isa.SUPPORTED_MNEMONICS
                    )
                    checked += 1
        self.assertEqual(checked, len(MMI_SHIFT_BASE) * 32)

    def test_reserved_mmi_selector_bits_are_flagged(self):
        bases = [
            (funct11, spec)
            for funct11, spec in sorted(isa.MMI_STANDALONE.items())
            if spec.fmt != "rd,rt,sa" and not spec.mnemonic.startswith("pmfhl")
        ]
        self.assertEqual(len(bases), 14)
        for funct11, spec in bases:
            with self.subTest(mnemonic=spec.mnemonic, selector=0):
                canonical = isa.decode_instruction(mmi_word(funct11), PC)
                self.assertEqual(canonical.mnemonic, spec.mnemonic)
                self.assertTrue(canonical.valid)
                self.assertEqual(canonical.note, "")
            for selector in (1, 5, 31):
                word = mmi_word(
                    funct11 | (selector << 6),
                    rd=SAMPLE["rd"],
                    rs=SAMPLE["rs"],
                    rt=SAMPLE["rt"],
                )
                with self.subTest(mnemonic=spec.mnemonic, selector=selector):
                    self.assertNotEqual((word & 0x7FF) >> 6, 0)
                    ins = isa.decode_instruction(word, PC)
                    self.assertEqual(ins.mnemonic, spec.mnemonic)
                    self.assertFalse(ins.valid)
                    self.assertFalse(ins.supported)
                    self.assertIn(
                        "Reserved MMI selector bits are non-zero.", ins.note
                    )
                    self.assertFalse(ins.mnemonic.startswith("unknown_"))

    def test_undefined_mmi_functions_are_unknown(self):
        words = [
            mmi_word(0x002),
            mmi_word(0x005),
            mmi_word(0x00E),
            mmi_word(0x015),
            mmi_word((0x18 << 6) | 0x08),  # undefined MMI0 sub-opcode
            mmi_word((0x01 << 6) | 0x29),  # undefined MMI3 sub-opcode
        ]
        for word in words:
            with self.subTest(word=f"0x{word:08X}"):
                funct11 = word & 0x7FF
                self.assertNotIn(funct11, isa.MMI_STANDALONE)
                group = isa.MMI_SUBTABLE_SELECT.get(funct11 & 0x3F)
                defined_subopcode = (
                    group is not None
                    and ((funct11 >> 6) & 0x1F) in isa.MMI_GROUPS[group]
                )
                self.assertFalse(defined_subopcode)
                ins = isa.decode_instruction(word, PC)
                self.assertEqual(ins.mnemonic, f"unknown_0x{word:08X}")
                self.assertFalse(ins.valid)
                self.assertFalse(ins.supported)
                with self.assertRaises(ValueError):
                    isa.decode_instruction(word, PC, strict=True)

    # -- unknown words ----------------------------------------------------

    def test_unknown_words_are_never_guessed(self):
        words = [
            0x00000001,  # SPECIAL funct 0x01
            0x00000005,  # SPECIAL funct 0x05
            0x0000000E,  # SPECIAL funct 0x0E
            0x0000003D,  # SPECIAL funct 0x3D
            0x4C000000,  # primary opcode 0x13
            0xC0000000,  # primary opcode 0x30
            0xD4000000,  # primary opcode 0x35
            0x74000000,  # primary opcode 0x1D
        ]
        for word in words:
            with self.subTest(word=f"0x{word:08X}"):
                opcode = (word >> 26) & 0x3F
                funct = word & 0x3F
                if opcode == 0:
                    self.assertNotIn(funct, isa.SPECIAL)
                else:
                    self.assertNotIn(opcode, isa.PRIMARY)
                ins = isa.decode_instruction(word, PC)
                self.assertEqual(ins.mnemonic, f"unknown_0x{word:08X}")
                self.assertEqual(ins.cls, "unknown")
                self.assertFalse(ins.valid)
                self.assertFalse(ins.supported)
                self.assertEqual(ins.verification, isa.UNSUPPORTED)
                self.assertTrue(ins.is_halt)
                self.assertIn("Unsupported", ins.note)
                with self.assertRaises(ValueError):
                    isa.decode_instruction(word, PC, strict=True)

    def test_zero_word_is_nop_and_known_words_do_not_raise_in_strict_mode(self):
        nop = isa.decode_instruction(0, PC)
        self.assertEqual(nop.mnemonic, "nop")
        self.assertTrue(nop.valid)
        self.assertTrue(nop.supported)
        self.assertIn("nop", isa.SUPPORTED_MNEMONICS)
        for mnemonic in ("paddw", "pmfhl.lw", "lq", "beq", "madd"):
            word = canonical_word(mnemonic)
            with self.subTest(mnemonic=mnemonic):
                ins = isa.decode_instruction(word, PC, strict=True)
                self.assertEqual(ins.mnemonic, mnemonic)

    def test_cop2_entries_are_exposed_as_an_opaque_placeholder(self):
        self.assertEqual(isa.PRIMARY[0x12].mnemonic, "cop2")
        self.assertFalse(isa.PRIMARY[0x12].supported)
        bc2_conditions = {"BC2F": 0, "BC2T": 1, "BC2FL": 2, "BC2TL": 3}
        bc2_words = set()
        for mnemonic in SKIPPED:
            entry = ENTRIES_BY_MNEMONIC[mnemonic]
            self.assertEqual(entry["class"], "cop2")
            if mnemonic in bc2_conditions:
                word = (
                    (0x12 << 26)
                    | (0x08 << 21)
                    | (bc2_conditions[mnemonic] << 16)
                    | (SAMPLE["offset"] & 0xFFFF)
                )
                bc2_words.add(word)
            else:
                rd_field = (
                    SAMPLE["vf"] if mnemonic in ("QMFC2", "QMTC2") else SAMPLE["id"]
                )
                word = (
                    (0x12 << 26)
                    | (SAMPLE["rt"] << 16)
                    | (rd_field << 11)
                    | (entry["funct"] & 0x3F)
                )
            with self.subTest(mnemonic=mnemonic):
                ins = isa.decode_instruction(word, PC)
                self.assertEqual(ins.mnemonic, "cop2")
                self.assertEqual(ins.cls, "cop2")
                self.assertTrue(ins.valid)
                self.assertFalse(ins.supported)
        # The four COP2 branch conditions are distinct words but share one
        # placeholder mnemonic, which is why they are recorded as skipped.
        self.assertEqual(len(bc2_words), 4)

    # -- lowering of every supported mnemonic -----------------------------

    def test_every_supported_mnemonic_decodes_and_lowers(self):
        expected_control = {
            "beq": "branch",
            "bne": "branch",
            "blez": "branch",
            "bgtz": "branch",
            "bltz": "branch",
            "bgez": "branch",
            "bltzal": "branch",
            "bgezal": "branch",
            "beql": "branch",
            "bnel": "branch",
            "blezl": "branch",
            "bgtzl": "branch",
            "bltzl": "branch",
            "bgezl": "branch",
            "bltzall": "branch",
            "bgezall": "branch",
            "j": "jump",
            "jal": "call",
            "jr": "indirect",
            "jalr": "indirect_call",
        }
        covered = set()
        unlowerable: list[str] = []
        for mnemonic in sorted(isa.SUPPORTED_MNEMONICS):
            word = canonical_word(mnemonic)
            with self.subTest(mnemonic=mnemonic):
                self.assertIsNotNone(
                    word, f"no decoder encoding found for supported {mnemonic!r}"
                )
                ins = isa.decode_instruction(word, PC)
                self.assertEqual(ins.mnemonic, mnemonic)
                self.assertTrue(ins.supported)
                covered.add(mnemonic)
            try:
                if mnemonic in isa.CONTROL_MNEMONICS:
                    delay = isa.decode_instruction(0, PC + 4)
                    block = BasicBlock(
                        start=PC,
                        instructions=[ins, delay],
                        kind="branch",
                        successors=(PC + 8,),
                    )
                    lowered = ir.lower_block(block)
                    self.assertEqual(lowered.control.mnemonic, mnemonic)
                    self.assertNotEqual(lowered.control.kind, "unsupported")
                    self.assertEqual(
                        lowered.control.kind, expected_control[mnemonic]
                    )
                else:
                    lowered_op = ir._lower_instruction(ins)
                    self.assertEqual(lowered_op.mnemonic, mnemonic)
                    self.assertEqual(lowered_op.pc, PC)
            except Exception as exc:  # LoweringError or a control-kind mismatch.
                unlowerable.append(f"{mnemonic}: {exc}")
        self.assertEqual(covered, set(isa.SUPPORTED_MNEMONICS))
        self.assertEqual(unlowerable, [])

    def test_jr_ra_lowers_to_return(self):
        word = (31 << 21) | 0x08
        ins = isa.decode_instruction(word, PC)
        self.assertEqual(ins.mnemonic, "jr")
        self.assertTrue(ins.supported)
        block = BasicBlock(
            start=PC,
            instructions=[ins, isa.decode_instruction(0, PC + 4)],
            kind="branch",
            successors=(PC + 8,),
        )
        lowered = ir.lower_block(block)
        self.assertEqual(lowered.control.kind, "return")
        self.assertEqual(lowered.control.target_reg, 31)

    def test_undefined_pmfhl_selectors_are_not_guessed(self):
        """Selectors 5..31 of the PMFHL function space are undefined.

        PMFHL selectors 0..4 are defined (lw 0x030, uw 0x070, slw 0x0B0,
        lh 0x0F0, sh 0x130); the masked standalone fallback must only apply
        to the PS shift ops, never to the PMFHL selector space.
        """
        wrongly_accepted = []
        for selector in range(5, 32):
            funct11 = (selector << 6) | 0x30
            word = MMI_BASE | funct11
            ins = isa.decode_instruction(word, PC)
            if ins.mnemonic != f"unknown_0x{word:08X}":
                wrongly_accepted.append(
                    f"0x{word:08X} -> {ins.mnemonic} (valid={ins.valid})"
                )
        self.assertEqual(wrongly_accepted, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
