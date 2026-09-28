"""Quote-load QC: read-only tree check, session abort, inch Finish."""

from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import MagicMock

import pytest

FIXTURE = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "q10488_p5_tree.json"
LIVE = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "fixtures"
    / "q10488_live_tree_20260928.json"
)
Q10504 = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "fixtures"
    / "q10504_after_finish_tree.json"
)
SUMMARY = (
    "8 parts / 10 pcs match LOM · all inch · Contours ok · "
    "4/4 formed have Bend · Err 0 · $1,087.70"
)
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
    assert text.splitlines()[2] == SUMMARY


def test_q10488_live_tree_flags_only_missing_weld_labor():
    tree = json.loads(LIVE.read_text(encoding="utf-8"))
    assert isinstance(tree.get("Data"), list) and len(tree["Data"]) == 9
    report = _report(tree)
    assert report.status == "FLAG"
    assert report.flags == [WELD_FLAG]
    text = report.text()
    assert text.splitlines()[0] == "Q10488 Diamond C — FLAG"
    assert text.splitlines()[1] == f" - {WELD_FLAG}"
    assert text.splitlines()[2] == SUMMARY


def test_live_parent_id_is_quote_not_assembly_link():
    tree = json.loads(LIVE.read_text(encoding="utf-8"))
    child = tree["Data"][0]
    assert child["ParentID"]
    assert child["ItemNumber"] == "35PX0.105RIB002"
    child["AssemblyName"] = None
    child["AssemblyID"] = None
    report = _report(tree)
    assert any(
        flag.startswith("loose top-level lines with assembly present:")
        and "35PX0.105RIB002" in flag
        for flag in report.flags
    )


def test_live_weld_operation_on_parent_passes():
    tree = json.loads(LIVE.read_text(encoding="utf-8"))
    parent = next(row for row in tree["Data"] if row.get("ProductType") == 300)
    parent["OperationCostList"] = [{"OperationName": "Weld"}]
    report = _report(tree)
    assert report.status == "PASS"
    assert report.flags == []


def test_negative_parent_unit_price_outside_child_sum():
    tree = json.loads(LIVE.read_text(encoding="utf-8"))
    parent = next(row for row in tree["Data"] if row.get("ProductType") == 300)
    parent["OperationCostList"] = [{"OperationName": "Weld"}]
    parent["UnitPrice"] = 1087.72
    report = _report(tree)
    assert report.status == "FLAG"
    assert report.flags == [
        "A-11949-000: parent unit price $1,087.72 is outside $0.01 of child sum $1,087.70"
    ]


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


def test_session_dead_signals_abort(tmp_path, monkeypatch):
    from secturafab.chrome_cdp import (
        ANOTHER_USER_BANNER,
        SessionDeadError,
        abort_if_session_dead,
        session_is_dead,
    )
    from secturafab.web_login import SecturaReloginError, reset_relogin_attempt_for_tests

    monkeypatch.setenv("SECTURA_RELOGIN_ALERT_DIR", str(tmp_path / "alerts"))
    monkeypatch.setenv("SECTURA_RELOGIN_LOCK_DIR", str(tmp_path / "locks"))
    monkeypatch.delenv("SECTURA_WEB_EMAIL", raising=False)
    monkeypatch.delenv("SECTURA_WEB_PASSWORD", raising=False)
    reset_relogin_attempt_for_tests()
    assert session_is_dead(url="https://www.secturafab.com/Account/Login?return=1") == "login_url"
    assert session_is_dead(url="https://www.secturafab.com/Account/LoginExtra") == "login_url"
    assert session_is_dead(title="SecturaFAB-Login") == "login_title"
    assert (
        session_is_dead(status=302, location="https://www.secturafab.com/Account/Login")
        == "login_redirect"
    )
    assert session_is_dead(body="ok " + ANOTHER_USER_BANNER) == "license_in_use"
    assert session_is_dead(url="https://www.secturafab.com/Quote/EDIT/abc", status=200) is None
    with pytest.raises(SecturaReloginError) as raised:
        abort_if_session_dead(title="SecturaFAB-Login")
    assert isinstance(raised.value, SessionDeadError)
    assert raised.value.reason == "login_title: env_missing"
    assert raised.value.page_state == "env_missing"


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
    assert "item.Description" in native
    assert "1e-4" in native
    assert "specIn.thickness" in native
    assert "row.Thickness" not in native
    assert "/Part/UpdateItemType" in native
    assert "armAjax" in native
    assert _PAGE_FINISH_JS.index("applyPageNativeCadThickness(rows, spec)") < _PAGE_FINISH_JS.index(
        "var finishName = findFinishName()"
    )
    assert "OnAddDXFClick" in _PAGE_FINISH_JS
    assert 'r.set("Length_Units", "meter")' not in _PAGE_FINISH_JS
    assert 'throw new Error("units_not_inch")' in _PAGE_FINISH_JS
    with pytest.raises(CadFinishNotInches):
        _cad_finish_dim_to_meters(12.5, "inch")


