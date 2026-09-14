"""Contours fill XHR hunt — NumberOfContours≥1. invent=false.

CoS 2026-09-14: no ProductType=Cad write to chase. Dig fill instead.
Safe Cave burns paused. Never remint / PATCH / Finish / ZZ-DEL
Q10333 / Q10348 / peers.

Fill XHR not found. QuoteOrderEdit snippets have 0 NumberOfContours
hits. Named classify / SetPartMode / UpdateItemType / GetBorderSize /
UpdateData paths are already not-fill. OnAddDXFClick copies
#gridDXFParts as-is.

Read-only GET 2026-09-14 (PASS vs FAIL distinguisher = Contours≥1):
  Q10333 / b5f56ac3  NumberOfContours=1  ProductType=100  prt_dxf
                     Laser  0.1875 in  ItemType/PartMode null
  Q10348 / 1defeed8  NumberOfContours=1  same shape (H.16.70)
  Q10354 / 7881d4b3  NumberOfContours=0  ProductType=100  prt_mill
                     Laser  0.1875 in  ItemType/PartMode null

CONTOURS_FILL_XHR stays None. Do not invent Contours / InternalData
or a fill body. Capture still needed: fresh unused STEP mid-wizard
HAR when NumberOfContours flips 0→1.
"""

from __future__ import annotations

from typing import Any

from secturafab.cadimport_js import (
    CLASSIFY_FINISH_INTERNALDATA_FILL,
    PRODUCT_TYPE_CAD_WRITE_HUNT_CLOSED,
    PRODUCT_TYPE_CAD_WRITE_XHR,
    UPDATE_ITEM_TYPE_PATH,
)
from secturafab.website import (
    CONTOURS_FILL_CAPTURE_NEEDED,
    CONTOURS_FILL_HUNT_CLOSED,
    CONTOURS_FILL_XHR,
    SINGLE_PLATE_CONTOURS_FLIP_XHR,
    STEP_CONTOURS_FILL_UNLOCKED,
    STEP_CONTOURS_MISSING_CALL,
)

LIVE_CONTOURS_FILL_XHR: dict[str, Any] = {
    "invent": False,
    "found": False,
    "cad_noun_write_closed": PRODUCT_TYPE_CAD_WRITE_HUNT_CLOSED,
    "product_type_cad_write_xhr": PRODUCT_TYPE_CAD_WRITE_XHR,
    "contours_fill_xhr": CONTOURS_FILL_XHR,
    "single_plate_contours_flip_xhr": SINGLE_PLATE_CONTOURS_FLIP_XHR,
    "classify_finish_internaldata_fill": CLASSIFY_FINISH_INTERNALDATA_FILL,
    "fill_unlocked": STEP_CONTOURS_FILL_UNLOCKED,
    "hunt_closed": CONTOURS_FILL_HUNT_CLOSED,
    "pass_vs_fail": "number_of_contours_ge_1",
    "pass_signal": "NumberOfContours>=1",
    "missing_call": STEP_CONTOURS_MISSING_CALL,
    "capture_needed": CONTOURS_FILL_CAPTURE_NEEDED,
    "quote_order_edit_number_of_contours_hits": 0,
    "safe_cave_burns_paused": True,
    "do_not_remint": True,
    "do_not_patch": True,
    "unlocks_automation_contours_fill": False,
    "q10333": {
        "quote_number": "Q10333",
        "quote_id": "b5f56ac3-326d-48e9-b82d-1e09a7897107",
        "product_type": 100,
        "number_of_contours": 1,
        "contours_pass": True,
    },
    "q10348": {
        "quote_number": "Q10348",
        "quote_id": "1defeed8-d95d-4939-b2fd-0a1774e56c6e",
        "product_type": 100,
        "number_of_contours": 1,
        "contours_pass": True,
    },
    "q10354": {
        "quote_number": "Q10354",
        "quote_id": "7881d4b3-5408-4ff4-ab18-6490170e6331",
        "product_type": 100,
        "number_of_contours": 0,
        "contours_pass": False,
    },
    "ruled_out": (
        UPDATE_ITEM_TYPE_PATH,
        "/CadImport/SetPartMode",
        "/CadImport/Data",
        "/Quote/GetBorderSize",
        "/CadImport/UpdateData",
    ),
}


def live_contours_fill_xhr() -> dict[str, Any]:
    """Read-only fill hunt. Does not invent Contours or a fill body."""
    out = dict(LIVE_CONTOURS_FILL_XHR)
    out["q10333"] = dict(LIVE_CONTOURS_FILL_XHR["q10333"])
    out["q10348"] = dict(LIVE_CONTOURS_FILL_XHR["q10348"])
    out["q10354"] = dict(LIVE_CONTOURS_FILL_XHR["q10354"])
    out["ruled_out"] = tuple(LIVE_CONTOURS_FILL_XHR["ruled_out"])
    return out
