"""Spent 21785-2 Outer Boom Insulated STEP — ZZ-DEL ARCHIVED.

Live capture @ ab58a96 leftover ``d5a6987d`` (read-only). CAD Files
upload+explode bound ``#gridDXFParts`` list_n=14 (Root+13). ImageString
nonempty 13/13 is preview only. InternalData empty 14/14,
OutsidePerimeter=0. Finish correctly refused (4a99b86).

Quoted from /workspace/step-part-create-capture-21785-2.json (emptiness
counts only — never contour JSON). Do **not** invent InternalData.
Do not remint 21785-1 / 21785-2 / 21785-3. Leave a7d6ca50.
"""

from __future__ import annotations

from typing import Any

SPENT_QUOTE_ID_PREFIX = "d5a6987d"
SPENT_QUOTE_NUMBER = "21785-2"
CAPTURE_COMMIT = "ab58a96"

# Live /part/create t.List emptiness — never InternalData/ImageString values.
LIVE_21785_2_TLIST_EMPTY = {
    "quote_id_prefix": SPENT_QUOTE_ID_PREFIX,
    "quote_number": SPENT_QUOTE_NUMBER,
    "readonly": True,
    "zz_del_archived": True,
    "finish_posted": False,
    "finish_refused": True,
    "list_n": 14,
    "root_n": 1,
    "kid_n": 13,
    "internaldata_empty_n": 14,
    "internaldata_nonempty_n": 0,
    "imagestring_nonempty_n": 13,
    "imagestring_empty_n": 1,
    "outsideperimeter": 0,
    "tlist_bind_source": False,
    "imagestring_without_internaldata": True,
}

# QuoteOrderEdit hunt: createAllParts collects #gridDXF IDs then calls
# DoCreateDXFParts immediately. No classify / SetPartMode / unfold XHR
# in between writes InternalData or CuttingLength.
EXPLODE_TO_DOCREATE_FILL = {
    "createAllParts": {
        "between_collect_and_docreate": ("SourceDataID", "Units"),
        "xhr": None,
        "writes_internaldata": False,
        "writes_cuttinglength": False,
    },
    "DoCreateDXFParts": {
        "path": "/part/create",
        "body": ("Location", "IDList", "unitList", "OtherFileIDList", "Height", "Width"),
        "success": "t.List as-is onto #gridDXFParts",
        "writes_internaldata": False,
    },
    "SetPartMode": {
        "path": "/CadImport/SetPartMode",
        "body": ("ID", "PartMode"),
        "writes_internaldata": False,
        "writes_cuttinglength": False,
    },
    "SetDXFFilePartMode": {
        "writes_internaldata": False,
        "writes_cuttinglength": False,
    },
    "Unfold": {
        "hits": 0,
        "writes_internaldata": False,
    },
    "GetPerimeterAndWeight": {
        "targets": "gridPDF",
        "fills_cuttinglength": True,
        "fills_filelist_internaldata": False,
    },
    "classify_finish_internaldata_fill": None,
}


def live_21785_2_tlist_empty() -> dict[str, Any]:
    """Read-only 21785-2 explode emptiness. Do not invent InternalData."""
    return dict(LIVE_21785_2_TLIST_EMPTY)


def explode_to_docreate_fill_dump() -> dict[str, Any]:
    """Hunt: no fill XHR between #gridDXF collect and DoCreateDXFParts."""
    return dict(EXPLODE_TO_DOCREATE_FILL)
