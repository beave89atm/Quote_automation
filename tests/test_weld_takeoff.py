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


def test_labeled_fillet_harvested_without_weld_sheet_keywords():
    from quote_core.weld.takeoff import _ingest_page_text

    sizes, _notes, hits, _dims = _ingest_page_text(1, "WELD SZ: 5/16 TYP AT JOINT")
    assert "5/16" in sizes
    assert any(h.get("explicit_label") for h in hits)


def test_laser_only_pdf_keeps_zero_fitup(tmp_path: Path):
    import fitz

    path = tmp_path / "laser.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "LASER CUT PLATE 12 X 24 A36")
    doc.save(path)
    doc.close()
    result = run_weld_takeoff(pdf_path=path)
    assert result.items == []
    assert result.fitup_drivers.get("part_count") == 0
    assert result.fitup_drivers.get("joint_count") == 0
    assert any("No weld symbols" in f for f in result.flags)


def test_pdf_bom_without_fillets_still_drives_fitup(tmp_path: Path):
    import fitz

    path = tmp_path / "21678-1.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (72, 72),
        "21678-1 WELDMENT\n1 A 21679-1 TUBE\n1 B 21680-1 PLATE\n2 C 21681-1 GUSSET",
    )
    doc.save(path)
    doc.close()
    result = run_weld_takeoff(pdf_path=path)
    assert result.items == []
    assert result.fitup_drivers.get("part_count") == 4
    assert result.pdf_bom.get("piece_count") == 4
    assert any("fillet" in f.lower() or "Fit-up uses PDF BOM" in f for f in result.flags)
    assert result.part_number == "21678-1"


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
