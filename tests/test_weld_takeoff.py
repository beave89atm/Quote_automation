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


def test_native_time_bom_piece_count_overrides_step_solids(monkeypatch):
    """1004715-2 style: 7 unique PNs / 10 BOM pcs must win over ~7 STEP solids."""
    from quote_core.weld.takeoff import estimate_fitup_drivers

    def _fake_weight(*_args, **_kwargs):
        return {
            "method": "native_time_multi_qty",
            "piece_count": 10,
            "part_number_count": 7,
            "assembly_weight_lb": None,
            "component_weights_lb": [],
            "material_label": None,
            "bom": {"method": "native_time_multi_qty", "piece_count": 10},
            "pdf_bom": {},
        }

    monkeypatch.setattr("quote_core.weight.estimate_assembly_weight", _fake_weight)
    stp_summary = {
        "solids": [{"kind": "plate", "qty": 1} for _ in range(7)],
        "solid_count": 7,
        "weld_segments": [],
    }
    drivers = estimate_fitup_drivers(stp_summary, notes=[])
    assert drivers["part_count"] == 10
    assert drivers["piece_count"] == 10
