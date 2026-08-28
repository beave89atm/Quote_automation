"""App drop/push path: process_job + push_job_secturafab → website Image Files / Long.

Unit tests only. Do not claim live Sectura success from these.
Never PATCH a7dc46bf (Kyle-confirmed 1001898-1) or other forbidden quotes.
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from secturafab.forbidden_quotes import (
    FORBIDDEN_LIVE_QUOTE_IDS,
    ForbiddenQuoteError,
    refuse_forbidden_quote_write,
)
from secturafab.org_ops import TIME_WACO_ORG_ID, TIME_WACO_ORG_NAME
from secturafab.client import SecturaFabApiError
from secturafab.push import (
    SecturaFabPushService,
    classify_sectura_item,
    _shop_material,
)
from secturafab.qa_harness import evaluate_quote_get
from secturafab.website import (
    EMPTY_GUID,
    WELD_CALC_PARAM_TYPE,
    WELD_OPERATION_CODE,
    build_add_feature_payload,
    build_copy_move_assembly_payload,
    build_weld_add_operation_payload,
    internal_data_from_holes,
)
from tests.fixtures.live_get_1001898 import (
    ASSEMBLY_DESC,
    HEADER_DESC,
    TIME_ORG,
    gold_1001898_get,
)
from tests.fixtures.time_gold import DASH_1001898
from tests.test_lom_xlsx import _1001898_lom_rows, write_excel_absolute_target_xlsx


def _bom_rows() -> list[dict]:
    return [
        {"part_no": pn, "qty": qty, "description": desc}
        for _i, qty, pn, desc in DASH_1001898
    ]


def test_classify_1004747_angles_channel_tube_are_linear():
    assert classify_sectura_item("32259-1 RETAINER BAR, HOSE") == "Linear"
    assert classify_sectura_item("1004740-1 MASTER CYLINDER MOUNT CHANNEL") == "Linear"
    assert classify_sectura_item("25060-6 TUBE, PIVOT") == "Linear"


def test_classify_plate_over_three_quarter_is_component():
    assert classify_sectura_item("1.25 A572 RING Ø23.5/Ø12 OUTSOURCE") == "Component"
    assert classify_sectura_item("1 A572 26.375 SQ OUTSOURCE") == "Component"
    assert classify_sectura_item('1/4" A36 PLATE') == "Cad"
    assert classify_sectura_item("FORMED ANGLE 1/4 A36 PLATE") == "Cad"
    assert classify_sectura_item("21689-1 HOSE GUARD") == "Linear"


def test_never_a569_material():
    assert _shop_material("A569") == "A36"
    assert _shop_material("A572") == "A572"
    assert _shop_material("") == "A36"


def test_weld_add_operation_is_q10056_shape():
    payload = build_weld_add_operation_payload(
        "new-qid",
        "asm-1",
        weld_inches=308.66,
        weld_hours=154.33 / 60.0,
        fitup_hours=108.0 / 60.0,
        setup_hours=0.25,
    )
    assert payload["operation_code"] == WELD_OPERATION_CODE
    assert payload["Equipment"] == "Welding"
    assert payload["ApplyTo"] == "ITEM"
    assert payload["CalcParamType"] == WELD_CALC_PARAM_TYPE
    assert payload["weld"] == pytest.approx(308.66)
    assert payload["perunittime"] == pytest.approx(154.33 / 60.0)
    assert payload["perunittime2"] == pytest.approx(108.0 / 60.0)
    assert payload["fixedtime"] == pytest.approx(0.25)


def test_copy_move_and_internal_payloads():
    move = build_copy_move_assembly_payload("qid", "kid", "asm", mode="Move")
    assert move["AssemblyID"] == "asm"
    assert move["Mode"] == "Move"
    feat = build_add_feature_payload("qid", "cad-1", diameter=0.375, qty=4)
    assert feat["FeatureType"] == "Internal"
    assert feat["Diameter"] == 0.375
    blob = internal_data_from_holes([{"diameter": 0.375, "qty": 4}])
    assert "0.375" in blob


def test_refuse_forbidden_quote_writes():
    for qid in FORBIDDEN_LIVE_QUOTE_IDS:
        with pytest.raises(ForbiddenQuoteError, match="forbidden"):
            refuse_forbidden_quote_write(
                method="POST", path="v1/quote", payload={"ID": qid}
            )
        refuse_forbidden_quote_write(
            method="GET", path=f"v1/quote/{qid}", payload=None
        )


def test_flat_root_kids_fail_qa():
    payload = gold_1001898_get()
    for it in payload["ItemList"][1:]:
        it["AssemblyID"] = None
    result = evaluate_quote_get(
        payload,
        part_key="1001898-1",
        expected_org=TIME_ORG,
        expected_header=HEADER_DESC,
        expected_assembly_title=ASSEMBLY_DESC,
        bom_rows=_bom_rows(),
    )
    assert result.ok is False
    assert any("Flat root kids" in f for f in result.failures)


def test_gold_get_with_kids_under_assembly_passes():
    payload = gold_1001898_get()
    result = evaluate_quote_get(
        payload,
        part_key="1001898-1",
        expected_org=TIME_ORG,
        expected_header=HEADER_DESC,
        expected_assembly_title=ASSEMBLY_DESC,
        bom_rows=_bom_rows(),
    )
    assert result.ok is True
    assert payload["PrimaryOrganizationID"] == TIME_WACO_ORG_ID


def test_push_job_pdf_time_weldment_calls_website_path(tmp_path: Path):
    pdf = tmp_path / "1001898-1.pdf"
    pdf.write_bytes(b"%PDF")
    lib = tmp_path / "Customer Drawings" / "Time" / "Pedestal Weldment - 1001898-1"
    lib.mkdir(parents=True)
    write_excel_absolute_target_xlsx(lib / "1001898-1-LOM.xlsx", _1001898_lom_rows())
    for pn in ("14501-1", "1001880-2", "9905-1", "1005940-1"):
        (lib / f"{pn}.pdf").write_bytes(b"%PDF")

    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=box"
    populated = gold_1001898_get()
    _n = {"i": 0}

    def _get_json(_path):
        _n["i"] += 1
        if _n["i"] == 1:
            return {"QuoteNumber": "1001898-1", "ItemCount": 0, "ItemList": []}
        return populated

    client.get_json.side_effect = _get_json
    save = MagicMock()
    save.status_code = 200
    client.request.return_value = save
    service = SecturaFabPushService(client=client)
    new_id = "11111111-aaaa-bbbb-cccc-000000000001"
    assert new_id not in FORBIDDEN_LIVE_QUOTE_IDS

    times = {
        "weld_minutes": 154.33,
        "total_inches": 308.66,
        "fitup_with_fixture_minutes": 108.0,
        "fitup_no_fixture_minutes": 162.0,
    }
    with patch.object(service, "upload_drawings_quote_request", return_value="qr"), patch.object(
        service, "create_quote", return_value=new_id
    ) as create_q, patch.object(
        service, "allocate_quote_number", return_value="1001898-1"
    ), patch.object(
        service, "finish_pdf_files", return_value=["Image Files Finish"]
    ) as pdf_finish, patch.object(
        service, "finish_linear_bom_rows", return_value=["Long Finish"]
    ) as lin_finish, patch.object(
        service, "finish_website_weldment", return_value=["Copy/Move kids", "Components"]
    ) as weldment, patch.object(
        service, "nest_after_finish", return_value=["Nest"]
    ), patch.object(
        service, "quick_add_cad"
    ) as qadd, patch(
        "secturafab.push.ensure_weld_ops",
        return_value=["AddOperation op_weld CalcParamType=" + WELD_CALC_PARAM_TYPE],
    ) as weld, patch(
        "secturafab.push.ensure_imperial_item_units", return_value=[]
    ), patch(
        "secturafab.push.apply_bom_quantities", return_value=[]
    ), patch(
        "secturafab.push.refresh_bom_rows_for_push",
        return_value=(_bom_rows(), []),
    ), patch(
        "secturafab.push.apply_quote_organization",
        return_value=[f"Set Organization: {TIME_WACO_ORG_NAME} ({TIME_WACO_ORG_ID})"],
    ), patch(
        "secturafab.push.persist_classified_item_fields", return_value=[]
    ), patch(
        "secturafab.push.persist_quote_header", return_value=[]
    ), patch(
        "secturafab.push.retype_linears_to_pt10_keep_persist", return_value=[]
    ), patch(
        "secturafab.push.extract_assembly_description",
        return_value="PEDESTAL WELDMENT",
    ), patch(
        "secturafab.push.ensure_laser_profile_ops"
    ) as graft:
        result = service.push_job(
            title="1001898-1",
            pdf_filename="1001898-1.pdf",
            pdf_path=pdf,
            stp_path=None,
            takeoff={
                "library": {
                    "part_key": "1001898-1",
                    "folder": str(lib),
                    "searched_roots": [str(lib.parent.parent)],
                    "related_pdfs": [f"{pn}.pdf" for pn in ("14501-1",)],
                },
                "bom_config": "1",
            },
            times=times,
            job_id=92,
        )
    assert result.ok is True
    assert result.quote_id == new_id
    assert result.quote_id not in FORBIDDEN_LIVE_QUOTE_IDS
    create_q.assert_called_once()
    pdf_finish.assert_called()
    lin_finish.assert_called()
    weldment.assert_called()
    weld.assert_called()
    qadd.assert_not_called()
    graft.assert_not_called()
    qa = evaluate_quote_get(
        populated,
        part_key="1001898-1",
        expected_org=TIME_ORG,
        expected_header=HEADER_DESC,
        expected_assembly_title=ASSEMBLY_DESC,
        bom_rows=_bom_rows(),
    )
    assert qa.ok is True


_RELOAD = ("app.paths", "app.db", "app.auth", "app.services")


def _reload_app() -> None:
    for name in _RELOAD:
        if name in sys.modules:
            importlib.reload(sys.modules[name])
        else:
            importlib.import_module(name)


def test_app_process_job_then_push_uses_website_weldment(tmp_path: Path, monkeypatch):
    """process_job / push_job_secturafab is the app drop/push link."""
    data_dir = tmp_path / "kannon-data"
    data_dir.mkdir()
    previous = os.environ.get("KANNON_DATA_DIR")
    monkeypatch.setenv("KANNON_DATA_DIR", str(data_dir))
    _reload_app()
    try:
        from app.db import Job, SessionLocal, init_db
        from app.services import process_job, push_job_secturafab
        from quote_core.weld.takeoff import WeldLineItem, WeldTakeoffResult

        init_db()
        pdf = tmp_path / "1001898-1.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        lib = tmp_path / "Time" / "Pedestal Weldment - 1001898-1"
        lib.mkdir(parents=True)
        write_excel_absolute_target_xlsx(lib / "1001898-1-LOM.xlsx", _1001898_lom_rows())

        db = SessionLocal()
        job = Job(
            title="1001898-1",
            status="uploaded",
            pdf_filename="1001898-1.pdf",
            pdf_path=str(pdf),
            bom_config="1",
            efficiency_pct=85.0,
        )
        db.add(job)
        db.commit()
        job_id = job.id
        db.close()

        items = [
            WeldLineItem(
                size="1/4",
                inches=308.66,
                joint_notes="fillet symbols",
                confidence="high",
                source="symbols",
            )
        ]
        takeoff = WeldTakeoffResult(
            items=items,
            flags=[],
            fitup_drivers={
                "part_count": 27,
                "joint_count": 26,
                "assembly_weight_lb": 400.0,
                "component_weights_lb": [10.0] * 17,
                "needs_info": False,
            },
        )
        captured: dict = {}

        def _fake_push(**kwargs):
            captured.update(kwargs)
            from secturafab.push import PushResult

            return PushResult(
                ok=True,
                quote_id="11111111-aaaa-bbbb-cccc-000000000002",
                quote_number="1001898-1",
                created_new_quote=True,
                item_count=18,
                notes=[
                    "Image Files Finish POST /Quote/AddItem_PDFFiles",
                    "Long POST /Quote/AddItem_Linear",
                    "Copy/Move kids into Assembly",
                    f"AddOperation {WELD_OPERATION_CODE} CalcParamType={WELD_CALC_PARAM_TYPE}",
                    f"Set Organization: {TIME_WACO_ORG_NAME} ({TIME_WACO_ORG_ID})",
                ],
                status="complete",
            )

        with patch(
            "app.services.run_weld_takeoff", return_value=takeoff
        ), patch(
            "app.services.attach_library_stp",
            return_value={
                "folder": str(lib),
                "part_key": "1001898-1",
                "related_pdfs": [],
                "notes": [],
            },
        ), patch(
            "quote_core.lom_clip.ensure_lom_xlsx",
            return_value=(lib / "1001898-1-LOM.xlsx", []),
        ):
            process_job(job_id)

        db = SessionLocal()
        job = db.get(Job, job_id)
        assert job is not None
        assert job.status in {"review", "needs_info"}
        stored_times = job.times()
        stored_takeoff = job.takeoff()
        db.close()
        assert stored_times.get("weld_minutes", 0) > 0
        assert stored_takeoff.get("total_inches", 0) > 0

        with patch("secturafab.push.SecturaFabPushService") as svc_cls:
            inst = MagicMock()
            inst.push_job.side_effect = lambda **kw: _fake_push(**kw)
            svc_cls.return_value = inst
            push_job_secturafab(job_id)
            inst.push_job.assert_called_once()
            kwargs = inst.push_job.call_args.kwargs
            assert kwargs["title"] == "1001898-1"
            assert kwargs["times"]["weld_minutes"] > 0
            assert Path(kwargs["pdf_path"]).name == "1001898-1.pdf"
            assert kwargs.get("stp_path") in (None, Path(""))

        db = SessionLocal()
        job = db.get(Job, job_id)
        sf = (job.takeoff() or {}).get("secturafab") or {}
        db.close()
        assert sf.get("ok") is True
        assert sf.get("quote_id") not in FORBIDDEN_LIVE_QUOTE_IDS
        assert sf.get("quote_number") == "1001898-1"
        blob = " ".join(sf.get("notes") or [])
        assert "AddItem_PDFFiles" in blob or "Image Files" in blob
        assert "AddItem_Linear" in blob or "Long" in blob
        assert "AddOperation" in blob
        assert "Time Manufacturing Waco" in blob
    finally:
        if previous is None:
            os.environ.pop("KANNON_DATA_DIR", None)
        else:
            os.environ["KANNON_DATA_DIR"] = previous
        _reload_app()


def test_ensure_weld_ops_uses_add_operation_when_cookie():
    from secturafab.weld_ops import ensure_weld_ops

    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=box"
    client.get_json.return_value = {
        "ItemList": [
            {
                "ID": "asm-1",
                "Description": "1001898-1 - PEDESTAL WELDMENT",
                "ProductType": 300,
                "IsAssembly": True,
                "Quantity": 1,
                "OperationCostList": [],
            },
            {
                "ID": "cad-1",
                "Description": "14501-1 PEDESTAL TOP PLATE",
                "ProductType": 100,
                "Quantity": 1,
                "OperationCostList": [],
            },
        ]
    }
    client.add_operation.return_value = {"ok": True}
    notes = ensure_weld_ops(
        client,
        "new-qid",
        times={
            "weld_minutes": 154.33,
            "total_inches": 308.66,
            "fitup_with_fixture_minutes": 108.0,
        },
        part_key="1001898-1",
    )
    client.add_operation.assert_called_once()
    kwargs = client.add_operation.call_args.kwargs
    assert kwargs["item_id"] == "asm-1"
    assert kwargs["weld_inches"] == pytest.approx(308.66)
    assert any("AddOperation" in n and "op_weld" in n for n in notes)
    client.request.assert_not_called()


def test_cadimport_rows_are_not_success_without_product_type_100_read(tmp_path, monkeypatch):
    """Attachment FileList + AddItem_PDFFiles 200 is not success until item read shows PT 100."""
    monkeypatch.setenv("SECTURA_WEBSITE_COOKIE", "ASP.NET_SessionId=box")
    pdf = tmp_path / "14501-1.pdf"
    pdf.write_bytes(b"%PDF")
    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=box"
    client.get_item_add_view.return_value = {}
    client.upload_item_pdf_attachment.return_value = {
        "FileID": "att-1",
        "ImageID": "img-1",
        "FileName": "14501-1.pdf",
        "Thickness": 0.1875,
        "Length": 21.875,
        "Width": 21.875,
    }
    client.add_item_pdf_files.return_value = {"ok": True}
    client.quote_item_read.return_value = {"Data": [], "Total": 0}
    client.get_json.return_value = {"ItemList": []}

    notes = SecturaFabPushService(client=client).finish_pdf_files(
        quote_id="11111111-aaaa-bbbb-cccc-000000000010",
        pdf_files=[pdf],
        material="A36",
        thickness="0.1875",
        qty=1,
        description="14501-1 PEDESTAL TOP PLATE",
    )
    client.upload_item_dxf_files.assert_not_called()
    assert client.upload_item_pdf_attachment.called
    assert client.add_item_pdf_files.called
    posted = client.add_item_pdf_files.call_args_list[0].kwargs["file_list"][0]
    assert posted["ItemType"] == "cad"
    assert posted["Status"] == 1
    assert posted["Machine"] == "Laser"
    assert posted["Thickness"] not in (None, "")
    assert posted["Length"] not in (None, "")
    assert posted["Width"] not in (None, "")
    assert client.quote_item_read.called or client.get_json.called
    blob = " ".join(notes)
    assert "0 ProductType 100" in blob
    assert "CadImport list is not success" in blob
    assert "persisted" not in blob.lower()
    assert "/Attachment/UploadItem_PDFFiles" in blob


def test_linear_http_500_does_not_abort_weld_or_nest(tmp_path, monkeypatch):
    """A Long AddItem_Linear HTTP 500 must not skip weld or nest."""
    monkeypatch.setenv("SECTURA_WEBSITE_COOKIE", "ASP.NET_SessionId=box")
    pdf = tmp_path / "1001898-1.pdf"
    pdf.write_bytes(b"%PDF")
    lib = tmp_path / "Customer Drawings" / "Time" / "Pedestal Weldment - 1001898-1"
    lib.mkdir(parents=True)
    write_excel_absolute_target_xlsx(lib / "1001898-1-LOM.xlsx", _1001898_lom_rows())
    (lib / "14501-1.pdf").write_bytes(b"%PDF")

    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=box"
    client.get_json.return_value = {
        "QuoteNumber": "1004747-1",
        "ItemCount": 0,
        "ItemList": [],
    }
    save = MagicMock()
    save.status_code = 200
    client.request.return_value = save
    service = SecturaFabPushService(client=client)
    new_id = "11111111-aaaa-bbbb-cccc-000000000011"
    assert new_id not in FORBIDDEN_LIVE_QUOTE_IDS
    linear_err = SecturaFabApiError(
        "API request failed (500) for /Quote/AddItem_Linear",
        status_code=500,
        body="error",
    )
    with patch.object(service, "upload_drawings_quote_request", return_value="qr"), patch.object(
        service, "create_quote", return_value=new_id
    ), patch.object(
        service, "allocate_quote_number", return_value="1004747-1"
    ), patch.object(
        service, "finish_pdf_files", return_value=["Image Files Finish"]
    ), patch.object(
        service, "finish_linear_bom_rows", side_effect=linear_err
    ) as lin, patch.object(
        service, "finish_website_weldment", return_value=["Copy/Move kids"]
    ) as weldment, patch.object(
        service, "nest_after_finish", return_value=["Nest"]
    ) as nest, patch.object(
        service, "quick_add_cad"
    ) as qadd, patch(
        "secturafab.push.ensure_weld_ops",
        return_value=["AddOperation op_weld"],
    ) as weld, patch(
        "secturafab.push.ensure_imperial_item_units", return_value=[]
    ), patch(
        "secturafab.push.apply_bom_quantities", return_value=[]
    ), patch(
        "secturafab.push.refresh_bom_rows_for_push",
        return_value=(_bom_rows(), []),
    ), patch(
        "secturafab.push.apply_quote_organization",
        return_value=[f"Set Organization: {TIME_WACO_ORG_NAME}"],
    ), patch(
        "secturafab.push.persist_classified_item_fields", return_value=[]
    ), patch(
        "secturafab.push.persist_quote_header", return_value=[]
    ), patch(
        "secturafab.push.retype_linears_to_pt10_keep_persist", return_value=[]
    ), patch(
        "secturafab.push.extract_assembly_description",
        return_value="OUTER BOOM WELDMENT",
    ), patch(
        "secturafab.push.ensure_laser_profile_ops"
    ) as graft:
        result = service.push_job(
            title="1004747-1",
            pdf_filename="1004747-1.pdf",
            pdf_path=pdf,
            stp_path=None,
            takeoff={
                "library": {
                    "part_key": "1004747-1",
                    "folder": str(lib),
                    "searched_roots": [str(lib.parent.parent)],
                    "related_pdfs": ["14501-1.pdf"],
                },
                "bom_config": "1",
            },
            times={
                "weld_minutes": 154.33,
                "total_inches": 308.66,
                "fitup_with_fixture_minutes": 108.0,
            },
            job_id=93,
        )
    lin.assert_called()
    nest.assert_called()
    weld.assert_called()
    weldment.assert_called()
    qadd.assert_not_called()
    graft.assert_not_called()
    blob = " ".join(result.notes or []) + " " + (result.error or "")
    assert "not aborting weld/nest" in blob
    assert result.quote_id == new_id
    assert result.quote_id not in FORBIDDEN_LIVE_QUOTE_IDS


def test_finish_linear_bom_rows_500_is_warning_not_raise(monkeypatch):
    monkeypatch.setenv("SECTURA_WEBSITE_COOKIE", "ASP.NET_SessionId=box")
    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=box"
    client.add_item_linear.side_effect = SecturaFabApiError(
        "API request failed (500) for /Quote/AddItem_Linear",
        status_code=500,
        body="error",
    )
    client.quote_item_read.return_value = {"Data": [], "Total": 0}
    client.get_json.return_value = {"ItemList": []}
    svc = SecturaFabPushService(client=client)
    product = {
        "ID": "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
        "ProductName": "L1/2X1/2X1/8-A36",
        "ProductSubType": "bar",
        "Dim1": 0.5,
        "Dim2": 0.5,
        "Dim3": 0.125,
        "WeightLength": 0.38,
    }
    bind = {
        "productID": product["ID"],
        "productConfigID": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        "productSubType": "bar",
        "dim1": 0.5,
        "dim2": 0.5,
        "dim3": 0.125,
        "dim4": 0,
        "weightLength": 0.38,
        "sku": "L1/2X1/2X1/8-A36",
    }
    with patch.object(
        svc, "_match_linear_product", return_value=(product, "L1/2X1/2X1/8-A36", None)
    ), patch.object(svc, "_linear_catalog_bind", return_value=bind):
        notes = svc.finish_linear_bom_rows(
            quote_id="11111111-aaaa-bbbb-cccc-000000000012",
            linear_rows=[
                {
                    "part_no": "21689-1",
                    "description": "HOSE GUARD",
                    "qty": 1,
                    "cut_length_in": 12.5,
                }
            ],
            material="A36",
            library={},
            extra_pdfs=[],
        )
    blob = " ".join(notes)
    assert "500" in blob or "continuing" in blob
    assert "not aborting weld/nest" in blob
    extra = client.add_item_linear.call_args.kwargs.get("extra") or {}
    assert extra.get("productConfigID") != EMPTY_GUID
    assert extra.get("productSubType")
    assert extra.get("weightLength") not in (None, "")


def test_linear_without_catalog_config_does_not_post(monkeypatch):
    monkeypatch.setenv("SECTURA_WEBSITE_COOKIE", "ASP.NET_SessionId=box")
    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=box"
    client.quote_item_read.return_value = {"Data": [], "Total": 0}
    client.get_json.return_value = {"ItemList": []}
    svc = SecturaFabPushService(client=client)
    product = {"ID": "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee", "ProductName": "C3X4.1-A36"}
    with patch.object(
        svc, "_match_linear_product", return_value=(product, "C3X4.1-A36", None)
    ), patch.object(svc, "_linear_catalog_bind", return_value=None):
        notes = svc.finish_linear_bom_rows(
            quote_id="11111111-aaaa-bbbb-cccc-000000000013",
            linear_rows=[
                {
                    "part_no": "1004740-1",
                    "description": "MASTER CYLINDER MOUNT CHANNEL",
                    "qty": 1,
                    "cut_length_in": 12.5,
                }
            ],
            material="A36",
            library={},
            extra_pdfs=[],
        )
    client.add_item_linear.assert_not_called()
    assert any("productConfigID" in n for n in notes)


def test_forbidden_includes_empty_1004747_draft():
    assert "5e111cd2-73d1-44e1-9602-f2a4a3de2fb4" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "936b5c6c-2fc5-4b28-a8f6-015db289cb4f" in FORBIDDEN_LIVE_QUOTE_IDS
    for qid in (
        "5e111cd2-73d1-44e1-9602-f2a4a3de2fb4",
        "936b5c6c-2fc5-4b28-a8f6-015db289cb4f",
    ):
        with pytest.raises(ForbiddenQuoteError, match="forbidden"):
            refuse_forbidden_quote_write(
                method="POST",
                path="/Quote/AddItem_PDFFiles",
                payload={"ID": qid},
            )


def test_weld_does_not_post_before_cad_or_linear_kids():
    from secturafab.weld_ops import ensure_weld_ops

    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=box"
    client.get_json.return_value = {
        "ItemList": [
            {
                "ID": "asm-1",
                "Description": "1004747-1 - OUTER BOOM WELDMENT",
                "ProductType": 300,
                "IsAssembly": True,
                "Quantity": 1,
                "OperationCostList": [],
            }
        ]
    }
    notes = ensure_weld_ops(
        client,
        "new-qid",
        times={
            "weld_minutes": 154.33,
            "total_inches": 308.66,
            "fitup_with_fixture_minutes": 108.0,
        },
        part_key="1004747-1",
    )
    client.add_operation.assert_not_called()
    assert any("no Cad/Linear kids" in n for n in notes)


def test_no_symbols_skips_weld():
    from secturafab.weld_ops import ensure_weld_ops

    client = MagicMock()
    notes = ensure_weld_ops(client, "qid", times={"weld_minutes": 0, "total_inches": 0})
    assert any("No weld minutes" in n for n in notes)
    client.add_operation.assert_not_called()
