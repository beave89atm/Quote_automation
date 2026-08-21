"""Nested weldment/assembly LOM clips from the drawing library.

Kyle drops only the top-level file. Recurse on children. Extra upload
only if the child is not in Customer Drawings. Do not merge child rows
into the parent BOM. Synthetic fixtures only — no customer PDFs in git.
"""

from __future__ import annotations

from pathlib import Path

from quote_core.bom import BomResult, BomRow, bom_from_lom_xlsx, extract_bom
from quote_core.bom_xlsx import apply_lom_xlsx_to_takeoff, read_lom_xlsx
from quote_core.nested_lom import (
    is_weldment_or_assembly_desc,
    nested_child_rows,
    nested_review_notes,
)

from tests.test_bom_table import (
    _KYLE_102728_1,
    _KYLE_103516,
    _KYLE_103516_PCS,
    _KYLE_103516_PN_COUNT,
    _assert_kyle_102728_1,
    _assert_kyle_103516,
    _assert_kyle_105098_1,
    _write_lom_pdf,
)

_CHILD_LOM: list[tuple[str, int, str, str]] = [
    ("A", 1, "555010", "PLATE, GATE"),
    ("B", 2, "555011", "TUBE, ROUND"),
]
_GRANDCHILD_LOM: list[tuple[str, int, str, str]] = [
    ("A", 1, "555099", "PIN"),
    ("B", 1, "555098", "WASHER"),
]


def _lom_data_rows(rows: list[tuple[str, int, str, str]]) -> list[list[str]]:
    return [[str(qty), item, pn, desc] for item, qty, pn, desc in rows]


def test_weldment_or_assembly_description_is_nested():
    assert is_weldment_or_assembly_desc("GATE WELDMENT")
    assert is_weldment_or_assembly_desc("CABLE TUBE WELDMENT")
    assert is_weldment_or_assembly_desc("LOCK ASSEMBLY")
    assert is_weldment_or_assembly_desc("Weldments")
    assert is_weldment_or_assembly_desc("ASSY, GATE")
    assert not is_weldment_or_assembly_desc("TUBE, ROUND")
    assert not is_weldment_or_assembly_desc("PLATE")
    assert not is_weldment_or_assembly_desc("GATE, FABRICATION")


def test_103516_fixture_names_gate_weldment_as_nested_child():
    """Live bar 27/45 including 103535-1 GATE WELDMENT. Named fixture rows only."""
    assert _KYLE_103516_PN_COUNT == 27
    assert _KYLE_103516_PCS == 45
    assert ("1", 1, "103535-1", "GATE WELDMENT") in _KYLE_103516
    bom = BomResult(
        rows=[
            BomRow(item=item, qty=qty, part_no=pn, description=desc)
            for item, qty, pn, desc in _KYLE_103516
        ]
    )
    children = nested_child_rows(bom)
    assert [r.part_no for r in children] == ["103535-1"]
    _assert_kyle_103516(bom)


