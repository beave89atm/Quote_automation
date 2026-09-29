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
  jQuery("#AssemblyName").val(name).trigger("change");
  var lineDesc = String((spec && spec.description) || "").trim();
  var nameEl = document.querySelector("#AssemblyName");
  var form = nameEl && nameEl.form;
  if (lineDesc && form) {
    var fields = form.querySelectorAll(
      "input[name='Description'], textarea[name='Description']"
    );
    for (var di = 0; di < fields.length; di++) {
      if (!form.contains(fields[di])) continue;
      jQuery(fields[di]).val(lineDesc).trigger("change");
      break;
    }
  }
  function applyAssemblyLineDesc(opts) {
    if (!lineDesc || !opts) return;
    if (typeof opts.data === "string") {
      var parts = opts.data.split("&");
      var found = false;
      for (var pi = 0; pi < parts.length; pi++) {
        if (parts[pi].indexOf("Description=") === 0) {
          parts[pi] = "Description=" + encodeURIComponent(lineDesc);
          found = true;
          break;
        }
      }
      if (!found) parts.push("Description=" + encodeURIComponent(lineDesc));
      opts.data = parts.join("&");
      return;
    }
    if (opts.data && typeof opts.data === "object" && !Array.isArray(opts.data)) {
      opts.data.Description = lineDesc;
    }
  }
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
    if (url.indexOf("/Quote/AddItem_Assembly") >= 0) applyAssemblyLineDesc(opts);
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
  // AddItem_Assembly ignores Description when the line does not exist yet.
  // Post it after the parent is stored, then read the stored value back.
  // This is the assembly line. Do not write the quote header.
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
  var stored = "";
  var postedDescription = "";
  if (lineDesc) {
    var quoteId = String((spec && spec.quoteId) || "").trim();
    var first = await ajaxBody({
      url: "/Quote/QuoteItem_ReadTreeListData",
      type: "GET",
      data: {ParentID: quoteId},
      dataType: "json"
    });
    var parent = assemblyParent(treeRows(first && first.body));
    stored = parent ? String(parent.Description || "").trim() : "";
    if (stored !== lineDesc) {
      var itemId = parent ? String(parent.ID || parent.Id || "").trim() : "";
      if (!itemId) {
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
      var payload = JSON.stringify([{
        ID: itemId,
        ParentID: quoteId,
        ParamName: "Description",
        Value: lineDesc
      }]);
      postedDescription = payload;
      await ajaxBody({
        url: "/api/v1/quoteOnline/update",
        type: "PUT",
        contentType: "application/json; charset=utf-8",
        processData: false,
        data: payload
      });
      var second = await ajaxBody({
        url: "/Quote/QuoteItem_ReadTreeListData",
        type: "GET",
        data: {ParentID: quoteId},
        dataType: "json"
      });
      parent = assemblyParent(treeRows(second && second.body));
      stored = parent ? String(parent.Description || "").trim() : "";
    }
    if (stored !== lineDesc) {
      return {
        ok: false,
        why: "assembly_description_not_stored",
        posted_additem: true,
        staged: staged,
        status: addStatus,
        stored_description: stored,
        posted_description: postedDescription
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
    posted_description: postedDescription
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


def grid_flat_over_120_refuses(row: dict[str, Any] | None) -> str | None:
    """Any Length or Width over 120 in stops Finish. Blank dims are not this check."""
    if not isinstance(row, dict):
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
    if (
        not line
        or line == key
        or is_bare_part_number(line, key)
        or is_drawing_boilerplate_title(line)
    ):
        line = ""
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