def test_empty_tree_is_na_not_false_green():
    from secturafab.quote_qc import check_tree

    report = check_tree({"rows": [], "grid": []}, EXPECTED, formed=FORMED, label=LABEL)
    assert report.status == "FLAG"
    assert report.flags == ["no lines"]
    assert report.summary == "n/a"
    text = report.text()
    assert "all inch" not in text
    assert "Contours ok" not in text
    assert "Err 0" not in text
    live_empty = check_tree(
        {"Data": [], "Total": 0, "Errors": None}, EXPECTED, formed=[], label="Q"
    )
    assert live_empty.flags == ["no lines"]
    assert live_empty.summary == "n/a"


def test_single_part_without_assembly_does_not_flag_weld():
    from secturafab.quote_qc import check_tree

    tree = {
        "rows": [
            {
                "N": "A-11521-000",
                "PT": 100,
                "Q": 1,
                "Desc": "A-11521-000  - 14 Ga A36 26.64 in X 37.5 in",
                "U": "inch",
                "Len": 37.5,
                "W": 26.64,
                "C": 1,
                "Err": 0,
                "UP": 10.0,
                "UC": 4.0,
            }
        ],
        "grid": ["1 1 0 A-11521-000 dummy in PR part 1 lbs 1m $10.00 $10.00"],
    }
    report = check_tree(tree, {"A-11521-000": 1}, formed=[], label="Q10504")
    assert report.status == "PASS"
    assert report.flags == []
    assert "$10.00" in report.summary
    assert "price missing" not in report.text()


