"""ProductType=Cad write XHR hunt — not found. invent=false.

PR39: POST /Part/UpdateItemType {ID, ItemType=Cad} sets ItemType only.
Classify / kendo stamps ProductType=100. Live UI may render that enum
as Cad or ``part``. This hunt asked for the write that persists a
ProductType Cad noun on Contours PASSes.

Allowed sources (2026-09-14, PR18 tip + live GET):

1. Box / workspace artifacts named live-*-kyle-ui*, live-*-xhr*.json,
   live-q10333*, live-h638*, live-mouse-cad-*, step-contours-kyle-har*,
   live-contours-our-bug-dig*, mid-wizard xhr — absent on this VM and
   Kyle Dropbox (same inventory as Q10359 BOX_ARTIFACT_MINE).
2. Read-only GET v1/quote of forever-protects (never remint / PATCH /
   Finish / ZZ-DEL):
     Q10333 / b5f56ac3  ProductType=100  ProductTypeName absent
                        ItemType=null  ProductSubType=prt_dxf
                        NumberOfContours=1
     Q10348 / 1defeed8  same shape (H.16.70)
     Peers Q10336 / Q10339 / Q10344 / Q10349 / Q10351 same
     Q10346 plate kid  ProductType=100  prt_dxf  NumberOfContours=12
     Contrast Q10354   ProductType=100  prt_mill  NumberOfContours=0
     Contrast Q10365   ProductType=100  prt_dxf  NumberOfContours=1
                        (same v1 shape as PASSes; ``part`` was UI)
3. PR18 bind_plate_step_product_type_cad writes kendo ProductType=100
   plus UpdateItemType ItemType=Cad — not a Cad noun persist.

Hypothesis check:
  UpdatePropertyValue / grid ProductType=Cad bind / AddItem_DXFFiles
  Cad-noun field — not found. AddItem_DXFFiles copies FileList
  ProductType (enum 100). QuoteOrderEdit GetPDFData includes
  ProductType:r.ProductType (PDF path). No UpdatePropertyValue.

Cad on Contours PASSes is shown via ProductType enum 100 +
ProductSubType prt_dxf (UI may label 100 Cad). Not a separate
ProductType=Cad write. PRODUCT_TYPE_CAD_WRITE_XHR stays None.
Do not invent a persist call.

Capture still needed (only if a Cad-noun persist is still believed):
  Fresh unused STEP — never remint protected quotes.
  DevTools HAR of Kyle Adjust Properties Product Type dropdown
  (not File type / UpdateItemType). Persist method+path+body of any
  XHR whose request or response contains ProductTypeName,
  ProductType:"Cad", or ProductType=Cad. If none fire before Finish,
  Cad noun stays UI-only.
"""

from __future__ import annotations

from typing import Any

from secturafab.cadimport_js import (
    PRODUCT_TYPE_CAD_SHOWN_VIA,
    PRODUCT_TYPE_CAD_WRITE_BODY,
    PRODUCT_TYPE_CAD_WRITE_CAPTURE_NEEDED,
    PRODUCT_TYPE_CAD_WRITE_METHOD,
    PRODUCT_TYPE_CAD_WRITE_PATH,
    PRODUCT_TYPE_CAD_WRITE_XHR,
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
    "category": None,
    "product_subtype": "prt_dxf",
    "number_of_contours": 1,
    "contours_pass": True,
}

Q10348_V1_PRODUCTTYPE: dict[str, Any] = {
    "quote_number": "Q10348",
    "quote_id": "1defeed8-d95d-4939-b2fd-0a1774e56c6e",
    "product_type": 100,
    "product_type_name": None,
    "item_type": None,
    "category": None,
    "product_subtype": "prt_dxf",
    "number_of_contours": 1,
    "contours_pass": True,
}

LIVE_PRODUCTTYPE_CAD_WRITE: dict[str, Any] = {
    "invent": False,
    "found": False,
    "product_type_cad_write_xhr": PRODUCT_TYPE_CAD_WRITE_XHR,
    "method": PRODUCT_TYPE_CAD_WRITE_METHOD,
    "path": PRODUCT_TYPE_CAD_WRITE_PATH,
    "body": PRODUCT_TYPE_CAD_WRITE_BODY,
    "update_item_type_sets_product_type_cad": (
        UPDATE_ITEM_TYPE_SETS_PRODUCT_TYPE_CAD
    ),
    "shown_via": PRODUCT_TYPE_CAD_SHOWN_VIA,
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
