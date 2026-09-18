"""Spent EHB3112-1 — leftover CAD Files dialog, no Finish.

Prefix cf8ec36e (full GUID not restated). Read-only leftover dump; dialog
closed; finish_posted=false. Cookie HTTP UploadItem_DXFFiles left #gridDXF
empty (same miss as Image Files #gridPDF on 103535-1). Live GET 0.

Capture named /workspace/live-cadfiles-bind.json — fixture here.
Do not PATCH. Do not remint. Do not Finish this leftover.
"""

from __future__ import annotations

from typing import Any

SPENT_QUOTE_ID_PREFIX = "cf8ec36e"
SPENT_QUOTE_NUMBER = "EHB3112-1"

# Leftover CAD Files dialog on cf8ec36e (read-only; dialog closed; no Finish).
LEFTOVER_GRIDDXF_BIND = {
    "quote_id_prefix": SPENT_QUOTE_ID_PREFIX,
    "quote_number": SPENT_QUOTE_NUMBER,
    "readonly": True,
    "dialog_closed": True,
    "finish_posted": False,
    "getitem_addview": {
        "ItemType": "dxf",
        "injects": "#files inside #dxfupload_Zone",
        "gridDXF": {"Data": [], "Total": 0},
        "kendoUpload": "#files",
    },
    "kendoUpload": {
        "selector": "#files",
        "zone": "#dxfupload_Zone",
        "success": "onSuccess_Upload",
        "complete": "onComplete_Upload",
        "upload": "onUpload_DXFUpload",
        "dropZone": ".dropZoneElement",
        "async": {
            "saveUrl": "/CadImport/UploadItem_DXFFiles",
            "autoUpload": True,
            "batch": True,
        },
        "validation": {
            "allowedExtensions": [".dxf", ".stp", ".step"],
        },
    },
    "onSuccess_Upload": {
        "only_fill": True,
        "adds": "#gridDXF.dataSource.add from n.response.List as-is",
        "not_grid": "#gridDXFParts",
        "list_other": "#gridOther",
        "writes_gridDXFParts_internaldata": False,
        "writes_gridDXFParts_cuttinglength": False,
    },
    "gridDXF_transport": {"read": {"url": ""}},
    "GetDXFData": {
        "exists": False,
    },
    "Next": {
        "caller": "createAllParts",
        "function": "DoCreateDXFParts",
        "path": "/part/create",
        "body": ("Location", "IDList", "unitList", "OtherFileIDList", "Height", "Width"),
        "success": "t.List as-is onto #gridDXFParts",
        "cookie_http_part_create_is_gold": False,
    },
    "OnAddDXFClick": {
        "walks": "#gridDXFParts",
        "keeps": "ErrorStatus===0 && Qty>0",
        "FileList": "#gridDXFParts ErrorStatus===0 Qty>0",
        "copies_internaldata": True,
        "fills_internaldata": False,
        "omits": ("CuttingLength", "CadType", "FileType"),
    },
    "GetPerimeterAndWeight": {
        "targets": "gridPDF",
        "fills_dxf_internaldata": False,
    },
    "UpdateDataNext": {
        "gold": False,
        "editor_only": True,
        "path": "/CadImport/UpdateDataNext",
    },
    "live_ehb3112_1": {
        "cookie_http_uploads": 1,
        "gridDXF_n": 0,
        "gridDXFParts_n": 0,
        "finish_posted": False,
        "cad_n": 0,
        "finish_why": "empty_gridDXF",
    },
}


def leftover_griddxf_bind_dump() -> dict[str, Any]:
    """Leftover CAD Files dialog: #files kendoUpload is the only #gridDXF fill."""
    return dict(LEFTOVER_GRIDDXF_BIND)


def live_ehb3112_1_cookie_http_empty_grid() -> dict[str, Any]:
    """Notes + GET shape after cookie HTTP upload / empty #gridDXF."""
    return {
        "IDPrefix": SPENT_QUOTE_ID_PREFIX,
        "QuoteNumber": SPENT_QUOTE_NUMBER,
        "ItemCount": 0,
        "ItemList": [],
        "cookie_http_uploads": 1,
        "gridDXF_n": 0,
        "gridDXFParts_n": 0,
        "finish_posted": False,
        "cad_n": 0,
        "finish_why": "empty_gridDXF",
    }
