"""Spent 35136-1 — leftover 8973f890 after Kyle STEP HAR.

Kyle HAR (emptiness / key names only — no Contours JSON):

    Upload
      → GET /CadImport/Data OpenContourCount=0
      → POST /part/create 3× bar InternalData empty
      → POST /Quote/AddItem_DXFFiles InternalData empty bar_flat

Contours never filled. That confirms fail-close
(``cad_internaldata_empty_after_explode`` /
``step_explode_no_internaldata``). It does **not** unlock Contours fill.
Do not invent Contours / InternalData. Do not remint / PATCH 35136-1 /
8973f890.

Child names on leftover explode (comment only): 35137 / 35138.

Live 14327-5 / c5cd8689 (flat-plate STEP) later showed the same empty
InternalData after ``/part/create`` — no extra plate CadImport/UI XHR.
Exact missing call is server ``POST /part/create t.List`` with nonempty
InternalData AND ImageString. Do not silent-graft Contours onto leftovers.
"""

from __future__ import annotations

from typing import Any

SPENT_QUOTE_ID = "8973f890-b2a1-48fb-b6be-3530caeb1819"
SPENT_QUOTE_ID_PREFIX = "8973f890"
SPENT_QUOTE_NUMBER = "35136-1"
LEFTOVER_CHILD_NAMES = ("35137", "35138")

# Leftover HAR shape — emptiness bools / key names only. Never contour
# JSON or InternalData values. OpenContourCount=0 is emptiness, not fill.
LIVE_35136_1_HAR: dict[str, Any] = {
    "quote_id": SPENT_QUOTE_ID,
    "quote_id_prefix": SPENT_QUOTE_ID_PREFIX,
    "quote_number": SPENT_QUOTE_NUMBER,
    "child_names": list(LEFTOVER_CHILD_NAMES),
    "readonly": True,
    "zz_del": True,
    "finish_posted": False,
    "finish_refused": True,
    "finish_why": "cad_internaldata_empty_after_explode",
    "step_explode_no_internaldata": True,
    "tlist_bind_source": False,
    "internaldata_empty": True,
    "contours_empty": True,
    "contours_never_filled": True,
    "opencontourcount": 0,
    "part_create_n": 3,
    "part_create_producttype": "bar",
    "additem_productsubtype": "bar_flat",
    "invent": False,
    "unlocks_contours_fill": False,
    "fail_close": True,
    "follow_up": (
        "Live 14327-5 flat plate confirmed the same miss as this bar "
        "leftover — exact missing call is POST /part/create t.List "
        "InternalData+ImageString. QuoteOrderEdit createAllParts has no "
        "extra CadImport/UI XHR. Do not silent-graft Contours onto "
        "bar_flat leftovers."
    ),
    "routes": {
        "POST /CadImport/UploadItem_DXFFiles": {
            "internaldata_empty": True,
            "contours_empty": True,
            "bindable": False,
        },
        "GET /CadImport/Data": {
            "opencontourcount": 0,
            "internaldata_empty": True,
            "contours_empty": True,
            "bindable": False,
        },
        "POST /part/create": {
            "n": 3,
            "producttype": "bar",
            "tlist_bind_source": False,
            "internaldata_empty": True,
            "bindable": False,
            "child_names": list(LEFTOVER_CHILD_NAMES),
        },
        "POST /Quote/AddItem_DXFFiles": {
            "internaldata_empty": True,
            "productsubtype": "bar_flat",
            "bindable": False,
        },
    },
}


def leftover_35136_1_har_dump() -> dict[str, Any]:
    """Read-only 35136-1 HAR emptiness. Does not unlock Contours fill."""
    return dict(LIVE_35136_1_HAR)


def leftover_35136_1_har_xhrs() -> list[dict[str, Any]]:
    """Sanitized HAR XHRs — emptiness / names only. No Contours values."""
    bars = [
        {
            "Name": "35136-1",
            "ProductType": "bar",
            "InternalData": "",
            "ImageString": "",
        },
        {
            "Name": "35137",
            "ProductType": "bar",
            "InternalData": "",
            "ImageString": "",
        },
        {
            "Name": "35138",
            "ProductType": "bar",
            "InternalData": "",
            "ImageString": "",
        },
    ]
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
            "method": "GET",
            "path": "/CadImport/Data",
            "response": {
                "List": [
                    {
                        "OpenContourCount": 0,
                        "InternalData": "",
                        "Contours": [],
                    }
                ]
            },
        },
        {
            "method": "POST",
            "path": "/part/create",
            "List": bars,
        },
        {
            "method": "POST",
            "path": "/Quote/AddItem_DXFFiles",
            "List": [
                {
                    "Name": name,
                    "ProductType": "bar",
                    "ProductSubType": "bar_flat",
                    "InternalData": "",
                    "FileType": "Cad",
                }
                for name in ("35136-1", "35137", "35138")
            ],
        },
    ]
