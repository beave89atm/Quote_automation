"""Finish / CAD Files JS contract; Finish is additive when a website cookie exists."""

from __future__ import annotations

import base64
import json
import os
import time
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
    assert linear["ProductType"] == 10


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


def _gold_cad(desc: str = "21680-1 PLATE") -> dict[str, Any]:
    return {
        "Description": desc,
        "ProductType": 100,
        "Category": "Cad",
        "BadgeString": "PR",
        "UnitCost": 12.5,
        "MaterialCost": 1.1,
        "Material": "A36",
        "Thickness": 0.25,
        "Machine": "Laser",
        "OperationCostList": [
            {"OperationName": "Profile", "OperationLabel": "PR", "CalculatorName": "Laser", "UnitTime": 0.03},
            {"OperationName": "Profile", "OperationLabel": "PR", "CalculatorName": "Drafting", "UnitTime": 0.05},
            {"OperationName": "Profile", "OperationLabel": "PR", "CalculatorName": "Laser-Setup", "UnitTime": 0.16},
            {"OperationName": "Profile", "OperationLabel": "PR", "CalculatorName": "Sheet Loading", "UnitTime": 0.05},
            {"OperationName": "Profile", "OperationLabel": "PR", "CalculatorName": "Deburr", "UnitTime": 0.03},
        ],
    }


def _gold_lin(desc: str = "21679-1 TUBE") -> dict[str, Any]:
    return {
        "Description": desc,
        "ProductType": 10,
        "Category": "Linear",
        "IsLinear": True,
        "Machine": "Saw",
        "Length": 16,
        "UnitCost": 7.63,
        "MaterialCost": 0.55,
        "SKU": "RT",
        "BadgeString": "",
        "OperationCostList": [
            {"CalculatorName": "Saw", "OperationName": "Cut"},
            {"CalculatorName": "Saw Setup", "OperationName": "Cut"},
        ],
    }


