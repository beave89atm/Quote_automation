"""Page-native weldment steps proven on ZZ Q10506.

Selection, units, assembly persist, and the quote-number change are
fail-closed. This module does not read cookies and does not log secrets.
"""

from __future__ import annotations

import json
import time
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
  var lineDesc = String((spec && spec.description) || "").trim();
  if (lineDesc.toLowerCase() === "root") {
    return {ok: false, why: "assembly_description_not_stored", posted_additem: false};
  }
  // AddItem_Assembly posts this name. The tree stores it as Description
  // and as ItemNumber. A formatted description is that name. An empty
  // description keeps the bare part number.
  var assemblyName = lineDesc || name;
  jQuery("#AssemblyName").val(assemblyName).trigger("change");
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
  // The add posts #AssemblyName. After OnAddClick the parent
  // Description is that string. ItemNumber is the same string.
  // Never store Root.
  function treeRows(body) {
    if (!body) return [];
    if (Array.isArray(body)) return body;
    var data = body.Data || body.rows || body.TreeListData;
    return Array.isArray(data) ? data : [];
  }
  function assemblyParent(rows) {
    for (var ri = 0; ri < rows.length; ri++) {
      var row = rows[ri] || {};
      var aid = String(row.AssemblyID || row.AID || "").trim();
      if (aid && aid !== "null") continue;
      var pt = row.ProductType;
      if (pt === 300 || pt === "300" || row.IsAssembly) return row;
      if (String(row.ItemType || row.Category || "") === "Assembly") return row;
    }
    return null;
  }
  function ajaxBody(opts) {
    return new Promise(function(resolve) {
      var ret = null;
      try { ret = jQuery.ajax(opts); } catch (eA) { resolve({body: null, status: 0}); return; }
      function finish(body, status) {
        resolve({body: body, status: status || 0});
      }
      if (ret && typeof ret.done === "function") {
        var settled = false;
        ret.done(function(body, _t, xhr) {
          if (settled) return;
          settled = true;
          finish(body, (xhr && xhr.status) || 200);
        });
        if (typeof ret.fail === "function") {
          ret.fail(function(xhr) {
            if (settled) return;
            settled = true;
            finish(null, (xhr && xhr.status) || 0);
          });
        }
        return;
      }
      if (ret && typeof ret.then === "function") {
        ret.then(function(body) { finish(body, 200); }, function() { finish(null, 0); });
        return;
      }
      finish(ret, 200);
    });
  }
  var quoteId = String((spec && spec.quoteId) || "").trim();
  var stored = "";
  async function readTree() {
    return ajaxBody({
      url: "/Quote/QuoteItem_ReadTreeListData",
      type: "GET",
      data: {ParentID: quoteId},
      dataType: "json"
    });
  }
  function looseKids(rows, parent) {
    var parentId = parent ? String(parent.ID || parent.Id || "").trim() : "";
    var loose = [];
    for (var li = 0; li < rows.length; li++) {
      var row = rows[li] || {};
      var id = String(row.ID || row.Id || "").trim();
      if (!id || (parentId && id === parentId)) continue;
      if (assemblyParent([row])) continue;
      var aid = String(row.AssemblyID || row.AID || "").trim();
      if (parentId && aid === parentId) continue;
      var label = String(row.Description || row.Name || "").trim();
      if (label.toLowerCase() === "root") continue;
      loose.push(row);
    }
    return loose;
  }
  var first = await readTree();
  var rows = treeRows(first && first.body);
  var parent = assemblyParent(rows);
  var loose = looseKids(rows, parent);
  var parentId = parent ? String(parent.ID || parent.Id || "").trim() : "";
  for (var ci = 0; ci < loose.length; ci++) {
    var kidId = String(loose[ci].ID || loose[ci].Id || "").trim();
    if (!parentId || !kidId) continue;
    await ajaxBody({
      url: "/Quote/CopyMoveItemToAssembly",
      type: "POST",
      data: {
        ID: quoteId,
        ItemID: kidId,
        AssemblyID: parentId,
        Mode: "Move"
      }
    });
  }
  if (loose.length) {
    var linked = await readTree();
    rows = treeRows(linked && linked.body);
    parent = assemblyParent(rows);
    loose = looseKids(rows, parent);
  }
  if (loose.length) {
    return {
      ok: false,
      why: "assembly_loose_line",
      posted_additem: true,
      staged: staged,
      status: addStatus,
      stored_description: parent ? String(parent.Description || "").trim() : "",
      posted_description: ""
    };
  }
  if (lineDesc) {
    stored = parent ? String(parent.Description || "").trim() : "";
    if (!stored || stored.toLowerCase() === "root" || stored !== lineDesc) {
      return {
        ok: false,
        why: "assembly_description_not_stored",
        posted_additem: true,
        staged: staged,
        status: addStatus,
        stored_description: stored,
        posted_description: ""
      };
    }
  }
  return {
    ok: true,
    why: "",
    posted_additem: true,
    staged: staged,
    status: addStatus,
    stored_description: stored,
    posted_description: ""
  };
})"""

PAGE_UPDATE_ASSEMBLY_JS = r"""(async function(spec) {
  // One STEP file. Finish already created the ProductType 300 parent.
  // DoEditItem opens that line. #asmAdd-but says Update Assembly and
  // posts AddItem_Assembly against the existing QuoteItemID.
  var lineDesc = String((spec && spec.description) || "").trim();
  if (!lineDesc || lineDesc.toLowerCase() === "root") {
    return {ok: false, why: "assembly_description_not_stored", posted_additem: false};
  }
  if (!window.jQuery) return {ok: false, why: "no_jquery", posted_additem: false};
  function treeRows(body) {
    if (!body) return [];
    if (Array.isArray(body)) return body;
    var data = body.Data || body.rows || body.TreeListData;
    return Array.isArray(data) ? data : [];
  }
  function rowId(row) {
    return String((row && (row.ID || row.Id)) || "").trim();
  }
  function assemblyId(row) {
    return String((row && (row.AssemblyID || row.AID)) || "").trim();
  }
  function isParent(row) {
    if (!row) return false;
    var aid = assemblyId(row);
    if (aid && aid !== "null") return false;
    var pt = row.ProductType;
    if (pt === 300 || pt === "300" || row.IsAssembly) return true;
    if (String(row.ItemType || row.Category || "") === "Assembly") return true;
    return false;
  }
  function ajaxBody(opts) {
    return new Promise(function(resolve) {
      var ret = null;
      try { ret = jQuery.ajax(opts); } catch (eA) { resolve({body: null, status: 0}); return; }
      function finish(body, status) {
        resolve({body: body, status: status || 0});
      }
      if (ret && typeof ret.done === "function") {
        var settled = false;
        ret.done(function(body, _t, xhr) {
          if (settled) return;
          settled = true;
          finish(body, (xhr && xhr.status) || 200);
        });
        if (typeof ret.fail === "function") {
          ret.fail(function(xhr) {
            if (settled) return;
            settled = true;
            finish(null, (xhr && xhr.status) || 0);
          });
        }
        return;
      }
      if (ret && typeof ret.then === "function") {
        ret.then(function(body) { finish(body, 200); }, function() { finish(null, 0); });
        return;
      }
      finish(ret, 200);
    });
  }
  var quoteId = String((spec && spec.quoteId) || "").trim();
  async function readTree() {
    return ajaxBody({
      url: "/Quote/QuoteItem_ReadTreeListData",
      type: "GET",
      data: {ParentID: quoteId},
      dataType: "json"
    });
  }
  var first = await readTree();
  var rows = treeRows(first && first.body);
  var parents = [];
  for (var pi = 0; pi < rows.length; pi++) {
    if (isParent(rows[pi])) parents.push(rows[pi]);
  }
  if (!parents.length) {
    return {ok: true, why: "no_assembly_parent", posted_additem: false, skipped: true};
  }
  if (parents.length !== 1) {
    return {ok: false, why: "assembly_parent_not_one", posted_additem: false};
  }
  var parentId = rowId(parents[0]);
  if (!parentId) {
    return {ok: false, why: "assembly_parent_missing", posted_additem: false};
  }
  var kidIds = [];
  for (var ki = 0; ki < rows.length; ki++) {
    var kid = rows[ki];
    if (!kid || isParent(kid)) continue;
    if (assemblyId(kid) === parentId) {
      var kidId = rowId(kid);
      if (kidId) kidIds.push(kidId);
    }
  }
  if (typeof DoEditItem !== "function") {
    return {ok: false, why: "no_doedititem", posted_additem: false};
  }
  try { DoEditItem(parentId); } catch (eEdit) {}
  function quoteItemValue() {
    var el = document.querySelector("#QuoteItemID");
    if (!el) return "";
    return String(el.value || "").trim();
  }
  function buttonText() {
    var el = document.querySelector("#asmAdd-but");
    if (!el) return "";
    return String(el.textContent || el.innerText || el.value || "").trim();
  }
  function formReady() {
    if (!document.querySelector("#newItem")) return false;
    if (quoteItemValue() !== parentId) return false;
    if (!/update assembly/i.test(buttonText())) return false;
    if (!document.querySelector("#AssemblyName")) return false;
    return true;
  }
  var formDeadline = Date.now() + 8000;
  while (!formReady() && Date.now() < formDeadline) {
    await new Promise(function(resolve) { setTimeout(resolve, 25); });
  }
  if (!formReady()) {
    return {ok: false, why: "edit_form_not_ready", posted_additem: false};
  }
  jQuery("#AssemblyName").val(lineDesc).trigger("change");
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
  var addBtn = document.querySelector("#asmAdd-but");
  if (!addBtn || typeof addBtn.click !== "function") {
    jQuery.ajax = orig;
    return {ok: false, why: "asm_add_button_missing", posted_additem: false};
  }
  try { addBtn.click(); } catch (eClick) {}
  var deadline = Date.now() + 8000;
  while (!pending && Date.now() < deadline) {
    await new Promise(function(resolve) { setTimeout(resolve, 25); });
  }
  jQuery.ajax = orig;
  if (!pending) {
    return {
      ok: false,
      why: "additem_assembly_missing",
      posted_additem: false,
      parent_id: parentId
    };
  }
  var addStatus = await pending;
  if (!(addStatus >= 200 && addStatus < 400)) {
    return {
      ok: false,
      why: "additem_assembly_http",
      posted_additem: false,
      parent_id: parentId,
      status: addStatus
    };
  }
  var again = await readTree();
  rows = treeRows(again && again.body);
  parents = [];
  for (var pj = 0; pj < rows.length; pj++) {
    if (isParent(rows[pj])) parents.push(rows[pj]);
  }
  var stored = parents.length ? String(parents[0].Description || "").trim() : "";
  var itemNumber = parents.length ? String(parents[0].ItemNumber || "").trim() : "";
  if (parents.length !== 1 || rowId(parents[0]) !== parentId) {
    return {
      ok: false,
      why: parents.length ? "assembly_parent_not_one" : "assembly_parent_missing",
      posted_additem: true,
      parent_id: parentId,
      status: addStatus,
      stored_description: stored,
      stored_item_number: itemNumber
    };
  }
  if (!stored || stored.toLowerCase() === "root" || stored !== lineDesc || itemNumber !== lineDesc) {
    return {
      ok: false,
      why: "assembly_description_not_stored",
      posted_additem: true,
      parent_id: parentId,
      status: addStatus,
      stored_description: stored,
      stored_item_number: itemNumber,
      kid_ids: kidIds
    };
  }
  var afterKids = [];
  for (var ak = 0; ak < rows.length; ak++) {
    var after = rows[ak];
    if (!after || isParent(after)) continue;
    if (assemblyId(after) === parentId) {
      var afterId = rowId(after);
      if (afterId) afterKids.push(afterId);
    }
  }
  for (var ck = 0; ck < kidIds.length; ck++) {
    if (afterKids.indexOf(kidIds[ck]) < 0) {
      return {
        ok: false,
        why: "assembly_loose_line",
        posted_additem: true,
        parent_id: parentId,
        status: addStatus,
        stored_description: stored,
        stored_item_number: itemNumber,
        kid_ids: afterKids
      };
    }
  }
  return {
    ok: true,
    why: "",
    posted_additem: true,
    skipped: false,
    parent_id: parentId,
    status: addStatus,
    stored_description: stored,
    stored_item_number: itemNumber,
    kid_ids: kidIds
  };
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


# Sectura Linear product types already used on the website (bar / tube / angle).
# Not a new length limit — these rows are simply not the 120 in sheet cap.
_LINEAR_CUT_PRODUCT_TYPES = frozenset({10, 30, 40})
_CAD_FLAT_ITEM_TOKENS = frozenset({"cad", "plate", "sheet", "sheets", "plates"})
_LINEAR_ITEM_TOKENS = frozenset(
    {"linear", "tube", "pipe", "structural", "angle", "bar"}
)
_CAD_FLAT_PRODUCT_TOKENS = frozenset(
    {"plate", "sheet", "sheets", "plates", "100", "cad"}
)
# OnAddLinearClick productType strings. "bar" is omitted here: the Image
# Files grid template uses ProductType bar / ProductSubType bar_flat for
# plates, and that path still refuses length over 120 in.
_LINEAR_PRODUCT_TEXT = frozenset({"tube", "pipe", "structural"})


def _row_item_token(row: dict[str, Any]) -> str:
    for key in ("ItemType", "Category", "FileType"):
        token = str(row.get(key) or "").strip().casefold()
        if token:
            return token
    return ""


def _product_type_texts(row: dict[str, Any]) -> list[str]:
    texts: list[str] = []
    for key in ("ProductType", "productType", "ProductSubType", "productSubType"):
        raw = row.get(key)
        if raw in (None, ""):
            continue
        texts.append(str(raw).strip().casefold())
    return texts


def _flag_true(value: Any) -> bool:
    if value is True or value == 1:
        return True
    if isinstance(value, str) and value.strip().casefold() in {"true", "1", "yes"}:
        return True
    return False


def linear_cut_length_skips_flat_cap(row: dict[str, Any] | None) -> bool:
    """True when this row is bar/tube Linear and the 120 in sheet cap does not apply.

    Sheet, plate, Cad, and PDF image-file rows stay on the cap. Numeric
    ProductType 10/30/40 are the existing Linear types. The Image Files
    grid default ProductType ``bar`` / ``bar_flat`` is a plate template,
    not Linear type 10, so it stays capped.
    """
    if not isinstance(row, dict):
        return False
    item = _row_item_token(row)
    if item in _CAD_FLAT_ITEM_TOKENS:
        return False
    # The assembly parent can carry the long tube's cut length. That
    # bbox is not a sheet. Live 1009353-1 Length=135 must not refuse
    # the tube.
    if item == "assembly" or _flag_true(row.get("IsAssembly")):
        return True
    try:
        if int(row.get("ProductType")) == 300:
            return True
    except (TypeError, ValueError):
        pass
    texts = _product_type_texts(row)
    for text in texts:
        if text.startswith("prt_") or text in _CAD_FLAT_PRODUCT_TOKENS:
            return False
    if item in _LINEAR_ITEM_TOKENS:
        return True
    if _flag_true(row.get("IsLinear")):
        return True
    try:
        if int(row.get("PartMode")) == 1:
            return True
    except (TypeError, ValueError):
        pass
    try:
        if int(row.get("ProductType")) in _LINEAR_CUT_PRODUCT_TYPES:
            return True
    except (TypeError, ValueError):
        pass
    if any(text in _LINEAR_PRODUCT_TEXT for text in texts):
        return True
    # ProductType "bar" / "bar_flat" with no Linear category is the
    # Image Files plate template. Leave it on the sheet cap.
    return False


def grid_flat_over_120_refuses(row: dict[str, Any] | None) -> str | None:
    """Sheet/plate/Cad/PDF Length or Width over 120 in stops Finish.

    Bar and tube (Linear) cut length is not this check. Blank dims are
    not this check. There is no replacement upper bound for tubes.
    """
    if not isinstance(row, dict):
        return None
    if linear_cut_length_skips_flat_cap(row):
        return None
    name = str(row.get("Name") or row.get("PartName") or row.get("ItemNumber") or "part")
    for key in ("Length", "Width"):
        raw = row.get(key)
        if raw in (None, ""):
            continue
        try:
            val = float(raw)
        except (TypeError, ValueError):
            continue
        if val > 120:
            return f"{name} {key}={val} in is over 120"
    return None


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


_PROPERTY_NOT_READY = frozenset(
    {"update_property_missing", "header_field_missing", "no_jquery"}
)


def set_page_quote_number(quote_id: str, quote_number: str) -> list[str]:
    """Set #quote_Text through its change event. The value is not logged.

    The first post right after GET /quote/create can return
    update_property_missing before the property endpoint is bound.
    That miss is retried. It does not abort the create.
    """
    number = str(quote_number or "").strip()
    if not number or not str(quote_id or "").strip():
        return ["Quote Number left blank — not calling UpdatePropertyValue"]
    from .forbidden_quotes import refuse_forbidden_quote_write

    refuse_forbidden_quote_write(
        method="POST",
        path="/Quote/UpdatePropertyValue",
        payload={"ID": quote_id, "QuoteNumber": number},
    )
    from .chrome_cdp import _cdp_evaluate_promise, minted_edit_tab_ready

    gate = minted_edit_tab_ready(quote_id, navigate=False)
    if not gate.get("ok"):
        why = str(gate.get("reason") or "wrong_document")
        return [f"WARNING: QuoteNumber UpdatePropertyValue stopped ({why})"]
    tab = gate.get("tab") if isinstance(gate.get("tab"), dict) else None
    expression = (
        _PAGE_SET_PROPERTY_JS
        + "("
        + json.dumps({"parameter": "QuoteNumber", "value": number})
        + ")"
    )
    last_why = "empty"
    for attempt in range(4):
        value = _cdp_evaluate_promise(expression, tab=tab, fallback=False)
        if isinstance(value, dict) and value.get("ok"):
            return [f"QuoteNumber set via UpdatePropertyValue ({number})"]
        last_why = value.get("why") if isinstance(value, dict) else "empty"
        if last_why not in _PROPERTY_NOT_READY or attempt >= 3:
            break
        time.sleep(0.5)
    return [f"WARNING: QuoteNumber UpdatePropertyValue stopped ({last_why})"]


def set_page_quote_description(quote_id: str, description: str) -> list[str]:
    """Set #Description through UpdatePropertyValue. Blank stays blank."""
    text = str(description or "").strip()
    if not text or not str(quote_id or "").strip():
        return ["Description left blank — not calling UpdatePropertyValue"]
    from .forbidden_quotes import refuse_forbidden_quote_write

    refuse_forbidden_quote_write(
        method="POST",
        path="/Quote/UpdatePropertyValue",
        payload={"ID": quote_id, "Description": text},
    )
    from .chrome_cdp import _cdp_evaluate_promise, minted_edit_tab_ready

    gate = minted_edit_tab_ready(quote_id, navigate=False)
    if not gate.get("ok"):
        why = str(gate.get("reason") or "wrong_document")
        return [f"WARNING: Description UpdatePropertyValue stopped ({why})"]
    tab = gate.get("tab") if isinstance(gate.get("tab"), dict) else None
    value = _cdp_evaluate_promise(
        _PAGE_SET_PROPERTY_JS
        + "("
        + json.dumps({"parameter": "Description", "value": text[:500]})
        + ")",
        tab=tab,
        fallback=False,
    )
    if not isinstance(value, dict) or not value.get("ok"):
        why = value.get("why") if isinstance(value, dict) else "empty"
        return [f"WARNING: Description UpdatePropertyValue stopped ({why})"]
    return ["Description set via UpdatePropertyValue"]


def add_page_assembly(
    *,
    quote_id: str,
    name: str,
    description: str | None = None,
) -> list[str]:
    """OnCopyAll is client-only. AddItem_Assembly must persist, then the tree is checked.

    ``description`` is the assembly line (``{PN} - {title chosen at create}``).
    It is not written onto the quote header.
    """
    key = str(name or "").strip()
    if key.upper().startswith("PN "):
        key = key[3:].strip()
    if not key:
        return ["WARNING: page assembly stopped (assembly_name_missing)"]
    from quote_core.drawing_title import is_drawing_boilerplate_title
    from secturafab.item_desc import is_bare_part_number

    line = str(description or "").strip()
    if line.casefold() == "root":
        return ["WARNING: page assembly stopped (assembly_description_not_stored)"]
    if (
        not line
        or line == key
        or is_bare_part_number(line, key)
        or is_drawing_boilerplate_title(line)
    ):
        line = ""
    from .forbidden_quotes import refuse_forbidden_quote_write

    refuse_forbidden_quote_write(
        method="POST",
        path="/Quote/AddItem_Assembly",
        payload={"quoteId": str(quote_id), "name": key, "description": line},
    )
    from .chrome_cdp import _cdp_evaluate_promise, minted_edit_tab_ready, page_jquery_ajax

    gate = minted_edit_tab_ready(quote_id, navigate=False)
    if not gate.get("ok"):
        why = str(gate.get("reason") or "wrong_document")
        return [f"WARNING: page assembly stopped ({why})"]
    tab = gate.get("tab") if isinstance(gate.get("tab"), dict) else None
    payload: dict[str, str] = {"name": key, "quoteId": str(quote_id)}
    if line:
        payload["description"] = line
    staged = _cdp_evaluate_promise(
        PAGE_ADD_ASSEMBLY_JS + "(" + json.dumps(payload) + ")",
        tab=tab,
        fallback=False,
    )
    if not isinstance(staged, dict) or not staged.get("posted_additem"):
        why = staged.get("why") if isinstance(staged, dict) else "empty"
        return [f"WARNING: page assembly stopped ({why or 'additem_assembly_missing'})"]
    if line and str(staged.get("why") or "") == "assembly_description_not_stored":
        return ["WARNING: page assembly stopped (assembly_description_not_stored)"]
    stored_line = str(staged.get("stored_description") or "").strip()
    if line and stored_line and stored_line != line:
        return ["WARNING: page assembly stopped (assembly_description_not_stored)"]
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
    rows = tree_rows(tree.get("body"))
    problem = assembly_tree_problems(rows, kid_count=kid_count)
    if problem:
        return [f"WARNING: page assembly stopped ({problem})"]
    if line:
        parents = [row for row in rows if _is_assembly_parent(row)]
        got = str(parents[0].get("Description") or "").strip() if parents else ""
        if got != line:
            return ["WARNING: page assembly stopped (assembly_description_not_stored)"]
    return ["AddItem_Assembly persisted; tree has one parent and no loose lines"]


def update_existing_assembly_name(
    *,
    quote_id: str,
    description: str | None = None,
) -> list[str]:
    """Rename the parent Finish already created for a one-file STEP.

    DoEditItem opens that line. ``#AssemblyName`` is the formatted
    description. One click on ``#asmAdd-but`` posts AddItem_Assembly
    against the existing QuoteItemID. A tree with no ProductType 300
    parent is left alone. This does not call add_page_assembly.
    """
    from quote_core.drawing_title import is_drawing_boilerplate_title
    from secturafab.item_desc import is_bare_part_number

    line = str(description or "").strip()
    if line.casefold() == "root":
        return ["WARNING: page assembly stopped (assembly_description_not_stored)"]
    if not line or is_bare_part_number(line) or is_drawing_boilerplate_title(line):
        return []
    if not str(quote_id or "").strip():
        return ["WARNING: page assembly stopped (assembly_name_missing)"]
    from .forbidden_quotes import refuse_forbidden_quote_write

    refuse_forbidden_quote_write(
        method="POST",
        path="/Quote/AddItem_Assembly",
        payload={"quoteId": str(quote_id), "description": line},
    )
    from .chrome_cdp import _cdp_evaluate_promise, minted_edit_tab_ready, page_jquery_ajax

    gate = minted_edit_tab_ready(quote_id, navigate=False)
    if not gate.get("ok"):
        why = str(gate.get("reason") or "wrong_document")
        return [f"WARNING: page assembly stopped ({why})"]
    tab = gate.get("tab") if isinstance(gate.get("tab"), dict) else None
    staged = _cdp_evaluate_promise(
        PAGE_UPDATE_ASSEMBLY_JS
        + "("
        + json.dumps({"quoteId": str(quote_id), "description": line})
        + ")",
        tab=tab,
        fallback=False,
    )
    if isinstance(staged, dict) and staged.get("skipped"):
        return []
    if not isinstance(staged, dict) or not staged.get("posted_additem"):
        why = staged.get("why") if isinstance(staged, dict) else "empty"
        return [f"WARNING: page assembly stopped ({why or 'additem_assembly_missing'})"]
    if str(staged.get("why") or "") == "assembly_description_not_stored":
        return ["WARNING: page assembly stopped (assembly_description_not_stored)"]
    stored_line = str(staged.get("stored_description") or "").strip()
    stored_number = str(staged.get("stored_item_number") or "").strip()
    if stored_line != line or stored_number != line:
        return ["WARNING: page assembly stopped (assembly_description_not_stored)"]
    parent_id = str(staged.get("parent_id") or "").strip()
    kid_ids = [
        str(item).strip() for item in (staged.get("kid_ids") or []) if str(item).strip()
    ]
    tree = page_jquery_ajax(
        url="/Quote/QuoteItem_ReadTreeListData",
        method="GET",
        data={"ParentID": str(quote_id)},
        quote_id=str(quote_id),
    )
    if not (isinstance(tree, dict) and tree.get("ok")):
        why = tree.get("why") if isinstance(tree, dict) else "empty"
        return [f"WARNING: page assembly stopped (assembly_tree_unreadable:{why})"]
    rows = tree_rows(tree.get("body"))
    parents = [row for row in rows if _is_assembly_parent(row)]
    if len(parents) != 1:
        why = "assembly_parent_missing" if not parents else "assembly_parent_not_one"
        return [f"WARNING: page assembly stopped ({why})"]
    got_id = str(parents[0].get("ID") or parents[0].get("Id") or "").strip()
    got = str(parents[0].get("Description") or "").strip()
    got_number = str(parents[0].get("ItemNumber") or "").strip()
    if got_id != parent_id or got != line or got_number != line:
        return ["WARNING: page assembly stopped (assembly_description_not_stored)"]
    under = {
        str(row.get("ID") or row.get("Id") or "").strip()
        for row in rows
        if _assembly_id(row) == got_id
    }
    if any(kid not in under for kid in kid_ids):
        return ["WARNING: page assembly stopped (assembly_loose_line)"]
    return ["Update Assembly persisted; the STEP parent kept its id and kids"]
