"""ZZ Q10506 weldment path: selection, units, assembly persist, quote number."""

from __future__ import annotations

from unittest.mock import MagicMock

from secturafab.page_weld import (
    PAGE_ADD_ASSEMBLY_JS,
    PAGE_UPDATE_ASSEMBLY_JS,
    STEP_MM_CONTINUE_NOTE,
    add_page_assembly,
    assembly_tree_problems,
    set_page_quote_number,
    step_header_is_millimetre,
    update_existing_assembly_name,
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
    """AddItem_Assembly stores #AssemblyName as the tree Description.

    A formatted description is that name. The bare part number is not.
    #assemblyDescription does not persist, and AddItem_Assembly does not
    take a Description parameter. ItemNumber is the same string.
    """
    import json
    import shutil
    import subprocess
    import textwrap
    from urllib.parse import unquote

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
        let assemblyNameValue = "";
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
        const treeEl = { id: "quote-lines" };
        let panelShowing = false;
        const writerTargets = [];
        sandbox.document = {
          querySelector(sel) {
            if (sel === "#AssemblyName") return { form: null };
            if (sel === "#assemblyDescription") return null;
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
          },
          querySelectorAll(sel) {
            const text = String(sel || "");
            if (text.indexOf("treelist") >= 0) return [treeEl];
            return [];
          }
        };
        sandbox.AddNewItemHTML = function() {};
        sandbox.OnCopyAll = function() {};
        sandbox.OnAddClick = function() {
          const storedName = assemblyNameValue || part;
          parent.Description = storedName;
          parent.ItemNumber = storedName;
          sandbox.jQuery.ajax({
            url: "/Quote/AddItem_Assembly",
            type: "POST",
            data: "name=" + encodeURIComponent(storedName)
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
        const gridParentRow = { ID: parent.ID, kind: "grid" };
        const gridKidRow = { ID: kid.ID, kind: "grid" };
        const treeParentRow = { ID: parent.ID, kind: "tree" };
        const treeKidRow = { ID: kid.ID, kind: "tree" };
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
              // A TreeList cell and #GridItem do not store the line.
              if (ev === "change" && cellOpen) {
                writerTargets.push(row.kind === "tree" ? "treelist" : "GridItem");
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
                toArray() { return [gridParentRow, gridKidRow]; }
              };
            }
          },
          dataItem(tr) {
            if (tr && tr.kind === "grid" && tr.ID === parent.ID) return parent;
            if (tr && tr.kind === "grid" && tr.ID === kid.ID) return kid;
            return {};
          },
          editCell() { cellOpen = true; writerTargets.push("GridItem"); },
          select() { writerTargets.push("GridItem"); return { length: 1 }; },
          closeCell() { cellOpen = false; }
        };
        const quoteTr = { ID: parent.ID };
        const quoteGrid = {
          dataSource: { data() { return [parent]; } },
          tbody: {
            find() {
              return { length: 1, toArray() { return [quoteTr]; } };
            }
          },
          dataItem(tr) {
            if (tr && tr.ID === parent.ID) return parent;
            return {};
          },
          select(tr) {
            if (tr && tr.ID === parent.ID) panelShowing = true;
            return { length: 1 };
          }
        };
        const lineTree = {
          columns: [{ field: "ItemNumber" }, { field: "Description" }],
          dataSource: {
            options: {
              transport: { read: { url: "/Quote/QuoteItem_ReadTreeListData" } }
            }
          },
          tbody: {
            find() {
              return {
                length: 2,
                toArray() { return [treeParentRow, treeKidRow]; }
              };
            }
          },
          dataItem(tr) {
            if (tr && tr.kind === "tree" && tr.ID === parent.ID) return parent;
            if (tr && tr.kind === "tree" && tr.ID === kid.ID) return kid;
            return {};
          },
          editCell() { cellOpen = true; },
          closeCell() { cellOpen = false; }
        };
        sandbox.jQuery = function(sel) {
          if (sel === "#AssemblyName") {
            return {
              val(v) {
                if (arguments.length === 0) return assemblyNameValue;
                assemblyNameValue = String(v == null ? "" : v);
                return this;
              },
              trigger() { return this; }
            };
          }
          if (sel === "#quote_Text" || sel === "#Description") {
            throw new Error("header field must stay untouched");
          }
          if (sel === "#assemblyDescription") {
            return {
              val() { return this; },
              trigger() { return this; }
            };
          }
          if (sel === "#gridQuoteItems") {
            return { data() { return quoteGrid; } };
          }
          if (sel === "#GridItem" || sel === "#GridAssembly") {
            return {
              data(name) {
                if (name === "kendoTreeList") return null;
                return itemGrid;
              }
            };
          }
          if (sel === treeEl) {
            return {
              data(name) {
                if (name === "kendoTreeList") return lineTree;
                return null;
              }
            };
          }
          if (sel && typeof sel === "object" && sel.kind) return wrapTr(sel);
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
            assemblyName: assemblyNameValue,
            itemNumber: parent.ItemNumber
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
    wanted = "11521-000 - DIAG DESC"
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
    add_posts = [row for row in posts if "AddItem_Assembly" in row["url"]]
    assert payload["started"] == "11521-000"
    assert payload["assemblyName"] == wanted
    assert payload["assemblyName"] != "11521-000"
    assert payload["reads"][0] == wanted
    assert payload["reads"][-1] == wanted
    assert payload["itemNumber"] == wanted
    assert payload["out"]["stored_description"] == wanted
    assert payload["out"]["ok"] is True
    assert add_posts
    add_body = unquote(str(add_posts[0].get("data") or ""))
    assert wanted in add_body
    assert "Description=" not in add_body
    assert not any(
        isinstance(row.get("data"), dict) and "Description" in (row.get("data") or {})
        for row in add_posts
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
    assert linear_out["assemblyName"] == linear
    assert linear_out["assemblyName"] != "1020243-1"
    assert linear_out["reads"][0] == linear
    assert linear_out["reads"][-1] == linear
    assert linear_out["itemNumber"] == linear
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
    assert parent_out["assemblyName"] == bare_parent
    assert parent_out["assemblyName"] != "34887-1"
    assert parent_out["reads"][0] == bare_parent
    assert parent_out["reads"][-1] == bare_parent
    assert parent_out["itemNumber"] == bare_parent
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
    assert root_out["assemblyName"] == rooted
    assert root_out["assemblyName"] != "34887-1"
    assert root_out["reads"][0] == rooted
    assert root_out["reads"][-1] == rooted
    assert root_out["itemNumber"] == rooted
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
    assert loose_out["assemblyName"] == loose_wanted
    assert loose_out["assemblyName"] != "34887-1"
    assert loose_out["reads"][0] == loose_wanted
    assert loose_out["reads"][-1] == loose_wanted
    assert loose_out["itemNumber"] == loose_wanted
    assert loose_out["out"]["ok"] is True, loose_out["out"]
    assert loose_out["out"]["stored_description"] == loose_wanted
    assert any("CopyMoveItemToAssembly" in row["url"] for row in loose_out["posts"])
    js_path.write_text(PAGE_ADD_ASSEMBLY_JS, encoding="utf-8")
    run_path.write_text(script, encoding="utf-8")
    try:
        proc = subprocess.run(
            [node, str(run_path), str(js_path), "", "11521-000"],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    finally:
        js_path.unlink(missing_ok=True)
        run_path.unlink(missing_ok=True)
    assert proc.returncode == 0, proc.stderr
    empty_out = json.loads(proc.stdout.strip().splitlines()[-1])
    assert empty_out["assemblyName"] == "11521-000"
    assert empty_out["reads"][0] == "11521-000"
    assert empty_out["itemNumber"] == "11521-000"
    assert empty_out["out"]["ok"] is True, empty_out["out"]


def test_one_file_assembly_name_is_the_update_click():
    """One STEP parent already exists. Rename it with Update Assembly.

    DoEditItem opens that line. #AssemblyName is the formatted
    description. One click on #asmAdd-but posts AddItem_Assembly
    because QuoteItemID is the existing line. A PartName write, a
    hand-built AddItem_Assembly body, and a direct OnAddAssemblyClick
    do not change the tree.
    """
    import inspect
    import json
    import shutil
    import subprocess
    import textwrap
    from pathlib import Path
    from urllib.parse import unquote

    import pytest

    from secturafab.chrome_cdp import _PAGE_FINISH_JS, invoke_page_dxf_finish
    from secturafab.client import SecturaFabClient
    from secturafab.push import SecturaFabPushService

    wanted = "34887-1 - ZZ-TEST assembly update on the tree"
    assert "writeAssemblyPartName" not in _PAGE_FINISH_JS
    assert "assemblyDescription" not in _PAGE_FINISH_JS
    assert "DoEditItem" in PAGE_UPDATE_ASSEMBLY_JS
    assert 'jQuery("#AssemblyName")' in PAGE_UPDATE_ASSEMBLY_JS
    assert "#asmAdd-but" in PAGE_UPDATE_ASSEMBLY_JS
    assert "AddNewItemHTML" not in PAGE_UPDATE_ASSEMBLY_JS
    assert "OnCopyAll" not in PAGE_UPDATE_ASSEMBLY_JS
    assert "OnAddClick" not in PAGE_UPDATE_ASSEMBLY_JS
    assert "OnAddAssemblyClick" not in PAGE_UPDATE_ASSEMBLY_JS
    assert "PartName" not in PAGE_UPDATE_ASSEMBLY_JS
    assert "#gridDXFParts" not in PAGE_UPDATE_ASSEMBLY_JS
    assert "#quote_Text" not in PAGE_UPDATE_ASSEMBLY_JS
    assert "#Description" not in PAGE_UPDATE_ASSEMBLY_JS
    assert "assembly_description" not in inspect.signature(invoke_page_dxf_finish).parameters
    assert "assembly_description" not in inspect.signature(
        SecturaFabClient.add_item_dxf_files
    ).parameters
    assert "assembly_description" not in inspect.signature(
        SecturaFabPushService.finish_cad_files
    ).parameters
    push_src = (
        Path(__file__).resolve().parents[1] / "secturafab" / "push.py"
    ).read_text(encoding="utf-8")
    cad_branch = push_src.split("if len(cad) >= 2:", 1)[1].split(
        "uploaded.extend", 1
    )[0]
    multi, one = cad_branch.split("elif len(cad) == 1", 1)
    assert "add_page_assembly(" in multi
    assert "update_existing_assembly_name(" in one
    assert "add_page_assembly(" not in one
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")
    script = textwrap.dedent(
        r"""
        const vm = require("vm");
        const fs = require("fs");
        const code = fs.readFileSync(process.argv[2], "utf8");
        const spec = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
        const wanted = spec.description;
        const mode = spec.mode;
        const parentId = "parent-1";
        const parent = {
          ID: parentId,
          ProductType: 300,
          Description: "34887-1",
          ItemNumber: "34887-1",
          AssemblyID: null,
          Name: null,
          ProductDescription: null
        };
        const kids = [
          {
            ID: "k-34892", ItemNumber: "34892", Description: "34892",
            ProductType: 100, AssemblyID: parentId, Price: 129,
            Thickness: 0.1875, Qty: 1
          },
          {
            ID: "k-34889", ItemNumber: "34889", Description: "34889",
            ProductType: 100, AssemblyID: parentId, Price: 169.88, Qty: 1
          },
          {
            ID: "k-10187", ItemNumber: "10187", Description: "10187",
            ProductType: 10, AssemblyID: parentId, Price: 16.37, Qty: 1
          }
        ];
        const kidSnap = JSON.stringify(kids);
        let formOpen = false;
        let quoteItemId = "";
        let assemblyNameValue = "";
        let fromButton = false;
        let clicks = 0;
        let directCall = false;
        let secondParent = false;
        let partNameWrite = false;
        let dirty = false;
        let nameAtClick = "";
        let quoteItemAtClick = "";
        const trace = [];
        const posts = [];
        const reads = [];
        const button = {
          id: "asmAdd-but",
          textContent: "",
          value: "",
          click() {
            if (!formOpen) return;
            clicks += 1;
            trace.push("click");
            nameAtClick = assemblyNameValue;
            quoteItemAtClick = quoteItemId;
            fromButton = true;
            try { sandbox.OnAddAssemblyClick(); }
            finally { fromButton = false; }
          }
        };
        const quoteEl = {
          id: "QuoteItemID",
          get value() { return quoteItemId; },
          set value(v) {
            if (String(v) !== parentId) dirty = true;
            quoteItemId = String(v);
          }
        };
        const dxfRow = { uid: "body", Name: "34887-1" };
        Object.defineProperty(dxfRow, "PartName", {
          get() { return this._partName; },
          set(v) { this._partName = v; partNameWrite = true; }
        });
        dxfRow._partName = "34887-1";
        const sandbox = {
          setTimeout, clearTimeout, Date, Promise, console, JSON,
          encodeURIComponent, Object, String, Number, Array
        };
        sandbox.window = sandbox;
        sandbox.DoEditItem = function(id) {
          trace.push("DoEditItem:" + id);
          if (String(id) !== parentId) {
            secondParent = true;
            return;
          }
          formOpen = true;
          quoteItemId = parentId;
          assemblyNameValue = parent.Description;
          button.textContent = "Update Assembly";
        };
        sandbox.OnAddAssemblyClick = function() {
          if (!fromButton) {
            directCall = true;
            return;
          }
          if (quoteItemId !== parentId) {
            secondParent = true;
            return;
          }
          parent.Description = assemblyNameValue;
          parent.ItemNumber = assemblyNameValue;
          sandbox.jQuery.ajax({
            url: "/Quote/AddItem_Assembly",
            type: "POST",
            data: "name=" + encodeURIComponent(assemblyNameValue)
          });
        };
        sandbox.OnAddClick = function() { directCall = true; };
        sandbox.AddNewItemHTML = function() { secondParent = true; };
        sandbox.OnCopyAll = function() { dirty = true; };
        sandbox.document = {
          querySelector(sel) {
            if (sel === "#quote_Text" || sel === "#Description") {
              throw new Error("header field must stay untouched");
            }
            if (!formOpen) return null;
            if (sel === "#newItem") return { id: "newItem" };
            if (sel === "#QuoteItemID") return quoteEl;
            if (sel === "#asmAdd-but") return button;
            if (sel === "#AssemblyName") return { id: "AssemblyName" };
            return null;
          }
        };
        function treeData() {
          if (mode === "no-parent") {
            return [{
              ID: "plate-1",
              ProductType: 100,
              Description: "34889 PLATE",
              ItemNumber: "34889",
              AssemblyID: null,
              Price: 129
            }];
          }
          return [Object.assign({}, parent)].concat(
            kids.map((kid) => Object.assign({}, kid))
          );
        }
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
        const blocked = new Set([
          "#Qty", "#Price", "#Memo", "#Quantity", "#UnitPrice", "#asmQty",
          "#AssemblyQty", "#AssemblyPrice", "#txtMemo", "#MemoText", "#LineMemo"
        ]);
        sandbox.jQuery = function(sel) {
          if (sel === "#quote_Text" || sel === "#Description") {
            throw new Error("header field must stay untouched");
          }
          if (sel === "#AssemblyName") {
            return {
              val(v) {
                if (arguments.length === 0) return assemblyNameValue;
                trace.push("AssemblyName:" + v);
                assemblyNameValue = String(v == null ? "" : v);
                return this;
              },
              trigger() { return this; }
            };
          }
          if (sel === "#asmAdd-but") {
            return {
              click() {
                button.click();
                return this;
              },
              text() { return button.textContent; }
            };
          }
          if (blocked.has(sel)) {
            return {
              val(v) {
                if (arguments.length) dirty = true;
                return arguments.length ? this : "";
              },
              trigger() { return this; }
            };
          }
          if (sel === "#gridDXFParts") {
            return {
              data() {
                return {
                  dataSource: {
                    data() { return [dxfRow]; },
                    remove() { dirty = true; }
                  }
                };
              }
            };
          }
          if (sel === "#GridAssembly" || sel === "#GridItem") {
            return {
              data() {
                return {
                  dataSource: {
                    data() { return kids; },
                    remove() { dirty = true; },
                    insert() { dirty = true; }
                  }
                };
              },
              val(v) {
                if (arguments.length) dirty = true;
                return this;
              }
            };
          }
          return {
            val(v) {
              if (arguments.length) dirty = true;
              return arguments.length ? this : "";
            },
            trigger() { return this; },
            data() { return null; }
          };
        };
        sandbox.jQuery.ajax = function(opts) {
          const url = String((opts && opts.url) || "");
          posts.push({
            url: url,
            type: String((opts && opts.type) || ""),
            data: opts ? opts.data : null,
            fromButton: fromButton
          });
          const deferred = Deferred();
          setTimeout(() => {
            if (url.indexOf("QuoteItem_ReadTreeListData") >= 0) {
              const rows = treeData();
              reads.push({
                clicks: clicks,
                parents: rows.filter((row) => row.ProductType === 300).map((row) => ({
                  ID: row.ID,
                  Description: row.Description,
                  ItemNumber: row.ItemNumber
                }))
              });
              deferred.resolve({ Data: rows }, 200);
              return;
            }
            deferred.resolve("ok", 200);
          }, 5);
          return deferred;
        };
        vm.createContext(sandbox);
        const runner = "(" + code + ")(" + JSON.stringify({
          quoteId: "qid",
          description: wanted
        }) + ")";
        vm.runInContext(runner, sandbox).then((out) => {
          console.log(JSON.stringify({
            out: out,
            trace: trace,
            clicks: clicks,
            directCall: directCall,
            secondParent: secondParent,
            partNameWrite: partNameWrite,
            dirty: dirty,
            nameAtClick: nameAtClick,
            quoteItemAtClick: quoteItemAtClick,
            posts: posts,
            reads: reads,
            parent: parent,
            kids: kids,
            kidsSame: JSON.stringify(kids) === kidSnap,
            finalTree: treeData()
          }));
        }).catch((err) => {
          console.error(err && err.stack || err);
          process.exit(1);
        });
        """
    )
    js_path = Path(__file__).resolve().parent / "_assembly_update.js"
    run_path = Path(__file__).resolve().parent / "_assembly_update_run.js"
    spec_path = Path(__file__).resolve().parent / "_assembly_update_spec.json"

    def _run(mode: str) -> dict:
        js_path.write_text(PAGE_UPDATE_ASSEMBLY_JS, encoding="utf-8")
        run_path.write_text(script, encoding="utf-8")
        spec_path.write_text(
            json.dumps({"mode": mode, "description": wanted}),
            encoding="utf-8",
        )
        proc = subprocess.run(
            [node, str(run_path), str(js_path), str(spec_path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
        assert proc.returncode == 0, proc.stderr
        return json.loads(proc.stdout.strip().splitlines()[-1])

    try:
        payload = _run("update")
    finally:
        js_path.unlink(missing_ok=True)
        run_path.unlink(missing_ok=True)
        spec_path.unlink(missing_ok=True)
    trace = payload["trace"]
    edit_at = trace.index("DoEditItem:parent-1")
    name_at = max(i for i, event in enumerate(trace) if event.startswith("AssemblyName:"))
    click_at = trace.index("click")
    assert edit_at < name_at < click_at
    assert trace[name_at] == "AssemblyName:" + wanted
    assert payload["clicks"] == 1
    assert payload["nameAtClick"] == wanted
    assert payload["quoteItemAtClick"] == "parent-1"
    assert payload["directCall"] is False
    assert payload["secondParent"] is False
    assert payload["partNameWrite"] is False
    assert payload["dirty"] is False
    assert payload["kidsSame"] is True
    assert payload["reads"][0]["clicks"] == 0
    assert payload["reads"][0]["parents"] == [
        {"ID": "parent-1", "Description": "34887-1", "ItemNumber": "34887-1"}
    ]
    assert payload["reads"][-1]["clicks"] == 1
    assert payload["reads"][-1]["parents"] == [
        {"ID": "parent-1", "Description": wanted, "ItemNumber": wanted}
    ]
    assert payload["parent"]["ID"] == "parent-1"
    assert payload["parent"]["Description"] == wanted
    assert payload["parent"]["ItemNumber"] == wanted
    assert payload["out"]["ok"] is True
    assert payload["out"]["parent_id"] == "parent-1"
    assert payload["out"]["stored_description"] == wanted
    assert payload["out"]["stored_item_number"] == wanted
    assert payload["out"]["kid_ids"] == ["k-34892", "k-34889", "k-10187"]
    parents = [row for row in payload["finalTree"] if row.get("ProductType") == 300]
    assert len(parents) == 1
    assert parents[0]["ID"] == "parent-1"
    kids_out = [row for row in payload["finalTree"] if row.get("ID") != "parent-1"]
    assert [row["ItemNumber"] for row in kids_out] == ["34892", "34889", "10187"]
    assert all(row["AssemblyID"] == "parent-1" for row in kids_out)
    by_pn = {row["ItemNumber"]: row for row in kids_out}
    assert by_pn["34892"]["Price"] == 129
    assert by_pn["34892"]["Thickness"] == 0.1875
    assert by_pn["34889"]["Price"] == 169.88
    assert by_pn["10187"]["Price"] == 16.37
    add_posts = [row for row in payload["posts"] if "AddItem_Assembly" in row["url"]]
    assert len(add_posts) == 1
    assert add_posts[0]["fromButton"] is True
    assert wanted in unquote(str(add_posts[0].get("data") or ""))
    try:
        skipped = _run("no-parent")
    finally:
        js_path.unlink(missing_ok=True)
        run_path.unlink(missing_ok=True)
        spec_path.unlink(missing_ok=True)
    assert skipped["trace"] == []
    assert skipped["clicks"] == 0
    assert skipped["secondParent"] is False
    assert skipped["directCall"] is False
    assert skipped["partNameWrite"] is False
    assert skipped["out"]["skipped"] is True
    assert skipped["out"]["why"] == "no_assembly_parent"
    assert skipped["out"]["posted_additem"] is False
    assert not any(row.get("ProductType") == 300 for row in skipped["finalTree"])


def test_one_file_update_skips_a_bare_name_and_rejects_a_bare_readback(monkeypatch):
    """A bare part number is not a rename. A read-back that stays bare fails."""
    monkeypatch.setattr(
        "secturafab.chrome_cdp._cdp_evaluate_promise",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("page must stay closed")),
    )
    assert update_existing_assembly_name(quote_id="qid", description="34887-1") == []
    assert update_existing_assembly_name(quote_id="qid", description="") == []
    wanted = "34887-1 - ZZ-TEST assembly update on the tree"
    seen = {}

    def _eval(expression, **kwargs):
        seen["expression"] = expression
        return {
            "ok": True,
            "posted_additem": True,
            "skipped": False,
            "parent_id": "parent-1",
            "stored_description": wanted,
            "stored_item_number": wanted,
            "kid_ids": ["k-34892", "k-34889", "k-10187"],
        }

    monkeypatch.setattr(
        "secturafab.chrome_cdp.minted_edit_tab_ready",
        lambda *a, **k: {"ok": True, "tab": {"webSocketDebuggerUrl": "ws://local"}},
    )
    monkeypatch.setattr("secturafab.chrome_cdp._cdp_evaluate_promise", _eval)
    monkeypatch.setattr(
        "secturafab.chrome_cdp.page_jquery_ajax",
        lambda **kwargs: {
            "ok": True,
            "body": {
                "Data": [
                    {
                        "ID": "parent-1",
                        "ProductType": 300,
                        "Description": "34887-1",
                        "ItemNumber": "34887-1",
                        "AssemblyID": None,
                    }
                ]
            },
        },
    )
    notes = update_existing_assembly_name(quote_id="qid", description=wanted)
    assert "DoEditItem" in seen["expression"]
    assert wanted in seen["expression"]
    assert any("assembly_description_not_stored" in note for note in notes)


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
