"""BOM extraction tests (native MAC + Time OCR voting)."""

from __future__ import annotations

from pathlib import Path

import pytest

from quote_core.bom import (
    _parse_qty_item_part_hits,
    _vote_bom_rows,
    extract_bom,
    extract_bom_from_ocr_time_style,
    extract_bom_from_native_time_style,
    normalize_part_no,
    upload_is_assembly_drawing,
)

_JIB_PDF = Path("data/uploads/30/35145-1 JIB ARM WELDMENT ALL DRAWINGS-DESKTOP-GTEFB1D.pdf")
_JIB_LIB = Path(
    r"C:\Users\Kyle\Kannon Manufacturing Inc\Fort Worth - Documents\Engineering\Customer Drawings\Time\35145-1"
)


def test_normalize_part_ocr_confusions():
    assert normalize_part_no("35121—1") == "35121-1"
    assert normalize_part_no("35i21-1") == "35121-1"
    assert normalize_part_no("351211") == "35121-1"


def test_vote_time_style_ocr_lines():
    bases = {"29754", "35121", "35122", "35144", "42021", "35145"}
    texts = [
        "|2|F|42021-9\n|2|E|29754-3\n|2|D|29754-2\nC|35121-2\n|1|B|35121-1\n2|A 35122-\n",
        "| 1 | G 435144—1\n| 2 | F |42021-¢\n| 2 | E |29754-3\n",
        "2 | A 35122-1\n1 | B |35i21-1\n",
    ]
    hits = _parse_qty_item_part_hits(texts, bases)
    rows = _vote_bom_rows(hits, bases)
    got = {(r.item, r.part_no, r.qty) for r in rows}
    expected = {
        ("A", "35122-1", 2),
        ("B", "35121-1", 1),
        ("C", "35121-2", 1),
        ("D", "29754-2", 2),
        ("E", "29754-3", 2),
        ("F", "42021-9", 2),
        ("G", "35144-1", 1),
    }
    assert got == expected
    assert sum(r.qty for r in rows) == 11


def test_vote_item_letters_beyond_g():
    """Knuckle-style BOMs use H/J/K/L; qty 2 on H and L → 13 pieces."""
    bases = {
        "21683",
        "21679",
        "21682",
        "21681",
        "21680",
        "21688",
        "21684",
        "21685",
        "21687",
        "21686",
        "21689",
    }
    texts = [
        "2 | L |21689-1 HOSE GUARD\n"
        "K |21686-1 ANCHOR, LEVELING CYLINDER\n"
        "J |21687-1 SUPPORT, LEVELING ANCHOR\n"
        "2 | H |21685-1 PLATE, CYLINDER ANCHOR\n"
        "G |21684-1 TUBE, CYLINDER ANCHOR\n"
        "F |21688-1 BOX BRACE, KNUCKLE\n"
        "E |21680-1 KNUCKLE PLATE, UB OUTSIDE\n"
        "D |21681-1 KNUCKLE PLATE, UB INSIDE\n"
        "C |21682-1 KNUCKLE PLATE, LB INSIDE\n"
        "B |21679-1 TUBE, KNUCKLE SUPPORT\n"
        "A |21683-1 KNUCKLE PLATE, LB OUTSIDE\n"
    ]
    hits = _parse_qty_item_part_hits(texts, bases)
    rows = _vote_bom_rows(hits, bases)
    assert len(rows) == 11
    assert sum(r.qty for r in rows) == 13
    by_item = {r.item: r for r in rows}
    assert by_item["H"].qty == 2 and by_item["H"].part_no == "21685-1"
    assert by_item["L"].qty == 2 and by_item["L"].part_no == "21689-1"


def test_library_does_not_snap_to_ambiguous_sibling():
    from quote_core.bom import _correct_part_with_library

    bases = {"21684", "21685", "21686", "21687", "21688"}
    # 21689 is Hamming-1 from both 21684 and 21688 — keep OCR reading.
    assert _correct_part_with_library("21689-1", bases) == "21689-1"


def test_native_time_style_bom_from_text_without_ocr():
    """PDF-only Time tables must parse from selectable text (no Tesseract)."""
    text = (
        "LIST OF MATERIAL\n"
        "1 A 21679-1 TUBE, KNUCKLE SUPPORT\n"
        "1 B 21680-1 PLATE, UB OUTSIDE\n"
        "2 C 21681-1 GUSSET\n"
    )
    bom = extract_bom_from_native_time_style(text=text)
    assert bom.method == "native_time"
    assert bom.piece_count == 4
    got = {r.part_no for r in bom.rows}
    assert {"21679-1", "21680-1", "21681-1"} <= got


def test_extract_bom_uses_native_time_before_ocr():
    text = "1 A 35122-1 PLATE\n1 B 35121-1 TUBE\n"
    bom = extract_bom(text=text)
    assert bom.method == "native_time"
    assert bom.piece_count == 2


def test_library_children_supplement_assembly_only(tmp_path: Path):
    folder = tmp_path / "21678-1"
    folder.mkdir()
    (folder / "21679.pdf").write_bytes(b"%PDF-c")
    (folder / "21680.pdf").write_bytes(b"%PDF-c")
    (folder / "21681-1.pdf").write_bytes(b"%PDF-c")

    import fitz

    assy = tmp_path / "21678-1.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "21678-1 WELDMENT")
    doc.save(assy)
    doc.close()

    assert upload_is_assembly_drawing(assy, folder) is True
    bom = extract_bom(
        assy,
        library_folder=folder,
        related_pdf_names=["21679.pdf", "21680.pdf", "21681-1.pdf"],
    )
    parts = {r.part_no.upper() for r in bom.rows}
    assert {"21679", "21680", "21681-1"} <= parts
    assert any(r.source == "library_folder" for r in bom.rows)
    assert any("drawing-library" in n for n in bom.notes)

    child = tmp_path / "21679.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "21679 TUBE")
    doc.save(child)
    doc.close()
    assert upload_is_assembly_drawing(child, folder) is False
    child_bom = extract_bom(
        child,
        library_folder=folder,
        related_pdf_names=["21680.pdf", "21681-1.pdf"],
    )
    child_parts = {r.part_no.upper() for r in child_bom.rows}
    assert "21680" not in child_parts
    assert "21681-1" not in child_parts


def test_native_mac_bom_still_preferred():
    text = """
WEIGHT:
10.0 lbm
1
2
80341690
CHANNEL
5.0 lbm
2
1
80341691
PLATE
5.0 lbm
"""
    bom = extract_bom(text=text)
    assert bom.method == "pdf_bom_qty"
    assert bom.piece_count == 3
    assert bom.part_number_count == 2


@pytest.mark.skipif(not _JIB_PDF.exists(), reason="Job 30 jib arm PDF not present")
def test_jib_arm_ocr_bom_eleven_pieces():
    lib = _JIB_LIB if _JIB_LIB.exists() else None
    bom = extract_bom_from_ocr_time_style(_JIB_PDF, library_folder=lib)
    assert bom.part_number_count == 7
    assert bom.piece_count == 11
    got = {(r.item, r.part_no, r.qty) for r in bom.rows}
    assert got == {
        ("A", "35122-1", 2),
        ("B", "35121-1", 1),
        ("C", "35121-2", 1),
        ("D", "29754-2", 2),
        ("E", "29754-3", 2),
        ("F", "42021-9", 2),
        ("G", "35144-1", 1),
    }
