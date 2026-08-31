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
from secturafab.website import SecturaFabWebsiteAuthError, WEBSITE_SESSION_EXPIRED
from secturafab.push import (
    SecturaFabPushService,
    classify_sectura_item,
    _shop_material,
)
from secturafab.qa_harness import evaluate_quote_get
from secturafab.item_desc import resolve_cad_plate_flats
from secturafab.locked_1001898 import locked_cad_spec
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


def _page_pdf_bind_ok(n: int = 1) -> dict:
    return {
        "bound": True,
        "upload_via": "page_add_files",
        "files_kendo": True,
        "grid_pdf_row_count": n,
        "status_gt0_n": n,
        "getpdfdata_n": n,
        "grid_id": "#gridPDF",
    }


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
    assert classify_sectura_item("1010108-1 SLUG") == "Linear"
    assert classify_sectura_item("1010109-1 BAR") == "Linear"
    assert classify_sectura_item("1010104-1 GUSSET") == "Cad"
    assert classify_sectura_item("1010105-1 MOUNT") == "Cad"
    assert classify_sectura_item("15890-1 END CAP, BOOM") == "Cad"
    assert classify_sectura_item("50122-1 1 1/4 NPT PIPE CAP") == "Component"
    assert classify_sectura_item("21689-1 HOSE GUARD") == "Linear"
    assert classify_sectura_item("34136-1 Aluminum Platform Weldment") == "Assembly"
    assert classify_sectura_item("88010 ALUMINUM HINGE Flexible") == "Component"
    assert classify_sectura_item("102196-5 PLATE (HINGE PLATE)") == "Cad"
    assert classify_sectura_item("PLATE-1297_30345-19") == "Cad"
    assert classify_sectura_item("RAIL MOUNT") == "Cad"
    assert classify_sectura_item("TRIANGLE GUSSET") == "Cad"
    assert classify_sectura_item("FLOOR GUSSET") == "Cad"
    assert classify_sectura_item("gate gusset") == "Cad"
    assert classify_sectura_item("CHANNEL PLATE") == "Cad"
    assert classify_sectura_item("ANCHOR PLATE") == "Cad"
    assert classify_sectura_item("SUPPORT PLATE") == "Cad"
    assert classify_sectura_item("KICK CHANNEL") == "Linear"
    assert classify_sectura_item("vertical tube") == "Linear"
    assert classify_sectura_item("main channel") == "Linear"
    assert classify_sectura_item(
        "PLATFORM BASE WELDMENT-2623_103603-1"
    ) == "Assembly"


def test_never_a569_material():
    assert _shop_material("A569") == "A36"
    assert _shop_material("A572") == "A572"
    assert _shop_material("A572 Grade 50") == "A572 Grade 50"
    assert _shop_material("PL025-50K") == "A572 Grade 50"
    assert _shop_material("100K") == "100K"
    assert _shop_material("A1011") == "A1011"
    assert _shop_material("A519") == "A519"
    assert _shop_material("") == "A36"
    assert _shop_material("5052-H32") == "5052-H32"
    assert _shop_material("ALPL009-28K") == "5052-H32"


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
    """Cookie HTTP upload + empty #gridPDF is not success (live 103535-1)."""
    monkeypatch.setenv("SECTURA_WEBSITE_COOKIE", "ASP.NET_SessionId=box")
    pdf = tmp_path / "14501-1.pdf"
    pdf.write_bytes(b"%PDF")
    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=box"
    client.get_item_add_view.return_value = {}
    client.upload_pdf_via_page_add_files.return_value = {
        "bound": False,
        "upload_via": "skipped",
        "grid_pdf_row_count": 0,
        "status_gt0_n": 0,
        "finish_why": "empty_dataSource",
    }
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
    client.upload_item_pdf_attachment.assert_not_called()
    client.add_item_pdf_files.assert_not_called()
    assert client.quote_item_read.called or client.get_json.called
    blob = " ".join(notes)
    assert "GET 0 Cad" in blob or "not bound" in blob
    assert "persisted" not in blob.lower()
    assert "cookie HTTP" in blob
    assert "#gridPDF" in blob


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
    cad_item = {
        "ID": "cad-1",
        "Description": "14501-1 PEDESTAL TOP PLATE",
        "ProductType": 100,
        "Quantity": 1,
        "BadgeString": "PR",
        "UnitCost": 12.5,
        "OperationCostList": [
            {"OperationName": "Profile", "CalculatorName": "Laser"},
            {"OperationName": "Profile", "CalculatorName": "Drafting"},
            {"OperationName": "Profile", "CalculatorName": "Deburr"},
            {"OperationName": "Profile", "CalculatorName": "Laser-Setup"},
            {"OperationName": "Profile", "CalculatorName": "Sheet Loading"},
        ],
    }
    client.get_json.return_value = {
        "QuoteNumber": "1004747-1",
        "ItemCount": 1,
        "ItemList": [cad_item],
    }
    client.quote_item_read.return_value = {"Data": [cad_item], "Total": 1}
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


def test_additem_pdf_uses_takeoff_flats_when_lock_missing(tmp_path, monkeypatch):
    """AddItem_PDFFiles must not skip solely because locked_cad_spec has no PN."""
    monkeypatch.setenv("SECTURA_WEBSITE_COOKIE", "ASP.NET_SessionId=box")
    pn = "1004738-1"
    assert locked_cad_spec(pn) is None
    w, length = resolve_cad_plate_flats(
        pn,
        bom_row={
            "part_no": pn,
            "description": "TOP STIFFENER, OUTER BOOM",
            "width_in": 18.5,
            "length_in": 6.25,
        },
        takeoff={"items": [{"part_no": pn, "blank": [18.5, 6.25]}]},
        locked=locked_cad_spec(pn),
    )
    assert w == 18.5
    assert length == 6.25
    pdf = tmp_path / f"{pn}.pdf"
    pdf.write_bytes(b"%PDF")
    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=box"
    client.get_item_add_view.return_value = {}
    client.upload_pdf_via_page_add_files.return_value = _page_pdf_bind_ok(1)
    client.add_item_pdf_files.return_value = {
        "ok": True,
        "via": "page_fn",
        "finish_fn": "OnAddPDFClick",
        "filelist_from_kendo": True,
        "finish_filelist_n": 1,
    }
    gold_cad = {
        "ID": "cad-1",
        "Description": pn,
        "ProductType": 100,
        "BadgeString": "PR",
        "UnitCost": 12.5,
        "OperationCostList": [
            {"OperationName": "Profile", "CalculatorName": "Laser"},
            {"OperationName": "Profile", "CalculatorName": "Deburr"},
            {"OperationName": "Profile", "CalculatorName": "Laser-Setup"},
            {"OperationName": "Profile", "CalculatorName": "Sheet Loading"},
        ],
    }
    client.quote_item_read.return_value = {"Data": [gold_cad], "Total": 1}
    notes = SecturaFabPushService(client=client).finish_pdf_files(
        quote_id="11111111-aaaa-bbbb-cccc-000000000020",
        pdf_files=[pdf],
        material="A36",
        thickness="0.25",
        qty=1,
        description="TOP STIFFENER, OUTER BOOM",
        bom_rows=[
            {
                "part_no": pn,
                "qty": 1,
                "description": "TOP STIFFENER, OUTER BOOM",
                "width_in": 18.5,
                "length_in": 6.25,
            }
        ],
        takeoff={"items": [{"part_no": pn, "blank": [18.5, 6.25]}]},
    )
    client.upload_item_pdf_attachment.assert_not_called()
    client.upload_pdf_via_page_add_files.assert_called_once()
    client.add_item_pdf_files.assert_called()
    assert client.add_item_pdf_files.call_args.kwargs.get("file_list") == []
    stamp = client.stamp_pdf_kendo_flats.call_args.kwargs["rows"][0]
    assert float(stamp["Width"]) == 18.5
    assert float(stamp["Length"]) == 6.25
    assert float(stamp["Thickness"]) > 0
    assert stamp["ItemType"] == "cad"
    assert "persisted" in " ".join(notes).lower()


def test_finish_pdf_files_302_raises_session_expired(tmp_path, monkeypatch):
    monkeypatch.setenv("SECTURA_WEBSITE_COOKIE", "ASP.NET_SessionId=stale")
    pdf = tmp_path / "1001913.pdf"
    pdf.write_bytes(b"%PDF")
    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=stale"
    client.get_item_add_view.side_effect = SecturaFabWebsiteAuthError(
        f"{WEBSITE_SESSION_EXPIRED} — GetItem_AddView 302"
    )
    with pytest.raises(SecturaFabWebsiteAuthError, match="website session expired"):
        SecturaFabPushService(client=client).finish_pdf_files(
            quote_id="qid",
            pdf_files=[pdf],
            material="A36",
            thickness="0.25",
            qty=1,
            description="PLATE",
        )
    client.add_item_pdf_files.assert_not_called()


