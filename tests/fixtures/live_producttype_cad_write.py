"""ProductType=Cad write XHR hunt — closed. invent=false.

PO box hunt complete (2026-09-14):
  No ProductType=Cad write XHR found.
  UpdateItemType is ItemType-only.
  SetPartMode is PartMode-only.

Read-only GET Contours PASSes (never remint / PATCH / Finish / ZZ-DEL):
  Q10333 / b5f56ac3  ProductType=100  NumberOfContours=1
                     Machine Laser  ProductSubType=prt_dxf  0.1875 in
                     ItemType=null  PartMode=null
  Q10348 / 1defeed8  same shape (H.16.70)

There is no separate ProductType=Cad write — Contours PASSes ARE
enum 100. Distinguish FAIL vs PASS by NumberOfContours≥1 / fill,
not Cad noun. PRODUCT_TYPE_CAD_WRITE_XHR stays None.

Next chase is Contours fill (not Cad noun). Safe Cave burns paused.
Do not invent Contours or a Cad persist call.
"""

from __future__ import annotations

from typing import Any

from secturafab.cadimport_js import (
    CONTOURS_PASS_VS_FAIL,
    PRODUCT_TYPE_CAD_SHOWN_VIA,
    PRODUCT_TYPE_CAD_WRITE_BODY,
    PRODUCT_TYPE_CAD_WRITE_CAPTURE_NEEDED,
    PRODUCT_TYPE_CAD_WRITE_HUNT_CLOSED,
    PRODUCT_TYPE_CAD_WRITE_METHOD,
    PRODUCT_TYPE_CAD_WRITE_PATH,
    PRODUCT_TYPE_CAD_WRITE_XHR,
    SET_PART_MODE_SETS_PRODUCT_TYPE_CAD,
    UPDATE_ITEM_TYPE_SETS_PRODUCT_TYPE_CAD,
)

# Read-only live GET 2026-09-14 — field names / scalars only. No
# InternalData / ImageString / OCL payloads. Never remint / PATCH.
Q10333_V1_PRODUCTTYPE: dict[str, Any] = {
    "quote_number": "Q10333",
    "quote_id": "b5f56ac3-326d-48e9-b82d-1e09a7897107",
    "product_type": 100,
    "product_type_name": None,
    "item_type": None,
    "part_mode": None,
    "category": None,
    "product_subtype": "prt_dxf",
    "machine": "Laser",
    "thickness": 0.1875,
    "thickness_units": "inch",
    "number_of_contours": 1,
    "contours_pass": True,
}

Q10348_V1_PRODUCTTYPE: dict[str, Any] = {
    "quote_number": "Q10348",
    "quote_id": "1defeed8-d95d-4939-b2fd-0a1774e56c6e",
    "product_type": 100,
    "product_type_name": None,
    "item_type": None,
    "part_mode": None,
    "category": None,
    "product_subtype": "prt_dxf",
    "machine": "Laser",
    "thickness": 0.1875,
    "thickness_units": "inch",
    "number_of_contours": 1,
    "contours_pass": True,
}

LIVE_PRODUCTTYPE_CAD_WRITE: dict[str, Any] = {
    "invent": False,
    "found": False,
    "po_box_hunt_complete": True,
    "product_type_cad_write_xhr": PRODUCT_TYPE_CAD_WRITE_XHR,
    "method": PRODUCT_TYPE_CAD_WRITE_METHOD,
    "path": PRODUCT_TYPE_CAD_WRITE_PATH,
    "body": PRODUCT_TYPE_CAD_WRITE_BODY,
    "hunt_closed": PRODUCT_TYPE_CAD_WRITE_HUNT_CLOSED,
    "update_item_type_sets_product_type_cad": (
        UPDATE_ITEM_TYPE_SETS_PRODUCT_TYPE_CAD
    ),
    "set_part_mode_sets_product_type_cad": SET_PART_MODE_SETS_PRODUCT_TYPE_CAD,
    "shown_via": PRODUCT_TYPE_CAD_SHOWN_VIA,
    "pass_vs_fail": CONTOURS_PASS_VS_FAIL,
    "capture_needed": PRODUCT_TYPE_CAD_WRITE_CAPTURE_NEEDED,
    "box_artifacts_present": False,
    "dropbox_artifacts_present": False,
    "do_not_remint": True,
    "do_not_patch": True,
    "unlocks_automation_contours_fill": False,
    "q10333": dict(Q10333_V1_PRODUCTTYPE),
    "q10348": dict(Q10348_V1_PRODUCTTYPE),
    "ruled_out": (
        "POST /Part/UpdateItemType {ID, ItemType}",
        "POST /CadImport/SetPartMode {ID, PartMode}",
        "UpdatePropertyValue",
        "AddItem_DXFFiles ProductType Cad noun",
    ),
}


def live_producttype_cad_write() -> dict[str, Any]:
    """Read-only hunt result. Does not invent a ProductType Cad persist."""
    out = dict(LIVE_PRODUCTTYPE_CAD_WRITE)
    out["q10333"] = dict(Q10333_V1_PRODUCTTYPE)
    out["q10348"] = dict(Q10348_V1_PRODUCTTYPE)
    out["ruled_out"] = tuple(LIVE_PRODUCTTYPE_CAD_WRITE["ruled_out"])
    return out
