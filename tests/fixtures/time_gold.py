"""Locked Time drawing gold — one row to add a 12th weldment.

Count-locked LOM workbooks encode Kyle-confirmed PN/pcs totals. 1001898-1
uses the live locked part list. Desktop ``*-LOM.xlsx`` files were not on
this VM for the other PNs; replace a count-locked sheet with Kyle's file
by dropping it into ``tests/fixtures/lom/{pn}-LOM.xlsx``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quote_core.lom_xlsx import write_lom_xlsx

FIXTURE_DIR = Path(__file__).resolve().parent / "lom"

# Letters skip I/O (Time balloon convention).
_LETTERS = [c for c in "ABCDEFGHJKLMNPQRSTUVWXYZ"]


def _item_letter(i: int) -> str:
    if i < len(_LETTERS):
        return _LETTERS[i]
    return f"{_LETTERS[i % len(_LETTERS)]}{i // len(_LETTERS)}"


def qty_mix_rows(
    part_prefix: int,
    mix: list[tuple[int, int]],
    *,
    extra: list[tuple[str, int, str, str]] | None = None,
    other_dash: list[tuple[str, str, str]] | None = None,
) -> list[list[str]]:
    """Build a Time dash grid. ``mix`` is (n_parts, qty_on_dash_1)."""
    header = ["-4", "-3", "-2", "-1", "ITEM", "PART NO", "DESCRIPTION"]
    rows = [header]
    i = 0
    for n_parts, qty in mix:
        for _ in range(n_parts):
            letter = _item_letter(i)
            rows.append(
                ["-", "-", "-", str(qty), letter, f"{part_prefix}-{i + 1}", f"PLATE {letter}"]
            )
            i += 1
    for item, qty, pn, desc in extra or []:
        rows.append(["-", "-", "-", str(qty), item, pn, desc])
    for item, pn, desc in other_dash or []:
        rows.append(["-", "-", "1", "-", item, pn, desc])
    return rows


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


def rows_1001898() -> list[list[str]]:
    header = ["-5", "-4", "-3", "-2", "-1", "ITEM", "PART NO", "DESCRIPTION"]
    rows = [header]
    for item, qty, pn, desc in DASH_1001898:
        rows.append(["-", "-", "-", "-", str(qty), item, pn, desc])
    for item, pn, desc in _1001898_OTHER_DASH:
        rows.append(["-", "-", "-", "1", "-", item, pn, desc])
    # Paint notes are not qty — omitted, does not become 1 pc.
    rows.append(["-", "-", "-", "-", "20 PLCS", "AD", "1999999-1", "PAINT NOTE"])
    return rows


def rows_1004747() -> list[list[str]]:
    """Dash -1 is 14 PN / 18 pcs. -2 is populated so a wrong dash under-counts."""
    header = ["-4", "-3", "-2", "-1", "ITEM", "PART NO", "DESCRIPTION"]
    rows = [header]
    for i, letter in enumerate("ABCDEFGHIJ"):
        pn = f"10048{10 + i:02d}-1"
        rows.append(["-", "-", "-", "1", letter, pn, f"PLATE {letter}"])
    rows.append(["-", "-", "1", "2", "K", "1004820-1", "GUSSET"])
    rows.append(["-", "-", "1", "2", "L", "1004821-1", "STIFFENER"])
    rows.append(["-", "-", "1", "2", "M", "1004822-1", "PAD"])
    rows.append(["-", "-", "1", "2", "N", "1004823-1", "CLIP"])
    return rows


@dataclass
class LomGold:
    part_key: str
    pn: int
    pcs: int
    title: str
    source: str  # locked_rows | count_locked
    builder: Any
    notes: str = ""
    extra_sheets: dict[str, list[list[str]]] = field(default_factory=dict)
    require_pn: tuple[str, ...] = ()
    forbid_pn: tuple[str, ...] = ()
    empty_l2: tuple[str, ...] = ()

    def drawn_rows(self) -> list[list[str]]:
        return self.builder()


def _gold(
    part_key: str,
    pn: int,
    pcs: int,
    *,
    title: str,
    source: str,
    builder,
    notes: str = "",
    extra_sheets: dict[str, list[list[str]]] | None = None,
    require_pn: tuple[str, ...] = (),
    forbid_pn: tuple[str, ...] = (),
    empty_l2: tuple[str, ...] = (),
) -> LomGold:
    return LomGold(
        part_key=part_key,
        pn=pn,
        pcs=pcs,
        title=title,
        source=source,
        builder=builder,
        notes=notes,
        extra_sheets=extra_sheets or {},
        require_pn=require_pn,
        forbid_pn=forbid_pn,
        empty_l2=empty_l2,
    )


def _103516_parent() -> list[list[str]]:
    # 20 PN / 30 pcs on parent including 103535-1 GATE WELDMENT.
    # 13×1 + 7×2 + weldment 1 = 21? We need 20 parent PN / 30 pcs including weldment.
    # 10×1 + 9×2 + 103535-1×1 = 20 PN / 10+18+1 = 29. Close.
    # 11×1 + 8×2 + weldment 1 = 20 PN / 11+16+1 = 28.
    # 9×1 + 10×2 + weldment 1 = 20 / 9+20+1 = 30. Yes.
    rows = qty_mix_rows(103516, [(9, 1), (10, 2)])
    rows.append(["-", "-", "-", "1", "U", "103535-1", "GATE WELDMENT"])
    return rows


def _103516_child() -> list[list[str]]:
    # 7 PN / 15 pcs → parent 20/30 + child 7/15 = 27/45 (weldment kept).
    # 20 parent includes 103535-1; child 7 new PNs → 27 PN.
    # 4×1 + 3×? 4+3=7, 4+3q=15 → 3q=11 no.
    # 3×1 + 4×3 = 3+12=15. Yes.
    return qty_mix_rows(103536, [(3, 1), (4, 3)])


def _105098_parent() -> list[list[str]]:
    rows = qty_mix_rows(105098, [(8, 1)])
    rows.append(["-", "-", "-", "1", "J", "103603-1", "CHILD TABLE PLATE"])
    return rows


def _105098_child_ignored() -> list[list[str]]:
    return qty_mix_rows(103604, [(12, 1)])


def _1004611_rows() -> list[list[str]]:
    # 21×3 + S80054-1×3 = 22 PN / 66 pcs; gasket line is locked.
    rows = qty_mix_rows(1004611, [(21, 3)])
    rows.append(["-", "-", "-", "3", "Z", "S 80054-1", '10" GASKET'])
    return rows


LOM_GOLD: list[LomGold] = [
    _gold(
        "102728-1",
        51,
        97,
        title="102728-1",
        source="count_locked",
        builder=lambda: qty_mix_rows(102728, [(5, 1), (46, 2)]),
        notes="5×1 + 46×2. Replace with Desktop 102728-1-LOM.xlsx when available.",
    ),
    _gold(
        "1004747-1",
        14,
        18,
        title="1004747",
        source="count_locked",
        builder=rows_1004747,
        notes="Dash trap: bare/ -1 title uses column -1, never folder -2.",
        forbid_pn=(),
    ),
    _gold(
        "28106-1",
        11,
        13,
        title="28106-1",
        source="count_locked",
        builder=lambda: qty_mix_rows(28106, [(9, 1), (2, 2)]),
        notes="9×1 + 2×2.",
    ),
    _gold(
        "1007922-1",
        6,
        14,
        title="1007922-1",
        source="count_locked",
        builder=lambda: qty_mix_rows(1007922, [(2, 1), (4, 3)]),
        notes="2×1 + 4×3. Count-locked; Desktop sheet not on this VM.",
    ),
    _gold(
        "21727-1",
        11,
        16,
        title="21727-1",
        source="count_locked",
        builder=lambda: qty_mix_rows(21727, [(6, 1), (5, 2)]),
        notes="6×1 + 5×2. Count-locked; Desktop sheet not on this VM.",
    ),
    _gold(
        "33612-1",
        21,
        47,
        title="33612-1",
        source="count_locked",
        builder=lambda: qty_mix_rows(33612, [(7, 1), (10, 2), (4, 5)]),
        notes="7×1 + 10×2 + 4×5. Count-locked; Desktop sheet not on this VM.",
    ),
    _gold(
        "105098-1",
        9,
        9,
        title="105098-1",
        source="count_locked",
        builder=_105098_parent,
        extra_sheets={"103603-1": _105098_child_ignored()},
        notes="Parent LOM only — do not roll up 103603-1 child table.",
        forbid_pn=tuple(f"103604-{i}" for i in range(1, 13)),
        require_pn=("103603-1",),
    ),
    _gold(
        "103516",
        27,
        45,
        title="103516",
        source="count_locked",
        builder=_103516_parent,
        extra_sheets={"103535-1": _103516_child()},
        notes="Nested 103535-1 GATE WELDMENT tab rolls up. Empty L2 fails.",
        require_pn=("103535-1",),
    ),
    _gold(
        "P904225-1",
        11,
        23,
        title="P904225-1",
        source="count_locked",
        builder=lambda: qty_mix_rows(
            904225,
            [(4, 1), (6, 3)],
            extra=[("K", 1, "P904225-1", "WELDMENT PLATE")],
        ),
        notes="4×1 + 6×3 + P904225-1. Count-locked; Desktop sheet not on this VM.",
        require_pn=("P904225-1",),
    ),
    _gold(
        "1004611-1",
        22,
        66,
        title="1004611-1",
        source="count_locked",
        builder=_1004611_rows,
        notes='22×3 including locked S 80054-1 10" gasket.',
        require_pn=("S80054-1",),
    ),
    _gold(
        "1001898-1",
        17,
        27,
        title="1001898-1",
        source="locked_rows",
        builder=rows_1001898,
        notes="Live locked dash -1 part list.",
        require_pn=("14500-1", "1005940-1", "50029-7"),
        forbid_pn=("1001899-1", "1999999-1"),
    ),
]


CLASSIFY_CASES: list[tuple[str, str, str]] = [
    ("14500-1", "PEDESTAL TOP PLATE", "Cad"),
    ("14501-1", "RESERVOIR TOP PLATE", "Cad"),
    ("1005966-1", "PEDESTAL BOTTOM PLATE", "Cad"),
    ("9905-1", "MOUNTING PLATE, EMER POWER", "Cad"),
    ("1005940-1", "PEDESTAL GUSSET", "Cad"),
    ("1001880-2", "PEDESTAL TUBE", "Linear"),
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
