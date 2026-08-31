"""Gold 21678-1 / Q10056 STEP look — hand-quoted. Do not PATCH. Do not remint.

Kyle UI: CAD Files drop → classify → Finish (OnAddDXFClick /
AddItem_DXFFiles) with no per-part #DXFEdit. GET Cad is PR + laser
pack + UnitCost. ItemList has no InternalData field (FileList-at-Finish).

UI-only gold — do not open/PATCH. GetPerimeterAndWeight remains
#gridPDF only (not the CAD Files InternalData analog). CAD Files
bind is in-page #files → onSuccess_Upload → #gridDXF, then page
Next createAllParts. Do not fire UpdateDataNext. Leave a7d6ca50.
"""

from __future__ import annotations

from typing import Any

GOLD_QUOTE_ID = "a7d6ca50-efec-409d-bd32-e68012e710c3"
GOLD_QUOTE_NUMBER = "21678-1"
ORG = "Time Waco"

LEFTOVER_DXF_PACK_BIND = {
    "quote_id": GOLD_QUOTE_ID,
    "quote_number": GOLD_QUOTE_NUMBER,
    "readonly": True,
    "finish_posted": False,
    "pack_xhr_named": False,
    "addrow_stamps_pr": False,
    "pack_already_on_additem_list": True,
    "list_pack_keys": ("Tag", "ProductionReady", "OperationCostList"),
    "OnAddDXFClick": {
        "FileList": "#gridDXFParts ErrorStatus===0 Qty>0",
        "no_dxfedit": True,
    },
    "UpdatePerimeterWeight": {
        "on": ("Stock_X", "Stock_Y", "Length", "Width"),
        "xhr": "POST /Quote/GetPerimeterAndWeight",
        "when": "change_before_AddItem",
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
    "classify_finish_internaldata_fill": None,
}


def leftover_dxf_pack_bind_dump() -> dict[str, Any]:
    """Leftover analog: pack is on AddItem_DXFFiles List after Stock type."""
    return dict(LEFTOVER_DXF_PACK_BIND)
