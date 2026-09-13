"""Q10335 / bcff1a24 — live mouse Component→Cad UpdateItemType leftover.

Live mouse Cad capture on Q10335:
  POST /Part/UpdateItemType — real Component→Cad dropdown click, status 200
  Also /part/PartImage and /Quote/GetBorderSize on thickness
  Contours still 0 before Finish
  Finish diagnostic in flight — leftover forbid (not PASS protect)

Full GUID was not restated. Prefix bcff1a24 + Q10335 / ZZ-DEL-Q10335
only. invent=false. Do not remint / PATCH. Do not invent Contours /
InternalData. UpdateItemType is the dropdown classify XHR; Contours
fill may still need Finish or further calls.

Q10333 / b5f56ac3 remains the Contours PASS protect. H638-CADPLATE /
Q10334 stay Cad-for-plate leftovers.
"""

from __future__ import annotations

from typing import Any

from secturafab.cadimport_js import (
    GET_BORDER_SIZE_PATH,
    UPDATE_ITEM_TYPE_BODY_KEYS,
    UPDATE_ITEM_TYPE_CAD,
    UPDATE_ITEM_TYPE_PATH,
)

Q10335_LEFTOVER: dict[str, Any] = {
    "quote_id": None,
    "quote_id_prefix": "bcff1a24",
    "quote_number": "Q10335",
    "zz_del_number": "ZZ-DEL-Q10335",
    "id_unknown": True,
    "via": "mouse_updateitemtype_cad",
    "update_item_type_path": UPDATE_ITEM_TYPE_PATH,
    "update_item_type_status": 200,
    "update_item_type_itemtype": UPDATE_ITEM_TYPE_CAD,
    "update_item_type_keys": UPDATE_ITEM_TYPE_BODY_KEYS,
    "companions": (
        "/part/PartImage",
        GET_BORDER_SIZE_PATH,
    ),
    "classify_cad": True,
    "internaldata_empty": True,
    "contours_empty": True,
    "contours_empty_before_finish": True,
    "finish_clicked": False,
    "finish_posted": False,
    "finish_diagnostic_in_flight": True,
    "finish_refused": True,
    "pass": False,
    "protect": False,
    "invent": False,
    "unlocks_automation_contours_fill": False,
    "unlocks_contours_fill": False,
    "update_item_type_is_classify_xhr": True,
    "update_item_type_fills_contours": False,
    "fail_close": True,
    "readonly": True,
    "zz_del": True,
    "do_not_remint": True,
    "do_not_patch": True,
}


def leftover_q10335_update_item_type_dump() -> dict[str, Any]:
    """Read-only Q10335 leftover. Does not unlock Contours fill."""
    out = dict(Q10335_LEFTOVER)
    out["companions"] = tuple(Q10335_LEFTOVER["companions"])
    out["update_item_type_keys"] = tuple(Q10335_LEFTOVER["update_item_type_keys"])
    return out
