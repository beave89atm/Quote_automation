"""Quote-load QC: read-only tree check, session abort, inch Finish."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

FIXTURE = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "q10488_p5_tree.json"
EXPECTED = {
    "35PX0.105RIB002": 3,
    "35PX0.075DPBOX025A": 1,
    "35PX0.075DPBOX025B": 1,
    "35PB0.075DPLID032": 1,
    "A-11528-000": 1,
    "A-11521-000": 1,
    "A-11513-000": 1,
    "35PB0.188BRK034": 1,
}
FORMED = ["A-11528-000", "A-11521-000", "A-11513-000", "35PB0.188BRK034"]
WELD_FLAG = "A-11949-000: weld labor not on parent (waiting on Kyle; not guessed)"
LABEL = "Q10488 Diamond C"


def _tree() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _with_weld(tree: dict) -> dict:
    copied = json.loads(json.dumps(tree))
    grid = []
    for line in copied["grid"]:
        if str(line).startswith("1 1 0 A-11949-000"):
            line = (
                "1 1 0 A-11949-000 dummy in Weld assembly "
                "84.94 lbs 07h 08m 38s $1,087.70 $1,087.70"
            )
        grid.append(line)
    copied["grid"] = grid
    return copied


def _report(tree: dict, *, formed=FORMED):
    from secturafab.quote_qc import check_tree

    return check_tree(tree, EXPECTED, formed=formed, label=LABEL)


def test_q10488_flags_only_missing_weld_labor():
    report = _report(_tree())
    assert report.status == "FLAG"
    assert report.flags == [WELD_FLAG]
    text = report.text()
    assert text.splitlines()[0] == "Q10488 Diamond C — FLAG"
    assert text.splitlines()[1] == f" - {WELD_FLAG}"
    assert text.splitlines()[2] == (
        "8 parts / 10 pcs match LOM · all inch · Contours ok · "
        "4/4 formed have Bend · Err 0 · $1,087.70"
    )


def test_weld_on_parent_passes():
    report = _report(_with_weld(_tree()))
    assert report.status == "PASS"
    assert report.flags == []


def test_negative_component_row():
    tree = _with_weld(_tree())
    tree["rows"][0]["PT"] = 200
    report = _report(tree)
    assert report.status == "FLAG"
    assert "35PX0.105RIB002: producttype_still_component" in report.flags


def test_negative_errorstatus_2():
    tree = _with_weld(_tree())
    tree["rows"][0]["Err"] = 2
    report = _report(tree)
    assert "35PX0.105RIB002: ErrorStatus 2" in report.flags
    assert "Err not 0" in report.summary


def test_negative_contours_zero():
    tree = _with_weld(_tree())
    tree["rows"][0]["C"] = 0
    report = _report(tree)
    assert "35PX0.105RIB002: Contours 0 < 1" in report.flags
    assert "Contours not ok" in report.summary


def test_negative_meter_and_implausible_length():
    tree = _with_weld(_tree())
    tree["rows"][0]["U"] = "meter"
    tree["rows"][0]["Len"] = 182000
    report = _report(tree)
    assert "35PX0.105RIB002: units meter not inch" in report.flags
    assert any("L=182000" in flag for flag in report.flags)
    assert "units not all inch" in report.summary


def test_negative_loose_child_duplicate_and_zero_price():
    tree = _with_weld(_tree())
    tree["rows"][1]["AID"] = None
    report = _report(tree)
    assert any("loose top-level" in flag and "35PX0.075DPBOX025A" in flag for flag in report.flags)

    tree = _with_weld(_tree())
    tree["rows"].append(dict(tree["rows"][0]))
    report = _report(tree)
    assert any(flag.startswith("duplicate lines:") and "35PX0.105RIB002" in flag for flag in report.flags)

    tree = _with_weld(_tree())
    tree["rows"][2]["UP"] = 0
    tree["rows"][2]["UC"] = 0
    report = _report(tree)
    assert "35PX0.075DPBOX025B: zero cost/price" in report.flags


def test_negative_missing_bend_on_formed_part():
    tree = _with_weld(_tree())
    tree["grid"] = [
        line.replace("PRBend", "PR") if "A-11528-000" in line else line
        for line in tree["grid"]
    ]
    report = _report(tree)
    assert "A-11528-000: formed part has no Bend op" in report.flags
    assert "3/4 formed have Bend" in report.summary


def test_missing_dims_and_contours_do_not_invent_zero():
    tree = _with_weld(_tree())
    del tree["rows"][0]["Len"]
    del tree["rows"][0]["C"]
    report = _report(tree)
    assert "35PX0.105RIB002: dims missing" in report.flags
    assert "35PX0.105RIB002: Contours missing" in report.flags
    blob = "\n".join(report.flags)
    assert "L=0" not in blob
    assert "Contours 0" not in blob
    assert "Contours None" not in blob


def test_quote_qc_module_has_no_writes():
    src = Path("secturafab/quote_qc.py").read_text(encoding="utf-8")
    assert not re.search(r"\b(POST|PUT|PATCH)\b", src)
    assert "QuoteItem_ReadTreeListData" in src
    assert "writes nothing" in src


def test_cli_offline_tree_does_not_read_live(tmp_path, monkeypatch):
    from secturafab import quote_qc

    def _boom(_quote_id: str):
        raise AssertionError("live read")

    monkeypatch.setattr(quote_qc, "_default_reader", _boom)
    expected = tmp_path / "expected.json"
    expected.write_text(
        json.dumps({"label": LABEL, "parts": EXPECTED, "formed": FORMED}),
        encoding="utf-8",
    )
    code = quote_qc.main(
        ["--quote", "Q10488", "--expected", str(expected), "--tree", str(FIXTURE)]
    )
    assert code == 1


def test_session_dead_signals_abort():
    from secturafab.chrome_cdp import (
        ANOTHER_USER_BANNER,
        SessionDeadError,
        abort_if_session_dead,
        session_is_dead,
    )

    assert session_is_dead(url="https://www.secturafab.com/Account/Login?return=1") == "login_url"
    assert session_is_dead(url="https://www.secturafab.com/Account/LoginExtra") == "login_url"
    assert session_is_dead(title="SecturaFAB-Login") == "login_title"
    assert (
        session_is_dead(status=302, location="https://www.secturafab.com/Account/Login")
        == "login_redirect"
    )
    assert session_is_dead(body="ok " + ANOTHER_USER_BANNER) == "license_in_use"
    assert session_is_dead(url="https://www.secturafab.com/Quote/EDIT/abc", status=200) is None
    with pytest.raises(SessionDeadError) as raised:
        abort_if_session_dead(title="SecturaFAB-Login")
    assert raised.value.reason == "login_title"


def test_page_native_cad_thickness_recipe_and_inch_finish():
    from secturafab.chrome_cdp import _PAGE_FINISH_JS
    from secturafab.website import CadFinishNotInches, _cad_finish_dim_to_meters

    native = _PAGE_FINISH_JS.split("function applyPageNativeCadThickness")[1].split(
        "function skipFinish"
    )[0]
    assert "#DXFItemType" in native
    assert "kendoDropDownList" in native
    assert 'ddl.value("cad")' in native
    assert 'ddl.trigger("change")' in native
    assert "/Part/UpdateItemType" in native
    assert "#ThicknessEdit" in native
    assert "kendoComboBox" in native
    assert "cb.select(idx)" in native
    assert 'cb.trigger("change")' in native
    assert "onThicknessChangeDXF" in native
    assert "/Quote/GetBorderSize" in native
    assert "ErrorStatus" in native
    assert "wrong_quote" in native
    assert "cb.value" not in native
    assert 'set("Thickness"' not in native
    assert "fetch(" not in native
    assert _PAGE_FINISH_JS.index("applyPageNativeCadThickness(rows, spec)") < _PAGE_FINISH_JS.index(
        "var finishName = findFinishName()"
    )
    assert "OnAddDXFClick" in _PAGE_FINISH_JS
    assert 'r.set("Length_Units", "meter")' not in _PAGE_FINISH_JS
    assert 'throw new Error("units_not_inch")' in _PAGE_FINISH_JS
    with pytest.raises(CadFinishNotInches):
        _cad_finish_dim_to_meters(12.5, "inch")
