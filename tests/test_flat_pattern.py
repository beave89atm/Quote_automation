"""Offline tests for flat-pattern Length × Width extraction."""

from __future__ import annotations

from pathlib import Path

from quote_core.flat_pattern import (
    extract_flat_pattern_dims,
    extract_flat_pattern_dims_from_text,
)

_MD23_UPLOAD = Path(
    "/home/ubuntu/.cursor/projects/workspace/uploads/MD23-1709LR.idw_c0d4.pdf"
)
_MC07_UPLOAD = Path(
    "/home/ubuntu/.cursor/projects/workspace/uploads/MC07-1620LR.idw_a49f.pdf"
)


def test_flat_section_paren_dims():
    text = """
    FLAT PATTERN
    FOR REFERENCE ONLY
    (26.85)
    (8.49)
    DOWN 30° R.20
    """
    assert extract_flat_pattern_dims_from_text(text) == (26.85, 8.49)


def test_flat_section_blank_pair():
    text = """
    FLAT PATTERN FOR REFERENCE ONLY
    26.85 x 8.49
    MATERIAL: 5052
    """
    assert extract_flat_pattern_dims_from_text(text) == (26.85, 8.49)


def test_rejects_stock_plate_three_number_callout():
    text = "1/8 x 60 x 120, 5052-H32 ALUMINUM\nMU02-1004-001\n"
    assert extract_flat_pattern_dims_from_text(text) is None


def test_rejects_stock_sheet_two_number_callout():
    text = 'FLAT PATTERN\n11 GA (0.091") 60" x 120" SHEET, ALUMINUM 5052-H32\n'
    assert extract_flat_pattern_dims_from_text(text) is None


def test_prefers_blank_over_stock_plate():
    text = """
    PARTS LIST
    1/8 x 60 x 120, 5052-H32 ALUMINUM
    MU02-1004-001
    26.85 x 8.49
    1
    """
    assert extract_flat_pattern_dims_from_text(text) == (26.85, 8.49)


def test_mc07_style_prefers_flat_overall_over_feature_parens_and_stock():
    """Regression: stock 60x120 SHEET + hole parens must not beat 14.75×20.25."""
    text = """
    FLAT PATTERN
    FOR REFERENCE ONLY
    PARTS LIST
    11 GA (0.091") 60" x 120" SHEET, ALUMINUM 5052-H32
    MU02-1004-001
    NOTES AND HOLES
    (1.13)
    (3.2)
    OVERALL
    (14.75)
    (20.25)
    """
    assert extract_flat_pattern_dims_from_text(text) == (20.25, 14.75)


def test_lesson01_style_long_rail():
    text = 'FLAT PATTERN\n85.42" X 7.78"\n'
    assert extract_flat_pattern_dims_from_text(text) == (85.42, 7.78)


def test_orders_longer_side_first():
    assert extract_flat_pattern_dims_from_text("FLAT PATTERN\n8.49 x 26.85\n") == (
        26.85,
        8.49,
    )


def test_empty_text():
    assert extract_flat_pattern_dims_from_text("") is None
    assert extract_flat_pattern_dims_from_text("NO DIMS HERE") is None


def test_md23_pdf_if_present():
    if not _MD23_UPLOAD.is_file():
        return
    assert extract_flat_pattern_dims(_MD23_UPLOAD) == (26.85, 8.49)


def test_mc07_pdf_if_present():
    if not _MC07_UPLOAD.is_file():
        return
    assert extract_flat_pattern_dims(_MC07_UPLOAD) == (20.25, 14.75)


def test_synthetic_pdf_blank(tmp_path: Path):
    import fitz

    pdf = tmp_path / "flat.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (72, 72),
        'FLAT PATTERN FOR REFERENCE ONLY\n26.85 x 8.49\n1/8 x 60 x 120 STOCK\n',
        fontsize=11,
    )
    doc.save(pdf)
    doc.close()
    assert extract_flat_pattern_dims(pdf) == (26.85, 8.49)
