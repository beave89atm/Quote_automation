"""Tests for BOM config / dash selection and multi-qty Time BOM rows."""

from quote_core.bom import _parse_multi_qty_time_hits, texts_have_multi_qty_headers
from quote_core.bom_config import normalize_bom_config, resolve_bom_config


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


def test_bare_title_means_dash_one_not_folder_dash_two():
    """Title 1004747 means -1 even when the folder is a -2 weldment."""
    cfg = resolve_bom_config(
        title="1004747",
        pdf_filename="1004747.pdf",
        library_folder=r"C:\drawings\Time\Weldment - 1004747-2",
        part_key="1004747-2",
    )
    assert cfg == "1"


def test_typed_dash_two_title_wins():
    cfg = resolve_bom_config(
        title="1004747-2",
        pdf_filename="1004747.pdf",
        library_folder=r"C:\drawings\Time\Weldment - 1004747-1",
    )
    assert cfg == "2"


def test_dashed_part_key_beats_folder_dash_two():
    """Title 1020249-1 / part_key 1020249-1 uses LOM -1, not folder -2."""
    cfg = resolve_bom_config(
        title="BASE PLATE, PEDESTAL",
        pdf_filename="1020249-1.pdf",
        library_folder=r"C:\drawings\Time\Pedestal Weldment - 1020249-2",
        part_key="1020249-1",
    )
    assert cfg == "1"
    cfg2 = resolve_bom_config(
        title="1020249-1",
        library_folder=r"C:\drawings\Time\Pedestal Weldment - 1020249-2",
        part_key="1020249-1",
    )
    assert cfg2 == "1"


def test_explicit_dash_overrides_bare_title():
    cfg = resolve_bom_config(explicit="-2", title="1004747")
    assert cfg == "2"


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
