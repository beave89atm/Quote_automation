"""Page-native weldment steps proven on ZZ Q10506.

Selection, units, assembly persist, and the quote-number change are
fail-closed. This module does not read cookies and does not log secrets.
"""

from __future__ import annotations

import json
import re
from typing import Any

_MM_HEADER_RE = re.compile(
    r"SI_UNIT\s*\(\s*\.MILLI\.\s*,\s*\.METRE\.\s*\)",
    re.IGNORECASE,
)
STEP_MM_NOTE = (
    "STEP header SI_UNIT(.MILLI.,.METRE.) — not calling SetDXFFileUnits('inch')"
)

_PAGE_SET_PROPERTY_JS = r"""(async function(spec) {
  var sel = spec.parameter === "QuoteNumber" ? "#quote_Text" : "#Description";
  if (!window.jQuery) return {ok: false, why: "no_jquery", parameter: spec.parameter};
  if (!document.querySelector(sel)) {
    return {ok: false, why: "header_field_missing", parameter: spec.parameter};
  }
  var posted = "";
  var orig = jQuery.ajax;
  jQuery.ajax = function(opts) {
    var url = "";
    if (typeof opts === "string") url = opts;
    else if (opts && opts.url) url = String(opts.url);
    if (!posted && url.indexOf("/Quote/UpdatePropertyValue") >= 0) {
      var data = opts && opts.data;
      if (typeof data === "string") posted = data;
      else {
        try { posted = JSON.stringify(data || {}); } catch (e) { posted = ""; }
      }
    }
    return orig.apply(this, arguments);
  };
  try {
    jQuery(sel).val(spec.value).trigger("change");
  } catch (e2) {
    jQuery.ajax = orig;
    return {ok: false, why: "header_change_failed", parameter: spec.parameter};
  }
  var deadline = Date.now() + 4000;
  while (!posted && Date.now() < deadline) {
    await new Promise(function(resolve) { setTimeout(resolve, 25); });
  }
  jQuery.ajax = orig;
  if (!posted) return {ok: false, why: "update_property_missing", parameter: spec.parameter};
  var paramOk = posted.indexOf("parameter=" + spec.parameter) >= 0
    || posted.indexOf('"parameter":"' + spec.parameter + '"') >= 0;
  var valueOk = spec.value && posted.indexOf(String(spec.value)) >= 0;
  if (!paramOk || !valueOk) {
    return {ok: false, why: "update_property_mismatch", parameter: spec.parameter};
  }
  return {ok: true, why: "", parameter: spec.parameter};
})"""

PAGE_ADD_ASSEMBLY_JS = r"""(async function(spec) {
  var name = String((spec && spec.name) || "").trim();
  if (!name) return {ok: false, why: "assembly_name_missing", posted_additem: false};
  if (!window.jQuery) return {ok: false, why: "no_jquery", posted_additem: false};
  if (typeof AddNewItemHTML === "function") {
    try { AddNewItemHTML("assembly", "top"); } catch (e0) {}
  }
  if (!document.querySelector("#AssemblyName")) {
    return {ok: false, why: "assembly_name_field_missing", posted_additem: false};
  }
  jQuery("#AssemblyName").val(name).trigger("change");
  var before = 0;
  try {
    before = jQuery("#GridItem").data("kendoGrid").dataSource.data().length;
  } catch (e1) { before = 0; }
  if (typeof OnCopyAll !== "function") {
    return {ok: false, why: "no_oncopyall", posted_additem: false};
  }
  OnCopyAll();
  var staged = 0;
  try {
    staged = jQuery("#GridAssembly").data("kendoGrid").dataSource.data().length;
  } catch (e2) { staged = 0; }
  if (before < 1 || staged !== before) {
    return {ok: false, why: "copyall_not_staged", posted_additem: false, staged: staged};
  }
  if (typeof OnAddClick !== "function") {
    return {ok: false, why: "no_onaddclick", posted_additem: false, staged: staged};
  }
  var posted = false;
  var orig = jQuery.ajax;
  jQuery.ajax = function(opts) {
    var url = "";
    if (typeof opts === "string") url = opts;
    else if (opts && opts.url) url = String(opts.url);
    if (url.indexOf("/Quote/AddItem_Assembly") >= 0) posted = true;
    return orig.apply(this, arguments);
  };
  try { OnAddClick(); } catch (e3) {}
  var deadline = Date.now() + 8000;
  while (!posted && Date.now() < deadline) {
    await new Promise(function(resolve) { setTimeout(resolve, 25); });
  }
  jQuery.ajax = orig;
  if (!posted) {
    return {ok: false, why: "additem_assembly_missing", posted_additem: false, staged: staged};
  }
  return {ok: true, why: "", posted_additem: true, staged: staged};
})"""


def step_header_is_millimetre(text: str) -> bool:
    """True when the STEP header is SI_UNIT(.MILLI.,.METRE.)."""
    return bool(_MM_HEADER_RE.search(text or ""))


def step_unit_fail_note(notes: list[str] | None) -> str | None:
    for note in notes or []:
        if STEP_MM_NOTE in str(note):
            return str(note)
    return None


