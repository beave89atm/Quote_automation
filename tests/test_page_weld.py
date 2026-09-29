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


def test_assembly_description_is_posted_after_the_line_exists():
    """The tree starts as the bare part number. The cell change stores the line.

    A hand-built /Quote/UpdatePropertyValue body, with or without the
    anti-forgery token, does not change the stored description. The page
    stores it when the assembly line's Description editor fires change.
    The read-back is QuoteItem_ReadTreeListData, not the request body.
    """
    import json
    import shutil
    import subprocess
    import textwrap

    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")
    from pathlib import Path

    script = textwrap.dedent(
        r"""
        const vm = require("vm");
        const fs = require("fs");
        const code = fs.readFileSync(process.argv[2], "utf8");
        const wanted = process.argv[3];
        const part = process.argv[4];
        const posts = [];
        const parent = {
          ID: "parent-1",
          ItemNumber: part,
          ProductType: 300,
          Description: part,
          AssemblyID: null
        };
        const kid = {
          ID: "kid-1",
          ItemNumber: "A-" + part,
          ProductType: 100,
          Description: "A-" + part,
          AssemblyID: process.argv[5] === "loose" ? null : "parent-1"
        };
        if (process.argv[6]) parent.Description = process.argv[6];
        const reads = [];
        let persistedVia = "";
        let cellOpen = false;
        const sandbox = {
          setTimeout, clearTimeout, Date, Promise, console, JSON, encodeURIComponent,
          Object, String, Number, Array
        };
        sandbox.window = sandbox;
        sandbox.kendo = {
          antiForgeryTokens() {
            return { __RequestVerificationToken: "af-live" };
          }
        };
        sandbox.document = {
          querySelector(sel) {
            if (sel === "#AssemblyName") return { form: null };
            if (sel === "#quote_Text" || sel === "#Description") {
              throw new Error("header field must stay untouched");
            }
            if (String(sel).indexOf("RequestVerification") >= 0) {
              return {
                value: "af-live",
                getAttribute() { return "__RequestVerificationToken"; }
              };
            }
            return null;
          }
        };
        sandbox.AddNewItemHTML = function() {};
        sandbox.OnCopyAll = function() {};
        sandbox.OnAddClick = function() {
          sandbox.jQuery.ajax({
            url: "/Quote/AddItem_Assembly",
            type: "POST",
            data: "AssemblyName=" + encodeURIComponent(part)
          });
        };
        function Deferred() {
          const doneFns = [];
          const failFns = [];
          const alwaysFns = [];
          return {
            done(fn) { doneFns.push(fn); return this; },
            fail(fn) { failFns.push(fn); return this; },
            always(fn) { alwaysFns.push(fn); return this; },
            then(fn) { doneFns.push(fn); return this; },
            resolve(body, status) {
              const xhr = { status: status || 200 };
              doneFns.forEach((fn) => fn(body, "success", xhr));
              alwaysFns.forEach((fn) => fn(body, "success", xhr));
            }
          };
        }
        const parentRow = { ID: parent.ID };
        const kidRow = { ID: kid.ID };
        function descriptionEditor(row) {
          const editor = {
            length: 1,
            _value: "",
            val(v) {
              if (arguments.length === 0) return this._value;
              this._value = v;
              return this;
            },
            trigger(ev) {
              // The page's own change handler is what stores the line.
              // A hand-built UpdatePropertyValue body does not.
              if (
                ev === "change"
                && cellOpen
                && row.ID === parent.ID
              ) {
                const text = String(this._value || "");
                if (text && text.toLowerCase() !== "root") {
                  parent.Description = text;
                  persistedVia = "description-cell";
                }
              }
              return this;
            },
            first() { return this; }
          };
          return editor;
        }
        function descriptionCell(row) {
          const editor = descriptionEditor(row);
          return {
            length: 1,
            find(sel) {
              const text = String(sel || "");
              if (text.indexOf("input") >= 0 || text.indexOf("textarea") >= 0) {
                return editor;
              }
              return { length: 0, first() { return { length: 0 }; } };
            },
            eq() { return this; },
            first() { return this; }
          };
        }
        function wrapTr(row) {
          return {
            length: 1,
            find(sel) {
              const text = String(sel || "");
              if (text.indexOf("Description") >= 0) return descriptionCell(row);
              if (text === "td") {
                return {
                  length: 2,
                  eq(i) { return i === 1 ? descriptionCell(row) : { length: 0 }; }
                };
              }
              return { length: 0 };
            }
          };
        }
        const itemGrid = {
          columns: [{ field: "ItemNumber" }, { field: "Description" }],
          dataSource: { data() { return [kid]; } },
          tbody: {
            find() {
              return {
                length: 2,
                toArray() { return [parentRow, kidRow]; }
              };
            }
          },
          dataItem(tr) {
            if (tr && tr.ID === parent.ID) return parent;
            if (tr && tr.ID === kid.ID) return kid;
            return {};
          },
          editCell() { cellOpen = true; },
          closeCell() { cellOpen = false; }
        };
        sandbox.jQuery = function(sel) {
          if (sel === "#AssemblyName") {
            return { val() { return this; }, trigger() { return this; } };
          }
          if (sel === "#quote_Text" || sel === "#Description") {
            throw new Error("header field must stay untouched");
          }
          if (sel === "#GridItem" || sel === "#GridAssembly") {
            return { data() { return itemGrid; } };
          }
          if (sel && typeof sel === "object" && sel.ID) return wrapTr(sel);
          return {
            data() { return null; },
            val() { return this; },
            trigger() { return this; },
            find() { return { length: 0 }; }
          };
        };
        sandbox.jQuery.ajax = function(opts) {
          const url = String((opts && opts.url) || "");
          posts.push({
            url: url,
            type: String((opts && opts.type) || ""),
            data: opts ? opts.data : null
          });
          const deferred = Deferred();
          setTimeout(() => {
            if (url.indexOf("AddItem_Assembly") >= 0) {
              deferred.resolve("ok", 200);
              return;
            }
            if (url.indexOf("quoteOnline/update") >= 0) {
              deferred.resolve(true, 200);
              return;
            }
            if (url.indexOf("UpdatePropertyValue") >= 0) {
              // Wrong shape, wrong id, or a token-bearing hand-built body:
              // the stored tree does not change.
              deferred.resolve(true, 200);
              return;
            }
            if (url.indexOf("CopyMoveItemToAssembly") >= 0) {
              const data = (opts && opts.data) || {};
              if (data.ItemID === kid.ID && data.AssemblyID) {
                kid.AssemblyID = data.AssemblyID;
              }
              deferred.resolve(true, 200);
              return;
            }
            if (url.indexOf("QuoteItem_ReadTreeListData") >= 0) {
              reads.push(String(parent.Description || ""));
              deferred.resolve({
                Data: [Object.assign({}, parent), Object.assign({}, kid)]
              }, 200);
              return;
            }
            deferred.resolve({}, 200);
          }, 5);
          return deferred;
        };
        vm.createContext(sandbox);
        const runner = "(" + code + ")(" + JSON.stringify({
          name: part,
          quoteId: "qid",
          description: wanted
        }) + ")";
        const started = parent.Description;
        vm.runInContext(runner, sandbox).then((out) => {
          console.log(JSON.stringify({
            out: out,
            posts: posts,
            started: started,
            reads: reads,
            persistedVia: persistedVia
          }));
        }).catch((err) => {
          console.error(err && err.stack || err);
          process.exit(1);
        });
        """
    )
    js_path = Path(__file__).resolve().parent / "_assembly_desc.js"
    run_path = Path(__file__).resolve().parent / "_assembly_desc_run.js"
    js_path.write_text(PAGE_ADD_ASSEMBLY_JS, encoding="utf-8")
    run_path.write_text(script, encoding="utf-8")
    wanted = "11521-000 - ZZ-TEST weldment 2b8fc8c inch push_job 9/29"
    try:
        proc = subprocess.run(
            [node, str(run_path), str(js_path), wanted, "11521-000"],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    finally:
        js_path.unlink(missing_ok=True)
        run_path.unlink(missing_ok=True)
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    posts = payload["posts"]
    assert payload["started"] == "11521-000"
    assert payload["reads"][0] == "11521-000"
    assert payload["reads"][-1] == wanted
    assert payload["persistedVia"] == "description-cell"
    assert payload["out"]["stored_description"] == wanted
    assert payload["out"]["ok"] is True
    assert not any(
        isinstance(row.get("data"), dict) and row["data"].get("parameter") == "Description"
        for row in posts
    )
    assert not any("quoteOnline/update" in row["url"] for row in posts)
    assert not any("quote_Text" in row["url"] for row in posts)
    linear = "1020243-1 - ZZ-TEST linear tube+channel nest+renest 2b8fc8c push_job 9/29"
    js_path.write_text(PAGE_ADD_ASSEMBLY_JS, encoding="utf-8")
    run_path.write_text(script, encoding="utf-8")
    try:
        proc = subprocess.run(
            [node, str(run_path), str(js_path), linear, "1020243-1"],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    finally:
        js_path.unlink(missing_ok=True)
        run_path.unlink(missing_ok=True)
    assert proc.returncode == 0, proc.stderr
    linear_out = json.loads(proc.stdout.strip().splitlines()[-1])
    assert linear_out["started"] == "1020243-1"
    assert linear_out["reads"][0] == "1020243-1"
    assert linear_out["reads"][-1] == linear
    assert linear_out["persistedVia"] == "description-cell"
    assert linear_out["out"]["stored_description"] == linear
    assert linear_out["out"]["ok"] is True
    bare_parent = "34887-1 - chosen description"
    js_path.write_text(PAGE_ADD_ASSEMBLY_JS, encoding="utf-8")
    run_path.write_text(script, encoding="utf-8")
    try:
        proc = subprocess.run(
            [node, str(run_path), str(js_path), bare_parent, "34887-1"],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    finally:
        js_path.unlink(missing_ok=True)
        run_path.unlink(missing_ok=True)
    assert proc.returncode == 0, proc.stderr
    parent_out = json.loads(proc.stdout.strip().splitlines()[-1])
    assert parent_out["started"] == "34887-1"
    assert parent_out["reads"][0] == "34887-1"
    assert parent_out["reads"][-1] == bare_parent
    assert parent_out["persistedVia"] == "description-cell"
    assert parent_out["out"]["stored_description"] == bare_parent
    assert parent_out["out"]["ok"] is True
    rooted = "34887-1 - chosen description"
    js_path.write_text(PAGE_ADD_ASSEMBLY_JS, encoding="utf-8")
    run_path.write_text(script, encoding="utf-8")
    try:
        proc = subprocess.run(
            [node, str(run_path), str(js_path), rooted, "34887-1", "linked", "Root"],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    finally:
        js_path.unlink(missing_ok=True)
        run_path.unlink(missing_ok=True)
    assert proc.returncode == 0, proc.stderr
    root_out = json.loads(proc.stdout.strip().splitlines()[-1])
    assert root_out["started"] == "Root"
    assert root_out["reads"][0] == "Root"
    assert root_out["reads"][-1] == rooted
    assert root_out["out"]["stored_description"] == rooted
    assert root_out["out"]["stored_description"] != "Root"
    assert root_out["out"]["ok"] is True
    loose_wanted = "34887-1 - chosen description"
    js_path.write_text(PAGE_ADD_ASSEMBLY_JS, encoding="utf-8")
    run_path.write_text(script, encoding="utf-8")
    try:
        proc = subprocess.run(
            [node, str(run_path), str(js_path), loose_wanted, "34887-1", "loose"],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    finally:
        js_path.unlink(missing_ok=True)
        run_path.unlink(missing_ok=True)
    assert proc.returncode == 0, proc.stderr
    loose_out = json.loads(proc.stdout.strip().splitlines()[-1])
    assert loose_out["started"] == "34887-1"
    assert loose_out["reads"][0] == "34887-1"
    assert loose_out["reads"][-1] == loose_wanted
    assert loose_out["persistedVia"] == "description-cell"
    assert loose_out["out"]["ok"] is True, loose_out["out"]
    assert loose_out["out"]["stored_description"] == loose_wanted
    assert any("CopyMoveItemToAssembly" in row["url"] for row in loose_out["posts"])


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
