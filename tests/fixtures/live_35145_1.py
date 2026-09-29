"""Kyle Loom c9d7c05a — Q10243 / 35145-1 STEP classify-before-Finish.

Exact UI: New Quote → PN → Org Time Waco → orange CAD Files → drop STEP
on +Add Files → blue Next → #gridDXFParts classify table → per-row Part
Mode (Cad plate/sheet, Linear tube/bar/angle/channel + Product Type,
Component purchased) → green Finish (OnAddDXFClick / AddItem_DXFFiles).

Do not remint 35145-1 / Q10243. Do not remint 21785-1/2/3. Leave a7d6ca50.
Do not invent InternalData. Do not fire UpdateDXF_LoadNew as Finish.
"""

from __future__ import annotations

from typing import Any

LOOM_ID = "c9d7c05a"
GOLD_QUOTE_NUMBER = "Q10243"
GOLD_PART_KEY = "35145-1"
ORG = "Time Waco"

KYLE_STEP_CLASSIFY_BEFORE_FINISH = {
    "loom": LOOM_ID,
    "quote_number": GOLD_QUOTE_NUMBER,
    "part_key": GOLD_PART_KEY,
    "readonly": True,
    "steps": (
        "upload_step_add_files",
        "next_createAllParts",
        "classify_part_mode",
        "finish_additem_dxf_files",
    ),
    "next": {
        "caller": "createAllParts",
        "grid": "#gridDXFParts",
    },
    "part_mode": {
        "Cad": "plate/sheet leave",
        "Linear": "tube/bar/angle/channel + Product Type/SKU",
        "Component": "purchased hardware",
    },
    "finish": {
        "fn": "OnAddDXFClick",
        "path": "/Quote/AddItem_DXFFiles",
        "not": "UpdateDXF_LoadNew",
    },
    "fail_close": (
        "PartMode still null after classify",
        "InternalData empty after Finish attempt",
    ),
}


def kyle_step_classify_dump() -> dict[str, Any]:
    return dict(KYLE_STEP_CLASSIFY_BEFORE_FINISH)
