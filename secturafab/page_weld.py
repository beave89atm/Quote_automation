"""Page-native weldment steps proven on ZZ Q10506.

Selection, units, assembly persist, and the quote-number change are
fail-closed. This module does not read cookies and does not log secrets.
"""

from __future__ import annotations

import json
from typing import Any

STEP_MM_NOTE = (
    "STEP header SI_UNIT(.MILLI.,.METRE.) — not calling SetDXFFileUnits('inch')"
)
STEP_MM_CONTINUE_NOTE = (
    "STEP is millimetres — skipping SetDXFFileUnits('inch'); Sectura keeps mm"
)
STEP_UNITS_UNKNOWN_NOTE = (
    "STEP length unit unknown — not calling SetDXFFileUnits and not creating parts"
)
STEP_MM_DIMS_NOTE = (
    "millimetre STEP Finish L/W not in plausible inch range"
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
  window.confirm = function(msg) {
    var text = String(msg || "");
    if (/discard the parts/i.test(text)) return true;
    return true;
  };
  var name = String((spec && spec.name) || "").trim();
  if (!name) return {ok: false, why: "assembly_name_missing", posted_additem: false};
  if (!window.jQuery) return {ok: false, why: "no_jquery", posted_additem: false};
  if (typeof AddNewItemHTML === "function") {
    try { AddNewItemHTML("assembly", "top"); } catch (e0) {}
  }
  var nameDeadline = Date.now() + 8000;
  while (!document.querySelector("#AssemblyName") && Date.now() < nameDeadline) {
    await new Promise(function(resolve) { setTimeout(resolve, 25); });
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
  var pending = null;
  var orig = jQuery.ajax;
  jQuery.ajax = function(opts) {
    var url = "";
    if (typeof opts === "string") url = opts;
    else if (opts && opts.url) url = String(opts.url);
    var ret = orig.apply(this, arguments);
    if (!pending && url.indexOf("/Quote/AddItem_Assembly") >= 0) {
      pending = new Promise(function(resolve) {
        function finish(xhr) {
          var st = 0;
          try { st = (xhr && xhr.status) ? Number(xhr.status) : 0; } catch (eS) { st = 0; }
          resolve(st);
        }
        if (ret && typeof ret.always === "function") {
          ret.always(function(a, b, c) {
            var xhr = (c && c.status != null) ? c : ((a && a.status != null) ? a : ret);
            finish(xhr);
          });
        } else {
          finish(ret);
        }
      });
    }
    return ret;
  };
  try { OnAddClick(); } catch (e3) {}
  var deadline = Date.now() + 8000;
  while (!pending && Date.now() < deadline) {
    await new Promise(function(resolve) { setTimeout(resolve, 25); });
  }
  jQuery.ajax = orig;
  if (!pending) {
    return {ok: false, why: "additem_assembly_missing", posted_additem: false, staged: staged};
  }
  var addStatus = await pending;
  if (!(addStatus >= 200 && addStatus < 400)) {
    return {
      ok: false,
      why: "additem_assembly_http",
      posted_additem: false,
      staged: staged,
      status: addStatus
    };
  }
  return {ok: true, why: "", posted_additem: true, staged: staged, status: addStatus};
})"""


def step_header_is_millimetre(text: str) -> bool:
    """True only for a real millimetre length unit, not an inch conversion base."""
    from .step_units import step_uses_millimetres

    return step_uses_millimetres(text or "")


def _unit_token(raw: Any) -> str:
    text = str(raw or "").strip().lower()
    if text in {"inch", "inches", "in"}:
        return "inch"
    if text in {"mm", "millimetre", "millimeter", "millimetres", "millimeters"}:
        return "mm"
    if text:
        return "unknown"
    return ""


def grid_dxf_units(rows: list[dict[str, Any]] | None) -> str | None:
    """Agreed ``#gridDXF`` Units column, or None when the column is blank.

    Disagreeing or unrecognized tokens are ``unknown`` (fail closed).
    """
    seen: list[str] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        token = _unit_token(row.get("Units") if "Units" in row else row.get("units"))
        if token:
            seen.append(token)
    if not seen:
        return None
    if len(set(seen)) == 1:
        return seen[0]
    return "unknown"


def resolve_cad_length_unit(
    *,
    headers: list[str],
    grid_rows: list[dict[str, Any]] | None = None,
) -> str:
    """Prefer the upload grid Units column over the STEP header."""
    from .step_units import step_length_unit

    grid = grid_dxf_units(grid_rows)
    if grid in {"inch", "mm", "unknown"}:
        return grid
    found = [step_length_unit(text) for text in headers]
    if not found or any(unit == "unknown" for unit in found):
        return "unknown"
    if all(unit == "inch" for unit in found):
        return "inch"
    if all(unit == "mm" for unit in found):
        return "mm"
    return "unknown"


def flats_are_plausible_inches(length: Any, width: Any) -> bool:
    try:
        length_in = float(length)
        width_in = float(width)
    except (TypeError, ValueError):
        return False
    return 0 < length_in <= 240 and 0 < width_in <= 120


def step_unit_fail_note(notes: list[str] | None) -> str | None:
    """Unknown units fail closed. A true mm file continues and is not this note."""
    for note in notes or []:
        text = str(note)
        if STEP_UNITS_UNKNOWN_NOTE in text or STEP_MM_DIMS_NOTE in text:
            return text
    return None


def mm_kept_flats_fail(
    notes: list[str] | None,
    items: list[dict[str, Any]] | None,
) -> str | None:
    """After a mm continue, previously blank L/W must land in inch range."""
    if not any(STEP_MM_CONTINUE_NOTE in str(note) for note in (notes or [])):
        return None
    rows = []
    for row in items or []:
        if not isinstance(row, dict):
            continue
        if row.get("ProductType") in (300, "300") or row.get("IsAssembly"):
            continue
        rows.append(row)
    if not rows:
        return None
    for row in rows:
        if not flats_are_plausible_inches(row.get("Length"), row.get("Width")):
            name = str(row.get("ItemNumber") or row.get("Description") or "part")
            return f"{STEP_MM_DIMS_NOTE} ({name})"
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
