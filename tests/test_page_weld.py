"""ZZ Q10506 weldment path: selection, units, assembly persist, quote number."""

from __future__ import annotations

from unittest.mock import MagicMock

from secturafab.page_weld import (
    PAGE_ADD_ASSEMBLY_JS,
    STEP_MM_CONTINUE_NOTE,
    add_page_assembly,
    assembly_tree_problems,
    set_page_quote_number,
    step_header_is_millimetre,
)

_INCH = "CONVERSION_BASED_UNIT('INCH',#12);"
_MM = "SI_UNIT(.MILLI.,.METRE.);"

_PARENT = "cf0c1bc5-59de-4fab-ad16-30aec441a288"
_Q10506 = [
    {
        "ID": "e0d53e45-cd4a-48ed-98ea-e31b33ec6aa2",
        "ItemNumber": "A-11521-000",
        "ProductType": 100,
        "AssemblyID": _PARENT,
        "AssemblyLevel": 2,
    },
    {
        "ID": "d5f4db37-c5f7-4e0e-b9ae-561ca40fdbe3",
        "ItemNumber": "A-11513-000",
        "ProductType": 100,
        "AssemblyID": _PARENT,
        "AssemblyLevel": 2,
    },
    {
        "ID": _PARENT,
        "ItemNumber": "ZZ-WELD-TEST-001",
        "ProductType": 300,
        "AssemblyID": None,
        "AssemblyLevel": 1,
    },
]


def test_step_header_millimetre_is_not_marked_inch():
    assert step_header_is_millimetre(_MM) is True
    assert step_header_is_millimetre(_INCH) is False
    assert step_header_is_millimetre("ISO-10303-21;") is False


def test_q10506_tree_is_one_parent_and_two_kids():
    assert assembly_tree_problems(_Q10506, kid_count=2) == ""


def test_loose_top_level_line_is_not_an_assembly():
    loose = list(_Q10506) + [
        {
            "ID": "loose",
            "ItemNumber": "EXTRA",
            "ProductType": 100,
            "AssemblyID": None,
            "AssemblyLevel": 1,
        }
    ]
    assert assembly_tree_problems(loose, kid_count=2) == "assembly_loose_line"


def test_oncopyall_without_additem_does_not_persist(monkeypatch):
    calls = []

    def _eval(expression, **kwargs):
        calls.append(expression)
        return {"ok": False, "why": "additem_assembly_missing", "posted_additem": False, "staged": 2}

    monkeypatch.setattr(
        "secturafab.chrome_cdp.minted_edit_tab_ready",
        lambda *a, **k: {"ok": True, "tab": {"webSocketDebuggerUrl": "ws://local"}},
    )
    monkeypatch.setattr("secturafab.chrome_cdp._cdp_evaluate_promise", _eval)
    monkeypatch.setattr(
        "secturafab.chrome_cdp.page_jquery_ajax",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("tree read")),
    )
    notes = add_page_assembly(quote_id="eefcc4e3-761e-4355-af46-fb2b6982cb8a", name="ZZ-WELD-TEST-001")
    assert notes == ["WARNING: page assembly stopped (additem_assembly_missing)"]
    assert "OnCopyAll()" in PAGE_ADD_ASSEMBLY_JS
    assert PAGE_ADD_ASSEMBLY_JS.index("OnCopyAll()") < PAGE_ADD_ASSEMBLY_JS.index(
        "/Quote/AddItem_Assembly"
    )
    assert calls


def test_additem_assembly_is_checked_on_the_tree(monkeypatch):
    monkeypatch.setattr(
        "secturafab.chrome_cdp.minted_edit_tab_ready",
        lambda *a, **k: {"ok": True, "tab": {"webSocketDebuggerUrl": "ws://local"}},
    )
    monkeypatch.setattr(
        "secturafab.chrome_cdp._cdp_evaluate_promise",
        lambda *a, **k: {"ok": True, "why": "", "posted_additem": True, "staged": 2},
    )

    def _tree(**kwargs):
        assert kwargs["method"] == "GET"
        assert kwargs["url"] == "/Quote/QuoteItem_ReadTreeListData"
        return {"ok": True, "body": {"Data": _Q10506}}

    monkeypatch.setattr("secturafab.chrome_cdp.page_jquery_ajax", _tree)
    notes = add_page_assembly(quote_id="qid", name="ZZ-WELD-TEST-001")
    assert notes == ["AddItem_Assembly persisted; tree has one parent and no loose lines"]


