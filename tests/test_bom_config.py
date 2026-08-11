"""Tests for BOM config / dash selection and multi-qty Time BOM rows."""

from pathlib import Path

from quote_core.bom import _parse_multi_qty_time_hits, texts_have_multi_qty_headers
from quote_core.bom_config import (
    extract_bom_config_from_pdf_text,
    infer_bom_config_from_pdf,
    normalize_bom_config,
    resolve_bom_config,
)


def test_normalize_bom_config():
    assert normalize_bom_config("-1") == "1"
    assert normalize_bom_config("1") == "1"
    assert normalize_bom_config("28106-1") == "1"
    assert normalize_bom_config("") is None


def test_resolve_from_folder_name():
    cfg = resolve_bom_config(
        title="28106",
        pdf_filename="28106.pdf",
        library_folder=r"C:\drawings\Time\Lower Boom Weldment - 28106-1",
    )
    assert cfg == "1"


def test_resolve_from_drawing_number_when_filename_bare():
    """Bare 1004715.pdf + title-block 1004715-2 → dash -2 qty column."""
    cfg = resolve_bom_config(
        title="1004715",
        pdf_filename="1004715.pdf",
        drawing_number="1004715-2",
    )
    assert cfg == "2"


def test_explicit_bom_config_beats_drawing_number():
    cfg = resolve_bom_config(
        explicit="1",
        title="1004715",
        pdf_filename="1004715.pdf",
        drawing_number="1004715-2",
    )
    assert cfg == "1"


def test_sheet_label_infers_dash2_not_bom_column_headers():
    text = """
PART NUMBER
DESCRIPTION
1004715-1
1004715-2
8
1004713-2
LOWER BOOM TUBE
1004715-1
REV.
ERCN
1004715-2
NOTE:
HOLD THE 8.50 DIMENSION
DWG.  NO.
1004715
"""
    assert extract_bom_config_from_pdf_text(text, base_hint="1004715") == "2"


_JOB3_PDF = Path("data/uploads/3/1004715.pdf")


def test_infer_bom_config_from_job3_pdf_if_present():
    if not _JOB3_PDF.is_file():
        return
    assert (
        infer_bom_config_from_pdf(
            _JOB3_PDF, title="1004715", pdf_filename="1004715.pdf"
        )
        == "2"
    )


def test_multi_qty_headers_and_column_filter():
    texts = [
        "[-4 [-3 [-2 [-1 |",
        "| - | - | - | 1 | A |16697-2 |Lower BOOM TUBE 91 1/8 LG.",
        "| - | - | 1 | - | L |16697-1 |Lower Boom TUBE 55 LG.",
        "| 2 | 2 | 2 | 2 | J |15864-2 |STIFFENER, BOOM PIVOT",
        "| 1 | 1 | 1 | 1 | B |26732-1 |CYLINDER MOUNT PLATE",
    ]
    assert texts_have_multi_qty_headers(texts)
    hits = _parse_multi_qty_time_hits(texts, bases={"16697", "15864", "26732"}, bom_config="1")
    by_item = {h["item"]: h for h in hits if int(h["qty"] or 0) > 0}
    assert by_item["A"]["part_no"] == "16697-2"
    assert by_item["A"]["qty"] == 1
    assert "L" not in by_item  # -2 only
    assert by_item["J"]["qty"] == 2
    assert by_item["B"]["part_no"] == "26732-1"


def test_28106_dash1_piece_count_if_present():
    """28106-1 BOM: 11 unique PNs, two at qty 2 → 13 pieces."""
    from pathlib import Path

    from quote_core.bom import extract_bom_from_ocr_time_style

    pdf = Path(
        r"C:\Users\Kyle\Kannon Manufacturing Inc\Fort Worth - Documents\Engineering"
        r"\Customer Drawings\Time\Lower Boom Weldment - 28106-1\28106.pdf"
    )
    if not pdf.exists():
        return
    bom = extract_bom_from_ocr_time_style(
        pdf, library_folder=pdf.parent, bom_config="1"
    )
    parts = {r.part_no for r in bom.rows}
    assert "16697-2" in parts
    assert "16697-1" not in parts and "16697-3" not in parts and "16697-4" not in parts
    assert len(bom.rows) == 11, [f"{r.part_no}×{r.qty}" for r in bom.rows]
    assert bom.piece_count == 13, [f"{r.part_no}×{r.qty}" for r in bom.rows]
    qty2 = sorted(r.part_no for r in bom.rows if r.qty == 2)
    assert qty2 == ["15864-2", "15891-1"], qty2