def test_push_job_no_cookie_fails_without_quickadd(tmp_path: Path):
    pdf = tmp_path / "part.pdf"
    stp = tmp_path / "part.stp"
    pdf.write_bytes(b"%PDF")
    stp.write_bytes(b"ISO")
    client = MagicMock()
    client.config.website_cookie = ""
    client.get_json.return_value = {
        "QuoteNumber": "part",
        "ItemCount": 0,
        "ItemList": [],
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
        "secturafab.push.refresh_bom_rows_for_push", return_value=([], [])
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
    assert result.ok is False
    create_q.assert_called_once()
    qadd.assert_not_called()
    finish.assert_called()
    blob = " ".join(result.notes or []) + " " + (result.error or "")
    assert "Chrome" in blob or "session" in blob.lower()
    assert "quickAddCAD" not in blob
    assert "falling back" not in blob


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
        "ItemList": [_gold_cad("21680-1 PLATE"), _gold_lin("21679-1 TUBE")],
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


def test_push_job_finish_failure_fails_without_quickadd(tmp_path: Path):
    pdf = tmp_path / "part.pdf"
    stp = tmp_path / "part.stp"
    pdf.write_bytes(b"%PDF")
    stp.write_bytes(b"ISO")
    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=test"
    client.get_json.return_value = {
        "QuoteNumber": "part",
        "ItemCount": 0,
        "ItemList": [],
    }
    service = SecturaFabPushService(client=client)

    def _finish_fail(**kwargs):
        raise SecturaFabWebsiteAuthError(WEBSITE_AUTH_GAP)

    with patch.object(service, "upload_drawings_quote_request", return_value="qr"), patch.object(
        service, "create_quote", return_value="qid"
    ) as create_q, patch.object(
        service, "allocate_quote_number", return_value="part"
    ), patch.object(
        service, "finish_cad_files", side_effect=_finish_fail
    ), patch.object(
        service, "quick_add_cad", return_value={"ok": True}
    ) as qadd, patch(
        "secturafab.push.refresh_bom_rows_for_push", return_value=([], [])
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
    assert result.ok is False
    create_q.assert_called_once()
    qadd.assert_not_called()
    blob = " ".join(result.notes or []) + " " + (result.error or "")
    assert "Chrome" in blob or "session" in blob.lower()
    assert "falling back" not in blob


def test_push_pdf_only_with_cookie_uses_image_files_finish(tmp_path: Path):
    pdf = tmp_path / "lonely.pdf"
    pdf.write_bytes(b"%PDF")
    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=test"
    populated = {
        "QuoteNumber": "lonely",
        "ItemCount": 1,
        "ItemList": [_gold_cad("lonely")],
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
    with pytest.raises(SecturaFabWebsiteAuthError, match="Chrome|session"):
        client.website_request("POST", "/Quote/AddItem_DXFFiles", json={})


def test_classify_filelist_restores_dashed_cad_pn():
    service = SecturaFabPushService(client=MagicMock())
    rows = [
        {
            "ErrorStatus": 0,
            "Qty": 1,
            "FileName": "14500.pdf",
            "Name": "14500",
            "SourceDataID": "src-1",
            "FileID": "file-1",
            "Stock_X": 11.0,
        }
    ]
    classified, _notes = service.classify_cadimport_rows(
        rows,
        default_material="A36",
        default_thickness="0.25",
        bom_rows=[{"part_no": "14500-1", "qty": 1, "description": "PEDESTAL TOP PLATE"}],
        library={},
        extra_pdfs=None,
        qty=1,
    )
    assert classified[0]["Name"] == "14500-1"
    assert str(classified[0]["Description"]).startswith("14500-1")
    assert classified[0]["SourceDataID"] == "src-1"
    assert classified[0]["FileID"] == "file-1"


def test_effective_cookie_prefers_config_not_chrome():
    from secturafab.browser_session import effective_website_cookie
    from secturafab.config import SecturaFabConfig

    cfg = SecturaFabConfig(website_cookie="ASP.NET_SessionId=from-env")
    assert effective_website_cookie(cfg) == "ASP.NET_SessionId=from-env"


def test_discover_cookie_from_sqlite(tmp_path: Path):
    import sqlite3

    from secturafab import browser_session as bs

    db = tmp_path / "Cookies"
    conn = sqlite3.connect(str(db))
    conn.execute(
        "CREATE TABLE cookies (host_key TEXT, name TEXT, value TEXT, encrypted_value BLOB)"
    )
    conn.execute(
        "INSERT INTO cookies VALUES (?,?,?,?)",
        (".secturafab.com", ".AspNet.ApplicationCookie", "auth-token", b""),
    )
    conn.execute(
        "INSERT INTO cookies VALUES (?,?,?,?)",
        ("www.secturafab.com", "ASP.NET_SessionId", "sess", b""),
    )
    conn.commit()
    conn.close()
    profile = {
        "label": "test",
        "cookies": db,
        "local_state": tmp_path / "Local State",
    }
    with patch.object(bs, "_browser_cookie_dbs", return_value=[profile]):
        header = bs.discover_sectura_website_cookie(force=True)
    assert ".AspNet.ApplicationCookie=auth-token" in header
    assert "ASP.NET_SessionId=sess" in header
    status = bs.discover_status()
    assert status["session_found"] is True
    assert status["source"] == "test"
    assert "auth-token" not in str(status)
    assert status.get("error") in {"", None}


def _write_cookie_db(path: Path, *, host: str = ".secturafab.com") -> None:
    import sqlite3

    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute(
        "CREATE TABLE cookies (host_key TEXT, name TEXT, value TEXT, encrypted_value BLOB)"
    )
    conn.execute(
        "INSERT INTO cookies VALUES (?,?,?,?)",
        (host, ".AspNet.ApplicationCookie", "auth-token", b""),
    )
    conn.execute(
        "INSERT INTO cookies VALUES (?,?,?,?)",
        ("www.secturafab.com", "ASP.NET_SessionId", "sess", b""),
    )
    conn.commit()
    conn.close()


def test_locked_shutil_copy_still_reads_chrome_default(tmp_path: Path):
    """WinError 32 on shutil.copy2 must not hide Chrome Default cookies."""
    from secturafab import browser_session as bs

    db = tmp_path / "Default" / "Network" / "Cookies"
    _write_cookie_db(db)
    profile = {
        "label": "chrome:Default",
        "cookies": db,
        "local_state": tmp_path / "Local State",
        "profile_dir": tmp_path / "Default",
        "history_hit": True,
    }

    def _locked(*_a, **_k):
        raise OSError(32, "The process cannot access the file")

    with patch.object(bs, "_browser_cookie_dbs", return_value=[profile]), patch.object(
        bs.shutil, "copy2", side_effect=_locked
    ):
        header = bs.discover_sectura_website_cookie(force=True)
    assert header
    assert bs.session_found() is True
    assert bs.last_discover_source() == "chrome:Default"
    assert "auth-token" not in bs.last_discover_error()


def test_share_copy_when_sqlite_backup_and_copy2_fail(tmp_path: Path):
    import sqlite3

    from secturafab import browser_session as bs

    db = tmp_path / "Cookies"
    _write_cookie_db(db)
    profile = {
        "label": "chrome:Default",
        "cookies": db,
        "local_state": tmp_path / "Local State",
        "profile_dir": tmp_path,
        "history_hit": True,
    }

    with patch.object(bs, "_browser_cookie_dbs", return_value=[profile]), patch.object(
        bs, "_sqlite_backup_nolock", side_effect=sqlite3.Error("locked")
    ), patch.object(bs.shutil, "copy2", side_effect=OSError(32, "locked")):
        header = bs.discover_sectura_website_cookie(force=True)
    assert header
    assert bs.discover_status()["session_found"] is True


def test_chrome_default_ranks_before_profile_1():
    from secturafab.browser_session import _profile_rank

    default = {
        "label": "chrome:Default",
        "cookies": "C:/x/Default/Network/Cookies",
        "history_hit": True,
    }
    profile1 = {
        "label": "chrome:Profile 1",
        "cookies": "C:/x/Profile 1/Network/Cookies",
        "history_hit": False,
    }
    edge = {
        "label": "edge:Default",
        "cookies": "C:/x/Edge/Default/Network/Cookies",
        "history_hit": False,
    }
    ranked = sorted([profile1, edge, default], key=_profile_rank)
    assert ranked[0]["label"] == "chrome:Default"
    assert ranked[1]["label"] == "chrome:Profile 1"


def test_snapshot_uses_lock_bypass_when_share_and_copy2_fail(tmp_path: Path):
    """Exclusive Chrome lock: share-open/copy2 fail; backup/dup/VSS must still copy."""
    import shutil
    import sqlite3

    from secturafab import browser_session as bs

    db = tmp_path / "Cookies"
    _write_cookie_db(db)
    dest = tmp_path / "snap" / "Cookies"
    dest.parent.mkdir()

    def _bypass(src: Path, dest_path: Path, **_k) -> None:
        shutil.copy2(src, dest_path)

    with patch.object(bs, "_sqlite_backup_nolock", side_effect=sqlite3.Error("locked")), patch.object(
        bs, "_share_copy_with_wal", side_effect=OSError(32, "locked")
    ), patch.object(
        bs, "_shutil_copy_with_wal", side_effect=OSError(32, "locked")
    ), patch.object(bs, "_win_lock_bypass_with_wal", side_effect=_bypass):
        bs._snapshot_sqlite_file(db, dest)
    assert dest.is_file() and dest.stat().st_size > 0


def test_dup_handle_timeout_raises_quickly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from secturafab import browser_session as bs

    monkeypatch.setattr(bs, "_DUP_HANDLE_TIMEOUT_S", 0.35)

    def _hang(*_a, **_k):
        time.sleep(30)

    monkeypatch.setattr(bs, "_win_dup_handle_copy_inner", _hang)
    t0 = time.monotonic()
    with pytest.raises(OSError) as ei:
        bs._win_dup_handle_copy(tmp_path / "Cookies", tmp_path / "out")
    assert "dup_handle_timeout" in str(ei.value)
    assert time.monotonic() - t0 < 3.0


def test_lock_bypass_times_out_dup_then_uses_backup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import shutil

    from secturafab import browser_session as bs

    monkeypatch.setattr(bs, "_DUP_HANDLE_TIMEOUT_S", 0.35)
    monkeypatch.setattr(bs.os, "name", "nt")
    bs._cache["dup_timed_out"] = False
    bs._cache["lock_bypass_pinned"] = False
    bs._cache["lock_bypass"] = ""
    db = tmp_path / "Cookies"
    _write_cookie_db(db)
    dest = tmp_path / "snap" / "Cookies"
    dest.parent.mkdir()

    def _hang(*_a, **_k):
        time.sleep(30)

    def _ok(src: Path, dest_path: Path) -> None:
        shutil.copy2(src, dest_path)

    def _fail(*_a, **_k):
        raise OSError(32, "skip")

    with patch.object(bs, "_win_dup_handle_copy_inner", _hang), patch.object(
        bs, "_win_backup_copy", _ok
    ), patch.object(bs, "_win_ntcreatefile_backup_copy", _fail), patch.object(
        bs, "_win_esentutl_copy", _fail
    ), patch.object(bs, "_win_robocopy_backup_copy", _fail), patch.object(
        bs, "_win_vss_existing_copy", _fail
    ):
        t0 = time.monotonic()
        bs._win_lock_bypass_with_wal(db, dest, allow_vss=False)
    assert dest.is_file() and dest.stat().st_size > 0
    assert bs._cache["lock_bypass"] == "backup_priv"
    assert time.monotonic() - t0 < 4.0


def test_nt_native_path_strips_extended_prefix():
    from secturafab.browser_session import _nt_native_path

    assert _nt_native_path(r"C:\Users\kyle\Cookies") == r"\??\C:\Users\kyle\Cookies"
    assert _nt_native_path(r"\\?\C:\Users\kyle\Cookies") == r"\??\C:\Users\kyle\Cookies"
    assert _nt_native_path(r"\??\C:\Users\kyle\Cookies") == r"\??\C:\Users\kyle\Cookies"


def test_rank_browser_pids_puts_network_first():
    from secturafab import browser_session as bs

    def _cmd(pid: int) -> str:
        return {
            11: r"chrome.exe",
            22: r"chrome.exe --type=utility --utility-sub-type=network.mojom.NetworkService",
            33: r"chrome.exe --type=renderer",
            44: r"chrome.exe --type=utility --utility-sub-type=storage.mojom.StorageService",
        }[pid]

    with patch.object(bs, "_process_command_line", side_effect=_cmd):
        ranked = bs._rank_browser_pids([11, 22, 33, 44])
    assert ranked[0] == 22
    assert ranked[1] == 44
    assert 11 in ranked


def test_lock_bypass_creates_vss_when_allowed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import shutil

    from secturafab import browser_session as bs

    monkeypatch.setattr(bs.os, "name", "nt")
    bs._cache["dup_timed_out"] = False
    bs._cache["lock_bypass_pinned"] = False
    bs._cache["lock_bypass"] = ""
    db = tmp_path / "Cookies"
    _write_cookie_db(db)
    dest = tmp_path / "snap" / "Cookies"
    dest.parent.mkdir()
    order: list[str] = []

    def _fail(name: str):
        def _inner(*_a, **_k):
            order.append(name)
            raise OSError(32, name)

        return _inner

    def _vss(src: Path, dest_path: Path) -> None:
        order.append("vss")
        shutil.copy2(src, dest_path)

    with patch.object(bs, "_win_dup_handle_copy", _fail("dup_handle")), patch.object(
        bs, "_win_backup_copy", _fail("backup_priv")
    ), patch.object(bs, "_win_ntcreatefile_backup_copy", _fail("nt_backup")), patch.object(
        bs, "_win_vss_copy", _vss
    ):
        bs._win_lock_bypass_with_wal(db, dest, allow_vss=True)
    assert dest.is_file()
    assert bs._cache["lock_bypass"] == "vss"
    assert order == ["dup_handle", "backup_priv", "nt_backup", "vss"]


def test_history_snapshot_does_not_scan_handles(tmp_path: Path):
    import sqlite3

    from secturafab import browser_session as bs

    hist = tmp_path / "History"
    conn = sqlite3.connect(str(hist))
    conn.execute("CREATE TABLE urls (url TEXT)")
    conn.commit()
    conn.close()

    def _nope(*_a, **_k):
        raise AssertionError("lock bypass must not run for History")

    with patch.object(bs, "_win_lock_bypass_with_wal", side_effect=_nope):
        assert bs._history_has_sectura(tmp_path) is False


def test_win_paths_match_strips_extended_prefix():
    from secturafab.browser_session import _paths_match

    assert _paths_match(
        r"\\?\C:\Users\kyle\AppData\Local\Google\Chrome\User Data\Default\Network\Cookies",
        r"C:\Users\kyle\AppData\Local\Google\Chrome\User Data\Default\Network\Cookies",
    )
    assert _paths_match(
        r"\Device\HarddiskVolume3\Users\kyle\AppData\Local\Google\Chrome\User Data\Default\Network\Cookies",
        r"D:\unused\Google\Chrome\User Data\Default\Network\Cookies",
    )
    # FileNameInfo is volume-relative (no drive) when GetFinalPathName is empty.
    assert _paths_match(
        r"\Users\kyle\AppData\Local\Google\Chrome\User Data\Default\Network\Cookies",
        r"C:\Users\kyle\AppData\Local\Google\Chrome\User Data\Default\Network\Cookies",
    )


def test_snapshot_failure_reports_bypass_not_bare_oserror(tmp_path: Path):
    import sqlite3

    from secturafab import browser_session as bs

    db = tmp_path / "Cookies"
    db.write_bytes(b"x")
    profile = {
        "label": "chrome:Default",
        "cookies": db,
        "local_state": tmp_path / "Local State",
        "profile_dir": tmp_path,
        "history_hit": True,
    }

    def _fail(*_a, **_k):
        raise OSError(32, "locked")

    with patch.object(bs, "_browser_cookie_dbs", return_value=[profile]), patch.object(
        bs, "_sqlite_backup_nolock", side_effect=sqlite3.Error("locked")
    ), patch.object(bs, "_share_copy_with_wal", side_effect=_fail), patch.object(
        bs, "_shutil_copy_with_wal", side_effect=_fail
    ), patch.object(bs, "_win_lock_bypass_with_wal", side_effect=_fail), patch.object(
        bs.time, "sleep", return_value=None
    ):
        header = bs.discover_sectura_website_cookie(force=True)
    assert header == ""
    status = bs.discover_status()
    assert status["session_found"] is False
    assert status["source"] == "chrome:Default"
    err = status["error"]
    assert "OSError" not in err or "nolock" in err or "lock_bypass" in err
    assert "lock_bypass=" in err
    assert "do not paste" in err.lower()
    assert status["lock_bypass"]
    assert status["lock_bypass"] != ""
    assert status["lock_bypass"]
    assert "open_copy_failed" not in status["lock_bypass"]


def test_localserver32_cmd_uses_console():
    from secturafab.browser_session import _localserver32_cmd

    cmd = _localserver32_cmd(
        Path(r"C:\Program Files\Google\Chrome\Application\151.0.7922.174\elevation_service.exe")
    )
    assert "--console" in cmd
    assert "-Embedding" in cmd
    assert "elevation_service.exe" in cmd


def test_rm_file_pids_empty_off_windows(tmp_path: Path):
    from secturafab.browser_session import _rm_file_pids

    assert _rm_file_pids(tmp_path / "Cookies") == []


def test_unwrap_keeps_helper_timeout_as_chrome_dir():
    from secturafab import browser_session as bs

    b64 = base64.b64encode(b"APPB" + b"\x01" * 40).decode("ascii")

    def _no_elevator(*_a, **_k):
        raise AssertionError("in-process CoCreate must not run")

    with patch.object(
        bs, "_elevator_decrypt_via_chrome_dir", return_value=(None, "helper:timeout")
    ), patch.object(bs, "_elevator_decrypt", side_effect=_no_elevator):
        key, status, hr = bs._unwrap_app_bound_key(b64, v20_sample=b"v20" + b"\x00" * 40)
    assert key is None
    assert status == "chrome_dir"
    assert hr == "helper:timeout"
    assert "CLASSNOTREG" not in hr


def test_hr_label_surfaces_classnotreg():
    from secturafab.browser_session import _hr_label, _label_classnotreg

    assert _hr_label(0x80040154) == "0x80040154:CLASSNOTREG"
    assert _hr_label(-2147221164) == "0x80040154:CLASSNOTREG"
    assert _hr_label(0x80040155) == "0x80040155:IIDNOTREG"
    assert _hr_label(0x80080005) == "0x80080005:SERVER_EXEC_FAILURE"
    assert "CLASSNOTREG" in _label_classnotreg("0x80040154", "no_elevation_service")
    assert "no_elevation_service" in _label_classnotreg("0x80040154", "no_elevation_service")
    assert _hr_label(0) == "0x00000000"


def test_elevation_service_exes_finds_versioned_151(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from secturafab import browser_session as bs

    root = tmp_path / "Google" / "Chrome" / "Application"
    root.mkdir(parents=True)
    (root / "chrome.exe").write_bytes(b"mz")
    ver = root / "151.0.7922.174"
    ver.mkdir()
    (ver / "chrome.exe").write_bytes(b"mz")
    (ver / "elevation_service.exe").write_bytes(b"mz")
    monkeypatch.setenv("PROGRAMFILES", str(tmp_path))
    monkeypatch.delenv("PROGRAMFILES(X86)", raising=False)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    with patch.object(bs, "_chrome_exe_from_registry", return_value=Path()):
        exes = bs._elevation_service_exes()
        dirs = bs._chrome_helper_dirs()
    assert any(p.name.lower() == "elevation_service.exe" for p in exes)
    assert dirs and dirs[0].name == "151.0.7922.174"


def test_prepare_elevator_without_exe_is_classnotreg_reason():
    from secturafab import browser_session as bs

    with patch.object(bs.os, "name", "nt"), patch.object(
        bs, "_elevation_service_exes", return_value=[]
    ):
        assert bs._prepare_elevator_com() == "no_elevation_service"


def test_unwrap_helper_miss_is_chrome_dir_not_classnotreg():
    from secturafab import browser_session as bs

    b64 = base64.b64encode(b"APPB" + b"\x01" * 40).decode("ascii")

    def _no_elevator(*_a, **_k):
        raise AssertionError("in-process CoCreate must not run")

    with patch.object(
        bs, "_elevator_decrypt_via_chrome_dir", return_value=(None, "csc_missing")
    ), patch.object(bs, "_elevator_decrypt", side_effect=_no_elevator):
        key, status, hr = bs._unwrap_app_bound_key(b64, v20_sample=b"v20" + b"\x00" * 40)
    assert key is None
    assert status == "chrome_dir"
    assert hr == "csc_missing"
    assert "CLASSNOTREG" not in hr
    assert "0x80040154" not in hr


def test_discover_abe_hr_is_chrome_dir(tmp_path: Path):
    import sqlite3

    from secturafab import browser_session as bs

    db = tmp_path / "Cookies"
    conn = sqlite3.connect(str(db))
    conn.execute(
        "CREATE TABLE cookies (host_key TEXT, name TEXT, value TEXT, encrypted_value BLOB)"
    )
    conn.execute(
        "INSERT INTO cookies VALUES (?,?,?,?)",
        ("www.secturafab.com", "ASP.NET_SessionId", "", b"v20" + b"\x00" * 40),
    )
    conn.commit()
    conn.close()
    local_state = tmp_path / "Local State"
    local_state.write_text(
        json.dumps(
            {"os_crypt": {"app_bound_encrypted_key": base64.b64encode(b"APPB" + b"\x01" * 40).decode()}}
        ),
        encoding="utf-8",
    )
    profile = {
        "label": "chrome:Default",
        "cookies": db,
        "local_state": local_state,
        "profile_dir": tmp_path,
        "history_hit": True,
    }
    with patch.object(bs, "_browser_cookie_dbs", return_value=[profile]), patch.object(
        bs, "_unwrap_app_bound_key", return_value=(None, "chrome_dir", "csc_missing")
    ):
        header = bs.discover_sectura_website_cookie(force=True)
    assert header == ""
    status = bs.discover_status()
    assert status["abe"] == "chrome_dir"
    assert status["abe_hr"] == "csc_missing"
    assert "CLASSNOTREG" not in status["abe_hr"]
    assert "csc_missing" in status["error"]
    assert "do not paste" in status["error"].lower()


def test_app_bound_strips_appb_prefix():
    from secturafab.browser_session import _accept_aes_key, _app_bound_ciphertext

    inner = b"\x01\x02\x03\x04" + (b"\xab" * 20)
    b64 = base64.b64encode(b"APPB" + inner).decode("ascii")
    assert _app_bound_ciphertext(b64) == inner
    assert _accept_aes_key(b"x" * 32) == b"x" * 32
    assert _accept_aes_key(b"x" * 16) == b"x" * 16
    assert _accept_aes_key(b"too-short") is None
    packed = (32).to_bytes(4, "little") + (b"k" * 32) + b"trailer"
    assert _accept_aes_key(packed) == b"k" * 32


def test_v20_cookie_uses_abe_key_never_v10():
    from secturafab.browser_session import _BrowserKeys, _decrypt_cookie_value, _v20_cookie_text

    abe = os.urandom(32)
    v10 = os.urandom(32)
    nonce = os.urandom(12)
    secret = b"sectura-session-value"
    plain = (b"\x11" * 32) + secret
    payload = _aes_gcm_encrypt(plain, abe, nonce)
    blob = b"v20" + nonce + payload
    assert _decrypt_cookie_value(blob, _BrowserKeys(abe=abe, v10=v10)) == secret.decode()
    assert _decrypt_cookie_value(blob, _BrowserKeys(abe=None, v10=abe)) == ""
    assert _v20_cookie_text(plain) == secret.decode()


def test_v20_blobs_fail_closed_without_abe(tmp_path: Path):
    import sqlite3

    from secturafab import browser_session as bs

    db = tmp_path / "Cookies"
    conn = sqlite3.connect(str(db))
    conn.execute(
        "CREATE TABLE cookies (host_key TEXT, name TEXT, value TEXT, encrypted_value BLOB)"
    )
    conn.execute(
        "INSERT INTO cookies VALUES (?,?,?,?)",
        (
            "www.secturafab.com",
            "ASP.NET_SessionId",
            "",
            b"v20" + b"\x00" * 40,
        ),
    )
    conn.commit()
    conn.close()
    local_state = tmp_path / "Local State"
    local_state.write_text(
        json.dumps(
            {
                "os_crypt": {
                    "app_bound_encrypted_key": base64.b64encode(b"APPB" + b"\x01" * 40).decode(),
                    "encrypted_key": base64.b64encode(b"DPAPI" + b"\x02" * 40).decode(),
                }
            }
        ),
        encoding="utf-8",
    )
    profile = {
        "label": "chrome:Default",
        "cookies": db,
        "local_state": local_state,
        "profile_dir": tmp_path,
        "history_hit": True,
    }
    fake_v10 = b"V" * 32
    with patch.object(bs, "_browser_cookie_dbs", return_value=[profile]), patch.object(
        bs, "_unwrap_app_bound_key", return_value=(None, "failed", "0x80070005")
    ), patch.object(bs, "_v10_os_crypt_key", return_value=fake_v10):
        header = bs.discover_sectura_website_cookie(force=True)
    assert header == ""
    assert bs.session_found() is False
    status = bs.discover_status()
    assert status["session_found"] is False
    assert status["source"] == "chrome:Default"
    assert status["abe"] == "failed"
    assert status["abe_hr"] == "0x80070005"
    assert status["v20_blobs"] == 1
    assert status["v20_ok"] == 0
    assert "0x80070005" in status["error"]
    assert "do not paste" in status["error"].lower()
    assert "auth-token" not in str(status)
    assert fake_v10.hex() not in str(status)


def test_elevator_overflow_does_not_crash_discover(tmp_path: Path):
    """SysFreeString OverflowError must set abe=failed and keep source."""
    import sqlite3

    from secturafab import browser_session as bs

    db = tmp_path / "Cookies"
    conn = sqlite3.connect(str(db))
    conn.execute(
        "CREATE TABLE cookies (host_key TEXT, name TEXT, value TEXT, encrypted_value BLOB)"
    )
    conn.execute(
        "INSERT INTO cookies VALUES (?,?,?,?)",
        ("www.secturafab.com", "ASP.NET_SessionId", "", b"v20" + b"\x00" * 40),
    )
    conn.commit()
    conn.close()
    local_state = tmp_path / "Local State"
    local_state.write_text(
        json.dumps(
            {"os_crypt": {"app_bound_encrypted_key": base64.b64encode(b"APPB" + b"\x01" * 40).decode()}}
        ),
        encoding="utf-8",
    )
    profile = {
        "label": "chrome:Default",
        "cookies": db,
        "local_state": local_state,
        "profile_dir": tmp_path,
        "history_hit": True,
    }
    with patch.object(bs, "_browser_cookie_dbs", return_value=[profile]), patch.object(
        bs, "_elevator_decrypt_via_chrome_dir",
        side_effect=OverflowError("int too long to convert"),
    ), patch.object(
        bs, "_elevator_decrypt",
        side_effect=AssertionError("in-process CoCreate must not run"),
    ):
        header = bs.discover_sectura_website_cookie(force=True)
    assert header == ""
    status = bs.discover_status()
    assert status["session_found"] is False
    assert status["source"] == "chrome:Default"
    assert status["abe"] == "chrome_dir"
    assert status["abe_hr"] == "OverflowError"
    assert status["v20_blobs"] == 1
    assert status["v20_ok"] == 0
    assert "OverflowError" in status["error"]
    assert "do not paste" in status["error"].lower()


def test_bstr_free_uses_c_void_p_not_raw_int():
    """Win64 SysFreeString must get a pointer-width c_void_p."""
    import ctypes
    from ctypes import c_void_p
    from unittest.mock import Mock

    from secturafab.browser_session import _bstr_free

    ole = Mock()
    huge = 0x7FFF_FFFF_ABCD_1234
    _bstr_free(ole, huge)
    ole.SysFreeString.assert_called_once()
    arg = ole.SysFreeString.call_args[0][0]
    assert isinstance(arg, c_void_p)
    assert int(arg.value) == huge
    ole.SysFreeString.side_effect = OverflowError("int too long to convert")
    _bstr_free(ole, c_void_p(huge))  # must not raise


def test_discover_outer_catch_writes_abe_after_crash(tmp_path: Path):
    from secturafab import browser_session as bs

    profile = {
        "label": "chrome:Default",
        "cookies": tmp_path / "Cookies",
        "local_state": tmp_path / "Local State",
        "profile_dir": tmp_path,
        "history_hit": True,
    }

    def _boom(*_a, **_k):
        bs._cache["lock_bypass"] = "dup_handle"
        bs._cache["source"] = "chrome:Default"
        raise OverflowError("int too long to convert")

    with patch.object(bs, "_browser_cookie_dbs", return_value=[profile]), patch.object(
        bs, "_read_cookie_rows", side_effect=_boom
    ):
        header = bs.discover_sectura_website_cookie(force=True)
    assert header == ""
    status = bs.discover_status()
    assert status["session_found"] is False
    assert status["source"] == "chrome:Default"
    assert status["lock_bypass"] == "dup_handle"
    assert status["abe"] == "failed"
    assert status["abe_hr"] == "OverflowError"


def test_v20_discover_succeeds_with_elevator_key(tmp_path: Path):
    import sqlite3

    from secturafab import browser_session as bs

    abe = os.urandom(32)
    nonce = os.urandom(12)
    secret = b"sess-ok"
    payload = _aes_gcm_encrypt((b"\x22" * 32) + secret, abe, nonce)
    db = tmp_path / "Cookies"
    conn = sqlite3.connect(str(db))
    conn.execute(
        "CREATE TABLE cookies (host_key TEXT, name TEXT, value TEXT, encrypted_value BLOB)"
    )
    conn.execute(
        "INSERT INTO cookies VALUES (?,?,?,?)",
        ("www.secturafab.com", "ASP.NET_SessionId", "", b"v20" + nonce + payload),
    )
    conn.commit()
    conn.close()
    profile = {
        "label": "chrome:Default",
        "cookies": db,
        "local_state": tmp_path / "Local State",
        "profile_dir": tmp_path,
        "history_hit": True,
    }
    keys = bs._BrowserKeys(abe=abe, status="elevator", hr="0x00000000")
    with patch.object(bs, "_browser_cookie_dbs", return_value=[profile]), patch.object(
        bs, "_browser_keys", return_value=keys
    ):
        header = bs.discover_sectura_website_cookie(force=True)
    assert "ASP.NET_SessionId=sess-ok" in header
    status = bs.discover_status()
    assert status["session_found"] is True
    assert status["source"] == "chrome:Default"
    assert status["abe"] == "elevator"
    assert status["v20_ok"] == 1
    assert "sess-ok" not in str(status)


def test_finish_session_error_includes_abe_not_values():
    from secturafab import browser_session as bs
    from secturafab.push import SecturaFabPushService

    bs._cache.update(
        {
            "cookie": "",
            "session_found": False,
            "source": "chrome:Default",
            "error": "app-bound decrypt failed",
            "abe": "failed",
            "abe_hr": "0x80004005",
            "lock_bypass": "vss=create:5",
            "vss": "create:5",
        }
    )
    svc = SecturaFabPushService(MagicMock())
    msg = svc._finish_session_error()
    assert "session_found=false" in msg
    assert "lock_bypass=vss=create:5" in msg
    assert "vss=create:5" in msg
    assert "abe=failed" in msg
    assert "abe_hr=0x80004005" in msg
    assert "hidden-secret" not in msg
    assert "do not paste a cookie" in msg.lower()


def test_chrome_default_uses_cached_snapshot_when_live_copy_fails(tmp_path: Path):
    """Chrome-open copy can reuse a Cookies DB that already landed."""
    from secturafab import browser_session as bs

    live = tmp_path / "live" / "Cookies"
    live.parent.mkdir()
    live.write_bytes(b"locked")
    cached = tmp_path / "cache" / "Cookies"
    _write_cookie_db(cached)
    profile = {
        "label": "chrome:Default",
        "cookies": live,
        "local_state": tmp_path / "Local State",
        "profile_dir": tmp_path,
        "history_hit": True,
    }

    def _vss_miss(*_a, **_k):
        return False

    with patch.dict(os.environ, {"KANNON_COOKIE_CACHE": str(tmp_path / "cache")}), patch.object(
        bs, "_browser_cookie_dbs", return_value=[profile]
    ), patch.object(bs, "_try_nolock_copy", return_value=False), patch.object(
        bs, "_try_handle_dup_copy", return_value=False
    ), patch.object(bs, "_try_vss_create_copy", side_effect=_vss_miss), patch.object(
        bs, "_sqlite_backup_nolock", side_effect=OSError(32, "locked")
    ), patch.object(bs, "_share_copy_with_wal", side_effect=OSError(32, "locked")), patch.object(
        bs, "_shutil_copy_with_wal", side_effect=OSError(32, "locked")
    ):
        header = bs.discover_sectura_website_cookie(force=True)
    assert header
    status = bs.discover_status()
    assert "cached" in status["lock_bypass"]
    assert status["session_found"] is True
    assert status["source"] == "chrome:Default"


def test_vss_create_hresult_stays_visible_after_fallback(tmp_path: Path):
    from secturafab import browser_session as bs

    db = tmp_path / "Cookies"
    _write_cookie_db(db)
    profile = {
        "label": "chrome:Default",
        "cookies": db,
        "local_state": tmp_path / "Local State",
        "profile_dir": tmp_path,
        "history_hit": True,
    }

    def _vss_create(*_a, **_k):
        bs._record_vss("create:5")
        return False

    with patch.object(bs, "_browser_cookie_dbs", return_value=[profile]), patch.object(
        bs, "_try_nolock_copy", return_value=False
    ), patch.object(
        bs, "_try_vss_create_copy", side_effect=_vss_create
    ):
        header = bs.discover_sectura_website_cookie(force=True)
    assert header
    status = bs.discover_status()
    assert status["vss"] == "create:5"
    assert status["lock_bypass"].startswith("vss=create:5")


def test_lock_bypass_with_vss_prefixes_create_hresult():
    from secturafab import browser_session as bs

    bs._cache["vss"] = "create:5"
    assert (
        bs._lock_bypass_with_vss("dup_handle_not_found")
        == "vss=create:5;dup_handle_not_found"
    )
    bs._cache["vss"] = "ok"
    assert bs._lock_bypass_with_vss("") == "vss"


def test_later_profile_cannot_wipe_default_vss_pin():
    from secturafab import browser_session as bs

    bs._cache["lock_bypass_pinned"] = False
    bs._cache["vss"] = "ok"
    bs._set_lock_bypass("vss", pin=True)
    bs._set_lock_bypass(
        "dup_handle_not_found;backup_priv:errno 6;vss_existing:errno 1"
    )
    assert bs._cache["lock_bypass"] == "vss"
    assert bs._cache["vss"] == "ok"


def test_chrome_default_records_vss_skip_on_linux(tmp_path: Path):
    from secturafab import browser_session as bs

    db = tmp_path / "Cookies"
    _write_cookie_db(db)
    profile = {
        "label": "chrome:Default",
        "cookies": db,
        "local_state": tmp_path / "Local State",
        "profile_dir": tmp_path,
        "history_hit": True,
    }
    with patch.object(bs, "_browser_cookie_dbs", return_value=[profile]):
        header = bs.discover_sectura_website_cookie(force=True)
    assert header
    status = bs.discover_status()
    assert "nolock" in status["lock_bypass"]
    assert status["session_found"] is True


def test_chrome_default_uses_nolock_before_vss(tmp_path: Path):
    from secturafab import browser_session as bs

    db = tmp_path / "Cookies"
    _write_cookie_db(db)
    profile = {
        "label": "chrome:Default",
        "cookies": db,
        "local_state": tmp_path / "Local State",
        "profile_dir": tmp_path,
        "history_hit": True,
    }

    def _no_vss(*_a, **_k):
        raise AssertionError("VSS must not run when nolock lands Cookies")

    def _no_dup(*_a, **_k):
        raise AssertionError("handle-dup must not run when nolock lands Cookies")

    with patch.object(bs, "_browser_cookie_dbs", return_value=[profile]), patch.object(
        bs, "_try_vss_create_copy", side_effect=_no_vss
    ), patch.object(bs, "_try_handle_dup_copy", side_effect=_no_dup):
        header = bs.discover_sectura_website_cookie(force=True)
    assert header
    status = bs.discover_status()
    assert "nolock" in status["lock_bypass"]
    assert status["session_found"] is True
    assert status["source"] == "chrome:Default"


def test_vss_create_script_uses_cim_not_file_drive_arg():
    from secturafab import browser_session as bs

    script = bs._vss_create_ps1()
    assert "Invoke-CimMethod" in script
    assert "Win32_ShadowCopy" in script
    assert "ClientAccessible" in script
    assert "param($ArgsFile)" in script
    assert "param($Drive,$Rel,$Dest,$Status)" not in script


def test_parse_vssadmin_create_output():
    from secturafab import browser_session as bs

    text = (
        "Successfully created shadow copy for 'C:\\'\n"
        "    Shadow Copy ID: {C7C1D1A0-1111-2222-3333-444444444444}\n"
        "    Shadow Copy Volume Name: "
        "\\\\?\\GLOBALROOT\\Device\\HarddiskVolumeShadowCopy12\n"
    )
    parsed = bs._parse_vss_create_output(text)
    assert parsed is not None
    assert parsed[0] == "{C7C1D1A0-1111-2222-3333-444444444444}"
    assert parsed[1].endswith("HarddiskVolumeShadowCopy12")
    assert bs._parse_vss_create_output("VSS none") is None


def test_prefer_vss_status_keeps_create_returnvalue():
    from secturafab import browser_session as bs

    wrapped = "exc:MethodInvocationException:0x80131501"
    assert bs._prefer_vss_status(wrapped, "create:1") == "create:1"
    assert bs._prefer_vss_status("", wrapped) == wrapped


def test_vss_ps_command_is_args_file_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import subprocess

    from secturafab import browser_session as bs

    dest = tmp_path / "out" / "Cookies"
    dest.parent.mkdir()
    seen: dict[str, list[str]] = {}

    def fake_run(args, **_k):
        seen["args"] = [str(a) for a in args]
        dest.write_bytes(b"sqlite")
        (dest.parent / (dest.name + ".vss-status")).write_text("ok", encoding="ascii")
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(bs, "_windows_powershell", lambda: "powershell.exe")
    with patch.object(bs.subprocess, "run", side_effect=fake_run):
        bs._win_vss_ps_create_copy(tmp_path / "Cookies", dest, r"Users\x\Cookies", "C:")
    args = seen["args"]
    assert args[0] == "powershell.exe"
    file_i = args.index("-File")
    assert len(args) == file_i + 3
    assert not any(a == "C:\\" or a.endswith("\\") and a[1:2] == ":" for a in args)
    assert args[-1].endswith(".vss-args")
    assert bs._cache["vss"] == "ok"


def test_win_vss_copy_uses_vssadmin_after_cim_throw(tmp_path: Path):
    import shutil

    from secturafab import browser_session as bs

    real = tmp_path / "Cookies"
    _write_cookie_db(real)
    dest = tmp_path / "snap" / "Cookies"
    dest.parent.mkdir()
    order: list[str] = []

    class _Driven:
        drive = "C:"

        def resolve(self):
            return self

        def __str__(self) -> str:
            return r"C:\Users\kyle\AppData\Local\Google\Chrome\User Data\Default\Network\Cookies"

    def _ps(*_a, **_k):
        order.append("ps")
        bs._record_vss("exc:MethodInvocationException:0x80131501")
        raise OSError(1, "ps")

    def _va(_src: Path, dest_path: Path, rel: str, letter: str) -> None:
        order.append("vssadmin")
        assert letter == "C:"
        assert rel.replace("\\", "/").endswith("Cookies")
        shutil.copy2(real, dest_path)
        bs._record_vss("ok")

    def _ds(*_a, **_k):
        raise AssertionError("diskshadow must not run after vssadmin ok")

    with patch.object(bs, "_win_vss_ps_create_copy", _ps), patch.object(
        bs, "_win_vss_vssadmin_copy", _va
    ), patch.object(bs, "_win_vss_diskshadow_copy", _ds), patch.object(
        bs, "_enable_privilege", lambda *_a, **_k: None
    ):
        bs._cache["vss"] = ""
        bs._win_vss_copy(_Driven(), dest)  # type: ignore[arg-type]
    assert dest.is_file() and dest.stat().st_size > 0
    assert order == ["ps", "vssadmin"]
    assert bs._cache["vss"] == "ok"


def test_sqlite_has_cookie_table(tmp_path: Path):
    from secturafab.browser_session import _sqlite_has_cookie_table

    missing = tmp_path / "nope"
    assert _sqlite_has_cookie_table(missing) is False
    junk = tmp_path / "junk"
    junk.write_bytes(b"not-sqlite")
    assert _sqlite_has_cookie_table(junk) is False
    other = tmp_path / "other.db"
    import sqlite3

    conn = sqlite3.connect(str(other))
    conn.execute("CREATE TABLE hosts (name TEXT)")
    conn.commit()
    conn.close()
    assert _sqlite_has_cookie_table(other) is False
    cookies = tmp_path / "Cookies"
    _write_cookie_db(cookies)
    assert _sqlite_has_cookie_table(cookies) is True


def test_call_with_timeout_returns_default_on_hang():
    from secturafab import browser_session as bs

    def _hang() -> str:
        time.sleep(8)
        return "late"

    t0 = time.monotonic()
    got = bs._call_with_timeout(_hang, 0.25, (None, "0x80080005:SERVER_EXEC_FAILURE:timeout"))
    elapsed = time.monotonic() - t0
    assert got == (None, "0x80080005:SERVER_EXEC_FAILURE:timeout")
    assert elapsed < 2.0


def test_elevator_decrypt_times_out_with_server_exec_failure():
    from secturafab import browser_session as bs

    def _hang(_blob: bytes):
        time.sleep(8)
        return b"k" * 32, "0x00000000"

    with patch.object(bs.os, "name", "nt"), patch.object(
        bs, "_elevator_decrypt_uncapped", side_effect=_hang
    ):
        t0 = time.monotonic()
        key, hr = bs._elevator_decrypt(b"\x01" * 40)
        elapsed = time.monotonic() - t0
    assert key is None
    assert "0x80080005" in hr
    assert "SERVER_EXEC_FAILURE" in hr
    assert "timeout" in hr
    assert elapsed < 6.0


def test_chrome_default_uses_handle_dup_before_vss(tmp_path: Path):
    import shutil

    from secturafab import browser_session as bs

    db = tmp_path / "Cookies"
    _write_cookie_db(db)
    profile = {
        "label": "chrome:Default",
        "cookies": db,
        "local_state": tmp_path / "Local State",
        "profile_dir": tmp_path,
        "history_hit": True,
    }
    order: list[str] = []

    def _dup(src: Path, dest: Path) -> bool:
        order.append("dup")
        shutil.copy2(src, dest)
        return True

    def _vss(*_a, **_k):
        order.append("vss")
        raise AssertionError("VSS must not run when handle-dup lands Cookies")

    with patch.object(bs, "_browser_cookie_dbs", return_value=[profile]), patch.object(
        bs, "_try_nolock_copy", return_value=False
    ), patch.object(
        bs, "_try_handle_dup_copy", side_effect=_dup
    ), patch.object(bs, "_try_vss_create_copy", side_effect=_vss):
        header = bs.discover_sectura_website_cookie(force=True)
    assert header
    status = bs.discover_status()
    assert order == ["dup"]
    assert "dup_handle" in status["lock_bypass"]
    assert status["session_found"] is True
    assert status["source"] == "chrome:Default"


def test_abe_helper_has_no_cocreate():
    from secturafab import browser_session as bs

    assert bs._ABE_HELPER_TIMEOUT_S <= 8
    cs = bs._ABE_HELPER_CS
    assert "CoCreateInstance" not in cs
    assert "ole32" not in cs
    assert "LocalServer32" not in cs
    assert "elevation_service" not in cs
    assert "CLASSNOTREG" not in cs
    assert "ReadProcessMemory" in cs
    assert "VirtualQueryEx" in cs
    assert "cand=" in cs
    assert "AbePid" in cs
    assert "SkipPid" in cs
    assert "PreferPid" in cs
    assert "--type=" in cs
    assert "MEM_MAPPED" in cs
    assert "KANNON_CHROME_PIDS" in cs
    assert "memscan:no_chrome" in cs
    assert "memscan:no_browser" not in cs


def test_run_abe_helper_timeout_is_helper_timeout():
    import subprocess

    from secturafab import browser_session as bs

    def _expire(*_a, **_k):
        raise subprocess.TimeoutExpired(cmd="abe", timeout=8)

    with patch.object(bs.subprocess, "run", side_effect=_expire):
        key, hr = bs._run_abe_helper(Path("kannon_quote_abe.exe"), b"v20" + b"\x00" * 40)
    assert key is None
    assert hr == "helper:timeout"
    assert "CLASSNOTREG" not in hr


def test_persist_cookie_snapshot_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from secturafab import browser_session as bs

    monkeypatch.setenv("KANNON_COOKIE_CACHE", str(tmp_path / "cache"))
    src = tmp_path / "Cookies"
    _write_cookie_db(src)
    bs._persist_cookie_snapshot(src)
    dest = tmp_path / "out" / "Cookies"
    dest.parent.mkdir()
    assert bs._try_cached_cookie_copy(dest) is True
    assert bs._sqlite_has_cookie_table(dest)


def test_copy_dup_handle_bytes_tries_mapview_first():
    import inspect

    from secturafab.browser_session import _copy_dup_handle_bytes

    src = inspect.getsource(_copy_dup_handle_bytes)
    assert "_mapview_handle_to_file" in src
    assert src.index("_mapview_handle_to_file") < src.index("_read_handle_to_file")


def test_unwrap_source_never_cocreates():
    import inspect

    from secturafab import browser_session as bs

    src = inspect.getsource(bs._unwrap_app_bound_key)
    assert "_prepare_elevator_com" not in src
    assert "_elevator_decrypt(" not in src.replace("_elevator_decrypt_via_chrome_dir", "CHROME_DIR")


def test_unwrap_real_path_is_chrome_dir_not_classnotreg():
    from secturafab import browser_session as bs

    b64 = base64.b64encode(b"APPB" + b"\x01" * 40).decode("ascii")
    key, status, hr = bs._unwrap_app_bound_key(b64, v20_sample=b"v20" + b"\x00" * 40)
    assert key is None
    assert status == "chrome_dir"
    assert "CLASSNOTREG" not in hr
    assert "0x80040154" not in hr
    assert "chrome_dir:not_nt" in hr or "csc_missing" in hr or "memscan:not_nt" in hr


def test_unwrap_uses_chrome_dir_helper_first():
    from secturafab import browser_session as bs

    b64 = base64.b64encode(b"APPB" + b"\x01" * 40).decode("ascii")
    key = b"k" * 32

    def _no_elevator(*_a, **_k):
        raise AssertionError("in-process CoCreate must not run when chrome_dir returns a key")

    with patch.object(
        bs, "_elevator_decrypt_via_chrome_dir", return_value=(key, "0x00000000")
    ), patch.object(bs, "_elevator_decrypt", side_effect=_no_elevator):
        got, status, hr = bs._unwrap_app_bound_key(b64, v20_sample=b"v20" + b"\x00" * 40)
    assert got == key
    assert status == "chrome_dir"
    assert hr == "0x00000000"


def test_user_abe_helper_dirs_skips_program_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from secturafab import browser_session as bs

    pf = tmp_path / "Program Files" / "Google" / "Chrome" / "Application" / "151.0.7922.174"
    pf.mkdir(parents=True)
    (pf / "chrome.exe").write_bytes(b"mz")
    local = tmp_path / "Local"
    monkeypatch.setenv("PROGRAMFILES", str(tmp_path / "Program Files"))
    monkeypatch.setenv("LOCALAPPDATA", str(local))
    with patch.object(bs, "_chrome_helper_dirs", return_value=[pf]):
        dirs = bs._user_abe_helper_dirs()
    assert dirs
    assert all("program files" not in str(d).lower() for d in dirs)
    assert any(d.name == "151.0.7922.174" and "Local" in str(d) for d in dirs)
    assert any(d.name == "abe" for d in dirs)


def test_install_abe_helper_writes_localapp_not_program_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from secturafab import browser_session as bs

    helper = tmp_path / "kannon_quote_abe.exe"
    helper.write_bytes(b"mz")
    local = tmp_path / "Local"
    dest_dir = local / "KannonQuote" / "abe"
    monkeypatch.setenv("LOCALAPPDATA", str(local))
    with patch.object(bs, "_user_abe_helper_dirs", return_value=[dest_dir]):
        dests, hr = bs._install_abe_helper(helper)
    assert hr == ""
    assert dests and dests[0].is_file()
    assert "Program Files" not in str(dests[0])


def test_extract_abe_candidate_ptrs_follows_vector():
    import struct

    from secturafab import browser_session as bs

    key_addr = 0x000001A2B3C4D500
    buf = bytearray(48)
    struct.pack_into("<QQQ", buf, 0, key_addr, key_addr + 32, key_addr + 32)
    assert (key_addr, 32) in bs._extract_abe_candidate_ptrs(bytes(buf))


def test_inline_bstr_keys_reads_after_size_t_and_dword():
    from secturafab import browser_session as bs

    junk = bytes(range(32))
    blob = b"\x20\x00\x00\x00\x00\x00\x00\x00" + junk
    assert junk in bs._inline_bstr_keys(blob)
    bstr = b"\x20\x00\x00\x00" + junk
    assert junk in bs._inline_bstr_keys(bstr)


def test_keys_from_key_blob_parses_elevator_layout():
    from secturafab import browser_session as bs

    key = bytes(range(32))
    blob = (8).to_bytes(4, "little") + b"validate" + (32).to_bytes(4, "little") + key
    assert key in bs._keys_from_key_blob(blob)


def test_chrome_abe_cmd_ok_skips_renderer():
    from secturafab import browser_session as bs

    assert bs._chrome_abe_cmd_ok("") is True
    assert bs._chrome_abe_cmd_ok(r"C:\...\chrome.exe") is True
    assert (
        bs._chrome_abe_cmd_ok(r'chrome.exe --utility-sub-type=network.mojom.NetworkService')
        is True
    )
    assert bs._chrome_abe_cmd_ok(r"chrome.exe --type=utility") is True
    assert bs._chrome_abe_cmd_ok(r"chrome.exe --type=renderer") is False
    assert bs._chrome_abe_cmd_ok(r"chrome.exe --type=gpu-process") is False


def test_chrome_pids_prioritized_falls_back_to_running_chrome():
    from secturafab import browser_session as bs

    with patch.object(bs, "_chrome_pids", return_value=[111, 222]), patch.object(
        bs.subprocess, "run", side_effect=OSError("no powershell")
    ):
        assert bs._chrome_pids_prioritized() == [111, 222]


def test_pick_v20_sample_skips_short():
    from secturafab import browser_session as bs

    short = b"v20" + b"\x00" * 10
    long = b"v20" + b"\x00" * 40
    assert bs._pick_v20_sample([("h", "n", "", short)]) is None
    assert bs._pick_v20_sample([("h", "n", "", short), ("h", "n", "", long)]) == long


def test_chrome_dir_copy_denied_is_not_classnotreg(tmp_path: Path):
    from secturafab import browser_session as bs

    helper = tmp_path / "kannon_quote_abe.exe"
    helper.write_bytes(b"mz")

    def _denied(*_a, **_k):
        exc = OSError(13, "Permission denied")
        raise exc

    with patch.object(bs.os, "name", "nt"), patch.object(
        bs, "_compiled_abe_helper_exe", return_value=(helper, "")
    ), patch.object(
        bs, "_user_abe_helper_dirs", return_value=[tmp_path / "abe"]
    ), patch.object(
        bs.shutil, "copy2", side_effect=_denied
    ), patch.object(
        bs, "_run_abe_helper", return_value=(None, "helper:exit1")
    ), patch.object(
        bs, "_memscan_abe_key", return_value=(None, "memscan:no_key")
    ):
        key, hr = bs._elevator_decrypt_via_chrome_dir(b"v20" + b"\x00" * 40)
    assert key is None
    assert "CLASSNOTREG" not in hr
    assert "copy:errno13" in hr or "helper:exit1" in hr or "memscan:no_key" in hr


def test_key_from_helper_candidates_decrypts_v20():
    from secturafab import browser_session as bs

    key = os.urandom(32)
    nonce = os.urandom(12)
    plain = (b"\x11" * 32) + b"session"
    payload = _aes_gcm_encrypt(plain, key, nonce)
    sample = b"v20" + nonce + payload
    stdout = f"cand={'00' * 32}\ncand={key.hex()}\n".encode("ascii")
    got = bs._key_from_helper_candidates(stdout, sample)
    assert got == key


def test_profile_1_does_not_run_vss_or_lock_bypass(tmp_path: Path):
    from secturafab import browser_session as bs

    db = tmp_path / "Cookies"
    _write_cookie_db(db)
    profile = {
        "label": "chrome:Profile 1",
        "cookies": db,
        "local_state": tmp_path / "Local State",
        "profile_dir": tmp_path,
        "history_hit": False,
    }

    def _nope(*_a, **_k):
        raise AssertionError("Profile 1 must not CREATE VSS or lock-bypass")

    with patch.object(bs, "_browser_cookie_dbs", return_value=[profile]), patch.object(
        bs, "_win_vss_copy", side_effect=_nope
    ), patch.object(bs, "_win_lock_bypass_with_wal", side_effect=_nope):
        header = bs.discover_sectura_website_cookie(force=True)
    assert header
    status = bs.discover_status()
    assert status["vss"] == ""
    assert status["source"] == "chrome:Profile 1"


def _aes_gcm_encrypt(plain: bytes, key: bytes, nonce: bytes) -> bytes:
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        return AESGCM(key).encrypt(nonce, plain, None)
    except Exception:  # noqa: BLE001
        from Crypto.Cipher import AES  # type: ignore[import-untyped]

        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        ct, tag = cipher.encrypt_and_digest(plain)
        return ct + tag
