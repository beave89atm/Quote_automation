"""PDF-only push: Image Files for plate, Long for tube, FLAG when a field is missing.

Page responses are fixtures. Nothing is written to SecturaFAB.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import fitz
import pytest

from secturafab.push import SecturaFabPushService
from tests.fixtures.pdf_only_pages import (
    PLATE_DRAWING,
    PLATE_FLATS,
    PLATE_MISSING_FLATS,
    PLATE_THICKNESS_IN,
    TUBE_CUT_LENGTH_IN,
    TUBE_DRAWING,
    plate_gold_finish_response,
    plate_gold_line,
    plate_perimeter_stamp,
    plate_upload_bound,
    tube_catalog_product,
    tube_gold_finish_response,
    tube_gold_line,
)

_ORG = {
    "OrganizationName": "Safe Cave",
    "PrimaryOrganizationID": "11111111-1111-4111-8111-111111111111",
}


def _write_pdf(path: Path, text: str) -> None:
    doc = fitz.open()
    try:
        page = doc.new_page()
        y = 72
        for line in text.splitlines():
            page.insert_text((72, y), line, fontsize=12)
            y += 16
        doc.save(path)
    finally:
        doc.close()


def _silence_chrome(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("secturafab.chrome_cdp.chrome_quotes_live", lambda *a, **k: False)
    monkeypatch.setattr(
        "secturafab.chrome_cdp.chrome_quotes_list_signed_in", lambda *a, **k: False
    )
    monkeypatch.setattr("secturafab.chrome_cdp.chrome_edit_signed_in", lambda *a, **k: False)
    monkeypatch.setattr("secturafab.chrome_cdp.chrome_login_page", lambda *a, **k: False)
    monkeypatch.setattr("secturafab.chrome_cdp.quotes_list_session_fetch", lambda *a, **k: {})
    monkeypatch.setattr("secturafab.chrome_cdp.dismiss_image_files_dialog", lambda *a, **k: [])


def _service(client: MagicMock) -> SecturaFabPushService:
    client.config.website_cookie = "ASP.NET_SessionId=test"
    return SecturaFabPushService(client=client)


def _common_patches(service: SecturaFabPushService, description: str):
    return (
        patch.object(service, "upload_drawings_quote_request", return_value="qr"),
        patch.object(service, "create_quote", return_value="qid"),
        patch.object(service, "allocate_quote_number", return_value="73476004"),
        patch.object(service, "find_quote_by_number", return_value=None),
        patch.object(service, "nest_after_finish", return_value=[]),
        patch("secturafab.push.refresh_bom_rows_for_push", return_value=([], [])),
        patch("secturafab.push.extract_assembly_description", return_value=description),
        patch("secturafab.push.ensure_weld_ops", return_value=[]),
        patch("secturafab.push.ensure_imperial_item_units", return_value=[]),
        patch("secturafab.push.apply_bom_quantities", return_value=[]),
        patch(
            "secturafab.push.apply_quote_organization",
            return_value=[f"Set Organization: {_ORG['OrganizationName']}"],
        ),
        patch("secturafab.push.persist_classified_item_fields", return_value=[]),
        patch("secturafab.push.persist_quote_header", return_value=[]),
        patch("secturafab.push.retype_linears_to_pt10_keep_persist", return_value=[]),
        patch("secturafab.plate_ops.fetch_plate_catalog", return_value=[]),
    )


def _quote_gets(gold: dict):
    reads = {"n": 0}

    def _get_json(path):
        text = str(path)
        if "product/linear" in text:
            return {"Results": [tube_catalog_product()], "HasNext": False}
        if "product/plate" in text:
            return []
        reads["n"] += 1
        if reads["n"] <= 2:
            return {
                "QuoteNumber": "73476004",
                "ItemCount": 0,
                "ItemList": [],
                "Description": gold.get("Description") or "",
                **_ORG,
            }
        return gold

    return _get_json


def test_pdf_plate_image_files_lands_gold_pack(tmp_path: Path, monkeypatch):
    _silence_chrome(monkeypatch)
    pdf = tmp_path / "73476004.pdf"
    _write_pdf(pdf, PLATE_DRAWING)
    client = MagicMock()
    client.upload_pdf_via_page_add_files.return_value = plate_upload_bound()
    client.stamp_pdf_kendo_flats.return_value = plate_perimeter_stamp()
    client.add_item_pdf_files.return_value = plate_gold_finish_response()
    client.quote_item_read.return_value = {}
    client.quote_item_read_treelist.return_value = {}
    gold = {
        "QuoteNumber": "73476004",
        "Description": "LIFT LOG GUSSET",
        "ItemCount": 1,
        "ItemList": [plate_gold_line("LIFT LOG GUSSET")],
        **_ORG,
    }
    client.get_json.side_effect = _quote_gets(gold)
    service = _service(client)
    patches = _common_patches(service, "LIFT LOG GUSSET")
    for item in patches:
        item.start()
    try:
        result = service.push_job(
            title="73476004",
            pdf_filename="73476004.pdf",
            pdf_path=pdf,
            stp_path=None,
            takeoff={"library": {}},
            times={},
            job_id=1,
            organization="Safe Cave",
        )
    finally:
        for item in reversed(patches):
            item.stop()

    assert result.ok is True, (result.error, result.notes)
    client.add_item_pdf_files.assert_called()
    client.add_item_linear.assert_not_called()
    stamped = client.stamp_pdf_kendo_flats.call_args.kwargs["rows"][0]
    assert float(stamped["Thickness"]) == pytest.approx(PLATE_THICKNESS_IN)
    assert {float(stamped["Width"]), float(stamped["Length"])} == set(PLATE_FLATS)
    blob = " ".join(result.notes or [])
    assert "Image Files" in blob
    assert "PR" in blob
    assert "UnitCost" in blob
    line = gold["ItemList"][0]
    assert line["BadgeString"] == "PR"
    assert line["UnitCost"] > line["UnitWeightCost"]
    names = [op["CalculatorName"] for op in line["OperationCostList"]]
    assert "Laser" in names and "Deburr" in names


def test_pdf_tube_long_lands_saw_packs(tmp_path: Path, monkeypatch):
    _silence_chrome(monkeypatch)
    pdf = tmp_path / "29860.pdf"
    _write_pdf(pdf, TUBE_DRAWING)
    client = MagicMock()
    client.add_item_linear.return_value = tube_gold_finish_response()
    client.quote_item_read.return_value = {}
    client.quote_item_read_treelist.return_value = {}
    client.read_data_linear_lookup.return_value = {}
    gold = {
        "QuoteNumber": "29860",
        "Description": "PEDESTAL TUBE",
        "ItemCount": 1,
        "ItemList": [tube_gold_line("PEDESTAL TUBE 2 X 2 X 0.250 TUBE")],
        **_ORG,
    }
    client.get_json.side_effect = _quote_gets(gold)
    service = _service(client)
    patches = _common_patches(service, "PEDESTAL TUBE")
    for item in patches:
        item.start()
    try:
        result = service.push_job(
            title="29860",
            pdf_filename="29860.pdf",
            pdf_path=pdf,
            stp_path=None,
            takeoff={"library": {}},
            times={},
            job_id=2,
            organization="Safe Cave",
        )
    finally:
        for item in reversed(patches):
            item.stop()

    assert result.ok is True, (result.error, result.notes)
    client.add_item_linear.assert_called()
    client.add_item_pdf_files.assert_not_called()
    assert client.add_item_linear.call_args.kwargs["length"] == pytest.approx(
        TUBE_CUT_LENGTH_IN
    )
    blob = " ".join(result.notes or [])
    assert "Long" in blob
    assert "Saw" in blob
    line = gold["ItemList"][0]
    assert line["UnitCost"] > line["UnitWeightCost"]
    assert line["BadgeString"] == ""
    names = [op["CalculatorName"] for op in line["OperationCostList"]]
    assert names == ["Saw", "Saw-Setup"]


def test_pdf_plate_missing_flats_flags_and_does_not_push(tmp_path: Path, monkeypatch):
    _silence_chrome(monkeypatch)
    pdf = tmp_path / "73476004.pdf"
    _write_pdf(pdf, PLATE_MISSING_FLATS)
    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=test"
    service = SecturaFabPushService(client=client)
    with patch.object(service, "create_quote", return_value="qid") as create_q, patch.object(
        service, "upload_drawings_quote_request", return_value="qr"
    ) as upload, patch.object(
        service, "finish_pdf_files"
    ) as finish, patch.object(
        service, "add_loose_linears"
    ) as linear, patch(
        "secturafab.push.refresh_bom_rows_for_push", return_value=([], [])
    ):
        result = service.push_job(
            title="73476004",
            pdf_filename="73476004.pdf",
            pdf_path=pdf,
            stp_path=None,
            takeoff={"library": {}},
            times={},
            job_id=3,
            organization="Safe Cave",
        )
    assert result.ok is False
    create_q.assert_not_called()
    upload.assert_not_called()
    finish.assert_not_called()
    linear.assert_not_called()
    blob = (result.error or "") + " " + " ".join(result.notes or [])
    assert "FLAG:" in blob
    assert "L/W" in blob
    assert "not inventing" in blob
