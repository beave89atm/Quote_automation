from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from secturafab.push import (
    SecturaFabPushService,
    _default_material,
    _weld_memo,
    collect_job_files,
)


def test_weld_memo_includes_inches():
    memo = _weld_memo({"total_inches": 154.12, "weld_minutes": 41.1}, {"sizes_found": ["3/16"]})
    assert "154.12" in memo
    assert "3/16" in memo


def test_default_material_from_takeoff():
    mat = _default_material({"fitup_drivers": {"weight_calc": {"material_label": "A572 GR50"}}})
    assert mat == "A572"


def test_collect_job_files(tmp_path: Path):
    pdf = tmp_path / "35145-1.pdf"
    stp = tmp_path / "35145-1.STEP"
    pdf.write_bytes(b"%PDF")
    stp.write_bytes(b"ISO")
    drawings, cad = collect_job_files(pdf_path=pdf, stp_path=stp, library=None)
    assert drawings == [pdf]
    assert cad == [stp]


def test_push_job_creates_quote_and_uploads():
    client = MagicMock()
    client.get_json.return_value = {"QuoteNumber": "35145-1", "ItemCount": 3, "ItemList": [{}, {}, {}]}

    service = SecturaFabPushService(client=client)
    pdf = Path("data/uploads/33/35145.pdf")
    stp = Path("data/uploads/33/35145-1.STEP")
    if not pdf.exists() or not stp.exists():
        return

    with patch.object(service, "upload_drawings_quote_request", return_value="qr-uuid") as up_d, patch.object(
        service, "quick_add_cad", return_value={"ok": True}
    ) as up_c, patch.object(service, "create_quote", return_value="quote-uuid") as create_q, patch.object(
        service, "allocate_quote_number", return_value="35145-1"
    ):
        result = service.push_job(
            title="35145-1 JIB ARM",
            pdf_filename="35145.pdf",
            pdf_path=pdf,
            stp_path=stp,
            takeoff={"library": {"part_key": "35145-1"}, "sizes_found": ["3/16"]},
            times={"total_inches": 154.12, "weld_minutes": 41.1},
            job_id=33,
        )
    assert result.ok
    assert result.quote_number == "35145-1"
    assert result.created_new_quote
    create_q.assert_called_once()
    up_d.assert_called_once()
    up_c.assert_called_once()


def test_allocate_quote_number_uses_date_when_part_taken():
    service = SecturaFabPushService(client=MagicMock())
    with patch.object(
        service,
        "find_quote_by_number",
        side_effect=lambda n: {"ID": "x"} if n == "21678-1" else None,
    ):
        result = service.allocate_quote_number("21678-1")
    assert result.startswith("21678-1-")
    assert result != "21678-1"
    suffix = result.removeprefix("21678-1-")
    assert len(suffix) == 8 and suffix.isdigit()


def test_repush_always_creates_new_quote_and_imports_cad():
    client = MagicMock()
    client.get_json.return_value = {
        "QuoteNumber": "21678-1-20260731",
        "ItemCount": 12,
        "ItemList": [{}] * 12,
    }

    service = SecturaFabPushService(client=client)
    pdf = Path("data/uploads/41/21678-1.pdf")
    stp = Path("data/uploads/41/21678-1.STEP")
    if not pdf.exists() or not stp.exists():
        pdf = Path("data/uploads/40/21678-1.pdf")
        stp = Path("data/uploads/40/21678-1.STEP")
    if not pdf.exists() or not stp.exists():
        return

    with patch.object(service, "upload_drawings_quote_request", return_value="qr-uuid"), patch.object(
        service, "quick_add_cad", return_value={"ok": True}
    ) as up_c, patch.object(service, "create_quote", return_value="new-id") as create_q, patch.object(
        service, "allocate_quote_number", return_value="21678-1-20260731"
    ):
        result = service.push_job(
            title="21678-1",
            pdf_filename="21678-1.pdf",
            pdf_path=pdf,
            stp_path=stp,
            takeoff={"library": {"part_key": "21678-1"}},
            times={},
            job_id=41,
        )
    assert result.ok
    assert result.created_new_quote
    assert result.quote_number == "21678-1-20260731"
    create_q.assert_called_once()
    up_c.assert_called_once()


def test_collect_related_pdf_from_sibling_folder(tmp_path: Path):
    knuckle = tmp_path / "Knuckle Weldment - 21678-1"
    sibling = tmp_path / "21678-1"
    knuckle.mkdir()
    sibling.mkdir()
    (sibling / "21689.pdf").write_bytes(b"%PDF")
    drawings, _cad = collect_job_files(
        pdf_path=None,
        stp_path=None,
        library={"folder": str(knuckle), "related_pdfs": ["21689.pdf"]},
    )
    assert len(drawings) == 1
    assert drawings[0].name == "21689.pdf"