def set_units_body(source_id: str) -> dict[str, Any]:
    """Body SetDXFFileUnits posts: IDList + Units, one source id."""
    return {"IDList": [str(source_id)], "Units": "inch"}


def _assembly_id(row: dict[str, Any]) -> str:
    return str(row.get("AssemblyID") or row.get("AID") or "").strip()


def _is_assembly_parent(row: dict[str, Any]) -> bool:
    if _assembly_id(row):
        return False
    pt = row.get("ProductType", row.get("PT"))
    if pt in (300, "300"):
        return True
    if row.get("IsAssembly") is True:
        return True
    cat = str(row.get("ItemType") or row.get("Category") or "")
    return cat == "Assembly"


def assembly_tree_problems(
    rows: list[dict[str, Any]] | None,
    *,
    kid_count: int | None = None,
) -> str:
    """Empty string when the tree is one parent, N kids, and no loose lines."""
    parents = [row for row in rows or [] if isinstance(row, dict) and _is_assembly_parent(row)]
    if len(parents) != 1:
        return "assembly_parent_missing" if not parents else "assembly_parent_not_one"
    parent_id = str(parents[0].get("ID") or parents[0].get("Id") or "").strip()
    if not parent_id:
        return "assembly_parent_missing"
    kids = []
    loose = 0
    for row in rows or []:
        if not isinstance(row, dict) or row is parents[0]:
            continue
        if _assembly_id(row) == parent_id:
            kids.append(row)
        else:
            loose += 1
    if loose:
        return "assembly_loose_line"
    if kid_count is not None and len(kids) != int(kid_count):
        return "assembly_kid_count"
    if not kids:
        return "assembly_kid_count"
    return ""


def tree_rows(body: Any) -> list[dict[str, Any]]:
    payload = body
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            return []
    if isinstance(payload, dict):
        data = payload.get("Data")
        if data is None:
            data = payload.get("rows")
        if isinstance(data, list):
            return [row for row in data if isinstance(row, dict)]
        return []
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    return []


def set_page_quote_number(quote_id: str, quote_number: str) -> list[str]:
    """Set #quote_Text through its change event. The value is not logged."""
    number = str(quote_number or "").strip()
    if not number or not str(quote_id or "").strip():
        return ["Quote Number left blank — not calling UpdatePropertyValue"]
    from .chrome_cdp import _cdp_evaluate_promise, minted_edit_tab_ready

    gate = minted_edit_tab_ready(quote_id, navigate=False)
    if not gate.get("ok"):
        why = str(gate.get("reason") or "wrong_document")
        return [f"WARNING: QuoteNumber UpdatePropertyValue stopped ({why})"]
    tab = gate.get("tab") if isinstance(gate.get("tab"), dict) else None
    value = _cdp_evaluate_promise(
        _PAGE_SET_PROPERTY_JS
        + "("
        + json.dumps({"parameter": "QuoteNumber", "value": number})
        + ")",
        tab=tab,
        fallback=False,
    )
    if not isinstance(value, dict) or not value.get("ok"):
        why = value.get("why") if isinstance(value, dict) else "empty"
        return [f"WARNING: QuoteNumber UpdatePropertyValue stopped ({why})"]
    return [f"QuoteNumber set via UpdatePropertyValue ({number})"]


def add_page_assembly(*, quote_id: str, name: str) -> list[str]:
    """OnCopyAll is client-only. AddItem_Assembly must persist, then the tree is checked."""
    key = str(name or "").strip()
    if key.upper().startswith("PN "):
        key = key[3:].strip()
    if not key:
        return ["WARNING: page assembly stopped (assembly_name_missing)"]
    from .chrome_cdp import _cdp_evaluate_promise, minted_edit_tab_ready, page_jquery_ajax

    gate = minted_edit_tab_ready(quote_id, navigate=False)
    if not gate.get("ok"):
        why = str(gate.get("reason") or "wrong_document")
        return [f"WARNING: page assembly stopped ({why})"]
    tab = gate.get("tab") if isinstance(gate.get("tab"), dict) else None
    staged = _cdp_evaluate_promise(
        PAGE_ADD_ASSEMBLY_JS + "(" + json.dumps({"name": key}) + ")",
        tab=tab,
        fallback=False,
    )
    if not isinstance(staged, dict) or not staged.get("posted_additem"):
        why = staged.get("why") if isinstance(staged, dict) else "empty"
        return [f"WARNING: page assembly stopped ({why or 'additem_assembly_missing'})"]
    tree = page_jquery_ajax(
        url="/Quote/QuoteItem_ReadTreeListData",
        method="GET",
        data={"ParentID": str(quote_id)},
        quote_id=str(quote_id),
    )
    if not (isinstance(tree, dict) and tree.get("ok")):
        why = tree.get("why") if isinstance(tree, dict) else "empty"
        return [f"WARNING: page assembly stopped (assembly_tree_unreadable:{why})"]
    try:
        kid_count = int(staged.get("staged") or 0)
    except (TypeError, ValueError):
        kid_count = 0
    problem = assembly_tree_problems(tree_rows(tree.get("body")), kid_count=kid_count)
    if problem:
        return [f"WARNING: page assembly stopped ({problem})"]
    return ["AddItem_Assembly persisted; tree has one parent and no loose lines"]
