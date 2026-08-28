"""Locked Time drawing gold — one row to add a 12th weldment.

Identity-locked: each fixture asserts the (part_no, qty) set for dash -1.
Desktop ``*-LOM.xlsx`` files were not on this VM; rows come from Kyle's
locked lists only. Do not invent PNs. Drop Kyle's sheet onto
``tests/fixtures/lom/{pn}-LOM.xlsx`` when it is available.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quote_core.lom_xlsx import write_lom_xlsx

FIXTURE_DIR = Path(__file__).resolve().parent / "lom"

# Kyle-confirmed 1001898-1 dash -1 (live GET / Desktop LOM).
DASH_1001898: list[tuple[str, int, str, str]] = [
    ("A", 1, "14500-1", "PEDESTAL TOP PLATE"),
    ("B", 1, "1001880-2", "PEDESTAL TUBE"),
    ("C", 2, "29860-4", "PEDESTAL BRACE ANGLE"),
    ("D", 1, "14501-1", "RESERVOIR TOP PLATE"),
    ("E", 1, "1005966-1", "PEDESTAL BOTTOM PLATE"),
    ("F", 2, "50137-5", "3/4 NPT HALF COUPLING"),
    ("G", 1, "50115-7", "1 1/4 NPT NIPPLE X 4 LG."),
    ("H", 1, "50030-5", "3/4 NPT COUPLING"),
    ("J", 1, "8166-1", "FILLER NECK"),
    ("K", 1, "9905-1", "MOUNTING PLATE, EMER POWER"),
    ("L", 1, "33637-1", "1 1/4 RETURN TUBE"),
    ("M", 1, "10081-2", "PEDESTAL HOSE TUBE"),
    ("N", 1, "50006-5", "3/4 NPT MAGNETIC PLUG"),
    ("P", 1, "50122-1", "1 1/4 NPT PIPE CAP"),
    ("U", 2, "29860-3", "PEDESTAL BRACE ANGLE"),
    ("X", 8, "1005940-1", "PEDESTAL GUSSET"),
    ("AB", 1, "50029-7", "1 1/4 90 STREET ELBOW"),
]
_1001898_OTHER_DASH = [
    ("Q", "1001899-1", "OTHER DASH Q"),
    ("R", "1001900-1", "OTHER DASH R"),
    ("S", "1001901-1", "OTHER DASH S"),
    ("T", "1001902-1", "OTHER DASH T"),
    ("V", "1001903-1", "OTHER DASH V"),
    ("W", "1001904-1", "OTHER DASH W"),
    ("Y", "1001905-1", "OTHER DASH Y"),
    ("Z", "1001906-1", "OTHER DASH Z"),
    ("AA", "1001907-1", "OTHER DASH AA"),
    ("AC", "1001908-1", "OTHER DASH AC"),
]

# Workspace-read 102728-1-LOM.xlsx (51/97). Notable items match Kyle this drop.
DASH_102728: list[tuple[str, int, str, str]] = [
    ("A", 1, "460200", "RAIL, BOTTOM FRONT MIDDLE"),
    ("B", 1, "460270", "RAIL, BOTTOM FRONT RIGHT HAND"),
    ("C", 1, "460280", "RAIL, BOTTOM FRONT LEFT HAND"),
    ("D", 1, "432580", "RAIL, BOTTOM BACK"),
    ("E", 2, "432600", "RAIL, BOTTOM SIDE"),
    ("F", 1, "100350-1", "TUBE, GRATING SUPPORT MIDDLE"),
    ("G", 2, "100373-2", "TUBE, GRATING SUPPORT SIDES"),
    ("H", 1, "100351-1", "RECTANGLE TUBE"),
    ("J", 1, "102733-1", "GRATING"),
    ("K", 2, "432640", "RAIL, VERTICAL MIDDLE BACK"),
    ("L", 1, "460230", "RAIL, VERTICAL MIDDLE FRONT"),
    ("M", 2, "460300", "RAIL, BOTTOM RIGHT HAND"),
    ("N", 1, "460340", "TUBE, TOP RAIL"),
    ("P", 2, "100362-1", "ROUND TUBE"),
    ("Q", 1, "432650", "RAIL, HORIZONTAL CENTER BACK"),
    ("R", 1, "432660", "RAIL, BACK TOP"),
    ("S", 2, "94560", "GATE, FABRICATION"),
    ("T", 2, "464100", "PIN, PLATFORM SHOCK"),
    ("U", 2, "298540", "CAP, TUBE RAIL"),
    ("V", 6, "432710", "CAP, 2 x 1 TUBE"),
    ("W", 4, "432690", "RAIL, CORNER VERTICAL"),
    ("X", 2, "432670", "RAIL, HORIZONTAL BACK OUTER"),
    ("Y", 4, "100363-1", "ANGLE"),
    ("Z", 2, "460320", "CAP, VERTICAL RAIL TOP"),
    ("AA", 5, "460330", "CAP, VERTICAL RAIL BOTTOM"),
    ("AB", 1, "464450", "RAIL TOP FRONT"),
    ("AC", 4, "100177-2", "PLATE"),
    ("AD", 8, "464440", "PLATE, SUPPORT"),
    ("AE", 2, "436010", "RAIL, SIDE TOP"),
    ("AF", 2, "464460", "RAIL, HORIZONTAL FRONT OUTER"),
    ("AG", 1, "100350-2", "TUBE, GRATING SUPPORT MIDDLE"),
    ("AH", 2, "100373-1", "TUBE, GRATING SUPPORT SIDES"),
    ("AJ", 1, "100351-2", "RECTANGLE TUBE"),
    ("AK", 1, "100351-3", "RECTANGLE TUBE"),
    ("AL", 1, "100738-1", "RAIL, VERTICAL MIDDLE FRONT"),
    ("AM", 1, "33688-6", "EXPANDED METAL PLATE"),
    ("AN", 2, "33688-7", "EXPANDED METAL PLATE"),
    ("AP", 2, "33688-8", "EXPANDED METAL PLATE"),
    ("AQ", 2, "33688-9", "EXPANDED METAL PLATE"),
    ("AR", 1, "33688-10", "EXPANDED METAL PLATE"),
    ("AS", 1, "100267-1", "CONTROL BOX PLATFORM MT."),
    ("AT", 2, "100366-27", "PLATE"),
    ("AU", 1, "102711-1", "CABLE TUBE WELDMENT"),
    ("AV", 1, "102712-1", "CABLE ENCLOSURE"),
    ("AW", 1, "102725-1", "PLATE, FRONT"),
    ("AX", 2, "102726-1", "HOOK"),
    ("AY", 1, "102727-1", "TUBE, ROUND"),
    ("AZ", 2, "102727-2", "TUBE, ROUND"),
    ("BA", 2, "102727-3", "TUBE, ROUND"),
    ("BB", 2, "102727-4", "TUBE, ROUND"),
    ("BC", 1, "102727-5", "TUBE, ROUND"),
]

DASH_1004747: list[tuple[str, int, str, str]] = [
    ("17", 2, "6993-1", "HOSE GUIDE"),
    ("15", 1, "1004806-1", "OUTER BOOM SUB-WELD"),
    ("12", 1, "32259-1", "RETAINER BAR, HOSE"),
    ("11", 1, "1004738-1", "TOP STIFFENER, OUTER BOOM"),
    ("10", 1, "1004739-1", "BOTTOM STIFFENER, OUTER BOOM"),
    ("9", 1, "1004711-1", "STIFFENER, CYLINDER MOUNT"),
    ("8", 1, "1004741-1", "MASTER CYLINDER MOUNT PLATE"),
    ("7", 1, "1004740-1", "MASTER CYLINDER MOUNT CHANNEL"),
    ("6", 2, "1004773-1", "CYLINDER SUPPORT"),
    ("5", 2, "1004743-1", "CYLINDER ANCHOR"),
    ("4", 1, "1004744-2", "BRACE, OUTER BOOM SIDE"),
    ("3", 1, "1004744-1", "BRACE, OUTER BOOM SIDE"),
    ("2", 2, "1004737-1", "PIVOT SUPPORT PLATE"),
    ("1", 1, "25060-6", "TUBE, PIVOT"),
]
_1004747_OTHER = [
    ("16", "1004806-2", ""),
    ("14", "11694-2", ""),
    ("13", "25009-2", ""),
]

DASH_28106: list[tuple[str, int, str, str]] = [
    ("A", 1, "16697-2", "LOWER BOOM TUBE 91 1/8 LG."),
    ("B", 1, "26732-1", "CYLINDER MOUNT PLATE W/ 3/8 HOLES"),
    ("C", 1, "26732-2", "CYLINDER MOUNT PLATE"),
    ("D", 1, "15644-1", "STIFFENER, CYLINDER MOUNT"),
    ("E", 1, "16694-1", "STIFFENER, CUTOUT"),
    ("F", 1, "15890-1", "END CAP, BOOM"),
    ("G", 2, "15891-1", "HOSE GUARD"),
    ("H", 1, "10187-1", "HOSE RETAINER"),
    ("J", 2, "15864-2", "STIFFENER, BOOM PIVOT"),
    ("K", 1, "15863-1", "PIVOT TUBE, LOWER BOOM"),
    ("M", 1, "15654-1", "STIFFENER PLATE"),
]
_28106_OTHER = [
    ("L", "-2", "16697-1", "LOWER BOOM TUBE 55 LG."),
    ("N", "-3", "16697-3", "LOWER BOOM TUBE"),
    ("P", "-4", "16697-4", "LOWER BOOM TUBE"),
]

DASH_1007922: list[tuple[str, int, str, str]] = [
    ("A", 2, "21897-1", "TUBE"),
    ("B", 4, "14149-1", "FILLER"),
    ("C", 4, "10099-1", "TUBE"),
    ("D", 1, "21750-1", "PLATE"),
    ("E", 1, "21743-1", "PLATE"),
    ("F", 2, "1007830-1", "OUTRIGGER LEG"),
]
_1007922_OTHER = [
    ("L", "21750-2", ""),
    ("P", "21743-2", ""),
]

DASH_21727: list[tuple[str, int, str, str]] = [
    ("A", 1, "10176-2", "TUBE"),
    ("B", 1, "21726-2", "PLATE"),
    ("C", 1, "21726-1", "PLATE"),
    ("D", 1, "21724-1", "PLATE"),
    ("E", 1, "21725-1", "PLATE"),
    ("F", 2, "21722-1", "PLATE"),
    ("G", 2, "21723-1", "PLATE"),
    ("H", 1, "21721-1", "PLATE"),
    ("J", 1, "14463-1", "PLATE"),
    ("K", 4, "50030-1", "COUPLING"),
    ("L", 1, "21889-1", "PLATE"),
]

DASH_33612: list[tuple[str, int, str, str]] = [
    ("A", 1, "28275-1", "TOE KICK, REAR"),
    ("B", 1, "28275-2", "TOE KICK, SIDE"),
    ("C", 1, "28276-1", "TOE KICK, FRONT"),
    ("D", 1, "28283-1", "PLATFORM DECK"),
    ("E", 2, "28270-1", "MOUNTING TUBE WELDMENT"),
    ("F", 2, "28269-1", "FLOOR SUPPORT, INNER"),
    ("G", 4, "28268-1", "FLOOR SUPPORT, OUTER"),
    ("H", 4, "28265-1", "HORIZ. INTERMED. RAIL, SIDE"),
    ("J", 1, "28265-2", "HORIZ. INTERMED. RAIL, LOWER GATE"),
    ("K", 3, "33613-1", "HORIZ. INTERMED. RAIL"),
    ("L", 1, "28274-2", "HORIZ. INTERMED. RAIL, FRONT"),
    ("M", 1, "28266-1", "VERT. RAIL, STRAIGHT"),
    ("N", 1, "28281-1", "STIFFENER"),
    ("P", 4, "28273-2", "CAP PLATE"),
    ("Q", 4, "28282-1", "LANYARD ANCHOR"),
    ("R", 1, "28278-1", "PLATFORM GATE WELDMENT"),
    ("S", 2, "28287-1", "GATE REST"),
    ("T", 4, "33611-1", "CORNER VERT. RAIL, STRAIGHT"),
    ("U", 4, "33638-1", "PIPE CAP"),
    ("V", 1, "28275-3", "TOE KICK, SIDE"),
    ("W", 4, "8121-2", "SPUD, VALVE SUPPORT"),
]

DASH_105098: list[tuple[str, int, str, str]] = [
    ("A", 1, "103603-1", "MAIN PLATFORM WELDMENT"),
    ("B", 1, "104124-1", "CONTROL BOX MOUNT"),
    ("C", 1, "104124-2", "CONTROL BOX MOUNT"),
    ("D", 1, "104977-1", "BATTERY BOX MOUNT"),
    ("E", 1, "105094-1", "PLATFORM REST SUB-WELDMENT"),
    ("F", 1, "105095-1", "PLATFORM SWITCH MOUNT"),
    ("G", 1, "105096-1", "CHARGE CABLE BRACKET"),
    ("H", 1, "105097-1", "INTERCOM MOUNT"),
    ("J", 1, "40002-2", "1/4-20NC HHCS X 5/8 L"),
]

DASH_103516: list[tuple[str, int, str, str]] = [
    ("1", 1, "103517-1", ""),
    ("2", 1, "103518-1", ""),
    ("3", 1, "103519-1", ""),
    ("4", 4, "103520-1", ""),
    ("5", 2, "103521-1", ""),
    ("6", 2, "103522-1", ""),
    ("7", 2, "103523-1", ""),
    ("8", 2, "103524-1", ""),
    ("9", 2, "103525-1", ""),
    ("10", 1, "103526-1", ""),
    ("11", 1, "103527-1", ""),
    ("12", 1, "103528-1", ""),
    ("13", 2, "103529-1", ""),
    ("14", 1, "103530-1", ""),
    ("15", 1, "103531-1", ""),
    ("16", 1, "103532-1", ""),
    ("17", 1, "103533-1", ""),
    ("18", 1, "103534-1", ""),
    ("19", 1, "30345-19", ""),
    ("20", 1, "103535-1", "GATE WELDMENT"),
    ("21", 1, "103536-1", ""),
    ("22", 1, "103537-1", ""),
    ("23", 2, "103538-1", ""),
    ("24", 3, "103539-1", ""),
    ("25", 4, "103540-1", ""),
    ("26", 4, "103541-1", ""),
    ("27", 1, "40002-2", ""),
]

DASH_103535: list[tuple[str, int, str, str]] = [
    ("A", 1, "103542-1", "GATE RAIL"),
    ("B", 2, "103543-1", "GATE RAIL"),
    ("C", 2, "103544-1", "STRIKER MOUNT"),
    ("D", 2, "30345-20", "PLATE (STRIKER BRACE)"),
    ("E", 1, "101229-4", "BAR ROUND 1/2 DIA.(STRIKER)"),
    ("F", 4, "103545-1", "GATE GUSSET"),
    ("G", 2, "102196-5", "PLATE (HINGE PLATE)"),
    ("H", 2, "671700", "HINGE SELF CLOSING 1-PAIR"),
    ("J", 1, "103546-1", "GATE STOP"),
]

DASH_P904225: list[tuple[str, int, str, str]] = [
    ("11", 2, "1002076-1", "PLATE"),
    ("10", 2, "1002038-1", "PLATE"),
    ("9", 2, "1002071-1", "PLATE"),
    ("8", 6, "11694-1", "PLATE"),
    ("7", 2, "1002068-1", "PLATE"),
    ("6", 1, "1002069-1", "PLATE"),
    ("5", 1, "P904245-1", "PLATE"),
    ("4", 2, "1002067-1", "PLATE"),
    ("3", 2, "P904231-1", "PLATE"),
    ("2", 2, "P904230-1", "PLATE"),
    ("1", 1, "P904226-1", "PLATE"),
]

DASH_1004611: list[tuple[str, int, str, str]] = [
    ("A", 1, "1004611-DWG", "DRAWING - STL PLATFORM ASSY"),
    ("B", 1, "1004612-1", "24 X 30 PLATFORM WELDMENT"),
    ("C", 2, "15062-2", ""),
    ("D", 8, "40002-8", ""),
    ("E", 8, "44013-7", ""),
    ("F", 8, "42005-1", ""),
    ("G", 2, "89047-1", ""),
    ("H", 1, "3649-7", ""),
    ("J", 1, "89028-1", ""),
    ("K", 1, "48049-1", ""),
    ("L", 4, "40014-1", ""),
    ("M", 4, "42005-17", ""),
    ("N", 1, "1004065-1", ""),
    ("P", 1, "89134-1", ""),
    ("Q", 1, "42005-3", ""),
    ("R", 1, "44013-6", ""),
    ("S", 1, "80054-1", '10" DOOR SEAL GASKET'),
    ("T", 1, "1004620-1", ""),
    ("W", 4, "12803-1", ""),
    ("X", 8, "44013-3", ""),
    ("Y", 4, "40006-7", ""),
    ("Z", 4, "42005-5", ""),
]
_1004611_OTHER = [
    ("U", "1004675-1", ""),
    ("V", "1004620-2", ""),
]


def _identity(rows: list[tuple[str, int, str, str]]) -> tuple[tuple[str, int], ...]:
    out: list[tuple[str, int]] = []
    for _item, qty, pn, _desc in rows:
        # Mirror lom_xlsx normalize (spaces dropped on prefixed stock).
        key = pn.replace(" ", "").upper() if pn[:1].isalpha() else pn
        out.append((key, qty))
    return tuple(out)


def rows_1001898() -> list[list[str]]:
    header = ["-5", "-4", "-3", "-2", "-1", "ITEM", "PART NO", "DESCRIPTION"]
    rows = [header]
    for item, qty, pn, desc in DASH_1001898:
        rows.append(["-", "-", "-", "-", str(qty), item, pn, desc])
    for item, pn, desc in _1001898_OTHER_DASH:
        rows.append(["-", "-", "-", "1", "-", item, pn, desc])
    rows.append(["-", "-", "-", "-", "20 PLCS", "AD", "1999999-1", "PAINT NOTE"])
    return rows


def rows_102728() -> list[list[str]]:
    rows = [["QTY", "ITEM", "PART NO", "DESCRIPTION"]]
    for item, qty, pn, desc in reversed(DASH_102728):
        rows.append([str(qty), item, pn, desc])
    return rows


def rows_1004747() -> list[list[str]]:
    header = ["-2", "-1", "ITEM", "PART NO", "DESCRIPTION"]
    dash1 = {item: (qty, pn, desc) for item, qty, pn, desc in DASH_1004747}
    other = {item: (pn, desc) for item, pn, desc in _1004747_OTHER}
    rows = [header]
    for n in range(17, 0, -1):
        item = str(n)
        if item in dash1:
            qty, pn, desc = dash1[item]
            rows.append(["-", str(qty), item, pn, desc])
        else:
            pn, desc = other[item]
            rows.append(["1", "-", item, pn, desc])
    return rows


def rows_28106() -> list[list[str]]:
    header = ["-4", "-3", "-2", "-1", "ITEM", "PART NO", "DESCRIPTION"]
    dash1 = {item: (qty, pn, desc) for item, qty, pn, desc in DASH_28106}
    other = {item: (dash, pn, desc) for item, dash, pn, desc in _28106_OTHER}
    rows = [header]
    for item in "ABCDEFGHJKLMNP":
        if item in dash1:
            qty, pn, desc = dash1[item]
            rows.append(["-", "-", "-", str(qty), item, pn, desc])
        else:
            dash, pn, desc = other[item]
            blank = ["-", "-", "-", "-"]
            blank[{"-4": 0, "-3": 1, "-2": 2}[dash]] = "1"
            rows.append([*blank, item, pn, desc])
    return rows


def rows_1007922() -> list[list[str]]:
    rows = [["-2", "-1", "ITEM", "PART NO", "DESCRIPTION"]]
    for item, qty, pn, desc in DASH_1007922:
        rows.append(["-", str(qty), item, pn, desc])
    for item, pn, desc in _1007922_OTHER:
        rows.append(["1", "-", item, pn, desc])
    rows.append(["-", "-", "S", "73207", "ADDED CONFIGURATION"])
    return rows


def rows_21727() -> list[list[str]]:
    rows = [["QTY", "ITEM", "PART NO", "DESCRIPTION"]]
    for item, qty, pn, desc in reversed(DASH_21727):
        rows.append([str(qty), item, pn, desc])
    rows.append(["-", "M", "61358", "REVISION BLOCK"])
    return rows


def rows_33612() -> list[list[str]]:
    rows = [["QTY", "ITEM", "PART NO", "DESCRIPTION"]]
    for item, qty, pn, desc in reversed(DASH_33612):
        rows.append([str(qty), item, pn, desc])
    rows.append(["-", "X", "56657", "FIRST RELEASE"])
    rows.append(["-", "BT", "97879", "PROPERTY OF TIME"])
    return rows


def rows_105098() -> list[list[str]]:
    # H is -1 only (blank on -2).
    rows = [["-2", "-1", "ITEM", "PART NO", "DESCRIPTION"]]
    for item, qty, pn, desc in reversed(DASH_105098):
        rows.append(["-", str(qty), item, pn, desc])
    return rows


def _105098_child_ignored() -> list[list[str]]:
    # Later-sheet bait — PNs Kyle named as not-LOM elsewhere. Must not roll up.
    return [
        ["QTY", "ITEM", "PART NO", "DESCRIPTION"],
        ["1", "A", "56657", "CHILD TABLE"],
        ["1", "B", "97879", "CHILD TABLE"],
        ["1", "C", "89176-1", "WELDING WIRE"],
    ]


def rows_103516() -> list[list[str]]:
    rows = [["-2", "-1", "ITEM", "PART NO", "DESCRIPTION"]]
    named = {item: (qty, pn, desc) for item, qty, pn, desc in DASH_103516}
    for n in range(27, 0, -1):
        item = str(n)
        qty, pn, desc = named[item]
        rows.append(["-", str(qty), item, pn, desc])
    return rows


def rows_103535() -> list[list[str]]:
    rows = [["QTY", "ITEM", "PART NO", "DESCRIPTION"]]
    for item, qty, pn, desc in reversed(DASH_103535):
        rows.append([str(qty), item, pn, desc])
    return rows


def rows_p904225() -> list[list[str]]:
    rows = [["P904225-1", "ITEM", "PART NO", "DESCRIPTION"]]
    named = {item: (qty, pn, desc) for item, qty, pn, desc in DASH_P904225}
    for n in range(11, 0, -1):
        item = str(n)
        qty, pn, desc = named[item]
        rows.append([str(qty), item, pn, desc])
    rows.append(["-", "12", "89176-1", "WELDING WIRE"])
    rows.append(["1", "13", "P904225-1", "WELDMENT"])
    return rows


def rows_1004611() -> list[list[str]]:
    rows = [["-2", "-1", "ITEM", "PART NO", "DESCRIPTION"]]
    for item, qty, pn, desc in DASH_1004611:
        qty_cell = '10"' if item == "S" else str(qty)
        rows.append(["-", qty_cell, item, pn, desc])
    for item, pn, desc in _1004611_OTHER:
        rows.append(["1", "-", item, pn, desc])
    return rows


@dataclass
class LomGold:
    part_key: str
    pn: int
    pcs: int
    title: str
    source: str
    builder: Any
    notes: str = ""
    extra_sheets: dict[str, list[list[str]]] = field(default_factory=dict)
    identity: tuple[tuple[str, int], ...] = ()
    child_identity: tuple[tuple[str, int], ...] = ()
    require_pn: tuple[str, ...] = ()
    forbid_pn: tuple[str, ...] = ()
    empty_l2: tuple[str, ...] = ()
    complete: bool = True
    gasket_pn: str = ""

    def drawn_rows(self) -> list[list[str]]:
        return self.builder()


def _gold(
    part_key: str,
    rows: list[tuple[str, int, str, str]],
    *,
    title: str,
    builder,
    notes: str = "",
    extra_sheets: dict[str, list[list[str]]] | None = None,
    child_rows: list[tuple[str, int, str, str]] | None = None,
    forbid_pn: tuple[str, ...] = (),
    empty_l2: tuple[str, ...] = (),
    complete: bool = True,
    pn: int | None = None,
    pcs: int | None = None,
    gasket_pn: str = "",
) -> LomGold:
    ident = _identity(rows)
    child_ident = _identity(child_rows) if child_rows else ()
    return LomGold(
        part_key=part_key,
        pn=pn if pn is not None else len(ident),
        pcs=pcs if pcs is not None else sum(q for _p, q in ident),
        title=title,
        source="identity",
        builder=builder,
        notes=notes,
        extra_sheets=extra_sheets or {},
        identity=ident,
        child_identity=child_ident,
        require_pn=tuple(p for p, _q in ident) + tuple(p for p, _q in child_ident),
        forbid_pn=forbid_pn,
        empty_l2=empty_l2,
        complete=complete,
        gasket_pn=gasket_pn,
    )


LOM_GOLD: list[LomGold] = [
    _gold(
        "102728-1",
        DASH_102728,
        title="102728-1",
        builder=rows_102728,
        notes="Full 51-row identity. A=460200, BB=102727-4×2.",
        forbid_pn=("102728-1",),
        pn=51,
        pcs=97,
    ),
    _gold(
        "1004747-1",
        DASH_1004747,
        title="1004747",
        builder=rows_1004747,
        notes="Dash trap: bare/-1 title uses column -1, never folder -2.",
        forbid_pn=("1004806-2", "11694-2", "25009-2"),
        pn=14,
        pcs=18,
    ),
    _gold(
        "28106-1",
        DASH_28106,
        title="28106-1",
        builder=rows_28106,
        notes="P/N/L are other-dash only.",
        forbid_pn=("16697-1", "16697-3", "16697-4"),
        pn=11,
        pcs=13,
    ),
    _gold(
        "1007922-1",
        DASH_1007922,
        title="1007922-1",
        builder=rows_1007922,
        notes="21750-2 / 21743-2 unused on -1. 73207 is not LOM.",
        forbid_pn=("21750-2", "21743-2", "73207"),
        pn=6,
        pcs=14,
    ),
    _gold(
        "21727-1",
        DASH_21727,
        title="21727-1",
        builder=rows_21727,
        notes="61358 is revision block, not LOM.",
        forbid_pn=("61358",),
        pn=11,
        pcs=16,
    ),
    _gold(
        "33612-1",
        DASH_33612,
        title="33612-1",
        builder=rows_33612,
        notes="A–W skip I/O. 56657 / 97879 omitted.",
        forbid_pn=("56657", "97879"),
        pn=21,
        pcs=47,
    ),
    _gold(
        "105098-1",
        DASH_105098,
        title="105098-1",
        builder=rows_105098,
        extra_sheets={"103603-1": _105098_child_ignored()},
        notes="Parent LOM only. H is -1 only. Later-sheet 103603-1 ignored.",
        forbid_pn=("56657", "97879", "89176-1"),
        pn=9,
        pcs=9,
    ),
    _gold(
        "103516",
        DASH_103516,
        title="103516",
        builder=rows_103516,
        extra_sheets={"103535-1": rows_103535()},
        child_rows=DASH_103535,
        notes="Parent 27/45; nested 103535-1 GATE WELDMENT rolls up 9/17.",
        pn=27,
        pcs=45,
    ),
    _gold(
        "P904225-1",
        DASH_P904225,
        title="P904225-1",
        builder=rows_p904225,
        notes="P904225-1 is the qty header, not a material row. 89176-1 omitted.",
        forbid_pn=("P904225-1", "89176-1"),
        pn=11,
        pcs=23,
    ),
    _gold(
        "1004611-1",
        DASH_1004611,
        title="1004611-1",
        builder=rows_1004611,
        notes="22 PN / 66 pcs + 10″ gasket on S (size, not 10 pieces).",
        forbid_pn=("1004620-2", "1004675-1"),
        pn=22,
        pcs=67,
        gasket_pn="80054-1",
    ),
    _gold(
        "1001898-1",
        DASH_1001898,
        title="1001898-1",
        builder=rows_1001898,
        notes="Live locked dash -1 part list.",
        forbid_pn=("1001899-1", "1999999-1"),
        pn=17,
        pcs=27,
    ),
]


CLASSIFY_CASES: list[tuple[str, str, str]] = [
    ("14500-1", "PEDESTAL TOP PLATE", "Component"),
    ("14501-1", "RESERVOIR TOP PLATE", "Cad"),
    ("1005966-1", "PEDESTAL BOTTOM PLATE", "Component"),
    ("9905-1", "MOUNTING PLATE, EMER POWER", "Cad"),
    ("1005940-1", "PEDESTAL GUSSET", "Cad"),
    ("1001880-2", "PEDESTAL TUBE", "Cad"),
    ("29860-3", "PEDESTAL BRACE ANGLE", "Linear"),
    ("29860-4", "PEDESTAL BRACE ANGLE", "Linear"),
    ("10081-2", "PEDESTAL HOSE TUBE", "Linear"),
    ("33637-1", "1 1/4 RETURN TUBE", "Linear"),
    ("50029-7", "1 1/4 90 STREET ELBOW", "Component"),
    ("50122-1", "1 1/4 NPT PIPE CAP", "Component"),
    ("50006-5", "3/4 NPT MAGNETIC PLUG", "Component"),
    ("8166-1", "FILLER NECK", "Component"),
    ("50030-5", "3/4 NPT COUPLING", "Component"),
    ("50115-7", "1 1/4 NPT NIPPLE X 4 LG.", "Component"),
    ("50137-5", "3/4 NPT HALF COUPLING", "Component"),
    ("21680-1", "HOSE GUARD", "Linear"),
    ("21679-1", "HOSEGUARD TUBE", "Linear"),
]


DESC_CASES: list[dict[str, Any]] = [
    {
        "kind": "cad",
        "part_no": "14500-1",
        "kwargs": {"thickness": 0.25, "grade": "A36", "width_in": 12, "length_in": 12},
        "want": '14500-1 - 1/4" A36 12 in x 12 in',
    },
    {
        "kind": "cad",
        "part_no": "21667-1",
        "kwargs": {
            "thickness": 0.375,
            "grade": "100K",
            "width_in": 10,
            "length_in": 9,
        },
        "want": '21667-1 - 3/8" 100K 10 in x 9 in',
    },
    {
        "kind": "cad_sheet",
        "part_no": "14501-1",
        "kwargs": {
            "thickness": 0.25,
            "grade": "A36",
            "width_in": 22.0,
            "length_in": 28.5,
            "noun": "RESERVOIR TOP PLATE",
        },
        "forbid": ("22", "28.5"),
        "contains": "RESERVOIR TOP PLATE",
    },
    {
        "kind": "linear",
        "part_no": "12689-1",
        "kwargs": {"sku": "RCT2 12X1 12X.065-A513", "length_in": 44.375},
        "want": "12689-1 - RCT2 12X1 12X.065-A513 - 44.375",
    },
    {
        "kind": "linear",
        "part_no": "12368-2",
        "kwargs": {"sku": "RCT2 2X2X.120-A513", "length_in": 12.25},
        "want": "12368-2 - RCT2 2X2X.120-A513 - 12.25",
    },
    {
        "kind": "component",
        "part_no": "50115-7",
        "kwargs": {"name": "50115-7 1 1/4 NPT NIPPLE X 4 LG."},
        "want": "1 1/4 NPT NIPPLE X 4 LG.",
    },
    {
        "kind": "assembly",
        "part_no": "1001898-1",
        "kwargs": {"title": "PEDESTAL WELDMENT"},
        "want": "1001898-1 - PEDESTAL WELDMENT",
    },
]


def write_gold_workbook(gold: LomGold, dest: Path | None = None) -> Path:
    dest = dest or (FIXTURE_DIR / f"{gold.part_key}-LOM.xlsx")
    dest.parent.mkdir(parents=True, exist_ok=True)
    write_lom_xlsx(
        dest,
        gold.drawn_rows(),
        part_key=gold.part_key,
        bom_config="1",
        extra_sheets=gold.extra_sheets or None,
    )
    return dest


def write_all_gold_workbooks(dest_dir: Path | None = None) -> list[Path]:
    folder = dest_dir or FIXTURE_DIR
    return [write_gold_workbook(g, folder / f"{g.part_key}-LOM.xlsx") for g in LOM_GOLD]


def write_empty_l2_workbook(dest: Path | None = None) -> Path:
    dest = dest or (FIXTURE_DIR / "empty-l2-LOM.xlsx")
    parent = [
        ["-1", "ITEM", "PART NO", "DESCRIPTION"],
        ["1", "A", "99999-1", "GATE WELDMENT"],
        ["1", "B", "99998-1", "TOP PLATE"],
    ]
    empty_child = [["-1", "ITEM", "PART NO", "DESCRIPTION"]]
    write_lom_xlsx(
        dest,
        parent,
        part_key="99999-1",
        extra_sheets={"99999-1": empty_child},
    )
    return dest


if __name__ == "__main__":
    paths = write_all_gold_workbooks()
    paths.append(write_empty_l2_workbook())
    for path in paths:
        print(path)