def test_clip_child_lom_from_library_does_not_merge_parent(tmp_path: Path):
    """103516 item 20 103535-1 GATE WELDMENT — clip child LOM; parent stays."""
    job = tmp_path / "job"
    lib = tmp_path / "Customer Drawings"
    job.mkdir()
    child_dir = lib / "Time" / "103535-1"
    child_dir.mkdir(parents=True)
    (lib / "Time" / "103516-1").mkdir(parents=True)
    _write_lom_pdf(
        child_dir / "103535-1.pdf",
        ["QTY", "ITEM", "PART NO.", "DESCRIPTION"],
        _lom_data_rows(_CHILD_LOM),
        title="GATE WELDMENT  103535-1  TIME MANUFACTURING",
    )
    parent = job / "103516-1.pdf"
    _write_lom_pdf(
        parent,
        ["QTY", "ITEM", "PART NO.", "DESCRIPTION"],
        [
            ["1", "20", "103535-1", "GATE WELDMENT"],
            ["1", "27", "40002-2", ""],
            ["2", "21", "111001", "TUBE, ROUND"],
            ["1", "22", "111002", "PLATE"],
        ],
        title="WELDMENT, PLATFORM  103516-1  TIME MANUFACTURING",
    )
    without = extract_bom(pdf_path=parent)
    parent_pns = {str(r.part_no) for r in without.rows}
    parent_pcs = without.piece_count
    assert "103535-1" in parent_pns
    assert "555010" not in parent_pns

    bom = extract_bom(
        pdf_path=parent,
        library_folder=lib / "Time" / "103516-1",
        bom_config="-1",
    )
    parts = {str(r.part_no or "") for r in bom.rows}
    assert "103535-1" in parts
    assert "40002-2" in parts
    assert "555010" not in parts
    assert "555011" not in parts
    assert sum(1 for r in bom.rows if r.part_no == "103535-1") == 1
    assert bom.piece_count == parent_pcs
    assert {str(r.part_no) for r in bom.rows} == parent_pns

    parent_xlsx = job / "103516-1-LOM.xlsx"
    child_xlsx = job / "103535-1-LOM.xlsx"
    assert parent_xlsx.is_file()
    assert child_xlsx.is_file()
    _header, child_sheet = read_lom_xlsx(child_xlsx)
    child_pns = {r["PART NO"] for r in child_sheet}
    assert child_pns == {"555010", "555011"}
    _header, parent_sheet = read_lom_xlsx(parent_xlsx)
    parent_sheet_pns = {r["PART NO"] for r in parent_sheet}
    assert "555010" not in parent_sheet_pns
    assert "103535-1" in parent_sheet_pns

    clipped = [c for c in bom.nested_children if c.get("part_no") == "103535-1"]
    assert clipped and clipped[0]["status"] == "clipped"
    assert clipped[0]["lom_xlsx"] == "103535-1-LOM.xlsx"
    assert any("Clipped child LOM 103535-1" in n for n in bom.notes)
    assert (job / "103535-1.pdf").is_file()
    assert not (lib / "Time" / "103535-1" / "103535-1-LOM.xlsx").exists()


def test_missing_child_drawing_flags_extra_upload(tmp_path: Path):
    job = tmp_path / "job"
    job.mkdir()
    parent = job / "103516-1.pdf"
    _write_lom_pdf(
        parent,
        ["QTY", "ITEM", "PART NO.", "DESCRIPTION"],
        [
            ["1", "20", "103535-1", "GATE WELDMENT"],
            ["1", "27", "40002-2", "PLATE"],
        ],
        title="WELDMENT, PLATFORM  103516-1  TIME MANUFACTURING",
    )
    bom = extract_bom(pdf_path=parent)
    parts = {str(r.part_no or "") for r in bom.rows}
    assert "103535-1" in parts
    assert "555010" not in parts
    assert not (job / "103535-1-LOM.xlsx").exists()
    assert any("extra upload needed" in n.lower() for n in bom.notes)
    assert any("103535-1" in n for n in nested_review_notes(bom.notes))
    missing = [c for c in bom.nested_children if c.get("status") == "missing_upload"]
    assert missing and missing[0]["part_no"] == "103535-1"


def test_recurse_one_extra_child_level(tmp_path: Path):
    job = tmp_path / "job"
    lib = tmp_path / "Customer Drawings"
    job.mkdir()
    gate_rows = _CHILD_LOM + [("C", 1, "555012-1", "LOCK ASSEMBLY")]
    gate_dir = lib / "Time" / "103535-1"
    lock_dir = lib / "Time" / "555012-1"
    gate_dir.mkdir(parents=True)
    lock_dir.mkdir(parents=True)
    (lib / "Time" / "103516-1").mkdir(parents=True)
    _write_lom_pdf(
        gate_dir / "103535-1.pdf",
        ["QTY", "ITEM", "PART NO.", "DESCRIPTION"],
        _lom_data_rows(gate_rows),
        title="GATE WELDMENT  103535-1",
    )
    _write_lom_pdf(
        lock_dir / "555012-1.pdf",
        ["QTY", "ITEM", "PART NO.", "DESCRIPTION"],
        _lom_data_rows(_GRANDCHILD_LOM),
        title="LOCK ASSEMBLY  555012-1",
    )
    parent = job / "103516-1.pdf"
    _write_lom_pdf(
        parent,
        ["QTY", "ITEM", "PART NO.", "DESCRIPTION"],
        [
            ["1", "20", "103535-1", "GATE WELDMENT"],
            ["1", "27", "40002-2", ""],
            ["2", "21", "111001", "TUBE, ROUND"],
        ],
        title="WELDMENT, PLATFORM  103516-1",
    )
    bom = extract_bom(
        pdf_path=parent,
        library_folder=lib / "Time" / "103516-1",
    )
    parts = {str(r.part_no or "") for r in bom.rows}
    assert "103535-1" in parts
    assert "40002-2" in parts
    assert "555012-1" not in parts
    assert "555099" not in parts
    assert (job / "103535-1-LOM.xlsx").is_file()
    assert (job / "555012-1-LOM.xlsx").is_file()
    _header, lock_sheet = read_lom_xlsx(job / "555012-1-LOM.xlsx")
    lock_pns = {r["PART NO"] for r in lock_sheet}
    assert {"555099", "555098"} <= lock_pns
    assert "555099" not in parts
    assert "555098" not in parts
    gate = next(c for c in bom.nested_children if c["part_no"] == "103535-1")
    inner = [c for c in (gate.get("nested_children") or []) if c.get("part_no") == "555012-1"]
    assert inner and inner[0]["status"] == "clipped"


