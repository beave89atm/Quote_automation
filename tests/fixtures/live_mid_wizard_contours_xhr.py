"""Mid-wizard Contours XHR carrier notes (mint skipped).

Live mint was skipped (session busy on protected tabs). Notes restated
from live-mid-wizard-contours-xhr.json — invent=false, no payloads.

NumberOfContours=1 appears on:
  finished GET v1 ItemList
  QuoteItem_ReadTreeListData
Absent on:
  QuoteItem_Read list items

CadImport/Data has no NumberOfContours. OpenContourCount=0 even on PASS.

Ruled out as Contours flip carrier:
  GET /CadImport/Data
  POST /Part/UpdateItemType
  /Quote/GetBorderSize

Still open URL-only (no invented body):
  POST /Quote/AddItem_DXFFiles
  /quote/ItemEdit
  post-Finish GET v1/quote ItemList
  GET /Quote/QuoteItem_ReadTreeListData

Persist PASS is NumberOfContours≥1 on v1 ItemList / TreeListData.
Never OpenContourCount. CoS: Cad-noun write closed; chase is fill.
Forever-protect Q10333 / Q10336 / Q10339 / Q10344.
Empty-InternalData Time STEPs stay refuse. Do not remint.
Safe Cave burns paused. invent=false.
"""

from __future__ import annotations

from typing import Any

from secturafab.cadimport_js import (
    GET_BORDER_SIZE_PATH,
    UPDATE_ITEM_TYPE_PATH,
)
from secturafab.website import (
    STEP_CONTOURS_FILL_UNLOCKED,
    WEBSITE_FINISH_PATHS,
)

LIVE_MID_WIZARD_CONTOURS_XHR: dict[str, Any] = {
    "invent": False,
    "mid_wizard_live_mint": "skipped_session_busy_protected_tabs",
    "unlocks_automation_contours_fill": False,
    "fill_unlocked": STEP_CONTOURS_FILL_UNLOCKED,
    "pass_signal": "NumberOfContours>=1",
    "not_pass_signal": "OpenContourCount",
    "number_of_contours_on": (
        "v1/quote ItemList",
        "/Quote/QuoteItem_ReadTreeListData",
    ),
    "number_of_contours_absent_on": ("/Quote/QuoteItem_Read list items",),
    "cadimport_data_has_number_of_contours": False,
    "cadimport_open_contour_count_even_on_pass": 0,
    "ruled_out_flip_carriers": (
        "/CadImport/Data",
        UPDATE_ITEM_TYPE_PATH,
        GET_BORDER_SIZE_PATH,
    ),
    "open_url_only": (
        "/Quote/AddItem_DXFFiles",
        "/quote/ItemEdit",
        "GET v1/quote ItemList",
        WEBSITE_FINISH_PATHS["quote_item_read_treelist"],
    ),
    "forever_protect": ("Q10333", "Q10336", "Q10339", "Q10344"),
}


def live_mid_wizard_contours_xhr() -> dict[str, Any]:
    """Read-only carrier notes. No invented payloads."""
    out = dict(LIVE_MID_WIZARD_CONTOURS_XHR)
    out["number_of_contours_on"] = tuple(
        LIVE_MID_WIZARD_CONTOURS_XHR["number_of_contours_on"]
    )
    out["number_of_contours_absent_on"] = tuple(
        LIVE_MID_WIZARD_CONTOURS_XHR["number_of_contours_absent_on"]
    )
    out["ruled_out_flip_carriers"] = tuple(
        LIVE_MID_WIZARD_CONTOURS_XHR["ruled_out_flip_carriers"]
    )
    out["open_url_only"] = tuple(LIVE_MID_WIZARD_CONTOURS_XHR["open_url_only"])
    out["forever_protect"] = tuple(LIVE_MID_WIZARD_CONTOURS_XHR["forever_protect"])
    return out