def test_page_native_description_gauge_and_delayed_errorstatus():
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
        const code = require("fs").readFileSync(process.argv[2], "utf8");
        const row = {
          uid: "u1",
          ItemType: "Cad",
          PartMode: 0,
          ProductType: 100,
          Thickness: 0.075,
          ErrorStatus: 2,
          Material: "A36"
        };
        const items = [{
          Thickness: 0.076,
          Thickness_Units: "inch",
          Value: "0.0760:inch",
          Description: ".076 - 14 Ga"
        }];
        let selected = -1;
        const sandbox = {
          setTimeout, clearTimeout, Date, Promise, console, Math, parseFloat,
          isFinite, Number, String, Object
        };
        sandbox.window = sandbox;
        sandbox.document = { querySelector: () => ({ textContent: "Q10504" }) };
        sandbox.location = { href: "https://www.secturafab.com/Quote/EDIT/qid" };
        function Deferred() {
          const fns = [];
          return {
            always(fn) { fns.push(fn); return this; },
            then(fn) { fns.push(fn); return this; },
            resolve() { fns.forEach((fn) => fn()); }
          };
        }
        sandbox.jQuery = function(sel) {
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
                  dataSource: { data() { return items; } },
                  select(idx) { selected = idx; },
                  trigger() { sandbox.jQuery.ajax({ url: "/Quote/GetBorderSize" }); }
                };
              }
              if (name === "kendoGrid") {
                return {
                  select() {},
                  tbody: { find() { return {}; } },
                  dataSource: { data() { return { toJSON() { return [row]; } }; } }
                };
              }
              return null;
            }
          };
        };
        sandbox.jQuery.ajax = function(opts) {
          const d = Deferred();
          const url = String((opts && opts.url) || "");
          if (url.indexOf("GetBorderSize") >= 0) {
            setTimeout(() => {
              d.resolve();
              setTimeout(() => { row.ErrorStatus = 0; }, 40);
            }, 15);
          } else {
            setTimeout(() => d.resolve(), 10);
          }
          return d;
        };
        sandbox.getSelected = () => selected;
        sandbox.currentErr = () => row.ErrorStatus;
        sandbox.resetErr = () => { row.ErrorStatus = 2; selected = -1; };
        vm.createContext(sandbox);
        const runner = `
          (async () => {
            const rows = [{
              uid: "u1", ItemType: "Cad", PartMode: 0, ProductType: 100,
              Thickness: 0.075, ErrorStatus: 2
            }];
            const described = await applyPageNativeCadThickness(
              rows, { quoteId: "qid", thickness: ".076 - 14 Ga" }
            );
            const describedIdx = getSelected();
            const errAfter = currentErr();
            resetErr();
            const numeric = await applyPageNativeCadThickness(
              rows, { quoteId: "qid", thickness: "0.076" }
            );
            const numericIdx = getSelected();
            resetErr();
            const model = await applyPageNativeCadThickness(
              rows, { quoteId: "qid", thickness: "0.075" }
            );
            const missing = await applyPageNativeCadThickness(
              rows, { quoteId: "qid" }
            );
            return {
              described: described.why,
              describedIdx,
              numeric: numeric.why,
              numericIdx,
              model: model.why,
              missing: missing.why,
              err: errAfter
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
    path = Path(__file__).resolve().parent / "_page_native_thickness_probe.js"
    fn_path = Path(__file__).resolve().parent / "_page_native_thickness_fn.js"
    fn_path.write_text(fn, encoding="utf-8")
    path.write_text(script, encoding="utf-8")
    try:
        proc = subprocess.run(
            [node, str(path), str(fn_path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    finally:
        path.unlink(missing_ok=True)
        fn_path.unlink(missing_ok=True)
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout.strip().splitlines()[-1])
    assert out["described"] == ""
    assert out["describedIdx"] == 0
    assert out["numeric"] == ""
    assert out["numericIdx"] == 0
    assert out["model"] == "gauge_not_in_list"
    assert out["missing"] == "thickness_missing"
    assert out["err"] == 0


def test_finish_cad_files_live_chrome_skips_cookie_reads(tmp_path, monkeypatch):
    from secturafab.push import SecturaFabPushService

    calls: list[dict] = []

    def _ajax(**kwargs):
        calls.append(kwargs)
        if str(kwargs.get("url") or "").endswith("SetUnits"):
            raise RuntimeError("stop-after-units")
        return {"ok": True, "status": 200, "body": "<div id='dxf'></div>"}

    monkeypatch.setattr("secturafab.chrome_cdp.chrome_session_lost", lambda *a, **k: False)
    monkeypatch.setattr("secturafab.chrome_cdp.chrome_quotes_live", lambda *a, **k: True)
    monkeypatch.setattr("secturafab.chrome_cdp.page_jquery_ajax", _ajax)
    stp = tmp_path / "A-11521-000.step"
    stp.write_bytes(b"ISO")
    client = MagicMock()
    client.upload_dxf_via_page_add_files.return_value = {
        "bound": True,
        "files_kendo": True,
        "upload_via": "page_add_files",
        "gridDXF_n": 1,
        "List": [{"SourceDataID": "src-1", "ID": "src-1"}],
    }
    client.create_all_parts_from_grid_dxf.return_value = {"via": "not-yet"}
    service = SecturaFabPushService(client=client)
    with pytest.raises(RuntimeError, match="stop-after-units"):
        service.finish_cad_files(
            quote_id="b78fd84e-4fe3-460d-878d-fd251dafe8e6",
            cad_files=[stp],
            material="A36",
            thickness="0.076",
            qty=1,
            takeoff={},
            bom_rows=[],
            library={},
            extra_pdfs=None,
            part_key="A-11521-000",
            explode_polls=1,
            explode_sleep_s=0,
        )
    urls = [str(call.get("url") or "") for call in calls]
    assert urls == ["/Quote/GetItem_AddView", "/CadImport/SetUnits"]
    assert calls[0]["method"] == "GET"
    assert calls[1]["method"] == "POST"
    assert calls[1]["data"] == {"units": "inch"}
    client.get_item_add_view.assert_not_called()
    client.cadimport_set_units.assert_not_called()
    client.harvest_chrome_antiforgery.assert_not_called()


def test_quote_qc_live_read_is_in_page_ajax():
    src = Path("secturafab/quote_qc.py").read_text(encoding="utf-8")
    assert "page_jquery_ajax" in src
    assert "quote_item_read_treelist" not in src
    assert 'method="GET"' in src


def test_quote_header_number_is_part_and_description_is_title():
    from secturafab.item_desc import title_from_bom_part
    from secturafab.push import quote_header_fields
    from secturafab.quote_qc import check_tree

    number, description = quote_header_fields(
        "A-11949-000", "NECK WINCH BOX ASSEMBLY (CENTERED)"
    )
    assert number == "A-11949-000"
    assert description == "NECK WINCH BOX ASSEMBLY (CENTERED)"
    blank_number, blank_description = quote_header_fields("A-11949-000", "A-11949-000")
    assert blank_number == "A-11949-000"
    assert blank_description == ""
    assert (
        title_from_bom_part(
            [
                {"part_no": "A-11521-000", "description": "14 Ga plate"},
                {
                    "part_no": "A-11949-000",
                    "description": "NECK WINCH BOX ASSEMBLY (CENTERED)",
                },
            ],
            part_key="A-11949-000",
        )
        == "NECK WINCH BOX ASSEMBLY (CENTERED)"
    )
    assert title_from_bom_part(
        [{"part_no": "A-11949-000", "description": "A-11949-000"}],
        part_key="A-11949-000",
    ) is None

    tree = json.loads(Q10504.read_text(encoding="utf-8"))
    tree["QuoteNumber"] = "A-11521-000"
    tree["HeaderDescription"] = "NECK WINCH BOX ASSEMBLY (CENTERED)"
    report = check_tree(
        tree, {"A-11521-000": 1}, formed=["A-11521-000"], label="Q10504"
    )
    assert report.flags == []
    assert "quote Description" not in report.text()

    tree["HeaderDescription"] = ""
    blank = check_tree(
        tree, {"A-11521-000": 1}, formed=["A-11521-000"], label="Q10504"
    )
    assert "quote Description blank" in blank.flags

    tree["HeaderDescription"] = "A-11521-000"
    numbered = check_tree(
        tree, {"A-11521-000": 1}, formed=["A-11521-000"], label="Q10504"
    )
    assert "quote Description is the part number" in numbered.flags

    tree["HeaderDescription"] = "NECK WINCH BOX ASSEMBLY (CENTERED)"
    tree["QuoteNumber"] = "Q10504"
    mismatch = check_tree(
        tree, {"A-11521-000": 1}, formed=["A-11521-000"], label="Q10504"
    )
    assert mismatch.flags == [
        "Quote Number Q10504 does not match top-level part A-11521-000"
    ]


def test_q10504_single_part_sums_line_price():
    from secturafab.quote_qc import check_tree

    tree = json.loads(Q10504.read_text(encoding="utf-8"))
    report = check_tree(
        tree, {"A-11521-000": 1}, formed=["A-11521-000"], label="Q10504"
    )
    assert report.status == "PASS"
    assert report.flags == []
    assert (
        report.summary
        == "1 parts / 1 pcs match LOM · all inch · Contours ok · "
        "1/1 formed have Bend · Err 0 · $177.46"
    )
    assert "price missing" not in report.text()


def test_read_quote_items_live_chrome_reads_tree_in_page(monkeypatch):
    """Chrome-live post-Finish read stays in the page. Q10504 is a Cad plate."""
    from secturafab.push import SecturaFabPushService
    from secturafab.website import (
        WEBSITE_FINISH_PATHS,
        step_cad_post_finish_contours_gate,
        step_finish_pack_missing,
    )

    tree = json.loads(Q10504.read_text(encoding="utf-8"))
    quote_id = "b78fd84e-4fe3-460d-878d-fd251dafe8e6"
    calls: list[dict] = []

    def _ajax(**kwargs):
        calls.append(kwargs)
        return {"ok": True, "status": 200, "body": tree}

    monkeypatch.setattr("secturafab.chrome_cdp.chrome_quotes_live", lambda *a, **k: True)
    monkeypatch.setattr("secturafab.chrome_cdp.page_jquery_ajax", _ajax)
    client = MagicMock()
    posted = SecturaFabPushService(client=client)._read_quote_items(quote_id)
    client.quote_item_read.assert_not_called()
    client.get_json.assert_not_called()
    client.quote_item_read_treelist.assert_not_called()
    assert len(calls) == 1
    assert calls[0]["url"] == WEBSITE_FINISH_PATHS["quote_item_read_treelist"]
    assert calls[0]["method"] == "GET"
    assert calls[0]["data"] == {"ParentID": quote_id}
    assert calls[0]["quote_id"] == quote_id
    row = posted["TreeListData"][0]
    assert row["ItemNumber"] == "A-11521-000"
    assert row["NumberOfContours"] == 1
    assert row["UnitPrice"] == 177.46
    assert step_finish_pack_missing(
        posted, expect_cad=True, expect_linear=False
    ) is None
    assert step_cad_post_finish_contours_gate(posted, expect_cad=True) is None
    data_only = step_finish_pack_missing(tree, expect_cad=True, expect_linear=False)
    assert data_only is not None
    assert "GET 0 Cad after Finish" in data_only
