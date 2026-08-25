"""Finish / CAD Files JS contract; Finish is additive when a website cookie exists."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from secturafab.push import SecturaFabPushService, classify_sectura_item
from secturafab.website import (
    EMPTY_GUID,
    WEBSITE_AUTH_GAP,
    WEBSITE_FINISH_PATHS,
    SecturaFabWebsiteAuthError,
    build_dxf_finish_payload,
    build_linear_add_payload,
    build_pdf_finish_payload,
    filelist_from_cadimport_upload,
    filter_finish_filelist,
    overlay_classified_row,
    pick_closest_linear_product,
)


def test_dxf_finish_payload_js_contract():
    rows = [
        {
            "ErrorStatus": 0,
            "Qty": 1,
            "Machine": "Laser",
            "Material": "100k",
            "Thickness": 0.375,
            "ProductID": None,
            "Name": "21680-1 PLATE",
        },
        {"ErrorStatus": 1, "Qty": 1, "Machine": "Laser", "Name": "bad"},
        {"ErrorStatus": 0, "Qty": 0, "Machine": "Saw", "Name": "zero"},
        {
            "ErrorStatus": 0,
            "Qty": 2,
            "Machine": "Saw",
            "Material": "A519",
            "ProductID": "abc-linear",
            "IsLinear": True,
            "LinearLength": 9.75,
            "Name": "21684 TUBE",
        },
    ]
    payload = build_dxf_finish_payload("quote-id", rows, item_id=None, customer_material=False)
    assert payload["ID"] == "quote-id"
    assert payload["ItemID"] == EMPTY_GUID
    assert payload["customerMaterial"] is False
    assert len(payload["FileList"]) == 2
    assert payload["FileList"][0]["Machine"] == "Laser"
    assert payload["FileList"][0]["Material"] == "100k"
    assert payload["FileList"][0]["Thickness"] == 0.375
    assert payload["FileList"][1]["ProductID"] == "abc-linear"
    assert payload["FileList"][1]["LinearLength"] == 9.75
    assert all(r.get("ErrorStatus") == 0 for r in payload["FileList"])
    assert all(r.get("Qty") > 0 for r in payload["FileList"])


def test_finish_filelist_keeps_cadimport_source_ids():
    rows = [
        {
            "ErrorStatus": 0,
            "Qty": 1,
            "Name": "14500-1",
            "SourceDataID": "src-1",
            "FileID": "file-1",
            "CadType": 0,
            "FileType": ".pdf",
            "Stock_X": 11.0,
            "Stock_Y": 6.25,
            "Stock_Units": "inch",
            "Machine": None,
            "Material": "A572",
        }
    ]
    payload = build_dxf_finish_payload("qid", rows)
    assert payload["FileList"][0]["SourceDataID"] == "src-1"
    assert payload["FileList"][0]["FileID"] == "file-1"
    assert payload["FileList"][0]["Stock_X"] == 11.0
    uploaded = filelist_from_cadimport_upload(
        {"status": "OK", "List": rows, "ListOther": []}
    )
    assert len(uploaded) == 1
    assert uploaded[0]["SourceDataID"] == "src-1"


def test_filter_filelist_matches_js_grid_rule():
    kept = filter_finish_filelist(
        [
            {"ErrorStatus": 0, "Qty": 1},
            {"ErrorStatus": 2, "Qty": 4},
            {"ErrorStatus": 0, "Quantity": 0},
        ]
    )
    assert len(kept) == 1
    assert kept[0]["Qty"] == 1


def test_pdf_and_linear_payloads_share_id_itemid():
    pdf = build_pdf_finish_payload(
        "qid",
        [{"ErrorStatus": 0, "Qty": 1, "Machine": "Laser", "FileName": "a.pdf"}],
    )
    assert pdf["ID"] == "qid"
    assert pdf["ItemID"] == EMPTY_GUID
    assert pdf["customerMaterial"] is False
    linear = build_linear_add_payload("qid", product_id="pid-1", qty=2, length=10.9)
    assert linear["ID"] == "qid"
    assert linear["ProductID"] == "pid-1"
    assert linear["Qty"] == 2


def test_website_paths_are_quote_mvc_not_quickadd():
    assert WEBSITE_FINISH_PATHS["add_item_dxf_files"] == "/Quote/AddItem_DXFFiles"
    assert WEBSITE_FINISH_PATHS["add_item_pdf_files"] == "/Quote/AddItem_PDFFiles"
    assert WEBSITE_FINISH_PATHS["add_item_linear"] == "/Quote/AddItem_Linear"
    assert WEBSITE_FINISH_PATHS["upload_dxf"] == "/CadImport/UploadItem_DXFFiles"
    assert "quickAddCAD" not in str(WEBSITE_FINISH_PATHS)


def test_classify_hose_guard_is_linear():
    assert classify_sectura_item("21689-1 HOSE GUARD") == "Linear"
    assert classify_sectura_item("HOSEGUARD FORMED VIEW") == "Linear"


def test_overlay_linear_sets_saw_and_product():
    row = overlay_classified_row(
        {"Name": "21684 TUBE", "ErrorStatus": 0},
        category="Linear",
        material="A519",
        thickness=0.375,
        product_id="pid",
        sku="RT4X0.375-A519",
        qty=1,
    )
    assert row["Machine"] == "Saw"
    assert row["IsLinear"] is True
    assert row["ProductID"] == "pid"
    assert row["PartMode"] == 1


def test_pick_closest_linear_prefers_round_bar_for_hose_guard():
    products = [
        {
            "ID": "tube",
            "ProductName": "RT4X0.375-A519",
            "ProductDescription": "Mechanical Tube 4 X 0.375 A519",
            "ShapeName": "Mechanical Tube",
            "MaterialGrade": "A519",
            "Dim1": 4.0,
            "Dim2": 0.375,
            "Active": True,
        },
        {
            "ID": "bar",
            "ProductName": "RB3/8-A36",
            "ProductDescription": "Round Bar 3/8 A36",
            "ShapeName": "Round Bar",
            "MaterialGrade": "A36",
            "Dim1": 0.375,
            "Active": True,
        },
    ]
    best, note = pick_closest_linear_product(
        products, description="21689-1 HOSE GUARD", material="A36"
    )
    assert best is not None
    assert best["ID"] == "bar"
    assert note is None or "mismatch" not in note.lower() or "A36" in (note or "")


def test_finish_cad_files_uses_upload_filelist_ids(tmp_path: Path):
    stp = tmp_path / "21678-1.STEP"
    stp.write_bytes(b"ISO")
    client = MagicMock()
    client.upload_item_dxf_files.return_value = {
        "status": "OK",
        "List": [
            {
                "SourceDataID": "src-cad",
                "FileID": "file-cad",
                "FileName": "21678-1.STEP",
                "Name": "21680-1 PLATE",
                "Qty": 1,
                "ErrorStatus": 0,
                "Stock_X": 18.7,
                "Stock_Y": 23.4,
            }
        ],
    }
    client.cadimport_data.return_value = {}
    captured: dict[str, Any] = {}

    def _add(**kwargs):
        captured.update(kwargs)
        return {"ok": True}

    client.add_item_dxf_files.side_effect = _add
    service = SecturaFabPushService(client=client)
    notes = service.finish_cad_files(
        quote_id="qid",
        cad_files=[stp],
        material="A36",
        thickness="0.25",
        qty=1,
        takeoff={},
        bom_rows=[],
        library={},
        extra_pdfs=None,
        part_key="21678-1",
    )
    assert captured["file_list"][0]["SourceDataID"] == "src-cad"
    assert captured["file_list"][0]["FileID"] == "file-cad"
    assert any("SourceDataID" in n for n in notes)


def test_add_item_dxf_files_sends_js_contract():
    client = MagicMock()
    from secturafab.client import SecturaFabClient

    real = SecturaFabClient.__new__(SecturaFabClient)
    real.config = MagicMock()
    real.config.timeout_seconds = 30
    captured: dict[str, Any] = {}

    def fake_website_request(method, path, **kwargs):
        captured["method"] = method
        captured["path"] = path
        captured["json"] = kwargs.get("json")
        resp = MagicMock()
        resp.status_code = 200
        resp.content = b"{}"
        resp.json.return_value = {"ok": True}
        resp.headers = {}
        resp.text = "{}"
        resp.url = path
        return resp

    real.website_request = fake_website_request  # type: ignore[method-assign]
    real.add_item_dxf_files(
        quote_id="qid",
        file_list=[
            {
                "ErrorStatus": 0,
                "Qty": 1,
                "Machine": "Laser",
                "Material": "100k",
                "Thickness": 0.375,
                "ProductID": None,
            }
        ],
    )
    assert captured["path"] == "/Quote/AddItem_DXFFiles"
    body = captured["json"]
    assert body["ID"] == "qid"
    assert body["ItemID"] == EMPTY_GUID
    assert body["customerMaterial"] is False
    assert isinstance(body["FileList"], list)
    assert body["FileList"][0]["Machine"] == "Laser"


def test_push_job_no_cookie_uses_working_quickadd(tmp_path: Path):
    pdf = tmp_path / "part.pdf"
    stp = tmp_path / "part.stp"
    pdf.write_bytes(b"%PDF")
    stp.write_bytes(b"ISO")
    client = MagicMock()
    client.config.website_cookie = ""
    client.get_json.return_value = {
        "QuoteNumber": "part",
        "ItemCount": 2,
        "ItemList": [{"Description": "A"}, {"Description": "B"}],
    }
    service = SecturaFabPushService(client=client)
    with patch.object(service, "upload_drawings_quote_request", return_value="qr"), patch.object(
        service, "create_quote", return_value="qid"
    ) as create_q, patch.object(
        service, "allocate_quote_number", return_value="part"
    ), patch.object(
        service, "quick_add_cad", return_value={"ok": True}
    ) as qadd, patch.object(
        service, "finish_cad_files", return_value=[]
    ) as finish, patch.object(
        service, "apply_item_categories", return_value=[]
    ), patch(
        "secturafab.push.ensure_assembly_root", return_value=[]
    ), patch(
        "secturafab.push.relink_assembly_children", return_value=[]
    ), patch(
        "secturafab.push.ensure_purchased_components", return_value=[]
    ), patch(
        "secturafab.push.find_purchased_part_keys", return_value={}
    ), patch(
        "secturafab.push.refresh_bom_rows_for_push", return_value=([], [])
    ), patch(
        "secturafab.push.apply_bom_quantities", return_value=[]
    ), patch(
        "secturafab.push.ensure_laser_profile_ops", return_value=[]
    ), patch(
        "secturafab.push.ensure_weld_ops", return_value=[]
    ), patch(
        "secturafab.push.finalize_quote_ops", return_value=[]
    ), patch(
        "secturafab.push.ensure_imperial_item_units", return_value=[]
    ), patch(
        "secturafab.push.extract_assembly_description", return_value=None
    ):
        result = service.push_job(
            title="part",
            pdf_filename="part.pdf",
            pdf_path=pdf,
            stp_path=stp,
            takeoff={"library": {"part_key": "part"}},
            times={},
            job_id=2,
        )
    assert result.ok is True
    create_q.assert_called_once()
    qadd.assert_called_once()
    finish.assert_called()
    assert any(
        "falling back" in n or "Finish failed" in n or "0 ItemList" in n
        for n in (result.notes or [])
    )


def test_push_job_cookie_uses_finish_not_quickadd(tmp_path: Path):
    pdf = tmp_path / "21678-1.pdf"
    stp = tmp_path / "21678-1.STEP"
    pdf.write_bytes(b"%PDF")
    stp.write_bytes(b"ISO")
    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=test"
    populated = {
        "QuoteNumber": "21678-1",
        "ItemCount": 12,
        "ItemList": [{"Description": "21680 PLATE"}, {"Description": "21679 TUBE"}],
    }
    _n = {"i": 0}

    def _get_json(_path):
        _n["i"] += 1
        return {"QuoteNumber": "21678-1", "ItemCount": 0, "ItemList": []} if _n["i"] == 1 else populated

    client.get_json.side_effect = _get_json
    service = SecturaFabPushService(client=client)
    finish = MagicMock(return_value=["Finish CAD"])
    with patch.object(service, "finish_cad_files", finish), patch.object(
        service, "nest_after_finish", return_value=["Nest"]
    ), patch.object(
        service, "upload_drawings_quote_request", return_value="qr"
    ), patch.object(
        service, "create_quote", return_value="qid"
    ), patch.object(
        service, "allocate_quote_number", return_value="21678-1"
    ), patch.object(
        service, "quick_add_cad"
    ) as qadd, patch(
        "secturafab.push.ensure_weld_ops", return_value=["Attached Weld"]
    ), patch(
        "secturafab.push.ensure_imperial_item_units", return_value=[]
    ), patch(
        "secturafab.push.apply_bom_quantities", return_value=[]
    ), patch(
        "secturafab.push.refresh_bom_rows_for_push", return_value=([], [])
    ), patch(
        "secturafab.push.extract_assembly_description", return_value="KNUCKLE"
    ):
        result = service.push_job(
            title="21678-1",
            pdf_filename="21678-1.pdf",
            pdf_path=pdf,
            stp_path=stp,
            takeoff={"library": {"part_key": "21678-1"}},
            times={"weld_minutes": 10, "total_inches": 20},
            job_id=1,
        )
    assert result.ok is True
    finish.assert_called_once()
    qadd.assert_not_called()
    import secturafab.push as pushmod

    assert hasattr(pushmod, "ensure_laser_profile_ops")
    assert hasattr(pushmod, "finalize_quote_ops")
    assert hasattr(pushmod, "quick_add_cad") or hasattr(SecturaFabPushService, "quick_add_cad")


def test_push_job_finish_failure_falls_back_to_quickadd(tmp_path: Path):
    pdf = tmp_path / "part.pdf"
    stp = tmp_path / "part.stp"
    pdf.write_bytes(b"%PDF")
    stp.write_bytes(b"ISO")
    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=test"
    client.get_json.return_value = {
        "QuoteNumber": "part",
        "ItemCount": 2,
        "ItemList": [{"Description": "A"}, {"Description": "B"}],
    }
    service = SecturaFabPushService(client=client)

    def _finish_fail(**kwargs):
        raise SecturaFabWebsiteAuthError(WEBSITE_AUTH_GAP)

    peek_empty = {"QuoteNumber": "part", "ItemCount": 0, "ItemList": []}
    peek_ok = {
        "QuoteNumber": "part",
        "ItemCount": 2,
        "ItemList": [{"Description": "A"}, {"Description": "B"}],
    }
    # First peek (Finish failed) is empty; later reads after quickAddCAD are populated.
    _gets = {"n": 0}

    def _get_json(_path):
        _gets["n"] += 1
        return peek_empty if _gets["n"] == 1 else peek_ok

    client.get_json.side_effect = _get_json

    with patch.object(service, "upload_drawings_quote_request", return_value="qr"), patch.object(
        service, "create_quote", return_value="qid"
    ) as create_q, patch.object(
        service, "allocate_quote_number", return_value="part"
    ), patch.object(
        service, "finish_cad_files", side_effect=_finish_fail
    ), patch.object(
        service, "quick_add_cad", return_value={"ok": True}
    ) as qadd, patch.object(
        service, "apply_item_categories", return_value=[]
    ), patch(
        "secturafab.push.ensure_assembly_root", return_value=[]
    ), patch(
        "secturafab.push.relink_assembly_children", return_value=[]
    ), patch(
        "secturafab.push.ensure_purchased_components", return_value=[]
    ), patch(
        "secturafab.push.find_purchased_part_keys", return_value={}
    ), patch(
        "secturafab.push.refresh_bom_rows_for_push", return_value=([], [])
    ), patch(
        "secturafab.push.apply_bom_quantities", return_value=[]
    ), patch(
        "secturafab.push.ensure_laser_profile_ops", return_value=[]
    ), patch(
        "secturafab.push.ensure_weld_ops", return_value=[]
    ), patch(
        "secturafab.push.finalize_quote_ops", return_value=[]
    ), patch(
        "secturafab.push.ensure_imperial_item_units", return_value=[]
    ), patch(
        "secturafab.push.extract_assembly_description", return_value=None
    ):
        result = service.push_job(
            title="part",
            pdf_filename="part.pdf",
            pdf_path=pdf,
            stp_path=stp,
            takeoff={"library": {"part_key": "part"}},
            times={},
            job_id=3,
        )
    assert result.ok is True
    create_q.assert_called_once()
    qadd.assert_called_once()
    assert any("falling back to working push" in n for n in (result.notes or []))


def test_push_pdf_only_with_cookie_uses_image_files_finish(tmp_path: Path):
    pdf = tmp_path / "lonely.pdf"
    pdf.write_bytes(b"%PDF")
    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=test"
    populated = {
        "QuoteNumber": "lonely",
        "ItemCount": 1,
        "ItemList": [{"Description": "lonely", "ProductType": 100}],
    }
    _n = {"i": 0}

    def _get_json(_path):
        _n["i"] += 1
        return {"QuoteNumber": "lonely", "ItemCount": 0, "ItemList": []} if _n["i"] == 1 else populated

    client.get_json.side_effect = _get_json
    service = SecturaFabPushService(client=client)
    pdf_finish = MagicMock(return_value=["Image Files Finish"])
    with patch.object(service, "finish_pdf_files", pdf_finish), patch.object(
        service, "nest_after_finish", return_value=[]
    ), patch.object(
        service, "upload_drawings_quote_request", return_value="qr"
    ), patch.object(
        service, "create_quote", return_value="qid"
    ) as create_q, patch.object(
        service, "allocate_quote_number", return_value="lonely"
    ), patch.object(
        service, "quick_add_cad"
    ) as qadd, patch(
        "secturafab.pdf_assembly_ops.build_single_pdf_quote"
    ) as old_pdf, patch(
        "secturafab.push.ensure_weld_ops", return_value=[]
    ), patch(
        "secturafab.push.ensure_imperial_item_units", return_value=[]
    ), patch(
        "secturafab.push.apply_bom_quantities", return_value=[]
    ), patch(
        "secturafab.push.refresh_bom_rows_for_push", return_value=([], [])
    ), patch(
        "secturafab.push.extract_assembly_description", return_value=None
    ):
        result = service.push_job(
            title="lonely Title",
            pdf_filename="lonely.pdf",
            pdf_path=pdf,
            stp_path=None,
            takeoff={"library": {}},
            times={},
            job_id=99,
        )
    assert result.ok is True
    pdf_finish.assert_called_once()
    qadd.assert_not_called()
    old_pdf.assert_not_called()
    create_q.assert_called_once()


def test_website_request_login_redirect_is_auth_gap():
    from secturafab.client import SecturaFabClient
    from secturafab.config import SecturaFabConfig

    client = SecturaFabClient.__new__(SecturaFabClient)
    client.config = SecturaFabConfig(client_id="x", client_secret="y")
    client._token = MagicMock()
    client._token.authorization_header = "Bearer tok"
    client._token.is_expired = False
    session = MagicMock()
    resp = MagicMock()
    resp.status_code = 302
    resp.headers = {"Location": "/Account/Login?ReturnUrl=%2FQuote%2FAddItem_DXFFiles"}
    resp.text = ""
    session.request.return_value = resp
    client.session = session
    client.authenticate = lambda force=False: client._token  # type: ignore[method-assign]
    with pytest.raises(SecturaFabWebsiteAuthError, match="AddItem_DXFFiles"):
        client.website_request("POST", "/Quote/AddItem_DXFFiles", json={})