def test_102728_1_extract_without_library_stays_51_97(tmp_path: Path):
    """AU 102711-1 CABLE TUBE WELDMENT may flag extra upload. Qty stays 97."""
    pdf = tmp_path / "Time 102728- Weldment.pdf"
    _write_lom_pdf(
        pdf,
        ["QTY", "ITEM", "PART NO.", "DESCRIPTION"],
        _lom_data_rows(_KYLE_102728_1),
        title="WELDMENT, PLATFORM  102728-1  TIME MANUFACTURING",
    )
    bom = extract_bom(pdf_path=pdf)
    _assert_kyle_102728_1(bom)
    assert "102711-1" in {r.part_no for r in bom.rows}
    assert not (tmp_path / "102711-1-LOM.xlsx").exists()
    assert any("102711-1" in n and "extra upload" in n.lower() for n in bom.notes)
    au = next(r for r in bom.rows if r.item == "AU")
    assert au.qty == 1 and au.part_no == "102711-1"


def test_105098_later_sheet_child_table_is_not_nested_merge(tmp_path: Path):
    """103603-1 on a later sheet is not a parent LOM row — do not merge it."""
    import fitz

    pdf = tmp_path / "105098-1.pdf"
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
    )
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
    _assert_kyle_105098_1(bom)
    assert not (tmp_path / "103603-1-LOM.xlsx").exists()
    assert not any(c.get("part_no") == "103603-1" for c in bom.nested_children)


def test_lom_xlsx_reread_keeps_nested_children(tmp_path: Path):
    path = tmp_path / "103516-1-LOM.xlsx"
    from quote_core.bom_xlsx import write_lom_xlsx

    write_lom_xlsx(
        path,
        [
            BomRow(item="20", qty=1, part_no="103535-1", description="GATE WELDMENT"),
        ],
    )
    prior = BomResult(
        rows=[BomRow(item="20", qty=1, part_no="103535-1", description="GATE WELDMENT")],
        method="table_cells",
        nested_children=[
            {
                "item": "20",
                "part_no": "103535-1",
                "status": "clipped",
                "lom_xlsx": "103535-1-LOM.xlsx",
            }
        ],
        notes=["Clipped child LOM 103535-1 from library → 103535-1-LOM.xlsx"],
    )
    sourced = bom_from_lom_xlsx(path, prior=prior)
    assert sourced.nested_children[0]["part_no"] == "103535-1"
    takeoff = {
        "fitup_drivers": {
            "weight_calc": {
                "bom": {
                    "method": "table_cells",
                    "rows": [{"item": "20", "qty": 1, "part_no": "103535-1"}],
                    "notes": prior.notes,
                    "nested_children": prior.nested_children,
                }
            }
        }
    }
    fixed = apply_lom_xlsx_to_takeoff(takeoff, path)
    assert fixed["bom"]["nested_children"][0]["part_no"] == "103535-1"
    assert any("Clipped child LOM" in n for n in fixed["bom"]["notes"])