def test_quote_number_posts_update_property_value(monkeypatch):
    seen = {}

    def _eval(expression, **kwargs):
        seen["expression"] = expression
        return {"ok": True, "why": "", "parameter": "QuoteNumber"}

    monkeypatch.setattr(
        "secturafab.chrome_cdp.minted_edit_tab_ready",
        lambda *a, **k: {"ok": True, "tab": {"webSocketDebuggerUrl": "ws://local"}},
    )
    monkeypatch.setattr("secturafab.chrome_cdp._cdp_evaluate_promise", _eval)
    notes = set_page_quote_number("qid", "A-11949-000")
    assert "#quote_Text" in seen["expression"]
    assert "/Quote/UpdatePropertyValue" in seen["expression"]
    assert '"parameter": "QuoteNumber"' in seen["expression"]
    assert notes == ["QuoteNumber set via UpdatePropertyValue (A-11949-000)"]


def test_quote_number_retries_when_the_property_endpoint_is_not_ready(monkeypatch):
    calls = {"n": 0}

    def _eval(expression, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return {
                "ok": False,
                "why": "update_property_missing",
                "parameter": "QuoteNumber",
            }
        return {"ok": True, "why": "", "parameter": "QuoteNumber"}

    monkeypatch.setattr(
        "secturafab.chrome_cdp.minted_edit_tab_ready",
        lambda *a, **k: {"ok": True, "tab": {"webSocketDebuggerUrl": "ws://local"}},
    )
    monkeypatch.setattr("secturafab.chrome_cdp._cdp_evaluate_promise", _eval)
    monkeypatch.setattr("secturafab.page_weld.time.sleep", lambda *_a, **_k: None)
    notes = set_page_quote_number("qid", "ZZ-WELD-TEST-701")
    assert calls["n"] == 2
    assert notes == ["QuoteNumber set via UpdatePropertyValue (ZZ-WELD-TEST-701)"]
    assert not any("WARNING" in note for note in notes)


def test_millimetre_step_does_not_call_set_units(tmp_path, monkeypatch):
    from secturafab.push import SecturaFabPushService

    calls = []

    def _ajax(**kwargs):
        calls.append(kwargs)
        return {"ok": True, "status": 200, "body": "<div id='dxf'></div>"}

    monkeypatch.setattr("secturafab.chrome_cdp.chrome_session_lost", lambda *a, **k: False)
    monkeypatch.setattr("secturafab.chrome_cdp.chrome_quotes_live", lambda *a, **k: True)
    monkeypatch.setattr("secturafab.chrome_cdp.page_jquery_ajax", _ajax)
    stp = tmp_path / "A-11513-000.step"
    stp.write_text(_MM, encoding="utf-8")
    client = MagicMock()
    client.upload_dxf_via_page_add_files.return_value = {
        "bound": True,
        "files_kendo": True,
        "upload_via": "page_add_files",
        "gridDXF_n": 1,
        "List": [{"SourceDataID": "src-mm"}],
    }
    client.create_all_parts_from_grid_dxf.return_value = {
        "via": "createAllParts",
        "List": [],
        "grid_present": False,
    }
    notes = SecturaFabPushService(client=client).finish_cad_files(
        quote_id="eefcc4e3-761e-4355-af46-fb2b6982cb8a",
        cad_files=[stp],
        material="A36",
        thickness="0.076",
        qty=1,
        takeoff={},
        bom_rows=[],
        library={},
        extra_pdfs=None,
        part_key="ZZ-WELD-TEST-001",
        explode_polls=1,
        explode_sleep_s=0,
    )
    assert "/CadImport/SetUnits" not in [call["url"] for call in calls]
    assert any(STEP_MM_CONTINUE_NOTE in note for note in notes)
    client.create_all_parts_from_grid_dxf.assert_called_once()
    client.cadimport_set_units.assert_not_called()
