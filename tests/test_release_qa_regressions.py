"""Regressions from the bdce8a9 live QA bundle. No Sectura calls."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from secturafab.page_weld import (
    PAGE_ADD_ASSEMBLY_JS,
    STEP_MM_CONTINUE_NOTE,
    STEP_UNITS_UNKNOWN_NOTE,
    resolve_cad_length_unit,
)
from secturafab.step_units import (
    convert_step_text_mm_to_inch,
    step_length_unit,
    step_uses_millimetres,
)

_OCC_INCH = """
#14=(LENGTH_UNIT()NAMED_UNIT(*)SI_UNIT(.MILLI.,.METRE.));
#13=LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE(25.4),#14);
#12=(CONVERSION_BASED_UNIT('INCH',#13)LENGTH_UNIT()NAMED_UNIT(*));
"""
_TRUE_MM = "SI_UNIT(.MILLI.,.METRE.);"
_QID = "eefcc4e3-761e-4355-af46-fb2b6982cb8a"


def test_occ_inch_conversion_base_is_not_millimetres():
    assert step_length_unit(_OCC_INCH) == "inch"
    assert step_uses_millimetres(_OCC_INCH) is False
    assert step_length_unit(_TRUE_MM) == "mm"
    assert step_uses_millimetres(_TRUE_MM) is True
    _out, changed = convert_step_text_mm_to_inch(_OCC_INCH)
    assert changed is False
    assert step_length_unit("ISO-10303-21;") == "unknown"


def test_grid_dxf_units_win_over_the_step_header():
    assert resolve_cad_length_unit(headers=[_TRUE_MM], grid_rows=[{"Units": "inch"}]) == "inch"
    assert resolve_cad_length_unit(headers=[_OCC_INCH], grid_rows=[{"Units": "mm"}]) == "mm"
    assert resolve_cad_length_unit(headers=["ISO-10303-21;"], grid_rows=[]) == "unknown"
    assert (
        resolve_cad_length_unit(
            headers=[_OCC_INCH],
            grid_rows=[{"Units": "inch"}, {"Units": "mm"}],
        )
        == "unknown"
    )


def test_unknown_units_fail_closed_before_create(tmp_path, monkeypatch):
    from secturafab.push import SecturaFabPushService

    monkeypatch.setattr("secturafab.chrome_cdp.chrome_session_lost", lambda *a, **k: False)
    monkeypatch.setattr("secturafab.chrome_cdp.chrome_quotes_live", lambda *a, **k: True)
    monkeypatch.setattr(
        "secturafab.chrome_cdp.page_jquery_ajax",
        lambda **k: {"ok": True, "status": 200, "body": "<div id='dxf'></div>"},
    )
    stp = tmp_path / "unknown.step"
    stp.write_text("ISO-10303-21;", encoding="utf-8")
    client = MagicMock()
    client.upload_dxf_via_page_add_files.return_value = {
        "bound": True,
        "files_kendo": True,
        "upload_via": "page_add_files",
        "gridDXF_n": 1,
        "List": [{"SourceDataID": "src"}],
    }
    notes = SecturaFabPushService(client=client).finish_cad_files(
        quote_id=_QID,
        cad_files=[stp],
        material="A36",
        thickness="0.076",
        qty=1,
        takeoff={},
        bom_rows=[],
        library={},
        extra_pdfs=None,
        part_key="ZZ",
        explode_polls=1,
        explode_sleep_s=0,
    )
    assert any(STEP_UNITS_UNKNOWN_NOTE in note for note in notes)
    client.create_all_parts_from_grid_dxf.assert_not_called()
    client.upload_item_dxf_files.assert_not_called()


def test_page_upload_miss_does_not_cookie_post(tmp_path, monkeypatch):
    from secturafab.push import SecturaFabPushService

    monkeypatch.setattr("secturafab.chrome_cdp.chrome_session_lost", lambda *a, **k: False)
    monkeypatch.setattr("secturafab.chrome_cdp.chrome_quotes_live", lambda *a, **k: True)
    monkeypatch.setattr(
        "secturafab.chrome_cdp.page_jquery_ajax",
        lambda **k: {"ok": True, "body": ""},
    )
    stp = tmp_path / "A.step"
    stp.write_text(_OCC_INCH, encoding="utf-8")
    client = MagicMock()
    client.upload_dxf_via_page_add_files.return_value = {}
    notes = SecturaFabPushService(client=client).finish_cad_files(
        quote_id=_QID,
        cad_files=[stp],
        material="A36",
        thickness="0.076",
        qty=1,
        takeoff={},
        bom_rows=[],
        library={},
        extra_pdfs=None,
        part_key="ZZ",
        explode_polls=1,
        explode_sleep_s=0,
    )
    client.upload_item_dxf_files.assert_not_called()
    assert any("not falling back" in note for note in notes)


def test_set_units_posts_before_create_all_parts(tmp_path, monkeypatch):
    from secturafab.push import SecturaFabPushService

    order: list[str] = []

    def _ajax(**kwargs):
        order.append(str(kwargs.get("url")))
        return {"ok": True, "status": 200, "body": "<div id='dxf'></div>"}

    def _create(**kwargs):
        order.append("create")
        return {"via": "createAllParts", "List": [], "grid_present": False}

    monkeypatch.setattr("secturafab.chrome_cdp.chrome_session_lost", lambda *a, **k: False)
    monkeypatch.setattr("secturafab.chrome_cdp.chrome_quotes_live", lambda *a, **k: True)
    monkeypatch.setattr("secturafab.chrome_cdp.page_jquery_ajax", _ajax)
    stp = tmp_path / "inch.step"
    stp.write_text(_OCC_INCH, encoding="utf-8")
    client = MagicMock()
    client.upload_dxf_via_page_add_files.return_value = {
        "bound": True,
        "files_kendo": True,
        "upload_via": "page_add_files",
        "gridDXF_n": 1,
        "List": [{"SourceDataID": "src-inch", "Units": "inch"}],
    }
    client.create_all_parts_from_grid_dxf.side_effect = _create
    SecturaFabPushService(client=client).finish_cad_files(
        quote_id=_QID,
        cad_files=[stp],
        material="A36",
        thickness="0.076",
        qty=1,
        takeoff={},
        bom_rows=[],
        library={},
        extra_pdfs=None,
        part_key="ZZ",
        explode_polls=1,
        explode_sleep_s=0,
    )
    assert order.index("/CadImport/SetUnits") < order.index("create")


def test_select_exactly_one_uses_view_uid_and_gauge_label():
    from secturafab.chrome_cdp import _PAGE_FINISH_JS

    assert "dataSource.view" in _PAGE_FINISH_JS
    assert "g.items" in _PAGE_FINISH_JS
    assert "0.003" in _PAGE_FINISH_JS
    assert "ga" in _PAGE_FINISH_JS
    assert 'ProductType", "prt_dxf"' in _PAGE_FINISH_JS or 'ProductType", "prt_dxf"' in _PAGE_FINISH_JS


def test_q10506_sheet_filelist_is_prt_dxf_not_bar():
    from secturafab.website import (
        Q10506_PROVEN_UNIT_PRICE,
        sanitize_cad_contours_plate_finish_filelist_row,
    )

    assert Q10506_PROVEN_UNIT_PRICE == {"A-11521-000": 177.46, "A-11513-000": 159.58}
    posted = sanitize_cad_contours_plate_finish_filelist_row(
        {
            "ItemType": "Cad",
            "Category": "Cad",
            "FileType": "Cad",
            "Material": "A36",
            "Thickness": "0.076",
            "Thickness_Units": "inch",
            "Machine": "Laser",
            "Name": "A-11521-000",
        }
    )
    assert posted["ProductType"] == "prt_dxf"
    assert posted["ProductSubType"] == "prt_dxf"
    assert posted["ProductSubType"] != "bar_flat"


def test_imagestring_preview_is_not_an_explode_refuse():
    from secturafab.website import STEP_EXPLODE_NO_INTERNALDATA, persist_part_create_tlist_bind_source

    preview: list[str] = []
    persist_part_create_tlist_bind_source(
        [{"ImageString": "preview-bytes"}],
        notes=preview,
    )
    assert STEP_EXPLODE_NO_INTERNALDATA not in preview
    empty: list[str] = []
    persist_part_create_tlist_bind_source([{}], notes=empty)
    assert STEP_EXPLODE_NO_INTERNALDATA in empty


def test_assembly_js_waits_for_name_and_additem_response():
    assert "nameDeadline" in PAGE_ADD_ASSEMBLY_JS
    assert "await pending" in PAGE_ADD_ASSEMBLY_JS
    assert PAGE_ADD_ASSEMBLY_JS.index("AddNewItemHTML") < PAGE_ADD_ASSEMBLY_JS.index(
        "nameDeadline"
    )
    assert PAGE_ADD_ASSEMBLY_JS.index("#AssemblyName") < PAGE_ADD_ASSEMBLY_JS.index(
        "OnCopyAll()"
    )


def test_push_keeps_every_step_file(tmp_path, monkeypatch):
    from secturafab.push import SecturaFabPushService

    first = tmp_path / "A-11521-000.step"
    second = tmp_path / "A-11513-000.step"
    first.write_text(_OCC_INCH, encoding="utf-8")
    second.write_text(_OCC_INCH, encoding="utf-8")
    seen: dict[str, int] = {}
    monkeypatch.setattr(
        "secturafab.push.collect_job_files",
        lambda **kwargs: ([], [first, second]),
    )
    monkeypatch.setattr("secturafab.chrome_cdp.chrome_quotes_live", lambda *a, **k: False)
    monkeypatch.setattr("secturafab.chrome_cdp.quotes_tab", lambda *a, **k: None)
    monkeypatch.setattr("secturafab.chrome_cdp.chrome_session_lost", lambda *a, **k: False)
    monkeypatch.setattr("secturafab.push.refresh_bom_rows_for_push", lambda *a, **k: ([], []))
    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=test"
    client.get_json.return_value = {"ItemList": [], "ItemCount": 0, "PrimaryOrganizationID": "org"}
    service = SecturaFabPushService(client=client)

    def _finish(**kwargs):
        seen["n"] = len(kwargs["cad_files"])
        return ["Finish stopped for the test"]

    monkeypatch.setattr(service, "create_quote", lambda **k: "qid")
    monkeypatch.setattr(service, "allocate_quote_number", lambda *a, **k: "ZZ-WELD")
    monkeypatch.setattr(service, "upload_drawings_quote_request", lambda *a, **k: "qr")
    monkeypatch.setattr(service, "finish_cad_files", _finish)
    monkeypatch.setattr(service, "apply_item_categories", lambda *a, **k: [])
    result = service.push_job(
        title="ZZ-WELD",
        pdf_filename=None,
        pdf_path=None,
        stp_path=first,
        takeoff={"library": {"part_key": "ZZ-WELD"}},
        times={},
        job_id=1,
    )
    assert seen["n"] == 2
    assert result.ok is False or result.notes


def test_fourteen_gauge_dp_parses_and_blank_thickness_is_not_seeded():
    from quote_core.part_materials import _parse_thickness_token, parse_material_block
    from secturafab.push import _default_thickness_in, _sanitize_thickness_param

    assert _parse_thickness_token("14 GA DP -") == pytest.approx(0.0747)
    thickness, _key, _src = parse_material_block("14 GA DP -")
    assert thickness == pytest.approx(0.0747)
    assert _sanitize_thickness_param(None) == ""
    assert _sanitize_thickness_param("") == ""
    assert _sanitize_thickness_param("14 GA DP -") == "0.0747"
    assert _default_thickness_in({}, None) == ""


def test_unresolved_plate_stops_and_tube_is_not_cad():
    from secturafab.push import SecturaFabPushService

    service = SecturaFabPushService(client=MagicMock())
    classified, notes = service.classify_cadimport_rows(
        [{"Name": "SIDE PLATE", "FileName": "plate.step"}],
        default_material="A36",
        default_thickness="",
        bom_rows=[],
        library={},
        extra_pdfs=None,
    )
    assert classified == []
    assert any("thickness unresolved" in note for note in notes)
    tubes, tube_notes = service.classify_cadimport_rows(
        [{"Name": "PIVOT TUBE", "FileName": "tube.step"}],
        default_material="A36",
        default_thickness="",
        bom_rows=[],
        library={},
        extra_pdfs=None,
        stock_kind="plate",
    )
    assert tubes
    assert not any("thickness unresolved" in note for note in tube_notes)
    blob = " ".join(str(tubes[0].get(key) or "") for key in ("Category", "ItemType", "FileType"))
    assert "Linear" in blob


def test_page_session_replaces_cookie_gate():
    from secturafab.push import SecturaFabPushService

    service = SecturaFabPushService(client=MagicMock())
    service._website_cookie_present = lambda: False  # type: ignore[method-assign]
    service._page_session_live = lambda: True  # type: ignore[method-assign]
    assert service._website_or_page_session() is True


def test_discard_pdf_confirm_is_overridden_in_page():
    from secturafab.chrome_cdp import _DISCARD_PDF_CONFIRM_JS

    assert "window.confirm" in _DISCARD_PDF_CONFIRM_JS
    assert "discard the PDF files" in _DISCARD_PDF_CONFIRM_JS
    assert "Image Files" in _DISCARD_PDF_CONFIRM_JS or "image files" in _DISCARD_PDF_CONFIRM_JS


def test_length_library_does_not_read_unrelated_pdfs(tmp_path, monkeypatch):
    from secturafab.line_item_ops import _length_from_library

    other = tmp_path / "unrelated.pdf"
    other.write_bytes(b"%PDF-1.4")
    monkeypatch.setattr(
        "secturafab.line_item_ops._cached_drawing_text",
        lambda *a, **k: "CUT LENGTH 10.25",
    )
    monkeypatch.setattr("secturafab.line_item_ops._pdfs_matching_part", lambda *a, **k: [])
    monkeypatch.setattr(
        "secturafab.pdf_assembly_ops.resolve_component_pdf",
        lambda *a, **k: None,
    )
    assert (
        _length_from_library(
            "21897-1",
            library_folder=tmp_path,
            extra_pdfs=[other],
        )
        is None
    )


def test_bare_tube_and_beam_do_not_fuzzy_pick_a_sku():
    from secturafab.website import pick_closest_linear_product

    tube, tube_note = pick_closest_linear_product(
        [{"ID": "1", "ProductName": "RT1/8X0.022-A519", "ShapeName": "TUBE", "MaterialGrade": "A519"}],
        description="TUBE",
    )
    beam, beam_note = pick_closest_linear_product(
        [{"ID": "2", "ProductName": "L1/2X1/2X1/8-A36", "ShapeName": "ANGLE", "MaterialGrade": "A36"}],
        description="BEAM",
    )
    assert tube is None and tube_note
    assert beam is None and beam_note
    assert "no tenant SKU" in tube_note
    assert "no tenant SKU" in beam_note


def test_linear_finish_500_is_not_ok(monkeypatch):
    from secturafab.chrome_cdp import invoke_page_linear_finish

    monkeypatch.setattr(
        "secturafab.chrome_cdp.minted_edit_tab_ready",
        lambda *a, **k: {"ok": True, "tab": {"webSocketDebuggerUrl": "ws://local"}},
    )

    def _eval(*args, **kwargs):
        return {
            "via": "page_fn",
            "long_from_page": True,
            "finish_fn": "OnAddLinearClick",
            "status": 500,
            "request_keys": ["ID"],
        }

    monkeypatch.setattr("secturafab.chrome_cdp._cdp_evaluate_promise", _eval)
    failed = invoke_page_linear_finish(quote_id=_QID)
    assert failed["status"] == 500
    assert failed["ok"] is False

    def _ok(*args, **kwargs):
        return {"via": "page_fn", "long_from_page": True, "status": 200, "finish_fn": "OnAddLinearClick"}

    monkeypatch.setattr("secturafab.chrome_cdp._cdp_evaluate_promise", _ok)
    passed = invoke_page_linear_finish(quote_id=_QID)
    assert passed["ok"] is True


def test_nest_quote_api_sends_idlist_object():
    from secturafab.client import SecturaFabClient

    client = MagicMock()
    SecturaFabClient.nest_quote_api(client, "qid", nest_type="multi", id_list=["line-1"])
    client.post_json.assert_called_once_with(
        "v1/Nest/quote/qid/multi",
        payload={"IDList": ["line-1"]},
    )
    client.post_json.reset_mock()
    SecturaFabClient.nest_quote_api(client, "qid")
    assert client.post_json.call_args.kwargs["payload"] == {"IDList": []}


def test_create_quote_posts_organization_object():
    from secturafab.push import SecturaFabPushService

    client = MagicMock()
    response = MagicMock(status_code=201)
    client.request.return_value = response
    client._parse_or_raise.return_value = "qid"
    client.get_json.return_value = {
        "PrimaryOrganizationID": "b7dbc294-3fd2-43aa-99be-268a6c4fce14"
    }
    SecturaFabPushService(client=client).create_quote(
        quote_number="ZZ-ORG",
        organization_name="Time Manufacturing Waco",
        organization_id="b7dbc294-3fd2-43aa-99be-268a6c4fce14",
    )
    payload = client.request.call_args_list[0].kwargs["json"]
    assert payload["PrimaryOrganizationID"] == "b7dbc294-3fd2-43aa-99be-268a6c4fce14"
    assert payload["Organization"]["ID"] == "b7dbc294-3fd2-43aa-99be-268a6c4fce14"
    assert payload["OrganizationID"] == payload["Organization"]["ID"]


def test_relogin_success_clears_cooldown(tmp_path, monkeypatch):
    from secturafab.web_login import (
        _cooldown_active,
        attempt_sectura_relogin,
        reset_relogin_attempt_for_tests,
    )
    from tests.test_sectura_relogin import FakeCdp, _env

    alerts = tmp_path / "alerts"
    locks = tmp_path / "locks"
    alerts.mkdir()
    locks.mkdir()
    reset_relogin_attempt_for_tests()
    attempt_sectura_relogin(
        trigger="login_url",
        cdp=FakeCdp("success"),
        launcher=lambda **kwargs: (_ for _ in ()).throw(AssertionError("launched")),
        alerts=alerts,
        locks=locks,
        env=_env(),
        sleep=lambda _s: None,
        max_polls=2,
        port=9224,
    )
    text = next(locks.glob("relogin-*.txt")).read_text(encoding="utf-8")
    assert "page_state=success" in text
    assert _cooldown_active(locks, now=__import__("time").time(), cooldown_s=12 * 3600) is False
    reset_relogin_attempt_for_tests()


def test_login_title_allows_spaces_and_alert_hook(monkeypatch):
    from secturafab.chrome_cdp import SessionDeadError, abort_if_session_dead, session_is_dead

    assert session_is_dead(title="SecturaFAB - Login") == "login_title"
    seen: dict[str, object] = {}

    def _attempt(**kwargs):
        seen["hook"] = kwargs.get("on_alert")

    monkeypatch.setattr("secturafab.web_login.attempt_sectura_relogin", _attempt)
    hook = lambda message: None  # noqa: E731
    abort_if_session_dead(title="SecturaFAB - Login", on_alert=hook)
    assert seen["hook"] is hook

    def _alert(message, **kwargs):
        seen["alert_hook"] = kwargs.get("on_alert")
        return Path("alert.txt")

    monkeypatch.setattr("secturafab.web_login.alert_chief_of_staff", _alert)
    with pytest.raises(SessionDeadError):
        abort_if_session_dead(body="Another user has logged in", on_alert=hook)
    assert seen["alert_hook"] is hook


def test_qc_flags_missing_profile_and_missing_parent():
    from secturafab.quote_qc import check_tree

    kid = {
        "ItemNumber": "A-11521-000",
        "ProductType": 100,
        "ProductSubType": "prt_dxf",
        "Machine": "Laser",
        "Quantity": 1,
        "Length": 37.5,
        "Width": 26.6,
        "Length_Units": "inch",
        "Material": "A36",
        "Thickness": 0.076,
        "Thickness_Units": "inch",
        "UnitCost": 33.19,
        "UnitPrice": 48.99,
        "NumberOfContours": 1,
        "ErrorCount": 0,
        "OperationCostList": [{"OperationName": "Bend"}],
    }
    other = dict(kid)
    other["ItemNumber"] = "A-11513-000"
    other["UnitPrice"] = 43.19
    report = check_tree(
        {"Data": [kid, other]},
        {"A-11521-000": 1, "A-11513-000": 1},
        formed=[],
        label="E",
    )
    assert any("no Profile op" in flag for flag in report.flags)
    assert any("weldment has no parent line" in flag for flag in report.flags)
    assert report.status == "FLAG"


def test_default_reader_navigates_to_the_edit_page(monkeypatch):
    from secturafab.quote_qc import _default_reader

    calls: list[bool] = []

    def _ready(quote_id, navigate=True, **kwargs):
        calls.append(bool(navigate))
        return {"ok": True, "tab": {"webSocketDebuggerUrl": "ws://local"}}

    monkeypatch.setattr("secturafab.chrome_cdp.minted_edit_tab_ready", _ready)
    monkeypatch.setattr(
        "secturafab.chrome_cdp.page_jquery_ajax",
        lambda **kwargs: {"ok": True, "body": {"rows": []}},
    )
    assert _default_reader(_QID) == {"rows": []}
    assert calls == [True]


def test_mm_continue_fails_when_finish_dims_are_blank():
    from secturafab.page_weld import mm_kept_flats_fail

    notes = [STEP_MM_CONTINUE_NOTE]
    assert mm_kept_flats_fail(notes, [{"ItemNumber": "A", "Length": None, "Width": None}])
    assert (
        mm_kept_flats_fail(
            notes,
            [{"ItemNumber": "A", "Length": 37.5, "Width": 26.6, "ProductType": 100}],
        )
        is None
    )
