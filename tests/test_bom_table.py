"""Table-first LIST OF MATERIAL grid — 102728-1 Time-style ground truth."""

from __future__ import annotations

from pathlib import Path

from quote_core.bom import (
    BomResult,
    BomRow,
    _native_cell_table_is_complete,
    _parse_material_list_on_page,
    _parse_qty_item_part_hits,
    _vote_bom_rows,
    extract_bom,
    extract_bom_from_native_mac,
    extract_bom_from_ocr_time_style,
)
from quote_core.bom_table import (
    detect_material_list_header,
    harvest_material_list_lines,
    harvest_ocr_row_strips,
    is_material_list_item,
    material_list_header_seen,
    parse_material_list_cells,
    parse_material_list_text,
    parse_material_list_words,
    parse_ocr_row_strip,
    pick_best_material_list,
    recover_time_part_no,
    text_has_material_list_grid,
    time_item_letters,
    union_sticky_harvest,
)

# Ground truth: Time 102728-1 WELDMENT, PLATFORM — 51 balloons, skip I/O.
_THROUGH = "BC"
_BB_PART = "102727-4"
_BB_DESC = "TUBE, ROUND"

# Kyle 102728-1 working truth (A at bottom on the page). 51 PNs, 97 pcs.
# Treat as truth until Kyle corrects a qty.
_KYLE_102728_1: list[tuple[str, int, str, str]] = [
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


def _platform_items() -> list[str]:
    items = time_item_letters(through=_THROUGH)
    assert len(items) == 51
    return items


def _platform_cell_rows(*, drop: set[str] | None = None) -> list[list[str]]:
    drop = drop or set()
    rows = [["QTY", "ITEM", "PART NO.", "DESCRIPTION"]]
    for i, item in enumerate(_platform_items()):
        if item in drop:
            continue
        if item == "BB":
            rows.append(["2", "BB", _BB_PART, _BB_DESC])
        else:
            rows.append(["1", item, f"1028{i:02d}-1", f"COMPONENT {item}"])
    return rows


def _platform_table_text(*, drop: set[str] | None = None) -> str:
    lines = [
        "WELDMENT, PLATFORM",
        "102728-1",
        "TIME MANUFACTURING",
        "SHEET 1 OF 2",
        "LIST OF MATERIAL",
    ]
    for row in _platform_cell_rows(drop=drop):
        lines.append(" | ".join(row))
    return "\n".join(lines)


def _assert_kyle_102728_1(bom) -> None:
    assert len(bom.rows) == 51, [f"{r.item}:{r.part_no}×{r.qty}" for r in bom.rows]
    assert sum(r.qty for r in bom.rows) == 97
    assert bom.piece_count == 97
    by_item = {r.item: r for r in bom.rows}
    for item, qty, pn, _desc in _KYLE_102728_1:
        assert item in by_item, item
        assert by_item[item].part_no == pn, (item, by_item[item].part_no, pn)
        assert by_item[item].qty == qty, (item, by_item[item].qty, qty)
    assert by_item["A"].part_no == "460200"
    assert by_item["Z"].part_no == "460320"
    assert by_item["BB"].part_no == _BB_PART and by_item["BB"].qty == 2


def _assert_kyle_xlsx(path: Path, expected: list[tuple[str, int, str, str]]) -> None:
    """Proof method: the emitted sheet must match every letter, PN, and qty."""
    from quote_core.bom_xlsx import read_lom_xlsx

    header, sheet = read_lom_xlsx(path)
    assert header == ["QTY", "ITEM", "PART NO", "DESCRIPTION"]
    assert len(sheet) == len(expected)
    assert sum(int(r["QTY"]) for r in sheet) == sum(q for _i, q, _p, _d in expected)
    by_item = {r["ITEM"]: r for r in sheet}
    for item, qty, pn, _desc in expected:
        assert item in by_item, item
        assert by_item[item]["PART NO"] == pn, (item, by_item[item]["PART NO"], pn)
        assert int(by_item[item]["QTY"]) == qty, (item, by_item[item]["QTY"], qty)


# Kyle 28106-1 working truth (A at bottom; quote -1 only). 11 PNs, 13 pcs.
# Other-dash tubes L/N/P must not appear on a -1 takeoff.
_KYLE_28106_1: list[tuple[str, int, str, str]] = [
    ("A", 1, "16697-2", "LOWER BOOM TUBE 91 1/8 LG."),
    ("B", 1, "26732-1", "CYLINDER MOUNT PLATE W/ 3/8 HOLES."),
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
_KYLE_28106_OTHER_DASH: list[tuple[str, str, str, str]] = [
    ("L", "-2", "16697-1", "LOWER BOOM TUBE 55 LG."),
    ("N", "-3", "16697-3", "LOWER BOOM TUBE"),
    ("P", "-4", "16697-4", "LOWER BOOM TUBE"),
]
_KYLE_28106_LETTERS = [c for c in "ABCDEFGHJKLMNP"]  # A–P skip I and O


def _kyle_28106_cell_rows() -> list[list[str]]:
    """14-row -4|-3|-2|-1 grid. Empty qty cells stay blank."""
    dash1 = {item: (qty, pn, desc) for item, qty, pn, desc in _KYLE_28106_1}
    other = {item: (dash, pn, desc) for item, dash, pn, desc in _KYLE_28106_OTHER_DASH}
    rows = [["-4", "-3", "-2", "-1", "ITEM", "PART NO.", "DESCRIPTION"]]
    for item in _KYLE_28106_LETTERS:
        q4 = q3 = q2 = q1 = ""
        if item in dash1:
            qty, pn, desc = dash1[item]
            q1 = str(qty)
        else:
            dash, pn, desc = other[item]
            if dash == "-4":
                q4 = "1"
            elif dash == "-3":
                q3 = "1"
            elif dash == "-2":
                q2 = "1"
        rows.append([q4, q3, q2, q1, item, pn, desc])
    return rows


def _assert_kyle_28106_1(bom) -> None:
    assert len(bom.rows) == 11, [f"{r.item}:{r.part_no}×{r.qty}" for r in bom.rows]
    assert sum(r.qty for r in bom.rows) == 13
    assert bom.piece_count == 13
    by_item = {r.item: r for r in bom.rows}
    for item, qty, pn, _desc in _KYLE_28106_1:
        assert item in by_item, item
        assert by_item[item].part_no == pn, (item, by_item[item].part_no, pn)
        assert by_item[item].qty == qty, (item, by_item[item].qty, qty)
    parts = {r.part_no for r in bom.rows}
    assert "16697-1" not in parts
    assert "16697-3" not in parts
    assert "16697-4" not in parts
    assert "L" not in by_item and "N" not in by_item and "P" not in by_item
    assert by_item["A"].part_no == "16697-2" and by_item["A"].qty == 1
    assert by_item["G"].qty == 2 and by_item["J"].qty == 2


# Kyle 1004747-1 confirmed against 1004747-1-LOM.xlsx + drawing.
# Items 1–17 (not A–Z). Item 1 at the bottom. Qty columns 1004747-1 / 1004747-2.
# Dash -1: 14 unique PNs / 18 pcs. 16/14/13 are -2 only.
_KYLE_1004747_1: list[tuple[str, int, str, str]] = [
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
_KYLE_1004747_OTHER_DASH: list[tuple[str, str, str]] = [
    ("16", "1004806-2", ""),
    ("14", "11694-2", ""),
    ("13", "25009-2", ""),
]


def _kyle_1004747_cell_rows() -> list[list[str]]:
    """17-row numbered grid. Item 1 at the bottom. Empty -1 qty stays blank."""
    dash1 = {item: (qty, pn, desc) for item, qty, pn, desc in _KYLE_1004747_1}
    other = {item: (pn, desc) for item, pn, desc in _KYLE_1004747_OTHER_DASH}
    rows = [["1004747-1", "1004747-2", "ITEM", "PART NO.", "DESCRIPTION", "NOTES"]]
    for n in range(17, 0, -1):
        item = str(n)
        q1 = q2 = ""
        if item in dash1:
            qty, pn, desc = dash1[item]
            q1 = str(qty)
        else:
            pn, desc = other[item]
            q2 = "1"
        rows.append([q1, q2, item, pn, desc, ""])
    return rows


def _assert_kyle_1004747_1(bom) -> None:
    assert len(bom.rows) == 14, [f"{r.item}:{r.part_no}×{r.qty}" for r in bom.rows]
    assert sum(r.qty for r in bom.rows) == 18
    assert bom.piece_count == 18
    by_item = {str(r.item): r for r in bom.rows}
    for item, qty, pn, _desc in _KYLE_1004747_1:
        assert item in by_item, item
        assert by_item[item].part_no == pn, (item, by_item[item].part_no, pn)
        assert by_item[item].qty == qty, (item, by_item[item].qty, qty)
    parts = {r.part_no for r in bom.rows}
    assert "1004806-2" not in parts
    assert "11694-2" not in parts
    assert "25009-2" not in parts
    assert "1004747-1" not in parts
    assert "1004773-1" in parts and "1004743-1" in parts
    assert "16" not in by_item and "14" not in by_item and "13" not in by_item
    assert by_item["1"].part_no == "25060-6" and by_item["1"].qty == 1
    assert by_item["17"].part_no == "6993-1" and by_item["17"].qty == 2
    assert by_item["6"].qty == 2 and by_item["5"].qty == 2


# Kyle 1004611-1 confirmed against 1004611-1-LOM.xlsx.
# 24 lettered rows A–Z skip I/O. A at the bottom. Qty cols left=-2 right=-1.
# Dash -1: 22 PNs / 66 pcs + 10″ gasket on S 80054-1.
# U 1004675-1 and V 1004620-2 are -2 only. A 1004611-DWG is a real LOM row.
# Remaining -1 PNs were not listed — do not invent them. Live bar is 22/66.
_KYLE_1004611_1_PN_COUNT = 22
_KYLE_1004611_1_PCS = 66
_KYLE_1004611_LETTERS = [c for c in "ABCDEFGHJKLMNPQRSTUVWXYZ"]
_KYLE_1004611_1: list[tuple[str, int, str, str]] = [
    ("A", 1, "1004611-DWG", ""),
    ("S", 1, "80054-1", '10" GASKET'),
]
_KYLE_1004611_OTHER_DASH: list[tuple[str, str, str]] = [
    ("U", "1004675-1", ""),
    ("V", "1004620-2", ""),
]


def _kyle_1004611_cell_rows() -> list[list[str]]:
    """24-row -2|-1 grid. A at the bottom when reversed. Empty -1 omits the row."""
    dash1 = {item: (qty, pn, desc) for item, qty, pn, desc in _KYLE_1004611_1}
    other = {item: (pn, desc) for item, pn, desc in _KYLE_1004611_OTHER_DASH}
    rows = [["-2", "-1", "ITEM", "PART NO.", "DESCRIPTION"]]
    for item in _KYLE_1004611_LETTERS:
        q2 = q1 = ""
        pn = desc = ""
        if item in dash1:
            qty, pn, desc = dash1[item]
            q1 = str(qty)
        elif item in other:
            pn, desc = other[item]
            q2 = "1"
        else:
            # Letter is on the -1 takeoff. PN not listed — do not invent.
            q1 = "1"
        rows.append([q2, q1, item, pn, desc])
    return rows


def _assert_kyle_1004611_1(bom) -> None:
    by_item = {r.item: r for r in bom.rows}
    parts = {r.part_no for r in bom.rows}
    assert by_item["A"].part_no == "1004611-DWG", by_item.get("A")
    assert by_item["A"].qty == 1
    assert by_item["S"].part_no == "80054-1"
    assert "GASKET" in by_item["S"].description.upper()
    assert "10" in by_item["S"].description
    assert "U" not in by_item and "V" not in by_item
    assert "1004620-2" not in parts
    assert "1004675-1" not in parts
    assert "1004611-1" not in parts
    assert "1004611-DWG" in parts
    assert "80054-1" in parts


# Kyle P904225-1 confirmed against P904225-1-LOM.xlsx.
# 11 numeric items (not A–Z). Item 1 at the bottom.
# Qty header is P904225-1 (also the title DWG) — not a BOM row.
# 11 PNs / 23 pcs. 89176-1 is a welding-wire note — omit.
# Documented children 89100-1 / P904226-1 stay. Remaining PNs were not
# listed — do not invent them. Live bar is 11/23. Item numbers on the
# documented pair are fixture slots, not a live Excel claim.
_KYLE_P904225_1_PN_COUNT = 11
_KYLE_P904225_1_PCS = 23
_KYLE_P904225_1: list[tuple[str, int, str, str]] = [
    ("1", 1, "89100-1", "TUBE"),
    ("2", 1, "P904226-1", "SUPPORT"),
]


def _kyle_p904225_cell_rows() -> list[list[str]]:
    """11-row numbered grid. Item 1 at the bottom. Header PN is not a row."""
    named = {item: (qty, pn, desc) for item, qty, pn, desc in _KYLE_P904225_1}
    rows = [["P904225-1", "ITEM", "PART NO.", "DESCRIPTION"]]
    for n in range(11, 0, -1):
        item = str(n)
        if item in named:
            qty, pn, desc = named[item]
            rows.append([str(qty), item, pn, desc])
        else:
            # Item is on the takeoff. PN not listed — do not invent.
            rows.append(["1", item, "", ""])
    rows.append(["1", "12", "89176-1", "WELDING WIRE"])
    rows.append(["1", "13", "P904225-1", "WELDMENT"])
    return rows


def _assert_kyle_p904225_1(bom) -> None:
    parts = {str(r.part_no or "") for r in bom.rows}
    by_item = {str(r.item): r for r in bom.rows}
    assert "P904225-1" not in parts
    assert "904225-1" not in parts
    assert "89176-1" not in parts
    assert all(str(r.item).isdigit() for r in bom.rows)
    assert all(1 <= int(r.item) <= 11 for r in bom.rows)
    assert "12" not in by_item and "13" not in by_item
    assert "89100-1" in parts
    assert any("904226" in p for p in parts)


# Kyle 103516 confirmed against 103516-LOM.xlsx.
# 27 numeric items (not A–Z). Item 1 at the bottom. Qty cols left=-2 right=-1.
# Dash -1: 27 PNs / 45 pcs including 103535-1 GATE WELDMENT.
# Item 27 40002-2 is on -1 only. Remaining PNs were not listed — do not invent.
# Live bar is 27/45. Item number on 103535-1 is a fixture slot, not a live claim.
_KYLE_103516_PN_COUNT = 27
_KYLE_103516_PCS = 45
_KYLE_103516: list[tuple[str, int, str, str]] = [
    ("1", 1, "103535-1", "GATE WELDMENT"),
    ("27", 1, "40002-2", ""),
]


def _kyle_103516_cell_rows() -> list[list[str]]:
    """27-row numbered -2|-1 grid. Item 27 is -1 only. Empty PN not invented."""
    named = {item: (qty, pn, desc) for item, qty, pn, desc in _KYLE_103516}
    rows = [["-2", "-1", "ITEM", "PART NO.", "DESCRIPTION"]]
    for n in range(27, 0, -1):
        item = str(n)
        q2 = q1 = ""
        pn = desc = ""
        if item in named:
            qty, pn, desc = named[item]
            q1 = str(qty)
        else:
            q1 = "1"
        rows.append([q2, q1, item, pn, desc])
    return rows


def _assert_kyle_103516(bom) -> None:
    parts = {str(r.part_no or "") for r in bom.rows}
    by_item = {str(r.item): r for r in bom.rows}
    assert "103516-1" not in parts
    assert "103516" not in parts
    assert "1035371" not in parts
    assert "103535-1" in parts
    assert "GATE" in by_item["1"].description.upper()
    assert "WELDMENT" in by_item["1"].description.upper()
    assert by_item["1"].part_no == "103535-1"
    assert "27" in by_item
    assert by_item["27"].part_no == "40002-2"
    assert by_item["27"].qty == 1
    assert all(str(r.item).isdigit() for r in bom.rows)
    assert all(1 <= int(r.item) <= 27 for r in bom.rows)


# Kyle 21727-1 confirmed against 21727-1-LOM.xlsx.
# Single QTY column (blank dash). Letters A–L skip I (11 letters; O is after L).
# 11 PNs / 16 pcs. 61358 is not a weld part. Remaining PNs were not listed —
# do not invent them. Live bar is 11/16. Item letters on the documented pair
# are fixture slots, not a live Excel claim.
_KYLE_21727_1_PN_COUNT = 11
_KYLE_21727_1_PCS = 16
_KYLE_21727_LETTERS = [c for c in "ABCDEFGHJKL"]
_KYLE_21727_1: list[tuple[str, int, str, str]] = [
    ("A", 1, "16697-1", "TUBE, SHORT"),
    ("B", 1, "16697-2", "TUBE, LONG"),
]


def _kyle_21727_cell_rows() -> list[list[str]]:
    """11-row QTY|ITEM|PN grid. A at the bottom when reversed. 61358 is extra junk."""
    named = {item: (qty, pn, desc) for item, qty, pn, desc in _KYLE_21727_1}
    rows = [["QTY", "ITEM", "PART NO.", "DESCRIPTION"]]
    for item in _KYLE_21727_LETTERS:
        if item in named:
            qty, pn, desc = named[item]
            rows.append([str(qty), item, pn, desc])
        else:
            # Letter is on the takeoff. PN not listed — do not invent.
            rows.append(["1", item, "", ""])
    rows.append(["1", "M", "61358", "REVISION NOTE"])
    return rows


def _assert_kyle_21727_1(bom) -> None:
    parts = {str(r.part_no or "") for r in bom.rows}
    by_item = {str(r.item): r for r in bom.rows}
    assert by_item["A"].part_no == "16697-1"
    assert by_item["A"].qty == 1
    assert "TUBE" in by_item["A"].description.upper()
    assert "SHORT" in by_item["A"].description.upper()
    assert by_item["B"].part_no == "16697-2"
    assert by_item["B"].qty == 1
    assert "LONG" in by_item["B"].description.upper()
    assert "61358" not in parts
    assert "21727-1" not in parts
    assert "21727" not in parts
    assert "I" not in by_item
    assert "M" not in by_item
    assert all(str(r.item) in _KYLE_21727_LETTERS for r in bom.rows)
    assert "16697-1" in parts and "16697-2" in parts


# Kyle 1007922-1 confirmed against 1007922-1-LOM.xlsx.
# Dash -1 of -2|-1: 6 PNs / 14 pcs including 14149-1×4 and 1007830-1×2.
# 21750-2 / 21743-2 are other-dash only. 73207 is not a weld part.
# Remaining PNs were not listed — do not invent them. Live bar is 6/14.
# Item letters on the documented children are fixture slots, not a live claim.
_KYLE_1007922_1_PN_COUNT = 6
_KYLE_1007922_1_PCS = 14
_KYLE_1007922_1: list[tuple[str, int, str, str]] = [
    ("A", 1, "1007800-1", "TUBE"),
    ("B", 4, "14149-1", "FILLER"),
    ("C", 2, "1007830-1", "OUTRIGGER LEG"),
    ("D", 1, "6993-1", "HOSE GUIDE"),
    ("N", 1, "28275-1", "TUBE"),
]
_KYLE_1007922_OTHER_DASH: list[tuple[str, str, str]] = [
    ("L", "21750-2", ""),
    ("P", "21743-2", ""),
]


def _kyle_1007922_cell_rows() -> list[list[str]]:
    """-2|-1 grid. A at the bottom when reversed. Empty -1 omits the row."""
    rows = [["-2", "-1", "ITEM", "PART NO.", "DESCRIPTION"]]
    for item, qty, pn, desc in _KYLE_1007922_1:
        rows.append(["", str(qty), item, pn, desc])
    for item, pn, desc in _KYLE_1007922_OTHER_DASH:
        rows.append(["1", "", item, pn, desc])
    rows.append(["", "1", "S", "73207", "ADDED CONFIGURATION"])
    return rows


def _assert_kyle_1007922_1(bom) -> None:
    parts = {str(r.part_no or "") for r in bom.rows}
    by_item = {str(r.item): r for r in bom.rows}
    assert by_item["B"].part_no == "14149-1"
    assert by_item["B"].qty == 4
    assert "FILLER" in by_item["B"].description.upper()
    assert by_item["C"].part_no == "1007830-1"
    assert by_item["C"].qty == 2
    assert "OUTRIGGER" in by_item["C"].description.upper()
    assert by_item["A"].part_no == "1007800-1"
    assert by_item["D"].part_no == "6993-1"
    assert by_item["N"].part_no == "28275-1"
    assert "14149-1" in parts and "1007830-1" in parts
    assert "1007800-1" in parts and "6993-1" in parts and "28275-1" in parts
    assert "21750-2" not in parts
    assert "21743-2" not in parts
    assert "73207" not in parts
    assert "1007922-1" not in parts
    assert "1007922" not in parts
    assert "L" not in by_item and "P" not in by_item and "S" not in by_item


# Kyle 33612-1 confirmed against 33612-1-LOM.xlsx.
# Single QTY column (blank dash). Letters A–W skip I/O (21 letters).
# 21 PNs / 47 pcs. 56657 / 97879 are not weld parts. Keep 282xx.
# Remaining PNs were not listed — do not invent them. Live bar is 21/47.
# Item letters on the documented children are fixture slots, not a live claim.
_KYLE_33612_1_PN_COUNT = 21
_KYLE_33612_1_PCS = 47
_KYLE_33612_LETTERS = [c for c in "ABCDEFGHJKLMNPQRSTUVW"]
_KYLE_33612_282XX = (
    "28275-1",
    "28275-2",
    "28275-3",
    "28276-1",
    "28281-1",
    "28282-1",
    "28283-1",
)
_KYLE_33612_1: list[tuple[str, int, str, str]] = [
    ("A", 1, "89176-1", "TUBE"),
    ("M", 1, "94560", "GATE, FABRICATION"),
    ("N", 1, "28275-1", "TUBE"),
    ("P", 1, "28275-2", "TUBE"),
    ("Q", 1, "28275-3", "TUBE"),
    ("R", 1, "28276-1", "TUBE"),
    ("S", 1, "28281-1", "TUBE"),
    ("T", 1, "28282-1", "TUBE"),
    ("U", 1, "28283-1", "TUBE"),
]


def _kyle_33612_cell_rows() -> list[list[str]]:
    """21-row QTY|ITEM|PN grid. A at the bottom when reversed. 56657/97879 are junk."""
    named = {item: (qty, pn, desc) for item, qty, pn, desc in _KYLE_33612_1}
    rows = [["QTY", "ITEM", "PART NO.", "DESCRIPTION"]]
    for item in _KYLE_33612_LETTERS:
        if item in named:
            qty, pn, desc = named[item]
            rows.append([str(qty), item, pn, desc])
        else:
            # Letter is on the takeoff. PN not listed — do not invent.
            rows.append(["1", item, "", ""])
    rows.append(["1", "X", "56657", "FIRST RELEASE TO PRODUCTION"])
    rows.append(["1", "BT", "97879", "THIS DRAWING IS THE PROPERTY OF TIME"])
    return rows


def _assert_kyle_33612_1(bom) -> None:
    parts = {str(r.part_no or "") for r in bom.rows}
    by_item = {str(r.item): r for r in bom.rows}
    assert by_item["A"].part_no == "89176-1"
    assert by_item["A"].qty == 1
    assert "TUBE" in by_item["A"].description.upper()
    assert "WIRE" not in by_item["A"].description.upper()
    assert by_item["M"].part_no == "94560"
    assert "GATE" in by_item["M"].description.upper()
    assert any(str(p).startswith("282") for p in parts)
    for pn in _KYLE_33612_282XX:
        assert pn in parts, pn
    assert by_item["N"].part_no == "28275-1"
    assert by_item["P"].part_no == "28275-2"
    assert "56657" not in parts
    assert "97879" not in parts
    assert "33612-1" not in parts
    assert "33612" not in parts
    assert "I" not in by_item and "O" not in by_item
    assert "X" not in by_item and "BT" not in by_item
    assert all(str(r.item) in _KYLE_33612_LETTERS for r in bom.rows)


# Kyle 105098-1 confirmed against 105098-1-LOM.xlsx.
# Parent LOM only: letters A–J skip I (9 letters). 9 PNs / 9 pcs.
# Do not ingest later-sheet 103603-1 child tables as this job's BOM.
# Remaining PNs were not listed — do not invent them. Live bar is 9/9.
_KYLE_105098_1_PN_COUNT = 9
_KYLE_105098_1_PCS = 9
_KYLE_105098_LETTERS = [c for c in "ABCDEFGHJ"]
_KYLE_105098_1: list[tuple[str, int, str, str]] = []


def _kyle_105098_cell_rows() -> list[list[str]]:
    """9-row QTY|ITEM|PN parent grid. A at the bottom when reversed."""
    rows = [["QTY", "ITEM", "PART NO.", "DESCRIPTION"]]
    for item in _KYLE_105098_LETTERS:
        # Letter is on the parent takeoff. PN not listed — do not invent.
        rows.append(["1", item, "", ""])
    return rows


def _assert_kyle_105098_1(bom) -> None:
    parts = {str(r.part_no or "") for r in bom.rows}
    by_item = {str(r.item): r for r in bom.rows}
    assert "103603-1" not in parts
    assert "103603" not in parts
    assert "105098-1" not in parts
    assert "105098" not in parts
    assert "I" not in by_item
    assert "K" not in by_item
    assert "M" not in by_item
    assert all(str(r.item) in _KYLE_105098_LETTERS for r in bom.rows)


def test_kyle_grid_writes_four_column_xlsx(tmp_path: Path):
    """Same 51-row grid Kyle confirmed — QTY / ITEM / PART NO / DESCRIPTION."""
    from quote_core.bom import BomResult, BomRow
    from quote_core.bom_xlsx import read_lom_xlsx, write_lom_xlsx

    rows = [
        BomRow(item=item, qty=qty, part_no=pn, description=desc)
        for item, qty, pn, desc in reversed(_KYLE_102728_1)
    ]
    path = write_lom_xlsx(tmp_path / "102728-1-LOM.xlsx", rows)
    header, sheet = read_lom_xlsx(path)
    assert header == ["QTY", "ITEM", "PART NO", "DESCRIPTION"]
    assert len(sheet) == 51
    assert sum(int(r["QTY"]) for r in sheet) == 97
    assert sheet[0]["ITEM"] == "A" and sheet[0]["PART NO"] == "460200"
    assert int(sheet[0]["QTY"]) == 1
    bb = next(r for r in sheet if r["ITEM"] == "BB")
    assert bb["PART NO"] == _BB_PART and int(bb["QTY"]) == 2
    _assert_kyle_102728_1(
        BomResult(
            rows=[
                BomRow(
                    item=r["ITEM"],
                    qty=int(r["QTY"]),
                    part_no=r["PART NO"],
                    description=r["DESCRIPTION"],
                )
                for r in sheet
            ]
        )
    )


def test_kyle_102728_1_a_at_bottom_51_pn_97_pcs():
    """Working truth until Kyle corrects a qty. A is at the bottom of the clip."""
    assert len(_KYLE_102728_1) == 51
    assert sum(q for _i, q, _p, _d in _KYLE_102728_1) == 97

    cells = [["QTY", "ITEM", "PART NO.", "DESCRIPTION"]]
    for item, qty, pn, desc in _KYLE_102728_1:
        cells.append([str(qty), item, pn, desc])
    _assert_kyle_102728_1(parse_material_list_cells(cells))

    text_lines = [
        "WELDMENT, PLATFORM",
        "102728-1",
        "TIME MANUFACTURING",
        "LIST OF MATERIAL",
        "QTY | ITEM | PART NO. | DESCRIPTION",
    ]
    for item, qty, pn, desc in _KYLE_102728_1:
        text_lines.append(f"{qty} | {item} | {pn} | {desc}")
    _assert_kyle_102728_1(parse_material_list_text("\n".join(text_lines)))
    _assert_kyle_102728_1(extract_bom(text="\n".join(text_lines)))
    # Filled -1 is harmless on a single QTY column; it is not required.
    _assert_kyle_102728_1(extract_bom(text="\n".join(text_lines), bom_config="-1"))

    # Page-1 clip: BC at the top, A at the bottom, header below.
    strips = [
        f"{qty} {item} {pn} {desc}"
        for item, qty, pn, desc in reversed(_KYLE_102728_1)
    ]
    strips.append("QTY | ITEM | PART NO. | DESCRIPTION")
    harvested = harvest_ocr_row_strips(strips)
    _assert_kyle_102728_1(harvested)

    # Unread letters: do not label the top PN as A (that was Z=460320).
    unread = [
        f"{qty} {pn} {desc}" for item, qty, pn, desc in reversed(_KYLE_102728_1)
    ]
    unread_bom = harvest_ocr_row_strips(unread)
    by_item = {r.item: r for r in unread_bom.rows}
    assert by_item["A"].part_no == "460200"
    assert by_item["Z"].part_no == "460320"
    assert by_item["BB"].part_no == _BB_PART and by_item["BB"].qty == 2
    assert sum(r.qty for r in unread_bom.rows) == 97
    assert not any("after PN set" in n and "letters after" in n for n in unread_bom.notes)


def test_fedf06b_live_mismatch_recovers_kyle_grid():
    """fedf06b laptop: 51 PNs / 65 pcs, A=460320. Grid letters + qty cells → 97."""
    unread_letters = {"A", "F", "J", "Q"}
    missing_qty = {
        "E", "G", "K", "M", "P", "S", "T", "U", "V", "W", "X", "Y", "Z",
        "AA", "AC", "AD", "AE", "AF", "AL", "AX",
    }
    blob_strips: list[str] = []
    cell_strips: list[str] = []
    for item, qty, pn, desc in reversed(_KYLE_102728_1):
        cell_strips.append(f"{qty} | {item} | {pn} | {desc}")
        if item == "Z":
            blob_strips.append(f"A {pn} {desc}")
        elif item in unread_letters:
            blob_strips.append(f"{pn} {desc}")
        elif item in missing_qty:
            blob_strips.append(f"{item} {pn} {desc}")
        else:
            blob_strips.append(f"{qty} {item} {pn} {desc}")
    blob_strips.append("QTY | ITEM | PART NO. | DESCRIPTION")
    cell_strips.append("QTY | ITEM | PART NO. | DESCRIPTION")

    first = harvest_ocr_row_strips(blob_strips)
    by_first = {r.item: r for r in first.rows}
    assert len(first.rows) == 51
    assert by_first["A"].part_no == "460200"
    assert by_first["Z"].part_no == "460320"
    assert by_first["BB"].part_no == _BB_PART and by_first["BB"].qty == 2
    assert any("A at bottom" in n or "grid bands" in n for n in first.notes)
    assert not any("letters after PN set" in n for n in first.notes)
    aa = next(r for r in first.rows if r.part_no == "460330")
    assert int(aa.qty) != 5

    cells = harvest_ocr_row_strips(cell_strips)
    _assert_kyle_102728_1(cells)
    assert cells.piece_count == 97

    united = union_sticky_harvest(first, cells)
    _assert_kyle_102728_1(united)
    assert united.piece_count == 97


# Live 791587b on 102728- Weldment.pdf: letters+PNs perfect, qty column mostly unread.
_791587B_EXACT_QTY2 = frozenset({"P", "AH", "AN", "AP", "AQ", "AT", "AZ", "BB"})
_791587B_WRONG_QTY = {"V": 4, "W": 1, "X": 1, "AC": 2, "AL": 2, "BA": 4}


def _791587b_live_qty_strips() -> list[str]:
    """Cell strips as the laptop actually read them. Empty qty stays blank."""
    lines: list[str] = []
    for item, _qty, pn, desc in reversed(_KYLE_102728_1):
        if item in _791587B_EXACT_QTY2:
            q = "2"
        elif item in _791587B_WRONG_QTY:
            q = str(_791587B_WRONG_QTY[item])
        else:
            q = ""
        lines.append(f"{q} | {item} | {pn} | {desc}")
    lines.append("QTY | ITEM | PART NO. | DESCRIPTION")
    return lines


def test_791587b_live_qty_column_unread_is_takeoff_fail():
    """Letters/PNs 51; sum(row.qty)=30 not 97. Do not ship. Do not count 0 as 1."""
    live = harvest_ocr_row_strips(_791587b_live_qty_strips())
    assert len(live.rows) == 51
    by_item = {r.item: r for r in live.rows}
    assert by_item["A"].part_no == "460200" and by_item["A"].qty == 0
    assert by_item["BB"].part_no == _BB_PART and by_item["BB"].qty == 2
    for item in _791587B_EXACT_QTY2:
        assert by_item[item].qty == 2, item
    raw_sum = sum(int(r.qty or 0) for r in live.rows)
    assert raw_sum == 30
    assert live.piece_count == 30
    assert live.piece_count != 67
    assert live.piece_count != 97
    joined = " ".join(live.notes).lower()
    assert "takeoff fail" in joined
    assert "not proof" in joined
    assert live.confidence <= 0.45

    cells = [
        f"{qty} | {item} | {pn} | {desc}"
        for item, qty, pn, desc in reversed(_KYLE_102728_1)
    ]
    cells.append("QTY | ITEM | PART NO. | DESCRIPTION")
    recovered = harvest_ocr_row_strips(cells)
    _assert_kyle_102728_1(recovered)
    assert recovered.piece_count == 97
    assert recovered.confidence > 0.45
    assert "takeoff fail" not in " ".join(recovered.notes).lower()
    # 51/30 unread must not beat 51/97 when both candidates exist.
    best = pick_best_material_list([live, recovered])
    assert best.piece_count == 97
    _assert_kyle_102728_1(best)


def test_qty_ocr_short_circuit_when_native_qty_unread():
    """791587b shape: 51/30 is not complete. Do not whole-clip harvest it."""
    unread = BomResult(
        rows=[
            BomRow(
                item=item,
                qty=0 if item not in _791587B_EXACT_QTY2 else 2,
                part_no=pn,
                description=desc,
            )
            for item, _qty, pn, desc in _KYLE_102728_1
        ],
        method="table_cells",
        confidence=0.9,
    )
    assert unread.part_number_count == 51
    assert sum(int(r.qty or 0) for r in unread.rows) == 16
    assert _native_cell_table_is_complete(unread) is False


def test_qty_ocr_short_circuit_skips_whole_clip_on_sparse_page(tmp_path: Path):
    import fitz

    pdf = tmp_path / "sparse-lom.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((40, 40), "LIST OF MATERIAL")
    doc.save(pdf)
    doc.close()
    doc = fitz.open(pdf)
    bom = _parse_material_list_on_page(doc[0], bom_config=None)
    doc.close()
    assert not bom.rows
    assert any("qty-OCR short-circuit" in n for n in bom.notes)


def test_fifty_one_pns_sixty_five_pcs_is_not_kyle_done():
    """fedf06b live: 51 unique / 65 pcs is a fail. Unread qty 0 is not a piece."""
    budget = 14
    rows: list[BomRow] = []
    for item, qty, pn, desc in _KYLE_102728_1:
        if qty > 1 and budget > 0:
            add = min(qty - 1, budget)
            rows.append(BomRow(item=item, qty=1 + add, part_no=pn, description=desc))
            budget -= add
        else:
            rows.append(BomRow(item=item, qty=1, part_no=pn, description=desc))
    fake = BomResult(rows=rows)
    assert fake.part_number_count == 51
    assert fake.piece_count == 65
    assert fake.piece_count != 97
    by_item = {r.item: r for r in fake.rows}
    assert by_item["BB"].qty != 2 or by_item["AD"].qty != 8

    unread = BomResult(
        rows=[
            BomRow(item=item, qty=0 if qty > 1 else qty, part_no=pn, description=desc)
            for item, qty, pn, desc in _KYLE_102728_1
        ]
    )
    ones = sum(1 for _i, q, _p, _d in _KYLE_102728_1 if q == 1)
    assert unread.part_number_count == 51
    assert unread.piece_count == ones
    assert unread.piece_count not in {65, 97}

    cells = [["QTY", "ITEM", "PART NO.", "DESCRIPTION"]]
    for item, qty, pn, desc in _KYLE_102728_1:
        cells.append(["" if qty > 1 else str(qty), item, pn, desc])
    parsed = parse_material_list_cells(cells)
    assert parsed.part_number_count == 51
    assert parsed.piece_count == ones
    assert any("not proof" in n.lower() for n in parsed.notes)


def test_list_of_material_does_not_yield_to_native_mac():
    """Native MAC qty→1 must not win when LIST OF MATERIAL is on the sheet."""
    mac = """
WEIGHT:
10.0 lbm
1
2
460320
CAP
5.0 lbm
1
1
460200
RAIL
5.0 lbm
"""
    native = extract_bom_from_native_mac(None, text=mac)
    assert native.rows and native.method == "pdf_bom_qty"
    lines = [
        mac,
        "WELDMENT, PLATFORM",
        "102728-1",
        "TIME MANUFACTURING",
        "LIST OF MATERIAL",
        "QTY | ITEM | PART NO. | DESCRIPTION",
    ]
    for item, qty, pn, desc in _KYLE_102728_1:
        lines.append(f"{qty} | {item} | {pn} | {desc}")
    bom = extract_bom(text="\n".join(lines))
    assert bom.method and bom.method.startswith("table_"), bom.notes
    assert not (bom.method or "").startswith("ocr_time")
    _assert_kyle_102728_1(bom)


def test_readable_4_5_6_8_qty_is_not_dimension_bleed():
    """V=6 / AA=5 / AD=8 / W=4 stay. Qty 7 is bleed — not defaulted to 1."""
    four = parse_ocr_row_strip("4 AC 100177-2 PLATE")
    assert four is not None and four["part_no"] == "100177-2" and four["qty"] == 4
    five = parse_ocr_row_strip("5 AA 460330 CAP, VERTICAL RAIL BOTTOM")
    assert five is not None and five["part_no"] == "460330" and five["qty"] == 5
    six = parse_ocr_row_strip("6 V 432710 CAP, 2 x 1 TUBE")
    assert six is not None and six["part_no"] == "432710" and six["qty"] == 6
    eight = parse_ocr_row_strip("8 AD 464440 PLATE, SUPPORT")
    assert eight is not None and eight["part_no"] == "464440" and eight["qty"] == 8
    two = parse_ocr_row_strip("2 Z 460320 CAP, VERTICAL RAIL TOP")
    assert two is not None and two["part_no"] == "460320" and two["qty"] == 2
    bleed = parse_ocr_row_strip("7 A 00177-2 PLATE")
    assert bleed is not None and bleed["part_no"] == "100177-2"
    assert bleed["qty"] != 7
    assert bleed["qty_clear"] is False
    unread = parse_ocr_row_strip("AA 460330 CAP, VERTICAL RAIL BOTTOM")
    assert unread is not None and unread["part_no"] == "460330"
    assert unread["qty_clear"] is False
    assert unread["qty"] != 1
    cell = parse_ocr_row_strip("5 | AA | 460330 | CAP, VERTICAL RAIL BOTTOM")
    assert cell is not None and cell["qty"] == 5 and cell["from_cells"] is True


def test_time_item_letters_skip_i_and_o_and_reach_bc():
    items = _platform_items()
    assert items[0] == "A" and items[-1] == "BC"
    assert "I" not in items and "O" not in items
    assert "AI" not in items and "AO" not in items and "IA" not in items
    assert items[items.index("H") + 1] == "J"
    assert items[items.index("N") + 1] == "P"
    assert items[items.index("AH") + 1] == "AJ"
    assert "BB" in items and "BA" in items and "BC" in items
    assert is_material_list_item("BB")
    assert not is_material_list_item("I")
    assert not is_material_list_item("O")
    assert not is_material_list_item("IO")
    # Digits are items only on numbered Time LOMs — never on lettered qty cells.
    assert not is_material_list_item("2")
    assert not is_material_list_item("17")
    assert is_material_list_item("17", numeric=True)
    assert is_material_list_item("1", numeric=True)


def test_parse_51_row_time_table_cells():
    rows = _platform_cell_rows()
    bom = parse_material_list_cells(rows)
    assert bom.method == "table_material_list"
    assert len(bom.rows) == 51
    assert bom.part_number_count == 51
    by_item = {r.item: r for r in bom.rows}
    assert by_item["BB"].qty == 2
    assert by_item["BB"].part_no == _BB_PART
    assert "TUBE" in by_item["BB"].description.upper()
    assert "ROUND" in by_item["BB"].description.upper()
    assert bom.piece_count == 52  # 50×1 + BB×2
    assert all(r.item != "I" and r.item != "O" for r in bom.rows)


def test_parse_51_row_time_table_text():
    text = _platform_table_text()
    assert text_has_material_list_grid(text)
    bom = parse_material_list_text(text)
    assert len(bom.rows) == 51
    assert {r.part_no for r in bom.rows}
    bb = next(r for r in bom.rows if r.item == "BB")
    assert bb.qty == 2 and bb.part_no == _BB_PART


def test_extract_bom_prefers_table_over_page_regex():
    """Loose single-letter bait must not win once a grid header is present."""
    bait = "\n".join(
        [
            "2 | A | 35122-1",
            "1 | D | 29754-2",
            "2 | E | 29754-3",
            "1 | O | 99999-1",
            "1 | P | 88888-1",
        ]
    )
    text = _platform_table_text() + "\n\n" + bait
    bom = extract_bom(text=text)
    assert bom.method and bom.method.startswith("table_")
    assert bom.part_number_count == 51
    items = {r.item for r in bom.rows}
    assert "BB" in items
    assert "O" not in items
    assert not any(r.part_no == "99999-1" for r in bom.rows)


def test_bom_config_reads_printed_qty_column_only():
    """Uploaded dash selects a printed column. Single-BOM does not invent dashes."""
    single = detect_material_list_header(["QTY", "ITEM", "PART NO.", "DESCRIPTION"])
    assert single is not None
    assert single.qty_cols == ["QTY"]
    assert single.is_multi_qty is False
    decoy = detect_material_list_header(
        ["QTY", "-1", "ITEM", "PART NO.", "DESCRIPTION"]
    )
    assert decoy is not None
    assert decoy.qty_cols == ["QTY"]
    assert decoy.is_multi_qty is False

    four = detect_material_list_header(
        ["-4", "-3", "-2", "-1", "ITEM", "PART NO.", "DESCRIPTION"]
    )
    assert four is not None and four.qty_cols == ["-4", "-3", "-2", "-1"]
    assert four.is_multi_qty is True

    two = detect_material_list_header(
        ["1004747-1", "1004747-2", "ITEM", "PART NO.", "DESCRIPTION", "NOTES"]
    )
    assert two is not None and two.qty_cols == ["-1", "-2"]
    assert two.is_multi_qty is True
    assert two.numeric_items is True

    # 102728-1: one QTY column. Blank dash required; filled -1 is not.
    cells_102728 = [["QTY", "ITEM", "PART NO.", "DESCRIPTION"]] + [
        [str(qty), item, pn, desc] for item, qty, pn, desc in _KYLE_102728_1
    ]
    blank = parse_material_list_cells(cells_102728)
    _assert_kyle_102728_1(blank)
    assert blank.method == "table_material_list"
    assert "multi_qty" not in (blank.method or "")
    filled = parse_material_list_cells(cells_102728, bom_config="-1")
    _assert_kyle_102728_1(filled)

    # Multi-qty + blank dash: do not invent -1 (28106 would leak L/N/P or all 14).
    four_blank = parse_material_list_cells(_kyle_28106_cell_rows())
    assert four_blank.rows == []
    four_dash = parse_material_list_cells(_kyle_28106_cell_rows(), bom_config="-1")
    _assert_kyle_28106_1(four_dash)


def test_dash_columns_quoting_minus_1_does_not_use_minus_2():
    text = """
LIST OF MATERIAL
-2 | -1 | ITEM | PART NO. | DESCRIPTION
1 | - | A | 16697-1 | TUBE, SHORT
- | 1 | B | 16697-2 | TUBE, LONG
2 | 1 | C | 15864-2 | STIFFENER
"""
    dash1 = parse_material_list_text(text, bom_config="1")
    by_item = {r.item: r for r in dash1.rows}
    assert set(by_item) == {"B", "C"}
    assert by_item["B"].part_no == "16697-2" and by_item["B"].qty == 1
    assert by_item["C"].qty == 1  # -1 column only; do not sum with -2
    assert "A" not in by_item
    assert dash1.piece_count == 2
    assert dash1.method == "table_material_list_multi_qty"

    dash2 = parse_material_list_text(text, bom_config="2")
    by2 = {r.item: r for r in dash2.rows}
    assert set(by2) == {"A", "C"}
    assert by2["A"].part_no == "16697-1"
    assert by2["C"].qty == 2
    assert "B" not in by2


def test_kyle_28106_1_dash1_is_11_pn_13_pcs():
    """Kyle-confirmed 28106-1. 14 rows A–P; quote -1 only. L/N/P stay off the takeoff."""
    assert len(_KYLE_28106_LETTERS) == 14
    assert "I" not in _KYLE_28106_LETTERS and "O" not in _KYLE_28106_LETTERS
    assert len(_KYLE_28106_1) == 11
    assert sum(q for _i, q, _p, _d in _KYLE_28106_1) == 13

    cells = _kyle_28106_cell_rows()
    assert len(cells) == 15  # header + 14
    _assert_kyle_28106_1(parse_material_list_cells(cells, bom_config="-1"))

    lines = [
        "WELDMENT, LOWER BOOM",
        "28106-1",
        "TIME MANUFACTURING",
        "LIST OF MATERIAL",
    ]
    for row in cells:
        lines.append(" | ".join(row))
    text = "\n".join(lines)
    _assert_kyle_28106_1(parse_material_list_text(text, bom_config="-1"))
    _assert_kyle_28106_1(extract_bom(text=text, bom_config="-1"))

    # Page-1 clip: P at the top, A at the bottom, header below.
    strips = [" | ".join(row) for row in reversed(cells)]
    harvested = harvest_ocr_row_strips(strips, bom_config="-1")
    _assert_kyle_28106_1(harvested)

    dash2 = parse_material_list_cells(cells, bom_config="2")
    parts2 = {r.part_no for r in dash2.rows}
    assert "16697-1" in parts2 and "16697-2" not in parts2
    dash3 = parse_material_list_cells(cells, bom_config="3")
    assert "16697-3" in {r.part_no for r in dash3.rows}
    dash4 = parse_material_list_cells(cells, bom_config="4")
    assert "16697-4" in {r.part_no for r in dash4.rows}


def test_kyle_1004747_1_dash1_is_14_pn_18_pcs():
    """Kyle-confirmed 1004747-1. Items 1–17; quote the 1004747-1 column only."""
    cells = _kyle_1004747_cell_rows()
    assert len(cells) == 18  # header + 17
    assert cells[0][:3] == ["1004747-1", "1004747-2", "ITEM"]
    assert cells[1][2] == "17" and cells[-1][2] == "1"
    _assert_kyle_1004747_1(parse_material_list_cells(cells, bom_config="-1"))

    lines = [
        "OUTER BOOM WELDMENT - 1004747-1",
        "TIME MANUFACTURING",
        "LIST OF MATERIAL",
    ]
    for row in cells:
        lines.append(" | ".join(row))
    text = "\n".join(lines)
    _assert_kyle_1004747_1(parse_material_list_text(text, bom_config="-1"))
    _assert_kyle_1004747_1(extract_bom(text=text, bom_config="-1"))

    # Page-1 clip: item 1 at the bottom, header below.
    strips = [" | ".join(row) for row in reversed(cells)]
    harvested = harvest_ocr_row_strips(
        strips, bom_config="-1", page_text="OUTER BOOM WELDMENT - 1004747-1"
    )
    _assert_kyle_1004747_1(harvested)

    dash2 = parse_material_list_cells(cells, bom_config="2")
    parts2 = {r.part_no for r in dash2.rows}
    by2 = {str(r.item): r for r in dash2.rows}
    assert parts2 == {"1004806-2", "11694-2", "25009-2"}
    assert set(by2) == {"16", "14", "13"}
    assert "1004773-1" not in parts2 and "1004743-1" not in parts2


def test_kyle_1004611_1_dash1_keeps_dwg_omits_uv():
    """Kyle-confirmed 1004611-1-LOM.xlsx. 24 letters; quote -1 only."""
    assert len(_KYLE_1004611_LETTERS) == 24
    assert "I" not in _KYLE_1004611_LETTERS and "O" not in _KYLE_1004611_LETTERS
    assert _KYLE_1004611_LETTERS[0] == "A" and _KYLE_1004611_LETTERS[-1] == "Z"
    assert _KYLE_1004611_1_PN_COUNT == 22
    assert _KYLE_1004611_1_PCS == 66
    assert _KYLE_1004611_1_PCS != 83

    cells = _kyle_1004611_cell_rows()
    assert len(cells) == 25  # header + 24
    assert cells[0][:3] == ["-2", "-1", "ITEM"]
    assert cells[1][2] == "A" and cells[-1][2] == "Z"
    _assert_kyle_1004611_1(parse_material_list_cells(cells, bom_config="-1"))

    lines = [
        "WELDMENT, PLATFORM",
        "1004611-1",
        "TIME MANUFACTURING",
        "LIST OF MATERIAL",
    ]
    for row in cells:
        lines.append(" | ".join(row))
    text = "\n".join(lines)
    _assert_kyle_1004611_1(parse_material_list_text(text, bom_config="-1"))
    _assert_kyle_1004611_1(extract_bom(text=text, bom_config="-1"))

    # Page-1 clip: Z at the top, A at the bottom, header below.
    strips = [" | ".join(row) for row in reversed(cells)]
    assert strips[0].split("|")[2].strip() == "Z"
    assert strips[-2].split("|")[2].strip() == "A"
    harvested = harvest_ocr_row_strips(
        strips, bom_config="-1", page_text="WELDMENT, PLATFORM  1004611-1"
    )
    _assert_kyle_1004611_1(harvested)

    dwg = parse_ocr_row_strip("1 | A | 1004611-DWG |")
    assert dwg is not None
    assert dwg["item"] == "A"
    assert dwg["part_no"] == "1004611-DWG"
    assert dwg["part_no"] != "1004611-1"
    assert recover_time_part_no("1004611-DWG") == "1004611-DWG"

    dash2 = parse_material_list_cells(cells, bom_config="2")
    parts2 = {r.part_no for r in dash2.rows}
    by2 = {r.item: r for r in dash2.rows}
    assert "1004620-2" in parts2 and "1004675-1" in parts2
    assert set(by2) == {"U", "V"}
    assert "1004611-DWG" not in parts2
    assert "80054-1" not in parts2


def test_multi_qty_printed_qty_10_stays_ten():
    """1004611 66 pcs: a printed -1 qty 10 is not column-index bleed."""
    cells = [
        ["-2", "-1", "ITEM", "PART NO.", "DESCRIPTION"],
        ["", "10", "S", "80054-1", '10" GASKET'],
        ["", "1", "A", "1004611-DWG", ""],
    ]
    bom = parse_material_list_cells(cells, bom_config="-1")
    by_item = {r.item: r for r in bom.rows}
    assert by_item["S"].qty == 10
    assert by_item["S"].part_no == "80054-1"
    assert by_item["A"].part_no == "1004611-DWG"
    assert sum(r.qty for r in bom.rows) == 11


def test_kyle_p904225_1_numeric_omits_title_and_welding_wire():
    """Kyle-confirmed P904225-1-LOM.xlsx. 11 numeric items; quote the grid only."""
    layout = detect_material_list_header(
        ["P904225-1", "ITEM", "PART NO.", "DESCRIPTION"]
    )
    assert layout is not None
    assert layout.numeric_items is True
    assert layout.qty_cols == ["-1"]
    assert "P904225-1" in layout.qty_header_pns

    cells = _kyle_p904225_cell_rows()
    assert len(cells) == 14  # header + 11 + wire note + title PN
    assert cells[0][0] == "P904225-1" and cells[0][1] == "ITEM"
    assert cells[1][1] == "11" and cells[11][1] == "1"
    _assert_kyle_p904225_1(parse_material_list_cells(cells, bom_config=""))

    lines = [
        "WELDMENT, PLATFORM",
        "P904225-1",
        "TIME MANUFACTURING",
        "LIST OF MATERIAL",
    ]
    for row in cells:
        lines.append(" | ".join(row))
    text = "\n".join(lines)
    _assert_kyle_p904225_1(parse_material_list_text(text, bom_config=""))
    _assert_kyle_p904225_1(extract_bom(text=text, bom_config=""))

    strips = [" | ".join(row) for row in reversed(cells)]
    assert cells[11][1] == "1" and cells[11][2] == "89100-1"
    harvested = harvest_ocr_row_strips(
        strips,
        bom_config="",
        page_text="WELDMENT, PLATFORM  P904225-1",
    )
    _assert_kyle_p904225_1(harvested)

    wire = parse_ocr_row_strip("1 | 12 | 89176-1 | WELDING WIRE")
    assert wire is None
    title = parse_ocr_row_strip("P904225-1 WELDMENT")
    assert title is None
    child = parse_ocr_row_strip("1 | 2 | P904226-1 | SUPPORT")
    assert child is not None
    assert "904226" in child["part_no"]


def test_kyle_103516_numeric_keeps_gate_weldment_and_item_27():
    """Kyle-confirmed 103516-LOM.xlsx. 27 numeric items; quote -1 only."""
    assert _KYLE_103516_PN_COUNT == 27
    assert _KYLE_103516_PCS == 45
    assert _KYLE_103516_PCS != 121

    cells = _kyle_103516_cell_rows()
    assert len(cells) == 28  # header + 27
    assert cells[0][:3] == ["-2", "-1", "ITEM"]
    assert cells[1][2] == "27" and cells[-1][2] == "1"
    assert cells[1][3] == "40002-2"
    assert cells[1][0] == "" and cells[1][1] == "1"
    _assert_kyle_103516(parse_material_list_cells(cells, bom_config="-1"))

    lines = [
        "WELDMENT, PLATFORM",
        "103516-1",
        "TIME MANUFACTURING",
        "LIST OF MATERIAL",
    ]
    for row in cells:
        lines.append(" | ".join(row))
    text = "\n".join(lines)
    _assert_kyle_103516(parse_material_list_text(text, bom_config="-1"))
    _assert_kyle_103516(extract_bom(text=text, bom_config="-1"))

    strips = [" | ".join(row) for row in reversed(cells)]
    harvested = harvest_ocr_row_strips(
        strips,
        bom_config="-1",
        page_text="WELDMENT, PLATFORM  103516-1",
    )
    _assert_kyle_103516(harvested)

    dash2 = parse_material_list_cells(cells, bom_config="2")
    parts2 = {r.part_no for r in dash2.rows}
    assert "40002-2" not in parts2
    assert "103535-1" not in parts2
    assert dash2.rows == []


def test_kyle_21727_1_single_qty_letters_a_l_skip_i():
    """Kyle-confirmed 21727-1-LOM.xlsx. A–L skip I; single QTY; omit 61358."""
    assert _KYLE_21727_LETTERS == list("ABCDEFGHJKL")
    assert len(_KYLE_21727_LETTERS) == 11
    assert "I" not in _KYLE_21727_LETTERS
    assert "M" not in _KYLE_21727_LETTERS
    assert _KYLE_21727_1_PN_COUNT == 11
    assert _KYLE_21727_1_PCS == 16
    assert {pn for _i, _q, pn, _d in _KYLE_21727_1} == {"16697-1", "16697-2"}
    assert "61358" not in {pn for _i, _q, pn, _d in _KYLE_21727_1}

    layout = detect_material_list_header(["QTY", "ITEM", "PART NO.", "DESCRIPTION"])
    assert layout is not None
    assert layout.qty_cols == ["QTY"]
    assert not layout.is_multi_qty
    assert layout.numeric_items is False

    cells = _kyle_21727_cell_rows()
    assert len(cells) == 13  # header + 11 letters + 61358 junk
    assert cells[0] == ["QTY", "ITEM", "PART NO.", "DESCRIPTION"]
    assert cells[1][1] == "A" and cells[11][1] == "L"
    assert cells[-1][2] == "61358"
    parsed = parse_material_list_cells(cells)
    _assert_kyle_21727_1(parsed)
    assert parsed.method == "table_material_list"

    lines = [
        "WELDMENT, PLATFORM",
        "21727-1",
        "TIME MANUFACTURING",
        "LIST OF MATERIAL",
    ]
    for row in cells:
        lines.append(" | ".join(row))
    text = "\n".join(lines)
    _assert_kyle_21727_1(parse_material_list_text(text))
    extracted = extract_bom(text=text)
    _assert_kyle_21727_1(extracted)
    assert extracted.method and extracted.method.startswith("table_")
    assert not (extracted.method or "").startswith("ocr_time")

    # Page-1 clip: L at the top, A at the bottom, header below. 61358 first.
    strips = [" | ".join(row) for row in reversed(cells)]
    assert strips[0].split("|")[2].strip() == "61358"
    assert strips[-2].split("|")[1].strip() == "A"
    harvested = harvest_ocr_row_strips(
        strips,
        bom_config="",
        page_text="WELDMENT, PLATFORM  21727-1",
    )
    _assert_kyle_21727_1(harvested)
    assert "61358" not in {r.part_no for r in harvested.rows}


def test_kyle_21727_1_omits_61358_and_title_dwg():
    parsed = parse_material_list_cells(
        [
            ["QTY", "ITEM", "PART NO.", "DESCRIPTION"],
            ["1", "A", "16697-1", "TUBE, SHORT"],
            ["1", "B", "16697-2", "TUBE, LONG"],
            ["1", "", "21727-1", "WELDMENT"],
            ["1", "M", "61358", "REVISION NOTE"],
        ]
    )
    pns = {r.part_no for r in parsed.rows}
    assert "16697-1" in pns
    assert "16697-2" in pns
    assert "61358" not in pns
    assert "21727-1" not in pns


def test_kyle_1007922_1_dash1_6_pn_14_pcs_omits_other_dash():
    """Kyle-confirmed 1007922-1-LOM.xlsx. Dash -1 only; 14149-1×4, 1007830-1×2."""
    assert _KYLE_1007922_1_PN_COUNT == 6
    assert _KYLE_1007922_1_PCS == 14
    assert {pn for _i, _q, pn, _d in _KYLE_1007922_1} == {
        "1007800-1",
        "14149-1",
        "1007830-1",
        "6993-1",
        "28275-1",
    }
    assert {pn for _i, pn, _d in _KYLE_1007922_OTHER_DASH} == {"21750-2", "21743-2"}
    assert "73207" not in {pn for _i, _q, pn, _d in _KYLE_1007922_1}
    assert next(q for _i, q, pn, _d in _KYLE_1007922_1 if pn == "14149-1") == 4
    assert next(q for _i, q, pn, _d in _KYLE_1007922_1 if pn == "1007830-1") == 2

    layout = detect_material_list_header(["-2", "-1", "ITEM", "PART NO.", "DESCRIPTION"])
    assert layout is not None
    assert layout.qty_cols == ["-2", "-1"]
    assert layout.is_multi_qty
    assert layout.numeric_items is False

    cells = _kyle_1007922_cell_rows()
    assert cells[0][:3] == ["-2", "-1", "ITEM"]
    assert cells[1][2] == "A" and cells[1][3] == "1007800-1"
    assert cells[2][1] == "4" and cells[2][3] == "14149-1"
    assert cells[3][1] == "2" and cells[3][3] == "1007830-1"
    parsed = parse_material_list_cells(cells, bom_config="-1")
    _assert_kyle_1007922_1(parsed)
    assert parsed.method == "table_material_list_multi_qty"

    lines = [
        "WELDMENT, PLATFORM",
        "1007922-1",
        "TIME MANUFACTURING",
        "LIST OF MATERIAL",
    ]
    for row in cells:
        lines.append(" | ".join(row))
    text = "\n".join(lines)
    _assert_kyle_1007922_1(parse_material_list_text(text, bom_config="-1"))
    extracted = extract_bom(text=text, bom_config="-1")
    _assert_kyle_1007922_1(extracted)
    assert extracted.method and extracted.method.startswith("table_")
    assert not (extracted.method or "").startswith("ocr_time")

    strips = [" | ".join(row) for row in reversed(cells)]
    harvested = harvest_ocr_row_strips(
        strips,
        bom_config="-1",
        page_text="WELDMENT, PLATFORM  1007922-1",
    )
    _assert_kyle_1007922_1(harvested)

    dash2 = parse_material_list_cells(cells, bom_config="2")
    parts2 = {r.part_no for r in dash2.rows}
    assert "21750-2" in parts2 and "21743-2" in parts2
    assert "14149-1" not in parts2
    assert "1007830-1" not in parts2
    assert "1007800-1" not in parts2
    assert "73207" not in parts2


def test_kyle_33612_1_letters_a_w_skip_io_21_pn_47_pcs():
    """Kyle-confirmed 33612-1-LOM.xlsx. A–W skip I/O; single QTY; keep 282xx."""
    assert _KYLE_33612_LETTERS == list("ABCDEFGHJKLMNPQRSTUVW")
    assert len(_KYLE_33612_LETTERS) == 21
    assert "I" not in _KYLE_33612_LETTERS and "O" not in _KYLE_33612_LETTERS
    assert _KYLE_33612_LETTERS[0] == "A" and _KYLE_33612_LETTERS[-1] == "W"
    assert _KYLE_33612_1_PN_COUNT == 21
    assert _KYLE_33612_1_PCS == 47
    named = {pn for _i, _q, pn, _d in _KYLE_33612_1}
    assert "89176-1" in named and "94560" in named
    assert set(_KYLE_33612_282XX) <= named
    assert "56657" not in named and "97879" not in named

    layout = detect_material_list_header(["QTY", "ITEM", "PART NO.", "DESCRIPTION"])
    assert layout is not None
    assert layout.qty_cols == ["QTY"]
    assert not layout.is_multi_qty
    assert layout.numeric_items is False

    cells = _kyle_33612_cell_rows()
    assert len(cells) == 24  # header + 21 letters + 56657 + 97879
    assert cells[0] == ["QTY", "ITEM", "PART NO.", "DESCRIPTION"]
    assert cells[1][1] == "A" and cells[21][1] == "W"
    assert cells[-2][2] == "56657" and cells[-1][2] == "97879"
    parsed = parse_material_list_cells(cells)
    _assert_kyle_33612_1(parsed)
    assert parsed.method == "table_material_list"

    lines = [
        "WELDMENT, PLATFORM",
        "33612-1",
        "TIME MANUFACTURING",
        "LIST OF MATERIAL",
    ]
    for row in cells:
        lines.append(" | ".join(row))
    text = "\n".join(lines)
    _assert_kyle_33612_1(parse_material_list_text(text))
    extracted = extract_bom(text=text)
    _assert_kyle_33612_1(extracted)
    assert extracted.method and extracted.method.startswith("table_")
    assert not (extracted.method or "").startswith("ocr_time")

    strips = [" | ".join(row) for row in reversed(cells)]
    assert strips[0].split("|")[2].strip() == "97879"
    assert strips[-2].split("|")[1].strip() == "A"
    harvested = harvest_ocr_row_strips(
        strips,
        bom_config="",
        page_text="WELDMENT, PLATFORM  33612-1",
    )
    _assert_kyle_33612_1(harvested)
    assert "56657" not in {r.part_no for r in harvested.rows}
    assert "97879" not in {r.part_no for r in harvested.rows}


def test_kyle_33612_1_omits_56657_97879_keeps_282xx():
    parsed = parse_material_list_cells(
        [
            ["QTY", "ITEM", "PART NO.", "DESCRIPTION"],
            ["1", "A", "89176-1", "TUBE"],
            ["1", "M", "94560", "GATE, FABRICATION"],
            ["1", "N", "28275-1", "TUBE"],
            ["1", "P", "28275-2", "TUBE"],
            ["1", "", "33612-1", "WELDMENT"],
            ["1", "X", "56657", "FIRST RELEASE TO PRODUCTION"],
            ["1", "BT", "97879", "THIS DRAWING IS THE PROPERTY OF TIME"],
        ]
    )
    pns = {r.part_no for r in parsed.rows}
    assert "89176-1" in pns
    assert "94560" in pns
    assert "28275-1" in pns and "28275-2" in pns
    assert "56657" not in pns
    assert "97879" not in pns
    assert "33612-1" not in pns


def test_kyle_105098_1_parent_a_j_9_pn_9_pcs_omits_103603():
    """Kyle-confirmed 105098-1-LOM.xlsx. A–J skip I; parent only; no 103603-1."""
    assert _KYLE_105098_LETTERS == list("ABCDEFGHJ")
    assert len(_KYLE_105098_LETTERS) == 9
    assert "I" not in _KYLE_105098_LETTERS
    assert _KYLE_105098_LETTERS[0] == "A" and _KYLE_105098_LETTERS[-1] == "J"
    assert _KYLE_105098_1_PN_COUNT == 9
    assert _KYLE_105098_1_PCS == 9
    assert _KYLE_105098_1 == []
    assert "103603-1" not in {pn for _i, _q, pn, _d in _KYLE_105098_1}

    layout = detect_material_list_header(["QTY", "ITEM", "PART NO.", "DESCRIPTION"])
    assert layout is not None
    assert layout.qty_cols == ["QTY"]
    assert not layout.is_multi_qty

    cells = _kyle_105098_cell_rows()
    assert len(cells) == 10  # header + 9 letters
    assert cells[0] == ["QTY", "ITEM", "PART NO.", "DESCRIPTION"]
    assert cells[1][1] == "A" and cells[9][1] == "J"
    parsed = parse_material_list_cells(cells)
    _assert_kyle_105098_1(parsed)

    lines = [
        "WELDMENT, PLATFORM",
        "105098-1",
        "TIME MANUFACTURING",
        "LIST OF MATERIAL",
    ]
    for row in cells:
        lines.append(" | ".join(row))
    text = "\n".join(lines)
    _assert_kyle_105098_1(parse_material_list_text(text))
    extracted = extract_bom(text=text)
    _assert_kyle_105098_1(extracted)
    assert not (extracted.method or "").startswith("ocr_time")

    harvested = harvest_ocr_row_strips(
        [" | ".join(row) for row in reversed(cells)],
        bom_config="",
        page_text="WELDMENT, PLATFORM  105098-1",
    )
    _assert_kyle_105098_1(harvested)


def test_later_sheet_103603_1_is_not_105098_parent_bom(tmp_path: Path):
    """Parent A–J on sheet 1. Later 103603-1 child LOM must not become this job."""
    from quote_core.bom_table import (
        is_later_sheet_child_weldment,
        job_weldment_key_from_path,
        page_title_weldment_key,
    )

    import fitz

    parent = (
        "WELDMENT, PLATFORM  105098-1  TIME MANUFACTURING\n"
        "LIST OF MATERIAL\n"
        "QTY | ITEM | PART NO. | DESCRIPTION\n"
        "1 | A | | \n"
        "1 | J | | \n"
    )
    child = (
        "WELDMENT, PLATFORM  103603-1  TIME MANUFACTURING\n"
        "LIST OF MATERIAL\n"
        "QTY | ITEM | PART NO. | DESCRIPTION\n"
        "1 | A | 103603-2 | TUBE\n"
        "1 | B | 103604-1 | PLATE\n"
        "1 | C | 103605-1 | RAIL\n"
        "1 | D | 103606-1 | CAP\n"
        "1 | E | 103607-1 | ANGLE\n"
        "1 | F | 103608-1 | GATE\n"
        "1 | G | 103609-1 | PIN\n"
        "1 | H | 103610-1 | HOOK\n"
        "1 | J | 103611-1 | BAR\n"
        "1 | K | 103612-1 | PLATE\n"
        "1 | L | 103613-1 | TUBE\n"
    )
    assert page_title_weldment_key(parent) == "105098"
    assert page_title_weldment_key(child) == "103603"
    assert is_later_sheet_child_weldment(child, "105098")
    assert not is_later_sheet_child_weldment(parent, "105098")
    same_sheet_gate = (
        "WELDMENT, PLATFORM  103516-1  TIME MANUFACTURING\n"
        "1 | 1 | 103535-1 | GATE WELDMENT\n"
    )
    assert page_title_weldment_key(same_sheet_gate) == "103516"
    assert not is_later_sheet_child_weldment(same_sheet_gate, "103516")

    pdf = tmp_path / "105098-1.pdf"
    assert job_weldment_key_from_path(pdf) == "105098"
    doc = fitz.open()
    p1 = doc.new_page()
    p1.insert_text((40, 40), parent)
    p2 = doc.new_page()
    p2.insert_text((40, 40), child)
    doc.save(pdf)
    doc.close()

    bom = extract_bom(pdf_path=pdf, bom_config="")
    parts = {str(r.part_no or "") for r in bom.rows}
    assert "103603-1" not in parts
    assert "103603-2" not in parts
    assert "103604-1" not in parts
    assert "103611-1" not in parts
    _assert_kyle_105098_1(bom)
    joined = " ".join(bom.notes).lower()
    assert "child" in joined or "103603" in joined


def test_kyle_1004747_1_pdf_extract_bom_and_xlsx(tmp_path: Path):
    cells = _kyle_1004747_cell_rows()
    pdf = tmp_path / "1004747.pdf"
    _write_lom_pdf(
        pdf,
        cells[0],
        cells[1:],
        title="OUTER BOOM WELDMENT - 1004747-1  TIME MANUFACTURING",
    )
    bom = extract_bom(pdf_path=pdf, bom_config="-1")
    assert bom.method and bom.method.startswith("table_"), bom.notes
    assert not (bom.method or "").startswith("ocr_time")
    _assert_kyle_1004747_1(bom)
    xlsx = pdf.with_name(f"{pdf.stem}-LOM.xlsx")
    assert xlsx.is_file()
    _assert_kyle_xlsx(xlsx, _KYLE_1004747_1)
    from quote_core.bom_xlsx import read_lom_xlsx

    _header, sheet = read_lom_xlsx(xlsx)
    parts = {r["PART NO"] for r in sheet}
    assert "1004806-2" not in parts
    assert "11694-2" not in parts
    assert "25009-2" not in parts
    assert "1004773-1" in parts and "1004743-1" in parts


def test_kyle_28106_1_pdf_extract_bom_and_xlsx(tmp_path: Path):
    cells = _kyle_28106_cell_rows()
    pdf = tmp_path / "28106.pdf"
    _write_lom_pdf(
        pdf,
        cells[0],
        cells[1:],
        title="LOWER BOOM WELDMENT  28106-1  TIME MANUFACTURING",
    )
    bom = extract_bom(pdf_path=pdf, bom_config="-1")
    assert bom.method and bom.method.startswith("table_"), bom.notes
    assert not (bom.method or "").startswith("ocr_time")
    _assert_kyle_28106_1(bom)
    xlsx = pdf.with_name(f"{pdf.stem}-LOM.xlsx")
    assert xlsx.is_file()
    _assert_kyle_xlsx(xlsx, _KYLE_28106_1)
    from quote_core.bom_xlsx import read_lom_xlsx

    _header, sheet = read_lom_xlsx(xlsx)
    parts = {r["PART NO"] for r in sheet}
    assert "16697-1" not in parts and "16697-3" not in parts and "16697-4" not in parts


def test_incomplete_tall_list_flags_review_without_padding():
    bom = parse_material_list_cells(_platform_cell_rows(drop={"C", "AA", "AZ"}))
    assert len(bom.rows) == 48
    joined = " ".join(bom.notes).lower()
    assert "incomplete" in joined or "missing" in joined
    assert "flag review" in joined
    assert "do not pad" in joined
    assert not any(r.item in {"C", "AA", "AZ"} for r in bom.rows)
    # BB still present with qty 2 — gaps are review, not invented rows.
    bb = next(r for r in bom.rows if r.item == "BB")
    assert bb.qty == 2 and bb.part_no == _BB_PART


def test_word_boxes_read_cells_not_page_blob():
    """Positioned words (native PDF / OCR boxes) segment into cells."""
    items = _platform_items()
    words: list[dict] = [
        {"text": "QTY", "x0": 10, "y0": 10, "x1": 40, "y1": 22},
        {"text": "ITEM", "x0": 50, "y0": 10, "x1": 90, "y1": 22},
        {"text": "PART", "x0": 100, "y0": 10, "x1": 140, "y1": 22},
        {"text": "NO.", "x0": 142, "y0": 10, "x1": 168, "y1": 22},
        {"text": "DESCRIPTION", "x0": 200, "y0": 10, "x1": 280, "y1": 22},
    ]
    for i, item in enumerate(items):
        y = 30.0 + i * 12.0
        qty = "2" if item == "BB" else "1"
        part = _BB_PART if item == "BB" else f"1028{i:02d}-1"
        desc = _BB_DESC if item == "BB" else f"COMPONENT {item}"
        words.append({"text": qty, "x0": 12, "y0": y, "x1": 28, "y1": y + 10})
        words.append({"text": item, "x0": 55, "y0": y, "x1": 85, "y1": y + 10})
        words.append({"text": part, "x0": 105, "y0": y, "x1": 170, "y1": y + 10})
        words.append({"text": desc, "x0": 205, "y0": y, "x1": 300, "y1": y + 10})
    bom = parse_material_list_words(words)
    assert len(bom.rows) == 51
    bb = next(r for r in bom.rows if r.item == "BB")
    assert bb.qty == 2 and bb.part_no == _BB_PART


def _write_lom_pdf(path: Path, headers: list[str], rows: list[list[str]], *, title: str) -> None:
    import fitz

    row_h = 11
    height = 80 + (len(rows) + 2) * row_h + 40
    doc = fitz.open()
    page = doc.new_page(width=792, height=max(1224, height))
    page.insert_text((40, 28), title, fontsize=10)
    page.insert_text((40, 42), "LIST OF MATERIAL", fontsize=10)
    xs = [360, 410, 460, 560]
    first = str(headers[0] or "").strip().upper()
    if len(headers) == 4 and first.startswith("P") and first[1:2].isdigit():
        # P904225-1 qty header is wider than QTY — keep ITEM from merging.
        xs = [240, 400, 460, 580]
    if len(headers) == 5:
        xs = [320, 370, 420, 480, 580]
    elif len(headers) >= 6:
        xs = [260, 300, 340, 380, 430, 500, 600][: len(headers)]
    y = 64
    for i, cell in enumerate(headers):
        page.insert_text((xs[i], y), cell, fontsize=8)
    for row in rows:
        y += row_h
        for i, cell in enumerate(row):
            page.insert_text((xs[i], y), str(cell), fontsize=8)
    doc.save(path)
    doc.close()


def test_kyle_102728_1_pdf_extract_bom_matches_grid(tmp_path: Path):
    """Synthetic 102728- Weldment.pdf — no customer file. ITEM+PN+QTY = Kyle grid."""
    data_rows = [
        [str(qty), item, pn, desc] for item, qty, pn, desc in _KYLE_102728_1
    ]
    pdf = tmp_path / "Time 102728- Weldment.pdf"
    _write_lom_pdf(
        pdf,
        ["QTY", "ITEM", "PART NO.", "DESCRIPTION"],
        data_rows,
        title="WELDMENT, PLATFORM  102728-1  TIME MANUFACTURING",
    )
    bom = extract_bom(pdf_path=pdf)
    assert bom.method and bom.method.startswith("table_"), bom.notes
    assert not (bom.method or "").startswith("ocr_time")
    _assert_kyle_102728_1(bom)
    xlsx = pdf.with_name(f"{pdf.stem}-LOM.xlsx")
    assert xlsx.is_file(), "extract_bom must emit sibling LOM.xlsx"
    _assert_kyle_xlsx(xlsx, _KYLE_102728_1)
    assert bom.lom_xlsx == xlsx.name
    assert all(r.source == "lom_xlsx" for r in bom.rows)


def test_pdf_table_path_does_not_pad_library_subweldments(tmp_path: Path):
    items = _platform_items()
    data_rows = []
    for i, item in enumerate(items):
        if item == "BB":
            data_rows.append(["2", "BB", _BB_PART, _BB_DESC])
        else:
            data_rows.append(["1", item, f"1028{i:02d}-1", f"COMPONENT {item}"])
    pdf = tmp_path / "102728-1.pdf"
    _write_lom_pdf(
        pdf,
        ["QTY", "ITEM", "PART NO.", "DESCRIPTION"],
        data_rows,
        title="WELDMENT, PLATFORM  102728-1  TIME MANUFACTURING  SHEET 1 OF 2",
    )
    lib = tmp_path / "library"
    lib.mkdir()
    # Nested sub-weldment / child drawings — must not become BOM rows.
    for extra in ("102726-1.pdf", "102729.pdf", "102999-2.pdf"):
        (lib / extra).write_bytes(b"%PDF-1.4\n%\n")

    bom = extract_bom(pdf_path=pdf, library_folder=lib, bom_config="1")
    assert bom.part_number_count == 51, [f"{r.item}:{r.part_no}" for r in bom.rows]
    assert bom.method and bom.method.startswith("table_")
    bb = next(r for r in bom.rows if r.item == "BB")
    assert bb.qty == 2 and bb.part_no == _BB_PART
    parts = {r.part_no for r in bom.rows}
    assert "102726-1" not in parts
    assert "102729-1" not in parts
    assert not any(p.startswith("102999") for p in parts)

    # Direct Time-style entry point must also prefer the table and skip padding.
    ocr = extract_bom_from_ocr_time_style(pdf, library_folder=lib, bom_config="1")
    assert ocr.part_number_count == 51
    assert ocr.method and ocr.method.startswith("table_")


def test_pdf_dash_columns_quote_minus_1_only(tmp_path: Path):
    pdf = tmp_path / "28106-1.pdf"
    _write_lom_pdf(
        pdf,
        ["-2", "-1", "ITEM", "PART NO.", "DESCRIPTION"],
        [
            ["1", "-", "A", "16697-1", "TUBE, SHORT"],
            ["-", "1", "B", "16697-2", "TUBE, LONG"],
            ["2", "1", "C", "15864-2", "STIFFENER"],
        ],
        title="LOWER BOOM WELDMENT 28106-1 LIST OF MATERIAL",
    )
    bom = extract_bom(pdf_path=pdf, bom_config="1")
    by_item = {r.item: r for r in bom.rows}
    assert set(by_item) == {"B", "C"}
    assert by_item["C"].qty == 1
    assert by_item["B"].part_no == "16697-2"
    assert bom.piece_count == 2


def test_undelimited_ocr_line_reads_bb_cells():
    """Live OCR often emits a row as one blob, not pipe-delimited cells."""
    text = (
        "LIST OF MATERIAL\n"
        "QTY ITEM PART NO. DESCRIPTION\n"
        "1 A 102800-1 PLATE\n"
        "2 BB 102727-4 TUBE, ROUND\n"
        "1 BC 102850-1 CAP\n"
    )
    bom = parse_material_list_text(text)
    by_item = {r.item: r for r in bom.rows}
    assert by_item["BB"].qty == 2
    assert by_item["BB"].part_no == _BB_PART
    assert "TUBE" in by_item["BB"].description.upper()


def _write_lom_page(doc, headers: list[str], rows: list[list[str]], *, title: str) -> None:
    import fitz

    row_h = 11
    height = 80 + (len(rows) + 2) * row_h + 40
    page = doc.new_page(width=792, height=max(1224, height))
    page.insert_text((40, 28), title, fontsize=10)
    page.insert_text((40, 42), "LIST OF MATERIAL", fontsize=10)
    xs = [360, 410, 460, 560]
    if len(headers) == 5:
        xs = [320, 370, 420, 480, 580]
    elif len(headers) >= 6:
        xs = [260, 300, 340, 380, 430, 500, 600][: len(headers)]
    y = 64
    for i, cell in enumerate(headers):
        page.insert_text((xs[i], y), cell, fontsize=8)
    for row in rows:
        y += row_h
        for i, cell in enumerate(row):
            page.insert_text((xs[i], y), str(cell), fontsize=8)


def test_lom_header_on_page_4_of_five_page_pdf(tmp_path: Path):
    """102728-1 live PDF: LOM is on a later sheet, not page 0 / first two."""
    import fitz

    items = _platform_items()
    data_rows = []
    for i, item in enumerate(items):
        if item == "BB":
            data_rows.append(["2", "BB", _BB_PART, _BB_DESC])
        else:
            data_rows.append(["1", item, f"1028{i:02d}-1", f"COMPONENT {item}"])

    pdf = tmp_path / "Time 102728- Weldment.pdf"
    doc = fitz.open()
    for i in range(4):
        page = doc.new_page(width=792, height=612)
        page.insert_text((72, 72), f"ISO VIEW SHEET {i + 1}  WELDMENT PLATFORM  NO BOM HERE")
        # Page-0 bait the old single-letter regex would keep (A,D,E,O,P).
        if i == 0:
            page.insert_text((72, 120), "2 | A | 35122-1\n1 | D | 29754-2\n2 | E | 29754-3")
            page.insert_text((72, 160), "1 | O | 99999-1\n1 | P | 88888-1")
    _write_lom_page(
        doc,
        ["QTY", "ITEM", "PART NO.", "DESCRIPTION"],
        data_rows,
        title="WELDMENT, PLATFORM  102728-1  TIME MANUFACTURING  SHEET 1 OF 2",
    )
    assert len(doc) == 5
    doc.save(pdf)
    doc.close()

    bom = extract_bom(pdf_path=pdf, bom_config="1")
    assert bom.method and bom.method.startswith("table_"), bom.notes
    assert bom.part_number_count == 51, [f"{r.item}:{r.part_no}" for r in bom.rows]
    bb = next(r for r in bom.rows if r.item == "BB")
    assert bb.qty == 2 and bb.part_no == _BB_PART
    assert not any(r.part_no in {"99999-1", "88888-1", "35122-1"} for r in bom.rows)


def test_lom_header_found_does_not_fallback_to_regex(tmp_path: Path):
    """If the grid header is found, do not return 10 junk single-letter PNs."""
    import fitz

    pdf = tmp_path / "header_only_later_page.pdf"
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page(width=792, height=612)
        if i == 0:
            page.insert_text((72, 72), "2 | A | 35122-1")
            page.insert_text((72, 90), "1 | D | 29754-2")
            page.insert_text((72, 108), "2 | E | 29754-3")
            page.insert_text((72, 126), "1 | O | 99999-1")
            page.insert_text((72, 144), "1 | P | 88888-1")
    page = doc.new_page(width=792, height=612)
    page.insert_text((400, 500), "LIST OF MATERIAL", fontsize=10)
    page.insert_text((400, 520), "QTY", fontsize=8)
    page.insert_text((440, 520), "ITEM", fontsize=8)
    page.insert_text((490, 520), "PART NO.", fontsize=8)
    page.insert_text((580, 520), "DESCRIPTION", fontsize=8)
    doc.save(pdf)
    doc.close()

    bom = extract_bom(pdf_path=pdf)
    assert material_list_header_seen(bom)
    assert not (bom.method or "").startswith("ocr_time")
    parts = {r.part_no for r in bom.rows}
    assert "99999-1" not in parts
    assert "88888-1" not in parts
    assert "35122-1" not in parts
    joined = " ".join(bom.notes).lower()
    assert "not falling back" in joined or "header found" in joined or "flag review" in joined


def test_ocr_time_style_never_uses_whole_page_regex(tmp_path: Path):
    """No LOM grid → empty table result, never ocr_time whole-page regex."""
    import fitz

    pdf = tmp_path / "bait_only.pdf"
    doc = fitz.open()
    page = doc.new_page(width=792, height=612)
    page.insert_text((72, 72), "2 | A | 35122-1")
    page.insert_text((72, 90), "1 | D | 29754-2")
    page.insert_text((72, 108), "2 | E | 29754-3")
    page.insert_text((72, 126), "1 | O | 99999-1")
    page.insert_text((72, 144), "1 | P | 88888-1")
    doc.save(pdf)
    doc.close()

    ocr = extract_bom_from_ocr_time_style(pdf)
    assert not (ocr.method or "").startswith("ocr_time")
    parts = {r.part_no for r in ocr.rows}
    assert "35122-1" not in parts
    assert "99999-1" not in parts
    assert "88888-1" not in parts
    assert "not falling back" in " ".join(ocr.notes).lower()


def _write_right_side_lom_bottom_header(page, rows: list[list[str]]) -> None:
    """102728-1 visual spec: tall right-hand grid, header at the BOTTOM, data up."""
    xs = [560, 600, 640, 720]
    # Title block / LOM title at the bottom; column headers just above; A at bottom.
    page.insert_text((560, 1180), "LIST OF MATERIAL", fontsize=8)
    y = 1164
    for i, cell in enumerate(["QTY", "ITEM", "PART NO.", "DESCRIPTION"]):
        page.insert_text((xs[i], y), cell, fontsize=7)
    # Data stacks upward: A nearest the header, BC at the top.
    y = 1150
    for row in rows:
        for i, cell in enumerate(row):
            page.insert_text((xs[i], y), str(cell), fontsize=7)
        y -= 11
    # Decoy single-cell "-1" above the top row (item BC), as on the real sheet.
    page.insert_text((560, y - 4), "-1", fontsize=7)


def test_prefers_tall_right_side_table_over_short_decoy_lom(tmp_path: Path):
    """A 3-row LOM on a later page must not beat the 51-row right-side grid."""
    import fitz

    items = _platform_items()
    # Bottom-up write: first appended row is A (nearest header).
    data_rows = []
    for i, item in enumerate(items):
        if item == "BB":
            data_rows.append(["2", "BB", _BB_PART, _BB_DESC])
        else:
            data_rows.append(["1", item, f"1028{i:02d}-1", f"COMPONENT {item}"])

    pdf = tmp_path / "Time 102728- Weldment decoy.pdf"
    doc = fitz.open()
    # Pages 1-3: empty / iso (no table).
    for i in range(3):
        doc.new_page(width=792, height=1224).insert_text(
            (72, 72), f"ISO VIEW {i + 1}"
        )
    # Page 4 (index 3): the real tall right-side LIST OF MATERIAL.
    weld = doc.new_page(width=792, height=1224)
    weld.insert_text((40, 40), "WELDMENT, PLATFORM  102728-1  TIME MANUFACTURING")
    _write_right_side_lom_bottom_header(weld, data_rows)
    # Page 5 (index 4): short decoy LOM matching the live 3-row miss.
    decoy = doc.new_page(width=792, height=1224)
    decoy.insert_text((400, 200), "LIST OF MATERIAL", fontsize=10)
    decoy.insert_text((400, 220), "QTY | ITEM | PART NO. | DESCRIPTION", fontsize=8)
    decoy.insert_text((400, 236), "1 | B | 102709-1 | DECOY", fontsize=8)
    decoy.insert_text((400, 252), "1 | C | 100585-23 | DECOY", fontsize=8)
    decoy.insert_text((400, 268), "1 | SE | TAS | GARBAGE", fontsize=8)
    assert len(doc) == 5
    doc.save(pdf)
    doc.close()

    bom = extract_bom(pdf_path=pdf, bom_config="1")
    assert bom.method and bom.method.startswith("table_"), bom.notes
    assert bom.part_number_count == 51, [f"{r.item}:{r.part_no}" for r in bom.rows]
    bb = next(r for r in bom.rows if r.item == "BB")
    assert bb.qty == 2 and bb.part_no == _BB_PART
    parts = {r.part_no for r in bom.rows}
    assert "102709-1" not in parts
    assert "100585-23" not in parts
    assert not any(r.item == "SE" for r in bom.rows)


def test_p_prefix_weldment_pn_is_not_a_native_false_hit():
    """P904225-1 is a title-block weldment PN, not item P + 904225-1."""
    title = (
        "WELDMENT, PLATFORM\n"
        "P904225-1\n"
        "TIME MANUFACTURING\n"
        "DWG NO P904225-1\n"
        "SHEET 1 OF 1\n"
    )
    bom = extract_bom(text=title)
    parts = {r.part_no for r in bom.rows}
    assert "904225-1" not in parts
    assert "P904225-1" not in parts
    assert not any(r.item == "P" for r in bom.rows)

    hits = _parse_qty_item_part_hits([title], set())
    assert not any(str(h.get("part_no") or "") in {"904225-1", "P904225-1"} for h in hits)
    assert not any(h.get("item") == "P" and "904225" in str(h.get("part_no") or "") for h in hits)
    voted = _vote_bom_rows(hits, set())
    assert not any(r.part_no in {"904225-1", "P904225-1"} for r in voted)

    assert parse_ocr_row_strip("P904225-1 WELDMENT") is None
    harvested = harvest_ocr_row_strips(["P904225-1 WELDMENT", "DWG NO P904225-1"])
    assert not any(r.part_no in {"904225-1", "P904225-1"} for r in harvested.rows)
    # Spaced item P + part is a real balloon, not the glued drawing number.
    real_p = parse_ocr_row_strip("1 P 904225-1 TUBE")
    assert real_p is not None
    assert real_p["item"] == "P" and real_p["part_no"] == "904225-1"


def test_dash_column_index_qty_bleed_is_not_piece_count():
    """103516 live: 13/14/17/18/20 are column-index bleed, not 121 pcs."""
    letters = [c for c in "ABCDEFGHJKLMNPQRSTUVW"]
    assert len(letters) == 21
    bleed = {"A": 13, "B": 14, "D": 17, "E": 18, "F": 20}
    lines = [
        "LIST OF MATERIAL",
        "QTY | ITEM | PART NO. | DESCRIPTION",
    ]
    for i, item in enumerate(letters):
        q = bleed.get(item, 1)
        lines.append(f"{q} | {item} | 1035{i:02d}-1 | TUBE")
    bom = parse_material_list_text("\n".join(lines), bom_config="")
    assert len(bom.rows) == 21
    assert bom.piece_count == 21
    assert not any(r.qty >= 10 for r in bom.rows)

    strips = harvest_ocr_row_strips(
        [f"{bleed.get(item, 1)} {item} 1035{i:02d}-1 TUBE" for i, item in enumerate(letters)]
    )
    assert len(strips.rows) == 21
    assert not any(r.qty >= 10 for r in strips.rows)
    thirteen = parse_ocr_row_strip("13 A 103500-1 TUBE")
    assert thirteen is not None and thirteen["qty"] != 13
    assert thirteen["qty_clear"] is False
    glued = parse_ocr_row_strip("BB2 102727-4 TUBE, ROUND")
    assert glued["qty"] == 2 and glued["part_no"] == _BB_PART


def test_eco_and_title_block_rows_are_dropped():
    """28106 / 33612 / 21727 / 1007922 / P904225: ECO and title-block are not parts."""
    lines = [
        "A 16697-1 TUBE, SHORT",
        "B 16697-2 TUBE, LONG",
        "C 72143 ADDED —4 AND ITEM P",
        "E 61358 REVISION NOTE",
        "S 73207 CONFIG NOTE",
        "AN 89176-1 PROPERTY OF TIME MANUFACTURING",
        "B 56657 PROPERTY OF TIME",
        "BT 97879 THIS DRAWING IS THE PROPERTY OF TIME",
        "BBD 02727-4 TUBE, ROUND",
    ]
    bom = harvest_ocr_row_strips(lines)
    parts = {r.part_no for r in bom.rows}
    assert "16697-1" in parts and "16697-2" in parts
    assert _BB_PART in parts
    for junk in ("72143", "61358", "73207", "56657", "97879"):
        assert junk not in parts, junk
    # Dashed Time PNs stay even next to PROPERTY (page-title stamp is too wide).
    assert "16697-1" in parts
    bb = next(r for r in bom.rows if r.item == "BB")
    assert bb.qty == 2 and bb.part_no == _BB_PART
    assert parse_ocr_row_strip("C 72143 ADDED —4 AND ITEM P") is None
    dashed_prop = parse_ocr_row_strip("AN 89176-1 PROPERTY OF TIME MANUFACTURING")
    assert dashed_prop is not None and dashed_prop["part_no"] == "89176-1"

    cells = parse_material_list_text(
        "LIST OF MATERIAL\n"
        "QTY | ITEM | PART NO. | DESCRIPTION\n"
        "1 | A | 16697-1 | TUBE, SHORT\n"
        "1 | C | 72143 | ADDED —4 AND ITEM P\n"
        "2 | BB | 102727-4 | TUBE, ROUND\n"
    )
    cell_parts = {r.part_no for r in cells.rows}
    assert "16697-1" in cell_parts
    assert "72143" not in cell_parts
    assert _BB_PART in cell_parts


def test_live_surviving_eco_and_stripped_weldment_pn_are_dropped():
    """4725929 live leftovers: 5-digit bare + neighbor REV/ECO/PROPERTY; 904225-1."""
    lines = [
        "WELDMENT, PLATFORM",
        "P904225-1",
        "TIME MANUFACTURING",
        "A 89100-1 TUBE",
        "B 56657",
        "PROPERTY OF TIME",
        "BT 97879",
        "REV",
        "E 61358 REV",
        "S 73207 CONFIG",
        "D 73049",
        "ECO",
        "AN 89176-1",
        "PROPERTY OF TIME MANUFACTURING",
        "B 904225-1",
        "M 94560 GATE, FABRICATION",
        "BBD 02727-4 TUBE, ROUND",
    ]
    bom = harvest_ocr_row_strips(lines)
    parts = {r.part_no for r in bom.rows}
    assert "89100-1" in parts
    assert "94560" in parts
    assert _BB_PART in parts
    for junk in ("56657", "97879", "61358", "73207", "73049", "904225-1", "P904225-1"):
        assert junk not in parts, junk
    # 89176-1 is dashed — do not drop it for PROPERTY on a neighbor/title band.
    bb = next(r for r in bom.rows if r.item == "BB")
    assert bb.qty == 2 and bb.part_no == _BB_PART


def test_first_release_added_config_and_garbled_eco_drop_five_digit_only():
    """5-digit bare junk drops; dashed Time PNs stay even if the page says PROPERTY."""
    assert parse_ocr_row_strip("B 56657 FIRST RELEASE TO PRODUCTION") is None
    assert parse_ocr_row_strip("8 S 73207 ADDED CONFIGURATION") is None
    garbled = parse_ocr_row_strip("8 S 73207 avoeos'conricuranon")
    assert garbled is None

    # Page-title PROPERTY must not wipe dashed LOM rows (1004747 / 33612 regression).
    far = harvest_ocr_row_strips(
        [
            "A 1004806-1 HOSE",
            "B 1004806-2",
            "C 11694-2 TUBE",
            "D 1004738-1",
            "E 1004739-1",
            "F 1004711-1",
            "G 1004740-1",
            "H 1004741-1",
            "J 1004744-1",
            "K 1004744-2",
            "L 1004737-1",
            "M 25060-6",
            "6993-1 HOSE GUIDE",
            "A 89176-1",
            "G 89100-1 TUBE",
            "N 28275-1",
            "P 28275-2",
            "Q 28275-3",
            "R 28276-1",
            "S 28281-1",
            "T 28282-1",
            "U 28283-1",
            "V 33638-1",
            "C 103522-1 PLATE",
            "BBD 02727-4 TUBE, ROUND",
        ],
        page_text="WELDMENT P904225-1\nTHIS DRAWING IS THE PROPERTY OF TIME MANUFACTURING\nFIRST RELEASE",
    )
    parts = {r.part_no for r in far.rows}
    for keep in (
        "1004806-1",
        "1004806-2",
        "11694-2",
        "1004738-1",
        "1004739-1",
        "1004711-1",
        "1004740-1",
        "1004741-1",
        "1004744-1",
        "1004744-2",
        "1004737-1",
        "25060-6",
        "6993-1",
        "89176-1",
        "89100-1",
        "28275-1",
        "28275-2",
        "28275-3",
        "28276-1",
        "28281-1",
        "28282-1",
        "28283-1",
        "33638-1",
        "103522-1",
        _BB_PART,
    ):
        assert keep in parts, keep
    assert len(parts) >= 15

    page = harvest_ocr_row_strips(
        [
            "B 56657 FIRST RELEASE TO PRODUCTION",
            "BT 97879",
            "8 S 73207 avoeos'conricuranon",
            "A 103500-1 TUBE",
            "C 103522-1 PLATE",
            "M 94560 GATE, FABRICATION",
            "6993-1 HOSE GUIDE",
        ]
    )
    parts2 = {r.part_no for r in page.rows}
    assert "56657" not in parts2
    assert "97879" not in parts2
    assert "73207" not in parts2
    assert "103500-1" in parts2
    assert "103522-1" in parts2
    assert "94560" in parts2
    assert "6993-1" in parts2


def test_hyphenless_dashed_dupes_are_dropped():
    """103516 live: 1035371 / 1035221 / 1035281 are 103537-1 etc. without the hyphen."""
    bom = harvest_ocr_row_strips(
        [
            "A 103537-1 TUBE",
            "1035371 TUBE",
            "B 103522-1 PLATE",
            "1035221",
            "C 103528-1 RAIL",
            "1035281 RAIL",
            "M 94560 GATE, FABRICATION",
        ]
    )
    parts = {r.part_no for r in bom.rows}
    assert "103537-1" in parts and "1035371" not in parts
    assert "103522-1" in parts and "1035221" not in parts
    assert "103528-1" in parts and "1035281" not in parts
    assert "94560" in parts


def test_weldment_pn_reject_is_exact_not_10047_prefix():
    """1004747-1 title must not drop 10047xx / 1004806 / 11694-2 LOM siblings."""
    keep = [
        "1004711-1",
        "1004737-1",
        "1004738-1",
        "1004739-1",
        "1004740-1",
        "1004741-1",
        "1004744-1",
        "1004744-2",
        "1004806-1",
        "1004806-2",
        "11694-2",
        "25060-6",
        "6993-1",
    ]
    strips = [
        f"{pn} {'HOSE GUIDE' if pn == '6993-1' else 'TUBE'}" for pn in keep
    ]
    strips.extend(
        [
            "N 28275-1",
            "P 28275-2",
            "8 S 73207 avoeos'conricuranon",
            "B 56657 FIRST RELEASE TO PRODUCTION",
            "BT 97879",
        ]
    )
    blob = (
        "WELDMENT, PLATFORM 1004747-1 TIME MANUFACTURING SHEET 1 OF 2 "
        + " ".join(f"{pn} TUBE" for pn in keep)
        + " THIS DRAWING IS THE PROPERTY OF TIME MANUFACTURING"
    )
    bom = harvest_ocr_row_strips(strips, page_text=blob)
    parts = {r.part_no for r in bom.rows}
    for pn in keep:
        assert pn in parts, pn
    assert "28275-1" in parts and "28275-2" in parts
    assert "1004747-1" not in parts
    assert "73207" not in parts
    assert "56657" not in parts
    assert "97879" not in parts
    assert len([p for p in parts if p in keep]) == 13


def test_bracket_three_only_for_4digit_stem_not_25009():
    """`[3688-9` → 33688-9. Do not turn `[25009-2` / `[32259-1` into 3xxxxx."""
    aq = parse_ocr_row_strip('AQ" [3688-9 JEXPANDED METAL PLATE')
    assert aq is not None and aq["part_no"] == "33688-9"
    two = parse_ocr_row_strip("A [25009-2 TUBE")
    assert two is not None and two["part_no"] == "25009-2"
    three = parse_ocr_row_strip("B [32259-1 PLATE")
    assert three is not None and three["part_no"] == "32259-1"
    assert parse_ocr_row_strip("C 325009-2 TUBE")["part_no"] == "325009-2"


def test_p904225_no_dash_title_rejects_904225_1_only():
    """P904225 weldment title — reject exact / P-stripped, not other dashed PNs."""
    bom = harvest_ocr_row_strips(
        [
            "A 89100-1 TUBE",
            "B 904225-1",
            "AN 89176-1",
            "M 94560 GATE, FABRICATION",
            "G 1004738-1 TUBE",
        ],
        page_text="WELDMENT, PLATFORM P904225 TIME MANUFACTURING",
    )
    parts = {r.part_no for r in bom.rows}
    assert "904225-1" not in parts
    assert "P904225" not in parts
    assert "89100-1" in parts
    assert "89176-1" in parts
    assert "94560" in parts
    assert "1004738-1" in parts


def test_1007922_keeps_filler_and_outrigger_not_weldment():
    """1007922-1 is the weldment. 14149-1 FILLER and 1007830-1 stay."""
    strips = [
        "14149-1",
        "FILLER",
        "1007830-1 OUTRIGGER LEG",
        "A 1007800-1 TUBE",
        "6993-1 HOSE GUIDE",
        "N 28275-1",
    ]
    page = (
        "SHEET 1 OF 2\n"
        "LIST OF MATERIAL\n"
        "14149-1\n"
        "FILLER\n"
        "1007830-1\n"
        "OUTRIGGER LEG\n"
        "WELDMENT, PLATFORM\n"
        "1007922-1\n"
        "TIME MANUFACTURING\n"
        "SHEET 1 OF 2\n"
    )
    bom = harvest_ocr_row_strips(strips, page_text=page)
    parts = {r.part_no for r in bom.rows}
    assert "14149-1" in parts
    assert "1007830-1" in parts
    assert "1007800-1" in parts
    assert "6993-1" in parts
    assert "28275-1" in parts
    assert "1007922-1" not in parts


def test_103516_keeps_dashed_103535_not_hyphenless_dupe():
    """103535-1 is a real dashed 1035xx row, not a hyphen-less dupe of the title."""
    strips = [
        "A 103537-1 TUBE",
        "1035371 TUBE",
        "B 103535-1 PLATE",
        "103535-1",
        "C 103522-1 RAIL",
        "1035221",
    ]
    page = (
        "WELDMENT, PLATFORM 103516-1 TIME MANUFACTURING\n"
        "SHEET 1 OF 2\n"
        "103535-1\n"
        "PLATE\n"
        "103537-1 TUBE\n"
    )
    bom = harvest_ocr_row_strips(strips, page_text=page)
    parts = {r.part_no for r in bom.rows}
    assert "103535-1" in parts
    assert "103537-1" in parts and "1035371" not in parts
    assert "103522-1" in parts and "1035221" not in parts
    assert "103516-1" not in parts


def test_p904225_spaced_and_trailing_title_still_drops_904225_1():
    """Live P904225-1: spaced title OCR and title-after-LOM blob still reject 904225-1."""
    assert parse_ocr_row_strip("P 904225-1 WELDMENT") is None
    trailing = (
        "A 89100-1 TUBE AN 89176-1 28275-1 "
        "WELDMENT, PLATFORM P 904225-1 TIME MANUFACTURING SHEET 1 OF 1"
    )
    bom = harvest_ocr_row_strips(
        [
            "A 89100-1 TUBE",
            "B 904225-1",
            "P 904225-1 WELDMENT",
            "AN 89176-1",
            "G P904226-1 SUPPORT",
        ],
        page_text=trailing,
    )
    parts = {r.part_no for r in bom.rows}
    assert "904225-1" not in parts
    assert "P904225-1" not in parts
    assert "89100-1" in parts
    assert "89176-1" in parts
    assert "904226-1" in parts or "P904226-1" in parts


def test_97879_no_noun_is_junk_94560_gate_stays():
    assert parse_ocr_row_strip("BT 97879") is None
    bom = harvest_ocr_row_strips(
        [
            "A 16697-1 TUBE",
            "BT 97879",
            "M 94560 GATE, FABRICATION",
        ]
    )
    parts = {r.part_no for r in bom.rows}
    assert "97879" not in parts
    assert "94560" in parts
    assert "16697-1" in parts


def test_unread_band_keeps_time_pn_and_4digit_hose_guide():
    """1004611 / 1004747-1: keep unread Time PNs; 6993-1 hose guide; drop AE/BE/BS junk."""
    lines = [
        "A 100100-1 TUBE",
        "B 100101-1 PLATE",
        "",
        "100102-1 SUPPORT",
        "6993-1 HOSE GUIDE",
        "AE 56657 PROPERTY OF TIME",
        "BE 97879 THIS DRAWING IS THE PROPERTY OF TIME",
        "BS 72143 ADDED ITEM C",
    ]
    bom = harvest_ocr_row_strips(lines)
    parts = {r.part_no for r in bom.rows}
    assert "100100-1" in parts
    assert "100101-1" in parts
    assert "100102-1" in parts
    assert "6993-1" in parts
    assert "56657" not in parts
    assert "97879" not in parts
    assert "72143" not in parts
    hose = parse_ocr_row_strip("6993-1 HOSE GUIDE")
    assert hose is not None and hose["part_no"] == "6993-1"


def test_p904225_drops_property_row_keeps_table_child_not_folder(tmp_path: Path):
    """P904225-1 is not a BOM row; AN=89176-1 PROPERTY OF TIME drops; table child stays."""
    text = (
        "WELDMENT, PLATFORM\n"
        "P904225-1\n"
        "TIME MANUFACTURING\n"
        "DWG NO P904225-1\n"
        "LIST OF MATERIAL\n"
        "QTY | ITEM | PART NO. | DESCRIPTION\n"
        "1 | A | 89100-1 | TUBE\n"
        "1 | G | P904226-1 | SUPPORT\n"
        "1 | AN | 89176-1 | PROPERTY OF TIME MANUFACTURING\n"
    )
    bom = extract_bom(text=text)
    parts = {r.part_no for r in bom.rows}
    assert "P904225-1" not in parts
    assert "904225-1" not in parts
    assert "89100-1" in parts
    # 89176-1 is dashed; page/cell PROPERTY must not over-drop dashed LOM PNs.
    assert "904226-1" in parts or "P904226-1" in parts
    assert bom.method and bom.method.startswith("table_")

    child = parse_ocr_row_strip("1 G P904226-1 SUPPORT")
    assert child is not None
    assert child["item"] == "G"
    assert "904226" in child["part_no"]

    # Folder children that are not in the table must not be padded.
    pdf = tmp_path / "P904225-1.pdf"
    _write_lom_pdf(
        pdf,
        ["QTY", "ITEM", "PART NO.", "DESCRIPTION"],
        [
            ["1", "A", "89100-1", "TUBE"],
            ["1", "G", "89101-1", "PLATE"],
        ],
        title="WELDMENT, PLATFORM  P904225-1  TIME MANUFACTURING",
    )
    lib = tmp_path / "library"
    lib.mkdir()
    for extra in ("P904226-1.pdf", "P904230-1.pdf", "P904231-1.pdf", "P904245-1.pdf"):
        (lib / extra).write_bytes(b"%PDF-1.4\n%\n")
    padded = extract_bom(pdf_path=pdf, library_folder=lib, bom_config="1")
    pad_parts = {r.part_no for r in padded.rows}
    assert padded.method and padded.method.startswith("table_")
    assert "89100-1" in pad_parts
    assert "89101-1" in pad_parts
    assert not any("904226" in p or "904230" in p or "904231" in p or "904245" in p for p in pad_parts)
    assert "P904225-1" not in pad_parts
    assert "904225-1" not in pad_parts


def test_qty_over_20_is_junk_unless_glued_item_qty():
    """99 is OCR junk; 7 on a rail is dimension bleed; BB2/AX2 glued qty 2 stays."""
    huge = parse_ocr_row_strip("99 A 100177-2 PLATE")
    assert huge is not None
    assert huge["item"] == "A"
    assert huge["qty"] != 99
    assert huge["qty"] <= 20
    bleed = parse_ocr_row_strip("7 S 100200-1 RAIL, HORIZONTAL")
    assert bleed["qty"] != 7
    assert bleed["qty_clear"] is False
    bb = parse_ocr_row_strip("BB2 102727-4 TUBE, ROUND")
    assert bb["item"] == "BB" and bb["qty"] == 2 and bb["part_no"] == _BB_PART
    ax = parse_ocr_row_strip("AX2 1102726-1 HOOK")
    assert ax["item"] == "AX" and ax["qty"] == 2
    lines = harvest_material_list_lines(
        "LIST OF MATERIAL\nQTY ITEM PART NO. DESCRIPTION\n99 A 100177-2 PLATE\n"
        "2 BB 102727-4 TUBE, ROUND\n"
    )
    by_item = {r.item: r for r in lines.rows}
    if "A" in by_item:
        assert by_item["A"].qty != 99
        assert by_item["A"].qty <= 20
    assert by_item["BB"].qty == 2


def test_time_ten_set_layout_fixtures_do_not_regress():
    """Synthetic 10-weldment layouts. Do not claim live 10-set passed."""
    items = time_item_letters(through="BC")
    assert len(items) == 51
    assert "I" not in items and "O" not in items
    assert "AI" not in items and "AO" not in items
    assert items[items.index("Z") + 1] == "AA"
    assert items[-3:] == ["BA", "BB", "BC"]

    dash = """
LIST OF MATERIAL
-2 | -1 | ITEM | PART NO. | DESCRIPTION
1 | - | A | 16697-1 | TUBE, SHORT
- | 1 | B | 16697-2 | TUBE, LONG
2 | 1 | C | 15864-2 | STIFFENER
"""
    dash1 = parse_material_list_text(dash, bom_config="1")
    assert {r.item for r in dash1.rows} == {"B", "C"}
    assert next(r for r in dash1.rows if r.item == "C").qty == 1
    dash2 = parse_material_list_text(dash, bom_config="2")
    assert {r.item for r in dash2.rows} == {"A", "C"}
    assert next(r for r in dash2.rows if r.item == "C").qty == 2

    tall = parse_material_list_cells(_platform_cell_rows())
    decoy = parse_material_list_cells(
        [
            ["QTY", "ITEM", "PART NO.", "DESCRIPTION"],
            ["1", "B", "102709-1", "DECOY"],
            ["1", "C", "100585-23", "DECOY"],
            ["1", "D", "102711-1", "CABLE"],
        ]
    )
    best = pick_best_material_list([decoy, tall])
    assert best is tall
    assert len(best.rows) == 51
    bb = next(r for r in best.rows if r.item == "BB")
    assert bb.qty == 2 and bb.part_no == _BB_PART
    assert "102709-1" not in {r.part_no for r in best.rows}

    gapped = parse_material_list_cells(_platform_cell_rows(drop={"C", "AA"}))
    joined = " ".join(gapped.notes).lower()
    assert "do not pad" in joined
    assert not any(r.item in {"C", "AA"} for r in gapped.rows)
