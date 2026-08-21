from pathlib import Path

from quote_core.weld.takeoff import run_weld_takeoff

ROOT = Path(__file__).resolve().parents[1]


def test_takeoff_80341805_if_present():
    pdf = ROOT / "references" / "80341805" / "80341805.pdf"
    stp = Path(
        r"c:\Users\Kyle\Kannon Manufacturing Inc\Fort Worth - Documents\Engineering\Customer Drawings\MAC Manufacturing\80341805\80341805.stp"
    )
    if not pdf.exists():
        # copied earlier in project history; skip if absent
        return
    result = run_weld_takeoff(pdf, stp if stp.exists() else None)
    assert result.sizes_found or result.items
    assert isinstance(result.flags, list)


def test_takeoff_73476047_if_present():
    pdf = Path(
        r"c:\Users\Kyle\Kannon Manufacturing Inc\Fort Worth - Documents\Engineering\Customer Drawings\MAC Manufacturing\73476047\73476047-FAB Packet.pdf"
    )
    stp = Path(
        r"c:\Users\Kyle\Kannon Manufacturing Inc\Fort Worth - Documents\Engineering\Customer Drawings\MAC Manufacturing\73476047\73476047.STEP"
    )
    if not pdf.exists():
        return
    result = run_weld_takeoff(pdf, stp if stp.exists() else None)
    assert "1/4" in result.sizes_found or any(i.size == "1/4" for i in result.items)
    assert result.to_dict()["total_inches"] >= 0


def test_tycrop_electrode_note_is_not_a_weld_symbol():
    """Title-block 'MINIMUM WELD ELECTRODE' + plate 3/16 must not invent weld time."""
    from quote_core.weld.takeoff import _ingest_page_text, _build_items_from_signals

    text = """
TYCROP MANUFACTURING LTD.
MINIMUM WELD ELECTRODE STRENGTH
R3/16"
3/16"
PLATE 100Q - 3/16 /SQ IN [10 5/16" X 4 21/32"]
DRAWING NUMBER
1505-8393
"""
    sizes, notes, hits, dims = _ingest_page_text(1, text)
    assert sizes == []
    assert hits == []
    items, flags = _build_items_from_signals(
        sizes=sizes,
        notes=notes,
        page_hits=hits,
        stp_summary={},
        pdf_name="1505-8393_R00.pdf",
        pdf_dimensions=dims,
        pdf_path=None,
    )
    assert items == []
    assert any("No weld symbols" in f for f in flags)


def test_job68_pdf_no_weld_if_present():
    pdf = ROOT / "data" / "uploads" / "68" / "1505-8393_R00.pdf"
    if not pdf.exists():
        return
    result = run_weld_takeoff(pdf)
    assert result.items == []
    assert result.to_dict()["total_inches"] == 0
    assert any("No weld symbols" in f for f in result.flags)


def test_fillet_callout_is_still_a_weld_symbol():
    from quote_core.weld.takeoff import _ingest_page_text, page_has_weld_symbols

    text = 'WELDMENT, PLATFORM\n1/4" FILLET WELD BOTH SIDES'
    assert page_has_weld_symbols(text) is True
    sizes, _notes, hits, _dims = _ingest_page_text(1, text)
    assert "1/4" in sizes
    assert hits and hits[0]["weld_sheet"] is True


def test_lom_and_weldment_title_are_not_weld_symbols():
    """A LIST OF MATERIAL + title WELDMENT + item letters is not a weld takeoff."""
    from quote_core.weld.takeoff import (
        _build_items_from_signals,
        _ingest_page_text,
        page_has_weld_symbols,
    )

    text = """
    WELDMENT, PLATFORM  102728-1  TIME MANUFACTURING
    SHEET 1 OF 2
    SCALE 1/4
    LIST OF MATERIAL
    QTY | ITEM | PART NO | DESCRIPTION
    1 | A | 460200 | RAIL, BOTTOM FRONT MIDDLE
    6 | V | 432710 | CAP, 2 x 1 TUBE
    2 | BB | 102727-4 | TUBE, ROUND
    AU | 1 | 102711-1 | CABLE TUBE WELDMENT
    """
    assert page_has_weld_symbols(text) is False
    sizes, notes, hits, dims = _ingest_page_text(1, text)
    assert sizes == []
    assert hits == []
    items, flags = _build_items_from_signals(
        sizes=sizes,
        notes=notes,
        page_hits=hits,
        stp_summary={},
        pdf_name="Time 102728- Weldment.pdf",
        pdf_dimensions=dims,
        pdf_path=None,
    )
    assert items == []
    assert any("No weld symbols" in f for f in flags)


def test_102728_lom_xlsx_stays_97_pcs_without_inventing_weld(tmp_path: Path):
    """LOM.xlsx-as-takeoff stays. Weld inches / times stay off without symbols."""
    from quote_core.bom import quote_bom_from_drawing
    from quote_core.config import load_shop_rates
    from quote_core.time_engine import compute_weld_times

    from tests.test_bom_table import (
        _KYLE_102728_1,
        _assert_kyle_102728_1,
        _assert_kyle_xlsx,
        _write_lom_pdf,
    )

    data_rows = [
        [str(qty), item, pn, desc] for item, qty, pn, desc in _KYLE_102728_1
    ]
    pdf = tmp_path / "Time 102728- Weldment.pdf"
    _write_lom_pdf(
        pdf,
        ["QTY", "ITEM", "PART NO.", "DESCRIPTION"],
        data_rows,
        title="WELDMENT, PLATFORM  102728-1  TIME MANUFACTURING  SCALE 1/4",
    )
    bom = quote_bom_from_drawing(pdf_path=pdf)
    _assert_kyle_102728_1(bom)
    xlsx = pdf.with_name(f"{pdf.stem}-LOM.xlsx")
    assert xlsx.is_file()
    _assert_kyle_xlsx(xlsx, _KYLE_102728_1)
    assert bom.piece_count == 97
    assert bom.to_dict()["source"] == "lom_xlsx"
    assert all(r.source == "lom_xlsx" for r in bom.rows)

    result = run_weld_takeoff(pdf)
    assert result.items == []
    assert result.to_dict()["total_inches"] == 0
    assert any("No weld symbols" in f for f in result.flags)
    assert any("BOM does not imply weld" in f for f in result.flags)
    weight = (result.fitup_drivers or {}).get("weight_calc") or {}
    pdf_bom = weight.get("pdf_bom") or weight.get("bom") or {}
    assert int(pdf_bom.get("piece_count") or result.fitup_drivers.get("piece_count") or 0) == 97
    assert pdf_bom.get("source") == "lom_xlsx"
    assert pdf_bom.get("lom_xlsx") == xlsx.name

    times = compute_weld_times(
        result.items,
        load_shop_rates(),
        efficiency_pct=100,
        part_count=97,
        component_weights_lb=[10.0] * 97,
    )
    assert times.weld_minutes == 0.0
    assert times.fitup_with_fixture_minutes == 0.0
    assert times.fitup_no_fixture_minutes == 0.0
