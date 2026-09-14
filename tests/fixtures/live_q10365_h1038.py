"""Q10365 / H.10.38 — Safe Cave mouse Cad-stick FAIL leftover.

Live mouse Product Type dropdown Cad + 0.1875 in on Safe Cave H.10.38:
  POST /Part/UpdateItemType 200 after Cad click
  Then /part/PartImage, /CadImport/UpdateData, /CadImport/CADData
  fill_xhr=null
  Finished v1 item ProductType noun ``part`` (enum 100)
  NumberOfContours unavailable / Contours PASS not proven

Same FAIL class as Q10354 / D.H.38.96 and Q10356 / V.20.78 —
Cad selector + inches set, Contours PASS not proven. Contrast
PASSes Q10333 / Q10348 (and Q10344/46/49/51): live GET
ProductType=100 + NumberOfContours=1 + Laser / prt_dxf / inches.
Do not refuse enum 100 — PASSes finish as 100 too.

Root cause (in-repo, invent=false):
  UpdateItemType body is ID + ItemType only. The Product Type
  dropdown Cad click is that classify XHR — it does not persist
  ProductType. Classify/kendo stamps ProductType=100. Contours
  PASS gate is NumberOfContours≥1 (plus inches / Laser / prt_dxf).
  Do not invent a ProductType persist XHR or Contours fill.

Quote UUID was not restated. Number-only leftover. Do not remint
existing forever-protects (Q10344/46/48/49/51/54/56). invent=false.
"""

from __future__ import annotations

from typing import Any

from secturafab.cadimport_js import (
    UPDATE_ITEM_TYPE_BODY_KEYS,
    UPDATE_ITEM_TYPE_CAD,
    UPDATE_ITEM_TYPE_PATH,
    UPDATE_ITEM_TYPE_SETS_PRODUCT_TYPE_CAD,
)

Q10365_H1038_FAIL: dict[str, Any] = {
    "quote_id": None,
    "quote_id_prefix": None,
    "quote_number": "Q10365",
    "part_number": "H.10.38",
    "customer": "Safe Cave",
    "piece": "H.10.38",
    "source": "Kyle UI / mouse Product Type Cad + DevTools",
    "outside_h638_family": True,
    "h638_contours_good": False,
    "via": "mouse_updateitemtype_cad_200_finished_producttype_part",
    "same_class_as": "Q10354 / D.H.38.96",
    "same_pattern_as": "UpdateItemType Cad 200 then GET ProductType part",
    "id_unknown": True,
    "pass": False,
    "contours_pass": False,
    "contours_pass_proven": False,
    "product_type": "part",
    "product_type_enum": 100,
    "cad_selector_set": True,
    "update_item_type_path": UPDATE_ITEM_TYPE_PATH,
    "update_item_type_status": 200,
    "update_item_type_itemtype": UPDATE_ITEM_TYPE_CAD,
    "update_item_type_keys": UPDATE_ITEM_TYPE_BODY_KEYS,
    "update_item_type_sets_product_type_cad": UPDATE_ITEM_TYPE_SETS_PRODUCT_TYPE_CAD,
    "companions": (
        "/part/PartImage",
        "/CadImport/UpdateData",
        "/CadImport/CADData",
    ),
    "fill_xhr": None,
    "thickness": "0.1875",
    "thickness_units": "inch",
    "thickness_inches": True,
    "number_of_contours_unavailable": True,
    "internaldata_empty": True,
    "contours_empty": True,
    "contours_fill": False,
    "invent": False,
    "zz_del": False,
    "zz_del_number": None,
    "protect": False,
    "readonly": True,
    "do_not_remint": True,
    "do_not_patch": True,
    "unlocks_automation_contours_fill": False,
    "unlocks_contours_fill": False,
    "fail_close": True,
}


def q10365_h1038_fail_dump() -> dict[str, Any]:
    """Read-only H.10.38 mouse Cad-stick FAIL leftover. Never remint."""
    out = dict(Q10365_H1038_FAIL)
    out["companions"] = tuple(Q10365_H1038_FAIL["companions"])
    out["update_item_type_keys"] = tuple(Q10365_H1038_FAIL["update_item_type_keys"])
    return out