def test_forbidden_includes_empty_1004747_draft():
    assert "5e111cd2-73d1-44e1-9602-f2a4a3de2fb4" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "936b5c6c-2fc5-4b28-a8f6-015db289cb4f" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "9354f680-ef91-47d9-af42-8dd65b75473f" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "f61c033a-48f2-4b11-9a10-96bc5c70716c" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "a522d863-1805-4206-85d1-36841dd107d2" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "7a555ac2-2a77-4bd9-a936-bf8a64eb60e7" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "8f87fbae-d2ef-40ee-abd4-47a8755ce19f" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "804172ea-f507-42fe-87ae-1b91d2cc0d29" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "f703b928-3475-45c2-ade5-fcce97e1709e" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "12239b72-c82c-4493-b226-c51a98eb4fb5" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "593d9450-530f-4ade-a137-9d195714ac73" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "b8be3545-1628-4176-b93a-804ad5575bc3" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "0e892c8f-93ee-49fa-90c9-3bb4bbf91c22" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "ed8cfcda-68e4-4655-a240-79cce4280d7e" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "ba7730a0-0848-42d2-8579-dc18f86ec27f" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "30940f1d-d262-4562-bfd3-1b17575dc83c" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "9a2bc798-f192-4e4c-9b12-78098305f7cc" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "aab44741-1213-470c-b941-d44ccf1068ea" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "069da4fe-5818-4125-983a-197bd4188ed1" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "a6ef6891-e080-45de-b57c-1a55fee00c19" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "997f1eb7-3eb0-4a76-83f9-4c3439e929b7" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "66a0271f-f2f7-42c1-ac01-cd879f1bfa22" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "75b3a938-ff89-4525-80d9-c6000d055a48" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "e2cc0a7d-90fa-4629-b48f-db1e8163557b" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "e2305b3c-7316-4a96-8c94-7685fca2be54" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "80eb38af-3721-4049-a0d5-e4026d293a0c" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "31204345-6c91-4122-a859-09f7d7a3ea9f" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "a9497a26-cba8-4ec9-a849-cb8bef81cbcc" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "a8e1b40e-54c2-4515-9f36-67843a1e5286" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "8de920f0-ea17-442d-898e-9a04367d91de" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "d59318c8-9c39-43a2-aef6-cbd28203ee82" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "aab5b3e2-8771-47a2-b625-a3f379c5b0c2" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "6a568912-5b19-4bfd-9e11-d06d7c149746" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "b8a62e76-6439-46d3-b32e-d48de29f389d" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "0d4b8a46-cc66-4586-baed-4cad20a07ddb" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "5b622a0d-4dab-4099-97e4-d0184df4b770" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "491f6387-520f-4eee-aab3-6d20585ee740" in FORBIDDEN_LIVE_QUOTE_IDS
    from secturafab.forbidden_quotes import (
        FORBIDDEN_LIVE_QUOTE_NUMBERS,
        is_forbidden_quote_id,
    )

    assert "34887-1" in FORBIDDEN_LIVE_QUOTE_NUMBERS
    assert "34639-1" in FORBIDDEN_LIVE_QUOTE_NUMBERS
    assert "11791-2" in FORBIDDEN_LIVE_QUOTE_NUMBERS
    assert "10072-1" in FORBIDDEN_LIVE_QUOTE_NUMBERS
    assert "34137-1" in FORBIDDEN_LIVE_QUOTE_NUMBERS
    assert "34137-2" in FORBIDDEN_LIVE_QUOTE_NUMBERS
    assert "34632-2" in FORBIDDEN_LIVE_QUOTE_NUMBERS
    assert "106386-1" in FORBIDDEN_LIVE_QUOTE_NUMBERS
    assert "106687-1" in FORBIDDEN_LIVE_QUOTE_NUMBERS
    assert "106384-1" in FORBIDDEN_LIVE_QUOTE_NUMBERS
    assert "105918-1" in FORBIDDEN_LIVE_QUOTE_NUMBERS
    assert "28110-2" in FORBIDDEN_LIVE_QUOTE_NUMBERS
    assert "107877-1" in FORBIDDEN_LIVE_QUOTE_NUMBERS
    assert "1020249-1" in FORBIDDEN_LIVE_QUOTE_NUMBERS
    assert "5003313-001" in FORBIDDEN_LIVE_QUOTE_NUMBERS
    assert "P001545" in FORBIDDEN_LIVE_QUOTE_NUMBERS
    assert "BB2000-ASM" in FORBIDDEN_LIVE_QUOTE_NUMBERS
    assert "EHB3112" in FORBIDDEN_LIVE_QUOTE_NUMBERS
    assert "EHB3112-1" in FORBIDDEN_LIVE_QUOTE_NUMBERS
    assert "11796-1" in FORBIDDEN_LIVE_QUOTE_NUMBERS
    assert "11796-2" in FORBIDDEN_LIVE_QUOTE_NUMBERS
    assert "107292-1" in FORBIDDEN_LIVE_QUOTE_NUMBERS
    assert "16629-1" in FORBIDDEN_LIVE_QUOTE_NUMBERS
    assert "10098-1" in FORBIDDEN_LIVE_QUOTE_NUMBERS
    assert "SC0600" in FORBIDDEN_LIVE_QUOTE_NUMBERS
    assert "FA Assembly" in FORBIDDEN_LIVE_QUOTE_NUMBERS
    assert "Skin Assembly" in FORBIDDEN_LIVE_QUOTE_NUMBERS
    assert "1001898-5" in FORBIDDEN_LIVE_QUOTE_NUMBERS
    assert "1001898-1" in FORBIDDEN_LIVE_QUOTE_NUMBERS
    assert "103535-1" in FORBIDDEN_LIVE_QUOTE_NUMBERS
    assert "Q10095" in FORBIDDEN_LIVE_QUOTE_NUMBERS
    assert "34137-4" in FORBIDDEN_LIVE_QUOTE_NUMBERS
    assert "1007922-3" in FORBIDDEN_LIVE_QUOTE_NUMBERS
    assert "29743-1" in FORBIDDEN_LIVE_QUOTE_NUMBERS
    assert "1002323-1" in FORBIDDEN_LIVE_QUOTE_NUMBERS
    assert "33819-1" in FORBIDDEN_LIVE_QUOTE_NUMBERS
    assert "21678-1" in FORBIDDEN_LIVE_QUOTE_NUMBERS
    assert "Q10056" in FORBIDDEN_LIVE_QUOTE_NUMBERS
    assert "491f6387-520f-4eee-aab3-6d20585ee740" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "bd5c2e3e-948d-463d-8844-4366910bb5ec" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "d2f7b031-a5a8-4020-a6a3-dba8de964ebf" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "b2e12461-442b-436e-9445-772e992644f6" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "47c393f8-db59-4b9a-a243-48d572011f77" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "a7d6ca50-efec-409d-bd32-e68012e710c3" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "8bcc226b-6bd9-4149-a7bb-aa830ce63a5d" in FORBIDDEN_LIVE_QUOTE_IDS
    assert "a7dc46bf-836a-4250-b038-9331cc0595a7" in FORBIDDEN_LIVE_QUOTE_IDS
    assert is_forbidden_quote_id("bd5c2e3e-948d-463d-8844-4366910bb5ec")
    assert is_forbidden_quote_id("bd5c2e3e-1111-2222-3333-444444444444")
    assert is_forbidden_quote_id("d2f7b031-1111-2222-3333-444444444444")
    assert is_forbidden_quote_id("b2e12461-442b-436e-9445-772e992644f6")
    assert is_forbidden_quote_id("b2e12461-1111-2222-3333-444444444444")
    assert is_forbidden_quote_id("47c393f8-db59-4b9a-a243-48d572011f77")
    assert is_forbidden_quote_id("47c393f8-1111-2222-3333-444444444444")
    assert is_forbidden_quote_id("425587a7-1111-2222-3333-444444444444")
    assert is_forbidden_quote_id("95b8c186-1111-2222-3333-444444444444")
    assert is_forbidden_quote_id("491f6387-520f-4eee-aab3-6d20585ee740")
    assert is_forbidden_quote_id("491f6387-1111-2222-3333-444444444444")
    assert is_forbidden_quote_id("280f4dcb-1111-2222-3333-444444444444")
    assert is_forbidden_quote_id("75b3a938-1111-2222-3333-444444444444")
    assert is_forbidden_quote_id("e2cc0a7d-1111-2222-3333-444444444444")
    assert is_forbidden_quote_id("e2305b3c-1111-2222-3333-444444444444")
    assert is_forbidden_quote_id("80eb38af-1111-2222-3333-444444444444")
    assert is_forbidden_quote_id("31204345-1111-2222-3333-444444444444")
    assert is_forbidden_quote_id("a9497a26-1111-2222-3333-444444444444")
    assert is_forbidden_quote_id("cf8ec36e-1111-2222-3333-444444444444")
    assert is_forbidden_quote_id("a8e1b40e-1111-2222-3333-444444444444")
    assert is_forbidden_quote_id("8de920f0-1111-2222-3333-444444444444")
    assert is_forbidden_quote_id("d59318c8-1111-2222-3333-444444444444")
    assert is_forbidden_quote_id("aab5b3e2-1111-2222-3333-444444444444")
    assert is_forbidden_quote_id("6a568912-1111-2222-3333-444444444444")
    assert is_forbidden_quote_id("b8a62e76-1111-2222-3333-444444444444")
    assert is_forbidden_quote_id("0d4b8a46-1111-2222-3333-444444444444")
    assert is_forbidden_quote_id("5b622a0d-1111-2222-3333-444444444444")
    assert is_forbidden_quote_id("a484ba3b-1111-2222-3333-444444444444")
    assert is_forbidden_quote_id("66a0271f-1111-2222-3333-444444444444")
    for qid in (
        "5e111cd2-73d1-44e1-9602-f2a4a3de2fb4",
        "936b5c6c-2fc5-4b28-a8f6-015db289cb4f",
        "9354f680-ef91-47d9-af42-8dd65b75473f",
        "f61c033a-48f2-4b11-9a10-96bc5c70716c",
        "a522d863-1805-4206-85d1-36841dd107d2",
        "7a555ac2-2a77-4bd9-a936-bf8a64eb60e7",
        "8f87fbae-d2ef-40ee-abd4-47a8755ce19f",
        "804172ea-f507-42fe-87ae-1b91d2cc0d29",
        "f703b928-3475-45c2-ade5-fcce97e1709e",
        "12239b72-c82c-4493-b226-c51a98eb4fb5",
        "593d9450-530f-4ade-a137-9d195714ac73",
        "b8be3545-1628-4176-b93a-804ad5575bc3",
        "0e892c8f-93ee-49fa-90c9-3bb4bbf91c22",
        "ed8cfcda-68e4-4655-a240-79cce4280d7e",
        "ba7730a0-0848-42d2-8579-dc18f86ec27f",
        "30940f1d-d262-4562-bfd3-1b17575dc83c",
        "9a2bc798-f192-4e4c-9b12-78098305f7cc",
        "aab44741-1213-470c-b941-d44ccf1068ea",
        "069da4fe-5818-4125-983a-197bd4188ed1",
        "a6ef6891-e080-45de-b57c-1a55fee00c19",
        "997f1eb7-3eb0-4a76-83f9-4c3439e929b7",
        "66a0271f-f2f7-42c1-ac01-cd879f1bfa22",
        "75b3a938-ff89-4525-80d9-c6000d055a48",
        "e2cc0a7d-90fa-4629-b48f-db1e8163557b",
        "e2305b3c-7316-4a96-8c94-7685fca2be54",
        "80eb38af-3721-4049-a0d5-e4026d293a0c",
        "31204345-6c91-4122-a859-09f7d7a3ea9f",
        "a9497a26-cba8-4ec9-a849-cb8bef81cbcc",
        "0d4b8a46-cc66-4586-baed-4cad20a07ddb",
        "5b622a0d-4dab-4099-97e4-d0184df4b770",
        "491f6387-520f-4eee-aab3-6d20585ee740",
        "bd5c2e3e-948d-463d-8844-4366910bb5ec",
        "a7dc46bf-836a-4250-b038-9331cc0595a7",
        "a7d6ca50-efec-409d-bd32-e68012e710c3",
        "8bcc226b-6bd9-4149-a7bb-aa830ce63a5d",
        "d2f7b031-a5a8-4020-a6a3-dba8de964ebf",
        "b2e12461-442b-436e-9445-772e992644f6",
        "47c393f8-db59-4b9a-a243-48d572011f77",
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


def test_website_cad_persist_skips_addplate_and_update_when_get_has_pack():
    """(a) website Cad must not addplate/update after GET already has PR+pack+UnitCost."""
    from secturafab.line_item_ops import persist_classified_item_fields

    stamped = {
        "ItemList": [
            {
                "ID": "c1",
                "Description": "1004738-1 - 1/4 A36 2 in x 9 in",
                "ProductType": 100,
                "Category": "Cad",
                "BadgeString": "PR",
                "UnitCost": 12.5,
                "Material": "A36",
                "Thickness": 0.25,
                "OperationCostList": [
                    {"OperationName": "Profile", "CalculatorName": "Laser"},
                    {"OperationName": "Profile", "CalculatorName": "Drafting"},
                    {"OperationName": "Profile", "CalculatorName": "Deburr"},
                    {"OperationName": "Profile", "CalculatorName": "Laser-Setup"},
                    {"OperationName": "Profile", "CalculatorName": "Sheet Loading"},
                ],
            }
        ]
    }
    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=box"
    client.get_json.return_value = stamped
    persist_classified_item_fields(
        client,
        "qid",
        bom_rows=[{"part_no": "1004738-1", "description": "TOP STIFFENER", "qty": 1}],
        persist_cad=True,
        persist_linear=False,
        plate_catalog=[{"ID": "pl", "ProductName": "PL1/4-A36", "Thickness": 0.25, "MaterialGrade": "A36", "Active": True}],
    )
    paths = [c.args[1] for c in client.request.call_args_list if len(c.args) > 1]
    assert not any("addplate" in str(p) for p in paths), paths
    assert not any("quoteOnline/update" in str(p) for p in paths), paths


def test_website_cad_persist_skips_addplate_even_without_pack():
    """addplate/update after Image Files wipes calculators — never call on website Cad."""
    from secturafab.line_item_ops import persist_classified_item_fields

    empty_pack = {
        "ItemList": [
            {
                "ID": "c1",
                "Description": "1004738-1 - 1/4 A36 2 in x 9 in",
                "ProductType": 100,
                "Category": "Cad",
                "BadgeString": "",
                "UnitCost": 0,
                "Material": "A36",
                "Thickness": 0.25,
                "OperationCostList": [],
            }
        ]
    }
    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=box"
    client.get_json.return_value = empty_pack
    persist_classified_item_fields(
        client,
        "qid",
        bom_rows=[{"part_no": "1004738-1", "description": "TOP STIFFENER", "qty": 1}],
        persist_cad=True,
        persist_linear=False,
        plate_catalog=[{"ID": "pl", "ProductName": "PL1/4-A36", "Thickness": 0.25, "MaterialGrade": "A36", "Active": True}],
    )
    paths = [c.args[1] for c in client.request.call_args_list if len(c.args) > 1]
    assert not any("addplate" in str(p) for p in paths), paths
    assert not any("quoteOnline/update" in str(p) for p in paths), paths


def test_takeoff_supplies_remaining_1004747_cad_flats():
    """Takeoff plates must resolve L×W for LOM Cad PNs that lock does not list."""
    remaining = [
        ("6993-1", "6993", [6.0, 2.0]),
        ("1004806-1", "1004806-1", [12.0, 8.0]),
        ("1004711-1", "1004711-1", [10.0, 4.0]),
        ("1004741-1", "1004741-1", [14.0, 8.0]),
        ("1004744-1", "1004744", [18.0, 3.0]),
    ]
    takeoff = {
        "plates": [
            {"part_no": src, "blank": blank, "width_in": blank[1], "length_in": blank[0]}
            for _pn, src, blank in remaining
        ]
    }
    for pn, _src, blank in remaining:
        assert locked_cad_spec(pn) is None
        w, length = resolve_cad_plate_flats(pn, takeoff=takeoff, locked=None)
        assert w and length, pn
        assert {w, length} == {blank[0], blank[1]}


def test_parse_plate_flats_reads_inch_and_overall():
    from secturafab.item_desc import parse_plate_flats

    assert parse_plate_flats('2" X 9"') == (2.0, 9.0)
    assert parse_plate_flats("OVERALL 18.5 X 6.25") == (18.5, 6.25)
    assert parse_plate_flats("1/4 X 2 X 9") == (2.0, 9.0)
    assert parse_plate_flats("2-1/2 X 9") == (2.5, 9.0)


def test_additem_pdf_302_fails_push_ok_false(tmp_path, monkeypatch):
    """302 Finish must not report push.ok or leave an empty shell as complete."""
    from secturafab.website import SecturaFabWebsiteAuthError, WEBSITE_SESSION_EXPIRED

    monkeypatch.setenv("SECTURA_WEBSITE_COOKIE", "ASP.NET_SessionId=stale")
    pdf = tmp_path / "1001775-1.pdf"
    pdf.write_bytes(b"%PDF")
    lib = tmp_path / "lib"
    lib.mkdir()
    child = lib / "1001913.pdf"
    child.write_bytes(b"%PDF")
    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=stale"
    client.get_json.return_value = {
        "QuoteNumber": "1001775-1",
        "ItemCount": 1,
        "ItemList": [
            {
                "ID": "asm-1",
                "Description": "1001775-1",
                "ProductType": 300,
                "IsAssembly": True,
                "UnitCost": 0,
            }
        ],
    }
    client.quote_item_read.return_value = {"Data": [], "Total": 0}
    service = SecturaFabPushService(client=client)
    new_id = "11111111-aaaa-bbbb-cccc-000000000177"
    with patch.object(service, "upload_drawings_quote_request", return_value="qr"), patch.object(
        service, "create_quote", return_value=new_id
    ), patch.object(
        service, "allocate_quote_number", return_value="1001775-1"
    ), patch.object(
        service,
        "finish_pdf_files",
        side_effect=SecturaFabWebsiteAuthError(
            f"{WEBSITE_SESSION_EXPIRED} — AddItem_PDFFiles 302"
        ),
    ), patch.object(
        service, "finish_website_weldment"
    ) as weldment, patch.object(
        service, "quick_add_cad"
    ) as qadd, patch(
        "secturafab.push.refresh_bom_rows_for_push",
        return_value=(
            [
                {
                    "part_no": "1001913-1",
                    "qty": 1,
                    "description": "PLATE",
                    "width_in": 6.0,
                    "length_in": 4.0,
                }
            ],
            [],
        ),
    ), patch(
        "secturafab.push.extract_assembly_description", return_value="WELDMENT"
    ), patch(
        "secturafab.push.apply_quote_organization", return_value=[]
    ), patch(
        "secturafab.push.ensure_imperial_item_units", return_value=[]
    ), patch(
        "secturafab.push.apply_bom_quantities", return_value=[]
    ), patch(
        "secturafab.push.ensure_weld_ops"
    ) as weld:
        result = service.push_job(
            title="1001775-1",
            pdf_filename="1001775-1.pdf",
            pdf_path=pdf,
            stp_path=None,
            takeoff={
                "library": {
                    "part_key": "1001775-1",
                    "folder": str(lib),
                    "related_pdfs": ["1001913.pdf"],
                },
                "plates": [
                    {
                        "part_no": "1001913-1",
                        "width_in": 6.0,
                        "length_in": 4.0,
                    }
                ],
            },
            times={"weld_minutes": 0, "total_inches": 0},
            job_id=1775,
        )
    assert result.ok is False
    assert result.ready is False
    assert result.status == "failed"
    assert WEBSITE_SESSION_EXPIRED in (result.error or "") or WEBSITE_SESSION_EXPIRED in " ".join(
        result.notes or []
    )
    weldment.assert_not_called()
    weld.assert_not_called()
    qadd.assert_not_called()


def test_filelist_missing_dims_is_not_counted_as_posted(tmp_path, monkeypatch):
    monkeypatch.setenv("SECTURA_WEBSITE_COOKIE", "ASP.NET_SessionId=box")
    pdf = tmp_path / "1001947.pdf"
    pdf.write_bytes(b"%PDF")
    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=box"
    client.get_item_add_view.return_value = {}
    client.upload_pdf_via_page_add_files.return_value = _page_pdf_bind_ok(1)
    client.add_item_pdf_files.return_value = {
        "ok": False,
        "via": "skipped",
        "filelist_from_kendo": False,
        "finish_why": "empty_dataSource",
    }
    client.quote_item_read.return_value = {"Data": [], "Total": 0}
    client.get_json.return_value = {"ItemList": []}
    notes = SecturaFabPushService(client=client).finish_pdf_files(
        quote_id="11111111-aaaa-bbbb-cccc-000000000194",
        pdf_files=[pdf],
        material="A36",
        thickness="0.25",
        qty=1,
        description="PLATE",
            bom_rows=[{"part_no": "1001947-1", "qty": 1, "description": "1/8 5052-H32 SHEET"}],
        takeoff={},
    )
    client.upload_item_pdf_attachment.assert_not_called()
    blob = " ".join(notes)
    assert "not inventing reconstructed FileList" in blob
    assert "0 ProductType 100" in blob or "GET 0 Cad" in blob
    assert "persisted" not in blob.lower()


def test_filelist_uses_lom_flats_and_5052_not_a36(tmp_path, monkeypatch):
    monkeypatch.setenv("SECTURA_WEBSITE_COOKIE", "ASP.NET_SessionId=box")
    pdf = tmp_path / "1001913.pdf"
    pdf.write_bytes(b"%PDF")
    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=box"
    client.get_item_add_view.return_value = {}
    client.upload_pdf_via_page_add_files.return_value = _page_pdf_bind_ok(1)
    client.add_item_pdf_files.return_value = {
        "ok": True,
        "via": "page_fn",
        "finish_fn": "OnAddPDFClick",
        "filelist_from_kendo": True,
        "finish_filelist_n": 1,
    }
    gold_cad = {
        "ID": "cad-1",
        "Description": "1001913-1",
        "ProductType": 100,
        "BadgeString": "PR",
        "UnitCost": 12.5,
        "OperationCostList": [
            {"OperationName": "Profile", "CalculatorName": "Laser"},
            {"OperationName": "Profile", "CalculatorName": "Deburr"},
            {"OperationName": "Profile", "CalculatorName": "Laser-Setup"},
            {"OperationName": "Profile", "CalculatorName": "Sheet Loading"},
        ],
    }
    client.quote_item_read.return_value = {"Data": [gold_cad], "Total": 1}
    notes = SecturaFabPushService(client=client).finish_pdf_files(
        quote_id="11111111-aaaa-bbbb-cccc-000000000191",
        pdf_files=[pdf],
        material="A36",
        thickness="0.25",
        qty=1,
        description="PLATE",
        bom_rows=[
            {
                "part_no": "1001913-1",
                "qty": 2,
                    "description": "1/8 5052-H32 SHEET",
            }
        ],
        takeoff={
            "plates": [
                {
                    "part_no": "1001913-1",
                    "width_in": 8.0,
                    "length_in": 12.0,
                    "blank": [12.0, 8.0],
                }
            ]
        },
        library={},
        extra_pdfs=[],
    )
    client.upload_item_pdf_attachment.assert_not_called()
    client.add_item_pdf_files.assert_called()
    assert client.add_item_pdf_files.call_args.kwargs.get("file_list") == []
    posted = client.stamp_pdf_kendo_flats.call_args.kwargs["rows"][0]
    assert posted["ItemType"] == "cad"
    assert posted["Machine"] == "Laser - Bay1"
    assert float(posted["Width"]) == 8.0
    assert float(posted["Length"]) == 12.0
    assert float(posted["Status"]) > 0
    assert posted["Material"] != "A36"
    assert "5052" in str(posted["Material"])
    assert "persisted" in " ".join(notes).lower()


def test_empty_shell_item_count_1_is_not_success(tmp_path, monkeypatch):
    monkeypatch.setenv("SECTURA_WEBSITE_COOKIE", "ASP.NET_SessionId=box")
    pdf = tmp_path / "1001775-1.pdf"
    pdf.write_bytes(b"%PDF")
    lib = tmp_path / "lib"
    lib.mkdir()
    (lib / "1001913.pdf").write_bytes(b"%PDF")
    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=box"
    shell = {
        "QuoteNumber": "1001775-1",
        "ItemCount": 1,
        "ItemList": [
            {
                "ID": "asm-1",
                "Description": "WELDMENT",
                "ProductType": 300,
                "IsAssembly": True,
                "UnitCost": 0,
            }
        ],
    }
    client.get_json.return_value = shell
    client.quote_item_read.return_value = {"Data": shell["ItemList"], "Total": 1}
    service = SecturaFabPushService(client=client)
    with patch.object(service, "upload_drawings_quote_request", return_value="qr"), patch.object(
        service, "create_quote", return_value="11111111-aaaa-bbbb-cccc-000000000178"
    ), patch.object(
        service, "allocate_quote_number", return_value="1001775-1"
    ), patch.object(
        service, "finish_pdf_files", return_value=["WARNING: AddItem_PDFFiles skipped"]
    ), patch.object(
        service, "finish_website_weldment"
    ) as weldment, patch(
        "secturafab.push.refresh_bom_rows_for_push",
        return_value=(
            [{"part_no": "1001913-1", "qty": 1, "description": "PLATE"}],
            [],
        ),
    ), patch(
        "secturafab.push.extract_assembly_description", return_value="WELDMENT"
    ), patch(
        "secturafab.push.apply_quote_organization", return_value=[]
    ):
        result = service.push_job(
            title="1001775-1",
            pdf_filename="1001775-1.pdf",
            pdf_path=pdf,
            stp_path=None,
            takeoff={
                "library": {
                    "part_key": "1001775-1",
                    "folder": str(lib),
                    "related_pdfs": ["1001913.pdf"],
                }
            },
            times={},
            job_id=1776,
        )
    assert result.ok is False
    assert result.ready is False
    assert result.status == "failed"
    assert "0 Cad" in (result.error or "") or "empty assembly" in (result.error or "").lower()
    weldment.assert_not_called()


def test_page_outline_1xn_is_not_a_cad_flat():
    from secturafab.item_desc import (
        looks_like_page_outline,
        parse_plate_flats,
        resolve_cad_plate_flats,
    )

    assert looks_like_page_outline(1.0, 2.0) is True
    assert looks_like_page_outline(1.0, 16.0) is True
    assert looks_like_page_outline(5.25, 5.75) is False
    assert looks_like_page_outline(14.625, 7.375) is False
    assert looks_like_page_outline(2.0, 9.0) is False
    drawing = "SCALE 1 X 2  TITLE 1 x 16  OVERALL 5.25 X 5.75"
    assert parse_plate_flats(drawing) == (5.25, 5.75)
    assert parse_plate_flats("1 x 2") == (None, None)
    assert parse_plate_flats("1 x 16") == (None, None)
    w, length = resolve_cad_plate_flats(
        "1007013-1",
        takeoff={
            "plates": [
                {
                    "part_no": "1007013-1",
                    "width_in": 1.0,
                    "length_in": 2.0,
                    "description": "OVERALL 5.25 X 5.75 A572",
                }
            ]
        },
        noun="1 x 2 OVERALL 5.25 x 5.75",
        locked=None,
    )
    assert {w, length} == {5.25, 5.75}


def test_filelist_built_for_every_cad_with_lom_flats(tmp_path, monkeypatch):
    """Every LOM Cad kid with takeoff flats gets a full Image Files FileList."""
    monkeypatch.setenv("SECTURA_WEBSITE_COOKIE", "ASP.NET_SessionId=box")
    kids = [
        ("1007012.pdf", "1007012-1", 7.375, 14.625),
        ("1007013.pdf", "1007013-1", 5.25, 5.75),
        ("1007014.pdf", "1007014-1", 6.0, 8.0),
        ("1007015.pdf", "1007015-1", 4.0, 10.0),
    ]
    pdfs = []
    for name, _pn, _w, _l in kids:
        p = tmp_path / name
        p.write_bytes(b"%PDF")
        pdfs.append(p)
    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=box"
    client.get_item_add_view.return_value = {}
    client.upload_pdf_via_page_add_files.return_value = _page_pdf_bind_ok(4)
    client.add_item_pdf_files.return_value = {
        "ok": True,
        "via": "page_fn",
        "finish_fn": "OnAddPDFClick",
        "filelist_from_kendo": True,
        "finish_filelist_n": 4,
    }
    gold_rows = [
        {
            "ID": f"cad-{pn}",
            "Description": pn,
            "ProductType": 100,
            "BadgeString": "PR",
            "UnitCost": 12.5,
            "OperationCostList": [
                {"OperationName": "Profile", "CalculatorName": "Laser"},
                {"OperationName": "Profile", "CalculatorName": "Deburr"},
                {"OperationName": "Profile", "CalculatorName": "Laser-Setup"},
                {"OperationName": "Profile", "CalculatorName": "Sheet Loading"},
            ],
        }
        for _n, pn, _w, _l in kids
    ]
    client.quote_item_read.return_value = {"Data": gold_rows, "Total": 4}
    notes = SecturaFabPushService(client=client).finish_pdf_files(
        quote_id="11111111-aaaa-bbbb-cccc-000000000704",
        pdf_files=pdfs,
        material="A36",
        thickness="0.25",
        qty=1,
        description="PLATE",
        bom_rows=[
            {
                "part_no": pn,
                "qty": 1,
                "description": "PL025-50K A572 Grade 50 PLATE",
            }
            for _n, pn, _w, _l in kids
        ],
        takeoff={
            "plates": [
                {
                    "part_no": pn,
                    "width_in": w,
                    "length_in": length,
                    "blank": [length, w],
                    "description": "A572 Grade 50",
                }
                for _n, pn, w, length in kids
            ]
        },
    )
    client.upload_item_pdf_attachment.assert_not_called()
    client.upload_pdf_via_page_add_files.assert_called_once()
    assert client.add_item_pdf_files.call_count == 1
    assert client.add_item_pdf_files.call_args.kwargs.get("file_list") == []
    posted_names = []
    for row in client.stamp_pdf_kendo_flats.call_args.kwargs["rows"]:
        posted_names.append(row.get("FileName"))
        assert row["ItemType"] == "cad"
        assert row["Machine"] == "Laser - Bay1"
        assert float(row["Status"]) > 0
        assert float(row["Thickness"]) > 0
        assert float(row["Width"]) > 1.1
        assert float(row["Length"]) > 1.1
        assert {float(row["Width"]), float(row["Length"])} != {1.0, 2.0}
        assert {float(row["Width"]), float(row["Length"])} != {1.0, 16.0}
        assert "A572" in str(row["Material"])
        assert row["Material"] != "A36"
    assert "1007014.pdf" in posted_names
    assert "1007015.pdf" in posted_names
    blob = " ".join(notes)
    assert "FileList missing" not in blob
    assert "AddItem_PDFFiles skipped" not in blob


def test_filelist_rejects_page_outline_dims_for_1007013(tmp_path, monkeypatch):
    monkeypatch.setenv("SECTURA_WEBSITE_COOKIE", "ASP.NET_SessionId=box")
    pdf = tmp_path / "1007013.pdf"
    pdf.write_bytes(b"%PDF")
    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=box"
    client.get_item_add_view.return_value = {}
    client.upload_pdf_via_page_add_files.return_value = _page_pdf_bind_ok(1)
    client.add_item_pdf_files.return_value = {
        "ok": True,
        "via": "page_fn",
        "finish_fn": "OnAddPDFClick",
        "filelist_from_kendo": True,
        "finish_filelist_n": 1,
    }
    client.quote_item_read.return_value = {
        "Data": [
            {
                "ProductType": 100,
                "Description": "1007013-1",
                "BadgeString": "PR",
                "UnitCost": 12.5,
                "OperationCostList": [
                    {"OperationName": "Profile", "CalculatorName": "Laser"},
                    {"OperationName": "Profile", "CalculatorName": "Deburr"},
                    {"OperationName": "Profile", "CalculatorName": "Laser-Setup"},
                    {"OperationName": "Profile", "CalculatorName": "Sheet Loading"},
                ],
            }
        ],
        "Total": 1,
    }
    SecturaFabPushService(client=client).finish_pdf_files(
        quote_id="11111111-aaaa-bbbb-cccc-000000000713",
        pdf_files=[pdf],
        material="A36",
        thickness="0.25",
        qty=1,
        description="PLATE",
        bom_rows=[
            {
                "part_no": "1007013-1",
                "qty": 1,
                "description": "1 x 2 OVERALL 5.25 x 5.75 A572 PLATE",
            }
        ],
        takeoff={
            "plates": [
                {
                    "part_no": "1007013-1",
                    "width_in": 1.0,
                    "length_in": 2.0,
                    "description": "OVERALL 5.25 X 5.75",
                }
            ]
        },
    )
    client.upload_item_pdf_attachment.assert_not_called()
    client.add_item_pdf_files.assert_called()
    assert client.add_item_pdf_files.call_args.kwargs.get("file_list") == []
    row = client.stamp_pdf_kendo_flats.call_args.kwargs["rows"][0]
    assert {float(row["Width"]), float(row["Length"])} == {5.25, 5.75}


def test_gold_miss_after_200_finish_is_not_session_expired(tmp_path, monkeypatch):
    """HTTP 200 AddItem_PDFFiles without PR/pack/UnitCost is fail, not session expired."""
    monkeypatch.setenv("SECTURA_WEBSITE_COOKIE", "ASP.NET_SessionId=box")
    pdf = tmp_path / "1007049-1.pdf"
    pdf.write_bytes(b"%PDF")
    lib = tmp_path / "lib"
    lib.mkdir()
    (lib / "1007013.pdf").write_bytes(b"%PDF")
    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=box"
    no_gold = {
        "QuoteNumber": "1007049-1",
        "ItemCount": 3,
        "ItemList": [
            {
                "ID": "asm-1",
                "Description": "WELDMENT",
                "ProductType": 300,
                "IsAssembly": True,
                "UnitCost": 0,
            },
            {
                "ID": "cad-1",
                "Description": "1007013-1",
                "ProductType": 100,
                "Category": "Cad",
                "BadgeString": "",
                "UnitCost": 0,
                "Machine": "Laser - Bay1",
                "OperationCostList": [],
            },
            {
                "ID": "cad-2",
                "Description": "1007012-1",
                "ProductType": 100,
                "Category": "Cad",
                "BadgeString": "",
                "UnitCost": 0,
                "Machine": "Laser - Bay1",
                "OperationCostList": [],
            },
        ],
    }
    client.get_json.return_value = no_gold
    client.quote_item_read.return_value = {"Data": no_gold["ItemList"], "Total": 3}
    service = SecturaFabPushService(client=client)
    with patch.object(service, "upload_drawings_quote_request", return_value="qr"), patch.object(
        service, "create_quote", return_value="11111111-aaaa-bbbb-cccc-000000000704"
    ), patch.object(
        service, "allocate_quote_number", return_value="1007049-1"
    ), patch.object(
        service,
        "finish_pdf_files",
        return_value=["Uploaded Image Files 200", "AddItem_PDFFiles HTTP 200"],
    ), patch.object(
        service, "finish_website_weldment"
    ) as weldment, patch(
        "secturafab.push.refresh_bom_rows_for_push",
        return_value=(
            [
                {
                    "part_no": "1007013-1",
                    "qty": 1,
                    "description": "PLATE",
                    "width_in": 5.25,
                    "length_in": 5.75,
                }
            ],
            [],
        ),
    ), patch(
        "secturafab.push.extract_assembly_description", return_value="WELDMENT"
    ), patch(
        "secturafab.push.apply_quote_organization", return_value=[]
    ), patch(
        "secturafab.push.ensure_imperial_item_units", return_value=[]
    ), patch(
        "secturafab.push.apply_bom_quantities", return_value=[]
    ), patch(
        "secturafab.push.ensure_weld_ops", return_value=[]
    ):
        result = service.push_job(
            title="1007049-1",
            pdf_filename="1007049-1.pdf",
            pdf_path=pdf,
            stp_path=None,
            takeoff={
                "library": {
                    "part_key": "1007049-1",
                    "folder": str(lib),
                    "related_pdfs": ["1007013.pdf"],
                },
                "plates": [
                    {
                        "part_no": "1007013-1",
                        "width_in": 5.25,
                        "length_in": 5.75,
                        "description": "A572 Grade 50",
                    }
                ],
            },
            times={"weld_minutes": 10, "total_inches": 40.0},
            job_id=7049,
        )
    assert result.ok is False
    assert result.ready is False
    blob = f"{result.error or ''} {' '.join(result.notes or [])}"
    assert "gold" in blob.lower() or "UnitCost" in blob or "pack" in blob.lower()
    assert WEBSITE_SESSION_EXPIRED not in blob
    weldment.assert_not_called()


def test_ensure_weld_ops_empty_200_counts_as_posted():
    from secturafab.weld_ops import ensure_weld_ops

    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=box"
    client.get_json.return_value = {
        "ItemList": [
            {
                "ID": "asm-1",
                "Description": "1007049-1 - WELDMENT",
                "ProductType": 300,
                "IsAssembly": True,
                "Quantity": 1,
                "OperationCostList": [],
            },
            {
                "ID": "cad-1",
                "Description": "1007013-1",
                "ProductType": 100,
                "Quantity": 1,
                "OperationCostList": [],
            },
        ]
    }
    client.add_operation.return_value = None
    notes = ensure_weld_ops(
        client,
        "new-qid",
        times={"weld_minutes": 20.0, "total_inches": 40.0},
        part_key="1007049-1",
    )
    client.add_operation.assert_called_once()
    assert client.add_operation.call_args.kwargs["weld_inches"] == pytest.approx(40.0)
    blob = " ".join(notes)
    assert "AddOperation" in blob
    assert "returned empty" not in blob
    assert "graft" not in blob.lower() or "not grafting" in blob
    client.request.assert_not_called()


def test_1001898_5_cad_unitcost_empty_ocl_no_pr_is_dod_fail(tmp_path, monkeypatch):
    """3 Cad + unitcost + empty OCL + no PR is FAIL. Linear saw PASS is not DoD."""
    from secturafab.line_item_ops import (
        cad_image_files_stamped,
        cad_kids_unitcost_without_pr,
        finish_produced_gold,
        image_files_dod_pass,
        item_has_pr_tag,
        item_has_saw_pack,
    )
    from tests.fixtures.live_1001898_5 import (
        SPENT_QUOTE_ID,
        live_1001898_5_quote,
    )

    quote = live_1001898_5_quote()
    assert cad_kids_unitcost_without_pr(quote) is True
    assert finish_produced_gold(quote, expect_cad=True, expect_linear=True) is False
    assert image_files_dod_pass(quote, expect_cad=True, expect_linear=True) is False
    cad = [it for it in quote["ItemList"] if it.get("ProductType") == 100]
    assert len(cad) == 3
    assert all(float(it["UnitCost"]) > 0 for it in cad)
    assert all(not it.get("OperationCostList") for it in cad)
    assert all(not item_has_pr_tag(it) for it in cad)
    assert all(not cad_image_files_stamped(it) for it in cad)
    linear = [it for it in quote["ItemList"] if it.get("IsLinear")]
    assert len(linear) == 2
    assert all(item_has_saw_pack(it) for it in linear)
    assert image_files_dod_pass(quote, expect_cad=False, expect_linear=True) is True

    monkeypatch.setenv("SECTURA_WEBSITE_COOKIE", "ASP.NET_SessionId=box")
    pdf = tmp_path / "14501-1.pdf"
    pdf.write_bytes(b"%PDF")
    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=box"
    client.get_item_add_view.return_value = {}
    client.upload_pdf_via_page_add_files.return_value = {
        "ok": False,
        "bound": False,
        "upload_via": "cookie_http",
        "grid_pdf_row_count": 0,
        "status_gt0_n": 0,
        "finish_why": "empty_dataSource",
    }
    client.quote_item_read.return_value = {"Data": quote["ItemList"], "Total": 8}
    client.get_json.return_value = quote
    notes = SecturaFabPushService(client=client).finish_pdf_files(
        quote_id=SPENT_QUOTE_ID,
        pdf_files=[pdf],
        material="A36",
        thickness="0.1875",
        qty=1,
        description="WELDMENT, PEDESTAL",
        bom_rows=[
            {"part_no": "14501-1", "qty": 1, "description": "PEDESTAL TOP PLATE"},
        ],
    )
    client.upload_item_pdf_attachment.assert_not_called()
    client.add_item_pdf_files.assert_not_called()
    blob = " ".join(notes)
    assert "cookie HTTP" in blob or "did not bind" in blob or "not bound" in blob
    assert "GET>0" in blob
    assert "DoD FAIL" in blob
    assert "Linear saw PASS is not DoD PASS" in blob
    assert "persisted" not in blob.lower()


def test_live_103535_1_cookie_http_empty_grid_is_fail(tmp_path, monkeypatch):
    """5 cookie HTTP uploads + 4 L×W stamps + empty_dataSource + GET 0 = FAIL."""
    from secturafab.website import (
        cookie_http_pdf_upload_is_fail,
        empty_gridpdf_after_stamp_is_fail,
        image_files_cookie_http_empty_grid_is_fail,
        leftover_gridpdf_fills_only_via_onsuccess,
        pdf_grid_upload_bound,
    )
    from tests.fixtures.live_103535_1 import (
        COOKIE_HTTP_PLATE_STEMS,
        MISSING_FLATS_STEM,
        SPENT_QUOTE_ID,
        STAMP_N,
        live_103535_1_cookie_http_empty_grid,
        leftover_gridpdf_bind_dump,
    )

    dump = leftover_gridpdf_bind_dump()
    assert leftover_gridpdf_fills_only_via_onsuccess(dump) is True
    assert dump["kendoUpload"]["selector"] == "#files"
    assert dump["GetPDFData"]["is_xhr"] is False
    snap = live_103535_1_cookie_http_empty_grid()
    assert snap["ID"] == SPENT_QUOTE_ID
    assert snap["cookie_http_uploads"] == 5
    assert snap["stamp_n"] == STAMP_N == 4
    assert MISSING_FLATS_STEM == "103544"
    assert image_files_cookie_http_empty_grid_is_fail(
        cookie_http_uploads=snap["cookie_http_uploads"],
        stamp_n=snap["stamp_n"],
        finish_why=snap["finish_why"],
        filelist_from_kendo=snap["filelist_from_kendo"],
        cad_n=snap["cad_n"],
    )
    assert cookie_http_pdf_upload_is_fail("cookie_http")
    assert cookie_http_pdf_upload_is_fail("http")
    assert not cookie_http_pdf_upload_is_fail("page_add_files")
    assert empty_gridpdf_after_stamp_is_fail(
        {"finish_why": "empty_dataSource", "filelist_from_kendo": False},
        grid_pdf_row_count=0,
    )
    assert not pdf_grid_upload_bound(
        {
            "upload_via": "cookie_http",
            "bound": False,
            "status_gt0_n": 0,
            "grid_pdf_row_count": 0,
        }
    )

    monkeypatch.setenv("SECTURA_WEBSITE_COOKIE", "ASP.NET_SessionId=box")
    pdfs = []
    for stem in COOKIE_HTTP_PLATE_STEMS:
        p = tmp_path / f"{stem}.pdf"
        p.write_bytes(b"%PDF")
        pdfs.append(p)
    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=box"
    client.get_item_add_view.return_value = {}
    client.upload_pdf_via_page_add_files.return_value = {
        "bound": False,
        "upload_via": "cookie_http",
        "grid_pdf_row_count": 0,
        "status_gt0_n": 0,
        "finish_why": "empty_dataSource",
    }
    client.quote_item_read.return_value = {"Data": snap["ItemList"], "Total": 1}
    client.get_json.return_value = snap
    notes = SecturaFabPushService(client=client).finish_pdf_files(
        quote_id="11111111-aaaa-bbbb-cccc-000000001035",
        pdf_files=pdfs,
        material="A36",
        thickness="0.25",
        qty=1,
        description="GATE WELDMENT",
        bom_rows=[
            {
                "part_no": stem,
                "qty": 1,
                "description": "PLATE",
                "width_in": 8.0 if stem != MISSING_FLATS_STEM else None,
                "length_in": 12.0 if stem != MISSING_FLATS_STEM else None,
            }
            for stem in COOKIE_HTTP_PLATE_STEMS
        ],
    )
    client.upload_item_pdf_attachment.assert_not_called()
    client.stamp_pdf_kendo_flats.assert_not_called()
    client.add_item_pdf_files.assert_not_called()
    blob = " ".join(notes)
    assert "cookie HTTP" in blob
    assert "#gridPDF" in blob
    assert "GET 0 Cad" in blob
    assert "persisted" not in blob.lower()
    assert "AddItem_PDFFiles posted 1 FileList" not in blob


def test_29743_1_files_kendo_bind_is_not_gold_pack(tmp_path, monkeypatch):
    """#files + GetPDFData + OnAddPDFClick with Cad UnitCost 0 / empty OCL is FAIL."""
    from tests.fixtures.live_29743_1 import live_29743_1_quote

    quote = live_29743_1_quote()
    monkeypatch.setenv("SECTURA_WEBSITE_COOKIE", "ASP.NET_SessionId=box")
    pdfs = []
    for name in ("29743-a.pdf", "29743-b.pdf"):
        p = tmp_path / name
        p.write_bytes(b"%PDF")
        pdfs.append(p)
    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=box"
    client.get_item_add_view.return_value = {}
    client.upload_pdf_via_page_add_files.return_value = _page_pdf_bind_ok(2)
    client.add_item_pdf_files.return_value = {
        "ok": True,
        "via": "page_fn",
        "finish_fn": "OnAddPDFClick",
        "filelist_from_kendo": True,
        "finish_filelist_n": 2,
    }
    client.quote_item_read.return_value = {"Data": quote["ItemList"], "Total": 4}
    client.get_json.return_value = quote
    notes = SecturaFabPushService(client=client).finish_pdf_files(
        quote_id="11111111-aaaa-bbbb-cccc-000000002974",
        pdf_files=pdfs,
        material="A572",
        thickness="0.1875",
        qty=2,
        description="SUBFRAME WELDMENT",
        bom_rows=[
            {"part_no": "29743-a", "qty": 2, "description": "PLATE", "width_in": 8.0, "length_in": 12.0},
            {"part_no": "29743-b", "qty": 2, "description": "PLATE", "width_in": 10.0, "length_in": 14.0},
        ],
    )
    client.upload_item_pdf_attachment.assert_not_called()
    blob = " ".join(notes)
    assert "29743-1" in blob or "not gold" in blob or "UnitPrice is not UnitCost" in blob
    assert "DoD FAIL" in blob
    assert "Linear saw PASS is not DoD PASS" in blob
    assert "persisted" not in blob.lower()


def test_29743_1_empty_perimeter_does_not_finish(tmp_path, monkeypatch):
    """UpdatePerimeterWeight empty OutsidePerimeter — do not Finish."""
    from tests.fixtures.live_29743_1 import live_29743_1_quote

    quote = live_29743_1_quote()
    monkeypatch.setenv("SECTURA_WEBSITE_COOKIE", "ASP.NET_SessionId=box")
    pdfs = []
    for name in ("29743-a.pdf", "29743-b.pdf"):
        p = tmp_path / name
        p.write_bytes(b"%PDF")
        pdfs.append(p)
    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=box"
    client.get_item_add_view.return_value = {}
    client.upload_pdf_via_page_add_files.return_value = _page_pdf_bind_ok(2)
    client.stamp_pdf_kendo_flats.return_value = {
        "ok": True,
        "stamped": 2,
        "cell_edit": 4,
        "outside_perimeter_n": 0,
        "cutting_length_n": 0,
        "getperimeter_xhr": False,
        "perimeter_via": "",
    }
    client.quote_item_read.return_value = {"Data": quote["ItemList"], "Total": 4}
    client.get_json.return_value = quote
    notes = SecturaFabPushService(client=client).finish_pdf_files(
        quote_id="11111111-aaaa-bbbb-cccc-000000002974",
        pdf_files=pdfs,
        material="A572",
        thickness="0.1875",
        qty=2,
        description="SUBFRAME WELDMENT",
        bom_rows=[
            {"part_no": "29743-a", "qty": 2, "description": "PLATE", "width_in": 8.0, "length_in": 12.0},
            {"part_no": "29743-b", "qty": 2, "description": "PLATE", "width_in": 10.0, "length_in": 14.0},
        ],
    )
    client.add_item_pdf_files.assert_not_called()
    blob = " ".join(notes)
    assert "UpdatePerimeterWeight" in blob
    assert "empty OutsidePerimeter" in blob
    assert "29743-1" in blob
    assert "do not Finish" in blob
    assert "persisted" not in blob.lower()


def test_1002323_1_no_hole_rectangle_still_finishes(tmp_path, monkeypatch):
    """Empty InternalData after perimeter is expected — still Finish."""
    from tests.fixtures.live_1002323_1 import live_1002323_1_quote

    quote = live_1002323_1_quote()
    monkeypatch.setenv("SECTURA_WEBSITE_COOKIE", "ASP.NET_SessionId=box")
    pdf = tmp_path / "WRB-PLATE.pdf"
    pdf.write_bytes(b"%PDF")
    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=box"
    client.get_item_add_view.return_value = {}
    client.upload_pdf_via_page_add_files.return_value = _page_pdf_bind_ok(1)
    client.stamp_pdf_kendo_flats.return_value = {
        "ok": True,
        "stamped": 1,
        "cell_edit": 2,
        "outside_perimeter_n": 1,
        "cutting_length_n": 0,
        "weight_n": 1,
        "internaldata_n": 0,
        "getperimeter_xhr": True,
        "perimeter_via": "UpdatePerimeterWeight",
    }
    client.add_item_pdf_files.return_value = {
        "ok": True,
        "via": "page_fn",
        "finish_fn": "OnAddPDFClick",
        "filelist_from_kendo": True,
        "finish_filelist_n": 1,
    }
    client.quote_item_read.return_value = {"Data": quote["ItemList"], "Total": 1}
    client.get_json.return_value = quote
    notes = SecturaFabPushService(client=client).finish_pdf_files(
        quote_id="11111111-aaaa-bbbb-cccc-000000001002",
        pdf_files=[pdf],
        material="A572",
        thickness="0.375",
        qty=2,
        description="WINCH ROLLER BRACKETS",
        bom_rows=[
            {
                "part_no": "WRB-PLATE",
                "qty": 2,
                "description": "PLATE",
                "width_in": 2.5,
                "length_in": 19.82,
            }
        ],
    )
    client.add_item_pdf_files.assert_called_once()
    blob = " ".join(notes)
    assert "1002323-1" in blob
    assert "do not Finish" not in blob
    assert "AddNewPDFFeature" not in blob
    assert "DoD FAIL" in blob
    assert "persisted" not in blob.lower()


def test_1002323_1_empty_weight_after_perimeter_does_not_finish(
    tmp_path, monkeypatch
):
    """GetPDFData bag Weight empty after landed perimeter — do not Finish."""
    from tests.fixtures.live_1002323_1 import live_1002323_1_quote

    quote = live_1002323_1_quote()
    monkeypatch.setenv("SECTURA_WEBSITE_COOKIE", "ASP.NET_SessionId=box")
    pdf = tmp_path / "WRB-PLATE.pdf"
    pdf.write_bytes(b"%PDF")
    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=box"
    client.get_item_add_view.return_value = {}
    client.upload_pdf_via_page_add_files.return_value = _page_pdf_bind_ok(1)
    client.stamp_pdf_kendo_flats.return_value = {
        "ok": True,
        "stamped": 1,
        "cell_edit": 2,
        "outside_perimeter_n": 1,
        "cutting_length_n": 0,
        "weight_n": 0,
        "internaldata_n": 0,
        "getperimeter_xhr": True,
        "perimeter_via": "UpdatePerimeterWeight",
    }
    client.quote_item_read.return_value = {"Data": quote["ItemList"], "Total": 1}
    client.get_json.return_value = quote
    notes = SecturaFabPushService(client=client).finish_pdf_files(
        quote_id="11111111-aaaa-bbbb-cccc-000000001002",
        pdf_files=[pdf],
        material="A572",
        thickness="0.375",
        qty=2,
        description="WINCH ROLLER BRACKETS",
        bom_rows=[
            {
                "part_no": "WRB-PLATE",
                "qty": 2,
                "description": "PLATE",
                "width_in": 2.5,
                "length_in": 19.82,
            }
        ],
    )
    client.add_item_pdf_files.assert_not_called()
    blob = " ".join(notes)
    assert "1002323-1" in blob
    assert "bag Weight empty" in blob
    assert "GetPDFData omits CuttingLength" in blob
    assert "do not Finish" in blob
    assert "persisted" not in blob.lower()


def test_33819_1_empty_productid_after_bind_does_not_finish(
    tmp_path, monkeypatch
):
    """GetPDFData ProductID empty after #files bind — do not Finish."""
    from tests.fixtures.live_33819_1 import live_33819_1_quote

    quote = live_33819_1_quote()
    monkeypatch.setenv("SECTURA_WEBSITE_COOKIE", "ASP.NET_SessionId=box")
    pdf = tmp_path / "COMP-LINK-LUG.pdf"
    pdf.write_bytes(b"%PDF")
    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=box"
    client.get_item_add_view.return_value = {}
    bind = _page_pdf_bind_ok(1)
    bind["productid_n"] = 0
    client.upload_pdf_via_page_add_files.return_value = bind
    client.quote_item_read.return_value = {"Data": quote["ItemList"], "Total": 1}
    client.get_json.return_value = quote
    notes = SecturaFabPushService(client=client).finish_pdf_files(
        quote_id="11111111-aaaa-bbbb-cccc-000000003381",
        pdf_files=[pdf],
        material="A572",
        thickness="0.625",
        qty=1,
        description="COMP LINK LUG",
        bom_rows=[
            {
                "part_no": "COMP-LINK-LUG",
                "qty": 1,
                "description": "PLATE",
                "width_in": 4.0,
                "length_in": 16.0,
            }
        ],
    )
    client.add_item_pdf_files.assert_not_called()
    client.stamp_pdf_kendo_flats.assert_not_called()
    blob = " ".join(notes)
    assert "33819-1" in blob
    assert "ProductID empty after #files bind" in blob
    assert "do not invent a GUID" in blob
    assert "do not Finish" in blob
    assert "persisted" not in blob.lower()


def test_33819_1_empty_productid_after_stamp_does_not_finish(
    tmp_path, monkeypatch
):
    """Stamp wipe of upload ProductID — do not Finish."""
    from tests.fixtures.live_33819_1 import live_33819_1_quote

    quote = live_33819_1_quote()
    monkeypatch.setenv("SECTURA_WEBSITE_COOKIE", "ASP.NET_SessionId=box")
    pdf = tmp_path / "COMP-LINK-LUG.pdf"
    pdf.write_bytes(b"%PDF")
    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=box"
    client.get_item_add_view.return_value = {}
    client.upload_pdf_via_page_add_files.return_value = _page_pdf_bind_ok(1)
    client.stamp_pdf_kendo_flats.return_value = {
        "ok": True,
        "stamped": 1,
        "cell_edit": 2,
        "outside_perimeter_n": 1,
        "cutting_length_n": 0,
        "weight_n": 1,
        "productid_n": 0,
        "internaldata_n": 0,
        "getperimeter_xhr": True,
        "perimeter_via": "UpdatePerimeterWeight",
    }
    client.quote_item_read.return_value = {"Data": quote["ItemList"], "Total": 1}
    client.get_json.return_value = quote
    notes = SecturaFabPushService(client=client).finish_pdf_files(
        quote_id="11111111-aaaa-bbbb-cccc-000000003381",
        pdf_files=[pdf],
        material="A572",
        thickness="0.625",
        qty=1,
        description="COMP LINK LUG",
        bom_rows=[
            {
                "part_no": "COMP-LINK-LUG",
                "qty": 1,
                "description": "PLATE",
                "width_in": 4.0,
                "length_in": 16.0,
            }
        ],
    )
    client.add_item_pdf_files.assert_not_called()
    blob = " ".join(notes)
    assert "33819-1" in blob
    assert "ProductID empty after L×W stamp" in blob
    assert "do not invent a GUID" in blob
    assert "do not Finish" in blob
    assert "persisted" not in blob.lower()


def test_33819_1_bind_without_productid_n_still_finishes_leftover_fail(
    tmp_path, monkeypatch
):
    """Older bind omitting productid_n still Finishes; leftover GET is FAIL."""
    from tests.fixtures.live_33819_1 import live_33819_1_quote

    quote = live_33819_1_quote()
    monkeypatch.setenv("SECTURA_WEBSITE_COOKIE", "ASP.NET_SessionId=box")
    pdf = tmp_path / "COMP-LINK-LUG.pdf"
    pdf.write_bytes(b"%PDF")
    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=box"
    client.get_item_add_view.return_value = {}
    client.upload_pdf_via_page_add_files.return_value = _page_pdf_bind_ok(1)
    client.stamp_pdf_kendo_flats.return_value = {
        "ok": True,
        "stamped": 1,
        "cell_edit": 2,
        "outside_perimeter_n": 1,
        "cutting_length_n": 0,
        "weight_n": 1,
        "productid_n": 1,
        "internaldata_n": 0,
        "getperimeter_xhr": True,
        "perimeter_via": "UpdatePerimeterWeight",
    }
    client.add_item_pdf_files.return_value = {
        "ok": True,
        "via": "page_fn",
        "finish_fn": "OnAddPDFClick",
        "filelist_from_kendo": True,
        "finish_filelist_n": 1,
        "filelist_bag": {
            "Machine": "Laser - Bay1",
            "ProductID": None,
            "Qty": 1,
            "Weight": 15.0875,
            "Weight_UseLocal": True,
            "OutsidePerimeter": 40,
            "OutsidePerimeter_UseLocal": True,
            "Material": "A572",
            "Thickness": "0.625",
            "Length": 16,
            "Width": 4,
        },
    }
    client.quote_item_read.return_value = {"Data": quote["ItemList"], "Total": 1}
    client.get_json.return_value = quote
    notes = SecturaFabPushService(client=client).finish_pdf_files(
        quote_id="11111111-aaaa-bbbb-cccc-000000003381",
        pdf_files=[pdf],
        material="A572",
        thickness="0.625",
        qty=1,
        description="COMP LINK LUG",
        bom_rows=[
            {
                "part_no": "COMP-LINK-LUG",
                "qty": 1,
                "description": "PLATE",
                "width_in": 4.0,
                "length_in": 16.0,
            }
        ],
    )
    client.add_item_pdf_files.assert_called_once()
    stamp_rows = client.stamp_pdf_kendo_flats.call_args.kwargs.get("rows") or []
    assert stamp_rows
    assert all("ProductID" not in row for row in stamp_rows)
    blob = " ".join(notes)
    assert "33819-1" in blob
    assert "do not Finish" not in blob
    assert "ProductID None" in blob
    assert "DoD FAIL" in blob
    assert "persisted" not in blob.lower()
