"""Spent 14327-5 — leftover c5cd8689 after flat-plate STEP empty InternalData.

Live capture @ 7b59ff0 (emptiness / key names only — no Contours JSON):

    mint 14327-5
      → POST /CadImport/UploadItem_DXFFiles
      → POST /part/create list_len=1 InternalData empty 1/1
         ImageString nonempty preview-only
         tlist_bind_source=false
         ProductType null
      → GET /CadImport/Data bindable=false OpenContourCount empty/null
      → GET /CadImport/CADData bindable=false
      → Finish refused (invented=false)
      → ZZ-DEL-14327-5

QuoteOrderEdit ``createAllParts`` has no intervening CadImport/UI XHR
between #gridDXF collect and ``DoCreateDXFParts`` / ``POST /part/create``.
GET Data/CADData are copy-if-nonempty only — both empty here.

This is the **flat-plate** twin of leftover 35136-1 (3× bar). Same miss:
server ``t.List`` never returned InternalData+ImageString. There is no
extra JS step to fire. Do not invent Contours / InternalData. Do not
remint / PATCH 14327-5 / c5cd8689 / ZZ-DEL-14327-5.
"""

from __future__ import annotations

from typing import Any

SPENT_QUOTE_ID = "c5cd8689-fed4-44d6-b2f5-f96bda8af424"
SPENT_QUOTE_ID_PREFIX = "c5cd8689"
SPENT_QUOTE_NUMBER = "14327-5"
SPENT_ZZ_DEL_NUMBER = "ZZ-DEL-14327-5"

# Leftover capture shape — emptiness bools / key names only. Never contour
# JSON or InternalData values. OpenContourCount empty/null is emptiness.
LIVE_14327_5_CAPTURE: dict[str, Any] = {
    "quote_id": SPENT_QUOTE_ID,
    "quote_id_prefix": SPENT_QUOTE_ID_PREFIX,
    "quote_number": SPENT_QUOTE_NUMBER,
    "zz_del_number": SPENT_ZZ_DEL_NUMBER,
    "readonly": True,
    "zz_del": True,
    "step_kind": "flat_plate",
    "finish_posted": False,
    "finish_refused": True,
    "finish_why": "cad_internaldata_empty_after_explode",
    "step_explode_no_internaldata": True,
    "tlist_bind_source": False,
    "internaldata_empty": True,
    "internaldata_empty_n": 1,
    "internaldata_nonempty_n": 0,
    "imagestring_empty": False,
    "imagestring_without_internaldata": True,
    "contours_empty": True,
    "contours_never_filled": True,
    "opencontourcount": None,
    "opencontourcount_empty": True,
    "part_create_n": 1,
    "part_create_producttype": None,
    "producttype_empty": True,
    "cadimport_data_bindable": False,
    "cadimport_caddata_bindable": False,
    "invent": False,
    "unlocks_contours_fill": False,
    "fail_close": True,
    "no_extra_cadimport_xhr": True,
    "missing_call": "POST /part/create t.List InternalData+ImageString",
    "follow_up": (
        "Exact missing call is server POST /part/create t.List with "
        "nonempty InternalData AND ImageString. QuoteOrderEdit "
        "createAllParts has no intervening CadImport/UI XHR. GET "
        "CadImport/Data+CADData were bindable=false (OpenContourCount "
        "empty/null). Flat plate 14327-5 matches bar 35136-1 — do not "
        "silent-graft Contours. Do not remint c5cd8689 / 14327-5."
    ),
    "routes": {
        "POST /CadImport/UploadItem_DXFFiles": {
            "internaldata_empty": True,
            "contours_empty": True,
            "bindable": False,
        },
        "POST /part/create": {
            "n": 1,
            "producttype": None,
            "tlist_bind_source": False,
            "internaldata_empty": True,
            "internaldata_empty_n": 1,
            "imagestring_without_internaldata": True,
            "bindable": False,
        },
        "GET /CadImport/Data": {
            "opencontourcount": None,
            "opencontourcount_empty": True,
            "internaldata_empty": True,
            "contours_empty": True,
            "bindable": False,
        },
        "GET /CadImport/CADData": {
            "internaldata_empty": True,
            "contours_empty": True,
            "bindable": False,
        },
    },
}


def leftover_14327_5_plate_dump() -> dict[str, Any]:
    """Read-only 14327-5 emptiness. Does not unlock Contours fill."""
    return dict(LIVE_14327_5_CAPTURE)


def leftover_14327_5_capture_xhrs() -> list[dict[str, Any]]:
    """Sanitized capture XHRs — emptiness / names only. No Contours values."""
    plate = {
        "Name": "14327-5",
        "ProductType": None,
        "InternalData": "",
        "ImageString": "iVBORw0KGgo",
    }
    return [
        {
            "method": "POST",
            "path": "/CadImport/UploadItem_DXFFiles",
            "n": 1,
            "internaldata_empty": True,
            "internaldata_nonempty_n": 0,
            "imagestring_empty": True,
            "imagestring_nonempty_n": 0,
        },
        {
            "method": "POST",
            "path": "/part/create",
            "List": [plate],
        },
        {
            "method": "GET",
            "path": "/CadImport/Data",
            "response": {
                "List": [
                    {
                        "OpenContourCount": None,
                        "InternalData": "",
                        "Contours": None,
                    }
                ]
            },
        },
        {
            "method": "GET",
            "path": "/CadImport/CADData",
            "response": {
                "InternalData": "",
                "Contours": None,
                "Length": 1,
                "Width": 1,
                "WebGL": True,
            },
        },
    ]
