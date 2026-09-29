"""Regressions from the bdce8a9 live QA bundle. No Sectura calls."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

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
        organization="Safe Cave",
        quote_number="ZZ-WELD",
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
    blob = " ".join(
        str(tubes[0].get(key) or "") for key in ("Category", "ItemType", "FileType")
    )
    assert "Linear" in blob
    assert tubes[0].get("Machine") != "Laser"


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


def test_nest_quote_api_does_not_post_json_idlist():
    from secturafab.client import SecturaFabApiError, SecturaFabClient

    client = MagicMock()
    with pytest.raises(SecturaFabApiError, match="OnNestQuote_Edit"):
        SecturaFabClient.nest_quote_api(client, "qid", nest_type="multi", id_list=["line-1"])
    client.post_json.assert_not_called()


def test_create_quote_uses_page_new_quote_and_open_new_header():
    from unittest.mock import patch

    from secturafab.client import SecturaFabApiError
    from secturafab.push import SecturaFabPushService

    client = MagicMock()
    client.get_json.return_value = {
        "ID": "new-qid",
        "ProfitModel": 1,
        "QuoteStatus": "OPEN-NEW",
        "PrimaryOrganizationID": "b7dbc294-3fd2-43aa-99be-268a6c4fce14",
    }
    with patch(
        "secturafab.chrome_cdp.page_create_quote",
        return_value={"ok": True, "quote_id": "new-qid", "via": "GET /quote/create"},
    ) as created, patch(
        "secturafab.page_weld.set_page_quote_number",
        return_value=["QuoteNumber set via UpdatePropertyValue"],
    ) as number, patch(
        "secturafab.page_weld.set_page_quote_description",
        return_value=["Description set via UpdatePropertyValue"],
    ) as desc, patch(
        "secturafab.chrome_cdp.bind_quote_organization_detail",
        return_value={
            "ok": True,
            "via": "OrganizationDetail",
            "search": False,
            "org_id": "bound",
        },
    ) as bound:
        quote_id = SecturaFabPushService(client=client).create_quote(
            quote_number="ZZ-ORG",
            description="SAFE CAVE",
            organization_name="Time Manufacturing Waco",
            organization_id="b7dbc294-3fd2-43aa-99be-268a6c4fce14",
        )
    assert quote_id == "new-qid"
    created.assert_called_once()
    assert number.call_args.args[1] == "ZZ-ORG"
    assert desc.call_args.args[1] == "SAFE CAVE"
    assert bound.call_args.kwargs["org_name"] == "Time Manufacturing Waco"
    client.request.assert_not_called()
    client.get_json.return_value = {"ProfitModel": 0, "QuoteStatus": "OPEN-DRAFT"}
    with patch(
        "secturafab.chrome_cdp.page_create_quote",
        return_value={"ok": True, "quote_id": "draft-qid", "via": "GET /quote/create"},
    ), patch(
        "secturafab.page_weld.set_page_quote_number",
        return_value=["QuoteNumber set via UpdatePropertyValue"],
    ), patch(
        "secturafab.chrome_cdp.bind_quote_organization_detail",
        return_value={"ok": True, "via": "OrganizationDetail", "search": False, "org_id": "bound"},
    ), pytest.raises(SecturaFabApiError, match="OPEN-NEW"):
        SecturaFabPushService(client=client).create_quote(
            quote_number="ZZ-ORG",
            organization_name="Time Manufacturing Waco",
        )
    client.request.assert_not_called()


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


def test_harvest_antiforgery_does_not_read_cookies():
    import inspect

    from secturafab.client import SecturaFabClient

    src = inspect.getsource(SecturaFabClient.harvest_chrome_antiforgery)
    assert "sectura_cookies_from_cdp" not in src


def test_dosetitemtype_passes_cad_then_part_id():
    from secturafab.chrome_cdp import _APPLY_GRID_PART_MODES_JS, _PAGE_FINISH_JS

    assert 'ddl.value("cad")' in _PAGE_FINISH_JS
    assert 'ddl.trigger("change")' in _PAGE_FINISH_JS
    assert 'DoSetItemType("cad", [partId])' not in _PAGE_FINISH_JS
    assert "DoSetItemType(typeName, [partId])" in _APPLY_GRID_PART_MODES_JS
    assert 'ddl.value(typeToken)' in _APPLY_GRID_PART_MODES_JS
    assert "opts.data.FileList = leanRows" not in _PAGE_FINISH_JS
    mark = _PAGE_FINISH_JS.index('ddl.trigger("change")')
    assert _PAGE_FINISH_JS.index("/Quote/GetBorderSize", mark) > mark


def test_mm_grid_converts_flats_and_keeps_inch_gauge():
    from secturafab.website import (
        convert_mm_grid_flats_to_inches,
        plate_step_thickness_invalid_vs_drawing,
    )

    row = {
        "Name": "plate",
        "Category": "Cad",
        "Length": 952.5,
        "Width": 385.445,
        "Length_Units": "mm",
        "Width_Units": "mm",
        "Units": "mm",
        "Thickness": 0.0747,
        "Thickness_Units": "mm",
        "thickness_source": "drawing",
        "drawing_thickness_in": "0.0747",
        "Material": "A36",
    }
    assert convert_mm_grid_flats_to_inches(row) is None
    assert row["Length"] == pytest.approx(37.5, rel=1e-3)
    assert row["Width"] == pytest.approx(385.445 / 25.4, rel=1e-3)
    assert row["Thickness"] == pytest.approx(0.0747)
    assert row["Length_Units"] == "inch"
    assert row["Thickness_Units"] == "inch"
    assert plate_step_thickness_invalid_vs_drawing(row) is None
    bad = {"Length": "nope", "Width": 10, "Length_Units": "mm", "Width_Units": "mm"}
    assert "not a number" in (convert_mm_grid_flats_to_inches(bad) or "")


def test_pn_plus_generic_tube_fails_closed():
    from secturafab.website import pick_closest_linear_product

    products = [
        {
            "ID": "rt18",
            "ProductName": "RT1/8X0.022-A519",
            "ShapeName": "TUBE",
            "MaterialGrade": "A519",
            "Dim1": 0.125,
            "Dim2": 0.022,
        },
        {
            "ID": "rt14",
            "ProductName": "RT2 1/4X0.5-A519",
            "ShapeName": "TUBE",
            "MaterialGrade": "A519",
            "Dim1": 0.25,
            "Dim2": 0.5,
        },
    ]
    hit, note = pick_closest_linear_product(
        products, description="21897-1 TUBE", material="A36"
    )
    assert hit is None
    assert note and "no tenant SKU" in note


def test_assembly_root_and_tubes_classify_per_part(monkeypatch):
    from secturafab.push import SecturaFabPushService

    monkeypatch.setattr("secturafab.chrome_cdp.chrome_quotes_live", lambda *a, **k: True)
    classified, notes = SecturaFabPushService(client=MagicMock()).classify_cadimport_rows(
        [
            {
                "Name": "34887-1",
                "PartName": "34536 PIVOT TUBE, BOOM TIP_34536-1",
                "ID": "tube-1",
            },
            {
                "Name": "34887-1",
                "PartName": "34894 TUBE CYLINDER ANCHOR SUPPORT_34894-1",
                "ID": "tube-2",
            },
            {"Name": "Root", "PartName": "Root", "ItemType": "assembly", "ID": "asm"},
        ],
        default_material="A36",
        default_thickness="",
        bom_rows=[],
        library={},
        extra_pdfs=[],
        part_key="34887-1",
    )
    cats = [str(row.get("Category") or "") for row in classified]
    blob = "\n".join(notes)
    assert cats.count("Linear") == 2
    assert "Assembly" in cats
    assert "Assembly:" in blob
    assert "Cad: 15" not in blob


def test_keep_grid_thickness_flags_are_per_part():
    from secturafab.website import keep_grid_cad_kids_drawing_thickness_refuses

    why = keep_grid_cad_kids_drawing_thickness_refuses(
        [
            {
                "Name": "PLATE-A",
                "PartName": "111 PLATE",
                "Category": "Cad",
                "thickness_source": "step",
                "Thickness": 0.25,
                "Material": "A36",
            },
            {
                "Name": "GUSSET",
                "PartName": "222 GUSSET",
                "Category": "Cad",
                "thickness_source": "step",
                "Thickness": 0.25,
                "Material": "A36",
            },
        ],
        keep_via="live",
    )
    assert why
    assert why.count("FLAG: thickness unresolved") == 2
    assert "111 PLATE" in why and "222 GUSSET" in why
    assert "STEP-derived" in why


def test_pdf_stamp_overwrites_defaults_without_claiming_post(monkeypatch, tmp_path):
    from secturafab.push import SecturaFabPushService

    monkeypatch.setenv("SECTURA_WEBSITE_COOKIE", "ASP.NET_SessionId=box")
    monkeypatch.setattr("secturafab.chrome_cdp.chrome_quotes_live", lambda *a, **k: False)
    monkeypatch.setattr("secturafab.plate_ops.fetch_plate_catalog", lambda client: [])
    pdf = tmp_path / "10099.pdf"
    pdf.write_bytes(b"%PDF")
    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=box"
    client.upload_pdf_via_page_add_files.return_value = {
        "bound": True,
        "files_kendo": True,
        "upload_via": "page_add_files",
        "grid_pdf_row_count": 1,
        "status_gt0_n": 1,
    }
    client.stamp_pdf_kendo_flats.return_value = {
        "stamped": 1,
        "outside_perimeter_n": 0,
        "cutting_length_n": 0,
        "form_lw_synced": False,
    }
    client.quote_item_read.return_value = {"Data": []}
    client.get_json.return_value = {"ItemList": []}
    notes = SecturaFabPushService(client=client).finish_pdf_files(
        quote_id=_QID,
        pdf_files=[pdf],
        material="A36",
        thickness="0.076",
        qty=2,
        description="10099",
    )
    client.stamp_pdf_kendo_flats.assert_not_called()
    blob = "\n".join(notes)
    assert "AddItem_PDFFiles" not in blob
    assert "Stamped" not in blob
    assert "not inventing L/W" in blob
    assert "FLAG: PDF row" in blob


def test_linear_stamp_uses_onselect_and_records_real_status():
    from secturafab.chrome_cdp import _PAGE_LINEAR_FINISH_JS, _STAMP_LINEAR_FORM_JS

    picker = _STAMP_LINEAR_FORM_JS.split("function pickLinearSku")[1].split(
        "function findLinearConfigWidget"
    )[0]
    assert "ProductName" not in picker
    assert "rows[0]" not in _STAMP_LINEAR_FORM_JS
    assert "onSelect_Linear" in _STAMP_LINEAR_FORM_JS
    assert "#productType" not in _STAMP_LINEAR_FORM_JS
    assert "cap.status = 200" not in _PAGE_LINEAR_FINISH_JS
    assert "ret.always" in _PAGE_LINEAR_FINISH_JS


def test_nest_quote_edit_is_page_native(monkeypatch):
    from secturafab.client import SecturaFabApiError, SecturaFabClient

    monkeypatch.setattr("secturafab.chrome_cdp.chrome_quotes_live", lambda *a, **k: False)
    bare = SecturaFabClient.__new__(SecturaFabClient)
    with pytest.raises(SecturaFabApiError, match="OnNestQuote_Edit"):
        bare.nest_quote_edit(_QID)
    seen: dict[str, object] = {}

    def _invoke(**kwargs):
        seen.update(kwargs)
        return {"ok": True, "status": 200}

    monkeypatch.setattr("secturafab.chrome_cdp.chrome_quotes_live", lambda *a, **k: True)
    monkeypatch.setattr("secturafab.chrome_cdp.invoke_page_nest_quote_edit", _invoke)
    assert bare.nest_quote_edit(_QID, extra={"nestType": "multi"})["ok"] is True
    assert seen["quote_id"] == _QID
    assert seen["nest_type"] == "multi"


def test_add_assembly_accepts_discard_parts_confirm():
    assert "discard the parts" in PAGE_ADD_ASSEMBLY_JS


def test_qc_flags_linear_without_saw_op():
    from secturafab.quote_qc import check_tree

    linear = {
        "ItemNumber": "1008763-1",
        "ProductType": 40,
        "Category": "Linear",
        "Quantity": 1,
        "Length": 20,
        "Width": 4,
        "Length_Units": "inch",
        "Material": "A36",
        "Thickness": 0.25,
        "Thickness_Units": "inch",
        "UnitCost": 6.61,
        "UnitPrice": 6.61,
        "ErrorCount": 0,
        "OperationCostList": [{"OperationName": "Material"}],
    }
    flagged = check_tree({"Data": [linear]}, {"1008763-1": 1}, formed=[], label="long")
    assert any(flag.endswith("no Saw op") for flag in flagged.flags)
    linear["OperationCostList"] = [
        {"OperationName": "Saw"},
        {"OperationName": "Saw-Setup"},
    ]
    clear = check_tree({"Data": [linear]}, {"1008763-1": 1}, formed=[], label="long")
    assert not any(flag.endswith("no Saw op") for flag in clear.flags)


def test_drawing_gauge_is_not_divided_by_mm_grid_units():
    from secturafab.website import (
        overlay_classified_row,
        plate_step_thickness_invalid_vs_drawing,
    )

    out = overlay_classified_row(
        {
            "Name": "A-11521-000",
            "Category": "Component",
            "Thickness_Units": "millimeter",
            "Length": 952.5,
            "Width": 676.656,
        },
        category="Cad",
        material="A36",
        thickness="0.0747",
        thickness_source="drawing",
    )
    assert float(out["Thickness"]) == pytest.approx(0.0747)
    assert out["Thickness"] != pytest.approx(0.0029)
    assert out["Thickness_Units"] == "inch"
    assert plate_step_thickness_invalid_vs_drawing(out) is None


def test_tube_sku_without_drawing_wall_fails_closed():
    from secturafab.website import pick_closest_linear_product

    products = [
        {
            "ID": "rt",
            "ProductName": "RT3.5X0.065-A519",
            "ProductDescription": "Mechanical Tube",
            "ShapeName": "TUBE",
            "MaterialGrade": "A519",
            "Dim1": 3.5,
            "Dim2": 0.065,
            "Active": True,
        }
    ]
    best, note = pick_closest_linear_product(
        products, description="3 1/2 TUBE", material="A519"
    )
    assert best is None
    assert note and "wall" in note


def test_page_itemtype_linear_mismatch_refuses_finish(tmp_path, monkeypatch):
    """Classifier Linear that never lands on the page ItemType is not Finish."""
    from unittest.mock import patch

    from secturafab.push import SecturaFabPushService
    from secturafab.website import (
        STEP_CAD_FINISH_HARD_GATE_EXEC_FAIL,
        cad_finish_notes_refuse_additem_dxf,
    )

    monkeypatch.setattr("secturafab.chrome_cdp.chrome_quotes_live", lambda *a, **k: False)
    stp = tmp_path / "34887-1.STEP"
    stp.write_bytes(b"ISO")
    kids = [
        {
            "SourceDataID": "src-tube",
            "FileID": "file-tube",
            "ID": "id-tube",
            "Name": "34887-1",
            "PartName": "34536 PIVOT TUBE, BOOM TIP_34536-1",
            "Qty": 1,
            "ErrorStatus": 0,
            "Status": 1,
            "CadType": 0,
            "InternalData": "server-stamped",
            "ImageString": "iVBORw0KGgo",
        }
    ]
    client = MagicMock()
    client.upload_dxf_via_page_add_files.return_value = {
        "bound": True,
        "upload_via": "page_add_files",
        "files_kendo": True,
        "gridDXF_n": 1,
        "List": [{"SourceDataID": "src-step", "ID": "src-step", "Units": "inch"}],
    }
    client.create_all_parts_from_grid_dxf.return_value = {
        "via": "createAllParts",
        "invoked": True,
        "List": kids,
        "grid_present": True,
        "grid_dxf_row_count": 1,
        "list_len": 1,
        "internaldata_key_n": 1,
        "internaldata_empty_n": 0,
        "internaldata_nonempty_n": 1,
    }
    client._grid_present = True
    client._grid_dxf_row_count = 1
    client._stale_grid = False
    client._edit_quote_id = _QID
    client._edit_gate = ""
    client.get_item_add_view.return_value = {}
    client.quote_item_read.return_value = {"Data": [], "Total": 0}
    client.get_json.return_value = {"ItemList": []}
    with patch(
        "secturafab.chrome_cdp.apply_grid_dxf_part_modes",
        return_value={
            "grid_present": True,
            "cad": 1,
            "linear": 0,
            "itemtype_cad": 1,
            "itemtype_linear": 0,
            "assembly": 0,
            "component": 0,
            "set_count": 1,
            "setpartmode_via": "page_fn",
            "updateitemtype_via": "dropdown",
            "updateitemtype_count": 1,
            "grid_dxf_row_count": 1,
        },
    ):
        notes = SecturaFabPushService(client=client).finish_cad_files(
            quote_id=_QID,
            cad_files=[stp],
            material="A36",
            thickness="0.25",
            qty=1,
            takeoff={},
            bom_rows=[],
            library={},
            extra_pdfs=None,
            part_key="34887-1",
            explode_polls=1,
            explode_sleep_s=0,
        )
    blob = " ".join(notes)
    assert "grid ItemType Linear 0" in blob
    assert "classifier Linear 1" in blob
    assert STEP_CAD_FINISH_HARD_GATE_EXEC_FAIL in blob
    assert cad_finish_notes_refuse_additem_dxf(notes)
    client.add_item_dxf_files.assert_not_called()


def test_apply_fields_leaves_product_type_to_the_page_dropdown():
    from secturafab.chrome_cdp import _APPLY_GRID_PART_MODES_JS

    fn = _APPLY_GRID_PART_MODES_JS.split("function applyFields")[1].split(
        "function force_live_grid_inch"
    )[0]
    cad = fn.split('if (cat === "Cad")')[1].split("else if")[0]
    assert "ProductType" not in cad
    assert "ProductSubType" not in cad
    assert "ItemType" not in cad
    assert "Machine" not in cad
    assert 'kendoModelSet(row, "ProductType", 100)' not in fn
    assert "row.ProductType = 100" not in fn


def test_linear_stamp_uses_linear_product_and_waits_for_subtype():
    from secturafab.chrome_cdp import _STAMP_LINEAR_FORM_JS

    finder = _STAMP_LINEAR_FORM_JS.split("function findLinearProductWidget")[1].split(
        "function pickLinearSku"
    )[0]
    assert "#LinearProduct" in finder
    assert "#gridSelectProductLinear" not in finder
    assert "waitProductSubTypeReload" in _STAMP_LINEAR_FORM_JS
    assert "dataBound" in _STAMP_LINEAR_FORM_JS


def test_add_item_linear_does_not_click_when_stamp_fails(monkeypatch):
    from secturafab.client import SecturaFabClient

    client = SecturaFabClient.__new__(SecturaFabClient)
    client._af_source = "chrome_dom"
    client.config = object()
    client.harvest_chrome_antiforgery = lambda: None
    monkeypatch.setattr(
        "secturafab.browser_session.effective_website_cookie",
        lambda *a, **k: True,
    )
    clicked = {"n": 0}

    monkeypatch.setattr("secturafab.chrome_cdp.chrome_quotes_live", lambda *a, **k: True)
    monkeypatch.setattr(
        "secturafab.chrome_cdp.minted_edit_tab_ready",
        lambda *a, **k: {"ok": True, "tab": {}},
    )
    monkeypatch.setattr(
        "secturafab.chrome_cdp.invoke_page_linear_finish",
        lambda **k: clicked.__setitem__("n", clicked["n"] + 1) or {"ok": True},
    )
    monkeypatch.setattr(
        client,
        "stamp_linear_form",
        lambda **k: {"ok": False, "picker_via": "#gridSelectProductLinear", "opened_via": "#but_bar"},
    )
    cap = client.add_item_linear(quote_id=_QID, product_id="pid", name="TUBE", length=10)
    assert clicked["n"] == 0
    assert cap["ok"] is False
    assert cap["finish_why"] == "stamp_linear_form_not_ok"


def test_renest_checks_every_nest_task():
    from unittest.mock import MagicMock, patch

    from secturafab.push import SecturaFabPushService

    tube_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    channel_id = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
    calls: list[str] = []

    def _get(path: str):
        calls.append(path)
        if "quoteID=" in path:
            return {"Results": [{"ID": tube_id}, {"ID": channel_id}]}
        if path.endswith(tube_id):
            return {"StockList": [{"SheetSizeLength": 240}]}
        if path.endswith(channel_id):
            if any("RenestLinear" in c or c == "renest" for c in calls):
                return {"StockList": [{"SheetSizeLength": 240}]}
            return {
                "ProductID": "73097795-5384-486c-8eab-b32a6593c0ba",
                "StockList": [{"SheetSizeLength": 240}, {"SheetSizeLength": 480}],
            }
        return {"ItemList": [], "StockList": []}

    client = MagicMock()
    client.nest_quote_edit.return_value = {}
    client.get_json.side_effect = _get
    client.read_data_linear_lookup.return_value = {"List": []}

    def _renest(*args, **kwargs):
        calls.append("renest")
        extra = kwargs.get("extra") or {}
        calls.append(str(extra.get("NestTaskID") or ""))
        return {}

    client.renest_linear.side_effect = _renest
    with patch("secturafab.quote_update.quote_online_update", return_value=True), patch(
        "secturafab.chrome_cdp.page_jquery_ajax",
        return_value={
            "ok": True,
            "body": [
                {
                    "ID": "00f8b766-a818-42f9-bcfa-1e4da59acefc",
                    "Length": 20,
                    "Length_Unit": "foot",
                },
                {
                    "ID": "d503d7e9-20d3-4029-872f-839dae144007",
                    "Length": 40,
                    "Length_Unit": "foot",
                },
            ],
        },
    ) as looked:
        notes = SecturaFabPushService(client=client).nest_after_finish(
            "qid-two", item_count=2
        )
    looked.assert_called_once()
    assert "73097795-5384-486c-8eab-b32a6593c0ba" in looked.call_args.kwargs["url"]
    client.read_data_linear_lookup.assert_not_called()
    assert client.renest_linear.call_count == 1
    payload = client.renest_linear.call_args.kwargs.get("extra") or {}
    assert payload.get("NestTaskID") == channel_id
    assert payload.get("ChuckSize") == 0.0
    assert payload.get("ChuckSize_Units") == "inch"
    checked = [row for row in payload.get("LengthList") or [] if row.get("Checked")]
    assert checked and checked[0]["ID"] == "00f8b766-a818-42f9-bcfa-1e4da59acefc"
    assert checked[0]["Length"] == 20
    assert checked[0]["Length_Units"] == "foot"
    assert any("RenestLinear" in n for n in notes)


def test_qc_ignores_sku_suffix_linear_width_and_non_weldment():
    from secturafab.quote_qc import check_tree

    tube = {
        "ItemNumber": "1020243-1 - RCT5X4X3/16-A500",
        "ProductType": 30,
        "Category": "Linear",
        "Quantity": 1,
        "Length": 45.1875,
        "Width": 0,
        "Length_Units": "inch",
        "Material": "A500",
        "Thickness": 0.1875,
        "Thickness_Units": "inch",
        "UnitCost": 56.46,
        "UnitPrice": 56.46,
        "ErrorCount": 0,
        "OperationCostList": [{"OperationName": "Saw"}],
    }
    channel = dict(tube)
    channel["ItemNumber"] = "1008763-1 - C4X5.4-A36"
    channel["ProductType"] = 40
    channel["Length"] = 26.6875
    channel["UnitCost"] = 6.61
    channel["UnitPrice"] = 6.61
    report = check_tree(
        {"Data": [tube, channel]},
        {"1020243-1": 1, "1008763-1": 1},
        formed=[],
        label="linear",
    )
    blob = "\n".join(report.flags)
    assert "part list mismatch" not in blob
    assert "implausible dims" not in blob
    assert "weldment has no parent line" not in blob


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


def test_page_cad_posts_updateitemtype_once_then_gauge():
    from secturafab.chrome_cdp import _PAGE_FINISH_JS

    native = _PAGE_FINISH_JS.split("function applyPageNativeCadThickness")[1].split(
        "function skipFinish"
    )[0]
    assert native.count('ddl.value("cad")') == 1
    assert native.count('ddl.trigger("change")') == 1
    assert 'already !== "cad"' in native
    assert "#MaterialEdit_Cad" in native
    trigger_at = native.index('ddl.trigger("change")')
    material_at = native.index("setMaterialCad(row)", trigger_at)
    assert trigger_at < material_at < native.index("cb.select(idx)")
    assert "flat_over_120" in native
    assert native.index("convertMmGrid(row)") < native.index("flatOver120(row)")


def test_apply_grid_pins_every_live_row():
    from secturafab.chrome_cdp import _APPLY_GRID_PART_MODES_JS

    js = _APPLY_GRID_PART_MODES_JS
    assert "rowPart" in js
    assert "pinned.PartID" in js
    loop = js.split("for (var i = 0; i < data.length; i++)")[1].split("if (!kids.length)")[0]
    assert "queueWant(pinned, rowPart" in loop
    match = js.split("function matchWant")[1].split("function wantFromName")[0]
    assert "sourceHit" in match
    assert match.index("wname && name && wname === name") < match.index("sourceHit = w")


def test_flat_over_120_refuses_labeled_inch_mm_grid():
    from secturafab.website import (
        cad_finish_notes_refuse_additem_dxf,
        cad_flat_over_120_refuses,
        convert_mm_grid_flats_to_inches,
    )

    labeled = {
        "Name": "plate",
        "Length": 952.5,
        "Width": 676.5,
        "Length_Units": "inch",
        "Width_Units": "inch",
        "Thickness": 0.076,
        "Thickness_Units": "inch",
    }
    why = cad_flat_over_120_refuses(labeled)
    assert why and "952.5" in why
    assert cad_finish_notes_refuse_additem_dxf([why])
    assert labeled["Length"] == 952.5
    real_mm = {
        "Name": "plate",
        "Length": 952.5,
        "Width": 676.5,
        "Length_Units": "mm",
        "Width_Units": "mm",
    }
    assert convert_mm_grid_flats_to_inches(real_mm) is None
    assert cad_flat_over_120_refuses(real_mm) is None
    assert real_mm["Length"] == pytest.approx(37.5, rel=1e-3)


def test_linear_stamp_waits_for_linear_product():
    from secturafab.chrome_cdp import _STAMP_LINEAR_FORM_JS

    picker = _STAMP_LINEAR_FORM_JS.split("function pickLinearSku")[1].split(
        "function findLinearConfigWidget"
    )[0]
    assert "waitForLinearProduct" in picker
    assert "8000" in picker
    assert "3000" in picker
    assert "none_linear_widget" in picker
    assert picker.index("waitForLinearProduct") < picker.index("none_linear_widget")


def test_nest_skips_when_linear_finish_produced_no_lines():
    from secturafab.push import SecturaFabPushService

    client = MagicMock()
    notes = SecturaFabPushService(client=client).nest_after_finish("qid", item_count=0)
    assert notes == ["Nest skipped — linear finish produced 0 lines"]
    client.nest_quote_edit.assert_not_called()
    client.renest_linear.assert_not_called()


def test_get_linear_config_error_is_not_swallowed():
    from unittest.mock import patch

    from secturafab.client import SecturaFabApiError
    from secturafab.push import SecturaFabPushService

    client = MagicMock()
    client.nest_quote_edit.return_value = {}
    nest_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    client.get_json.side_effect = [
        {"Results": [{"ID": nest_id, "SheetSizeLength": 480, "ProductID": "pid-1"}]},
        {"ProductID": "pid-1", "StockList": [{"StockLength": 480}]},
        {"ItemList": []},
    ]
    with patch(
        "secturafab.chrome_cdp.page_jquery_ajax",
        return_value={"ok": False, "why": "wrong_document"},
    ), pytest.raises(SecturaFabApiError, match="GetLinearConfig failed"):
        SecturaFabPushService(client=client).nest_after_finish("qid", item_count=1)
    client.renest_linear.assert_not_called()
    client.read_data_linear_lookup.assert_not_called()


def test_pdf_skip_does_not_warn_form_lw_synced():
    from secturafab.website import finish_empty_filelist_after_good_stamp_is_fail

    skipped = {
        "finish_filelist_n": 0,
        "getpdfdata_n": 0,
        "finish_why": "empty_perimeter",
    }
    assert finish_empty_filelist_after_good_stamp_is_fail(skipped, None) is False
    assert (
        finish_empty_filelist_after_good_stamp_is_fail(
            skipped, {"form_lw_synced": False, "outside_perimeter_n": 0}
        )
        is False
    )


def test_saw_and_laser_pack_qc_guards_stay():
    from secturafab.quote_qc import check_tree
    from secturafab.website import step_finish_pack_missing

    src_qc = Path("secturafab/quote_qc.py").read_text(encoding="utf-8")
    src_web = Path("secturafab/website.py").read_text(encoding="utf-8")
    assert "no Saw op" in src_qc
    assert "Cad PR+laser pack missing after Finish" in src_web
    report = check_tree(
        {
            "Data": [
                {
                    "ItemNumber": "1020243-1",
                    "ProductType": 30,
                    "Category": "Linear",
                    "Quantity": 1,
                    "Length": 45,
                    "Length_Units": "inch",
                    "UnitPrice": 56.46,
                    "OperationCostList": [],
                }
            ]
        },
        {"1020243-1": 1},
        formed=[],
        label="Q",
    )
    assert any("no Saw op" in flag for flag in report.flags)
    assert step_finish_pack_missing is not None


def test_apply_grid_wrapper_returns_itemtype_counts(monkeypatch):
    """Live 3a: the page counted Linear 3; the wrapper must not drop it."""
    from secturafab.chrome_cdp import apply_grid_dxf_part_modes

    monkeypatch.setattr(
        "secturafab.chrome_cdp.minted_edit_tab_ready",
        lambda *a, **k: {
            "ok": True,
            "tab": {"webSocketDebuggerUrl": "ws://edit"},
            "edit_quote_id": _QID,
            "minted_id": _QID,
            "reason": "",
        },
    )

    def _eval(*a, **k):
        return {
            "grid_present": True,
            "cad": 10,
            "linear": 3,
            "assembly": 1,
            "component": 1,
            "itemtype_cad": 10,
            "itemtype_linear": 3,
            "set_count": 14,
            "setpartmode_via": "page_fn",
            "updateitemtype_count": 14,
            "updateitemtype_via": "dropdown",
            "grid_dxf_row_count": 14,
        }

    monkeypatch.setattr("secturafab.chrome_cdp._cdp_evaluate_promise", _eval)
    out = apply_grid_dxf_part_modes(
        [{"Category": "Linear", "Name": "34536 PIVOT TUBE"}],
        quote_id=_QID,
    )
    assert out["itemtype_linear"] == 3
    assert out["itemtype_cad"] == 10
    assert out["updateitemtype_via"] == "dropdown"


def test_matching_itemtype_linear_does_not_false_refuse(tmp_path, monkeypatch):
    """Classifier Linear 1 and grid ItemType Linear 1 is not the 3a refuse."""
    from unittest.mock import patch

    from secturafab.push import SecturaFabPushService

    monkeypatch.setattr("secturafab.chrome_cdp.chrome_quotes_live", lambda *a, **k: False)
    stp = tmp_path / "34887-1.STEP"
    stp.write_bytes(b"ISO")
    kids = [
        {
            "SourceDataID": "src-tube",
            "FileID": "file-tube",
            "ID": "id-tube",
            "Name": "34887-1",
            "PartName": "34536 PIVOT TUBE, BOOM TIP_34536-1",
            "Qty": 1,
            "ErrorStatus": 0,
            "Status": 1,
            "CadType": 0,
            "InternalData": "server-stamped",
            "ImageString": "iVBORw0KGgo",
        }
    ]
    client = MagicMock()
    client.upload_dxf_via_page_add_files.return_value = {
        "bound": True,
        "upload_via": "page_add_files",
        "files_kendo": True,
        "gridDXF_n": 1,
        "List": [{"SourceDataID": "src-step", "ID": "src-step", "Units": "inch"}],
    }
    client.create_all_parts_from_grid_dxf.return_value = {
        "via": "createAllParts",
        "invoked": True,
        "List": kids,
        "grid_present": True,
        "grid_dxf_row_count": 1,
        "list_len": 1,
        "internaldata_key_n": 1,
        "internaldata_empty_n": 0,
        "internaldata_nonempty_n": 1,
    }
    client._grid_present = True
    client._grid_dxf_row_count = 1
    client._stale_grid = False
    client._edit_quote_id = _QID
    client._edit_gate = ""
    client.get_item_add_view.return_value = {}
    client.quote_item_read.return_value = {"Data": [], "Total": 0}
    client.get_json.return_value = {"ItemList": []}
    with patch(
        "secturafab.chrome_cdp.apply_grid_dxf_part_modes",
        return_value={
            "grid_present": True,
            "cad": 0,
            "linear": 1,
            "itemtype_cad": 0,
            "itemtype_linear": 1,
            "assembly": 0,
            "component": 0,
            "set_count": 1,
            "setpartmode_via": "page_fn",
            "updateitemtype_via": "dropdown",
            "updateitemtype_count": 1,
            "grid_dxf_row_count": 1,
        },
    ):
        notes = SecturaFabPushService(client=client).finish_cad_files(
            quote_id=_QID,
            cad_files=[stp],
            material="A36",
            thickness="0.25",
            qty=1,
            takeoff={},
            bom_rows=[],
            library={},
            extra_pdfs=None,
            part_key="34887-1",
            explode_polls=1,
            explode_sleep_s=0,
        )
    blob = " ".join(notes)
    assert "grid ItemType Linear 0" not in blob
    assert "kyle_classify_before_finish=true" in blob


def test_linear_add_omits_internal_and_length_suffix():
    """Gold OnAddLinearClick: no Internal key, name is PN - SKU."""
    from secturafab.chrome_cdp import _PAGE_LINEAR_FINISH_JS, _STAMP_LINEAR_FORM_JS
    from secturafab.item_desc import linear_additem_name
    from secturafab.website import LINEAR_ADD_FIELDS, build_linear_add_payload

    plain = linear_additem_name(
        "1020243-1", sku="RCT5X4X3/16-A500", noun="TUBE"
    )
    assert plain == "1020243-1 - RCT5X4X3/16-A500"
    assert "45.188" not in plain
    extra = {
        "productConfigID": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        "productSubType": "tube_rect",
        "dim1": 5,
        "dim2": 4,
        "dim3": 0.1875,
        "dim4": "",
        "weightLength": 9.99,
        "sku": "RCT5X4X3/16-A500",
    }
    payload = build_linear_add_payload(
        "qid",
        product_id="pid-tube",
        qty=1,
        length=45.1875,
        name=plain,
        extra=extra,
    )
    assert "Internal" not in payload
    assert "Internal" not in LINEAR_ADD_FIELDS
    assert payload["name"] == "1020243-1 - RCT5X4X3/16-A500"
    assert payload["length"] == 45.1875
    assert payload["productConfigID"] == extra["productConfigID"]
    assert "#Internal" not in _STAMP_LINEAR_FORM_JS
    assert "delete opts.data.Internal" in _PAGE_LINEAR_FINISH_JS
    assert 'opts.data.Internal = ""' not in _PAGE_LINEAR_FINISH_JS
    assert ' - "' in _PAGE_LINEAR_FINISH_JS


def test_second_long_resets_linear_product_before_search():
    from secturafab.chrome_cdp import _STAMP_LINEAR_FORM_JS

    picker = _STAMP_LINEAR_FORM_JS.split("function pickLinearSku")[1].split(
        "function findLinearConfigWidget"
    )[0]
    assert "resetLinearAutocomplete" in picker
    assert 'widget.value("")' in picker
    assert "waitLinearDataSource" in picker
    assert "dataBound" in picker
    assert picker.index("resetLinearAutocomplete") < picker.index("exactIndex(data")
    assert picker.index("w.open") < picker.index("exactIndex(data")
    config = _STAMP_LINEAR_FORM_JS.split("function pickLinearConfig20ft")[1].split(
        "var lastPicker"
    )[0]
    assert "dataSource.read" in config
    assert "20 ft" in _STAMP_LINEAR_FORM_JS
    assert 'lastConfigVia = "none"' in _STAMP_LINEAR_FORM_JS
    assert "ok: !!picked," in _STAMP_LINEAR_FORM_JS
    assert "ok: !!picked && !!cfg" not in _STAMP_LINEAR_FORM_JS


def test_push_job_overrides_win_and_missing_org_fails_closed(tmp_path, monkeypatch):
    from secturafab.push import SecturaFabPushService

    stp = tmp_path / "ZZ-OVERRIDE.step"
    stp.write_text(_OCC_INCH, encoding="utf-8")
    monkeypatch.setattr(
        "secturafab.push.collect_job_files",
        lambda **kwargs: ([], [stp]),
    )
    monkeypatch.setattr("secturafab.chrome_cdp.chrome_quotes_live", lambda *a, **k: False)
    monkeypatch.setattr("secturafab.chrome_cdp.quotes_tab", lambda *a, **k: None)
    monkeypatch.setattr("secturafab.chrome_cdp.chrome_session_lost", lambda *a, **k: False)
    monkeypatch.setattr("secturafab.push.refresh_bom_rows_for_push", lambda *a, **k: ([], []))
    monkeypatch.setattr(
        "secturafab.push.detect_organization",
        lambda **kwargs: "Time Manufacturing Waco",
    )
    client = MagicMock()
    client.config.website_cookie = "ASP.NET_SessionId=test"
    client.get_json.return_value = {"ItemList": [], "ItemCount": 0}
    service = SecturaFabPushService(client=client)
    created: dict[str, object] = {}

    def _create(**kwargs):
        created.update(kwargs)
        return "qid-override"

    monkeypatch.setattr(service, "create_quote", _create)
    monkeypatch.setattr(service, "allocate_quote_number", lambda *a, **k: "SHOULD-NOT-WIN")
    monkeypatch.setattr(service, "upload_drawings_quote_request", lambda *a, **k: None)
    monkeypatch.setattr(service, "find_quote_by_number", lambda *a, **k: None)
    monkeypatch.setattr(service, "finish_cad_files", lambda **k: ["Finish stopped for the test"])
    monkeypatch.setattr(service, "apply_item_categories", lambda *a, **k: [])
    monkeypatch.setattr("secturafab.push.apply_quote_organization", lambda *a, **k: [])

    overridden = service.push_job(
        title="ZZ-OVERRIDE",
        pdf_filename=None,
        pdf_path=None,
        stp_path=stp,
        takeoff={"library": {"part_key": "ZZ-OVERRIDE"}},
        times={},
        organization="Safe Cave",
        quote_number="ZZ-OVERRIDE-TEST",
    )
    assert created["organization_name"] == "Safe Cave"
    assert created["quote_number"] == "ZZ-OVERRIDE-TEST"
    assert created.get("organization_id") in (None, "")
    assert "organization_override=Safe Cave" in overridden.notes

    created.clear()
    time_job = service.push_job(
        title="21684-1",
        pdf_filename=None,
        pdf_path=None,
        stp_path=stp,
        takeoff={"library": {"part_key": "21684-1"}},
        times={},
    )
    assert created["organization_name"] == "Time Manufacturing Waco"
    assert "organization_override=" not in " ".join(time_job.notes)

    created.clear()
    monkeypatch.setattr("secturafab.push.detect_organization", lambda **kwargs: None)
    missing = service.push_job(
        title="NO-ORG",
        pdf_filename=None,
        pdf_path=None,
        stp_path=stp,
        takeoff={"library": {"part_key": "NO-ORG"}},
        times={},
    )
    assert missing.ok is False
    assert "not creating the quote" in (missing.error or "")
    assert "organization_name" not in created


def test_refused_finish_does_not_claim_additem_post(tmp_path):
    """flat_over_120 skipped the POST — do not say Finish POST or empty body."""
    from unittest.mock import patch

    from secturafab.push import SecturaFabPushService, cad_finish_refused_before_post

    assert cad_finish_refused_before_post(
        {"finish_why": "flat_over_120"}, "skipped"
    )
    assert not cad_finish_refused_before_post(
        {"finish_why": "flat_over_120", "finish_fn": "OnAddDXFClick"},
        "page_fn",
    )
    stp = tmp_path / "mm.STEP"
    stp.write_bytes(b"ISO")
    kids = [
        {
            "SourceDataID": "src-1",
            "FileID": "file-1",
            "ID": "id-1",
            "Name": "PLATE",
            "Qty": 1,
            "ErrorStatus": 0,
            "Status": 1,
            "CadType": 0,
            "Stock_X": 11.0,
            "Stock_Y": 6.25,
            "Length": 6.25,
            "Width": 11.0,
            "Thickness": 0.105,
            "Thickness_Units": "inch",
            "Material": "A36",
            "ProductType": 100,
            "Category": "Cad",
            "PartMode": 0,
            "InternalData": "server-stamped",
            "ImageString": "iVBORw0KGgo",
        }
    ]
    client = MagicMock()
    client.upload_dxf_via_page_add_files.return_value = {
        "bound": True,
        "upload_via": "page_add_files",
        "files_kendo": True,
        "gridDXF_n": 1,
        "List": [{"SourceDataID": "src-step", "ID": "src-step", "Units": "inch"}],
    }
    client.create_all_parts_from_grid_dxf.return_value = {
        "via": "createAllParts",
        "invoked": True,
        "List": kids,
        "grid_present": True,
        "grid_dxf_row_count": 1,
        "list_len": 1,
    }
    client._grid_present = True
    client._grid_dxf_row_count = 1
    client._stale_grid = False
    client._edit_quote_id = _QID
    client._edit_gate = ""
    client._finish_via = "skipped"
    client._setpartmode_via = "page_fn"
    client.get_item_add_view.return_value = {}
    client.quote_item_read.return_value = {"Data": [], "Total": 0}
    client.get_json.return_value = {"ItemList": []}
    client.add_item_dxf_files.return_value = {
        "status": 0,
        "via": "skipped",
        "finish_fn": "",
        "finish_why": "flat_over_120",
        "finish_filelist_n": 0,
        "empty_body": True,
        "body_type": "empty",
        "body_keys": [],
        "has_NewItem": False,
        "grid_dxf_row_count": 2,
        "filelist_sourcedataid_n": 0,
        "filelist_from_kendo": False,
        "finish_af_present": False,
    }
    with patch(
        "secturafab.chrome_cdp.apply_grid_dxf_part_modes",
        return_value={
            "grid_present": True,
            "cad": 1,
            "linear": 0,
            "itemtype_cad": 1,
            "itemtype_linear": 0,
            "assembly": 0,
            "component": 0,
            "set_count": 1,
            "setpartmode_via": "page_fn",
            "updateitemtype_via": "page_fn",
            "updateitemtype_count": 1,
            "grid_dxf_row_count": 1,
            "cad_blank_material": 0,
            "producttype_still_component": 0,
        },
    ):
        notes = SecturaFabPushService(client=client).finish_cad_files(
            quote_id=_QID,
            cad_files=[stp],
            material="A36",
            thickness="0.105",
            qty=1,
            takeoff={},
            bom_rows=[],
            library={},
            extra_pdfs=None,
            part_key="MM-PLATE",
            explode_polls=1,
            explode_sleep_s=0,
        )
    blob = " ".join(notes)
    assert client.add_item_dxf_files.called
    assert "finish_why=flat_over_120" in blob
    assert "Finish POST /Quote/AddItem_DXFFiles" not in blob
    assert "empty body" not in blob.lower()
    assert "posted FileList lacks FileType" not in blob


def test_collect_keeps_every_step_in_the_part_folder(tmp_path: Path):
    from secturafab.push import collect_job_files

    folder = tmp_path / "inch"
    folder.mkdir()
    first = folder / "A-11521-000.step"
    second = folder / "A-11513-000.step"
    first.write_bytes(b"ISO")
    second.write_bytes(b"ISO")
    _drawings, cad = collect_job_files(
        pdf_path=None,
        stp_path=first,
        library={"folder": str(folder)},
    )
    assert [p.name for p in cad] == ["A-11521-000.step", "A-11513-000.step"]


def test_upload_dxf_posts_each_step_file(tmp_path):
    from secturafab.chrome_cdp import upload_dxf_via_page_add_files

    first = tmp_path / "A-11521-000.step"
    second = tmp_path / "A-11513-000.step"
    first.write_bytes(b"ISO")
    second.write_bytes(b"ISO")
    sets: list[list[str]] = []
    tab = {
        "title": "*Quote-ZZ",
        "url": "https://www.secturafab.com/Quote/EDIT/qid",
        "webSocketDebuggerUrl": "ws://127.0.0.1:9224/devtools/page/edit",
        "type": "page",
    }

    def _set(_ws, _selector, paths):
        sets.append(list(paths))
        return "objectId"

    def _eval(expr, **kwargs):
        if "opened_via" in expr:
            return {"opened_via": "AddNewItemHTML"}
        if "dropZoneElement" in expr:
            return {
                "selector": "#dxfupload_Zone #files",
                "files_kendo": True,
                "save_url": "/CadImport/UploadItem_DXFFiles",
                "zone": "#dxfupload_Zone",
                "grid_id": "#gridDXF",
            }
        if "gridDXF" in expr:
            return {
                "grid_id": "#gridDXF",
                "gridDXF_n": len(sets),
                "files_kendo": True,
                "List": [{"FileName": Path(p).name} for batch in sets for p in batch],
                "save_url": "/CadImport/UploadItem_DXFFiles",
            }
        return {"changed": True, "files_kendo": True, "file_n": 1}

    with patch(
        "secturafab.chrome_cdp.minted_edit_tab_ready",
        return_value={"ok": True, "tab": tab, "reason": ""},
    ), patch(
        "secturafab.chrome_cdp._cdp_set_file_input_files", side_effect=_set
    ), patch(
        "secturafab.chrome_cdp._cdp_evaluate_promise", side_effect=_eval
    ), patch("secturafab.chrome_cdp.time.sleep"):
        result = upload_dxf_via_page_add_files(
            [first, second], quote_id="11111111-aaaa-bbbb-cccc-000000000086"
        )
    assert result["bound"] is True
    assert result["gridDXF_n"] == 2
    assert sets == [[str(first.resolve())], [str(second.resolve())]]
    assert result["finish_why"] != "partial_upload"


def test_header_persist_keeps_explicit_number_and_skips_weld_note():
    from quote_core.drawing_title import extract_title_from_pdf_text, is_drawing_boilerplate_title
    from secturafab.push import minted_header_for_persist

    note = "1. ALL WELDS FULL LENGTH UNLESS"
    assert is_drawing_boilerplate_title(note) is True
    assert (
        extract_title_from_pdf_text(
            note + "\nDW WINCH BOX FRONT\n",
            part_key="A-11521-000",
        )
        == "DW WINCH BOX FRONT"
    )
    number, desc = minted_header_for_persist(
        quote_number="ZZ-WELD-TEST-602",
        description="DW WINCH BOX FRONT",
        part_key="11521-000",
    )
    assert number == "ZZ-WELD-TEST-602"
    assert desc == "DW WINCH BOX FRONT"
    _number, cleared = minted_header_for_persist(
        quote_number="ZZ-WELD-TEST-602",
        description=note,
        part_key="11521-000",
    )
    assert cleared == ""
    explicit_number, explicit_desc = minted_header_for_persist(
        quote_number="ZZ-WELD-TEST-602",
        description=note,
        part_key="11521-000",
        description_explicit=True,
    )
    assert explicit_number == "ZZ-WELD-TEST-602"
    assert explicit_desc == note
    real_number, _real_desc = minted_header_for_persist(
        quote_number="A-11521-000",
        description="DW WINCH BOX FRONT",
        part_key="11521-000",
    )
    assert real_number == "A-11521-000"


def test_one_step_thickness_kid_does_not_refuse_the_others():
    from secturafab.website import (
        cad_finish_notes_refuse_additem_dxf,
        rows_keeping_resolved_thickness,
    )

    good = {
        "Name": "34890 PLATE",
        "PartName": "34890 PLATE",
        "Category": "Cad",
        "Material": "A36",
        "Thickness": 0.25,
        "thickness_source": "drawing",
        "drawing_thickness_in": 0.25,
    }
    bad = {
        "Name": "34892 BOTTOM PLATE",
        "PartName": "34892 BOTTOM PLATE",
        "Category": "Cad",
        "Material": "A36",
        "Thickness": 0.25,
        "thickness_source": "step",
    }
    tube = {"Name": "34536 PIVOT TUBE", "Category": "Linear", "Material": "A36"}
    kept, flags = rows_keeping_resolved_thickness(
        [good, bad, tube], keep_via="live"
    )
    assert [row["Name"] for row in kept] == ["34890 PLATE", "34536 PIVOT TUBE"]
    assert len(flags) == 1
    assert "34892" in flags[0]
    assert flags[0].startswith("FLAG: thickness unresolved")
    assert cad_finish_notes_refuse_additem_dxf(flags) is None
    from secturafab.website import thickness_flag_label

    assert thickness_flag_label(flags[0]) == "34892 BOTTOM PLATE"


def test_flagged_thickness_kid_is_dropped_from_the_page_grid(monkeypatch):
    from secturafab.chrome_cdp import (
        _DROP_FLAGGED_GRID_PARTS_JS,
        drop_flagged_grid_dxf_parts,
    )

    assert "#gridDXFParts" in _DROP_FLAGGED_GRID_PARTS_JS
    assert "dataSource.remove" in _DROP_FLAGGED_GRID_PARTS_JS
    monkeypatch.setattr(
        "secturafab.chrome_cdp.chrome_quotes_live", lambda *_a, **_k: False
    )
    quiet = drop_flagged_grid_dxf_parts(["34892 BOTTOM PLATE"], quote_id="qid")
    assert quiet["live"] is False
    assert quiet["still"] == []
    seen: dict[str, str] = {}

    def _eval(expr, **_kwargs):
        seen["expr"] = expr
        return {
            "ok": False,
            "removed": 0,
            "still": ["34892 BOTTOM PLATE"],
            "why": "still_on_grid",
        }

    monkeypatch.setattr(
        "secturafab.chrome_cdp.chrome_quotes_live", lambda *_a, **_k: True
    )
    monkeypatch.setattr(
        "secturafab.chrome_cdp.minted_edit_tab_ready",
        lambda *_a, **_k: {
            "ok": True,
            "tab": {"webSocketDebuggerUrl": "ws://127.0.0.1/devtools/page/edit"},
        },
    )
    monkeypatch.setattr("secturafab.chrome_cdp._cdp_evaluate_promise", _eval)
    blocked = drop_flagged_grid_dxf_parts(
        ["34892 BOTTOM PLATE"], quote_id="qid"
    )
    assert "34892 BOTTOM PLATE" in seen["expr"]
    assert blocked["live"] is True
    assert blocked["ok"] is False
    assert blocked["still"] == ["34892 BOTTOM PLATE"]


def test_page_session_runs_image_and_long_without_env_cookie(tmp_path, monkeypatch):
    from secturafab.push import SecturaFabPushService

    pdf = tmp_path / "10099.pdf"
    pdf.write_bytes(b"%PDF")
    monkeypatch.setattr("secturafab.push.detect_organization", lambda **_k: "Safe Cave")
    monkeypatch.setattr("secturafab.chrome_cdp.chrome_quotes_live", lambda *_a, **_k: True)
    monkeypatch.setattr("secturafab.chrome_cdp.quotes_tab", lambda *_a, **_k: None)
    monkeypatch.setattr("secturafab.chrome_cdp.chrome_session_lost", lambda *_a, **_k: False)
    monkeypatch.setattr("secturafab.push.refresh_bom_rows_for_push", lambda *_a, **_k: ([], []))
    monkeypatch.setattr("secturafab.push.extract_assembly_description", lambda **_k: None)
    monkeypatch.setattr(
        "secturafab.push.apply_quote_organization",
        lambda *_a, **_k: ["Set Organization: Safe Cave"],
    )
    client = MagicMock()
    client.config.website_cookie = ""
    client.get_json.return_value = {
        "ItemList": [],
        "ItemCount": 0,
        "OrganizationName": "Safe Cave",
        "PrimaryOrganizationID": "11111111-1111-4111-8111-111111111111",
    }
    service = SecturaFabPushService(client=client)
    called: dict[str, bool] = {}
    monkeypatch.setattr(service, "create_quote", lambda **_k: "qid")
    monkeypatch.setattr(service, "allocate_quote_number", lambda *_a, **_k: "10099")
    monkeypatch.setattr(service, "upload_drawings_quote_request", lambda *_a, **_k: "qr")
    monkeypatch.setattr(service, "preflight_website_addview_session", lambda: (True, []))
    monkeypatch.setattr(service, "_page_session_live", lambda: True)
    monkeypatch.setattr(service, "_website_cookie_present", lambda: False)

    def _pdf(**_k):
        called["pdf"] = True
        return ["Image Files"]

    def _lin(**_k):
        called["lin"] = True
        return ["Long"]

    monkeypatch.setattr(service, "finish_pdf_files", _pdf)
    monkeypatch.setattr(service, "finish_linear_bom_rows", _lin)
    monkeypatch.setattr(service, "_library_cad_pdfs", lambda *_a, **_k: [pdf])
    monkeypatch.setattr(
        service,
        "_library_linear_rows",
        lambda *_a, **_k: [{"part_no": "21897-1", "description": "TUBE"}],
    )
    result = service.push_job(
        title="10099",
        pdf_filename="10099.pdf",
        pdf_path=pdf,
        stp_path=None,
        takeoff={"library": {"part_key": "10099"}},
        times={},
        job_id=6,
    )
    assert called.get("pdf") is True
    assert called.get("lin") is True
    blob = " ".join(result.notes or [])
    assert "skipped Image Files / Long" not in blob


def test_assembly_line_uses_part_number_and_chosen_description(monkeypatch):
    from secturafab.page_weld import PAGE_ADD_ASSEMBLY_JS, add_page_assembly

    seen: dict[str, str] = {}

    def _eval(expression, **_kwargs):
        seen["expr"] = expression
        return {"ok": True, "why": "", "posted_additem": True, "staged": 1}

    monkeypatch.setattr(
        "secturafab.chrome_cdp.minted_edit_tab_ready",
        lambda *_a, **_k: {"ok": True, "tab": {"webSocketDebuggerUrl": "ws://local"}},
    )
    monkeypatch.setattr("secturafab.chrome_cdp._cdp_evaluate_promise", _eval)
    monkeypatch.setattr(
        "secturafab.chrome_cdp.page_jquery_ajax",
        lambda **_k: {
            "ok": True,
            "body": {
                "Data": [
                    {
                        "ID": "parent",
                        "ItemNumber": "11521-000",
                        "ProductType": 300,
                        "Description": "11521-000 - ZZ-TEST weldment",
                    },
                    {
                        "ID": "kid",
                        "ItemNumber": "A-11521-000",
                        "ProductType": 100,
                        "AssemblyID": "parent",
                    },
                ]
            },
        },
    )
    notes = add_page_assembly(
        quote_id="qid",
        name="11521-000",
        description="11521-000 - ZZ-TEST weldment",
    )
    assert '"description": "11521-000 - ZZ-TEST weldment"' in seen["expr"]
    assert "applyAssemblyLineDesc" in PAGE_ADD_ASSEMBLY_JS
    assert "editCell" in PAGE_ADD_ASSEMBLY_JS
    assert "data-field='Description'" in PAGE_ADD_ASSEMBLY_JS
    assert 'parameter: "Description"' not in PAGE_ADD_ASSEMBLY_JS
    assert "#quote_Text" not in PAGE_ADD_ASSEMBLY_JS
    assert "quoteOnline/update" not in PAGE_ADD_ASSEMBLY_JS
    assert any("AddItem_Assembly persisted" in note for note in notes)
    seen.clear()
    add_page_assembly(
        quote_id="qid",
        name="11521-000",
        description="1. ALL WELDS FULL LENGTH UNLESS",
    )
    assert "ALL WELDS" not in seen["expr"]


def test_unlisted_gauge_drops_that_kid_and_keeps_the_rest():
    import json
    import shutil
    import subprocess
    import textwrap

    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")
    from secturafab.chrome_cdp import _PAGE_FINISH_JS

    start = _PAGE_FINISH_JS.index("async function applyPageNativeCadThickness")
    end = _PAGE_FINISH_JS.index("  function skipFinish")
    fn = _PAGE_FINISH_JS[start:end]
    script = textwrap.dedent(
        r"""
        const vm = require("vm");
        const fs = require("fs");
        const code = fs.readFileSync(process.argv[2], "utf8");
        const store = [
          { uid: "good", PartID: "good", Name: "34890 PLATE", ItemType: "Cad",
            PartMode: 0, ProductType: 100, Thickness: 0.076, ErrorStatus: 0, Material: "A36" },
          { uid: "bad", PartID: "bad", Name: "34892 BOTTOM PLATE", ItemType: "Cad",
            PartMode: 0, ProductType: 100, Thickness: 0.125, ErrorStatus: 2, Material: "A36" },
          { uid: "tube", PartID: "tube", Name: "34536 PIVOT TUBE", ItemType: "Linear",
            PartMode: 1, ProductType: 30, ErrorStatus: 0 }
        ];
        const gauges = [{ Thickness: 0.076, Description: ".076 - 14 Ga", Value: "0.076" }];
        let current = store[0];
        const sandbox = { setTimeout, clearTimeout, Date, Promise, console, Math, parseFloat, isFinite, Number, String, Object };
        sandbox.store = store;
        sandbox.window = sandbox;
        sandbox.document = { querySelector: () => ({ textContent: "Q34887" }) };
        sandbox.location = { href: "https://www.secturafab.com/Quote/EDIT/qid" };
        function Deferred() {
          const fns = [];
          return { always(fn) { fns.push(fn); return this; }, then(fn) { fns.push(fn); return this; }, resolve() { fns.forEach((fn) => fn()); } };
        }
        sandbox.jQuery = function() {
          return {
            data(name) {
              if (name === "kendoDropDownList") return { value() {}, trigger() { sandbox.jQuery.ajax({ url: "/Part/UpdateItemType" }); } };
              if (name === "kendoComboBox") return {
                dataSource: { data() { return gauges; } },
                select() {},
                trigger() { sandbox.jQuery.ajax({ url: "/Quote/GetBorderSize" }); }
              };
              if (name === "kendoGrid") return {
                clearSelection() {},
                select(tr) {
                  if (tr === undefined) return { length: 1, toArray() { return [{ id: current.uid }]; } };
                  return { length: 1 };
                },
                dataItem() { return current; },
                tbody: {
                  find(sel) {
                    const match = String(sel || "").match(/data-uid='([^']+)'/);
                    if (match) current = store.find((row) => row.uid === match[1]) || current;
                    return { length: current ? 1 : 0 };
                  }
                },
                dataSource: {
                  view() { return store; },
                  data() { return { toJSON() { return store.map((row) => Object.assign({}, row)); } }; },
                  remove(row) {
                    const id = row && (row.uid || row.PartID);
                    const at = store.findIndex((item) => item.uid === id || item.PartID === id);
                    if (at >= 0) store.splice(at, 1);
                  }
                }
              };
              return null;
            }
          };
        };
        sandbox.jQuery.ajax = function() {
          const d = Deferred();
          setTimeout(() => d.resolve(), 5);
          return d;
        };
        vm.createContext(sandbox);
        const runner = `
          (async () => {
            const out = await applyPageNativeCadThickness(store.slice(), {
              quoteId: "qid", thickness: "0.125"
            });
            return { why: out.why, skipped: out.gauge_skipped, left: store.map((row) => row.Name) };
          })()
        `;
        vm.runInContext(code + "\n" + runner, sandbox).then((out) => {
          console.log(JSON.stringify(out));
        }).catch((err) => {
          console.error(err && err.stack || err);
          process.exit(1);
        });
        """
    )
    fn_path = tmp_path_unused = None
    from pathlib import Path

    fn_path = Path(__file__).resolve().parent / "_unlisted_gauge_fn.js"
    run_path = Path(__file__).resolve().parent / "_unlisted_gauge_run.js"
    fn_path.write_text(fn, encoding="utf-8")
    run_path.write_text(script, encoding="utf-8")
    try:
        proc = subprocess.run(
            [node, str(run_path), str(fn_path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    finally:
        fn_path.unlink(missing_ok=True)
        run_path.unlink(missing_ok=True)
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout.strip().splitlines()[-1])
    assert out["why"] == ""
    assert out["skipped"] == ["34892 BOTTOM PLATE"]
    assert "34890 PLATE" in out["left"]
    assert "34536 PIVOT TUBE" in out["left"]
    assert "34892 BOTTOM PLATE" not in out["left"]


def test_errorstatus_row_is_flagged_and_the_rest_continue():
    """One ErrorStatus row must not skip Finish for the other kids.

    The old inspectFresh returned errorstatus_not_zero for the whole grid
    and skipFinish dropped gauge_skipped before the notes were written.
    """
    import json
    import shutil
    import subprocess
    import textwrap

    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")
    from secturafab.chrome_cdp import _PAGE_FINISH_JS

    start = _PAGE_FINISH_JS.index("async function applyPageNativeCadThickness")
    end = _PAGE_FINISH_JS.index("  function skipFinish")
    fn = _PAGE_FINISH_JS[start:end]
    skip_start = _PAGE_FINISH_JS.index("  function skipFinish")
    skip_end = _PAGE_FINISH_JS.index("  var rows = gridData();", skip_start)
    skip_fn = _PAGE_FINISH_JS[skip_start:skip_end]
    script = textwrap.dedent(
        r"""
        const vm = require("vm");
        const fs = require("fs");
        const code = fs.readFileSync(process.argv[2], "utf8");
        const skip = fs.readFileSync(process.argv[3], "utf8");
        const gauges = [
          { Thickness: 0.076, Description: ".076 - 14 Ga", Value: "0.076" },
          { Thickness: 0.125, Description: "0.125", Value: "0.125" }
        ];
        function makeStore() {
          return [
            { uid: "good", PartID: "good", Name: "34890 PLATE", ItemType: "Cad",
              PartMode: 0, ProductType: 100, Thickness: 0.076, ErrorStatus: 0, Material: "A36" },
            { uid: "bad", PartID: "bad", Name: "34892 BOTTOM PLATE", ItemType: "Cad",
              PartMode: 0, ProductType: 100, Thickness: 0.125, ErrorStatus: 2, Material: "A36" },
            { uid: "tube", PartID: "tube", Name: "34536 PIVOT TUBE", ItemType: "Linear",
              PartMode: 1, ProductType: 30, ErrorStatus: 0 }
          ];
        }
        const sandbox = {
          setTimeout, clearTimeout, Date, Promise, console, Math, parseFloat,
          isFinite, Number, String, Object
        };
        sandbox.window = sandbox;
        sandbox.document = { querySelector: () => ({ textContent: "Q34887" }) };
        sandbox.location = { href: "https://www.secturafab.com/Quote/EDIT/qid" };
        let store = makeStore();
        let current = store[0];
        sandbox.store = store;
        function Deferred() {
          const fns = [];
          return {
            always(fn) { fns.push(fn); return this; },
            then(fn) { fns.push(fn); return this; },
            resolve() { fns.forEach((fn) => fn()); }
          };
        }
        sandbox.jQuery = function() {
          return {
            data(name) {
              if (name === "kendoDropDownList") return {
                value() {},
                trigger() { sandbox.jQuery.ajax({ url: "/Part/UpdateItemType" }); }
              };
              if (name === "kendoComboBox") return {
                dataSource: { data() { return gauges; } },
                select() {},
                trigger() { sandbox.jQuery.ajax({ url: "/Quote/GetBorderSize" }); }
              };
              if (name === "kendoGrid") return {
                clearSelection() {},
                select(tr) {
                  if (tr === undefined) return { length: 1, toArray() { return [{ id: current.uid }]; } };
                  return { length: 1 };
                },
                dataItem() { return current; },
                tbody: {
                  find(sel) {
                    const match = String(sel || "").match(/data-uid='([^']+)'/);
                    if (match) current = store.find((row) => row.uid === match[1]) || current;
                    return { length: current ? 1 : 0 };
                  }
                },
                dataSource: {
                  view() { return store; },
                  data() { return { toJSON() { return store.map((row) => Object.assign({}, row)); } }; },
                  remove(row) {
                    const id = row && (row.uid || row.PartID);
                    const at = store.findIndex((item) => item.uid === id || item.PartID === id);
                    if (at >= 0) store.splice(at, 1);
                  }
                }
              };
              return null;
            }
          };
        };
        sandbox.jQuery.ajax = function() {
          const d = Deferred();
          setTimeout(() => d.resolve(), 5);
          return d;
        };
        vm.createContext(sandbox);
        const runner = `
          (async () => {
            const many = await applyPageNativeCadThickness(store.slice(), {
              quoteId: "qid", thickness: "0.125"
            });
            const manyOut = {
              why: many.why,
              skipped: many.gauge_skipped,
              whyList: many.gauge_skip_why,
              left: store.map((row) => row.Name)
            };
            store.length = 0;
            store.push({
              uid: "only", PartID: "only", Name: "34892 BOTTOM PLATE", ItemType: "Cad",
              PartMode: 0, ProductType: 100, Thickness: 0.125, ErrorStatus: 2, Material: "A36"
            });
            current = store[0];
            const alone = await applyPageNativeCadThickness(store.slice(), {
              quoteId: "qid", thickness: "0.125"
            });
            return {
              many: manyOut,
              alone: {
                why: alone.why,
                skipped: alone.gauge_skipped,
                left: store.map((row) => row.Name)
              }
            };
          })()
        `;
        const skipRunner = `
          var gaugeSkipped = ["34892 BOTTOM PLATE"];
          var gaugeSkipWhy = ["errorstatus_not_zero"];
          var count = 3;
          function summarize() { return {}; }
          function kendoGridPresent() { return true; }
          ${skip}
          skipFinish("errorstatus_not_zero").then((out) => out);
        `;
        vm.runInContext(code + "\n" + runner, sandbox).then((out) => {
          return vm.runInContext(skipRunner, sandbox).then((skipped) => {
            out.skip = skipped;
            console.log(JSON.stringify(out));
          });
        }).catch((err) => {
          console.error(err && err.stack || err);
          process.exit(1);
        });
        """
    )
    from pathlib import Path

    fn_path = Path(__file__).resolve().parent / "_errorstatus_fn.js"
    skip_path = Path(__file__).resolve().parent / "_errorstatus_skip.js"
    run_path = Path(__file__).resolve().parent / "_errorstatus_run.js"
    fn_path.write_text(fn, encoding="utf-8")
    skip_path.write_text(skip_fn, encoding="utf-8")
    run_path.write_text(script, encoding="utf-8")
    try:
        proc = subprocess.run(
            [node, str(run_path), str(fn_path), str(skip_path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    finally:
        fn_path.unlink(missing_ok=True)
        skip_path.unlink(missing_ok=True)
        run_path.unlink(missing_ok=True)
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout.strip().splitlines()[-1])
    assert out["many"]["why"] == ""
    assert out["many"]["skipped"] == ["34892 BOTTOM PLATE"]
    assert out["many"]["whyList"] == ["errorstatus_not_zero"]
    assert "34890 PLATE" in out["many"]["left"]
    assert "34536 PIVOT TUBE" in out["many"]["left"]
    assert "34892 BOTTOM PLATE" not in out["many"]["left"]
    assert out["alone"]["why"] == "errorstatus_not_zero"
    assert out["alone"]["skipped"] == ["34892 BOTTOM PLATE"]
    assert out["skip"]["via"] == "skipped"
    assert out["skip"]["finish_why"] == "errorstatus_not_zero"
    assert out["skip"]["gauge_skipped"] == ["34892 BOTTOM PLATE"]
    assert out["skip"]["gauge_skip_why"] == ["errorstatus_not_zero"]


def test_skip_finish_notes_name_the_errorstatus_row():
    from secturafab.push import dxf_finish_skip_notes

    notes = dxf_finish_skip_notes(
        {
            "via": "skipped",
            "finish_why": "errorstatus_not_zero",
            "gauge_skipped": ["34892 BOTTOM PLATE"],
            "gauge_skip_why": ["errorstatus_not_zero"],
        }
    )
    assert notes == [
        "FLAG: 34892 BOTTOM PLATE — errorstatus_not_zero "
        "(removed before Finish; not inventing a gauge)"
    ]
    assert dxf_finish_skip_notes(
        {"via": "skipped", "finish_why": "errorstatus_not_zero"}
    ) == []


def test_linear_only_confident_sku_creates_quote_and_nests(monkeypatch):
    from secturafab.push import SecturaFabPushService

    monkeypatch.setattr("secturafab.push.detect_organization", lambda **_k: "Safe Cave")
    monkeypatch.setattr("secturafab.chrome_cdp.chrome_quotes_live", lambda *_a, **_k: True)
    monkeypatch.setattr("secturafab.chrome_cdp.quotes_tab", lambda *_a, **_k: None)
    monkeypatch.setattr("secturafab.chrome_cdp.chrome_session_lost", lambda *_a, **_k: False)
    monkeypatch.setattr("secturafab.push.extract_assembly_description", lambda **_k: None)
    monkeypatch.setattr(
        "secturafab.push.apply_quote_organization",
        lambda *_a, **_k: ["Set Organization: Safe Cave"],
    )
    monkeypatch.setattr("secturafab.push.ensure_imperial_item_units", lambda *_a, **_k: [])
    monkeypatch.setattr("secturafab.push.apply_bom_quantities", lambda *_a, **_k: [])
    monkeypatch.setattr("secturafab.push.ensure_weld_ops", lambda *_a, **_k: [])
    rows = [{"part_no": "1020243-1", "description": "1 X 1 TUBE", "qty": 1}]
    monkeypatch.setattr(
        "secturafab.push.refresh_bom_rows_for_push", lambda *_a, **_k: (rows, [])
    )
    client = MagicMock()
    client.config.website_cookie = ""
    client.get_json.return_value = {
        "ItemList": [{"ProductType": 30, "Description": "1020243-1 - TUBE"}],
        "ItemCount": 1,
        "OrganizationName": "Safe Cave",
        "PrimaryOrganizationID": "11111111-1111-4111-8111-111111111111",
        "Description": "tube job",
    }
    service = SecturaFabPushService(client=client)
    called: dict[str, bool] = {}
    monkeypatch.setattr(service, "create_quote", lambda **_k: "qid")
    monkeypatch.setattr(service, "allocate_quote_number", lambda *_a, **_k: "1020243-1")
    monkeypatch.setattr(service, "upload_drawings_quote_request", lambda *_a, **_k: "qr")
    monkeypatch.setattr(service, "preflight_website_addview_session", lambda: (True, []))
    monkeypatch.setattr(service, "_page_session_live", lambda: True)
    monkeypatch.setattr(service, "_website_cookie_present", lambda: False)
    monkeypatch.setattr(
        service,
        "_match_linear_product",
        lambda *_a, **_k: ({"ID": "sku-1", "ProductName": "RT1X1-A500"}, "RT1X1-A500", None),
    )

    def _lin(**_k):
        called["lin"] = True
        return ["Long"]

    def _nest(*_a, **_k):
        called["nest"] = True
        return ["RenestLinear"]

    monkeypatch.setattr(service, "finish_linear_bom_rows", _lin)
    monkeypatch.setattr(service, "nest_after_finish", _nest)
    monkeypatch.setattr(service, "_library_cad_pdfs", lambda *_a, **_k: [])
    result = service.push_job(
        title="1020243-1",
        pdf_filename=None,
        pdf_path=None,
        stp_path=None,
        takeoff={"library": {"part_key": "1020243-1"}, "description": "tube job"},
        times={},
        job_id=7,
        organization="Safe Cave",
        quote_number="ZZ-LIN-TEST-701",
    )
    assert called.get("lin") is True
    assert called.get("nest") is True
    blob = " ".join(result.notes or [])
    assert "No PDF or STEP files found to push" not in blob
    assert "Linear-only job" in blob


def test_linear_only_without_confident_sku_still_stops(monkeypatch):
    from secturafab.push import SecturaFabPushService

    rows = [{"part_no": "21897-1", "description": "TUBE", "qty": 1}]
    monkeypatch.setattr(
        "secturafab.push.refresh_bom_rows_for_push", lambda *_a, **_k: (rows, [])
    )
    service = SecturaFabPushService(client=MagicMock())
    monkeypatch.setattr(
        service,
        "_match_linear_product",
        lambda *_a, **_k: (None, None, "no tenant SKU"),
    )
    created = {"n": 0}
    monkeypatch.setattr(service, "create_quote", lambda **_k: created.__setitem__("n", 1) or "qid")
    result = service.push_job(
        title="21897-1",
        pdf_filename=None,
        pdf_path=None,
        stp_path=None,
        takeoff={"library": {"part_key": "21897-1"}},
        times={},
        job_id=8,
    )
    assert result.ok is False
    assert result.error == "No PDF or STEP files found to push"
    assert created["n"] == 0


def test_step_0188_is_not_11_ga_and_assembly_body_is_not_a_plate(monkeypatch):
    """push_job classifies through classify_cadimport_rows.

    34892's solid is 0.188. That is not 11 Ga and not any other dropdown
    gauge. The bare 34887-1 solid is the assembly line, not a Cad plate.
    34536 has no catalog SKU, so it is flagged and not a laser plate.
    """
    from secturafab.push import SecturaFabPushService

    monkeypatch.setattr("secturafab.chrome_cdp.chrome_quotes_live", lambda *a, **k: True)
    classified, notes = SecturaFabPushService(client=MagicMock()).classify_cadimport_rows(
        [
            {"Name": "34887-1", "PartName": "34887-1", "ID": "body"},
            {
                "Name": "34887-1",
                "PartName": "34892 BOTTOM PLATE",
                "ID": "plate",
                "Stock_Z": 0.188,
                "Length": 43.563,
                "Width": 8.438,
            },
            {
                "Name": "34887-1",
                "PartName": "34536 PIVOT TUBE, BOOM TIP_34536-1",
                "ID": "tube",
            },
            {
                "Name": "34887-1",
                "PartName": "34889 PLATE",
                "ID": "good",
                "Stock_Z": 0.1196,
            },
        ],
        default_material="A36",
        default_thickness="0.1196",
        bom_rows=[],
        library={},
        extra_pdfs=[],
        part_key="34887-1",
        default_thickness_source="drawing",
    )
    names = [str(row.get("PartName") or row.get("Name") or "") for row in classified]
    assert not any("34892" in name for name in names)
    assert any("34892" in note and "0.188" in note for note in notes)
    assert "11 Ga" not in " ".join(
        str(row.get("Description") or "") for row in classified if "34892" in str(row)
    )
    body = next(row for row in classified if str(row.get("ID") or "") == "body")
    assert body.get("Category") == "Assembly"
    assert body.get("Machine") != "Laser"
    assert "11 Ga" not in str(body.get("Description") or "")
    tube = next(row for row in classified if str(row.get("ID") or "") == "tube")
    assert tube.get("Category") == "Linear"
    assert tube.get("Machine") != "Laser"
    assert not tube.get("ProductID")
    assert any("34889" in name for name in names)


def test_page_finish_drops_0188_root_and_unpriced_tube():
    """applyPageNativeCadThickness is the Finish path push_job calls.

    quoteOnline-style gauge stamps must not keep 0.188 as 11 Ga.
    Root and the bare assembly solid are removed. A tube with no SKU
    is removed instead of finished as a laser plate.
    """
    import json
    import shutil
    import subprocess
    import textwrap

    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")
    from secturafab.chrome_cdp import _PAGE_FINISH_JS

    start = _PAGE_FINISH_JS.index("async function applyPageNativeCadThickness")
    end = _PAGE_FINISH_JS.index("  function skipFinish")
    fn = _PAGE_FINISH_JS[start:end]
    script = textwrap.dedent(
        r"""
        const vm = require("vm");
        const fs = require("fs");
        const code = fs.readFileSync(process.argv[2], "utf8");
        const store = [
          { uid: "root", PartID: "root", Name: "Root", PartName: "Root",
            ItemType: "Cad", PartMode: 0, ProductType: 100, Thickness: "11 Ga",
            ErrorStatus: 0, Material: "A36" },
          { uid: "body", PartID: "body", Name: "34887-1", PartName: "34887-1",
            ItemType: "Cad", PartMode: 0, ProductType: 100, Thickness: "11 Ga",
            ErrorStatus: 0, Material: "A36" },
          { uid: "bad", PartID: "bad", Name: "34887-1", PartName: "34892 BOTTOM PLATE",
            ItemType: "Cad", PartMode: 0, ProductType: 100, Thickness: "11 Ga",
            Stock_Z: 0.188, Length: 43.5625, Width: 8.4375, ErrorStatus: 0, Material: "A36" },
          { uid: "good", PartID: "good", Name: "34887-1", PartName: "34889 PLATE",
            ItemType: "Cad", PartMode: 0, ProductType: 100, Thickness: "0.1345",
            Stock_Z: 0.1345, ErrorStatus: 0, Material: "A36" },
          { uid: "tube", PartID: "tube", Name: "34887-1",
            PartName: "34536 PIVOT TUBE, BOOM TIP_34536-1",
            ItemType: "Cad", PartMode: 0, ProductType: 100, ErrorStatus: 0 },
          { uid: "bar", PartID: "bar", Name: "10187", PartName: "10187 BAR",
            ItemType: "Linear", PartMode: 1, ProductType: 10, ProductID: "sku-10187",
            ErrorStatus: 0 }
        ];
        const gauges = [
          { Thickness: 0.1196, Description: "11 Ga" },
          { Thickness: 0.1793, Description: "7 Ga" },
          { Thickness: 0.1875, Description: "3/16" },
          { Thickness: 0.1345, Description: "10 Ga" }
        ];
        let current = store[0];
        const selected = [];
        const sandbox = {
          setTimeout, clearTimeout, Date, Promise, console, Math, parseFloat,
          isFinite, Number, String, Object
        };
        sandbox.store = store;
        sandbox.selected = selected;
        sandbox.window = sandbox;
        sandbox.document = { querySelector: () => ({ textContent: "Q34887" }) };
        sandbox.location = { href: "https://www.secturafab.com/Quote/EDIT/qid" };
        function Deferred() {
          const fns = [];
          return {
            always(fn) { fns.push(fn); return this; },
            then(fn) { fns.push(fn); return this; },
            resolve() { fns.forEach((fn) => fn()); }
          };
        }
        sandbox.jQuery = function() {
          return {
            data(name) {
              if (name === "kendoDropDownList") {
                return {
                  value() {},
                  trigger() { sandbox.jQuery.ajax({ url: "/Part/UpdateItemType" }); }
                };
              }
              if (name === "kendoComboBox") {
                return {
                  dataSource: { data() { return gauges; } },
                  select(idx) { selected.push(gauges[idx] && gauges[idx].Description); },
                  trigger() { sandbox.jQuery.ajax({ url: "/Quote/GetBorderSize" }); }
                };
              }
              if (name === "kendoGrid") {
                return {
                  clearSelection() {},
                  select(tr) {
                    if (tr === undefined) {
                      return { length: 1, toArray() { return [{ id: current.uid }]; } };
                    }
                    return { length: 1 };
                  },
                  dataItem() { return current; },
                  tbody: {
                    find(sel) {
                      const match = String(sel || "").match(/data-uid='([^']+)'/);
                      if (match) current = store.find((row) => row.uid === match[1]) || current;
                      return { length: current ? 1 : 0 };
                    }
                  },
                  dataSource: {
                    view() { return store; },
                    data() { return store; },
                    remove(row) {
                      const id = row && (row.uid || row.PartID);
                      const at = store.findIndex((item) => item.uid === id || item.PartID === id);
                      if (at >= 0) store.splice(at, 1);
                    }
                  }
                };
              }
              return null;
            }
          };
        };
        sandbox.jQuery.ajax = function() {
          const d = Deferred();
          setTimeout(() => d.resolve(), 5);
          return d;
        };
        vm.createContext(sandbox);
        const runner = `
          (async () => {
            const out = await applyPageNativeCadThickness(store.slice(), {
              quoteId: "qid", thickness: "11 Ga"
            });
            return {
              why: out.why,
              skipped: out.gauge_skipped,
              whyList: out.gauge_skip_why,
              left: store.map((row) => row.PartName || row.Name),
              selected: selected
            };
          })()
        `;
        vm.runInContext(code + "\n" + runner, sandbox).then((out) => {
          console.log(JSON.stringify(out));
        }).catch((err) => {
          console.error(err && err.stack || err);
          process.exit(1);
        });
        """
    )
    from pathlib import Path

    fn_path = Path(__file__).resolve().parent / "_round9_finish_fn.js"
    run_path = Path(__file__).resolve().parent / "_round9_finish_run.js"
    fn_path.write_text(fn, encoding="utf-8")
    run_path.write_text(script, encoding="utf-8")
    try:
        proc = subprocess.run(
            [node, str(run_path), str(fn_path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    finally:
        fn_path.unlink(missing_ok=True)
        run_path.unlink(missing_ok=True)
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout.strip().splitlines()[-1])
    assert out["why"] == "", out
    left = " ".join(out["left"])
    assert "Root" not in left
    assert "34892" not in left
    assert "34536" not in left
    assert "34887-1" not in left
    assert "34889" in left
    assert "10187" in left
    assert "34892 BOTTOM PLATE" in out["skipped"]
    assert "34536 PIVOT TUBE, BOOM TIP_34536-1" in out["skipped"]
    assert "step_thickness_not_a_gauge" in out["whyList"]
    assert "no_catalog_sku" in out["whyList"]
    assert "11 Ga" not in out["selected"]
    assert "3/16" not in out["selected"]
    assert "7 Ga" not in out["selected"]


def _run_page_finish(store, gauges, thickness):
    """applyPageNativeCadThickness is the Finish function push_job calls."""
    import json
    import shutil
    import subprocess
    import textwrap

    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")
    from secturafab.chrome_cdp import _PAGE_FINISH_JS

    start = _PAGE_FINISH_JS.index("async function applyPageNativeCadThickness")
    end = _PAGE_FINISH_JS.index("  function skipFinish")
    fn = _PAGE_FINISH_JS[start:end]
    script = textwrap.dedent(
        r"""
        const vm = require("vm");
        const fs = require("fs");
        const code = fs.readFileSync(process.argv[2], "utf8");
        const spec = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
        const store = spec.store;
        const gauges = spec.gauges;
        const thickness = spec.thickness;
        const selected = [];
        let current = store[0];
        const sandbox = {
          setTimeout, clearTimeout, Date, Promise, console, Math, parseFloat,
          isFinite, Number, String, Object
        };
        sandbox.store = store;
        sandbox.selected = selected;
        sandbox.thickness = thickness;
        sandbox.window = sandbox;
        sandbox.document = { querySelector: () => ({ textContent: "Q11521" }) };
        sandbox.location = { href: "https://www.secturafab.com/Quote/EDIT/qid" };
        function Deferred() {
          const fns = [];
          return {
            always(fn) { fns.push(fn); return this; },
            then(fn) { fns.push(fn); return this; },
            resolve() { fns.forEach((fn) => fn()); }
          };
        }
        sandbox.jQuery = function() {
          return {
            data(name) {
              if (name === "kendoDropDownList") {
                return {
                  value() {},
                  trigger() { sandbox.jQuery.ajax({ url: "/Part/UpdateItemType" }); }
                };
              }
              if (name === "kendoComboBox") {
                return {
                  dataSource: { data() { return gauges; } },
                  select(idx) {
                    const item = gauges[idx];
                    selected.push(
                      (item && (item.Description || item.Text)) || String(item || "")
                    );
                  },
                  trigger() { sandbox.jQuery.ajax({ url: "/Quote/GetBorderSize" }); }
                };
              }
              if (name === "kendoGrid") {
                return {
                  clearSelection() {},
                  select(tr) {
                    if (tr === undefined) {
                      return { length: 1, toArray() { return [{ id: current.uid }]; } };
                    }
                    return { length: 1 };
                  },
                  dataItem() { return current; },
                  tbody: {
                    find(sel) {
                      const match = String(sel || "").match(/data-uid='([^']+)'/);
                      if (match) current = store.find((row) => row.uid === match[1]) || current;
                      return { length: current ? 1 : 0 };
                    }
                  },
                  dataSource: {
                    view() { return store; },
                    data() { return store; },
                    remove(row) {
                      const id = row && (row.uid || row.PartID);
                      const at = store.findIndex((item) => item.uid === id || item.PartID === id);
                      if (at >= 0) store.splice(at, 1);
                    }
                  }
                };
              }
              return null;
            }
          };
        };
        sandbox.jQuery.ajax = function() {
          const d = Deferred();
          setTimeout(() => d.resolve(), 5);
          return d;
        };
        vm.createContext(sandbox);
        const runner = `
          (async () => {
            const out = await applyPageNativeCadThickness(store.slice(), {
              quoteId: "qid", thickness: thickness
            });
            return {
              why: out.why,
              skipped: out.gauge_skipped,
              whyList: out.gauge_skip_why,
              left: store.map((row) => row.PartName || row.Name),
              selected: selected
            };
          })()
        `;
        vm.runInContext(code + "\n" + runner, sandbox).then((out) => {
          console.log(JSON.stringify(out));
        }).catch((err) => {
          console.error(err && err.stack || err);
          process.exit(1);
        });
        """
    )
    from pathlib import Path

    fn_path = Path(__file__).resolve().parent / "_round10_finish_fn.js"
    run_path = Path(__file__).resolve().parent / "_round10_finish_run.js"
    spec_path = Path(__file__).resolve().parent / "_round10_finish_spec.json"
    fn_path.write_text(fn, encoding="utf-8")
    run_path.write_text(script, encoding="utf-8")
    spec_path.write_text(
        json.dumps({"store": store, "gauges": gauges, "thickness": thickness}),
        encoding="utf-8",
    )
    try:
        proc = subprocess.run(
            [node, str(run_path), str(fn_path), str(spec_path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    finally:
        fn_path.unlink(missing_ok=True)
        run_path.unlink(missing_ok=True)
        spec_path.unlink(missing_ok=True)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout.strip().splitlines()[-1])


def test_drawing_14_ga_0747_selects_dropdown_076():
    """A-11513-000. Drawing 14 GA parses to 0.0747. The list row is .076.

    The old numeric read treated '.076 - 14 Ga' as 76 and dropped the kid
    as gauge_not_in_list. push_job finishes through applyPageNativeCadThickness.
    """
    store = [
        {
            "uid": "sib",
            "PartID": "sib",
            "Name": "A-11521-000",
            "PartName": "A-11521-000",
            "ItemType": "Cad",
            "PartMode": 0,
            "ProductType": 100,
            "Thickness": "0.076",
            "ErrorStatus": 0,
            "Material": "A36",
            "Length": 26.6,
            "Width": 37.5,
        },
        {
            "uid": "kid",
            "PartID": "kid",
            "Name": "A-11513-000",
            "PartName": "A-11513-000",
            "ItemType": "Cad",
            "PartMode": 0,
            "ProductType": 100,
            "Thickness": "0.0747",
            "drawing_thickness_in": "0.0747",
            "ErrorStatus": 0,
            "Material": "A36",
            "Length": 15.0,
            "Width": 37.5,
        },
    ]
    out = _run_page_finish(store, [".076 - 14 Ga"], "0.076")
    assert out["why"] == "", out
    assert "A-11513-000" in out["left"]
    assert "A-11521-000" in out["left"]
    assert "A-11513-000" not in out["skipped"]
    assert "gauge_not_in_list" not in out["whyList"]
    assert out["selected"].count(".076 - 14 Ga") == 2
    objects = _run_page_finish(
        store,
        [{"Thickness": 0.076, "Description": ".076 - 14 Ga"}],
        "0.076",
    )
    assert objects["why"] == "", objects
    assert "A-11513-000" in objects["left"]
    assert "gauge_not_in_list" not in objects["whyList"]
    assert ".076 - 14 Ga" in objects["selected"]


def test_kid_without_callout_keeps_job_level_14_ga():
    """A-11513-000 has no 14 GA of its own. The job gauge is 14 Ga.

    plates.length > 1 used to replace that name with the grid Thickness
    before the callout check. This row's Thickness is not a dropdown row
    and the blob does not say 14 GA, so gaugeIndex returned -1 and the
    FLAG was gauge_not_in_list. The kid keeps the job-level 14 Ga.
    0.0747 and the list row .076 are that same gauge. applyPageNativeCadThickness
    is the Finish function push_job calls.
    """
    store = [
        {
            "uid": "sib",
            "PartID": "sib",
            "Name": "A-11521-000",
            "PartName": "A-11521-000",
            "ItemType": "Cad",
            "PartMode": 0,
            "ProductType": 100,
            "Thickness": "0.076",
            "ErrorStatus": 0,
            "Material": "A36",
            "Length": 26.6,
            "Width": 37.5,
        },
        {
            "uid": "kid",
            "PartID": "kid",
            "Name": "A-11513-000",
            "PartName": "A-11513-000",
            "Description": "A-11513-000",
            "ItemType": "Cad",
            "PartMode": 0,
            "ProductType": 100,
            "Thickness": "not a dropdown row",
            "ErrorStatus": 0,
            "Material": "A36",
            "Length": 15.0,
            "Width": 37.5,
        },
    ]
    gauges = [{"Thickness": 0.076, "Description": ".076 - 14 Ga"}]
    out = _run_page_finish(store, gauges, "14 Ga")
    assert out["why"] == "", out
    assert "A-11513-000" in out["left"]
    assert "A-11521-000" in out["left"]
    assert "A-11513-000" not in " ".join(out["skipped"])
    assert "gauge_not_in_list" not in out["whyList"]
    assert out["selected"].count(".076 - 14 Ga") == 2


def test_page_finish_34892_three_sixteenth_not_11_ga():
    """34892 names 3/16 PLATE and Stock_Y is 0.188. Do not stamp 11 Ga.

    A stray 1/8 must not win. 0.188 is not 11 Ga and not 7 Ga.
    applyPageNativeCadThickness is the Finish function push_job calls.
    """
    store = [
        {
            "uid": "good",
            "PartID": "good",
            "Name": "34887-1",
            "PartName": "34889 PLATE",
            "ItemType": "Cad",
            "PartMode": 0,
            "ProductType": 100,
            "Thickness": "0.1345",
            "Stock_Z": 0.1345,
            "ErrorStatus": 0,
            "Material": "A36",
            "Length": 10,
            "Width": 8,
        },
        {
            "uid": "bad",
            "PartID": "bad",
            "Name": "34887-1",
            "PartName": "34892 BOTTOM PLATE",
            "Description": "3/16 PLATE DOMEX/WELDOX\n.125 SIZE SCALE\n1/8",
            "ItemType": "Cad",
            "PartMode": 0,
            "ProductType": 100,
            "Thickness": "11 Ga",
            "Stock_Y": 0.188,
            "ErrorStatus": 0,
            "Material": "A36",
            "Length": 43.5625,
            "Width": 8.4375,
        },
    ]
    out = _run_page_finish(
        store,
        [
            {"Thickness": 0.1196, "Description": "11 Ga"},
            {"Thickness": 0.1793, "Description": "7 Ga"},
            {"Thickness": 0.1875, "Description": "3/16"},
            {"Thickness": 0.125, "Description": "1/8"},
        ],
        "11 Ga",
    )
    assert out["why"] == "", out
    assert "34892 BOTTOM PLATE" in out["left"]
    assert "34892 BOTTOM PLATE" not in out["skipped"]
    assert "3/16" in out["selected"]
    assert "11 Ga" not in out["selected"]
    assert "7 Ga" not in out["selected"]
    assert "1/8" not in out["selected"]


def test_classify_34892_three_sixteenth_not_11_ga(tmp_path, monkeypatch):
    """push_job classifies through classify_cadimport_rows.

    The kid PDF says 3/16 PLATE. Parent 11 Ga and a stray 1/8 must not stamp.
    Stock_Y 0.188 agrees with 3/16, so the kid stays.
    """
    import fitz

    from secturafab.push import SecturaFabPushService

    pdf = tmp_path / "34892.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (72, 720),
        "3/16 PLATE DOMEX/WELDOX\nTITLE BOTTOM PLATE\n.125 SIZE SCALE\n"
        "DWG. NO. 54892-1\n1/8",
    )
    doc.save(pdf)
    doc.close()
    monkeypatch.setattr("secturafab.chrome_cdp.chrome_quotes_live", lambda *a, **k: True)
    classified, notes = SecturaFabPushService(client=MagicMock()).classify_cadimport_rows(
        [
            {
                "Name": "34887-1",
                "PartName": "34892 BOTTOM PLATE",
                "ID": "plate",
                "Stock_Y": 0.188,
                "Length": 43.563,
                "Width": 8.438,
            }
        ],
        default_material="A36",
        default_thickness="0.1196",
        bom_rows=[],
        library={},
        extra_pdfs=[pdf],
        part_key="34887-1",
        default_thickness_source="drawing",
    )
    row = next(item for item in classified if "34892" in str(item.get("PartName") or ""))
    assert float(row["Thickness"]) == pytest.approx(0.1875)
    assert "11 Ga" not in str(row.get("Description") or "")
    assert "0.125" not in str(row.get("Thickness") or "")
    assert not any(
        "34892" in note and "not a dropdown gauge" in note for note in notes
    )
