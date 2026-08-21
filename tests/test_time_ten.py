"""Ordered Time-10 LOM fixtures. Synthetic only — do not claim live Excel.

Kyle order: 102728-1 → 28106-1 → 1004747-1 → 1004611 → 103516 →
105098-1 → 33612-1 → 21727-1 → 1007922-1 → P904225-1.

102728-1 qty (51/97) is still first. 28106-1 (11/13) and 1004747-1
(14/18 numbered 1–17) are Kyle-locked. The rest use only PNs already
documented in this repo. Live proof is the laptop clip → xlsx.
Do not merge until all 10 live sheets match.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from quote_core.bom import extract_bom
from quote_core.bom_table import (
    harvest_ocr_row_strips,
    parse_material_list_cells,
    parse_material_list_text,
)

from tests.test_bom_table import (
    _KYLE_1004747_1,
    _KYLE_102728_1,
    _KYLE_28106_1,
    _assert_kyle_1004747_1,
    _assert_kyle_102728_1,
    _assert_kyle_28106_1,
    _assert_kyle_xlsx,
    _kyle_1004747_cell_rows,
    _kyle_28106_cell_rows,
    _write_lom_pdf,
)

TIME_TEN_ORDER = (
    "102728-1",
    "28106-1",
    "1004747-1",
    "1004611",
    "103516",
    "105098-1",
    "33612-1",
    "21727-1",
    "1007922-1",
    "P904225-1",
)


@dataclass(frozen=True)
class TimeTenSpec:
    key: str
    title: str
    bom_config: str
    kyle_locked: bool
    header: list[str]
    rows: list[tuple[str, int, str, str]]
    reject_pns: frozenset[str]
    library_bait: tuple[str, ...] = ()
    extra_cells: list[list[str]] = field(default_factory=list)
    status: str = "working_fixture"


# Kyle-locked 1004747-1: 14 unique / 18 pcs. Live 74f3ab3 reported 15 —
# it leaked 1004806-2 / 11694-2 / 25009-2 and missed 1004773-1 / 1004743-1.

_103516: list[tuple[str, int, str, str]] = [
    ("A", 1, "103537-1", "TUBE"),
    ("B", 1, "103522-1", "PLATE"),
    ("C", 1, "103528-1", "RAIL"),
    ("D", 1, "103535-1", "PLATE"),
    ("M", 1, "94560", "GATE, FABRICATION"),
]

_1007922_1: list[tuple[str, int, str, str]] = [
    ("A", 1, "1007800-1", "TUBE"),
    ("B", 1, "14149-1", "FILLER"),
    ("C", 1, "1007830-1", "OUTRIGGER LEG"),
    ("D", 1, "6993-1", "HOSE GUIDE"),
    ("N", 1, "28275-1", "TUBE"),
]

_P904225_1: list[tuple[str, int, str, str]] = [
    ("A", 1, "89100-1", "TUBE"),
    ("G", 1, "P904226-1", "SUPPORT"),
    ("M", 1, "94560", "GATE, FABRICATION"),
    ("AN", 1, "89176-1", "TUBE"),
]


def _qty_header_rows(rows: list[tuple[str, int, str, str]]) -> list[list[str]]:
    cells = [["QTY", "ITEM", "PART NO.", "DESCRIPTION"]]
    for item, qty, pn, desc in rows:
        cells.append([str(qty), item, pn, desc])
    return cells


def _specs() -> dict[str, TimeTenSpec]:
    return {
        "102728-1": TimeTenSpec(
            key="102728-1",
            title="WELDMENT, PLATFORM  102728-1  TIME MANUFACTURING",
            bom_config="",
            kyle_locked=True,
            header=["QTY", "ITEM", "PART NO.", "DESCRIPTION"],
            rows=list(_KYLE_102728_1),
            reject_pns=frozenset({"102728-1"}),
            library_bait=("102726-1.pdf", "102729.pdf"),
            status="kyle_locked",
        ),
        "28106-1": TimeTenSpec(
            key="28106-1",
            title="LOWER BOOM WELDMENT  28106-1  TIME MANUFACTURING",
            bom_config="-1",
            kyle_locked=True,
            header=["-4", "-3", "-2", "-1", "ITEM", "PART NO.", "DESCRIPTION"],
            rows=list(_KYLE_28106_1),
            reject_pns=frozenset({"28106-1", "16697-1", "16697-3", "16697-4"}),
            extra_cells=_kyle_28106_cell_rows()[1:],
            status="kyle_locked",
        ),
        "1004747-1": TimeTenSpec(
            key="1004747-1",
            title="OUTER BOOM WELDMENT - 1004747-1  TIME MANUFACTURING",
            bom_config="-1",
            kyle_locked=True,
            header=["1004747-1", "1004747-2", "ITEM", "PART NO.", "DESCRIPTION", "NOTES"],
            rows=list(_KYLE_1004747_1),
            reject_pns=frozenset(
                {
                    "1004747-1",
                    "1004806-2",
                    "11694-2",
                    "25009-2",
                    "56657",
                    "97879",
                    "73207",
                }
            ),
            extra_cells=_kyle_1004747_cell_rows()[1:],
            library_bait=("1004748-1.pdf",),
            status="kyle_locked",
        ),
        "1004611": TimeTenSpec(
            key="1004611",
            title="WELDMENT, PLATFORM  1004611-1  TIME MANUFACTURING",
            bom_config="",
            kyle_locked=False,
            header=["QTY", "ITEM", "PART NO.", "DESCRIPTION"],
            rows=[("A", 1, "6993-1", "HOSE GUIDE")],
            reject_pns=frozenset({"1004611-1", "1004611", "56657", "97879", "72143"}),
            status="needs_kyle_excel",
        ),
        "103516": TimeTenSpec(
            key="103516",
            title="WELDMENT, PLATFORM  103516-1  TIME MANUFACTURING",
            bom_config="",
            kyle_locked=False,
            header=["QTY", "ITEM", "PART NO.", "DESCRIPTION"],
            rows=list(_103516),
            reject_pns=frozenset({"103516-1", "103516", "1035371", "1035221", "1035281"}),
            status="needs_kyle_excel",
        ),
        "105098-1": TimeTenSpec(
            key="105098-1",
            title="WELDMENT, PLATFORM  105098-1  TIME MANUFACTURING",
            bom_config="",
            kyle_locked=False,
            header=["QTY", "ITEM", "PART NO.", "DESCRIPTION"],
            rows=[("M", 1, "94560", "GATE, FABRICATION")],
            reject_pns=frozenset({"105098-1", "105098", "56657", "97879"}),
            status="needs_kyle_excel",
        ),
        "33612-1": TimeTenSpec(
            key="33612-1",
            title="WELDMENT, PLATFORM  33612-1  TIME MANUFACTURING",
            bom_config="",
            kyle_locked=False,
            header=["QTY", "ITEM", "PART NO.", "DESCRIPTION"],
            rows=[
                ("A", 1, "89176-1", "TUBE"),
                ("M", 1, "94560", "GATE, FABRICATION"),
            ],
            reject_pns=frozenset({"33612-1", "33612", "56657", "97879", "72143"}),
            status="needs_kyle_excel",
        ),
        "21727-1": TimeTenSpec(
            key="21727-1",
            title="WELDMENT, PLATFORM  21727-1  TIME MANUFACTURING",
            bom_config="",
            kyle_locked=False,
            header=["QTY", "ITEM", "PART NO.", "DESCRIPTION"],
            rows=[
                ("A", 1, "16697-1", "TUBE, SHORT"),
                ("B", 1, "16697-2", "TUBE, LONG"),
            ],
            reject_pns=frozenset({"21727-1", "21727", "72143", "61358", "73207"}),
            status="needs_kyle_excel",
        ),
        "1007922-1": TimeTenSpec(
            key="1007922-1",
            title="WELDMENT, PLATFORM  1007922-1  TIME MANUFACTURING",
            bom_config="",
            kyle_locked=False,
            header=["QTY", "ITEM", "PART NO.", "DESCRIPTION"],
            rows=list(_1007922_1),
            reject_pns=frozenset({"1007922-1", "1007922"}),
            library_bait=("1007923-1.pdf",),
            status="needs_kyle_excel",
        ),
        "P904225-1": TimeTenSpec(
            key="P904225-1",
            title="WELDMENT, PLATFORM  P904225-1  TIME MANUFACTURING",
            bom_config="",
            kyle_locked=False,
            header=["QTY", "ITEM", "PART NO.", "DESCRIPTION"],
            rows=list(_P904225_1),
            reject_pns=frozenset({"P904225-1", "904225-1", "P904225", "904225"}),
            library_bait=("P904230-1.pdf", "P904231-1.pdf", "P904245-1.pdf"),
            status="needs_kyle_excel",
        ),
    }


def _cells_for(spec: TimeTenSpec) -> list[list[str]]:
    if spec.key == "28106-1":
        return _kyle_28106_cell_rows()
    if spec.key == "1004747-1":
        return _kyle_1004747_cell_rows()
    cells = [list(spec.header)]
    cells.extend([str(qty), item, pn, desc] for item, qty, pn, desc in spec.rows)
    cells.extend(spec.extra_cells)
    return cells


def _assert_grid(bom, spec: TimeTenSpec) -> None:
    if spec.key == "102728-1":
        _assert_kyle_102728_1(bom)
        return
    if spec.key == "28106-1":
        _assert_kyle_28106_1(bom)
        return
    if spec.key == "1004747-1":
        _assert_kyle_1004747_1(bom)
        return
    by_item = {r.item: r for r in bom.rows}
    assert len(bom.rows) == len(spec.rows), [f"{r.item}:{r.part_no}×{r.qty}" for r in bom.rows]
    assert sum(r.qty for r in bom.rows) == sum(q for _i, q, _p, _d in spec.rows)
    for item, qty, pn, _desc in spec.rows:
        assert item in by_item, item
        got = str(by_item[item].part_no or "")
        want = pn
        if spec.key == "P904225-1" and "904226" in want:
            assert "904226" in got, (item, got, want)
        else:
            assert got == want, (item, got, want)
        assert by_item[item].qty == qty, (item, by_item[item].qty, qty)
    parts = {str(r.part_no or "") for r in bom.rows}
    for junk in spec.reject_pns:
        assert junk not in parts, junk
        if junk.startswith("P") and junk[1:]:
            assert junk[1:] not in parts, junk


def test_time_ten_order_is_kyle_order():
    assert TIME_TEN_ORDER == (
        "102728-1",
        "28106-1",
        "1004747-1",
        "1004611",
        "103516",
        "105098-1",
        "33612-1",
        "21727-1",
        "1007922-1",
        "P904225-1",
    )
    specs = _specs()
    assert list(specs) == list(TIME_TEN_ORDER)
    assert specs["102728-1"].kyle_locked
    assert specs["28106-1"].kyle_locked
    assert specs["1004747-1"].kyle_locked
    assert not any(specs[k].kyle_locked for k in TIME_TEN_ORDER[3:])
    assert len(_KYLE_1004747_1) == 14
    assert sum(q for _i, q, _p, _d in _KYLE_1004747_1) == 18
    assert {pn for _i, _q, pn, _d in _KYLE_1004747_1}.isdisjoint(
        {"1004806-2", "11694-2", "25009-2"}
    )


def test_time_ten_cell_text_harvest_and_xlsx(tmp_path: Path):
    """Each synthetic grid must round-trip letter / PN / qty. Not live proof."""
    specs = _specs()
    for key in TIME_TEN_ORDER:
        spec = specs[key]
        cells = _cells_for(spec)
        _assert_grid(parse_material_list_cells(cells, bom_config=spec.bom_config), spec)

        lines = [spec.title, "LIST OF MATERIAL"]
        for row in cells:
            lines.append(" | ".join(row))
        text = "\n".join(lines)
        _assert_grid(parse_material_list_text(text, bom_config=spec.bom_config), spec)
        extracted = extract_bom(text=text, bom_config=spec.bom_config)
        assert extracted.method and extracted.method.startswith("table_"), (key, extracted.notes)
        assert not (extracted.method or "").startswith("ocr_time"), key
        _assert_grid(extracted, spec)

        strips = [" | ".join(row) for row in reversed(cells)]
        harvested = harvest_ocr_row_strips(strips, bom_config=spec.bom_config, page_text=spec.title)
        _assert_grid(harvested, spec)

        pdf = tmp_path / f"{key.replace('/', '-')}.pdf"
        _write_lom_pdf(pdf, cells[0], cells[1:], title=spec.title)
        if spec.library_bait:
            lib = tmp_path / f"{key}-lib"
            lib.mkdir()
            for extra in spec.library_bait:
                (lib / extra).write_bytes(b"%PDF-1.4\n%\n")
            bom = extract_bom(pdf_path=pdf, library_folder=lib, bom_config=spec.bom_config)
        else:
            bom = extract_bom(pdf_path=pdf, bom_config=spec.bom_config)
        assert bom.method and bom.method.startswith("table_"), (key, bom.notes)
        assert not (bom.method or "").startswith("ocr_time"), key
        _assert_grid(bom, spec)
        xlsx = pdf.with_name(f"{pdf.stem}-LOM.xlsx")
        assert xlsx.is_file(), key
        if spec.key != "P904225-1":
            _assert_kyle_xlsx(xlsx, spec.rows)
        keep = {pn for _i, _q, pn, _d in spec.rows}
        keep.add("904226-1")
        parts = {str(r.part_no or "") for r in bom.rows}
        for extra in spec.library_bait:
            stem = Path(extra).stem
            if stem not in keep and stem.lstrip("P") not in keep:
                assert stem not in parts, (key, stem)


def test_1004747_1_does_not_drop_siblings_or_hose_guide():
    spec = _specs()["1004747-1"]
    cells = _cells_for(spec)
    cells.append(["1", "", "99", "73207", "ADDED CONFIGURATION", ""])
    cells.append(["1", "", "98", "56657", "FIRST RELEASE TO PRODUCTION", ""])
    bom = parse_material_list_cells(cells, bom_config="-1")
    parts = {r.part_no for r in bom.rows}
    assert "6993-1" in parts
    assert "1004806-1" in parts and "1004711-1" in parts
    assert "1004773-1" in parts and "1004743-1" in parts
    assert "1004747-1" not in parts
    assert "1004806-2" not in parts
    assert "11694-2" not in parts
    assert "25009-2" not in parts
    assert "73207" not in parts and "56657" not in parts
    assert len(bom.rows) == 14
    assert sum(r.qty for r in bom.rows) == 18


def test_103516_hyphenless_dupes_and_column_index_are_not_pieces():
    spec = _specs()["103516"]
    cells = _cells_for(spec)
    for pn in ("1035371", "1035221", "1035281"):
        cells.append(["1", "Z", pn, "TUBE"])
    cells.append(["13", "E", "103500-1", "TUBE"])
    bom = parse_material_list_cells(cells, bom_config="-1")
    parts = {r.part_no for r in bom.rows}
    assert "103537-1" in parts and "1035371" not in parts
    assert "103522-1" in parts and "1035221" not in parts
    assert "103516-1" not in parts
    assert not any(r.qty == 13 for r in bom.rows)


def test_time_ten_is_not_live_done():
    """Fixtures ≠ laptop 10-set. 102728-1 qty (97 pcs) is still first."""
    specs = _specs()
    locked = [k for k, s in specs.items() if s.kyle_locked]
    assert locked == ["102728-1", "28106-1", "1004747-1"]
    assert specs["102728-1"].rows[0] == ("A", 1, "460200", "RAIL, BOTTOM FRONT MIDDLE")
    assert specs["102728-1"].rows[-2][2] == "102727-4"
    assert sum(q for _i, q, _p, _d in specs["102728-1"].rows) == 97
    assert specs["102728-1"].bom_config == ""
    assert specs["28106-1"].bom_config == "-1"
    assert specs["1004747-1"].bom_config == "-1"
    assert sum(q for _i, q, _p, _d in specs["28106-1"].rows) == 13
    assert len(specs["1004747-1"].rows) == 14
    assert sum(q for _i, q, _p, _d in specs["1004747-1"].rows) == 18
    assert specs["1004747-1"].rows[-1] == ("1", 1, "25060-6", "TUBE, PIVOT")
    parts = {pn for _i, _q, pn, _d in specs["1004747-1"].rows}
    assert "1004806-2" not in parts
    assert "11694-2" not in parts
    assert "25009-2" not in parts
    waiting = [k for k, s in specs.items() if not s.kyle_locked]
    assert waiting == list(TIME_TEN_ORDER[3:])
